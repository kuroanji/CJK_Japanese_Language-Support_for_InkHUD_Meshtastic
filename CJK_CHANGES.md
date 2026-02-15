# CJK Implementation — Code Changes

## New Files

### `src/graphics/niche/Fonts/CJK/CJKFont.h`
CJK font data structures and binary search lookup function.

### `src/graphics/niche/Fonts/CJK/CJKFont_DotGothic18px.h`
Generated font data (DotGothic16, 18px cell, 2526 glyphs, ~116KB).

### `tools/generate_cjk_font.py`
Python script to convert TTF → C header with packed bitmap data.

### `tools/joyo_kanji.txt`
List of 2136 Joyo kanji for font generation.

### `tools/DotGothic16.ttf`
Source font file (pixel-optimized Japanese font).

---

## Modified Files

### `src/graphics/niche/InkHUD/AppletFont.h`

```diff
+#include "graphics/niche/Fonts/CJK/CJKFont.h"

 enum Encoding {
     ASCII,
     WINDOWS_1250,
     WINDOWS_1251,
     WINDOWS_1252,
     WINDOWS_1253,
+    JAPANESE,
 };

+AppletFont(const GFXfont &adafruitGFXFont, Encoding encoding, int8_t paddingTop, int8_t paddingBottom,
+           const CJKFont *cjkFont, float cjkScale = 1.0f);

-const GFXfont *gfxFont = NULL;
+const GFXfont *gfxFont = NULL;
+const CJKFont *cjkFont = nullptr;
+float cjkScale = 1.0f;

+// Japanese font macros (end of file)
+#include "graphics/niche/Fonts/CJK/CJKFont_DotGothic18px.h"
+#define FREESANS_12PT_JP InkHUD::AppletFont(FreeSans12pt_Win1251, InkHUD::AppletFont::JAPANESE, -3, 1, &CJKFontDotGothic18px, 1.0f)
+#define FREESANS_9PT_JP InkHUD::AppletFont(FreeSans9pt_Win1251, InkHUD::AppletFont::JAPANESE, -2, -1, &CJKFontDotGothic18px, 0.72f)
+#define FREESANS_6PT_JP InkHUD::AppletFont(FreeSans6pt_Win1251, InkHUD::AppletFont::JAPANESE, -1, -2, &CJKFontDotGothic18px, 0.67f)
```

### `src/graphics/niche/InkHUD/AppletFont.cpp`

```diff
+// New constructor
+InkHUD::AppletFont::AppletFont(const GFXfont &adafruitGFXFont, Encoding encoding, int8_t paddingTop, int8_t paddingBottom,
+                                const CJKFont *cjkFont, float cjkScale)
+    : AppletFont(adafruitGFXFont, encoding, paddingTop, paddingBottom)
+{
+    this->cjkFont = cjkFont;
+    this->cjkScale = cjkScale;
+}

 // In decodeUTF8(), replace:
-decoded += applyEncoding(utf8Char);
+char mapped = applyEncoding(utf8Char);
+
+// CJK escape encoding
+if (mapped == '\x1A' && encoding == JAPANESE && cjkFont != nullptr && utf8Char.length() > 1) {
+    uint32_t cp = toUtf32(utf8Char);
+    int16_t glyphIdx = NicheGraphics::cjkLookup(cjkFont, (uint16_t)cp);
+    if (glyphIdx >= 0) {
+        decoded += '\x1B';
+        decoded += (char)((glyphIdx / 254) + 1);
+        decoded += (char)((glyphIdx % 254) + 1);
+        mapped = 0;
+    }
+}
+if (mapped != 0)
+    decoded += mapped;

 // In applyEncoding():
-else if (encoding == WINDOWS_1251) {
+else if (encoding == WINDOWS_1251 || encoding == JAPANESE) {
```

### `src/graphics/niche/InkHUD/Applet.h`

```diff
+size_t write(uint8_t c) override;

+uint16_t getMixedTextWidth(const char *text);
+void drawCJKGlyph(int16_t x, int16_t y, uint16_t glyphIndex);

+// Private:
+uint8_t cjkEscState = 0;
+uint8_t cjkHighByte = 0;
```

### `src/graphics/niche/InkHUD/Applet.cpp`

