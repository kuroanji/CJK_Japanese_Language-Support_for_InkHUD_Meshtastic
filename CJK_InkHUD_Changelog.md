# CJK InkHUD — Detailed File Changelog

Every change made to implement CJK (Japanese) support in InkHUD, shown as before/after diffs.

---

## New Files

These files did not exist before and were created from scratch:

- `src/graphics/niche/Fonts/CJK/CJKFont.h` — CJK font data structures and binary search
- `src/graphics/niche/Fonts/CJK/CJKFont_18px.h` — Auto-generated 18px CJK bitmap font (large)
- `src/graphics/niche/Fonts/CJK/CJKFont_13px.h` — Auto-generated 13px CJK bitmap font (medium)
- `src/graphics/niche/Fonts/CJK/CJKFont_12px.h` — Auto-generated 13px CJK bitmap font (small, named 12px for legacy reasons)
- `tools/generate_cjk_font.py` — Python script for CJK font generation from TTF
- `docs/CJK_InkHUD_Implementation.md` — Implementation documentation
- `docs/CJK_InkHUD_Changelog.md` — This file

---

## `variants/nrf52840/t-echo-plus/platformio.ini`

**What:** Added InkHUD build environment for T-Echo Plus.

### Added (appended after existing `[env:t-echo-plus]` section):

```ini
[env:t-echo-plus-inkhud]
extends = nrf52840_base, inkhud
board = t-echo
board_level = pr
board_check = true
debug_tool = jlink
build_flags =
  ${nrf52840_base.build_flags}
  ${inkhud.build_flags}
  -DTTGO_T_ECHO_PLUS
  -Ivariants/nrf52840/t-echo-plus
  -DEINK_DISPLAY_MODEL=GxEPD2_154_D67
  -DEINK_WIDTH=200
  -DEINK_HEIGHT=200
  -DUSE_EINK
  -DUSE_EINK_DYNAMICDISPLAY
  -DEINK_LIMIT_FASTREFRESH=20
  -DEINK_BACKGROUND_USES_FAST
  -DI2C_NO_RESCAN
build_src_filter =
  ${nrf52_base.build_src_filter}
  ${inkhud.build_src_filter}
  +<../variants/nrf52840/t-echo-plus>
lib_deps =
  ${inkhud.lib_deps}
  ${nrf52840_base.lib_deps}
  https://github.com/meshtastic/GxEPD2/archive/55f618961db45a23eff0233546430f1e5a80f63a.zip
  lewisxhe/PCF8563_Library@^1.0.1
  adafruit/Adafruit DRV2605 Library@1.2.4
```

---

## `variants/nrf52840/t-echo-plus/nicheGraphics.h`

**What:** Changed font assignments from Win1252 to Japanese (CJK) fonts.

### Before:
```cpp
InkHUD::Applet::fontLarge = FREESANS_12PT_WIN1252;
InkHUD::Applet::fontMedium = FREESANS_9PT_WIN1252;
InkHUD::Applet::fontSmall = FREESANS_6PT_WIN1252;
```

### After:
```cpp
// [CJK] Japanese fonts: Win1251 (Latin/Cyrillic) + CJK bitmap (Hiragana/Katakana/Kanji)
InkHUD::Applet::fontLarge = FREESANS_12PT_JP;
InkHUD::Applet::fontMedium = FREESANS_9PT_JP;
InkHUD::Applet::fontSmall = FREESANS_6PT_JP;
```

---

## `src/graphics/niche/InkHUD/AppletFont.h`

**What:** Added JAPANESE encoding enum, CJK font pointer, CJK constructor, CJK font includes and macros.

### Change 1 — Added CJKFont.h include

#### Before:
```cpp
#include <GFX.h> // GFXRoot drawing lib

namespace NicheGraphics::InkHUD
```

#### After:
```cpp
#include <GFX.h> // GFXRoot drawing lib

#include "graphics/niche/Fonts/CJK/CJKFont.h"

namespace NicheGraphics::InkHUD
```

