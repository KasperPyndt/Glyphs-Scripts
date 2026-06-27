# MenuTitle: Align to Vertical Center of Hyphen 
# -*- coding: utf-8 -*-

def alignHyphen():
    font = Glyphs.font
    hyphenGlyph = font.glyphs["hyphen"]
    if not hyphenGlyph:
        print("No 'hyphen' glyph found in this font.")
        return
    
    font.disableUpdateInterface()  # to speed things up and avoid flicker
    
    for layer in font.selectedLayers:
        parentGlyph = layer.parent
        hyphenLayer = hyphenGlyph.layers[layer.layerId]
        if not hyphenLayer:
            print(f"No hyphen layer found for {parentGlyph.name} in layer {layer.name}")
            continue
        
        # Vertical centers from bounds
        hyphenCenterY = hyphenLayer.bounds.origin.y + hyphenLayer.bounds.size.height * 0.5
        glyphCenterY = layer.bounds.origin.y + layer.bounds.size.height * 0.5
        deltaY = hyphenCenterY - glyphCenterY
        
        if abs(deltaY) < 0.01:
            print(f"{parentGlyph.name}: already aligned")
            continue
        
        # Move paths (nodes)
        for path in layer.paths:
            for node in path.nodes:
                node.y += deltaY
        
        # Move components
        for comp in layer.components:
            pos = comp.position
            comp.position = (pos.x, pos.y + deltaY)
        
        print(f"Aligned {parentGlyph.name} on {layer.name} by {deltaY:.1f} units")
    
    font.enableUpdateInterface()

# Run the function
alignHyphen()