#MenuTitle: Clear Selected Glyphs
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs, Message
import vanilla


class ClearSelectedGlyphs:

	def __init__(self):

		self.w = vanilla.FloatingWindow(
			(260, 105),
			"Clear Selected Glyphs"
		)

		self.w.allMasters = vanilla.CheckBox(
			(15, 15, -15, 20),
			"All masters",
			value=False
		)

		self.w.removeButton = vanilla.Button(
			(15, 50, -15, 30),
			"Clear",
			callback=self.clearGlyphs
		)

		self.w.setDefaultButton(self.w.removeButton)
		self.w.open()


	def clearLayer(self, layer):

		# Removes:
		# - paths
		# - nodes
		# - components
		# - anchors
		# - hints
		# - selection
		layer.clear()

		# Remove layer-local guides
		try:
			layer.guides = []
		except Exception:
			pass

		# Remove annotations
		try:
			layer.annotations = []
		except Exception:
			pass

		# Remove background image
		try:
			layer.backgroundImage = None
		except Exception:
			pass

		# Remove complete background layer
		try:
			layer.background = None
		except Exception:
			try:
				layer.background.clear()
			except Exception:
				pass


	def clearGlyphs(self, sender):

		font = Glyphs.font

		if font is None:
			Message(
				"No Font Open",
				"Open a font first."
			)
			return

		glyphs = list(font.selection)

		if not glyphs:
			Message(
				"No Glyphs Selected",
				"Select one or more glyphs in Font View."
			)
			return

		if self.w.allMasters.get():
			masterIDs = [master.id for master in font.masters]
		else:
			masterIDs = [font.selectedFontMaster.id]

		font.disableUpdateInterface()

		try:

			for glyph in glyphs:

				glyph.beginUndo()

				try:

					for masterID in masterIDs:

						layer = glyph.layers[masterID]

						if layer is not None:
							self.clearLayer(layer)

				finally:
					glyph.endUndo()

		except Exception as e:

			Glyphs.showMacroWindow()
			print("ERROR — Clear Selected Glyphs")
			print(e)

		finally:
			font.enableUpdateInterface()

		# Hide window without triggering the Vanilla/Glyphs 4 close bug
		try:
			self.w._window.orderOut_(None)
		except Exception:
			pass


ClearSelectedGlyphs()