```diff
+// CJK-aware character output
+size_t InkHUD::Applet::write(uint8_t c)
+{
+    if (cjkEscState == 0) {
+        if (c == 0x1B && currentFont.cjkFont != nullptr) {
+            cjkEscState = 1;
+            return 1;
+        }
+        return GFX::write(c);
+    }
+    if (cjkEscState == 1) {
+        cjkHighByte = c;
+        cjkEscState = 2;
+        return 1;
+    }
+    // Got both bytes, render glyph
+    uint16_t glyphIndex = (uint16_t)(cjkHighByte - 1) * 254 + (c - 1);
+    drawCJKGlyph(getCursorX(), getCursorY(), glyphIndex);
+    setCursor(getCursorX() + (int16_t)(currentFont.cjkFont->xAdvance * currentFont.cjkScale + 0.5f), getCursorY());
+    cjkEscState = 0;
+    return 1;
+}

 // In printAt(), after getTextBounds:
+if (currentFont.cjkFont)
+    textWidth = getMixedTextWidth(text);

+// Width calculation with CJK escapes
+uint16_t InkHUD::Applet::getMixedTextWidth(const char *text)
+{
+    if (!currentFont.cjkFont)
+        return getTextWidth(text);
+
+    uint16_t totalWidth = 0;
+    std::string normalChars;
+    const char *p = text;
+
+    while (*p) {
+        if ((uint8_t)*p == 0x1B && *(p + 1) && *(p + 2)) {
+            if (!normalChars.empty()) {
+                totalWidth += getTextWidth(normalChars);
+                normalChars.clear();
+            }
+            totalWidth += (uint16_t)(currentFont.cjkFont->xAdvance * currentFont.cjkScale + 0.5f);
+            p += 3;
+        } else {
+            normalChars += *p;
+            p++;
+        }
+    }
+    if (!normalChars.empty())
+        totalWidth += getTextWidth(normalChars);
+    return totalWidth;
+}

+// Bilinear-scaled CJK glyph rendering
+static inline uint8_t getCJKPixel(const uint8_t *bitmap, uint32_t bitmapOffset, uint8_t w, uint8_t col, uint8_t row)
+{
+    uint16_t bitIndex = (uint16_t)row * w + col;
+    uint32_t byteIndex = bitmapOffset + (bitIndex / 8);
+    uint8_t bitMask = 0x80 >> (bitIndex % 8);
+    return (pgm_read_byte(&bitmap[byteIndex]) & bitMask) ? 1 : 0;
+}
+
+void InkHUD::Applet::drawCJKGlyph(int16_t x, int16_t y, uint16_t glyphIndex)
+{
+    const CJKFont *font = currentFont.cjkFont;
+    if (!font || glyphIndex >= font->glyphCount)
+        return;
+
+    uint32_t bitmapOffset = pgm_read_dword(&font->glyphs[glyphIndex].bitmapOffset);
+    uint8_t srcW = font->width;
+    uint8_t srcH = font->height;
+    int8_t yOff = font->yOffset;
+    float scale = currentFont.cjkScale;
+
+    uint8_t destW = (uint8_t)(srcW * scale + 0.5f);
+    uint8_t destH = (uint8_t)(srcH * scale + 0.5f);
+    int16_t drawY = y + (int16_t)(yOff * scale);
+
+    // Fast path: native size
+    if (scale >= 0.99f && scale <= 1.01f) {
+        for (uint8_t row = 0; row < srcH; row++) {
+            for (uint8_t col = 0; col < srcW; col++) {
+                if (getCJKPixel(font->bitmap, bitmapOffset, srcW, col, row))
+                    drawPixel(x + col, drawY + row, BLACK);
+            }
+        }
+        return;
+    }
+
+    // Bilinear interpolation
+    for (uint8_t dy = 0; dy < destH; dy++) {
+        float srcY = dy / scale;
+        uint8_t y0 = (uint8_t)srcY;
+        uint8_t y1 = (y0 + 1 < srcH) ? y0 + 1 : y0;
+        float fy = srcY - y0;
+
+        for (uint8_t dx = 0; dx < destW; dx++) {
+            float srcX = dx / scale;
+            uint8_t x0 = (uint8_t)srcX;
+            uint8_t x1 = (x0 + 1 < srcW) ? x0 + 1 : x0;
+            float fx = srcX - x0;
+
+            uint8_t p00 = getCJKPixel(font->bitmap, bitmapOffset, srcW, x0, y0);
+            uint8_t p10 = getCJKPixel(font->bitmap, bitmapOffset, srcW, x1, y0);
+            uint8_t p01 = getCJKPixel(font->bitmap, bitmapOffset, srcW, x0, y1);
+            uint8_t p11 = getCJKPixel(font->bitmap, bitmapOffset, srcW, x1, y1);
+
+            float val = (1-fx)*(1-fy)*p00 + fx*(1-fy)*p10 + (1-fx)*fy*p01 + fx*fy*p11;
+            if (val > 0.5f)
+                drawPixel(x + dx, drawY + dy, BLACK);
+        }
+    }
+}
```

### `variants/nrf52840/t-echo-plus/nicheGraphics.h`

```diff
-InkHUD::Applet::fontLarge = FREESANS_12PT_WIN1252;
-InkHUD::Applet::fontMedium = FREESANS_9PT_WIN1252;
-InkHUD::Applet::fontSmall = FREESANS_6PT_WIN1252;
+InkHUD::Applet::fontLarge = FREESANS_12PT_JP;
+InkHUD::Applet::fontMedium = FREESANS_9PT_JP;
+InkHUD::Applet::fontSmall = FREESANS_6PT_JP;
```