### Change 2 — Added JAPANESE to Encoding enum

#### Before:
```cpp
enum Encoding {
    ASCII,
    WINDOWS_1250,
    WINDOWS_1251,
    WINDOWS_1252,
    WINDOWS_1253,
};
```

#### After:
```cpp
enum Encoding {
    ASCII,
    WINDOWS_1250,
    WINDOWS_1251,
    WINDOWS_1252,
    WINDOWS_1253,
    JAPANESE, // Win1251 (Cyrillic/Latin) + CJK bitmap font for Japanese
};
```

### Change 3 — Added CJK constructor overload

#### Before:
```cpp
AppletFont();
AppletFont(const GFXfont &adafruitGFXFont, Encoding encoding = ASCII, int8_t paddingTop = 0, int8_t paddingBottom = 0);
```

#### After:
```cpp
AppletFont();
AppletFont(const GFXfont &adafruitGFXFont, Encoding encoding = ASCII, int8_t paddingTop = 0, int8_t paddingBottom = 0);
AppletFont(const GFXfont &adafruitGFXFont, Encoding encoding, int8_t paddingTop, int8_t paddingBottom,
           const CJKFont *cjkFont);
```

### Change 4 — Added CJK font pointer member

#### Before:
```cpp
const GFXfont *gfxFont = NULL;       // Default value: in-built AdafruitGFX font
```

#### After:
```cpp
const GFXfont *gfxFont = NULL;       // Default value: in-built AdafruitGFX font
const CJKFont *cjkFont = nullptr;    // Optional CJK bitmap font (for Japanese encoding)
```

### Change 5 — Added Japanese font macros (appended after Greek section)

#### Before:
(nothing after Greek macros, just `#endif`)

#### After:
```cpp
// Japanese (Cyrillic + CJK)
// Reuses Win1251 GFXfont for ASCII/Cyrillic, adds CJK bitmap font for Japanese characters
// CJK cell sizes are matched to Latin 'A' height; small font uses 13px cell for readability
// See docs/CJK_InkHUD_Implementation.md for details
#include "graphics/niche/Fonts/CJK/CJKFont_18px.h"
#include "graphics/niche/Fonts/CJK/CJKFont_13px.h"
#include "graphics/niche/Fonts/CJK/CJKFont_12px.h"
#define FREESANS_12PT_JP InkHUD::AppletFont(FreeSans12pt_Win1251, InkHUD::AppletFont::JAPANESE, -3, 1, &CJKFont18px)
#define FREESANS_9PT_JP InkHUD::AppletFont(FreeSans9pt_Win1251, InkHUD::AppletFont::JAPANESE, -2, -1, &CJKFont13px)
#define FREESANS_6PT_JP InkHUD::AppletFont(FreeSans6pt_Win1251, InkHUD::AppletFont::JAPANESE, -1, -2, &CJKFont12px)
```

---

## `src/graphics/niche/InkHUD/AppletFont.cpp`

**What:** Added CJK delegating constructor, JAPANESE handling in applyEncoding(), CJK escape encoding in decodeUTF8().

### Change 1 — Added CJK constructor (after existing constructor)

#### Added:
```cpp
InkHUD::AppletFont::AppletFont(const GFXfont &adafruitGFXFont, Encoding encoding, int8_t paddingTop, int8_t paddingBottom,
                                const CJKFont *cjkFont)
    : AppletFont(adafruitGFXFont, encoding, paddingTop, paddingBottom)
{
    this->cjkFont = cjkFont;
}
```

### Change 2 — JAPANESE shares Win1251 encoding path

#### Before:
```cpp
else if (encoding == WINDOWS_1251) {
```

#### After:
```cpp
else if (encoding == WINDOWS_1251 || encoding == JAPANESE) {
```

### Change 3 — CJK escape encoding in decodeUTF8() (after `applyEncoding()` call)

