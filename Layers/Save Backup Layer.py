# MenuTitle: Save Backup Layer
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
from datetime import datetime

font = Glyphs.font

if font and font.selectedLayers:
	layer = font.selectedLayers[0]
	glyph = layer.parent

	# Duplicate the current layer
	backup = layer.copy()

	# Name it like a normal backup layer
	backup.name = datetime.now().strftime("%d. %b %y, %H:%M")

	# Attach it to the same master
	backup.associatedMasterId = layer.associatedMasterId

	# Add it to the Layers panel
	glyph.layers.append(backup)