# CJK (Japanese) Support for InkHUD

This document describes how to add Japanese language support to InkHUD on T-Echo Plus devices.

## Overview

InkHUD's font system uses 8-bit extended ASCII encodings (Windows-125x), limited to 255 glyphs. Japanese requires ~2500+ characters (Hiragana, Katakana, Kanji). This implementation adds a parallel CJK bitmap font system that coexists with existing Latin/Cyrillic fonts.

**Approach:** CJK characters are encoded as 3-byte escape sequences in the text pipeline, then rendered via a custom bitmap font with bilinear scaling.

## Architecture

### Text Flow

```
UTF-8 input
    ↓
decodeUTF8() → ASCII/Cyrillic: Win1251 single-byte encoding
             → CJK: 3-byte escape sequence (\x1B + high + low)
    ↓
print() → write() override intercepts escape sequences
    ↓
drawCJKGlyph() → bilinear-scaled bitmap rendering
```

### Escape Encoding

CJK characters are encoded as:
- Byte 0: `\x1B` (ESC)
- Byte 1: `(glyphIndex / 254) + 1`
- Byte 2: `(glyphIndex % 254) + 1`

This avoids `\x00` (string terminator) and supports up to 64,516 glyphs.

## Files to Create

### 1. `src/graphics/niche/Fonts/CJK/CJKFont.h`

```cpp
#pragma once
#include <stdint.h>
#include <Arduino.h>

namespace NicheGraphics
{

struct CJKGlyph {
    uint16_t codepoint;    // Unicode codepoint (sorted for binary search)
    uint32_t bitmapOffset; // Byte offset into bitmap data
};

struct CJKFont {
    const uint8_t *bitmap;    // Packed 1bpp bitmap data (PROGMEM)
    const CJKGlyph *glyphs;   // Glyph table sorted by codepoint
    uint16_t glyphCount;
    uint8_t width;            // Fixed glyph width in pixels
    uint8_t height;           // Fixed glyph height in pixels
    uint8_t xAdvance;         // Horizontal cursor advance
    int8_t yOffset;           // Y offset from baseline (negative = above)
};

// Binary search for codepoint, returns glyph index or -1
inline int16_t cjkLookup(const CJKFont *font, uint16_t codepoint)
{
    if (!font || !font->glyphs || font->glyphCount == 0)
        return -1;

    int16_t lo = 0, hi = font->glyphCount - 1;
    while (lo <= hi) {
        int16_t mid = lo + (hi - lo) / 2;
        uint16_t midCp = pgm_read_word(&font->glyphs[mid].codepoint);
        if (midCp == codepoint) return mid;
        else if (midCp < codepoint) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}

} // namespace NicheGraphics
```

### 2. `tools/generate_cjk_font.py`

Font generator script that converts TTF → C header. See `tools/generate_cjk_font.py` for full implementation.

Usage:
```bash
python3 tools/generate_cjk_font.py <ttf_file> <cell_size> <output.h> [--var-prefix NAME]
```

### 3. `tools/joyo_kanji.txt`

List of 2136 Joyo kanji (one per line). Download from:
https://raw.githubusercontent.com/scriptin/topokanji/master/joyo.txt

### 4. Generated Font Header

```bash
# Download DotGothic16 (pixel-optimized Japanese font)
curl -L "https://github.com/fontworks-fonts/DotGothic16/raw/master/fonts/ttf/DotGothic16-Regular.ttf" \
    -o tools/DotGothic16.ttf

# Generate 18px font
python3 tools/generate_cjk_font.py tools/DotGothic16.ttf 18 \
    src/graphics/niche/Fonts/CJK/CJKFont_DotGothic18px.h \
    --var-prefix CJKFontDotGothic18px
```

## Files to Modify

### 1. `src/graphics/niche/InkHUD/AppletFont.h`

Add:
```cpp
#include "graphics/niche/Fonts/CJK/CJKFont.h"

// In Encoding enum:
JAPANESE, // Win1251 (Cyrillic/Latin) + CJK bitmap font

// New constructor:
AppletFont(const GFXfont &adafruitGFXFont, Encoding encoding, int8_t paddingTop, int8_t paddingBottom,
           const CJKFont *cjkFont, float cjkScale = 1.0f);

// New members:
const CJKFont *cjkFont = nullptr;
float cjkScale = 1.0f;

// Japanese font macros (at end of file):
#include "graphics/niche/Fonts/CJK/CJKFont_DotGothic18px.h"
#define FREESANS_12PT_JP InkHUD::AppletFont(FreeSans12pt_Win1251, InkHUD::AppletFont::JAPANESE, -3, 1, &CJKFontDotGothic18px, 1.0f)
#define FREESANS_9PT_JP InkHUD::AppletFont(FreeSans9pt_Win1251, InkHUD::AppletFont::JAPANESE, -2, -1, &CJKFontDotGothic18px, 0.72f)
#define FREESANS_6PT_JP InkHUD::AppletFont(FreeSans6pt_Win1251, InkHUD::AppletFont::JAPANESE, -1, -2, &CJKFontDotGothic18px, 0.67f)
```

### 2. `src/graphics/niche/InkHUD/AppletFont.cpp`

Add constructor:
```cpp
InkHUD::AppletFont::AppletFont(const GFXfont &adafruitGFXFont, Encoding encoding, int8_t paddingTop, int8_t paddingBottom,
                                const CJKFont *cjkFont, float cjkScale)
    : AppletFont(adafruitGFXFont, encoding, paddingTop, paddingBottom)
{
    this->cjkFont = cjkFont;
    this->cjkScale = cjkScale;
}
```

Modify `decodeUTF8()` — after `applyEncoding()`, add CJK escape encoding.

Modify `applyEncoding()` — add `|| encoding == JAPANESE` to Win1251 case.

### 3. `src/graphics/niche/InkHUD/Applet.h`

Add:
```cpp
size_t write(uint8_t c) override;
uint16_t getMixedTextWidth(const char *text);
void drawCJKGlyph(int16_t x, int16_t y, uint16_t glyphIndex);

// Private state:
uint8_t cjkEscState = 0;
uint8_t cjkHighByte = 0;
```

### 4. `src/graphics/niche/InkHUD/Applet.cpp`

Implement:
- `write()` — intercept ESC sequences, call `drawCJKGlyph()`
- `getMixedTextWidth()` — calculate width with CJK escapes
- `drawCJKGlyph()` — bilinear-scaled bitmap rendering

Modify `printAt()` — use `getMixedTextWidth()` when CJK font active.

### 5. `variants/nrf52840/t-echo-plus/nicheGraphics.h`

Change font assignments:
```cpp
InkHUD::Applet::fontLarge = FREESANS_12PT_JP;
InkHUD::Applet::fontMedium = FREESANS_9PT_JP;
InkHUD::Applet::fontSmall = FREESANS_6PT_JP;
```

## Font Sizes

| Font | Scale | Result |
|------|-------|--------|
| fontLarge | 1.0 | 18px native |
| fontMedium | 0.72 | 13px |
| fontSmall | 0.67 | 12px |

## Character Coverage

- Hiragana: U+3041–U+3096 (83 chars)
- Katakana: U+30A1–U+30FC (90 chars)
- CJK Punctuation: 。、・「」『』 etc.
- Fullwidth ASCII: ０-９、Ａ-Ｚ、ａ-ｚ
- Joyo Kanji: 2136 chars
- **Total: ~2526 glyphs**

## Flash Usage

- Font data: ~116 KB
- Total firmware: ~96% of 815 KB

## Build

```bash
pio run -e t-echo-plus-inkhud
```
