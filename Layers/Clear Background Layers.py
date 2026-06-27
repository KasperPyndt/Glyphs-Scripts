# MenuTitle: Clear Background Layers
# -*- coding: utf-8 -*-
__doc__ = """
Removes all elements (paths, components, anchors, guides, etc.)
from the background layers of all glyphs in the current font.
"""

import GlyphsApp

font = Glyphs.font  # Frontmost font

if font is None:
    Message("No font open", "Please open a font before running this script.")
else:
    font.disableUpdateInterface()  # Improves performance during batch operation
    try:
        count = 0
        for glyph in font.glyphs:
            for layer in glyph.layers:
                if layer.background:
                    layer.background.clear()
                    count += 1

        print(f"✅ Cleared background elements in {count} layers.")
        Glyphs.showNotification(
            "Clear Background Layers",
            f"Removed background elements in {count} layers."
        )
    except Exception as e:
        Glyphs.showNotification("Error", str(e))
        print(f"Error: {e}")
    finally:
        font.enableUpdateInterface()