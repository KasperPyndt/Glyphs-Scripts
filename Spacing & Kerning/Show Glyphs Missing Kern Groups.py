# MenuTitle: Show Glyphs Missing Kern Groups
# Run in Glyphs' Macro Panel or save in your Scripts folder.

from GlyphsApp import Glyphs

font = Glyphs.font

if font is None:
    print("Open a font in Glyphs first.")
else:
    master = font.selectedFontMaster
    missing_layers = []

    for glyph in font.glyphs:
        if glyph.export and (not glyph.leftKerningGroup or not glyph.rightKerningGroup):
            layer = glyph.layers[master.id]
            if layer is not None:
                missing_layers.append(layer)

    if missing_layers:
        font.newTab(missing_layers)
        print("Opened %d glyphs missing a left or right kerning group in %s." % (
            len(missing_layers), master.name
        ))
    else:
        print("No glyphs missing a left or right kerning group in %s." % master.name)
