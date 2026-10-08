"""Tests for src/tg_music_dl/media.py."""
from types import SimpleNamespace

import pytest

from tg_music_dl.media import AUDIO, VIDEO, VOICE, file_name, media_type

DOCUMENT = object()


def make_message(**media):
    """Builds a stand-in Telethon message carrying only the given media properties."""
    fields = {"audio": None, "voice": None, "video": None, "video_note": None, "gif": None,
              "document": None}
    fields.update(media)
    return SimpleNamespace(**fields)


class TestMediaType:
    def test_should_detect_music_sent_as_audio(self):
        message = make_message(audio=DOCUMENT, document=DOCUMENT)

        assert media_type(message) == AUDIO

    def test_should_detect_music_sent_as_a_plain_audio_document(self):
        message = make_message(document=SimpleNamespace(mime_type="audio/mpeg"))

        assert media_type(message) == AUDIO

    def test_should_detect_a_voice_note_even_though_its_document_is_audio(self):
        message = make_message(voice=DOCUMENT, document=SimpleNamespace(mime_type="audio/ogg"))

        assert media_type(message) == VOICE

    def test_should_detect_a_video(self):
        message = make_message(video=DOCUMENT, document=SimpleNamespace(mime_type="video/mp4"))

        assert media_type(message) == VIDEO

    def test_should_ignore_round_video_notes_and_gifs(self):
        round_note = make_message(video=DOCUMENT, video_note=DOCUMENT, document=DOCUMENT)
        gif = make_message(video=DOCUMENT, gif=DOCUMENT, document=DOCUMENT)

        assert media_type(round_note) is None
        assert media_type(gif) is None

    def test_should_ignore_other_documents_and_plain_messages(self):
        pdf = make_message(document=SimpleNamespace(mime_type="application/pdf"))

        assert media_type(pdf) is None
        assert media_type(make_message()) is None


def make_file_message(name, ext=".mp3", message_id=42):
    """Builds a stand-in message whose media has the given file name and extension."""
    return SimpleNamespace(id=message_id, file=SimpleNamespace(name=name, ext=ext))


class TestFileName:
    def test_should_use_the_name_the_sender_gave(self):
        assert file_name(make_file_message("01 Artist - Song.mp3")) == "01 Artist - Song.mp3"

    @pytest.mark.parametrize("crafted", ["../../escape.mp3", "/etc/escape.mp3", "..\\escape.mp3"])
    def test_should_keep_only_the_last_part_of_a_path(self, crafted):
        assert file_name(make_file_message(crafted)) == "escape.mp3"

    @pytest.mark.parametrize("unusable", [None, "", "  ", "..", "folder/"])
    def test_should_fall_back_to_the_message_id_and_extension(self, unusable):
        assert file_name(make_file_message(unusable)) == "42.mp3"

    def test_should_fall_back_to_the_bare_message_id_without_an_extension(self):
        assert file_name(make_file_message(None, ext=None)) == "42"
