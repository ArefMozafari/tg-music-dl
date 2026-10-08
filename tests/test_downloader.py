"""Tests for src/tg_music_dl/downloader.py."""
import asyncio
from types import SimpleNamespace

import pytest

from tg_music_dl.downloader import download_channel
from tg_music_dl.state import DownloadState

AUDIO_DOCUMENT = SimpleNamespace(mime_type="audio/mpeg")
CHANNEL = "channel"


def make_message(message_id, name, content=b"song", voice=False):
    """Builds a stand-in Telethon message holding one audio file (or voice note)."""
    return SimpleNamespace(
        id=message_id, audio=None if voice else AUDIO_DOCUMENT, voice=AUDIO_DOCUMENT if voice else None,
        video=None, video_note=None, gif=None, document=AUDIO_DOCUMENT,
        file=SimpleNamespace(name=name, ext=".mp3", size=len(content)), content=content)


class FakeClient:
    """Serves messages newest first and writes their content where it is told to."""

    def __init__(self, messages, drop_connection_on=None):
        self.messages = messages
        self.drop_connection_on = drop_connection_on

    async def iter_messages(self, entity):
        for message in self.messages:
            yield message

    async def download_media(self, message, file, progress_callback):
        with open(file, "wb") as partial:
            partial.write(message.content[:1])
            if message.id == self.drop_connection_on:
                raise ConnectionError("connection dropped")
            partial.write(message.content[1:])
        progress_callback(len(message.content), len(message.content))
        return file


def run(client, output, state, limit=20, types=("audio",)):
    return asyncio.run(download_channel(client, None, CHANNEL, str(output), limit, set(types), state))


@pytest.fixture
def state(tmp_path):
    return DownloadState(tmp_path / "state.json")


class TestDownloadChannel:
    def test_should_download_the_newest_files_up_to_the_limit(self, tmp_path, state):
        client = FakeClient([make_message(3, "c.mp3"), make_message(2, "b.mp3"), make_message(1, "a.mp3")])

        count = run(client, tmp_path, state, limit=2)

        assert count == 2
        assert (tmp_path / "c.mp3").read_bytes() == b"song"
        assert (tmp_path / "b.mp3").exists()
        assert not (tmp_path / "a.mp3").exists()
        assert state.has(CHANNEL, 3) and state.has(CHANNEL, 2)

    def test_should_skip_messages_already_downloaded(self, tmp_path, state):
        state.add(CHANNEL, 2)
        client = FakeClient([make_message(2, "b.mp3"), make_message(1, "a.mp3")])

        count = run(client, tmp_path, state, limit=1)

        assert count == 1
        assert (tmp_path / "a.mp3").exists()
        assert not (tmp_path / "b.mp3").exists()

    def test_should_skip_media_types_not_asked_for(self, tmp_path, state):
        client = FakeClient([make_message(2, "note.ogg", voice=True), make_message(1, "a.mp3")])

        run(client, tmp_path, state)

        assert not (tmp_path / "note.ogg").exists()
        assert (tmp_path / "a.mp3").exists()

    def test_should_record_an_identical_file_already_on_disk_without_downloading(self, tmp_path, state):
        (tmp_path / "a.mp3").write_bytes(b"song")

        count = run(FakeClient([make_message(1, "a.mp3")]), tmp_path, state)

        assert count == 0
        assert state.has(CHANNEL, 1)

    def test_should_save_a_different_file_with_the_same_name_alongside(self, tmp_path, state):
        (tmp_path / "a.mp3").write_bytes(b"another song")

        count = run(FakeClient([make_message(1, "a.mp3")]), tmp_path, state)

        assert count == 1
        assert (tmp_path / "a.mp3").read_bytes() == b"another song"
        assert (tmp_path / "a (1).mp3").read_bytes() == b"song"

    def test_should_keep_an_interrupted_download_out_of_the_finished_files(self, tmp_path, state):
        message = make_message(1, "a.mp3")

        with pytest.raises(ConnectionError):
            run(FakeClient([message], drop_connection_on=1), tmp_path, state)

        assert not (tmp_path / "a.mp3").exists()
        assert (tmp_path / "a.mp3.part").exists()
        assert not state.has(CHANNEL, 1)

    def test_should_finish_an_interrupted_download_on_the_next_run(self, tmp_path, state):
        message = make_message(1, "a.mp3")
        with pytest.raises(ConnectionError):
            run(FakeClient([message], drop_connection_on=1), tmp_path, state)

        count = run(FakeClient([message]), tmp_path, state)

        assert count == 1
        assert (tmp_path / "a.mp3").read_bytes() == b"song"
        assert not (tmp_path / "a.mp3.part").exists()
