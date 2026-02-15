# Add Japanese (CJK) Language Support for InkHUD

## Summary

Adds Japanese language support to InkHUD, enabling display of Hiragana, Katakana, and 2136 Joyo Kanji characters on e-ink devices.

## Why

InkHUD's 8-bit font encoding (max 255 glyphs) cannot support Japanese, which requires 2500+ characters. This implementation adds a secondary bitmap font system that coexists with Latin/Cyrillic support.

See CJK_IMPLEMENTATION.md for instructions (CJK統合フォントをメッシュタスティックinkHUDデバイスに
適用する手順).
