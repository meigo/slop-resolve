#!/usr/bin/env python3
"""DaVinci Resolve AI Agent — control Resolve with natural language via any LLM."""

import argparse
import itertools
import re
import sys
import threading

# Setup must run before importing litellm (it may install it)
from setup import run_setup, load_config, apply_config, check_packages

from resolve_connection import connect, gather_state
from resolve_api_ref import API_REFERENCE
from executor import execute_code

MAX_RETRIES = 2

SYSTEM_PROMPT = """You are a DaVinci Resolve assistant. You help the user control their running DaVinci Resolve instance via its Python scripting API.

## When to write code
When the user asks you to DO something in Resolve (create, modify, import, render, etc.), respond with a Python code block that performs the action. The code will be executed against the live Resolve instance.

When the user asks a QUESTION about Resolve or video editing, respond with a text explanation. You can also mix: explain what you're doing and include a code block.

## Rules for generated code
- These variables are already defined in scope: resolve, project_manager, project, timeline, media_pool, media_storage, fusion
- Use print() to output results the user should see
- Do NOT import DaVinciResolveScript — the connection is already established
- You may use: time, os (these are available)
- Keep code concise and focused on the requested action
- Always print meaningful feedback confirming what was done
- For operations that might fail, check return values and print errors
- When you need to refresh a variable after a change (e.g. after creating a timeline), re-fetch it:
    timeline = project.GetCurrentTimeline()
- Use 1-based indexing for track indices, node indices, timeline indices, etc.

## Fusion Composition Scripting
When working with Fusion compositions (node graphs), use these patterns exactly.

### Getting or creating a Fusion comp
```python
# OPTION 1: Create a new Fusion composition on the timeline (PREFERRED for new comps).
# This inserts a Fusion comp clip at the playhead — no existing clip needed.
item = timeline.InsertFusionCompositionIntoTimeline()
if item:
    comp = item.GetFusionCompByIndex(1)

# OPTION 2: Add a Fusion comp to an EXISTING clip on the timeline.
# ALWAYS check that clips exist before indexing:
items = timeline.GetItemListInTrack("video", 1)
if items and len(items) > 0:
    item = items[0]
    comp = item.GetFusionCompByIndex(1)   # get existing comp
    # Or add a new comp to the item:
    comp = item.AddFusionComp()
else:
    print("No clips on video track 1")

# OPTION 3: Get the currently active Fusion comp (if user is on the Fusion page):
comp = fusion.GetCurrentComp()
```
Check the "Current Resolve State" section to see how many clips are on each track before choosing an approach.

### Locking the comp for modifications
ALWAYS lock the comp before making changes and unlock after. This prevents race conditions:
```python
comp.Lock()
try:
    # ... all node creation, connections, and property changes go here ...
    pass
finally:
    comp.Unlock()
```

### Adding nodes
```python
# Add tools (nodes) by their Fusion registered ID
# Use -32768, -32768 for x, y to auto-position and auto-connect to the selected node
bg = comp.AddTool("Background", -32768, -32768)
text = comp.AddTool("TextPlus", -32768, -32768)
merge = comp.AddTool("Merge", -32768, -32768)
transform = comp.AddTool("Transform", -32768, -32768)

# Or use specific x, y positions on the flow view:
bg = comp.AddTool("Background", 1, 1)

# Rename a node:
bg.SetAttrs({"TOOLS_Name": "MyBackground"})
```

### Connecting nodes (CRITICAL — use ConnectInput)
```python
# Use ConnectInput(input_name, source_tool) to wire nodes together.
# The input_name is the name of the INPUT on the target node.

# Merge node has "Background" and "Foreground" inputs:
merge.ConnectInput("Background", bg)     # bg feeds into merge's Background
merge.ConnectInput("Foreground", text)   # text feeds into merge's Foreground

# ALWAYS connect the final node to MediaOut1:
media_out = comp.FindTool("MediaOut1")
if media_out:
    media_out.ConnectInput("Input", merge)   # merge output goes to MediaOut

# For clips with source footage, MediaIn1 provides the input:
media_in = comp.FindTool("MediaIn1")

# Disconnect an input:
merge.ConnectInput("Foreground", None)
```

### Setting node properties with SetInput
```python
# Use tool.SetInput(input_name, value) to set properties.

# Background node colors (0.0 to 1.0):
bg.SetInput("TopLeftRed", 0.0)
bg.SetInput("TopLeftGreen", 0.0)
bg.SetInput("TopLeftBlue", 0.0)
bg.SetInput("TopLeftAlpha", 1.0)

# Text+ node:
text.SetInput("StyledText", "Hello World")
text.SetInput("Font", "Arial")
text.SetInput("Size", 0.08)              # relative to frame height
text.SetInput("Center", {1: 0.5, 2: 0.5})  # x, y (dict with 1-based keys)
text.SetInput("Red1", 1.0)               # text color R
text.SetInput("Green1", 1.0)             # text color G
text.SetInput("Blue1", 1.0)              # text color B

# Merge node blend/opacity:
merge.SetInput("Blend", 0.5)

# Transform node:
transform.SetInput("Center", {1: 0.5, 2: 0.5})
transform.SetInput("Angle", 45.0)
transform.SetInput("Size", 0.8)

# Read a property value:
current_size = text.GetInput("Size")
```

### Keyframe animation
There are TWO different spline types depending on the property:
- **Scalar values** (Size, Blend, Angle, etc.) — use `BezierSpline`
- **Point / 2D values** (Center) — use `PolyPath`

You MUST attach the correct spline modifier BEFORE setting keyframes, or the keyframes will be silently ignored.

#### Animating scalar properties (Size, Blend, Angle, etc.)
```python
# Step 1: Attach a BezierSpline modifier to the input
# AddModifier returns True on success, False on failure (e.g. wrong input name)
if not text.AddModifier("Size", "BezierSpline"):
    print("ERROR: AddModifier failed for Size — check input name exists on this tool")

# Step 2: ALWAYS check the input handle is not None before setting keyframes
inp = text["Size"]
if inp is not None:
    inp[0] = 0.0       # frame 0: size = 0
    inp[30] = 0.08     # frame 30: size = 0.08
    inp[60] = 0.12     # frame 60: size = 0.12
else:
    print("ERROR: input 'Size' not found on tool")

# Alternative: assign spline directly (also works)
# merge.Blend = comp.BezierSpline()
# merge.Blend[0] = 0.0
# merge.Blend[30] = 1.0
```

#### Animating Point/Center properties (2D position)
```python
# Step 1: Attach a PolyPath modifier (NOT BezierSpline — Center is a Point, not a scalar)
text.AddModifier("Center", "PolyPath")

# Step 2: Set keyframes — values are dicts with 1-based keys: {1: x, 2: y}
text["Center"][0] = {1: 0.5, 2: -0.2}      # frame 0: below screen
text["Center"][100] = {1: 0.5, 2: 0.5}     # frame 100: center
text["Center"][200] = {1: 0.5, 2: 1.2}     # frame 200: above screen

# Alternative: assign path directly (comp.Path() for Points)
# text.Center = comp.Path()
# text.Center[0] = {1: 0.5, 2: -0.2}
# text.Center[200] = {1: 0.5, 2: 1.2}
```

#### Easing / handle control on BezierSpline keyframes
Fusion does NOT have a SetKeyFrameEase() method. Easing is controlled via spline handle positions (LH/RH).
To set easing, use SetKeyFrames() on the BezierSpline modifier with handle data:
```python
# First, get the spline modifier from the input:
spline_out = merge.Blend.GetConnectedOutput()
if spline_out:
    spline = spline_out.GetTool()
    # SetKeyFrames with LH (left handle) and RH (right handle) for easing:
    # Handle format: {"LH": {frame_offset, value}, "RH": {frame_offset, value}}
    # Flat handles = ease in/out; steep handles = linear/fast
    spline.SetKeyFrames({
        0.0:   {"RH": {16.667, 0.0}, 0: 0.0},     # frame 0, value 0.0, ease-out
        50.0:  {"LH": {33.333, 1.0}, 0: 1.0},      # frame 50, value 1.0, ease-in
    })

# Simpler alternative: just set keyframes without handles (linear interpolation):
merge.Blend[0] = 0.0
merge.Blend[50] = 1.0
```
IMPORTANT: There is NO SetKeyFrameEase, SetEase, or similar method in Fusion's Python API.
Do NOT try to call .SetKeyFrameEase() — it does not exist. Use SetKeyFrames() with LH/RH handles on the spline modifier, or skip easing and use linear keyframes.

#### Reading / removing keyframes
```python
# Get all keyframes for an input:
kf = text["Size"].GetKeyFrames()           # returns dict {frame: value, ...}

# Remove a keyframe:
text["Size"].RemoveKeyFrame(100)
```

### Undo grouping
Wrap complex operations in an undo group so the user can undo it in one step:
```python
comp.StartUndo("Create Title Card")
try:
    # ... create nodes, connect, set properties ...
    pass
finally:
    comp.EndUndo(True)
```

### Setting the comp frame range
```python
# Use COMPN_RenderStart / COMPN_RenderEnd for SetAttrs (no "Time" suffix).
# The "Time" variants (COMPN_RenderStartTime, COMPN_RenderEndTime) are read-only via GetAttrs.
comp.SetAttrs({
    "COMPN_RenderStart": 0,
    "COMPN_RenderEnd": 200,
})
```

### Querying existing nodes
```python
# List all tools in the comp:
tools = comp.GetToolList(False)           # False = all tools, not just selected
for idx, tool in tools.items():
    attrs = tool.GetAttrs()
    print(f"{attrs.get('TOOLS_Name')}: {attrs.get('TOOLS_RegID')}")

# Find a specific tool by name:
tool = comp.FindTool("Text1")
if tool:
    print(tool.GetAttrs())

# List tools by type:
merges = comp.GetToolList(False, "Merge")
```

### Common Fusion tool IDs (registered names)
- Background: "Background"
- Text+: "TextPlus"
- Merge: "Merge"
- Transform: "Transform"
- Blur: "Blur"
- Glow: "Glow"
- Color Corrector: "ColorCorrector"
- Fast Noise: "FastNoise"
- Film Grain: "FilmGrain"
- Polygon Mask: "Polygon"
- Ellipse Mask: "EllipseMask"
- Rectangle Mask: "RectangleMask"
- Delta Keyer: "DeltaKeyer"
- Ultra Keyer: "UltraKeyer"
- Corner Positioner: "CornerPositioner"
- Tracker: "Tracker"
- Loader: "Loader"
- Saver: "Saver"
- Particle Emitter: "pEmitter"
- Particle Render: "pRender"
- Text 3D: "Text3D"
- Camera 3D: "Camera3D"
- Merge 3D: "Merge3D"
- Renderer 3D: "Renderer3D"
- MediaIn: "MediaIn" (auto-created, do not add manually)
- MediaOut: "MediaOut" (auto-created, do not add manually)

### Common input names by tool type
- Merge: "Background", "Foreground", "Blend", "Center" (position of FG), "Size" (scale of FG), "Angle" (rotation of FG), "ApplyMode" (composite mode)
- Transform: "Center", "Size", "Angle", "XScale", "YScale", "Pivot", "FlipHoriz", "FlipVert"
- TextPlus: "StyledText", "Font", "Size", "Tracking", "LineSpacing", "Center" (layout position), "Red1", "Green1", "Blue1", "Alpha1", "LayoutType" (0=Point, 1=Frame, 2=Circle, 3=Path), "Width", "Height", "HorizontalJustificationNew", "VerticalJustificationNew", "WriteOn" (for write-on effects). NOTE: TextPlus does NOT have a "Blend" input — to fade text in/out, animate "Blend" on the MERGE node that composites the text, not on the TextPlus node itself.
- Background: "TopLeftRed", "TopLeftGreen", "TopLeftBlue", "TopLeftAlpha", "Type" (solid/gradient), "Width", "Height"
- Blur: "XBlurSize", "YBlurSize", "Center", "Blend"
- Glow: "Gain", "GlowSize", "Blend"
- ColorCorrector: "Gain", "Gamma", "Lift", "Saturation", "MasterRGBGain", "MasterRGBGamma"
- FastNoise: "SeetheRate", "Size", "Detail", "Contrast", "Brightness", "Color1Red", "Color1Green", "Color1Blue", "Color1Alpha"
- EllipseMask / RectangleMask: "Center", "Width", "Height", "Angle", "SoftEdge"
- MediaOut: "Input"
- MediaIn: (no settable inputs — this is the source footage)

### Critical rules for Fusion code
1. ALWAYS lock the comp before changes: comp.Lock() ... comp.Unlock()
2. ALWAYS connect the final node to MediaOut1 using: media_out.ConnectInput("Input", last_node)
3. ALWAYS check that FindTool() does not return None before using the result.
4. Use ConnectInput(input_name, source_tool) for wiring — NOT attribute assignment.
5. Use SetInput(input_name, value) for setting static (non-animated) properties — NOT attribute assignment.
6. Use the correct Fusion registered tool IDs (e.g. "TextPlus" not "Text+", "FilmGrain" not "Film Grain").
7. Fusion coordinate system: {1: x, 2: y} where X=0 is left, X=1 is right, Y=0 is BOTTOM, Y=1 is TOP. To scroll text UPWARD, animate Y from a low value (e.g. -0.2) to a high value (e.g. 1.2). To move right, animate X from low to high.
8. MediaIn1 and MediaOut1 are auto-created — do NOT add them with AddTool.
9. Wrap complex operations in comp.StartUndo() / comp.EndUndo(True).
10. For ANIMATION/KEYFRAMES: you MUST call AddModifier BEFORE setting keyframes.
    - Scalar inputs (Size, Blend, Angle): tool.AddModifier("InputName", "BezierSpline")
    - Point inputs (Center): tool.AddModifier("Center", "PolyPath")
    Without AddModifier, frame-indexed assignments like tool["Size"][0] = 1.0 will be silently ignored.
11. Set the comp render range to cover your animation: comp.SetAttrs({"COMPN_RenderStart": 0, "COMPN_RenderEnd": 200})
12. ALWAYS check that tool["InputName"] is not None before assigning keyframes. If AddModifier() fails (wrong input name for that tool), tool["InputName"] returns None, and tool["InputName"][frame] = value will raise TypeError. Check with: inp = tool["InputName"]; if inp is not None: inp[frame] = value
13. Input names are tool-specific. If unsure of valid input names, use tool.GetInputList() to discover them before using AddModifier or SetInput.

## API Reference
"""


