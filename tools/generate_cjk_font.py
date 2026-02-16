#!/usr/bin/env python3
"""
Generate CJK bitmap font headers for InkHUD from a TTF font.

Usage:
    python3 generate_cjk_font.py <ttf_path> <cell_size> <output.h> [options]

Options:
    --var-prefix PREFIX    Variable name prefix (default: CJKFont<cell_size>px)
    --render-size SIZE     TTF render size in pixels (default: cell_size * 1.4)
    --y-offset OFFSET      yOffset value for glyph positioning (default: -cell_size)
    --x-advance ADVANCE    xAdvance value for cursor movement (default: cell_size + 1)
    --max-kanji N          Maximum number of kanji to include (default: all)
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def get_japanese_codepoints(max_kanji=None):
    """Get all Japanese codepoints to include in the font."""
    codepoints = set()

    # Hiragana: U+3041-U+3096
    for cp in range(0x3041, 0x3097):
        codepoints.add(cp)

    # Katakana: U+30A1-U+30FA + prolonged sound mark
    for cp in range(0x30A1, 0x30FB):
        codepoints.add(cp)
    codepoints.add(0x30FC)

    codepoints.add(0x3000)  # Ideographic space

    for ch in "。、・「」『』（）【】〜〇々〈〉《》〒〝〞〟":
        codepoints.add(ord(ch))

    for ch in "？！，．：；＠＃＄％＆＊＋－＝＜＞／＼｜＿～＾｀":
        codepoints.add(ord(ch))

    for ch in "（）［］｛｝「」『』【】＂＇":
        codepoints.add(ord(ch))

    for cp in range(0xFF10, 0xFF1A):
        codepoints.add(cp)
    for cp in range(0xFF21, 0xFF3B):
        codepoints.add(cp)
    for cp in range(0xFF41, 0xFF5B):
        codepoints.add(cp)

    for ch in "→←↑↓○●◎△▲▽▼□■◇◆★☆※†‡":
        codepoints.add(ord(ch))

    for ch in "¢£¥￠￡￥²³×÷¼½¾℃♠♣♥♦♪":
        codepoints.add(ord(ch))

    for cp in range(0xFF65, 0xFFA0):
        codepoints.add(cp)

    # Kanji (limited if max_kanji specified)
    kanji_list = get_joyo_kanji()
    if max_kanji is not None and max_kanji < len(kanji_list):
        kanji_list = kanji_list[:max_kanji]
    for ch in kanji_list:
        codepoints.add(ord(ch))

    return sorted(codepoints)


def get_joyo_kanji():
    """Load all 2136 Joyo kanji from joyo_kanji.txt file."""
    script_dir = Path(__file__).parent
    kanji_file = script_dir / "joyo_kanji.txt"

    if not kanji_file.exists():
        print(f"Warning: {kanji_file} not found")
        return []

    kanji = []
    with open(kanji_file, 'r', encoding='utf-8') as f:
        for line in f:
            ch = line.strip()
            if ch and len(ch) == 1:
                kanji.append(ch)

    return kanji


def render_glyph(font, codepoint, cell_size, render_size):
    """Render a single glyph to a fixed-size bitmap cell."""
    char = chr(codepoint)

    try:
        bbox = font.getbbox(char)
        if bbox is None or (bbox[2] - bbox[0]) == 0:
            return None
    except Exception:
        return None

    img_size = render_size * 3
    img = Image.new('L', (img_size, img_size), 0)
    draw = ImageDraw.Draw(img)
    draw.text((render_size, render_size), char, font=font, fill=255)

    pixels = img.load()
    min_x = min_y = img_size
    max_x = max_y = 0
    found = False
    for y in range(img_size):
        for x in range(img_size):
            if pixels[x, y] > 64:
                found = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if not found:
        return None

    result = Image.new('L', (cell_size, cell_size), 0)
    actual_w = max_x - min_x + 1
    actual_h = max_y - min_y + 1

    if actual_w > cell_size or actual_h > cell_size:
        scale = min(cell_size / actual_w, cell_size / actual_h)
        crop = img.crop((min_x, min_y, max_x + 1, max_y + 1))
        new_w = max(1, int(actual_w * scale))
        new_h = max(1, int(actual_h * scale))
        crop = crop.resize((new_w, new_h), Image.LANCZOS)
        offset_x = (cell_size - new_w) // 2
        offset_y = (cell_size - new_h) // 2
        result.paste(crop, (offset_x, offset_y))
    else:
        offset_x = (cell_size - actual_w) // 2
        offset_y = (cell_size - actual_h) // 2
        crop = img.crop((min_x, min_y, max_x + 1, max_y + 1))
        result.paste(crop, (offset_x, offset_y))

    result = result.point(lambda p: 1 if p > 96 else 0, '1')

    bitmap = []
    byte_val = 0
    bit = 7
    result_pixels = result.load()
    for y in range(cell_size):
        for x in range(cell_size):
            if result_pixels[x, y]:
                byte_val |= (1 << bit)
            bit -= 1
            if bit < 0:
                bitmap.append(byte_val)
                byte_val = 0
                bit = 7

    if bit < 7:
        bitmap.append(byte_val)

    return bytes(bitmap)


def make_blank_glyph(cell_size):
    """Create an empty bitmap for invisible glyphs like fullwidth space."""
    total_bits = cell_size * cell_size
    total_bytes = (total_bits + 7) // 8
    return bytes(total_bytes)


def generate_font_header(ttf_path, cell_size, render_size, output_path, var_prefix, y_offset, x_advance, max_kanji):
    """Generate a C header file with CJK bitmap font data."""
    print(f"Loading font: {ttf_path}")
    font = ImageFont.truetype(str(ttf_path), render_size)

    codepoints = get_japanese_codepoints(max_kanji)
    kanji_count = len([cp for cp in codepoints if 0x4E00 <= cp <= 0x9FFF])
    print(f"Processing {len(codepoints)} codepoints ({kanji_count} kanji, cell={cell_size}px)...")

    force_blank = {0x3000}
    glyphs = []
    skipped = 0

    for cp in codepoints:
        if cp in force_blank:
            glyphs.append((cp, make_blank_glyph(cell_size)))
            continue

        result = render_glyph(font, cp, cell_size, render_size)
        if result is not None:
            glyphs.append((cp, result))
        else:
            skipped += 1

    print(f"  Rendered: {len(glyphs)} glyphs, skipped: {skipped}")

    glyphs.sort(key=lambda g: g[0])

    bitmap_data = bytearray()
    glyph_entries = []
    for cp, bmp in glyphs:
        offset = len(bitmap_data)
        bitmap_data.extend(bmp)
        glyph_entries.append((cp, offset))

    total_kb = (len(bitmap_data) + len(glyph_entries) * 6) / 1024
    print(f"  Bitmap: {len(bitmap_data) / 1024:.1f} KB, table: {len(glyph_entries) * 6 / 1024:.1f} KB, total: {total_kb:.1f} KB")

    with open(output_path, 'w') as f:
        f.write(f"// Auto-generated CJK bitmap font: {cell_size}px cell, {render_size}px render\n")
        f.write(f"// Source: {Path(ttf_path).name}\n")
        f.write(f"// Glyphs: {len(glyphs)} ({kanji_count} kanji), Bitmap: {len(bitmap_data)} bytes\n\n")
        f.write("#pragma once\n\n")
        f.write("#include \"graphics/niche/Fonts/CJK/CJKFont.h\"\n\n")

        f.write(f"const uint8_t {var_prefix}Bitmaps[] PROGMEM = {{\n")
        for i in range(0, len(bitmap_data), 16):
            chunk = bitmap_data[i:i + 16]
            f.write("    " + ", ".join(f"0x{b:02X}" for b in chunk) + ",\n")
        f.write("};\n\n")

        f.write(f"const NicheGraphics::CJKGlyph {var_prefix}Glyphs[] PROGMEM = {{\n")
        for cp, offset in glyph_entries:
            ch = chr(cp)
            f.write(f"    {{ 0x{cp:04X}, {offset:6d} }}, // {ch}\n")
        f.write("};\n\n")

        f.write(f"const NicheGraphics::CJKFont {var_prefix} PROGMEM = {{\n")
        f.write(f"    {var_prefix}Bitmaps,\n")
        f.write(f"    {var_prefix}Glyphs,\n")
        f.write(f"    {len(glyphs)},  // glyphCount\n")
        f.write(f"    {cell_size},    // width\n")
        f.write(f"    {cell_size},    // height\n")
        f.write(f"    {x_advance},    // xAdvance\n")
        f.write(f"    {y_offset},     // yOffset\n")
        f.write("};\n")

    print(f"  Written: {output_path}")


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    ttf_path = sys.argv[1]
    cell_size = int(sys.argv[2])
    output_path = sys.argv[3]

    var_prefix = f"CJKFont{cell_size}px"
    render_size = int(cell_size * 1.4)
    y_offset = -cell_size
    x_advance = cell_size + 1
    max_kanji = None

    args = sys.argv[4:]
    i = 0
    while i < len(args):
        if args[i] == "--var-prefix" and i + 1 < len(args):
            var_prefix = args[i + 1]
            i += 2
        elif args[i] == "--render-size" and i + 1 < len(args):
            render_size = int(args[i + 1])
            i += 2
        elif args[i] == "--y-offset" and i + 1 < len(args):
            y_offset = int(args[i + 1])
            i += 2
        elif args[i] == "--x-advance" and i + 1 < len(args):
            x_advance = int(args[i + 1])
            i += 2
        elif args[i] == "--max-kanji" and i + 1 < len(args):
            max_kanji = int(args[i + 1])
            i += 2
        else:
            print(f"Unknown option: {args[i]}")
            i += 1

    generate_font_header(ttf_path, cell_size, render_size, output_path, var_prefix, y_offset, x_advance, max_kanji)


if __name__ == "__main__":
    main()
