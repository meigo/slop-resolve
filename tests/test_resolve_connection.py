"""Tests for resolve_connection.py — state gathering."""
from resolve_connection import gather_state


class TestGatherStateFullProject:
    """Test state gathering with a full project setup."""

    def test_contains_version(self, mock_resolve):
        state = gather_state(mock_resolve)
        assert "19.1.2" in state

    def test_contains_page(self, mock_resolve):
        state = gather_state(mock_resolve)
        assert "edit" in state

    def test_contains_project_name(self, mock_resolve):
        state = gather_state(mock_resolve)
        assert "Test Project" in state

    def test_contains_timeline_name(self, mock_resolve):
        state = gather_state(mock_resolve)
        assert "Main Timeline" in state

    def test_contains_frame_range(self, mock_resolve):
        state = gather_state(mock_resolve)
        assert "0" in state and "1000" in state

    def test_contains_timecode(self, mock_resolve):
        state = gather_state(mock_resolve)
        assert "00:00:00:00" in state

    def test_contains_track_counts(self, mock_resolve):
        state = gather_state(mock_resolve)
        assert "2 video" in state
        assert "3 audio" in state

    def test_contains_media_pool_count(self, mock_resolve):
        state = gather_state(mock_resolve)
        assert "3 clips" in state

    def test_contains_render_queue(self, mock_resolve):
        state = gather_state(mock_resolve)
        assert "Render queue: empty" in state


class TestGatherStateNoProject:
    """Test state gathering when no project is loaded."""

    def test_no_project(self, mock_resolve_no_project):
        state = gather_state(mock_resolve_no_project)
        assert "none loaded" in state

    def test_still_has_version(self, mock_resolve_no_project):
        state = gather_state(mock_resolve_no_project)
        assert "19.1.2" in state


class TestGatherStateNoTimeline:
    """Test state gathering when project has no timeline."""

    def test_no_timeline(self, mock_resolve_no_timeline):
        state = gather_state(mock_resolve_no_timeline)
        assert "Timeline: none" in state

    def test_still_has_project(self, mock_resolve_no_timeline):
        state = gather_state(mock_resolve_no_timeline)
        assert "Test Project" in state


class TestGatherStateRenderInProgress:
    """Test state gathering during rendering."""

    def test_render_in_progress(self, mock_resolve):
        project = mock_resolve.GetProjectManager().GetCurrentProject()
        project.GetRenderJobList.return_value = [{"id": "job1"}]
        project.IsRenderingInProgress.return_value = True
        state = gather_state(mock_resolve)
        assert "1 jobs" in state
        assert "Rendering in progress" in state


class TestGatherStateExceptionHandling:
    """Test that gather_state handles exceptions gracefully."""

    def test_version_exception(self, mock_resolve):
        mock_resolve.GetVersionString.side_effect = Exception("fail")
        state = gather_state(mock_resolve)
        assert "unknown" in state

    def test_timeline_setting_exception(self, mock_resolve):
        timeline = mock_resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
        timeline.GetSetting.side_effect = Exception("fail")
        # Should not crash, just skip the frame rate
        state = gather_state(mock_resolve)
        assert "Main Timeline" in state
