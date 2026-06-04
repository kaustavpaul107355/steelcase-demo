# COMPASS — Presentation deck

A self-contained, multi-slide HTML presentation for the COMPASS Steelcase demo.
No build step, no dependencies — open `index.html` in any modern browser.

## Run it

```bash
# Simplest: just open the file
open presentation/index.html

# Or serve it (avoids any file:// quirks)
cd presentation && python3 -m http.server 8000   # → http://localhost:8000
```

## Navigation

| Action | Keys / controls |
|--------|-----------------|
| Next / previous | `→` `←`, Space, PageDown/PageUp, or the `‹ ›` buttons |
| Jump to slide | Click a dot in the bottom nav |
| First / last | `Home` / `End` |
| Fullscreen | `f`, or the **⤢ Fullscreen** button |
| Deep-link a slide | URL hash, e.g. `index.html#5` |

## Attaching images, GIFs, and videos

Each content slide has a dashed **media slot**. To fill it:

- **Click** the slot to pick a file, or
- **Drag & drop** onto it.

Supported formats:

| Type | Formats |
|------|---------|
| Images | PNG, JPG, GIF, WEBP |
| Video | MP4, WebM, MOV (plays looped, muted — like a GIF) |

Videos autoplay **loop + muted** (presentation-friendly). Keep clips **short and under ~3MB** when possible — browser `localStorage` caps around ~5MB total for the whole deck.

### Multiple images per slot

Each media frame can hold a **gallery** of images or videos:

- **Add more:** click **Add** in the bar below, or drag & drop multiple files at once onto an empty slot
- **Browse:** click **‹ ›** on the sides of the frame (appear on hover), or use the gallery controls in the bar
- **Replace** swaps only the currently visible item; **Remove this** removes it; **Clear all** empties the slot

Gallery position is saved per slot and included in **Export media**.

### Resizing the media frame

- **Drag the corner handle** on the frame to resize within the fixed anchor box
- **Reset** in the bar restores full size; frame settings apply to the whole gallery

Attachments are saved in your browser's `localStorage`, so they persist across
reloads **on the same browser**. If you hit the storage limit, use **Export media**.

### Sharing the deck with images

`localStorage` is per-browser, so to move the deck (or send it to a teammate):

1. Click **Export media** → downloads `compass-deck-media.json` (all attachments).
2. Share the `presentation/` folder **and** that JSON.
3. The recipient opens `index.html` and clicks **Import media**, choosing the JSON.

> Prefer committing screenshots to the repo? Drop them in `assets/` and reference
> them directly in `index.html` (e.g. replace a `<div class="media-slot">` with
> `<img src="assets/genie.gif">`). The upload flow is for quick, browser-local iteration.

## Editing content

Slide text lives directly in `index.html` as `<section class="slide">` blocks —
edit the HTML. Each media slot is a `<div class="media-slot" data-slot="UNIQUE_ID">`;
the `data-slot` id is the storage key, so keep it unique per slot. `app.js` handles
navigation + uploads; `styles.css` is the theme.

## Print / PDF

`Cmd/Ctrl+P` renders every slide stacked (one per page) for a PDF handout.
