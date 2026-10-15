# MenuTitle: Show Glyphs Using Selected Diacritic
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

__doc__ = """
Opens a new tab with all glyphs that use the selected glyph
(e.g. a diacritic) as a component.
"""

from GlyphsApp import Glyphs

font = Glyphs.font
selectedLayers = font.selectedLayers

if not selectedLayers:
    Glyphs.showNotification("Error", "Please select a diacritic glyph.")
else:
    # Assume first selected glyph is the diacritic
    diacriticGlyph = selectedLayers[0].parent
    diacriticName = diacriticGlyph.name

    print(f"Searching for glyphs using: {diacriticName}")

    resultGlyphs = []

    for glyph in font.glyphs:
        for layer in glyph.layers:
            if not layer.isMasterLayer:
                continue

            for component in layer.components:
                if component.componentName == diacriticName:
                    resultGlyphs.append(glyph.name)
                    break  # found in this layer → next glyph
            else:
                continue
            break

    if resultGlyphs:
        tabText = "/" + "/".join(sorted(set(resultGlyphs)))
        font.newTab(tabText)
    else:
        Glyphs.showNotification(
            "No Matches",
            f"No glyphs use {diacriticName} as a component."
        )