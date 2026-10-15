# MenuTitle: Show All Glyphs Missing Kerning Groups

from GlyphsApp import Glyphs

font = Glyphs.font

if font is None:
    print("Open a font in Glyphs first.")
else:
    master = font.selectedFontMaster
    layers = []

    for glyph in font.glyphs:
        if not glyph.leftKerningGroup or not glyph.rightKerningGroup:
            layer = glyph.layers[master.id]
            if layer is not None:
                layers.append(layer)

    if layers:
        font.newTab(layers)
        print("Opened %d glyphs in %s." % (len(layers), master.name))
    else:
        print("No glyphs are missing a kerning group in %s." % master.name)
