# Subtitles & YouTube Chapters

Generate SRT subtitle files and YouTube chapter markers alongside your videos.

## Subtitles (SRT)

### Usage

Add `--srt` to any `run`, `full` or `batch` command:

```bash
neurascreen full --srt scenario.json
```

This creates `output/scenario.srt` next to `output/scenario.mp4`.

### Output format

Standard SRT format, compatible with YouTube, VLC, and all major video players:

```
1
00:00:04,206 --> 00:00:23,246
Welcome to this demo of the dashboard module.

2
00:00:33,392 --> 00:01:04,272
Here we can see the workflow editor with existing nodes.
```

### How it works

- Each narrated step becomes one subtitle entry
- Start time = real timestamp when the audio started playing during recording
- End time = start time + audio duration (from the generated WAV file)
- Text = the `narration` field from the scenario JSON

### Using SRT files

**YouTube**: Upload the `.srt` file in YouTube Studio > Subtitles > Add language > Upload file. Viewers can toggle subtitles on/off.

**VLC**: Place the `.srt` file next to the `.mp4` with the same name. VLC loads it automatically.

**Embed in video**: If you need hardcoded subtitles (burned into the video), use ffmpeg:

```bash
ffmpeg -i video.mp4 -vf subtitles=video.srt output.mp4
```

---

## YouTube Chapters

### Usage

Add `--chapters` to any `run`, `full` or `batch` command:

```bash
neurascreen full --chapters scenario.json
```

This creates `output/scenario.chapters.txt`.

### Output format

YouTube-compatible chapter markers, one per line:

```
00:00 Introduction
00:04 Dashboard overview
00:33 Workflow editor
01:12 Control flow palette
01:36 Router node
02:17 Guard node
```

### How it works

- Each narrated step generates a chapter
- The chapter title comes from the step's `title` field (falls back to "Section N" if empty)
- Timestamps are taken from the real recording
- An "Introduction" chapter at `00:00` is auto-inserted if the first narration starts later

### Using chapter markers

Copy the content of the `.chapters.txt` file into your YouTube video description. YouTube automatically detects the timestamp format and creates clickable chapters in the video player.

**Requirements for YouTube chapters**:
- First chapter must start at `00:00` (NeuraScreen handles this automatically)
- Minimum 3 chapters
- Each chapter must be at least 10 seconds long

---

## Combining both

```bash
# Single video with subtitles and chapters
neurascreen full --srt --chapters scenario.json

# Batch: all videos in a folder
neurascreen batch scenarios/ --srt --chapters
```

## Tips

- Write meaningful `title` fields in your scenario steps — they become chapter names
- Keep narrations concise — long text makes subtitles hard to read
- Use `--srt --chapters` together by default for production videos
- The files are generated after the video, so they don't slow down recording
