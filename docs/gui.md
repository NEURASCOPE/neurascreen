# Desktop GUI

NeuraScreen includes an optional desktop interface for editing scenarios, running commands and previewing output — all without touching the terminal.

## Install

```bash
pip install neurascreen[gui]
```

This installs PySide6 (Qt for Python). The GUI is optional — the CLI works without it.

## Launch

```bash
neurascreen gui
```

## Overview

The GUI has four main areas:

| Area | Description |
|------|-------------|
| **Sidebar** (left) | File browser showing your scenario folders |
| **Editor** (center) | Visual scenario editor with step list and detail panel |
| **Tabs** (right) | Detail view, JSON source view, or split view |
| **Console** (bottom) | Execution output, hidden by default |

## Editing scenarios

### Create or open

- `Ctrl+N` — new empty scenario
- `Ctrl+O` — open a JSON file
- Double-click a file in the sidebar

### Step list

The left panel shows all steps in a table:

| Column | Content |
|--------|---------|
| # | Step number |
| Action | Action type (colored by category) |
| Title | Step title |
| Narration | Narration text preview |

Actions:
- **+ Add** — insert a new step
- **Dup** — duplicate selected step
- **Del** — delete selected step(s)
- **Up / Down** — reorder steps
- **Right-click** — context menu with all actions + templates

### Detail panel

Click a step to edit it. The form adapts to the action type:

- `navigate` shows URL field
- `click` shows CSS selector field
- `type` shows selector, text and delay fields
- `wait` shows duration field
- `drag` shows item name field
- Actions without parameters show "No parameters"

Common fields (always visible): Wait after, Narration, Screenshot after step.

### JSON view

Switch to the **JSON** tab to edit the raw JSON directly. Changes sync bidirectionally with the visual editor. Syntax highlighting colors keys, strings, numbers and booleans.

The **Split** tab shows both views side by side.

### Templates

Right-click in the step list → **Insert template** to add common patterns:

- Navigation + Narration (2 steps)
- Click + Narration (2 steps)
- Form Fill (3 steps)
- Drag + Configure + Delete (7 steps)
- Scroll + Narration (2 steps)
- Introduction / Conclusion (1 step each)

## Running commands

Press **F5**–**F8** or use the **Tools** menu:

| Shortcut | Command | Description |
|----------|---------|-------------|
| F5 | Validate | Check scenario for errors |
| F6 | Preview | Run in browser without recording |
| F7 | Run | Record video without narration |
| F8 | Full | Record with TTS narration |

The console panel opens automatically and shows real-time output. Colored by level: white (info), yellow (warning), red (error), green (success).

Options (checkboxes in the console panel): SRT subtitles, YouTube chapters, headless mode, verbose logging.

## Themes

Two built-in themes:

- **NeuraScope Dark Teal** (default) — dark background with teal accents
- **NeuraScope Light** — light background with teal accents

Switch themes: `Ctrl+T` (cycle) or **View > Theme**.

### Custom themes

Create a JSON file in `~/.neurascreen/themes/`:

```json
{
  "name": "My Custom Theme",
  "variant": "dark",
  "colors": {
    "primary": "#8B5CF6",
    "background": "#1a1a2e",
    "surface": "#16213e",
    "text": "#FFFFFF",
    "...": "see dark-teal.json for all keys"
  },
  "fonts": {
    "family": "Fira Sans, sans-serif",
    "size_md": 14,
    "monospace": "Fira Code, monospace"
  },
  "radius": 6,
  "spacing": 8
}
```

The theme appears in the **View > Theme** menu on next launch.

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New scenario |
| Ctrl+O | Open scenario |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save as |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| Ctrl+C | Copy steps |
| Ctrl+V | Paste steps |
| Ctrl+D | Duplicate step |
| Del | Delete step |
| F5 | Validate |
| F6 | Preview |
| F7 | Run |
| F8 | Full (with TTS) |
| Ctrl+R | Record macro |
| Ctrl+, | Configuration |
| Ctrl+B | Toggle sidebar |
| Ctrl+` | Toggle console |
| Ctrl+T | Cycle theme |
| Ctrl+Q | Quit |
