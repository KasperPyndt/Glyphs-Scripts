# MenuTitle: Align to Vertical Center, all masters
# Centers the complete foreground of every master layer of each selected glyph
# between that master's baseline and cap height.
ALIGN_ALL_MASTERS = True

from Foundation import NSPoint
from GlyphsApp import Glyphs


def unique_selected_layers(font):
    result = []
    seen = set()
    for layer in font.selectedLayers:
        if layer is None:
            continue
        glyph = getattr(layer, "parent", None)
        glyph_id = getattr(glyph, "id", None)
        layer_id = getattr(layer, "layerId", None)
        key = (
            str(glyph_id) if glyph_id is not None else id(glyph),
            str(layer_id) if layer_id is not None else id(layer),
        )
        if key not in seen:
            seen.add(key)
            result.append(layer)
    return result


def layers_to_align(font):
    selected_layers = unique_selected_layers(font)
    if not ALIGN_ALL_MASTERS:
        return selected_layers

    result = []
    seen_glyphs = set()
    for selected_layer in selected_layers:
        glyph = getattr(selected_layer, "parent", None)
        if glyph is None:
            continue
        glyph_id = getattr(glyph, "id", None)
        key = str(glyph_id) if glyph_id is not None else id(glyph)
        if key in seen_glyphs:
            continue
        seen_glyphs.add(key)

        master_layers = {
            str(layer.layerId): layer
            for layer in glyph.layers
            if layer is not None and getattr(layer, "layerId", None) is not None
        }
        for master in font.masters:
            layer = master_layers.get(str(master.id))
            if layer is not None:
                result.append(layer)
    return result


def selected_geometry(layer):
    """Return selected nodes, components and anchors without duplicate path moves."""
    nodes = [
        node
        for path in layer.paths
        for node in path.nodes
        if node.selected
    ]
    components = [component for component in layer.components if component.selected]
    anchors = [anchor for anchor in layer.anchors if anchor.selected]
    return nodes, components, anchors


def geometry_y_values(layer, nodes=None, components=None, anchors=None):
    ys = []

    if nodes is None:
        nodes = [node for path in layer.paths for node in path.nodes]
    if components is None:
        components = list(layer.components)
    if anchors is None:
        anchors = list(layer.anchors)

    ys.extend(node.position.y for node in nodes)

    for component in components:
        bounds = component.bounds
        ys.extend((bounds.origin.y, bounds.origin.y + bounds.size.height))

    ys.extend(anchor.position.y for anchor in anchors)
    return ys


def move_selected_geometry(nodes, components, anchors, delta_y):
    for node in nodes:
        node.position = NSPoint(node.position.x, node.position.y + delta_y)

    for component in components:
        component.position = NSPoint(
            component.position.x,
            component.position.y + delta_y,
        )

    for anchor in anchors:
        anchor.position = NSPoint(
            anchor.position.x,
            anchor.position.y + delta_y,
        )


font = Glyphs.font
if not font:
    raise RuntimeError("No font open.")

font.disableUpdateInterface()
try:
    for layer in layers_to_align(font):
        glyph = layer.parent
        master = layer.master
        target_center_y = master.capHeight * 0.5

        if ALIGN_ALL_MASTERS:
            nodes, components, anchors = [], [], []
        else:
            nodes, components, anchors = selected_geometry(layer)
        has_selection = bool(nodes or components or anchors)

        if has_selection:
            ys = geometry_y_values(layer, nodes, components, anchors)
        else:
            ys = geometry_y_values(layer)

        if not ys:
            print(f"{glyph.name}: no geometry found")
            continue

        current_center_y = (min(ys) + max(ys)) * 0.5
        delta_y = target_center_y - current_center_y

        if abs(delta_y) < 0.01:
            print(f"{glyph.name}: already aligned")
            continue

        glyph.beginUndo()
        layer.beginChanges()
        try:
            if has_selection:
                move_selected_geometry(nodes, components, anchors, delta_y)
            else:
                # Whole-layer transform is the most reliable way to keep all
                # geometric layer content together.
                layer.applyTransform((1.0, 0.0, 0.0, 1.0, 0.0, delta_y))
        finally:
            layer.endChanges()
            glyph.endUndo()

        print(f"Aligned {glyph.name} ({layer.name}) by {delta_y:.1f} units")
finally:
    font.enableUpdateInterface()

Glyphs.redraw()
