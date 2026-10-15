# MenuTitle: Assign Uppercase Kerning Groups to Small Caps
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs

font = Glyphs.font

if not font:
    print("No font open.")

else:
    updated = 0
    skipped = 0

    def lowercaseGlyphName(glyphName):
        """
        Convert an uppercase glyph name to its lowercase equivalent
        using Glyphs' glyph info.

        Examples:
        H       -> h
        E       -> e
        Aacute  -> aacute
        Oslash  -> oslash
        """
        if not glyphName:
            return None

        info = Glyphs.glyphInfoForName(glyphName)

        if info and info.unicode:
            try:
                char = chr(int(info.unicode, 16))
                lowerChar = char.lower()

                if len(lowerChar) == 1:
                    lowerInfo = Glyphs.glyphInfoForUnicode(
                        f"{ord(lowerChar):04X}"
                    )

                    if lowerInfo:
                        return lowerInfo.name

            except Exception:
                pass

        # Fallback for straightforward glyph names
        return glyphName[0].lower() + glyphName[1:]


    font.disableUpdateInterface()

    try:
        for scGlyph in font.glyphs:

            if not scGlyph.name.endswith(".sc"):
                continue

            # e.sc -> e
            baseName = scGlyph.name[:-3]

            # Find uppercase counterpart:
            # e -> E
            # eacute -> Eacute
            sourceGlyph = None

            info = Glyphs.glyphInfoForName(baseName)

            if info and info.unicode:
                try:
                    char = chr(int(info.unicode, 16))
                    upperChar = char.upper()

                    if len(upperChar) == 1:
                        upperInfo = Glyphs.glyphInfoForUnicode(
                            f"{ord(upperChar):04X}"
                        )

                        if upperInfo:
                            sourceGlyph = font.glyphs[upperInfo.name]

                except Exception:
                    pass

            # Fallback
            if sourceGlyph is None and baseName:
                fallbackName = baseName[0].upper() + baseName[1:]
                sourceGlyph = font.glyphs[fallbackName]

            if sourceGlyph is None:
                print(f"⚠️ No uppercase source found for {scGlyph.name}")
                skipped += 1
                continue

            # LEFT kerning group
            if sourceGlyph.leftKerningGroup:
                lowerGroup = lowercaseGlyphName(
                    sourceGlyph.leftKerningGroup
                )

                scGlyph.leftKerningGroup = lowerGroup + ".sc"
            else:
                scGlyph.leftKerningGroup = None

            # RIGHT kerning group
            if sourceGlyph.rightKerningGroup:
                lowerGroup = lowercaseGlyphName(
                    sourceGlyph.rightKerningGroup
                )

                scGlyph.rightKerningGroup = lowerGroup + ".sc"
            else:
                scGlyph.rightKerningGroup = None

            print(
                f"✓ {sourceGlyph.name} → {scGlyph.name} | "
                f"L: {scGlyph.leftKerningGroup} | "
                f"R: {scGlyph.rightKerningGroup}"
            )

            updated += 1

    finally:
        font.enableUpdateInterface()

    print()
    print(f"Done. Updated {updated} small-cap glyphs.")
    print(f"Skipped {skipped}.")