#### Before:
```cpp
        char mapped = applyEncoding(utf8Char);

        if (mapped != 0)
            decoded += mapped;
```

#### After:
```cpp
        char mapped = applyEncoding(utf8Char);

        // [CJK] If unmapped by Win1251 and we have a CJK font, encode as 3-byte escape.
        // This allows CJK characters (and symbols missing from Win1251 like £ ¥) to pass
        // through the 8-bit text pipeline. See docs/CJK_InkHUD_Implementation.md
        if (mapped == '\x1A' && encoding == JAPANESE && cjkFont != nullptr && utf8Char.length() > 1) {
            uint32_t cp = toUtf32(utf8Char);
            int16_t glyphIdx = NicheGraphics::cjkLookup(cjkFont, (uint16_t)cp);
            if (glyphIdx >= 0) {
                // Encode as 3-byte escape: ESC + high + low (avoiding \x00)
                decoded += '\x1B';
                decoded += (char)((glyphIdx / 254) + 1);
                decoded += (char)((glyphIdx % 254) + 1);
                mapped = 0; // Signal: already handled
            }
        }

        if (mapped != 0)
            decoded += mapped;
```

---

## `src/graphics/niche/InkHUD/Applet.h`

**What:** Added write() override, CJK helper methods, CJK state variables.

### Change 1 — Added write() override in public section

#### Before:
```cpp
    const char *name = nullptr;

  protected:
```

#### After:
```cpp
    const char *name = nullptr;

    size_t write(uint8_t c) override; // CJK-aware character output

  protected:
```

### Change 2 — Added CJK helper methods in protected section

#### Before:
```cpp
    uint16_t getTextWidth(const char *text);
    uint32_t getWrappedTextHeight(...);
```

#### After:
```cpp
    uint16_t getTextWidth(const char *text);
    uint16_t getMixedTextWidth(const char *text); // Width calculation accounting for CJK escape sequences
    void drawCJKGlyph(int16_t x, int16_t y, uint16_t glyphIndex); // Render one CJK glyph via drawPixel
    uint32_t getWrappedTextHeight(...);
```

### Change 3 — Added CJK state variables in private section

#### Before:
```cpp
    AppletFont currentFont;

    // As set by setCrop
```

#### After:
```cpp
    AppletFont currentFont;

    // CJK escape sequence state (for write() override)
    uint8_t cjkEscState = 0;  // 0=normal, 1=got ESC, 2=got high byte
    uint8_t cjkHighByte = 0;

    // As set by setCrop
```

---

## `src/graphics/niche/InkHUD/Applet.cpp`

**What:** Added write(), drawCJKGlyph(), getMixedTextWidth(), CJK-aware printAt/printWrapped, increased header padding.

### Change 1 — Added write() override (after constructor)

#### Added:
```cpp
// CJK-aware character output
// Intercepts ESC escape sequences encoding CJK glyph indices
// For normal characters, delegates to GFX::write()
size_t InkHUD::Applet::write(uint8_t c)
{
    // State machine for 3-byte CJK escape: \x1B + high + low
    if (cjkEscState == 0) {
        if (c == 0x1B && currentFont.cjkFont != nullptr) {
            cjkEscState = 1;
            return 1;
        }
        return GFX::write(c);
    }

    if (cjkEscState == 1) {
        cjkHighByte = c;
        cjkEscState = 2;
        return 1;
    }

    // cjkEscState == 2: got both bytes, render CJK glyph
    uint16_t glyphIndex = (uint16_t)(cjkHighByte - 1) * 254 + (c - 1);
    drawCJKGlyph(getCursorX(), getCursorY(), glyphIndex);
    setCursor(getCursorX() + currentFont.cjkFont->xAdvance, getCursorY());
    cjkEscState = 0;
    return 1;
}
```

### Change 2 — CJK-aware width in printAt()

