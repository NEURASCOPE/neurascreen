# Cross-Platform Support

NeuraScreen runs on macOS, Linux and Windows. This guide covers platform-specific setup.

## Platform support matrix

| Feature | macOS | Linux | Windows |
|---------|-------|-------|---------|
| Browser automation (Playwright) | Yes | Yes | Yes |
| Screen capture | avfoundation | x11grab | gdigrab |
| Audio playback | afplay | paplay / aplay | PowerShell |
| TTS generation | Yes | Yes | Yes |
| Video assembly (ffmpeg) | Yes | Yes | Yes |

Platform is detected automatically — no configuration needed for single-monitor setups.

## macOS

### Install

```bash
brew install ffmpeg
pip install neurascreen
playwright install chromium
```

### Multi-monitor

```env
# ffmpeg avfoundation screen index
# Find yours: ffmpeg -f avfoundation -list_devices true -i ""
CAPTURE_SCREEN=1

# X pixel offset to position browser on the target screen
# Each 2560px screen adds 2560 (e.g. screen 2 = 5120)
BROWSER_SCREEN_OFFSET=5120
```

**Note**: ffmpeg screen indices do NOT match macOS System Preferences order. Capture one frame per screen to identify the correct index.

---

## Linux

### Install

```bash
# System dependencies
sudo apt install ffmpeg pulseaudio alsa-utils

# NeuraScreen
pip install neurascreen
playwright install chromium
```

### Screen capture (x11grab)

NeuraScreen uses `ffmpeg -f x11grab` on Linux. This requires an X11 display.

```env
# X11 display (default: :0.0)
CAPTURE_DISPLAY=:0.0

# Capture a specific region (offset from top-left)
CAPTURE_DISPLAY=:0.0+100,200
```

### Audio playback

NeuraScreen detects the available player automatically:

1. **paplay** (PulseAudio) — preferred, used if available
2. **aplay** (ALSA) — fallback

Install at least one:

```bash
# PulseAudio (recommended)
sudo apt install pulseaudio

# ALSA (alternative)
sudo apt install alsa-utils
```

### Headless Linux (no display)

Use Xvfb to create a virtual display:

```bash
# Install
sudo apt install xvfb

# Run NeuraScreen with virtual display
xvfb-run -s "-screen 0 1920x1080x24" neurascreen full scenario.json
```

Or use the [Docker container](docker.md) which handles this automatically.

---

## Windows

### Install

```bash
# Install ffmpeg (via Chocolatey)
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html and add to PATH

# NeuraScreen
pip install neurascreen
playwright install chromium
```

### Screen capture (gdigrab)

NeuraScreen uses `ffmpeg -f gdigrab` on Windows.

```env
# Capture full desktop (default)
CAPTURE_DISPLAY=desktop

# Capture a specific window by title
CAPTURE_DISPLAY=title=My Application
```

### Audio playback

Audio is played via PowerShell's `SoundPlayer` (built-in, no extra install needed).

### Known limitations on Windows

- `BROWSER_SCREEN_OFFSET` for multi-monitor positioning works via CDP but window placement may differ from macOS behavior
- Some ffmpeg features (like cursor capture) may behave differently with gdigrab

---

## Verifying your setup

Check that all dependencies are available:

```bash
# Verify ffmpeg
ffmpeg -version

# Verify Playwright
playwright --version

# Verify NeuraScreen
neurascreen --version

# Test with an example scenario
neurascreen validate examples/01-simple-navigation.json
neurascreen --headless preview examples/01-simple-navigation.json
```
