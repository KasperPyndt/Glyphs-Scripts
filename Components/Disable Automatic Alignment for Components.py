# MenuTitle: Disable Auto Alignment for Components in Selected Glyphs
# -*- coding: utf-8 -*-
__doc__ = """
Disables automatic alignment for all components in the selected glyphs.
"""

import GlyphsApp

Font = Glyphs.font
selectedGlyphs = [l.parent for l in Font.selectedLayers]

for glyph in selectedGlyphs:
    for layer in glyph.layers:
        for component in layer.components:
            if component.automaticAlignment:
                component.automaticAlignment = False
    glyph.updateGlyphInfo()

Glyphs.showNotification(
    "Disable Auto Alignment",
    f"Auto alignment disabled for components in {len(selectedGlyphs)} glyph(s)."
)