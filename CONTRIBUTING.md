# Contributing to NeuraScreen

Thanks for your interest in contributing to NeuraScreen!

## How to contribute

### Report a bug

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your OS and Python version

### Suggest a feature

Open an issue with the `enhancement` label. Describe the use case and why it would be useful.

### Submit a pull request

1. Fork the repository
2. Create a feature branch: `git checkout -b my-feature`
3. Make your changes
4. Test locally: `python -m src validate examples/01-simple-navigation.json`
5. Commit: `git commit -m "Add my feature"`
6. Push: `git push origin my-feature`
7. Open a pull request

## Adding a TTS provider

TTS providers are defined in `src/tts.py`.

1. Create a new class extending `BaseTTSClient`
2. Implement the `_synthesize(text: str) -> bytes` method (must return WAV audio bytes)
3. Add your provider to the `create_tts_client()` factory function
4. Document the required `.env` variables in the README
5. Add the provider name to `.env.example`

Example:

```python
class MyTTSClient(BaseTTSClient):
    def _synthesize(self, text: str) -> bytes:
        # Call your TTS API and return WAV bytes
        ...
```

## Adding a scenario action

Actions are defined in `src/browser.py` in the `_do_step()` method.

1. Add your action name to `VALID_ACTIONS` in `src/scenario.py`
2. Add validation rules in `validate_scenario()` if needed
3. Implement the action in `_do_step()` using a `case` block
4. Document the action in the README actions table

## Code style

- Python 3.12+ with type hints
- No external linter enforced — keep it readable
- Prefer simple, clear code over abstractions
- Log important steps with `logger.info()` and details with `logger.debug()`

## Project philosophy

NeuraScreen should remain:
- **Simple** — easy to understand and modify
- **Scriptable** — CLI-first, no GUI
- **Focused** — generate demo videos, nothing else
