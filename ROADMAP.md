# Roadmap

## v1.0 — Current Release

- [x] JSON scenario format with 14 browser actions
- [x] Playwright browser engine with fullscreen CDP
- [x] Native screen capture via ffmpeg avfoundation (macOS)
- [x] Real-time audio synchronization
- [x] 5 TTS providers (OpenAI, ElevenLabs, Gradium, Google, Coqui)
- [x] CLI interface (validate, preview, run, full, list)
- [x] Multi-monitor support
- [x] Audio caching by content hash
- [x] Example scenarios

## v1.1 — Packaging & Config

- [x] pyproject.toml for `pip install neurascreen`
- [x] `neurascreen` CLI entry point (instead of `python -m src`)
- [x] `--version` flag
- [x] Configurable login form selectors (#3)
- [x] Configurable canvas/modal selectors for drag/delete_node/close_modal (#4)
- [x] Unit tests for assembler and utils (#5)

## v1.2 — Cross-platform

- [x] Linux screen capture via x11grab (#1)
- [x] Linux audio playback via aplay/paplay (#2)
- [x] Windows screen capture via gdigrab (#8)

## v1.3 — Production features

- [x] Subtitle generation (SRT) from narration timestamps (#10)
- [x] YouTube chapter markers from scenario step titles (#11)
- [x] Batch mode: generate multiple videos from a folder (#12)

## v1.4 — Advanced

- [ ] Macro recorder: record browser interactions → JSON scenario (#9)
- [ ] Docker container for headless generation (#13)

## Future Ideas

- Azure Speech TTS provider
- Amazon Polly TTS provider
- Whisper-based pronunciation validation
- Web UI for scenario editing
- AI-powered scenario repair (auto-fix broken selectors)