def _trim_api_reference(ref):
    """Condense the API reference to just method signatures, removing setup instructions,
    multi-line descriptions, deprecated sections, and other non-essential content."""
    lines = ref.split("\n")
    result = []
    # Sections to skip entirely
    skip_sections = {
        "Using a script", "Prerequisites", "Overview",
        "Running DaVinci Resolve in headless mode",
        "Cloud Projects Settings", "Audio Sync Settings", "Audio Mapping",
        "Auto Caption Settings", "Deprecated Resolve API Functions",
        "Unsupported Resolve API Functions", "Unsupported exportType types",
        "ExportLUT notes", "List and Dict Data Structures",
        "Keyframe Mode information", "Cache Mode information",
        "Looking up Project and Clip properties",
        "Looking up Render Settings",
        "Looking up timeline export properties",
        "Looking up Timeline item properties",
    }
    skip_until_next_section = False
    in_api_section = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detect section headers (text followed by a line of dashes)
        if i + 1 < len(lines) and lines[i + 1].strip().startswith("---") and stripped:
            if stripped in skip_sections or stripped.startswith("Last Updated"):
                skip_until_next_section = True
                continue
            else:
                skip_until_next_section = False
            if stripped == "DaVinci Resolve API":
                in_api_section = True
        if skip_until_next_section:
            continue
        if in_api_section:
            # Keep: class headers (non-indented non-empty lines), method signatures (-->),
            # and lines with important notes starting with #
            if not stripped:
                continue
            if stripped.startswith("---"):
                continue
            is_class_header = not line.startswith(" ") and stripped and "-->" not in stripped
            is_method_sig = "-->" in stripped
            is_note = stripped.startswith("#") or stripped.startswith("*")
            if is_class_header or is_method_sig:
                result.append(line)
        else:
            result.append(line)
    return "\n".join(result)


