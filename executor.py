import builtins
import io
import sys
import time
import os
import os.path
import traceback
import urllib.request
import tempfile
import shutil


def execute_code(code, resolve):
    """
    Execute LLM-generated Python code against the live Resolve instance.
    Returns (stdout_output, error_or_none).
    """
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject() if pm else None
    media_pool = project.GetMediaPool() if project else None
    timeline = project.GetCurrentTimeline() if project else None

    # Auto-create a timeline if none exists
    if timeline is None and media_pool is not None:
        timeline = media_pool.CreateEmptyTimeline("Timeline 1")
        if timeline is not None:
            project.SetCurrentTimeline(timeline)  # type: ignore[union-attr]
    media_storage = resolve.GetMediaStorage()
    fusion = resolve.Fusion()

    exec_globals = {
        "__builtins__": builtins,
        # Resolve objects
        "resolve": resolve,
        "project_manager": pm,
        "project": project,
        "timeline": timeline,
        "media_pool": media_pool,
        "media_storage": media_storage,
        "fusion": fusion,
        # Useful modules
        "time": time,
        "os": os,
        "urllib": urllib,
        "tempfile": tempfile,
        "shutil": shutil,
    }

    # Capture stdout
    old_stdout = sys.stdout
    captured = io.StringIO()
    sys.stdout = captured

    error = None
    try:
        exec(code, exec_globals)
    except Exception:
        error = traceback.format_exc()
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    return output, error
