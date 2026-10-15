# MenuTitle: Disable Auto Alignment for Components in Selected Glyphs
# -*- coding: utf-8 -*-
__doc__ = """
Disables automatic alignment for all components in the selected glyphs.
"""

from GlyphsApp import Glyphs, Message

font = Glyphs.font
if font is None:
    Message("No font open", "Open a font before running this script.")
else:
    selectedGlyphs = [layer.parent for layer in font.selectedLayers]

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
