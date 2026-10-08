"""Decides which kind of downloadable media a message carries and what to name its file."""
import os

AUDIO = "audio"
VOICE = "voice"
VIDEO = "video"
MEDIA_TYPES = (AUDIO, VOICE, VIDEO)
AUDIO_MIME_PREFIX = "audio/"


def media_type(message):
    """Returns which of MEDIA_TYPES the message carries, or None.

    Music normally arrives with Telegram's audio attribute, but some channels
    post it as a plain document, so any other audio/* document counts as audio
    too. Voice notes are checked first because their document is audio/ogg.
    Round video notes and GIFs are not videos here.
    """
    if message.voice:
        return VOICE
    if message.audio:
        return AUDIO
    document = message.document
    if document is not None and (getattr(document, "mime_type", None) or "").startswith(AUDIO_MIME_PREFIX):
        return AUDIO
    if message.video and not message.video_note and not message.gif:
        return VIDEO
    return None


def file_name(message):
    """Returns a safe file name for the message's media.

    Uses the name the sender gave the file, cut down to its last path part so a
    crafted name cannot write outside the output folder, and falls back to the
    message ID plus the media's extension.
    """
    name = os.path.basename((message.file.name or "").replace("\\", "/")).strip()
    if name in ("", ".", ".."):
        name = f"{message.id}{message.file.ext or ''}"
    return name
