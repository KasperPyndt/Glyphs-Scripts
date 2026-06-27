# MenuTitle: Align to Horizontal Center
# Aligns selected anchors, components, and outlines to the canvas horizontal center axis

from GlyphsApp import Glyphs
from Foundation import NSPoint
from math import radians, tan


font = Glyphs.font
if not font:
    raise Exception("No font open.")


def italic_center_x(layer, y):
    return (
        layer.width / 2.0
        + (y - layer.master.xHeight / 2.0) * tan(radians(layer.master.italicAngle))
    )


def bounds_center(bounds):
    return NSPoint(
        bounds.origin.x + bounds.size.width / 2.0,
        bounds.origin.y + bounds.size.height / 2.0,
    )


def move_by_x(items, dx):
    for item in items:
        item.position = NSPoint(item.position.x + dx, item.position.y)


def align_items(layer, items, center):
    if not items:
        return

    target_x = italic_center_x(layer, center.y)
    move_by_x(items, target_x - center.x)


def selected_nodes(layer):
    nodes = []

    for path in layer.paths:
        if path.selected:
            nodes.extend(path.nodes)
        else:
            nodes.extend(node for node in path.nodes if node.selected)

    return nodes


def nodes_center(nodes):
    min_x = min(node.position.x for node in nodes)
    max_x = max(node.position.x for node in nodes)
    min_y = min(node.position.y for node in nodes)
    max_y = max(node.position.y for node in nodes)

    return NSPoint((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)


font.disableUpdateInterface()

try:
    for layer in font.selectedLayers:
        glyph = layer.parent
        glyph.beginUndo()

        try:
            for anchor in layer.anchors:
                if anchor.selected:
                    align_items(layer, [anchor], anchor.position)

            for component in layer.components:
                if component.selected:
                    align_items(layer, [component], bounds_center(component.bounds))

            nodes = selected_nodes(layer)
            if nodes:
                align_items(layer, nodes, nodes_center(nodes))

        finally:
            glyph.endUndo()

    Glyphs.redraw()
    Glyphs.showNotification(
        "Aligned to italic center",
        "Selected anchors, components, and outlines were aligned."
    )

finally:
    font.enableUpdateInterface()