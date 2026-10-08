"""Remembers which messages were downloaded, so each run resumes where the last one stopped."""
import json
import os
import sys

# Kept inside the output folder, so the record travels with the files it describes.
STATE_FILE_NAME = ".tg-music-dl.json"


class DownloadState:
    """Per-channel sets of downloaded message IDs, saved as JSON after every change."""

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as state_file:
                data = json.load(state_file)
            return {channel: set(ids) for channel, ids in data["downloaded"].items()}
        except FileNotFoundError:
            return {}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            # Losing the record only costs re-checking files already on disk,
            # which are recognized and skipped, so carry on instead of failing.
            print(f"warning: ignoring unreadable {self.path}", file=sys.stderr)
            return {}

    def __init__(self, path):
        self.path = path
        self.downloaded = self._load()

    def has(self, channel_key, message_id):
        return message_id in self.downloaded.get(channel_key, set())

    def _save(self):
        data = {"downloaded": {channel: sorted(ids) for channel, ids in self.downloaded.items()}}
        temporary_path = f"{self.path}.tmp"
        with open(temporary_path, "w", encoding="utf-8") as state_file:
            json.dump(data, state_file)
        # Replaces the old file in one step, so a crash mid-write never leaves half a record.
        os.replace(temporary_path, self.path)

    def add(self, channel_key, message_id):
        """Records a finished download and saves at once, so an interrupted run keeps its progress."""
        self.downloaded.setdefault(channel_key, set()).add(message_id)
        self._save()
