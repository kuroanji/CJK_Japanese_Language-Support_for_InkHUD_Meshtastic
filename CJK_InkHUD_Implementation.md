# CJK (Japanese) Language Support for InkHUD

This document describes the implementation of CJK (Chinese-Japanese-Korean) character rendering in InkHUD, specifically targeting the T-Echo Plus variant with Japanese, Russian, and English language support.

## Overview

InkHUD uses AdafruitGFX-based 8-bit encoded fonts (Windows-125x codepages) which cannot represent CJK characters. This implementation adds a secondary bitmap font system for CJK characters, using an escape sequence encoding to pass CJK glyph indices through the existing single-byte text pipeline.

### Architecture

```
UTF-8 input
    │
    ▼
decodeUTF8() ─── Latin/Cyrillic ──► Win1251 single-byte encoding
    │
    CJK character
    │
    ▼
cjkLookup() ─── binary search by codepoint
    │
    ▼
3-byte escape: \x1B + high_byte + low_byte  (glyph index encoded)
    │
    ▼
write() override ─── state machine decodes escape
    │
    ▼
drawCJKGlyph() ─── renders packed bitmap via drawPixel()
```

## Files Modified / Created

### New Files

| File | Description |
|------|-------------|
| `src/graphics/niche/Fonts/CJK/CJKFont.h` | CJK font data structures (`CJKGlyph`, `CJKFont`) and binary search lookup function |
| `src/graphics/niche/Fonts/CJK/CJKFont_18px.h` | Auto-generated bitmap font, 18px cell (paired with 12pt Latin) |
| `src/graphics/niche/Fonts/CJK/CJKFont_13px.h` | Auto-generated bitmap font, 13px cell (paired with 9pt Latin) |
| `src/graphics/niche/Fonts/CJK/CJKFont_12px.h` | Auto-generated bitmap font, 13px cell (paired with 6pt Latin, larger for readability) |
| `tools/generate_cjk_font.py` | Python script to generate CJK bitmap font headers from TTF files |
| `docs/CJK_InkHUD_Implementation.md` | This document |

### Modified Files

| File | Changes |
|------|---------|
| `variants/nrf52840/t-echo-plus/platformio.ini` | Added `[env:t-echo-plus-inkhud]` build environment |
| `variants/nrf52840/t-echo-plus/nicheGraphics.h` | Set fonts to `FREESANS_*_JP` macros for CJK support |
| `src/graphics/niche/InkHUD/AppletFont.h` | Added `JAPANESE` encoding, CJK font pointer, JP font macros |
| `src/graphics/niche/InkHUD/AppletFont.cpp` | Added CJK-aware constructor, `JAPANESE` encoding in `applyEncoding()`, CJK escape encoding in `decodeUTF8()` |
| `src/graphics/niche/InkHUD/Applet.h` | Added `write()` override, `drawCJKGlyph()`, `getMixedTextWidth()`, CJK state vars |
| `src/graphics/niche/InkHUD/Applet.cpp` | Added CJK rendering, CJK-aware word wrapping in `printWrapped()`, increased header padding for CJK clearance |
| `src/graphics/niche/InkHUD/Applets/Bases/NodeList/NodeListApplet.h` | Added `lineGap` between short name and long name in card layout |
| `src/graphics/niche/InkHUD/Applets/Bases/NodeList/NodeListApplet.cpp` | Applied `lineGap` to line B position |
| `src/graphics/niche/InkHUD/WindowManager.cpp` | Battery icon sized to match Latin font, centered vertically in header |

## Implementation Details

### 1. CJK Escape Sequence Encoding

Since the text pipeline is 8-bit, CJK characters are encoded as 3-byte escape sequences:

```
\x1B  +  high_byte  +  low_byte
```

- `\x1B` (ESC) signals a CJK character follows
- `high_byte = (glyphIndex / 254) + 1` (avoiding `\x00`)
- `low_byte = (glyphIndex % 254) + 1` (avoiding `\x00`)

This supports up to 254 * 254 = 64,516 glyphs.

### 2. CJK Font Structure

```cpp
struct CJKFont {
    const uint8_t *bitmap;    // Packed 1-bit-per-pixel bitmap data (PROGMEM)
    const CJKGlyph *glyphs;   // Glyph table sorted by codepoint (for binary search)
    uint16_t glyphCount;
    uint8_t width, height;     // Fixed cell dimensions
    uint8_t xAdvance;          // Horizontal cursor advance
    int8_t yOffset;            // Vertical offset from baseline (negative = above)
};
```

All CJK glyphs are fixed-width (square cells). Lookup is O(log n) binary search by Unicode codepoint.

### 3. Font Size Pairings

CJK cell sizes are matched to Latin capital letter 'A' height for visual consistency:

| Latin Font | Latin 'A' Height | CJK Cell | CJK Render | yOffset | xAdvance |
|------------|-------------------|----------|------------|---------|----------|
| FreeSans 12pt | 18px | 18px | 25px TTF | -16 | 19 |
| FreeSans 9pt | 13px | 13px | 18px TTF | -12 | 14 |
| FreeSans 6pt | 9px | 13px* | 18px TTF | -12 | 14 |

\* Small CJK font uses 13px cell (not 9px) because CJK characters with many strokes are unreadable below ~12px.

### 4. Character Coverage (~1071 glyphs per size)

