# MenuTitle: Center Anchor to Selection
# Center selected anchor between selected nodes and components
# Compatible with current Glyphs versions

from GlyphsApp import Glyphs, GSAnchor, GSNode, GSComponent

font = Glyphs.font
if not font:
	raise Exception("No font open.")

layer = font.selectedLayers[0]

anchor = None
xs = []
ys = []

for item in layer.selection:
	if isinstance(item, GSAnchor):
		anchor = item

	elif isinstance(item, GSNode):
		xs.append(item.x)
		ys.append(item.y)

	elif isinstance(item, GSComponent):
		b = item.bounds  # NSRect in layer coordinates
		xs.extend([b.origin.x, b.origin.x + b.size.width])
		ys.extend([b.origin.y, b.origin.y + b.size.height])

# Safety checks
if anchor is None:
	raise Exception("Select exactly one anchor.")
if len(xs) < 2 or len(ys) < 2:
	raise Exception("Select at least two nodes and/or components.")

# Center anchor to bounding box of selection
anchor.x = (min(xs) + max(xs)) * 0.5
anchor.y = (min(ys) + max(ys)) * 0.5
