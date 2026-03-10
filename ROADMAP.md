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

## v1.1 — Quality of Life

- [ ] Linux screen capture via x11grab
- [ ] Linux audio playback via aplay/paplay
- [ ] Configurable login form selectors
- [ ] Configurable canvas/modal selectors for drag/delete_node/close_modal
- [ ] Better error messages with resolution hints
- [ ] install.sh setup script

## v1.2 — Developer Experience

- [ ] Unit tests for scenario parser and assembler
- [ ] Integration tests with headless browser
- [ ] GitHub Actions CI workflow example
- [ ] pyproject.toml for pip install
- [ ] `neurascreen` CLI entry point (instead of `python -m src`)

## v1.3 — New Features

- [ ] Windows screen capture via gdigrab
- [ ] Windows audio playback via powershell
- [ ] Macro recorder: record browser interactions and generate JSON scenario automatically
- [ ] Subtitle generation (SRT) from narration timestamps
- [ ] Chapter markers for YouTube from scenario step titles
- [ ] Intro/outro image overlay support

## v1.4 — Scale

- [ ] Batch mode: generate multiple videos from a folder of scenarios
- [ ] Parallel TTS generation
- [ ] Remote browser support (connect to existing Chrome/Chromium)
- [ ] Docker container for headless generation
- [ ] PyPI publication

## Future Ideas

- Azure Speech TTS provider
- Amazon Polly TTS provider
- Whisper-based pronunciation validation
- Web UI for scenario editing
- AI-powered scenario repair (auto-fix broken selectors)
