# Resolve AI Agent

Control DaVinci Resolve with natural language. Ask it to build timelines, set up Fusion graphs, import media, configure renders -- and it translates your words into Resolve API calls and executes them live.

Works with any LLM provider: Claude, GPT, Gemini, Ollama (local), OpenRouter, and 100+ others via litellm.

## How It Works

```
You (terminal) --> Agent --> LLM --> generates Python code --> executes against running Resolve
```

The agent connects to your running DaVinci Resolve instance via its scripting API, gathers the current state (project, timeline, media pool, etc.), and sends your request along with the full Resolve API reference to the LLM. The LLM responds with Python code, which the agent executes. If the code fails, it automatically retries with the error context.

## Quick Start

**Prerequisites:** Python 3.6+, DaVinci Resolve (running)

```bash
python resolve_agent.py
```

On first run, the setup wizard will:

1. Install the `litellm` package
2. Ask you to choose an LLM provider
3. Prompt for your API key (with a link to get one)
4. Let you pick a model
5. Save everything to `~/.resolve-agent/config.json`

## Example Session

```
Connected to DaVinci Resolve 19.1.2
Project: My Documentary
Model: claude-sonnet-4-20250514

You: create a new timeline called Rough Cut with 3 video tracks

Assistant: I will create a new timeline and add extra video tracks.

[Executing code...]
Created timeline: Rough Cut
Added video track 2
Added video track 3

You: set up a ProRes 422 HQ render to the Output folder on my desktop

Assistant: I will configure the render settings for ProRes 422 HQ.

[Executing code...]
Render format: QuickTime
Codec: Apple ProRes 422 HQ
Target: C:/Users/meigo/Desktop/Output
Render job added: job_001
```

## Supported Providers

| Provider | Model examples | API key env var |
|----------|---------------|-----------------|
| Anthropic (Claude) | `claude-sonnet-4-20250514`, `claude-opus-4-20250514` | `ANTHROPIC_API_KEY` |
| OpenAI (GPT) | `gpt-4o`, `gpt-4o-mini` | `OPENAI_API_KEY` |
| Google (Gemini) | `gemini/gemini-2.5-pro`, `gemini/gemini-2.5-flash` | `GEMINI_API_KEY` |
| OpenRouter | `openrouter/anthropic/claude-sonnet-4-20250514` | `OPENROUTER_API_KEY` |
| Ollama (local) | `ollama/llama3`, `ollama/mistral` | none |

Any model supported by [litellm](https://docs.litellm.ai/docs/providers) works.

## Commands

Inside the chat loop:

| Command | Action |
|---------|--------|
| `setup` | Re-run the configuration wizard |
| `clear` | Clear conversation history |
| `exit` / `quit` / `q` | Quit |

CLI flags:

```bash
python resolve_agent.py --setup       # Force reconfiguration
python resolve_agent.py -m gpt-4o     # Override model for this session
```

## What It Can Do

Anything the DaVinci Resolve scripting API supports:

- **Project management** -- create, load, save projects
- **Timeline editing** -- create timelines, add tracks, insert clips, set markers
- **Media pool** -- import media, organize folders, manage clips
- **Color grading** -- set CDL values, apply LUTs, manage node graphs and versions
- **Fusion compositing** -- create and modify Fusion compositions
- **Rendering** -- configure render settings, add jobs, start renders
- **Fairlight audio** -- track management, voice isolation
- **Introspection** -- query current state, list clips, inspect properties

## Project Structure

```
resolve_agent.py        # Main entry point -- REPL loop and LLM integration
resolve_connection.py   # Connects to Resolve and gathers current state
resolve_api_ref.py      # Full Resolve scripting API reference (auto-generated)
executor.py             # Sandboxed code execution for LLM-generated Python
setup.py                # First-run wizard -- installs packages, configures provider
requirements.txt        # litellm
tests/                  # 70 tests covering all modules
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

Tests mock the Resolve API so they run without a Resolve instance.

## How the API Reference Works

The file `resolve_api_ref.py` contains the full DaVinci Resolve scripting API reference (~1000 lines) extracted from the README.txt bundled with Resolve at:

```
C:/ProgramData/Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/README.txt
```

This is included in every LLM request so the model knows every available method, parameter, and return type. It adds ~15K tokens to the system prompt, which fits comfortably in modern context windows.

## License

MIT
