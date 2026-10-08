"""Decides which kind of downloadable media a message carries."""

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
