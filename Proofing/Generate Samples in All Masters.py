# MenuTitle: Generate Samples in All Masters
# A panel that allows you to input sample strings in all masters at once, opening in the same tab.

# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs, GSControlLayer, Message
from AppKit import (
	NSFont,
	NSScreen,
	NSColor,
	NSMutableAttributedString,
	NSForegroundColorAttributeName,
	NSFontAttributeName,
)
import vanilla


class GenerateSampleTextInAllMasters:

	# -----------------------------
	# Layout
	# -----------------------------

	WINDOW_WIDTH = 500

	MARGIN = 8
	ROW_HEIGHT = 21
	ROW_GAP = 3
	LABEL_HEIGHT = 15

	GLOBAL_LABEL_TO_INPUT_GAP = 6
	GLOBAL_INPUT_TO_ROWS_GAP = 8
	ROWS_TO_BUTTON_GAP = 6

	BUTTON_WIDTH = 154
	BUTTON_HEIGHT = 30

	REORDER_BUTTON_WIDTH = 22
	REORDER_BUTTON_GAP = 2

	SHOW_X = MARGIN + 6
	SHOW_WIDTH = 58

	EDIT_X = MARGIN + 64
	EDIT_WIDTH = 48

	MASTER_NAME_X = MARGIN + 114
	MASTER_NAME_WIDTH = 80

	INPUT_X = MARGIN + 196

	# -----------------------------
	# Text
	# -----------------------------

	WINDOW_TITLE = "Generate sample text in all masters"
	GLOBAL_LABEL = "Global sample string"
	GENERATE_BUTTON_TITLE = "Generate sample strings"

	SHOW_TITLE = "Show"
	EDIT_TITLE = "Edit"

	# -----------------------------
	# Setup
	# -----------------------------

	def __init__(self):
		self.font = Glyphs.font

		if not self.font:
			Message(
				title="No Font Open",
				message="Please open a font first.",
				OKButton="OK"
			)
			return

		self.globalText = ""
		self.masterData = self.makeMasterData()
		self.masterRows = []

		self.setFontsAndColors()
		self.buildWindow()

	def makeMasterData(self):
		return [
			{
				"master": master,
				"text": "",
				"isEdited": False,
				"isShown": True,
			}
			for master in self.font.masters
		]

	def setFontsAndColors(self):
		self.labelFont = NSFont.systemFontOfSize_(12)
		self.boldLabelFont = NSFont.boldSystemFontOfSize_(12)
		self.buttonFont = NSFont.systemFontOfSize_(12)

		self.activeTextColor = NSColor.labelColor()
		self.inactiveTextColor = NSColor.secondaryLabelColor()
		self.disabledTextColor = NSColor.tertiaryLabelColor()

	# -----------------------------
	# Window
	# -----------------------------

	def buildWindow(self):
		self.masterRows = []

		windowHeight = self.windowHeight()
		self.windowHeightValue = windowHeight

		self.w = vanilla.FloatingWindow(
			(self.WINDOW_WIDTH, windowHeight),
			self.WINDOW_TITLE
		)

		y = self.MARGIN

		self.addGlobalControls(y)
		y += self.LABEL_HEIGHT
		y += self.GLOBAL_LABEL_TO_INPUT_GAP
		y += self.ROW_HEIGHT
		y += self.GLOBAL_INPUT_TO_ROWS_GAP

		for index, data in enumerate(self.masterData):
			self.addMasterRow(index, data, y)
			y += self.ROW_HEIGHT + self.ROW_GAP

		y += self.ROWS_TO_BUTTON_GAP
		self.addGenerateButton(y)

		self.w.setDefaultButton(self.w.generateButton)
		self.positionWindowTopCenter()
		self.w.open()
		self.w.makeKey()

	def windowHeight(self):
		numberOfMasters = len(self.masterData)

		return (
			self.MARGIN
			+ self.LABEL_HEIGHT
			+ self.GLOBAL_LABEL_TO_INPUT_GAP
			+ self.ROW_HEIGHT
			+ self.GLOBAL_INPUT_TO_ROWS_GAP
			+ numberOfMasters * (self.ROW_HEIGHT + self.ROW_GAP)
			+ self.ROWS_TO_BUTTON_GAP
			+ self.BUTTON_HEIGHT
			+ self.MARGIN
		)

	def addGlobalControls(self, y):
		self.w.globalLabel = vanilla.TextBox(
			(self.MARGIN, y, -self.MARGIN, self.LABEL_HEIGHT),
			self.GLOBAL_LABEL,
			sizeStyle="small"
		)
		self.setTextBoxFont(self.w.globalLabel, self.boldLabelFont)

		y += self.LABEL_HEIGHT + self.GLOBAL_LABEL_TO_INPUT_GAP

		self.w.globalInput = vanilla.EditText(
			(self.MARGIN, y, -self.MARGIN, self.ROW_HEIGHT),
			self.globalText,
			callback=self.globalTextChanged,
			sizeStyle="small"
		)
		self.setEditTextFont(self.w.globalInput, self.labelFont)

	def addMasterRow(self, index, data, y):
		reorderX = self.reorderX()
		inputRightMargin = self.WINDOW_WIDTH - reorderX + 4

		master = data["master"]

		showCheckbox = vanilla.CheckBox(
			(self.SHOW_X, y + 1, self.SHOW_WIDTH, self.ROW_HEIGHT),
			self.SHOW_TITLE,
			value=data["isShown"],
			callback=self.showCheckboxChanged,
			sizeStyle="small"
		)

		editCheckbox = vanilla.CheckBox(
			(self.EDIT_X, y + 1, self.EDIT_WIDTH, self.ROW_HEIGHT),
			self.EDIT_TITLE,
			value=data["isEdited"],
			callback=self.editCheckboxChanged,
			sizeStyle="small"
		)

		masterLabel = vanilla.TextBox(
			(self.MASTER_NAME_X, y + 3, self.MASTER_NAME_WIDTH, self.LABEL_HEIGHT),
			master.name,
			sizeStyle="small"
		)

		inputField = vanilla.EditText(
			(self.INPUT_X, y, -inputRightMargin, self.ROW_HEIGHT),
			data["text"],
			sizeStyle="small"
		)

		upButton = vanilla.Button(
			(reorderX, y, self.REORDER_BUTTON_WIDTH, self.ROW_HEIGHT),
			"↑",
			callback=self.moveMasterUp,
			sizeStyle="small"
		)

		downButton = vanilla.Button(
			(
				reorderX + self.REORDER_BUTTON_WIDTH + self.REORDER_BUTTON_GAP,
				y,
				self.REORDER_BUTTON_WIDTH,
				self.ROW_HEIGHT
			),
			"↓",
			callback=self.moveMasterDown,
			sizeStyle="small"
		)

		self.storeRowControls(index, {
			"master": master,
			"showCheckbox": showCheckbox,
			"editCheckbox": editCheckbox,
			"label": masterLabel,
			"input": inputField,
			"upButton": upButton,
			"downButton": downButton,
		})

	def storeRowControls(self, index, row):
		self.attachRowToWindow(index, row)
		self.tagRowControls(index, row)
		self.styleRowControls(row)
		self.updateMoveButtons(index, row)
		self.updateRowAppearance(row, self.masterData[index])

		self.masterRows.append(row)

	def attachRowToWindow(self, index, row):
		for key, control in row.items():
			if key == "master":
				continue

			setattr(self.w, "%s_%i" % (key, index), control)

	def tagRowControls(self, index, row):
		row["showCheckbox"].masterIndex = index
		row["editCheckbox"].masterIndex = index
		row["upButton"].masterIndex = index
		row["downButton"].masterIndex = index

	def styleRowControls(self, row):
		self.setCheckboxFont(row["showCheckbox"], self.labelFont)
		self.setCheckboxFont(row["editCheckbox"], self.labelFont)
		self.setTextBoxFont(row["label"], self.labelFont)
		self.setEditTextFont(row["input"], self.labelFont)
		self.setButtonFont(row["upButton"], self.labelFont)
		self.setButtonFont(row["downButton"], self.labelFont)

	def updateMoveButtons(self, index, row):
		row["upButton"].enable(index > 0)
		row["downButton"].enable(index < len(self.masterData) - 1)

	def addGenerateButton(self, y):
		self.w.generateButton = vanilla.Button(
			(
				-self.MARGIN - self.BUTTON_WIDTH,
				y,
				self.BUTTON_WIDTH,
				self.BUTTON_HEIGHT
			),
			self.GENERATE_BUTTON_TITLE,
			callback=self.generateSampleStrings
		)

		self.setButtonFont(self.w.generateButton, self.buttonFont)

		try:
			self.w.generateButton.getNSButton().setBezelStyle_(1)
			self.w.generateButton.getNSButton().setKeyEquivalent_("\r")
		except Exception:
			pass

	def reorderX(self):
		return (
			self.WINDOW_WIDTH
			- self.MARGIN
			- self.REORDER_BUTTON_WIDTH * 2
			- self.REORDER_BUTTON_GAP
		)

	# -----------------------------
	# Styling
	# -----------------------------

	def setCheckboxFont(self, checkbox, font):
		try:
			checkbox.getNSButton().setFont_(font)
		except Exception:
			pass

	def setTextBoxFont(self, textBox, font):
		try:
			textBox.getNSTextField().setFont_(font)
		except Exception:
			pass

	def setEditTextFont(self, editText, font):
		try:
			editText.getNSTextField().setFont_(font)
		except Exception:
			pass

	def setButtonFont(self, button, font):
		try:
			button.getNSButton().setFont_(font)
		except Exception:
			pass

	def attributedText(self, text, color, font):
		attributedString = NSMutableAttributedString.alloc().initWithString_(text)
		fullRange = (0, len(text))

		attributedString.addAttribute_value_range_(
			NSForegroundColorAttributeName,
			color,
			fullRange
		)

		attributedString.addAttribute_value_range_(
			NSFontAttributeName,
			font,
			fullRange
		)

		return attributedString

	def setCheckboxTitleColor(self, checkbox, title, color):
		try:
			checkbox.getNSButton().setAttributedTitle_(
				self.attributedText(title, color, self.labelFont)
			)
		except Exception:
			pass

	def updateRowAppearance(self, row, data):
		isShown = data["isShown"]
		isEdited = data["isEdited"]

		if not isShown:
			color = self.disabledTextColor
		elif isEdited:
			color = self.activeTextColor
		else:
			color = self.inactiveTextColor

		self.setCheckboxTitleColor(
			row["showCheckbox"],
			self.SHOW_TITLE,
			self.activeTextColor
		)

		self.setCheckboxTitleColor(
			row["editCheckbox"],
			self.EDIT_TITLE,
			color
		)

		try:
			row["label"].getNSTextField().setTextColor_(color)
		except Exception:
			pass

		row["editCheckbox"].enable(isShown)
		row["input"].enable(isShown and isEdited)

	# -----------------------------
	# Positioning
	# -----------------------------

	def positionWindowTopCenter(self):
		try:
			frame = Glyphs.currentDocument.windowController().window().frame()
			x = frame.origin.x + (frame.size.width - self.WINDOW_WIDTH) / 2
			y = frame.origin.y + frame.size.height - self.windowHeightValue - 90
		except Exception:
			try:
				frame = NSScreen.mainScreen().visibleFrame()
				x = frame.origin.x + (frame.size.width - self.WINDOW_WIDTH) / 2
				y = frame.origin.y + frame.size.height - self.windowHeightValue - 90
			except Exception:
				return

		self.w.getNSWindow().setFrameTopLeftPoint_(
			(x, y + self.windowHeightValue)
		)

	# -----------------------------
	# State
	# -----------------------------

	def captureCurrentState(self):
		self.globalText = self.w.globalInput.get()

		for index, row in enumerate(self.masterRows):
			self.masterData[index]["text"] = row["input"].get()
			self.masterData[index]["isEdited"] = row["editCheckbox"].get()
			self.masterData[index]["isShown"] = row["showCheckbox"].get()

	def rebuildWindow(self):
		self.captureCurrentState()
		self.w.close()
		self.buildWindow()

	def syncUneditedRowsToGlobalText(self):
		for index, row in enumerate(self.masterRows):
			if not row["editCheckbox"].get():
				row["input"].set(self.globalText)
				self.masterData[index]["text"] = self.globalText

	# -----------------------------
	# Callbacks
	# -----------------------------

	def globalTextChanged(self, sender):
		self.globalText = sender.get()
		self.syncUneditedRowsToGlobalText()

	def showCheckboxChanged(self, sender):
		index = sender.masterIndex
		row = self.masterRows[index]

		self.masterData[index]["isShown"] = sender.get()
		self.masterData[index]["isEdited"] = row["editCheckbox"].get()

		self.updateRowAppearance(row, self.masterData[index])

	def editCheckboxChanged(self, sender):
		index = sender.masterIndex
		row = self.masterRows[index]

		isEdited = sender.get()

		self.masterData[index]["isEdited"] = isEdited
		self.masterData[index]["isShown"] = row["showCheckbox"].get()

		if not isEdited:
			row["input"].set(self.w.globalInput.get())
			self.masterData[index]["text"] = self.w.globalInput.get()

		self.updateRowAppearance(row, self.masterData[index])

	def moveMasterUp(self, sender):
		index = sender.masterIndex

		if index <= 0:
			return

		self.captureCurrentState()
		self.masterData[index - 1], self.masterData[index] = (
			self.masterData[index],
			self.masterData[index - 1],
		)
		self.w.close()
		self.buildWindow()

	def moveMasterDown(self, sender):
		index = sender.masterIndex

		if index >= len(self.masterData) - 1:
			return

		self.captureCurrentState()
		self.masterData[index + 1], self.masterData[index] = (
			self.masterData[index],
			self.masterData[index + 1],
		)
		self.w.close()
		self.buildWindow()

	# -----------------------------
	# Glyph Handling
	# -----------------------------

	def glyphForCharacter(self, character):
		unicodeValue = "%04X" % ord(character)
		return self.font.glyphForUnicode_(unicodeValue)

	def layersForTextInMaster(self, text, master):
		layers = []
		missingCharacters = set()

		for character in text:
			glyph = self.glyphForCharacter(character)

			if glyph:
				layer = glyph.layers[master.id]
				if layer:
					layers.append(layer)
			else:
				missingCharacters.add(character)

		return layers, missingCharacters

	# -----------------------------
	# Generate
	# -----------------------------

	def generateSampleStrings(self, sender):
		self.captureCurrentState()

		shownMasterData = [
			data for data in self.masterData
			if data["isShown"]
		]

		if not shownMasterData:
			Message(
				title="No Masters Shown",
				message="Please show at least one master.",
				OKButton="OK"
			)
			return

		allLayers = []
		allMissingCharacters = set()

		for index, data in enumerate(shownMasterData):
			layers, missingCharacters = self.layersForTextInMaster(
				data["text"],
				data["master"]
			)

			allLayers.extend(layers)
			allMissingCharacters.update(missingCharacters)

			if index < len(shownMasterData) - 1:
				allLayers.append(GSControlLayer.newline())

		if not allLayers:
			Message(
				title="No Glyphs Found",
				message="Please enter a sample string first.",
				OKButton="OK"
			)
			return

		tab = self.font.newTab()
		tab.layers = allLayers

		self.reportMissingCharacters(allMissingCharacters)

	def reportMissingCharacters(self, missingCharacters):
		if not missingCharacters:
			return

		print("Missing characters:")
		for character in sorted(missingCharacters):
			print("‘%s’ U+%04X" % (character, ord(character)))


GenerateSampleTextInAllMasters()