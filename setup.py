#!/usr/bin/env python3
"""First-run setup and configuration for the Resolve AI Agent."""

import json
import os
import subprocess
import sys

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".resolve-agent")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

PROVIDERS = {
    "1": {
        "name": "Anthropic (Claude)",
        "env_var": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
        "models": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-4-5-20251001"],
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "2": {
        "name": "OpenAI (GPT)",
        "env_var": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
        "key_url": "https://platform.openai.com/api-keys",
    },
    "3": {
        "name": "Google (Gemini)",
        "env_var": "GEMINI_API_KEY",
        "default_model": "gemini/gemini-2.5-pro",
        "models": ["gemini/gemini-2.5-pro", "gemini/gemini-2.5-flash"],
        "key_url": "https://aistudio.google.com/apikey",
    },
    "4": {
        "name": "OpenRouter (any model)",
        "env_var": "OPENROUTER_API_KEY",
        "default_model": "openrouter/anthropic/claude-sonnet-4-20250514",
        "models": ["openrouter/anthropic/claude-sonnet-4-20250514", "openrouter/openai/gpt-4o", "openrouter/google/gemini-2.5-pro"],
        "key_url": "https://openrouter.ai/keys",
    },
    "5": {
        "name": "Ollama (local, free)",
        "env_var": None,
        "default_model": "ollama/llama3",
        "models": ["ollama/llama3", "ollama/llama3.1", "ollama/mistral", "ollama/codellama"],
        "key_url": None,
    },
}


def load_config():
    """Load config from disk, or return empty dict."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save config to disk."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def apply_config(config):
    """Apply saved config to environment variables."""
    for key, value in config.get("env", {}).items():
        os.environ[key] = value


def install_packages():
    """Install required Python packages."""
    print("\nInstalling required packages...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "litellm"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("  litellm installed.")
    except subprocess.CalledProcessError:
        print("  Failed to install litellm. Try manually: pip install litellm")
        return False
    return True


def check_packages():
    """Check if required packages are installed."""
    try:
        import litellm  # noqa: F401
        return True
    except ImportError:
        return False


def prompt_choice(prompt, options, allow_empty=False):
    """Prompt user to pick from numbered options."""
    while True:
        choice = input(prompt).strip()
        if allow_empty and choice == "":
            return ""
        if choice in options:
            return choice
        print(f"  Invalid choice. Pick one of: {', '.join(options)}")


def run_setup(reconfigure=False):
    """Interactive setup wizard. Returns config dict."""
    config = load_config()

    if config and not reconfigure:
        apply_config(config)
        return config

    print("=" * 50)
    print("  Resolve AI Agent — Setup")
    print("=" * 50)

    # Step 1: Install packages
    if not check_packages():
        print("\nRequired package 'litellm' is not installed.")
        answer = input("Install it now? [Y/n]: ").strip().lower()
        if answer in ("", "y", "yes"):
            if not install_packages():
                sys.exit(1)
        else:
            print("Cannot continue without litellm. Install manually: pip install litellm")
            sys.exit(1)

    # Step 2: Choose provider
    print("\nChoose your LLM provider:\n")
    for key, p in PROVIDERS.items():
        print(f"  {key}. {p['name']}")
    print()

    choice = prompt_choice("Provider [1-5]: ", list(PROVIDERS.keys()))
    provider = PROVIDERS[choice]
    print(f"\n  Selected: {provider['name']}")

    # Step 3: API key (if needed)
    env = {}
    if provider["env_var"]:
        existing = os.environ.get(provider["env_var"], "")
        need_key = True

        if existing:
            masked = existing[:8] + "..." + existing[-4:]
            print(f"\n  Found existing {provider['env_var']}: {masked}")
            use_existing = input("  Use this key? [Y/n]: ").strip().lower()
            if use_existing in ("", "y", "yes"):
                env[provider["env_var"]] = existing
                need_key = False

        if need_key:
            print(f"\n  Get your API key at: {provider['key_url']}")
            api_key = input(f"  Enter {provider['env_var']}: ").strip()
            if not api_key:
                print("  No key provided. You can set it later as an environment variable.")
            else:
                env[provider["env_var"]] = api_key
    else:
        print("\n  No API key needed (local model).")
        print("  Make sure Ollama is running: ollama serve")

    # Step 4: Choose model
    print(f"\n  Available models for {provider['name']}:")
    for i, m in enumerate(provider["models"], 1):
        default_tag = " (default)" if m == provider["default_model"] else ""
        print(f"    {i}. {m}{default_tag}")
    print()

    model_opts = [str(i) for i in range(1, len(provider["models"]) + 1)]
    model_choice = input(f"  Model [1-{len(provider['models'])}] or custom name (Enter for default): ").strip()

    if model_choice == "":
        model = provider["default_model"]
    elif model_choice in model_opts:
        model = provider["models"][int(model_choice) - 1]
    else:
        model = model_choice  # custom model name

    print(f"\n  Model: {model}")

    # Save config
    config = {
        "provider": provider["name"],
        "model": model,
        "env": env,
    }
    save_config(config)
    apply_config(config)

    print(f"\n  Config saved to: {CONFIG_FILE}")
    print("  Run with --setup to reconfigure anytime.")
    print("=" * 50)

    return config
