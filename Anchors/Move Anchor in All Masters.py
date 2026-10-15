# MenuTitle: Move Anchor in All Masters 2
# -*- coding: utf-8 -*-
__doc__ = """
Move the selected anchor by the same relative amount in all masters of
all selected glyphs.

Select one anchor in Edit View, select the glyphs to affect, choose the
number of units, then use the arrow buttons. Vertical moves follow each
master's italic angle.
"""

from GlyphsApp import Glyphs
from Foundation import NSPoint
from math import radians, tan
from vanilla import FloatingWindow, TextBox, EditText, Button


class MoveAnchorInAllMasters(object):

	def __init__(self):
		self.anchorName = None

		# Layout
		margin = 12
		windowWidth = 210
		windowHeight = 190

		buttonSize = 38
		buttonGap = 6

		gridWidth = buttonSize * 3 + buttonGap * 2
		gridLeft = (windowWidth - gridWidth) / 2

		row1Y = 82
		row2Y = row1Y + buttonSize + buttonGap

		col1X = gridLeft
		col2X = gridLeft + buttonSize + buttonGap
		col3X = gridLeft + (buttonSize + buttonGap) * 2

		self.w = FloatingWindow(
			(windowWidth, windowHeight),
			"Move Anchor in All Masters",
			autosaveName="com.kasperpyndt.moveAnchorAllMasters"
		)

		# Status
		self.w.info = TextBox(
			(margin, 12, -margin, 20),
			"Select an anchor"
		)

		# Units
		self.w.unitsLabel = TextBox(
			(margin, 46, 40, 20),
			"Units:"
		)

		self.w.units = EditText(
			(54, 42, 54, 24),
			"1"
		)

		# Arrow grid
		self.w.up = Button(
			(col2X, row1Y, buttonSize, buttonSize),
			"↑",
			callback=self.moveUp
		)

		self.w.left = Button(
			(col1X, row2Y, buttonSize, buttonSize),
			"←",
			callback=self.moveLeft
		)

		self.w.down = Button(
			(col2X, row2Y, buttonSize, buttonSize),
			"↓",
			callback=self.moveDown
		)

		self.w.right = Button(
			(col3X, row2Y, buttonSize, buttonSize),
			"→",
			callback=self.moveRight
		)

		self.w.open()
		self.rememberSelectedAnchor()


	def rememberSelectedAnchor(self):

		font = Glyphs.font

		if font is None or not font.selectedLayers:
			return

		selectedAnchors = []

		for layer in font.selectedLayers:
			for anchor in layer.anchors:
				if anchor.selected:
					selectedAnchors.append(anchor)

		if len(selectedAnchors) == 1:
			self.anchorName = selectedAnchors[0].name
			self.w.info.set("Anchor: %s" % self.anchorName)


	def selectedGlyphsAndAnchorName(self):

		font = Glyphs.font

		if font is None:
			self.w.info.set("No font open")
			return None, None, None

		if not font.selectedLayers:
			self.w.info.set("No active layer")
			return None, None, None

		selectedLayers = list(font.selectedLayers)
		selectedAnchors = []

		for layer in selectedLayers:
			for anchor in layer.anchors:
				if anchor.selected:
					selectedAnchors.append(anchor)

		if len(selectedAnchors) > 1:
			self.w.info.set("Select only one anchor")
			return None, None, None

		if len(selectedAnchors) == 1:
			self.anchorName = selectedAnchors[0].name

		if self.anchorName is None:
			self.w.info.set("Select one anchor")
			return None, None, None

		glyphs = []
		seenGlyphNames = set()

		for layer in selectedLayers:
			glyph = layer.parent

			if glyph is None or glyph.name in seenGlyphNames:
				continue

			seenGlyphNames.add(glyph.name)
			glyphs.append(glyph)

		return font, glyphs, self.anchorName


	def unitsValue(self):

		try:
			value = float(self.w.units.get())

			if value <= 0:
				raise ValueError

			return value

		except:
			self.w.info.set("Invalid unit value")
			return None


	def move(self, xDirection, yDirection):

		font, glyphs, anchorName = self.selectedGlyphsAndAnchorName()

		if anchorName is None:
			return

		units = self.unitsValue()

		if units is None:
			return

		dx = xDirection * units
		dy = yDirection * units

		movedCount = 0
		movedGlyphCount = 0

		for glyph in glyphs:
			glyphMovedCount = 0
			glyph.beginUndo()

			try:

				for master in font.masters:

					layer = glyph.layers[master.id]

					if layer is None:
						continue

					anchor = layer.anchors[anchorName]

					if anchor is None:
						continue

					oldPosition = anchor.position
					italicAngle = layer.italicAngle or 0.0
					italicDx = dy * tan(radians(italicAngle))

					anchor.position = NSPoint(
						oldPosition.x + dx + italicDx,
						oldPosition.y + dy
					)

					movedCount += 1
					glyphMovedCount += 1

			finally:
				glyph.endUndo()

			if glyphMovedCount:
				movedGlyphCount += 1

		Glyphs.redraw()

		self.w.info.set(
			"%s — %i masters in %i glyphs" %
			(anchorName, movedCount, movedGlyphCount)
		)


	def moveLeft(self, sender):
		self.move(-1, 0)

	def moveRight(self, sender):
		self.move(1, 0)

	def moveUp(self, sender):
		self.move(0, 1)

	def moveDown(self, sender):
		self.move(0, -1)


MoveAnchorInAllMasters()
