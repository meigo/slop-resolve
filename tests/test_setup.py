"""Tests for setup.py — config management."""
import json
import os
import pytest
from unittest.mock import patch

from setup import load_config, save_config, apply_config, PROVIDERS


class TestLoadConfig:
    """Test config loading from disk."""

    def test_load_existing(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"model": "gpt-4o", "env": {}}))
        with patch("setup.CONFIG_FILE", str(config_file)):
            config = load_config()
        assert config["model"] == "gpt-4o"

    def test_load_missing(self, tmp_path):
        with patch("setup.CONFIG_FILE", str(tmp_path / "missing.json")):
            config = load_config()
        assert config == {}

    def test_load_malformed(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("not json")
        with patch("setup.CONFIG_FILE", str(config_file)):
            with pytest.raises(json.JSONDecodeError):
                load_config()


class TestSaveConfig:
    """Test config saving to disk."""

    def test_save_creates_dir(self, tmp_path):
        config_dir = tmp_path / "subdir"
        config_file = config_dir / "config.json"
        with patch("setup.CONFIG_DIR", str(config_dir)), \
             patch("setup.CONFIG_FILE", str(config_file)):
            save_config({"model": "test", "env": {}})
        assert config_file.exists()
        assert json.loads(config_file.read_text())["model"] == "test"

    def test_save_overwrites(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"model": "old"}))
        with patch("setup.CONFIG_DIR", str(tmp_path)), \
             patch("setup.CONFIG_FILE", str(config_file)):
            save_config({"model": "new", "env": {}})
        assert json.loads(config_file.read_text())["model"] == "new"


class TestApplyConfig:
    """Test config application to environment."""

    def test_sets_env_vars(self):
        env_key = "_TEST_RESOLVE_AGENT_KEY_12345"
        config = {"env": {env_key: "test-value"}}
        apply_config(config)
        assert os.environ.get(env_key) == "test-value"
        del os.environ[env_key]

    def test_empty_env(self):
        config = {"env": {}}
        apply_config(config)  # should not raise

    def test_missing_env_key(self):
        config = {"model": "test"}
        apply_config(config)  # should not raise (no "env" key)


class TestProviders:
    """Test provider configuration is well-formed."""

    def test_all_providers_have_required_keys(self):
        for key, provider in PROVIDERS.items():
            assert "name" in provider
            assert "env_var" in provider
            assert "default_model" in provider
            assert "models" in provider
            assert "key_url" in provider

    def test_default_model_is_in_models_list(self):
        for key, provider in PROVIDERS.items():
            assert provider["default_model"] in provider["models"], (
                f"Provider {provider['name']}: default model not in models list"
            )

    def test_ollama_has_no_key(self):
        ollama = PROVIDERS["5"]
        assert ollama["env_var"] is None
        assert ollama["key_url"] is None

    def test_provider_keys_are_sequential(self):
        assert list(PROVIDERS.keys()) == ["1", "2", "3", "4", "5"]
