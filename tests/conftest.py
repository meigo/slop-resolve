"""Shared test fixtures — mock Resolve objects."""
import pytest
from unittest.mock import MagicMock


def make_mock_resolve():
    """Create a fully mocked DaVinci Resolve object hierarchy."""
    resolve = MagicMock()
    resolve.GetVersionString.return_value = "19.1.2"
    resolve.GetCurrentPage.return_value = "edit"
    resolve.GetProductName.return_value = "DaVinci Resolve"

    # Project Manager
    pm = MagicMock()
    resolve.GetProjectManager.return_value = pm

    # Project
    project = MagicMock()
    pm.GetCurrentProject.return_value = project
    project.GetName.return_value = "Test Project"
    project.GetTimelineCount.return_value = 1
    project.IsRenderingInProgress.return_value = False
    project.GetRenderJobList.return_value = []

    # Timeline
    timeline = MagicMock()
    project.GetCurrentTimeline.return_value = timeline
    timeline.GetName.return_value = "Main Timeline"
    timeline.GetSetting.return_value = "24"
    timeline.GetStartFrame.return_value = 0
    timeline.GetEndFrame.return_value = 1000
    timeline.GetCurrentTimecode.return_value = "00:00:00:00"
    timeline.GetTrackCount.side_effect = lambda t: {"video": 2, "audio": 3, "subtitle": 0}[t]

    # Media Pool
    media_pool = MagicMock()
    project.GetMediaPool.return_value = media_pool
    root_folder = MagicMock()
    media_pool.GetRootFolder.return_value = root_folder
    root_folder.GetClipList.return_value = [MagicMock(), MagicMock(), MagicMock()]

    # Media Storage
    media_storage = MagicMock()
    resolve.GetMediaStorage.return_value = media_storage

    # Fusion
    fusion = MagicMock()
    resolve.Fusion.return_value = fusion

    return resolve


@pytest.fixture
def mock_resolve():
    return make_mock_resolve()


@pytest.fixture
def mock_resolve_no_project():
    resolve = MagicMock()
    resolve.GetVersionString.return_value = "19.1.2"
    resolve.GetCurrentPage.return_value = "media"
    pm = MagicMock()
    resolve.GetProjectManager.return_value = pm
    pm.GetCurrentProject.return_value = None
    resolve.GetMediaStorage.return_value = MagicMock()
    resolve.Fusion.return_value = MagicMock()
    return resolve


@pytest.fixture
def mock_resolve_no_timeline():
    resolve = make_mock_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    project.GetCurrentTimeline.return_value = None
    project.GetMediaPool().CreateEmptyTimeline.return_value = None
    return resolve
