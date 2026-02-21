# Add Japanese (CJK) Language Support for InkHUD [Meshtastic devices]

## New implementation (Unified CJK font with Japanese or Chinese/Korean and Cyrillic support) integrated in InkHUD2: https://github.com/kuroanji/InkHUD2

## Summary

Adds Japanese language support to InkHUD (currently implemented for Lilygo T-Echo PLUS, for other InkHUD devices just edit nicheGraphics.h file accordingly), enabling display of Hiragana, Katakana, and 2136 Joyo Kanji characters on e-ink devices.

## Why

InkHUD's 8-bit font encoding (max 255 glyphs) cannot support Japanese, which requires 2500+ characters. This implementation adds a secondary bitmap font system that coexists with Latin/Cyrillic support.

See CJK_IMPLEMENTATION.md for instructions (CJK統合フォントをメッシュタスティックinkHUDデバイスに
適用する手順).

Merge branch: https://github.com/kuroanji/firmware/tree/CJK_Japanese_support_InkHUD
