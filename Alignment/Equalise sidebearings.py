# MenuTitle: Equalise sidebearings
# Makes left and right sidebearings equal without changing the glyph width.

from GlyphsApp import Glyphs


def unique_selected_layers(font):
    """Return selected layers once each, even if a glyph occurs repeatedly in Edit View."""
    result = []
    seen = set()
    for layer in font.selectedLayers:
        glyph = layer.parent
        key = (glyph.id, layer.layerId)
        if key not in seen:
            seen.add(key)
            result.append(layer)
    return result


font = Glyphs.font
if not font:
    raise RuntimeError("No font open.")

font.disableUpdateInterface()
try:
    for layer in unique_selected_layers(font):
        glyph = layer.parent
        glyph.beginUndo()
        layer.beginChanges()
        try:
            # LSB and RSB are derived from the current layer bounds and width,
            # so syncing metrics is neither necessary nor desirable here: a
            # metrics key could otherwise undo the equalisation.
            lsb = layer.LSB
            rsb = layer.RSB

            if abs(lsb - rsb) < 0.01:
                continue

            original_width = layer.width
            shift_x = (rsb - lsb) * 0.5

            # Transforming the layer moves its geometric content together.
            # Do not move anchors a second time afterwards.
            layer.applyTransform((1.0, 0.0, 0.0, 1.0, shift_x, 0.0))

            # Explicitly preserve the advance width.
            layer.width = original_width
        finally:
            layer.endChanges()
            glyph.endUndo()
finally:
    font.enableUpdateInterface()

Glyphs.redraw()
