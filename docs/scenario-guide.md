# Scenario Writing Guide

This guide explains how to write effective demo scenarios for NeuraScreen.

## Structure

A scenario is a JSON file with a title, description, resolution, and an ordered list of steps.

```json
{
  "title": "Video title",
  "description": "Short description",
  "resolution": { "width": 1920, "height": 1080 },
  "steps": [...]
}
```

## Step-by-step process

### 1. Plan your video

Before writing JSON, outline:
- What pages to visit
- What elements to interact with
- What to say in the narration
- How long each section should be

### 2. Explore the UI first

Always check the real interface before writing selectors:
- Use browser DevTools to find CSS selectors
- Verify that text matches exactly for `click_text`
- Check that elements are visible and clickable

### 3. Write the scenario

Follow the **action-then-narrate** pattern:

```json
{ "action": "navigate", "url": "/dashboard", "wait": 2000 },
{ "action": "wait", "duration": 1000, "narration": "Description of what's visible." }
```

### 4. Validate and preview

```bash
python -m src validate my-scenario.json
python -m src preview my-scenario.json
```

Fix any failing steps before recording.

### 5. Generate the video

```bash
python -m src full my-scenario.json
```

## Tips

### Timing

- `wait` on action steps = pause AFTER the action (ms)
- `duration` on wait steps = how long the pause lasts
- The narrator automatically extends waits to match audio duration
- Keep transitions short (300-1500ms) for a snappy video

### Narration

- Write short, declarative sentences
- Describe what is VISIBLE on screen
- Start with an intro, end with a conclusion
- Use the **action-then-narrate** pattern consistently

### TTS pronunciation

TTS engines read text literally. If a word is mispronounced, adjust the spelling in the narration:

```json
"narration": "The worke flo engine processes data in real time."
```

This is a known technique. Test each audio segment and adjust as needed.

### Selectors

- Prefer `click_text` when there's visible text
- Use `click` with CSS selectors for buttons without text
- Use specific selectors: `button[title='Save']` is better than `button`
- Avoid fragile selectors like `.class-name-123`

## AI-assisted scenario creation

You can use AI to generate scenarios. Provide the AI with:

1. Your app's URL structure
2. Screenshots or descriptions of the pages
3. The list of available actions (from the README)
4. A narration outline

The AI will produce a JSON scenario that the tool can execute directly.
