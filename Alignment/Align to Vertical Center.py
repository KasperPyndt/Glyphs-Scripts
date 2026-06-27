# MenuTitle: Align to Vertical Center
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs, GSNode, GSPath, GSComponent, GSAnchor

def collect_full_layer_positions(layer):
    """Fallback when nothing is explicitly selected: use whole glyph geometry."""
    ys = []

    # All nodes in all paths
    for path in layer.paths:
        for node in path.nodes:
            ys.append(node.y)

    # Component bounds
    for comp in layer.components:
        b = comp.bounds
        ys.append(b.origin.y)
        ys.append(b.origin.y + b.size.height)

    # Anchors
    for anchor in layer.anchors:
        ys.append(anchor.position.y)

    return ys

def shift_whole_layer(layer, deltaY):
    """Move ALL geometric elements in a layer by deltaY."""
    # Paths
    for path in layer.paths:
        for node in path.nodes:
            node.y += deltaY

    # Components
    for comp in layer.components:
        x, y = comp.position
        comp.position = (x, y + deltaY)

    # Anchors
    for anchor in layer.anchors:
        x, y = anchor.position
        anchor.position = (x, y + deltaY)


def alignSelectionToCapHeight():
    font = Glyphs.font
    if not font:
        print("No font open.")
        return

    font.disableUpdateInterface()

    for layer in font.selectedLayers:
        parentGlyph = layer.parent
        master = layer.master

        capHeight = master.capHeight
        capCenterY = capHeight * 0.5

        # Explicit selections
        selectedNodes = [n for n in layer.selection if isinstance(n, GSNode)]
        selectedPaths = [p for p in layer.selection if isinstance(p, GSPath)]
        selectedComponents = [c for c in layer.selection if isinstance(c, GSComponent)]
        selectedAnchors = [a for a in layer.selection if isinstance(a, GSAnchor)]

        hasExplicitSelection = bool(selectedNodes or selectedPaths or selectedComponents or selectedAnchors)

        # Collect Y coordinates:
        selectedYs = []

        if hasExplicitSelection:
            # Nodes
            for node in selectedNodes:
                selectedYs.append(node.y)

            # Paths (all nodes inside)
            for path in selectedPaths:
                for node in path.nodes:
                    selectedYs.append(node.y)

            # Components (true visual bounds)
            for comp in selectedComponents:
                b = comp.bounds
                selectedYs.append(b.origin.y)
                selectedYs.append(b.origin.y + b.size.height)

            # Anchors
            for anchor in selectedAnchors:
                selectedYs.append(anchor.position.y)
        else:
            # TEXT MODE FALLBACK: using full glyph geometry
            selectedYs = collect_full_layer_positions(layer)

        if not selectedYs:
            print(f"{parentGlyph.name}: no geometry found")
            continue

        selectionMinY = min(selectedYs)
        selectionMaxY = max(selectedYs)
        selectionCenterY = (selectionMinY + selectionMaxY) * 0.5

        deltaY = capCenterY - selectionCenterY

        if abs(deltaY) < 0.01:
            print(f"{parentGlyph.name}: already aligned")
            continue

        if hasExplicitSelection:
            # Move nodes
            for node in selectedNodes:
                node.y += deltaY

            # Move path groups
            for path in selectedPaths:
                for node in path.nodes:
                    node.y += deltaY

            # Move components
            for comp in selectedComponents:
                x, y = comp.position
                comp.position = (x, y + deltaY)

            # Move anchors
            for anchor in selectedAnchors:
                x, y = anchor.position
                anchor.position = (x, y + deltaY)

        else:
            # TEXT MODE: shift entire layer content
            shift_whole_layer(layer, deltaY)

        print(f"Aligned in {parentGlyph.name} ({layer.name}) by {deltaY:.1f} units")

    font.enableUpdateInterface()

alignSelectionToCapHeight()
