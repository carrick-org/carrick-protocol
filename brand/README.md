# Carrick brand assets — Waterline

The identity for the Carrick Protocol, the open standard for AI memory that people own.
The symbol is **Waterline**: a crag above the tide line, with its reflection broken into three calm strokes.
The rock stays put while the water moves. Carrick comes from the Irish *carraig*, meaning rock.

Carrick is neutral infrastructure. Keep its mark separate from Lodestone's: never pair the
Carrick symbol with Lodestone's amber, and never put the two marks in one lockup.

Status: v1, selected 2026-10-21. Every file is self-contained: the wordmark is converted to outlines, so no font needs to be installed.

## Contents

| Folder | Files | Use |
|---|---|---|
| `symbol/` | `carrick-symbol.svg`, `-on-dark`, `-mono-basalt`, `-mono-white` | The symbol at 24 px and above |
| `symbol/` | `carrick-symbol-small*.svg` | A redrawn 16-unit pixel-grid version for 16–23 px |
| `symbol/png/` | 64–1024 px transparent PNGs | For places that can't take SVG |
| `lockup/` | `carrick-lockup*.svg`, `carrick-protocol-lockup*.svg`; PNGs 240 px tall in `lockup/png/` | Symbol + wordmark, horizontal |
| `social/` | `carrick-social-card.svg`, `.png` (1280 × 640) | Open Graph and social preview image (GitHub: Settings › Social preview) |
| `favicon/` | `favicon.svg` (switches with light/dark mode), `favicon.ico` (16/32/48), `favicon-16/32/48.png`, `apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png` (maskable) | Websites and docs |
| `avatar/` | `carrick-avatar.svg`, `carrick-avatar-500.png`, `-1024.png`, `carrick-app-icon-maskable.svg` | GitHub org, social profiles, app icons |
| `badge/` | `carrick-compatible.svg` (20 px), `@2x`, `carrick-compatible-card.svg`, `-card-dark.svg` | The "Carrick compatible" conformance mark |
| `tokens/` | `carrick-tokens.css`, `carrick-tokens.json` | Colours and type for code |
| `source/` | `build.py`, `render.py` | Regenerate everything (see the end of this file) |
| `preview.png` | | Contact sheet of the whole pack |

## Colour

| Token | Hex | Use |
|---|---|---|
| Basalt | `#1B2A31` | Primary ink: the rock, the wordmark, text on light |
| Lough | `#2A7C7C` | The sea on light backgrounds; badge message field |
| Shallows | `#74B8B2` | The sea on dark backgrounds |
| Spray | `#E4EBE9` | The rock on dark backgrounds; light tint |
| Foam | `#F1F5F4` | Wordmark and one-colour symbol on dark |
| Ground | `#F4F6F5` | Light page background |
| Night | `#15232A` | Dark page background |
| Slate | `#4D5D63` | Secondary text on light ("Protocol" in the lockup) |

Contrast checks: white on Lough 4.9:1, Lough on Ground 4.5:1, Foam on Basalt 13.4:1, Shallows on Night 7.1:1.
Lough fails for body text on Basalt (3.0:1), so on dark backgrounds use Shallows instead.

## Type

- **Wordmark:** Schibsted Grotesk SemiBold (600), letter-spacing −0.03em. "Protocol" is set in Schibsted Grotesk Regular (400) in Slate.
- **Text:** Schibsted Grotesk 400/500/600. **Code and labels:** IBM Plex Mono 400/500.
- Both typefaces are SIL OFL 1.1 and available on Google Fonts.

## Using the symbol

- **Clear space:** leave a quarter of the symbol's width clear on every side.
- **Sizes:** use the full symbol from 24 px up. Below 24 px use `carrick-symbol-small`, which is redrawn on a pixel grid with two waves instead of three.
- **Colour:** use full colour where you can, and one colour (Basalt or white) where only one colour is available. On dark backgrounds use the `-on-dark` files, never the light-background colours.
- **Don't:** recolour the rock and waves into other hues, add gradients or shadows, outline the symbol, change the number or spacing of the waves, rotate it, or set the wordmark in another typeface.

## Snippets

**Website head**

```html
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
```

```json
{ "icons": [
  { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
  { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
] }
```

**"Carrick compatible" README badge**

Only servers that pass the conformance suite at Core level may use the badge (see
[Name and trademark](../spec/1-introduction.md#name-and-trademark)). Link it to this repository:

```markdown
[![Carrick compatible](https://raw.githubusercontent.com/carrick-org/carrick-protocol/main/brand/badge/carrick-compatible.svg)](https://github.com/carrick-org/carrick-protocol)
```

The badge text is already converted to outlines (in DejaVu Sans, the face shields.io badges render in), so it looks the same everywhere and sits evenly beside other badges.
To serve the badge from shields.io instead:

```
https://img.shields.io/badge/Carrick-compatible-2A7C7C?labelColor=1B2A31&logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiIgcm9sZT0iaW1nIiBhcmlhLWxhYmVsPSJDYXJyaWNrIj48dGl0bGU+Q2FycmljazwvdGl0bGU+PHBhdGggZD0iTTEgOSBMMyA1IEw2IDQgTDggNCBMOSAyIEwxMiAyIEwxMyA0IEwxNSA5IFoiIGZpbGw9IiNGMUY1RjQiLz48cmVjdCB4PSIxIiB5PSIxMSIgd2lkdGg9IjE0IiBoZWlnaHQ9IjIiIGZpbGw9IiM3NEI4QjIiLz48cmVjdCB4PSI0IiB5PSIxNCIgd2lkdGg9IjgiIGhlaWdodD0iMiIgZmlsbD0iIzc0QjhCMiIvPjwvc3ZnPgo=
```

**Website badge:** use `badge/carrick-compatible-card.svg` (light pages) or `-card-dark.svg` (dark pages), 280 × 68, linked to the conformance results.

## Wordmark

The wordmark, "Protocol" and the website card's text are outlined from Schibsted Grotesk (600 and
400, with the font's own kerning), and the social card's URL from its 500 weight. The lockup layout
is a 112-unit symbol, a 22-unit gap, then 92-unit type on an 88-unit baseline.

## Licence

The logo, symbol, wordmark and badge files are the Carrick marks. They are not covered by CC BY 4.0
or Apache 2.0 (see [LICENSE.md](../LICENSE.md)). You may use them unchanged to refer to the Carrick
Protocol, and the badge only as described above. The build scripts in `source/` are under Apache 2.0.

## Regenerating

From the repository root, with Schibsted Grotesk's variable font (`SchibstedGrotesk-VariableFont_wght.ttf`
from Google Fonts, SIL OFL 1.1; it isn't kept in this repository):

```
python3 brand/source/build.py brand --wordmark-font SchibstedGrotesk-VariableFont_wght.ttf
python3 brand/source/render.py brand
```

`build.py` rewrites every SVG and the tokens, leaving README.md and `source/` in place. `render.py`
renders the PNGs and `favicon.ico` with headless Chromium (needs `fonttools`, `Pillow` and
`playwright`). Without `--wordmark-font`, the lockups fall back to live text and no social card or
PNG lockups are made, so always pass it for a release.
The geometry lives in `build.py`: `ROCK`/`WAVES` for the 64-unit master and `ROCK_S`/`WAVES_S` for the
16-unit small version. Change it there, never in the output files.
