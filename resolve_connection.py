import sys
import os
import platform


def _get_resolve_paths():
    """Return (modules_path, script_api, fusion_lib) for the current platform."""
    system = platform.system()

    if system == "Darwin":
        modules_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
        script_api = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
        fusion_lib = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
    elif system == "Linux":
        modules_path = "/opt/resolve/Developer/Scripting/Modules"
        script_api = "/opt/resolve/Developer/Scripting"
        fusion_lib = "/opt/resolve/libs/Fusion/fusionscript.so"
    else:
        # Windows
        programdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        programfiles = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        modules_path = os.path.join(programdata, "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting", "Modules")
        script_api = os.path.join(programdata, "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting")
        fusion_lib = os.path.join(programfiles, "Blackmagic Design", "DaVinci Resolve", "fusionscript.dll")

    return modules_path, script_api, fusion_lib


def connect():
    """Connect to running DaVinci Resolve instance. Returns (resolve, error_message)."""
    modules_path, script_api, fusion_lib = _get_resolve_paths()

    # Add Resolve scripting modules to path
    if modules_path not in sys.path:
        sys.path.append(modules_path)

    # Set environment variables if not already set
    os.environ.setdefault("RESOLVE_SCRIPT_API", script_api)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", fusion_lib)

    try:
        import DaVinciResolveScript as dvr  # type: ignore[import-not-found]
    except ImportError:
        return None, (
            f"Could not import DaVinciResolveScript.\n"
            f"Platform: {platform.system()}\n"
            f"Checked modules path: {modules_path}\n"
            f"Make sure DaVinci Resolve is installed."
        )
    except SystemError:
        lib_name = "fusionscript.so" if platform.system() != "Windows" else "fusionscript.dll"
        return None, (
            f"{lib_name} failed to initialize.\n"
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
                    if items:
                        last_item = items[-1]
                        fusion_comps = last_item.GetFusionCompCount() if hasattr(last_item, "GetFusionCompCount") else 0
                        if fusion_comps and fusion_comps > 0:
                            parts.append(f"    Last clip has {fusion_comps} Fusion comp(s) — use GetFusionCompByIndex(1) to modify")
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
