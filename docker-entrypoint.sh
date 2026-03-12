#!/bin/bash
set -e

# Start Xvfb virtual framebuffer for headless screen capture
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for Xvfb to be ready
sleep 1

# Start PulseAudio for audio playback (needed by paplay)
pulseaudio --start --exit-idle-time=-1 2>/dev/null || true

# Run neurascreen with all arguments
exec neurascreen "$@"
