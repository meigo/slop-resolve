import sys
import os


def connect():
    """Connect to running DaVinci Resolve instance. Returns (resolve, error_message)."""
    # Add Resolve scripting modules to path
    modules_path = os.path.join(
        os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
        "Blackmagic Design",
        "DaVinci Resolve",
        "Support",
        "Developer",
        "Scripting",
        "Modules",
    )
    if modules_path not in sys.path:
        sys.path.append(modules_path)

    # Set environment variables if not already set
    script_api = os.path.join(
        os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
        "Blackmagic Design",
        "DaVinci Resolve",
        "Support",
        "Developer",
        "Scripting",
    )
    fusion_lib = os.path.join(
        os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        "Blackmagic Design",
        "DaVinci Resolve",
        "fusionscript.dll",
    )
    os.environ.setdefault("RESOLVE_SCRIPT_API", script_api)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", fusion_lib)

    try:
        import DaVinciResolveScript as dvr  # type: ignore[import-not-found]
    except ImportError:
        return None, (
            f"Could not import DaVinciResolveScript.\n"
            f"Checked modules path: {modules_path}\n"
            f"Make sure DaVinci Resolve is installed."
        )
    except SystemError:
        return None, (
            f"fusionscript.dll failed to initialize.\n"
            f"Common causes:\n"
            f"  1. DaVinci Resolve is not running — start it first\n"
            f"  2. Python version not supported — Resolve requires Python 3.6-3.10 (you have {sys.version.split()[0]})\n"
            f"     Try running with: python resolve_agent.py (not python3)"
        )

    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        return None, "Could not connect to DaVinci Resolve. Is it running?"

    return resolve, None


def gather_state(resolve):
    """Gather current Resolve state as a string for context."""
    parts = []

    try:
        parts.append(f"Resolve version: {resolve.GetVersionString()}")
    except Exception:
        parts.append("Resolve version: unknown")

    try:
        parts.append(f"Current page: {resolve.GetCurrentPage()}")
    except Exception:
        pass

    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject() if pm else None

    if project:
        parts.append(f"Project: \"{project.GetName()}\"")

        timeline = project.GetCurrentTimeline()
        if timeline:
            parts.append(f"Timeline: \"{timeline.GetName()}\"")
            try:
                fps = timeline.GetSetting("timelineFrameRate")
                parts.append(f"  Frame rate: {fps}")
            except Exception:
                pass
            try:
                start = timeline.GetStartFrame()
                end = timeline.GetEndFrame()
                parts.append(f"  Frame range: {start} - {end}")
            except Exception:
                pass
            try:
                tc = timeline.GetCurrentTimecode()
                parts.append(f"  Current timecode: {tc}")
            except Exception:
                pass
            try:
                v_tracks = timeline.GetTrackCount("video")
                a_tracks = timeline.GetTrackCount("audio")
                s_tracks = timeline.GetTrackCount("subtitle")
                parts.append(f"  Tracks: {v_tracks} video, {a_tracks} audio, {s_tracks} subtitle")
                for ti in range(1, v_tracks + 1):
                    items = timeline.GetItemListInTrack("video", ti)
                    count = len(items) if items else 0
                    parts.append(f"  Video track {ti}: {count} clip(s)")
            except Exception:
                pass
        else:
            parts.append("Timeline: none")

        media_pool = project.GetMediaPool()
        if media_pool:
            try:
                root = media_pool.GetRootFolder()
                clips = root.GetClipList()
                parts.append(f"Media pool root: {len(clips) if clips else 0} clips")
            except Exception:
                parts.append("Media pool: available")

        try:
            render_jobs = project.GetRenderJobList()
            if render_jobs:
                parts.append(f"Render queue: {len(render_jobs)} jobs")
                if project.IsRenderingInProgress():
                    parts.append("  Rendering in progress")
            else:
                parts.append("Render queue: empty")
        except Exception:
            pass
    else:
        parts.append("Project: none loaded")

    return "\n".join(parts)
