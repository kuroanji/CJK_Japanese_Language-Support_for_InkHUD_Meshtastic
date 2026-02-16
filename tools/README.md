Font generator script that converts TTF → C header. See `generate_cjk_font.py` for full implementation.

Usage:
```bash
python3 tools/generate_cjk_font.py <ttf_file> <cell_size> <output.h> [--var-prefix NAME]
```

`joyo_kanji.txt`

List of 2136 Joyo kanji (one per line) from https://github.com/scriptin/topokanji