- **Hiragana**: U+3041–U+3096 (83 characters)
- **Katakana**: U+30A1–U+30FA + ー (91 characters)
- **Halfwidth Katakana**: U+FF65–U+FF9F
- **CJK Punctuation**: 。、・「」『』（）【】〜 etc.
- **Fullwidth ASCII**: digits (U+FF10–FF19), uppercase (U+FF21–FF3A), lowercase (U+FF41–FF5A)
- **Fullwidth Punctuation**: ？！，．：；＠＃＄％＆ etc.
- **Ideographic Space**: U+3000 (rendered as blank glyph for correct xAdvance)
- **Currency Symbols**: ¢ £ ¥ ￠ ￡ ￥ (missing from Win1251)
- **Math/Science**: ² ³ × ÷ ¼ ½ ¾ ℃
- **Card Suits / Music**: ♠ ♣ ♥ ♦ ♪
- **Arrows / Shapes**: → ← ↑ ↓ ○ ● ◎ △ ▲ □ ■ ★ ☆ etc.
- **Kanji**: ~650 most frequent (from newspaper/web corpus frequency lists)

### 5. Text Rendering Pipeline

#### `decodeUTF8()` (AppletFont.cpp)
1. Collects UTF-8 bytes into complete characters
2. Attempts Win1251 mapping via `applyEncoding()`
3. If unmapped (`\x1A`) and encoding is `JAPANESE`: looks up codepoint in CJK font
4. If found: encodes as 3-byte escape sequence
5. If not found: character is dropped (SUB)

#### `write()` override (Applet.cpp)
State machine intercepting the byte stream:
- State 0: normal character → `GFX::write(c)`. If `\x1B` → state 1
- State 1: store high byte → state 2
- State 2: decode glyph index, call `drawCJKGlyph()`, advance cursor → state 0

#### `printWrapped()` (Applet.cpp)
CJK-aware word wrapping:
- Each CJK character is treated as an individual wrap point (no spaces between CJK words)
- Accumulated Latin text before a CJK character is flushed with width checking
- CJK characters check remaining line width before rendering

#### `getMixedTextWidth()` (Applet.cpp)
Width calculation for mixed Latin+CJK strings:
- Scans for `\x1B` escape sequences
- Latin segments measured via `getTextBounds()`
- CJK characters use `cjkFont->xAdvance`

### 6. Header Layout Adjustments

The header `padDivH` was increased from 2 to 5 to accommodate the taller CJK glyphs in the status bar area. The battery icon is sized to match the Latin `fontSmall` line height and vertically centered between the header divider lines.

### 7. NodeList Card Layout

A 2px `lineGap` was added between the short name (fontMedium) and long name (fontSmall) lines in node list cards, improving readability with CJK text.

## Font Generation

### Prerequisites

```bash
pip install Pillow
```

### Usage

```bash
python3 tools/generate_cjk_font.py <ttf_path> <cell_size> <output.h> [options]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--var-prefix PREFIX` | C variable name prefix | `CJKFont<cell_size>px` |
| `--render-size SIZE` | TTF rendering size in pixels | `cell_size * 1.4` |
| `--y-offset OFFSET` | Glyph Y offset from baseline | `-cell_size` |
| `--x-advance ADVANCE` | Horizontal cursor advance | `cell_size + 1` |

### Generating All Three Sizes

```bash
# Large (paired with FreeSans 12pt)
python3 tools/generate_cjk_font.py NotoSansJP.ttf 18 CJKFont_18px.h \
    --var-prefix CJKFont18px --render-size 25 --y-offset -16 --x-advance 19

# Medium (paired with FreeSans 9pt)
python3 tools/generate_cjk_font.py NotoSansJP.ttf 13 CJKFont_13px.h \
    --var-prefix CJKFont13px --render-size 18 --y-offset -12 --x-advance 14

# Small (paired with FreeSans 6pt — uses 13px cell for readability)
python3 tools/generate_cjk_font.py NotoSansJP.ttf 13 CJKFont_12px.h \
    --var-prefix CJKFont12px --render-size 18 --y-offset -12 --x-advance 14
```

The TTF font file (`NotoSansJP-Regular.ttf` or similar) should be placed in `tools/`.

### How Font Generation Works

1. Loads TTF font at `render_size` (larger than `cell_size` for better detail)
2. Renders each codepoint to a grayscale image
3. Finds the bounding box of actual glyph pixels
4. Scales down (LANCZOS) to fit the `cell_size` cell
5. Centers horizontally and vertically in the cell
6. Binarizes with threshold > 96
7. Packs to 1-bit-per-pixel bitmap (MSB first, row-major)
8. Outputs C header with PROGMEM arrays

## Adding to a New Variant

To enable CJK support on a new device variant:

1. **platformio.ini**: Create an `inkhud` build environment (see `t-echo-plus` example)

2. **nicheGraphics.h**: Use the JP font macros:
   ```cpp
   InkHUD::Applet::fontLarge = FREESANS_12PT_JP;
   InkHUD::Applet::fontMedium = FREESANS_9PT_JP;
   InkHUD::Applet::fontSmall = FREESANS_6PT_JP;
   ```

No other code changes are needed — the CJK rendering system is fully integrated into the InkHUD core.

## Memory Usage

Approximate flash usage for all three CJK font sizes (~1071 glyphs each):

| Font | Bitmap | Glyph Table | Total |
|------|--------|-------------|-------|
| 18px (large) | 42.9 KB | 4.2 KB | 47.1 KB |
| 13px (medium) | 23.0 KB | 4.2 KB | 27.2 KB |
| 13px (small) | 23.0 KB | 4.2 KB | 27.2 KB |
| **Total** | **88.9 KB** | **12.6 KB** | **~101 KB** |

This fits comfortably within the T-Echo Plus 2MB flash.
