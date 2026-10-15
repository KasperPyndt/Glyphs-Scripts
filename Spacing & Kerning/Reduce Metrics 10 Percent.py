# MenuTitle: Reduce Metrics by 10% — All Masters
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
import math

font = Glyphs.font

if not font:
	print("⚠️ No font open.")

else:
	selectedLayers = list(font.selectedLayers)

	if not selectedLayers:
		print("⚠️ No glyph selected.")

	else:
		# Get unique glyphs from selected/active layers
		glyphs = []
		seen = set()

		for layer in selectedLayers:
			glyph = layer.parent

			if glyph and glyph.name not in seen:
				glyphs.append(glyph)
				seen.add(glyph.name)

		font.disableUpdateInterface()

		try:
			for glyph in glyphs:

				print("\n%s" % glyph.name)

				for master in font.masters:
					layer = glyph.layers[master.id]

					if not layer:
						continue

					oldLSB = layer.LSB
					oldRSB = layer.RSB

					newLSB = math.floor(oldLSB * 0.9)
					newRSB = math.floor(oldRSB * 0.9)

					layer.LSB = newLSB
					layer.RSB = newRSB

					print(
						"  %s: LSB %s → %s | RSB %s → %s"
						% (
							master.name,
							oldLSB,
							newLSB,
							oldRSB,
							newRSB,
						)
					)

		finally:
			font.enableUpdateInterface()

		print("\n✅ Reduced metrics by 10% in all masters.")