#### Before:
```cpp
void InkHUD::Applet::printAt(...)
{
    int16_t textOffsetX, textOffsetY;
    uint16_t textWidth, textHeight;
    getTextBounds(text, 0, 0, &textOffsetX, &textOffsetY, &textWidth, &textHeight);

    int16_t cursorX = 0;
```

#### After:
```cpp
void InkHUD::Applet::printAt(...)
{
    // Measure text width, accounting for CJK escape sequences
    int16_t textOffsetX, textOffsetY;
    uint16_t textWidth, textHeight;
    getTextBounds(text, 0, 0, &textOffsetX, &textOffsetY, &textWidth, &textHeight);

    // Override width with CJK-aware calculation if CJK font is active
    if (currentFont.cjkFont)
        textWidth = getMixedTextWidth(text);

    int16_t cursorX = 0;
```

### Change 3 — Added getMixedTextWidth() (after getTextWidth)

#### Added:
```cpp
// Get text width accounting for CJK escape sequences (\x1B + 2 bytes)
uint16_t InkHUD::Applet::getMixedTextWidth(const char *text)
{
    if (!currentFont.cjkFont)
        return getTextWidth(text);

    uint16_t totalWidth = 0;
    std::string normalChars;
    const char *p = text;

    while (*p) {
        if ((uint8_t)*p == 0x1B && *(p + 1) && *(p + 2)) {
            if (!normalChars.empty()) {
                totalWidth += getTextWidth(normalChars);
                normalChars.clear();
            }
            totalWidth += currentFont.cjkFont->xAdvance;
            p += 3;
        } else {
            normalChars += *p;
            p++;
        }
    }

    if (!normalChars.empty())
        totalWidth += getTextWidth(normalChars);

    return totalWidth;
}
```

### Change 4 — Added drawCJKGlyph() (after getMixedTextWidth)

#### Added:
```cpp
// Render a single CJK glyph from the bitmap font at the specified position
void InkHUD::Applet::drawCJKGlyph(int16_t x, int16_t y, uint16_t glyphIndex)
{
    const CJKFont *font = currentFont.cjkFont;
    if (!font || glyphIndex >= font->glyphCount)
        return;

    uint16_t bitmapOffset = pgm_read_word(&font->glyphs[glyphIndex].bitmapOffset);
    uint8_t w = font->width;
    uint8_t h = font->height;
    int8_t yOff = font->yOffset;

    int16_t drawY = y + yOff;

    for (uint8_t row = 0; row < h; row++) {
        for (uint8_t col = 0; col < w; col++) {
            uint16_t bitIndex = (uint16_t)row * w + col;
            uint16_t byteIndex = bitmapOffset + (bitIndex / 8);
            uint8_t bitMask = 0x80 >> (bitIndex % 8);

            uint8_t bitmapByte = pgm_read_byte(&font->bitmap[byteIndex]);
            if (bitmapByte & bitMask)
                drawPixel(x + col, drawY + row, BLACK);
        }
    }
}
```

### Change 5 — CJK-aware word wrapping in printWrapped()

#### Before:
```cpp
        // CJK escape sequence handling did not exist
        // Only space/newline triggered word wrapping
```

#### After (inserted before the space/newline word-split logic):
```cpp
        // CJK escape sequence: treat each CJK character as its own wrappable unit
        if ((uint8_t)text[i] == 0x1B && currentFont.cjkFont && (i + 2) < text.length()) {
            // Flush any accumulated Latin text before this CJK char
            if (i > wordStart) {
                std::string segment = text.substr(wordStart, i - wordStart);
                if (!segment.empty()) {
                    // Check if segment fits on current line before printing
                    int16_t sl, st;
                    uint16_t sw, sh;
                    getTextBounds(segment.c_str(), getCursorX(), getCursorY(), &sl, &st, &sw, &sh);
                    if ((sl + sw) > left + (int16_t)width)
                        setCursor(left, getCursorY() + getFont().lineHeight());
                    print(segment.c_str());
                }
            }

            uint8_t cjkW = currentFont.cjkFont->xAdvance;

            // Wrap to next line if CJK char won't fit
            if ((getCursorX() + cjkW) > left + (int16_t)width)
                setCursor(left, getCursorY() + getFont().lineHeight());

            // Print the 3-byte CJK escape sequence via write()
            write((uint8_t)text[i]);
            write((uint8_t)text[i + 1]);
            write((uint8_t)text[i + 2]);
            i += 2;
            wordStart = i + 1;
            continue;
        }
```

