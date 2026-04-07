import builtins
import io
import sys
import time
import os
import os.path
import traceback


def execute_code(code, resolve):
    """
    Execute LLM-generated Python code against the live Resolve instance.
    Returns (stdout_output, error_or_none).
    """
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject() if pm else None
    timeline = project.GetCurrentTimeline() if project else None
    media_pool = project.GetMediaPool() if project else None
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
