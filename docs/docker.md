# Docker — Headless Video Generation

Run NeuraScreen in a Docker container without a display. Useful for CI/CD pipelines, servers, and automated video generation.

## Quick start

### Build the image

```bash
docker build -t neurascreen .
```

### Generate a video

```bash
docker run --rm \
  -v ./scenarios:/app/examples \
  -v ./output:/app/output \
  -e APP_URL=http://host.docker.internal:3000 \
  -e TTS_PROVIDER=openai \
  -e TTS_API_KEY=sk-... \
  -e TTS_VOICE_ID=alloy \
  neurascreen full examples/demo.json --srt --chapters
```

### Batch mode

```bash
docker run --rm \
  -v ./scenarios:/app/examples \
  -v ./output:/app/output \
  -e APP_URL=http://host.docker.internal:3000 \
  neurascreen batch examples/ --no-narration
```

## How it works

The container includes:

| Component | Purpose |
|-----------|---------|
| **Python 3.12** | Runtime |
| **Playwright + Chromium** | Browser automation |
| **Xvfb** | Virtual framebuffer (fake display) |
| **ffmpeg** | Screen capture and video assembly |
| **PulseAudio** | Audio playback (for narration sync) |

The entrypoint script (`docker-entrypoint.sh`) starts Xvfb and PulseAudio before running NeuraScreen.

## Configuration

Pass environment variables with `-e`:

```bash
docker run --rm \
  -e APP_URL=http://host.docker.internal:3000 \
  -e APP_EMAIL=user@example.com \
  -e APP_PASSWORD=secret \
  -e TTS_PROVIDER=openai \
  -e TTS_API_KEY=sk-... \
  -e TTS_VOICE_ID=alloy \
  -e TTS_MODEL=tts-1-hd \
  -e VIDEO_WIDTH=1920 \
  -e VIDEO_HEIGHT=1080 \
  -e VIDEO_FPS=30 \
  neurascreen full examples/demo.json
```

Or use an env file:

```bash
docker run --rm --env-file .env \
  -v ./scenarios:/app/examples \
  -v ./output:/app/output \
  neurascreen full examples/demo.json
```

## Volumes

| Container path | Purpose |
|---------------|---------|
| `/app/examples` | Scenario JSON files (input) |
| `/app/output` | Generated videos, SRT, chapters (output) |
| `/app/temp` | Intermediate files (optional, for debugging) |
| `/app/logs` | Execution logs (optional) |

## Networking

### Access your local app

Use `host.docker.internal` to reach services running on the host:

```bash
-e APP_URL=http://host.docker.internal:3000
```

On Linux, you may need `--network host` instead:

```bash
docker run --rm --network host \
  -e APP_URL=http://localhost:3000 \
  ...
```

### Access remote apps

Point `APP_URL` to the remote server directly:

```bash
-e APP_URL=https://demo.example.com
```

## CI/CD integration

### GitHub Actions

```yaml
jobs:
  generate-video:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build NeuraScreen
        run: docker build -t neurascreen .

      - name: Generate demo video
        run: |
          docker run --rm \
            -v ${{ github.workspace }}/scenarios:/app/examples \
            -v ${{ github.workspace }}/output:/app/output \
            -e APP_URL=${{ secrets.APP_URL }} \
            -e TTS_PROVIDER=openai \
            -e TTS_API_KEY=${{ secrets.TTS_API_KEY }} \
            -e TTS_VOICE_ID=alloy \
            neurascreen full examples/demo.json --srt --chapters

      - name: Upload video
        uses: actions/upload-artifact@v4
        with:
          name: demo-video
          path: output/
```

## Troubleshooting

### Browser fails to start

Check that Chromium was installed correctly:

```bash
docker run --rm neurascreen validate examples/01-simple-navigation.json
```

### No video output

Check the logs:

```bash
docker run --rm -v ./logs:/app/logs neurascreen -v full examples/demo.json
cat logs/*.log
```

### Screen capture is black

Xvfb may not have started. Check the entrypoint:

```bash
docker run --rm --entrypoint bash neurascreen -c "Xvfb :99 &; sleep 1; DISPLAY=:99 neurascreen preview examples/01-simple-navigation.json"
```

### App not reachable

Verify connectivity from the container:

```bash
docker run --rm --entrypoint bash neurascreen -c "curl -s http://host.docker.internal:3000 | head -5"
```
