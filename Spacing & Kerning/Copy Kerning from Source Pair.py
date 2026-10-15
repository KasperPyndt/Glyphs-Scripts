# MenuTitle: Copy Kerning From Source Pair
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs, GSLTR
from vanilla import FloatingWindow, TextBox, EditText, Button, CheckBox
from vanilla.dialogs import message


class CopyKerningFromSourcePair(object):

	def __init__(self):
		self.font = Glyphs.font

		margin = 10
		label_h = 18
		input_h = 22
		check_h = 20
		button_h = 30
		gap = 8
		small_gap = 3

		window_w = 260
		window_h = (
			margin
			+ label_h + small_gap + input_h
			+ gap
			+ label_h + small_gap + input_h
			+ gap
			+ check_h
			+ gap
			+ button_h
			+ margin
		)

		self.w = FloatingWindow(
			(window_w, window_h),
			"Copy kern pair values",
		)

		y = margin

		self.w.sourceLabel = TextBox(
			(margin, y, -margin, label_h),
			"Source pair",
		)

		y += label_h + small_gap

		self.w.sourcePair = EditText(
			(margin, y, -margin, input_h),
			placeholder="e.g. Ev, E v, E.sc v",
		)

		y += input_h + gap

		self.w.adjustmentLabel = TextBox(
			(margin, y, -margin, label_h),
			"Adjustment",
		)

		y += label_h + small_gap

		self.w.adjustment = EditText(
			(margin, y, -margin, input_h),
			placeholder="e.g. 10 or -10",
		)

		y += input_h + gap

		self.w.allMasters = CheckBox(
			(margin, y, -margin, check_h),
			"Copy in all masters",
			value=True,
		)

		y += check_h + gap

		self.w.copyButton = Button(
			(margin, y, -margin, button_h),
			"Copy to current pair",
			callback=self.copyCallback,
		)

		self.w.open()


	# -------------------------
	# Pair parsing
	# -------------------------

	def glyphForToken(self, token):
		token = token.strip()

		if not token:
			return None

		glyph = self.font.glyphs[token]
		if glyph:
			return glyph

		if len(token) == 1:
			unicodeValue = "%04X" % ord(token)
			glyph = self.font.glyphForUnicode_(unicodeValue)
			if glyph:
				return glyph

		return None


	def parsePair(self, pairString):
		pairString = pairString.strip()

		if not pairString:
			message("No source pair", "Please enter a source pair.")
			return None, None

		for separator in ["/", ",", "+"]:
			pairString = pairString.replace(separator, " ")

		parts = [p for p in pairString.split() if p]

		if len(parts) == 2:
			leftToken, rightToken = parts

		elif len(parts) == 1:
			text = parts[0]

			if len(text) == 2:
				leftToken = text[0]
				rightToken = text[1]
			else:
				message(
					"Could not read source pair",
					'Use two glyph names, e.g. "E.sc v", or two characters, e.g. "Ev".',
				)
				return None, None

		else:
			message(
				"Could not read source pair",
				'Use two glyph names, e.g. "E.sc v", or two characters, e.g. "Ev".',
			)
			return None, None

		leftGlyph = self.glyphForToken(leftToken)
		rightGlyph = self.glyphForToken(rightToken)

		if not leftGlyph:
			message("Glyph not found", 'Could not find left glyph: "%s"' % leftToken)
			return None, None

		if not rightGlyph:
			message("Glyph not found", 'Could not find right glyph: "%s"' % rightToken)
			return None, None

		return leftGlyph, rightGlyph


	def adjustmentValue(self):
		rawValue = self.w.adjustment.get().strip()

		if not rawValue:
			return 0

		try:
			return int(rawValue)
		except:
			try:
				return float(rawValue)
			except:
				message(
					"Invalid adjustment",
					'Please enter a number, e.g. "10", "-10", or leave it empty.',
				)
				return None


	# -------------------------
	# Target pair from Edit View
	# -------------------------

	def currentTargetPair(self):
		tab = self.font.currentTab

		if not tab:
			message("No Edit tab", "Open an Edit tab and place the cursor between the target pair.")
			return None, None

		layers = list(tab.layers)
		cursorIndex = tab.layersCursor

		if cursorIndex is None:
			message("No cursor position", "Place the text cursor between the target pair.")
			return None, None

		if cursorIndex <= 0 or cursorIndex >= len(layers):
			message(
				"No target pair",
				"Place the text cursor between two glyphs in the Edit tab.",
			)
			return None, None

		leftLayer = layers[cursorIndex - 1]
		rightLayer = layers[cursorIndex]

		if not leftLayer or not rightLayer:
			message("No target pair", "Could not read the two glyphs around the cursor.")
			return None, None

		leftGlyph = leftLayer.parent
		rightGlyph = rightLayer.parent

		if not leftGlyph or not rightGlyph:
			message("No target pair", "Could not read the two glyphs around the cursor.")
			return None, None

		return leftGlyph, rightGlyph


	# -------------------------
	# Kerning helpers
	# -------------------------

	def removeDuplicates(self, keys):
		cleanKeys = []

		for key in keys:
			if key and key not in cleanKeys:
				cleanKeys.append(key)

		return cleanKeys


	def sourceKeysToTry(self, leftGlyph, rightGlyph):
		leftKeys = []
		rightKeys = []

		# Group-aware source keys first.
		if leftGlyph.rightKerningKey:
			leftKeys.append(leftGlyph.rightKerningKey)

		if rightGlyph.leftKerningKey:
			rightKeys.append(rightGlyph.leftKerningKey)

		# Glyph-specific fallbacks.
		leftKeys.append(leftGlyph.name)
		rightKeys.append(rightGlyph.name)

		return self.removeDuplicates(leftKeys), self.removeDuplicates(rightKeys)


	def kerningForSourcePair(self, masterID, leftGlyph, rightGlyph):
		leftKeys, rightKeys = self.sourceKeysToTry(leftGlyph, rightGlyph)

		for leftKey in leftKeys:
			for rightKey in rightKeys:
				value = self.font.kerningForPair(
					masterID,
					leftKey,
					rightKey,
					GSLTR,
				)

				if value is not None:
					return value, leftKey, rightKey

		return None, None, None


	def targetKeysForWriting(self, leftGlyph, rightGlyph):
		"""
		Use group keys for the target pair whenever possible.

		This avoids writing glyph-to-glyph exception kerning,
		which is what opens the little kerning lock in Glyphs.
		"""

		leftKey = leftGlyph.rightKerningKey
		rightKey = rightGlyph.leftKerningKey

		missingGroups = []

		if not leftKey:
			leftKey = leftGlyph.name
			missingGroups.append(leftGlyph.name)

		if not rightKey:
			rightKey = rightGlyph.name
			missingGroups.append(rightGlyph.name)

		return leftKey, rightKey, missingGroups


	def setTargetKerning(self, masterID, leftGlyph, rightGlyph, value):
		leftKey, rightKey, missingGroups = self.targetKeysForWriting(leftGlyph, rightGlyph)

		self.font.setKerningForPair(
			masterID,
			leftKey,
			rightKey,
			value,
			GSLTR,
		)

		return leftKey, rightKey, missingGroups


	# -------------------------
	# Main action
	# -------------------------

	def copyCallback(self, sender):
		self.font = Glyphs.font

		if not self.font:
			message("No font open", "Open a font first.")
			return

		sourceLeft, sourceRight = self.parsePair(self.w.sourcePair.get())
		if not sourceLeft or not sourceRight:
			return

		adjustment = self.adjustmentValue()
		if adjustment is None:
			return

		targetLeft, targetRight = self.currentTargetPair()
		if not targetLeft or not targetRight:
			return

		if self.w.allMasters.get():
			masters = self.font.masters
		else:
			masters = [self.font.selectedFontMaster]

		copied = []
		missingSource = []
		missingTargetGroups = []

		print("")
		print("Copy Kerning From Source Pair")
		print("--------------------------------")
		print("Source pair: %s / %s" % (sourceLeft.name, sourceRight.name))
		print("Target pair: %s / %s" % (targetLeft.name, targetRight.name))
		print("Adjustment:  %+s" % adjustment)
		print("")

		for master in masters:
			sourceValue, sourceLeftKey, sourceRightKey = self.kerningForSourcePair(
				master.id,
				sourceLeft,
				sourceRight,
			)

			if sourceValue is None:
				missingSource.append(master.name)
				continue

			targetValue = sourceValue + adjustment

			targetLeftKey, targetRightKey, missingGroups = self.setTargetKerning(
				master.id,
				targetLeft,
				targetRight,
				targetValue,
			)

			for glyphName in missingGroups:
				if glyphName not in missingTargetGroups:
					missingTargetGroups.append(glyphName)

			copied.append(master.name)

			print("%s:" % master.name)
			print("  Read from:    %s / %s" % (sourceLeftKey, sourceRightKey))
			print("  Wrote to:     %s / %s" % (targetLeftKey, targetRightKey))
			print("  Source value: %s" % sourceValue)
			print("  Adjustment:   %+s" % adjustment)
			print("  Final value:  %s" % targetValue)
			print("")

		if copied:
			Glyphs.showNotification(
				"Kerning copied",
				"%s %s %+s → %s %s" % (
					sourceLeft.name,
					sourceRight.name,
					adjustment,
					targetLeft.name,
					targetRight.name,
				),
			)

		if missingSource:
			message(
				"Some masters had no source kerning",
				"No kerning value was found for the source pair in:\n\n%s" % "\n".join(missingSource),
			)

		if missingTargetGroups:
			message(
				"Target glyph missing kerning group",
				"The following target glyphs had no kerning group on the relevant side, so glyph-level kerning was used for them:\n\n%s" % "\n".join(missingTargetGroups),
			)


CopyKerningFromSourcePair()
