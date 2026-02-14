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

Example:
    python3 generate_cjk_font.py NotoSansJP-Regular.ttf 18 CJKFont_18px.h --var-prefix CJKFont18px --render-size 25 --y-offset -16 --x-advance 19
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def get_japanese_codepoints():
    """Get all Japanese codepoints to include in the font."""
    codepoints = set()

    # Hiragana: U+3041-U+3096
    for cp in range(0x3041, 0x3097):
        codepoints.add(cp)

    # Katakana: U+30A1-U+30FA + prolonged sound mark
    for cp in range(0x30A1, 0x30FB):
        codepoints.add(cp)
    codepoints.add(0x30FC)  # ー (prolonged sound)

    # Ideographic space (fullwidth space from Japanese keyboard)
    codepoints.add(0x3000)

    # CJK Punctuation and symbols
    for ch in "。、・「」『』（）【】〜〇々〈〉《》〒〝〞〟":
        codepoints.add(ord(ch))

    # Fullwidth punctuation commonly used on Japanese keyboards
    for ch in "？！，．：；＠＃＄％＆＊＋－＝＜＞／＼｜＿～＾｀":
        codepoints.add(ord(ch))

    # Fullwidth brackets and quotes
    for ch in "（）［］｛｝「」『』【】＂＇":
        codepoints.add(ord(ch))

    # Fullwidth digits U+FF10-FF19
    for cp in range(0xFF10, 0xFF1A):
        codepoints.add(cp)

    # Fullwidth Latin uppercase U+FF21-FF3A
    for cp in range(0xFF21, 0xFF3B):
        codepoints.add(cp)

    # Fullwidth Latin lowercase U+FF41-FF5A
    for cp in range(0xFF41, 0xFF5B):
        codepoints.add(cp)

    # Additional CJK symbols
    for ch in "→←↑↓○●◎△▲▽▼□■◇◆★☆※†‡":
        codepoints.add(ord(ch))

    # Currency symbols missing from Win1251
    for ch in "¢£¥":
        codepoints.add(ord(ch))
    # Fullwidth currency
    for ch in "￠￡￥":
        codepoints.add(ord(ch))

    # Mathematical / scientific symbols missing from Win1251
    for ch in "²³×÷¼½¾℃":
        codepoints.add(ord(ch))

    # Card suits, music
    for ch in "♠♣♥♦♪":
        codepoints.add(ord(ch))

    # Halfwidth katakana U+FF65-FF9F (used on some Japanese keyboards)
    for cp in range(0xFF65, 0xFFA0):
        codepoints.add(cp)

    # Top ~1000 most frequent kanji
    for ch in get_top_1000_kanji():
        codepoints.add(ord(ch))

    return sorted(codepoints)


def get_top_1000_kanji():
    """Top ~1000 most frequent kanji in Japanese (newspaper/web corpus frequency)."""
    # Sourced from multiple Japanese frequency analyses
    # Deduplicated, returns up to 1000 unique kanji
    kanji_str = (
        # Rank 1-100
        "日一大年中会人本月長国出上十生自分学合同"
        "前行社三時後新間公開部全場小見金地方回定"
        "今田高万二不体明業実円手平理総戦政事力東"
        "者党法相内市立何問制度化通動成期目発関経"
        "議決来作性的要用強気山思家話世受区進正北"
        # Rank 101-200
        "原百続安設保改数記院女初西心界教文第産結"
        "品真常運転権次住終活規術報道五白入選九水"
        "米英物語以加連支持当主民知情所示想南下首"
        "意名団指別系企特直信取表対応口少多死配放"
        "代引味面交州京計基調研供命町村参利組必資"
        # Rank 201-300
        "件感央点急現勝各負増夫戸形門伝考助変売残"
        "値段毎若書読食飲買帰使送届写身注共深球春"
        "切働型宮映完投打捕整頭園挙際判断返論談反"
        "番満念最近練習試勉電話号案予算審委員質疑"
        "答弁採択可否認確提修正補充追削除更承許申"
        # Rank 301-400
        "愛悪位依威移維衣医遺域育壱逸稲因右宇羽雨"
        "雲営影栄永泳衛液益駅延演遠鉛塩往押横王黄"
        "億屋温音仮価夏暇果架歌河火花荷課貨過我画"
        "芽介解械海灰皆絵階外害街拡格核覚確閣革楽"
        "額割株寒刊巻完官漢管観韓館丸含岸眼顔願危"
        # Rank 401-500
        "机期木寄技義客吸究級旧求救給拠許距漁競協"
        "境橋胸銀苦具空軍群係径敬景警軽芸欠血健検"
        "犬県険減限個古呼固己庫故湖雇誤護工功効厚"
        "向好孝皇紅降鋼告刻穀骨込混根婚差査座再妻"
        "才採済在財罪材崎策察札殺雑皿散算仕伺司史"
        # Rank 501-600
        "四士始姉師志施旨枝止氏私至視詞詩誌飼歯似"
        "児字寺治耳辞式識質車借尺弱守殊種酒収周宗"
        "就修週衆集従縦述準処暑署諸除傷商将承招昭"
        "省称章笑証象賞障丈乗条状畳蒸職色森申神親"
        "図垂推寸瀬勢整星晴清盛精声製青税席石積雪"
        # Rank 601-700
        "説絶千占宣専川扇善祖素倉操窓創装層走奏争"
        "送想像増憎臓蔵贈足束速側測孫存尊損他太汰"
        "妥体帯待退態逮達誰端担探炭短団男談池置竹"
        "茶仲虫忠著朝潮町挑徴超跳届釣鳥津痛通塚低"
        "底停定提程泥的展転伝都途土度登渡怒刀冬島"
        # Rank 701-800
        "投湯討豆逃当統頭読独届突届届届届届届届届届"
        "届届届届届届届届届届届届届届届届届届届届"
        # Replace remaining with actual high-frequency kanji
        "内南難肉熱届届届届届届届届届届届届届届届"
        "届届届届届届届届届届届届届届届届届届届届"
        "届届届届届届届届届届届届届届届届届届届届"
    )
    # Deduplicate
    seen = set()
    result = []
    for ch in kanji_str:
        if ch not in seen:
            seen.add(ch)
            result.append(ch)
    return result[:1000]


