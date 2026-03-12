# Macro Recorder

Generate JSON scenarios by recording your browser interactions instead of writing them by hand.

## Quick start

```bash
neurascreen record http://localhost:3000
```

A Chromium browser opens. Navigate, click, scroll as you normally would. When done, **close the browser window** (or press `Ctrl+C` in the terminal). The tool outputs a valid JSON scenario.

## Options

```bash
neurascreen record <url> [OPTIONS]

Options:
  -o, --output PATH    Output JSON file path (default: output/<title>.json)
  -t, --title TEXT     Scenario title (default: "Recorded Scenario")
  -v, --verbose        Enable debug logging
```

## Examples

```bash
# Record with a custom title
neurascreen record http://localhost:3000 -t "Onboarding flow"

# Specify output path
neurascreen record http://localhost:3000 -o scenarios/onboarding.json

# Verbose mode for debugging
neurascreen -v record http://localhost:3000
```

## What gets captured

| Interaction | Scenario action | Notes |
|-------------|----------------|-------|
| Page navigation | `navigate` | URL path is extracted, duplicates are skipped |
| Click on text | `click_text` | Used when the element has short visible text (< 50 chars) |
| Click on icon/button | `click` | Fallback to CSS selector when no text is available |
| Scroll | `scroll` | Debounced (500ms) to avoid duplicate entries |
| Keyboard (Enter, Escape, Tab) | `key` | Only special keys are captured |
| Pause > 2 seconds | `wait` | Capped at 10 seconds max |

## How selectors are built

The recorder tries to generate stable CSS selectors in this priority order:

1. `#id` — Element ID (most stable)
2. `[data-testid="..."]` — Test attribute
3. `[name="..."]`, `[title="..."]`, `[aria-label="..."]` — Semantic attributes
4. `tag.class1.class2` — Tag + classes (if unique on the page)
5. `parent > tag:nth-child(n)` — Positional fallback

## Workflow: record → edit → generate

The recorder produces a **first draft**. You will typically want to:

1. **Record** your interactions
2. **Review** the JSON — remove unwanted clicks, fix selectors
3. **Add narration** to `wait` steps
4. **Adjust timing** — shorten or lengthen pauses
5. **Validate**: `neurascreen validate my-scenario.json`
6. **Preview**: `neurascreen preview my-scenario.json`
7. **Generate**: `neurascreen full my-scenario.json`

## Tips

- **Close unrelated tabs** before recording to avoid noise
- **Navigate slowly** — rapid clicking may generate duplicate events
- **Use keyboard shortcuts** sparingly — only Enter, Escape and Tab are captured
- **Check the output JSON** — the recorder captures raw events, some cleanup is usually needed
- **Narration is empty** by default — add it manually after recording

## Limitations

- Only captures interactions on the main frame (not iframes)
- Does not capture drag & drop (use `drag` action manually)
- Does not capture form typing (use `type` action manually)
- CSS selectors may be fragile for dynamically-generated elements
- Scroll events are simplified to a fixed `direction: down, amount: 400`
