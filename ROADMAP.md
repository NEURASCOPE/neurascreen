# Roadmap

## v1.0 — Initial Release

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

- [x] Macro recorder: record browser interactions → JSON scenario (#9)
- [x] Docker container for headless generation (#13)

## v1.5 — Desktop GUI (in progress)

Optional PySide6 desktop interface: `pip install neurascreen[gui]`

- [x] GUI foundation: main window, menu bar, toolbar, sidebar, status bar (#25)
- [x] Theme engine: JSON palettes → dynamic QSS, dark teal + light themes (#25)
- [x] Scenario editor: visual step list, adaptive detail panel, JSON source view (#26)
- [x] Execution panel: run commands from GUI with real-time console logs (#27)
- [ ] TTS & audio preview: per-step narration preview, pronunciation helper (#28)
- [ ] Configuration manager: visual .env editor with tabbed interface (#29)
- [ ] Output browser: browse generated videos, SRT/chapters viewers (#30)
- [ ] Macro recorder integration: record browser interactions from GUI (#31)
- [ ] Advanced: selector validator, scenario stats, diff viewer, autosave (#32)

## Future Ideas

- Azure Speech TTS provider
- Amazon Polly TTS provider
- Whisper-based pronunciation validation
- AI-powered scenario repair (auto-fix broken selectors)
