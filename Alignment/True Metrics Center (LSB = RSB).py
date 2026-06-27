# MenuTitle: True Metric Center (LSB = RSB)
# Makes left and right sidebearings equal without changing the glyphs total width

from GlyphsApp import Glyphs
from Foundation import NSPoint

font = Glyphs.font
if not font:
    raise Exception("No font open.")

for layer in font.selectedLayers:
    
    # Ensure metrics are up to date
    layer.syncMetrics()
    
    LSB = layer.LSB
    RSB = layer.RSB
    
    # If already equal, skip
    if abs(LSB - RSB) < 0.01:
        continue
    
    # Calculate correction
    shift = (RSB - LSB) / 2.0
    
    # Move outlines/components
    layer.applyTransform((1, 0, 0, 1, shift, 0))

    # Move anchors by the same amount.
    # Anchors need an NSPoint assignment; a plain tuple may not update them reliably.
    for anchor in layer.anchors:
        anchor.position = NSPoint(anchor.position.x + shift, anchor.position.y)
    
    # Recalculate metrics
    layer.syncMetrics()

Glyphs.redraw()