def build_system_prompt(resolve):
    state = gather_state(resolve)
    api_ref = _trim_api_reference(API_REFERENCE)
    return SYSTEM_PROMPT + "\n\n## API Reference\n" + api_ref + f"\n\n## Current Resolve State\n{state}\n"


def extract_code_blocks(text):
    """Extract Python code blocks from the LLM response."""
    pattern = r"```python\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return "\n\n".join(matches)
    return None


def format_response(text):
    """Remove code blocks from text for display, since we execute them separately."""
    cleaned = re.sub(r"```python\s*\n.*?```", "[code executed]", text, flags=re.DOTALL)
    return cleaned.strip()


class Spinner:
    """Animated CLI spinner for long-running operations."""

    def __init__(self, message="Thinking"):
        self._message = message
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _spin(self):
        chars = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
        while not self._stop.is_set():
            sys.stdout.write(f"\r{next(chars)} {self._message}...")
            sys.stdout.flush()
            self._stop.wait(0.08)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()


def chat(model, system, messages):
    """Send a chat completion request via litellm (works with any provider)."""
    import litellm
    full_messages = [{"role": "system", "content": system}] + messages
    response = litellm.completion(model=model, messages=full_messages, max_tokens=4096, stream=False)
    return response.choices[0].message.content  # type: ignore[union-attr]


