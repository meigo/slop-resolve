#!/usr/bin/env python3
"""DaVinci Resolve AI Agent — control Resolve with natural language via any LLM."""

import argparse
import itertools
import re
import sys
import threading

# Setup must run before importing litellm (it may install it)
from setup import run_setup, load_config, save_config, apply_config, check_packages

from resolve_connection import connect, gather_state
from resolve_api_ref import API_REFERENCE
from executor import execute_code

MAX_RETRIES = 2

SYSTEM_PROMPT = """You are a DaVinci Resolve creative assistant. You translate the user's creative intent into working Resolve Python scripts. The user describes WHAT they want — you decide HOW to build it.

## Your role
You are an expert video editor and motion graphics artist who also writes code. When a user says "make a countdown", you choose the right nodes, animations, colors, and timing. When they say "add a title card", you pick fonts, sizes, positioning, and transitions that look professional. You make creative decisions — don't ask the user which nodes to use.

## When to write code
When the user asks you to DO something in Resolve (create, modify, import, render, etc.), respond with a brief explanation of your creative approach, then a Python code block. The code will be executed against the live Resolve instance.

When the user asks a QUESTION about Resolve or video editing, respond with a text explanation.

## Creative guidelines
- Make things look good by default — use smooth animations, sensible timing, and clean compositions
- Interpret vague requests generously: "make it pop" = add glow/contrast, "animate it" = add keyframed motion, "title card" = styled text with background and fade
- When the user doesn't specify details, choose professional defaults (clean fonts, subtle animations, balanced colors)
- Explain your creative choices briefly so the user can request adjustments

## Rules for generated code
- These variables are already defined in scope: resolve, project_manager, project, timeline, media_pool, media_storage, fusion
- Use print() to output results the user should see
- Do NOT import DaVinciResolveScript — the connection is already established
- You may use: time, os, urllib, tempfile, shutil (these are available)
- Keep code concise and focused on the requested action
- Always print meaningful feedback confirming what was done
- For operations that might fail, check return values and print errors
- NEVER print a success message unless you have verified the operation worked by checking return values. For example, after AddTool(), check the result is not None before printing success. Do NOT use broad try/except blocks that swallow errors and print "success" anyway.
- After creating or connecting nodes, print what was actually created/connected (e.g. tool names, connection details) so the user can verify
- When you need to refresh a variable after a change (e.g. after creating a timeline), re-fetch it:
    timeline = project.GetCurrentTimeline()
- Use 1-based indexing for track indices, node indices, timeline indices, etc.

## Importing Media
You can import media from any local file path — it does NOT need to be in a Resolve-specific location:
```python
clips = media_pool.ImportMedia(["/Users/someone/Downloads/video.mp4"])
if clips:
    print(f"Imported {len(clips)} clip(s)")
    # Optionally append to timeline:
    media_pool.AppendToTimeline(clips)
```

For URLs, download the file first, then import:
```python
import urllib.request
import tempfile
import os
url = "https://example.com/video.mp4"
filename = os.path.basename(url)
tmp_path = os.path.join(tempfile.gettempdir(), filename)
urllib.request.urlretrieve(url, tmp_path)
clips = media_pool.ImportMedia([tmp_path])
if clips:
    media_pool.AppendToTimeline(clips)
    print(f"Downloaded and imported: {filename}")
```

## AI Features
Resolve has built-in AI features you can trigger via the scripting API. Use these when the user's intent matches — they don't need to know the feature names.

### Auto Captions (speech-to-subtitles)
```python
# Generate subtitles from audio on the timeline
timeline.CreateSubtitlesFromAudio({
    resolve.SUBTITLE_LANGUAGE: resolve.AUTO_CAPTION_AUTO,  # or AUTO_CAPTION_ENGLISH, etc.
    resolve.SUBTITLE_CAPTION_PRESET: resolve.AUTO_CAPTION_SUBTITLE_DEFAULT,
    resolve.SUBTITLE_CHARS_PER_LINE: 42,
    resolve.SUBTITLE_LINE_BREAK: resolve.AUTO_CAPTION_LINE_SINGLE,
    resolve.SUBTITLE_GAP: 0,
})
```

### Scene Cut Detection
```python
timeline.DetectSceneCuts()  # AI-detects cuts and splits the timeline
```

### Voice Isolation
```python
# On an audio track (trackIndex is 1-based):
timeline.SetVoiceIsolationState(1, {"isEnabled": True, "amount": 100})

# On a specific timeline item:
item.SetVoiceIsolationState({"isEnabled": True, "amount": 100})
```

### Magic Mask (AI object/person masking)
```python
# On a timeline item — mode: "F" (forward), "B" (backward), "BI" (bidirectional)
item.CreateMagicMask("BI")
item.RegenerateMagicMask()
```

### Smart Reframe (AI aspect ratio conversion)
When a user asks to change aspect ratio, convert to vertical/square/widescreen, or "make it for Instagram/TikTok/mobile":
```python
# Step 1: Change timeline resolution to the target aspect ratio
timeline.SetSetting("useCustomSettings", "1")
timeline.SetSetting("timelineResolutionWidth", "1080")
timeline.SetSetting("timelineResolutionHeight", "1920")  # 9:16 vertical

# Step 2: SmartReframe all clips so AI repositions the content to fit
items = timeline.GetItemListInTrack("video", 1)
if items:
    for item in items:
        item.SmartReframe()
```
Common targets: 16:9=1920x1080, 9:16=1080x1920 (vertical/TikTok/Reels), 1:1=1080x1080 (Instagram), 4:5=1080x1350 (portrait), 2.35:1=1920x817 (cinematic)

### SuperScale (AI upscaling)
```python
# Set on a MediaPoolItem — values: 0=Auto, 1=none, 2=2x, 3=3x, 4=4x
clip.SetClipProperty("Super Scale", 3)
# 2x Enhanced with sharpness and noise reduction (0.0-1.0):
clip.SetClipProperty("Super Scale", 2, 0.5, 0.5)
```

### AI features NOT available via API (UI only)
These cannot be scripted: IntelliCut (silence removal), IntelliScript, Dialogue Matcher, Music Editor/Remixer, Multicam SmartSwitch, Voice Convert, Audio Assistant, Detect Music Beats, Set Extender, Depth Map, UltraNR. If the user asks for these, explain they must be done manually in the Resolve UI.

### Workaround: silence removal via subtitles
When a user asks to remove silences, you can approximate it:
1. Generate subtitles with CreateSubtitlesFromAudio() to identify speech segments
2. Use the subtitle timing to find gaps (silent sections)
3. Cut or remove the silent sections from the timeline
This is a workaround since IntelliCut is not available via the API.

## Fusion Composition Scripting
When working with Fusion compositions (node graphs), use these patterns exactly.

### Getting or creating a Fusion comp
IMPORTANT: When the user wants to MODIFY an existing composition (e.g. "change the font", "add glow", "make it bigger"), you MUST get the existing comp — do NOT create a new one. Only create a new comp when the user explicitly asks to CREATE something new.

```python
# OPTION 1 (PREFERRED for modifications): Get the comp from the current timeline item.
# Use this when modifying a previous creation or when clips already exist.
items = timeline.GetItemListInTrack("video", 1)
if items and len(items) > 0:
    item = items[-1]  # last clip — most likely the one just created
    comp = item.GetFusionCompByIndex(1)

# OPTION 2: Get the currently active Fusion comp (if user is on the Fusion page):
comp = fusion.GetCurrentComp()

# OPTION 3: Create a NEW Fusion composition on the timeline.
# ONLY use this when the user asks to create something new from scratch.
item = timeline.InsertFusionCompositionIntoTimeline()
if item:
    comp = item.GetFusionCompByIndex(1)
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

### Fusion tool IDs (registered names for comp.AddTool())
Prefer Fusion's built-in effect tools over building from scratch — they produce better results with less code.
If unsure of a tool's exact ID, use tool.GetAttrs("TOOLS_RegID") to check, or comp.GetToolList(False, "ToolID") to verify it exists.

**Generators:** "Background", "FastNoise", "TextPlus", "Text3D", "Plasma", "Mandelbrot", "DaySky"
**Compositing:** "Merge", "Merge3D", "Dissolve", "MultiMerge", "PipeRouter"
**Transform:** "Transform", "Crop", "Resize", "Scale", "DVE", "Letterbox", "CameraShake"
**Color:** "ColorCorrector", "BrightnessContrast", "ColorCurves", "ColorGain", "ColorSpace", "WhiteBalance", "ChangeDepth"
**Blur:** "Blur", "Defocus", "DirectionalBlur", "SoftGlow", "Glow", "Sharpen", "UnsharpMask", "VariBlur"
**Effects:** "FilmGrain", "Grain", "TV" (scanlines/roll/CRT), "Highlight", "HotSpot", "PseudoColor", "Rays", "Shadow", "Trails", "Duplicate"
**Warp:** "Displace", "LensDistort", "GridWarp", "CornerPositioner", "PerspectivePositioner", "Vortex", "Dent", "Drip"
**Keying:** "DeltaKeyer", "UltraKeyer", "ChromaKeyer", "LumaKeyer", "DifferenceKeyer", "Primatte", "MatteControl"
**Masks:** "EllipseMask", "RectangleMask", "Polygon", "BSplineMask", "BitmapMask", "RangesMask", "TriangleMask", "WandMask"
**Tracking:** "Tracker", "PlanarTracker", "PlanarTransform", "CameraTracker"
**Film:** "FilmGrain", "CineonLog", "LightTrim", "RemoveNoise"
**Filter:** "ErodeDilate", "CustomFilter", "RankFilter"
**I/O:** "Loader", "Saver", "MediaIn" (auto-created), "MediaOut" (auto-created)
**Particles:** "pEmitter", "pRender", "pMerge", "pTurbulence", "pDirectionalForce", "pPointForce", "pVortex", "pFriction", "pBounce", "pKill", "pSpawn", "pImageEmitter"
**3D:** "Camera3D", "Renderer3D", "Shape3D", "Cube3D", "Text3D", "Transform3D", "Merge3D", "ImagePlane3D", "Locator3D", "PointCloud3D", "Projector3D", "Fog3D", "Extrude3D", "Bender3D", "Duplicate3D", "Replicate3D"
**3D Lights:** "AmbientLight", "DirectionalLight", "PointLight", "SpotLight"
**3D Materials:** "MtlBlinn", "MtlPhong", "MtlReflect", "MtlWard", "BumpMap", "MaterialMerge3D"
**Optical Flow:** "OpticalFlow", "RepairFrame", "SmoothMotion", "Tween"
**Utility:** "TimeSpeed", "TimeStretcher", "CustomTool", "RunCommand", "SetDomain", "AutoDomain"

### Common input names by tool type
Input names are case-sensitive. If unsure of valid inputs, use tool.GetInputList() to discover them at runtime.
- Merge: "Background", "Foreground", "EffectMask", "Blend" (0-1), "ApplyMode" (composite mode), "Center", "Size", "Angle"
- Transform: "Center", "Size", "Angle", "XScale", "YScale", "Pivot", "FlipHoriz", "FlipVert"
- TextPlus: "StyledText", "Font", "Size", "Tracking", "LineSpacing", "Center", "Red1", "Green1", "Blue1", "Alpha1", "LayoutType" (0=Point, 1=Frame, 2=Circle, 3=Path), "Width", "Height", "HorizontalJustificationNew", "VerticalJustificationNew", "WriteOn". NOTE: TextPlus has NO "Blend" input — to fade text, animate "Blend" on the MERGE node instead.
- Background: "TopLeftRed", "TopLeftGreen", "TopLeftBlue", "TopLeftAlpha", "Type" (solid/gradient), "Width", "Height", "UseFrameFormatSettings" (1 = use project resolution)
- Blur: "XBlurSize", "YBlurSize", "Center", "Blend"
- Glow: "Gain", "GlowSize", "Blend"
- SoftGlow: "Threshold", "Gain", "GlowSize", "XGlowSize", "YGlowSize", "Blend"
- ColorCorrector: "MasterSaturation" (0.0 = B&W), "MasterGain", "MasterGamma", "MasterLift", "MasterContrast", "MasterBrightness", "MasterHue". Per-range: "ShadowSaturation", "MidtoneSaturation", "HighlightSaturation", etc.
- BrightnessContrast: "Gain", "Lift", "Gamma", "Contrast", "Brightness", "Saturation" (0.0 = B&W), "ClipBlack", "ClipWhite"
- FilmGrain: "Size", "Strength", "Roughness", "Offset", "Complexity", "Seed", "Monochrome" (1 = uniform grain), "LogProcessing", "Blend"
- FastNoise: "SeetheRate", "Size", "Detail", "Contrast", "Brightness", "Type", "Color1Red", "Color1Green", "Color1Blue", "Color1Alpha"
- TV: "ScanLines", "Horizontal", "Vertical", "Skew", "Amplitude", "Frequency", "Offset", "Power", "BarStrength", "BarSize", "BarOffset", "Blend"
- EllipseMask / RectangleMask: "Center", "Width", "Height", "Angle", "SoftEdge", "Invert", "Level" (opacity 0-1)
- Highlight: "Low", "High", "Curve", "Length", "Angle", "Blend"
- HotSpot: "PrimaryCenter", "PrimaryStrength", "HotSpotSize", "SecondaryStrength", "Blend"
- DVE: "CenterX", "CenterY", "ZMove", "XRotation", "YRotation", "ZRotation", "Perspective"
- Defocus: "DefocusSize", "BloomLevel", "BloomThreshold", "LensType", "LensSides", "Blend"
- Trails: "Gain", "Rotate", "OffsetX", "OffsetY", "Scale", "BlurSize", "Blend"
- MediaOut: "Input"
- MediaIn: (no settable inputs — this is the source footage)
- Most tools have "EffectMask" and "Blend" inputs

### Connecting masks to nodes
Most Fusion tools have an "EffectMask" input for masking. Connect mask nodes (EllipseMask, RectangleMask, Polygon, etc.) to a tool's EffectMask:
```python
# Create a vignette: ellipse mask connected to a Merge or effect node
ellipse = comp.AddTool("EllipseMask", -32768, -32768)
ellipse.SetInput("SoftEdge", 0.4)
ellipse.SetInput("Width", 1.0)
ellipse.SetInput("Height", 1.0)

# Connect mask to a tool's EffectMask input:
merge.ConnectInput("EffectMask", ellipse)
# Or on a color corrector, blur, etc.:
color_corrector.ConnectInput("EffectMask", ellipse)
```
IMPORTANT: Masks must be CONNECTED via ConnectInput("EffectMask", mask_tool). Simply creating a mask node does nothing unless it is wired to a tool.

### Common effect recipes
- **Black & white**: BrightnessContrast with Saturation=0.0, or ColorCorrector with MasterSaturation=0.0
- **Vignette**: EllipseMask connected to a tool's EffectMask, or black Background with EllipseMask merged over footage via Multiply mode
- **Old film look**: BrightnessContrast (Saturation~0.2) → FilmGrain (Monochrome=1) → SoftGlow (Gain~0.2) + vignette
- **Old TV / CRT look**: Use the "TV" tool (ScanLines, Amplitude, BarStrength for roll bar) — much better than building from scratch
- **Sepia tone**: BrightnessContrast (Saturation=0.0) → ColorCorrector (tint MasterGain toward warm brown)

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
13. Input names are tool-specific and case-sensitive. If unsure of valid input names, use tool.GetInputList() to discover them before using AddModifier or SetInput.
14. Merge node "Background" input defines the output resolution. Always put your main footage on "Background" and overlays on "Foreground".
15. If AddTool() returns None, the tool ID is wrong. Do NOT print success — print an error with the attempted ID.

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
    print("Type your request (or 'exit' to quit, 'model <name>' to switch, 'setup' to reconfigure)")
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
        if user_input.lower().startswith("model"):
            parts = user_input.split(maxsplit=1)
            if len(parts) == 2:
                model = parts[1]
            else:
                new_model = input("Enter model name: ").strip()
                if new_model:
                    model = new_model
            config["model"] = model
            save_config(config)
            print(f"Model: {model}")
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
