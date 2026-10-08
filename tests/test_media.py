"""Tests for src/tg_music_dl/media.py."""
from types import SimpleNamespace

from tg_music_dl.media import AUDIO, VIDEO, VOICE, media_type

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