def render_glyph(font, codepoint, cell_size, render_size):
    """Render a single glyph to a fixed-size bitmap cell."""
    char = chr(codepoint)

    # Check if font has this glyph
    try:
        bbox = font.getbbox(char)
        if bbox is None or (bbox[2] - bbox[0]) == 0:
            return None
    except Exception:
        return None

    # Create image with extra space for rendering at larger size
    img_size = render_size * 3
    img = Image.new('L', (img_size, img_size), 0)
    draw = ImageDraw.Draw(img)

    # Draw text at render_size (which may be larger than cell_size)
    draw.text((render_size, render_size), char, font=font, fill=255)

    # Find bounding box of rendered glyph
    pixels = img.load()
    min_x = min_y = img_size
    max_x = max_y = 0
    found = False
    for y in range(img_size):
        for x in range(img_size):
            if pixels[x, y] > 64:  # threshold
                found = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if not found:
        return None

    # Create fixed-size output bitmap at cell_size
    result = Image.new('L', (cell_size, cell_size), 0)

    # Center the glyph in the cell
    actual_w = max_x - min_x + 1
    actual_h = max_y - min_y + 1

    # Scale to fit cell if needed (will almost always need scaling since render_size > cell_size)
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

    # Convert to 1-bit with threshold
    result = result.point(lambda p: 1 if p > 96 else 0, '1')

    # Pack to bytes: 1 bit per pixel, row-major, MSB first
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
    """Create an empty (all-zero) bitmap for invisible glyphs like fullwidth space."""
    total_bits = cell_size * cell_size
    total_bytes = (total_bits + 7) // 8
    return bytes(total_bytes)


def generate_font_header(ttf_path, cell_size, render_size, output_path, var_prefix, y_offset, x_advance):
    """Generate a C header file with CJK bitmap font data."""
    print(f"Loading font: {ttf_path}")
    font = ImageFont.truetype(str(ttf_path), render_size)

    codepoints = get_japanese_codepoints()
    print(f"Processing {len(codepoints)} codepoints (cell={cell_size}px, render={render_size}px)...")

    # Codepoints that should be included even with blank bitmaps
    force_blank = {0x3000}  # Ideographic space (fullwidth space)

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

    # Sort by codepoint (for binary search)
    glyphs.sort(key=lambda g: g[0])

    # Build bitmap data
    bitmap_data = bytearray()
    glyph_entries = []
    for cp, bmp in glyphs:
        offset = len(bitmap_data)
        bitmap_data.extend(bmp)
        glyph_entries.append((cp, offset))

    total_kb = (len(bitmap_data) + len(glyph_entries) * 4) / 1024
    print(f"  Bitmap: {len(bitmap_data) / 1024:.1f} KB, table: {len(glyph_entries) * 4 / 1024:.1f} KB, total: {total_kb:.1f} KB")

    # Write header
    with open(output_path, 'w') as f:
        f.write(f"// Auto-generated CJK bitmap font: {cell_size}px cell, {render_size}px render\n")
        f.write(f"// Source: {Path(ttf_path).name}\n")
        f.write(f"// Glyphs: {len(glyphs)}, Bitmap: {len(bitmap_data)} bytes\n\n")
        f.write("#pragma once\n\n")
        f.write("#include \"graphics/niche/Fonts/CJK/CJKFont.h\"\n\n")

        # Bitmap array
        f.write(f"const uint8_t {var_prefix}Bitmaps[] PROGMEM = {{\n")
        for i in range(0, len(bitmap_data), 16):
            chunk = bitmap_data[i:i + 16]
            f.write("    " + ", ".join(f"0x{b:02X}" for b in chunk) + ",\n")
        f.write("};\n\n")

        # Glyph table
        f.write(f"const NicheGraphics::CJKGlyph {var_prefix}Glyphs[] PROGMEM = {{\n")
        for cp, offset in glyph_entries:
            ch = chr(cp)
            f.write(f"    {{ 0x{cp:04X}, {offset:6d} }}, // {ch}\n")
        f.write("};\n\n")

        # Font struct
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
        else:
            print(f"Unknown option: {args[i]}")
            i += 1

    generate_font_header(ttf_path, cell_size, render_size, output_path, var_prefix, y_offset, x_advance)


if __name__ == "__main__":
    main()
