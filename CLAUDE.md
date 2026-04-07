# Slop Resolve — DaVinci Resolve AI Agent

## Project overview
A CLI agent that controls DaVinci Resolve via natural language using any LLM (through litellm).

## Tech stack
- Python 3.10+
- litellm (multi-provider LLM routing)
- pytest (testing)
- ruff (linting)
- pyright via npx (type checking)

## Project structure
- `resolve_agent.py` — Main agent loop, prompt building, LLM chat
- `executor.py` — Sandboxed code execution against Resolve
- `resolve_connection.py` — Resolve connection and state gathering
- `resolve_api_ref.py` — API reference string for the system prompt
- `setup.py` — First-run setup wizard (provider/model/key config)
- `tests/` — pytest test suite with mock Resolve fixtures

## Commands

### Lint
```
ruff check .
```

### Fix lint errors
```
ruff check --fix .
```

### Type check
```
npx pyright .
```

### Run tests
```
python -m pytest tests/ -v
```

### Full check (lint + types + tests)
```
ruff check . && npx pyright . && python -m pytest tests/ -v
```

## Post-generation checklist
After writing or modifying Python code, always run the full check:
1. `ruff check .` — catch unused imports, f-string issues, style problems
2. `ruff check --fix .` — auto-fix what's fixable
3. `npx pyright .` — catch type errors (attribute access on None, wrong types, etc.)
4. `python -m pytest tests/ -v` — ensure all tests pass

## Code conventions
- No unused imports
- No f-strings without placeholders (use plain strings instead)
- Handle `None` returns properly — use guards (`if x is None`) or `or ""` fallbacks
- Use `# type: ignore[rule]` only for unavoidable cases (e.g. litellm union return types, runtime-only imports like DaVinciResolveScript)
- Tests use pytest classes grouped by function under test
- Tests must narrow optional types with `assert x is not None` before using `in` or attribute access
- Mock Resolve objects are defined in `tests/conftest.py`
