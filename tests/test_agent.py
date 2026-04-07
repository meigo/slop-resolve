"""Tests for resolve_agent.py — code extraction, response formatting, prompt building."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resolve_agent import extract_code_blocks, format_response, build_system_prompt


class TestExtractCodeBlocks:
    """Test Python code block extraction from LLM responses."""

    def test_single_code_block(self):
        text = 'Here is the code:\n```python\nprint("hello")\n```\nDone.'
        code = extract_code_blocks(text)
        assert code == 'print("hello")\n'

    def test_multiple_code_blocks(self):
        text = '```python\nprint("a")\n```\nAnd:\n```python\nprint("b")\n```'
        code = extract_code_blocks(text)
        assert code is not None
        assert 'print("a")' in code
        assert 'print("b")' in code

    def test_no_code_block(self):
        text = "Just a text response with no code."
        code = extract_code_blocks(text)
        assert code is None

    def test_non_python_code_block(self):
        text = '```javascript\nconsole.log("hi")\n```'
        code = extract_code_blocks(text)
        assert code is None

    def test_empty_code_block(self):
        text = '```python\n\n```'
        code = extract_code_blocks(text)
        assert code is not None  # matched, even if empty/whitespace

    def test_multiline_code(self):
        text = '```python\nx = 1\ny = 2\nprint(x + y)\n```'
        code = extract_code_blocks(text)
        assert code is not None
        assert "x = 1" in code
        assert "y = 2" in code
        assert "print(x + y)" in code

    def test_code_block_with_indentation(self):
        text = '```python\ndef foo():\n    return 42\n```'
        code = extract_code_blocks(text)
        assert code is not None
        assert "def foo():" in code
        assert "    return 42" in code


class TestFormatResponse:
    """Test response formatting (code block removal for display)."""

    def test_removes_code_block(self):
        text = 'Explanation:\n```python\nprint("hi")\n```\nDone.'
        result = format_response(text)
        assert "```python" not in result
        assert "[code executed]" in result
        assert "Explanation:" in result
        assert "Done." in result

    def test_text_only(self):
        text = "Just an explanation with no code."
        result = format_response(text)
        assert result == "Just an explanation with no code."

    def test_multiple_code_blocks(self):
        text = '```python\na\n```\nmiddle\n```python\nb\n```'
        result = format_response(text)
        assert result.count("[code executed]") == 2
        assert "middle" in result

    def test_strips_whitespace(self):
        text = "  \n  response  \n  "
        result = format_response(text)
        assert result == "response"


class TestBuildSystemPrompt:
    """Test system prompt construction."""

    def test_contains_api_reference(self, mock_resolve):
        prompt = build_system_prompt(mock_resolve)
        assert "API Reference" in prompt

    def test_contains_current_state(self, mock_resolve):
        prompt = build_system_prompt(mock_resolve)
        assert "Current Resolve State" in prompt
        assert "Test Project" in prompt
        assert "Main Timeline" in prompt

    def test_contains_code_rules(self, mock_resolve):
        prompt = build_system_prompt(mock_resolve)
        assert "resolve, project_manager, project, timeline" in prompt
        assert "print()" in prompt

    def test_contains_role(self, mock_resolve):
        prompt = build_system_prompt(mock_resolve)
        assert "DaVinci Resolve assistant" in prompt
