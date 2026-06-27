# MenuTitle: Open All Drawn Glyphs

# Opens a tab with all glyphs that contain drawn paths

from GlyphsApp import Glyphs

font = Glyphs.font
currentMaster = font.selectedFontMaster
tabText = ""

for glyph in font.glyphs:

    # Skip non-exporting glyphs
    if not glyph.export:
        continue

    layer = glyph.layers[currentMaster.id]

    hasContent = (
        (layer.paths and len(layer.paths) > 0)
        or (layer.components and len(layer.components) > 0)
    )

    if hasContent:
        tabText += "/" + glyph.name

if tabText:
    font.newTab(tabText)
else:
    print("No exporting glyphs with content found in the current master.")