# Resolve AI Agent

Control DaVinci Resolve with natural language. Describe what you want -- "make a cinematic intro", "add a countdown timer", "set up a ProRes render" -- and the agent figures out the technical details, generates the code, and executes it live.

Works with any LLM provider: Claude, GPT, Gemini, Ollama (local), OpenRouter, and 100+ others via litellm.

## How It Works

The agent connects to your running DaVinci Resolve instance via its scripting API, gathers the current state (project, timeline, media pool, etc.), and sends your request along with the full Resolve API reference to the LLM. The LLM acts as a creative collaborator -- it makes its own decisions about which nodes, effects, animations, and settings to use based on your intent. The generated code is executed live, and if it fails, the agent automatically retries with the error context.

## Quick Start

**Prerequisites:** Python 3.6+, DaVinci Resolve (running)

    python resolve_agent.py

On first run, the setup wizard will:

1. Install the litellm package
2. Ask you to choose an LLM provider
3. Prompt for your API key (with a link to get one)
4. Let you pick a model
5. Save everything to ~/.resolve-agent/config.json

## Example Prompts

You don't need to know the Resolve API. Just describe what you want:

- "make a countdown timer" -- creates a Fusion comp with animated text
- "add a cinematic title card that says Episode 1" -- picks fonts, colors, fade-in
- "set up a ProRes 422 HQ render to my desktop" -- configures render settings
- "create a new timeline called Rough Cut with 3 video tracks" -- timeline management
- "import the video from /Users/me/Downloads/podcast.mp4" -- imports from any local path
- "grab the video from https://example.com/clip.mp4 and add it to the timeline" -- downloads and imports
- "add captions to this video" -- uses AI auto-captioning
- "isolate the voice on the audio track" -- uses AI voice isolation
- "upscale this footage to 4x" -- uses AI SuperScale
- "add a glow effect to the text" -- modifies the last creation
- "make the numbers bigger and change the font" -- iterates on previous work

The conversation history is preserved, so you can iterate on your work. When you ask to modify something, the agent updates the existing Fusion composition in place rather than creating a new one.

## Supported Providers

| Provider | Model examples | API key env var |
|----------|---------------|-----------------|
| Anthropic (Claude) | claude-sonnet-4-20250514, claude-opus-4-20250514 | ANTHROPIC_API_KEY |
| OpenAI (GPT) | gpt-4o, gpt-4o-mini | OPENAI_API_KEY |
| Google (Gemini) | gemini/gemini-2.5-pro, gemini/gemini-2.5-flash | GEMINI_API_KEY |
| OpenRouter | openrouter/anthropic/claude-sonnet-4-20250514 | OPENROUTER_API_KEY |
| Ollama (local) | ollama/llama3, ollama/mistral | none |

Any model supported by litellm works (https://docs.litellm.ai/docs/providers).

## Commands

Inside the chat loop:

| Command | Action |
|---------|--------|
| model <name> | Switch model (e.g. model gpt-4o) -- saves to config |
| model | Prompt to enter a model name |
| setup | Re-run the full configuration wizard |
| clear | Clear conversation history |
| exit / quit / q | Quit |

CLI flags:

    python resolve_agent.py --setup       # Force reconfiguration
    python resolve_agent.py -m gpt-4o     # Override model for this session

## What It Can Do

Anything the DaVinci Resolve scripting API supports:

- **Media import** -- import from any local path or URL, organize in media pool
- **Project management** -- create, load, save projects
- **Timeline editing** -- create timelines, add tracks, insert clips, set markers
- **Color grading** -- set CDL values, apply LUTs, manage node graphs and versions
- **Fusion compositing** -- create and modify Fusion compositions, animate nodes, build motion graphics
- **Rendering** -- configure render settings, add jobs, start renders
- **Fairlight audio** -- track management, voice isolation
- **Introspection** -- query current state, list clips, inspect properties

### AI Features

The agent can trigger Resolve's built-in AI tools:

- **Auto Captions** -- generate subtitles from speech (16+ languages)
- **Scene Cut Detection** -- AI-detect and split cuts on the timeline
- **Voice Isolation** -- isolate dialogue from background noise
- **Magic Mask** -- AI-powered object/person masking
- **Smart Reframe** -- auto-reframe footage to different aspect ratios
- **SuperScale** -- AI upscaling (2x, 3x, 4x)

Some Resolve AI features (IntelliCut, Dialogue Matcher, Music Editor, etc.) are not yet available via the scripting API and must be used from the Resolve UI.

## Cross-Platform Support

Works on macOS, Windows, and Linux. The agent auto-detects the platform and finds the Resolve scripting modules in the correct location.

## Project Structure

    resolve_agent.py        # Main entry point -- REPL loop and LLM integration
    resolve_connection.py   # Connects to Resolve and gathers current state
    resolve_api_ref.py      # Full Resolve scripting API reference
    executor.py             # Sandboxed code execution for LLM-generated Python
    setup.py                # First-run wizard -- installs packages, configures provider
    requirements.txt        # litellm
    tests/                  # Tests covering all modules

## Running Tests

    pip install pytest
    python -m pytest tests/ -v

Tests mock the Resolve API so they run without a Resolve instance.

## How the API Reference Works

The file resolve_api_ref.py contains the full DaVinci Resolve scripting API reference extracted from the README.txt bundled with Resolve. This is included in every LLM request so the model knows every available method, parameter, and return type. It adds ~15K tokens to the system prompt, which fits comfortably in modern context windows.

## License

MIT
