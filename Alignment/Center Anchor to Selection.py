# MenuTitle: Center Anchor to Selection
# Centers one selected anchor in the bounding box of selected nodes/components.

from Foundation import NSPoint
from GlyphsApp import Glyphs, GSAnchor, GSComponent, GSNode


font = Glyphs.font
if not font:
    raise RuntimeError("No font open.")

if not font.selectedLayers:
    raise RuntimeError("No glyph layer selected.")

layer = font.selectedLayers[0]
glyph = layer.parent

anchors = [item for item in layer.selection if isinstance(item, GSAnchor)]
nodes = [item for item in layer.selection if isinstance(item, GSNode)]
components = [item for item in layer.selection if isinstance(item, GSComponent)]

if len(anchors) != 1:
    raise RuntimeError("Select exactly one anchor.")

xs = [node.position.x for node in nodes]
ys = [node.position.y for node in nodes]

for component in components:
    bounds = component.bounds
    xs.extend((bounds.origin.x, bounds.origin.x + bounds.size.width))
    ys.extend((bounds.origin.y, bounds.origin.y + bounds.size.height))

# Preserve the old script's intent: one lone node is not enough to define a
# useful selection box, while a single component is (because it has bounds).
if len(xs) < 2 or len(ys) < 2:
    raise RuntimeError("Select at least two nodes, or one or more components.")

anchor = anchors[0]
center_x = (min(xs) + max(xs)) * 0.5
center_y = (min(ys) + max(ys)) * 0.5

glyph.beginUndo()
layer.beginChanges()
try:
    anchor.position = NSPoint(center_x, center_y)
finally:
    layer.endChanges()
    glyph.endUndo()

Glyphs.redraw()
