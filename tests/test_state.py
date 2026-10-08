"""Tests for src/tg_music_dl/state.py."""
from tg_music_dl.state import DownloadState


class TestDownloadState:
    def test_should_start_empty_without_a_state_file(self, tmp_path):
        state = DownloadState(tmp_path / "state.json")

        assert not state.has("channel", 1)

    def test_should_remember_downloads_across_runs(self, tmp_path):
        path = tmp_path / "state.json"
        DownloadState(path).add("channel", 7)

        reloaded = DownloadState(path)

        assert reloaded.has("channel", 7)
        assert not reloaded.has("channel", 8)

    def test_should_keep_channels_apart(self, tmp_path):
        state = DownloadState(tmp_path / "state.json")
        state.add("first", 1)

        assert not state.has("second", 1)

    def test_should_leave_no_temporary_file_after_saving(self, tmp_path):
        DownloadState(tmp_path / "state.json").add("channel", 1)

        assert sorted(path.name for path in tmp_path.iterdir()) == ["state.json"]

    def test_should_start_over_with_a_warning_when_the_file_is_unreadable(self, tmp_path, capsys):
        path = tmp_path / "state.json"
        path.write_text("{not json")

        state = DownloadState(path)
        state.add("channel", 1)

        assert "ignoring unreadable" in capsys.readouterr().err
        assert DownloadState(path).has("channel", 1)