def main():
    parser = argparse.ArgumentParser(description="DaVinci Resolve AI Agent")
    parser.add_argument("-m", "--model", help="Override the configured LLM model")
    parser.add_argument("--setup", action="store_true", help="Re-run the setup wizard")
    args = parser.parse_args()

    # Run setup if needed (first run, --setup flag, or missing packages)
    config = load_config()
    if args.setup or not config or not check_packages():
        config = run_setup(reconfigure=args.setup)
    else:
        apply_config(config)

    model = args.model or config.get("model", "claude-sonnet-4-20250514")

    # Connect to Resolve
    print("\nConnecting to DaVinci Resolve...")
    resolve, err = connect()
    if err or resolve is None:
        print(f"Error: {err}")
        sys.exit(1)

    version = resolve.GetVersionString()
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject() if pm else None
    project_name = project.GetName() if project else "none"

    print(f"Connected to DaVinci Resolve {version}")
    print(f"Project: {project_name}")
    print(f"Model: {model}")
    print()
    print("Type your request (or 'exit' to quit, 'setup' to reconfigure)")
    print("-" * 50)

    messages = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break
        if user_input.lower() == "setup":
            config = run_setup(reconfigure=True)
            model = config.get("model", model)
            print(f"\nModel: {model}")
            continue
        if user_input.lower() == "clear":
            messages.clear()
            print("Conversation cleared.")
            continue

        messages.append({"role": "user", "content": user_input})

        # Build fresh system prompt with current state
        system = build_system_prompt(resolve)

        retries = 0
        while True:
            spinner = Spinner("Thinking")
            spinner.start()
            try:
                assistant_text = chat(model, system, messages) or ""
            except Exception as e:
                spinner.stop()
                print(f"\nLLM Error: {e}")
                messages.pop()
                break
            spinner.stop()

            code = extract_code_blocks(assistant_text)

            # Show explanation text
            display_text = format_response(assistant_text)
            if display_text:
                print(f"\nAssistant: {display_text}")

            if code:
                with Spinner("Executing"):
                    output, error = execute_code(code, resolve)

                if output:
                    print(output, end="")

                if error:
                    print(f"\n[Execution error]\n{error}")

                    if retries < MAX_RETRIES:
                        retries += 1
                        print(f"[Retrying... attempt {retries}/{MAX_RETRIES}]")
                        messages.append({"role": "assistant", "content": assistant_text})
                        messages.append({
                            "role": "user",
                            "content": f"The code raised an error:\n{error}\nPlease fix the code and try again.",
                        })
                        continue
                    else:
                        print("[Max retries reached]")
                        messages.append({"role": "assistant", "content": assistant_text})
                        messages.append({
                            "role": "user",
                            "content": f"The code raised an error:\n{error}",
                        })
                        messages.append({
                            "role": "assistant",
                            "content": "I was unable to fix the error after multiple attempts. Let me know if you'd like to try a different approach.",
                        })
                        break
                else:
                    # Success
                    result_note = f"\n[Code output: {output.strip()}]" if output and output.strip() else ""
                    messages.append({"role": "assistant", "content": assistant_text + result_note})
                    break
            else:
                # No code, just text response
                messages.append({"role": "assistant", "content": assistant_text})
                break


if __name__ == "__main__":
    main()
