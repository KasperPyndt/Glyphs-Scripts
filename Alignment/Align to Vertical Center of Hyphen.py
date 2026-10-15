# MenuTitle: Align to Vertical Center of Hyphen
# Aligns selected glyph layers vertically to the center of the hyphen.
# Useful for math symbols and punctuation.

from GlyphsApp import Glyphs


def unique_selected_layers(font):
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

hyphen_glyph = font.glyphs["hyphen"]
if not hyphen_glyph:
    raise RuntimeError("No 'hyphen' glyph found in this font.")

font.disableUpdateInterface()
try:
    for layer in unique_selected_layers(font):
        glyph = layer.parent

        # layerId only matches across glyphs for master layers. For special
        # layers, use the associated master instead.
        master_id = layer.master.id
        hyphen_layer = hyphen_glyph.layers[master_id]

        if hyphen_layer is None:
            print(f"No hyphen layer found for {glyph.name} ({layer.name})")
            continue

        hyphen_bounds = hyphen_layer.bounds
        glyph_bounds = layer.bounds

        if hyphen_bounds.size.height == 0:
            print(f"Hyphen has no measurable outline in {hyphen_layer.name}")
            continue
        if glyph_bounds.size.height == 0:
            print(f"{glyph.name}: no measurable outline")
            continue

        hyphen_center_y = hyphen_bounds.origin.y + hyphen_bounds.size.height * 0.5
        glyph_center_y = glyph_bounds.origin.y + glyph_bounds.size.height * 0.5
        delta_y = hyphen_center_y - glyph_center_y

        if abs(delta_y) < 0.01:
            print(f"{glyph.name}: already aligned")
            continue

        glyph.beginUndo()
        layer.beginChanges()
        try:
            # Move the layer as one unit. This also handles components and
            # mixed path/component glyphs consistently.
            layer.applyTransform((1.0, 0.0, 0.0, 1.0, 0.0, delta_y))
        finally:
            layer.endChanges()
            glyph.endUndo()

        print(f"Aligned {glyph.name} ({layer.name}) by {delta_y:.1f} units")
finally:
    font.enableUpdateInterface()

Glyphs.redraw()