### Change 6 — Increased header padding for CJK clearance

#### Before (in both `drawHeader()` and `getHeaderHeight()`):
```cpp
constexpr int16_t padDivH = 2;
```

#### After:
```cpp
constexpr int16_t padDivH = 5; // [CJK] Increased from 2 to 5 so CJK glyphs clear the top divider line
```

---

## `src/graphics/niche/InkHUD/Applets/Bases/NodeList/NodeListApplet.h`

**What:** Added gap between short name and long name lines in node card layout.

### Before:
```cpp
    // Card Dimensions
    // - for rendering and for maxCards calc
    uint8_t cardMarginH = fontSmall.lineHeight() / 2;                                // Gap between cards
    uint16_t cardH = fontMedium.lineHeight() + fontSmall.lineHeight() + cardMarginH; // Height of card
```

### After:
```cpp
    // Card Dimensions
    // - for rendering and for maxCards calc
    static constexpr uint8_t lineGap = 2;                                                        // [CJK] Gap between short name and long name for readability
    uint8_t cardMarginH = fontSmall.lineHeight() / 2;                                            // Gap between cards
    uint16_t cardH = fontMedium.lineHeight() + lineGap + fontSmall.lineHeight() + cardMarginH;   // Height of card
```

---

## `src/graphics/niche/InkHUD/Applets/Bases/NodeList/NodeListApplet.cpp`

**What:** Applied lineGap to long name line position.

### Before:
```cpp
        uint16_t lineAY = cardTopY + (fontMedium.lineHeight() / 2);
        uint16_t lineBY = cardTopY + fontMedium.lineHeight() + (fontSmall.lineHeight() / 2);
```

### After:
```cpp
        uint16_t lineAY = cardTopY + (fontMedium.lineHeight() / 2);
        uint16_t lineBY = cardTopY + fontMedium.lineHeight() + lineGap + (fontSmall.lineHeight() / 2); // [CJK] lineGap added
```

---

## `src/graphics/niche/InkHUD/WindowManager.cpp`

**What:** Battery icon sized to match Latin font height, centered vertically in header.

### Before:
```cpp
    const uint16_t batteryIconHeight = Applet::getHeaderHeight() - 2 - 2;
    const uint16_t batteryIconWidth = batteryIconHeight * 1.8;
    inkhud->getSystemApplet("BatteryIcon")
        ->getTile()
        ->setRegion(inkhud->width() - batteryIconWidth - 1, // x
                    1,                                      // y
                    batteryIconWidth + 1,                   // width
                    batteryIconHeight + 2);                 // height
```

### After:
```cpp
    // [CJK] Battery icon sized to Latin fontSmall and centered vertically in header
    const uint16_t batteryIconHeight = Applet::fontSmall.lineHeight();
    const uint16_t batteryIconWidth = batteryIconHeight * 1.8;
    const uint16_t batteryTileH = batteryIconHeight + 2;
    const uint16_t batteryTileY = (Applet::getHeaderHeight() - batteryTileH) / 2;
    inkhud->getSystemApplet("BatteryIcon")
        ->getTile()
        ->setRegion(inkhud->width() - batteryIconWidth - 1, // x
                    batteryTileY,                           // y (centered between header lines)
                    batteryIconWidth + 1,                   // width
                    batteryTileH);                          // height
```
