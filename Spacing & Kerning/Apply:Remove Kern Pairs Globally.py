# MenuTitle: Apply/Remove Kern Pairs Globally
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs, LTR
from vanilla import FloatingWindow, Button
from vanilla.dialogs import message


class GlobalKerningPairPanel(object):

	def __init__(self):
		self.margin = 6
		self.button_gap = self.margin / 2
		self.button_height = 32
		self.button_padding = 18

		self.apply_title = "Apply kern pair to all masters"
		self.remove_title = "Remove kern pair from all masters"

		self.button_width = self.required_button_width([
			self.apply_title,
			self.remove_title,
		])

		window_width = self.button_width + self.margin * 2
		window_height = self.button_height * 2 + self.margin * 2 + self.button_gap

		self.w = FloatingWindow(
			(window_width, window_height),
			"Apply/remove kern pairs globally",
			autosaveName="com.yourname.GlobalKerningPairPanel"
		)

		self.w.applyButton = Button(
			(
				self.margin,
				self.margin,
				self.button_width,
				self.button_height,
			),
			self.apply_title,
			callback=self.apply_callback
		)

		self.w.removeButton = Button(
			(
				self.margin,
				self.margin + self.button_height + self.button_gap,
				self.button_width,
				self.button_height,
			),
			self.remove_title,
			callback=self.remove_callback
		)

		self.make_button_blue(self.w.applyButton)

		self.center_window_in_app()
		self.w.open()
		self.w.makeKey()

	def required_button_width(self, titles):
		"""Return a tight shared button width based on the longest title."""
		return max([self.text_width(title) + self.button_padding for title in titles])

	def text_width(self, text):
		"""Measure button text width using the default macOS system font."""
		try:
			from AppKit import NSFont, NSString

			font = NSFont.systemFontOfSize_(13)
			size = NSString.alloc().initWithString_(text).sizeWithAttributes_(
				{"NSFont": font}
			)
			return int(size.width)

		except Exception:
			return len(text) * 7

	def make_button_blue(self, button):
		"""Make a vanilla button blue where supported."""
		try:
			button.getNSButton().setBezelColor_(Glyphs.colorObjectToNSColor("BLUE"))
		except Exception:
			pass

	def center_window_in_app(self):
		"""Center the floating panel in the Glyphs app window."""
		try:
			main_window = Glyphs.font.parent.windowController().window()
			main_frame = main_window.frame()
			panel = self.w.getNSWindow()
			panel_frame = panel.frame()

			x = main_frame.origin.x + (main_frame.size.width - panel_frame.size.width) / 2
			y = main_frame.origin.y + (main_frame.size.height - panel_frame.size.height) / 2

			panel.setFrameOrigin_((x, y))

		except Exception:
			try:
				self.w.center()
			except Exception:
				pass

	def current_pair_layers(self, font):
		"""Return the two layers around the cursor in the current Edit tab."""
		tab = font.currentTab

		if not tab or not tab.layers:
			return None, None

		cursor_index = tab.textCursor

		if cursor_index is None:
			return None, None

		left_index = cursor_index - 1
		right_index = cursor_index

		if left_index < 0 or right_index >= len(tab.layers):
			return None, None

		return tab.layers[left_index], tab.layers[right_index]

	def kerning_keys_for_pair(self, left_layer, right_layer):
		"""
		For a visual pair A V:
		- the left glyph contributes its right kerning key
		- the right glyph contributes its left kerning key
		"""
		left_glyph = left_layer.parent
		right_glyph = right_layer.parent

		left_key = left_glyph.rightKerningKey or left_glyph.name
		right_key = right_glyph.leftKerningKey or right_glyph.name

		return left_key, right_key

	def current_pair_data(self):
		"""Return font, active master, pair keys, and active-master kern value."""
		font = Glyphs.font

		if not font:
			message("No font open", "Open a font and try again.")
			return None

		active_master = font.selectedFontMaster

		if not active_master:
			message("No active master", "Could not determine the active master.")
			return None

		left_layer, right_layer = self.current_pair_layers(font)

		if not left_layer or not right_layer:
			message(
				"No kerning pair found",
				"Place the cursor between two glyphs in an Edit tab, then press a button."
			)
			return None

		left_key, right_key = self.kerning_keys_for_pair(left_layer, right_layer)

		value = font.kerningForPair(
			active_master.id,
			left_key,
			right_key,
			direction=LTR
		)

		return font, active_master, left_key, right_key, value

	def apply_callback(self, sender):
		pair_data = self.current_pair_data()

		if not pair_data:
			return

		font, active_master, left_key, right_key, value = pair_data

		if value is None:
			message(
				"No kerning value found",
				"The current pair has no explicit kerning value in the active master."
			)
			return

		font.disableUpdateInterface()

		try:
			for master in font.masters:
				font.setKerningForPair(
					master.id,
					left_key,
					right_key,
					value,
					direction=LTR
				)

		finally:
			font.enableUpdateInterface()

		Glyphs.showNotification(
			"Kerning applied to all masters",
			"%s / %s = %s" % (left_key, right_key, value)
		)

		print("Applied kern pair to all masters:")
		print("Left key:  %s" % left_key)
		print("Right key: %s" % right_key)
		print("Value:     %s" % value)
		print("Masters:   %s" % ", ".join([master.name for master in font.masters]))

	def remove_callback(self, sender):
		pair_data = self.current_pair_data()

		if not pair_data:
			return

		font, active_master, left_key, right_key, value = pair_data

		font.disableUpdateInterface()

		try:
			for master in font.masters:
				font.removeKerningForPair(
					master.id,
					left_key,
					right_key,
					direction=LTR
				)

		finally:
			font.enableUpdateInterface()

		Glyphs.showNotification(
			"Kerning removed from all masters",
			"%s / %s" % (left_key, right_key)
		)

		print("Removed kern pair from all masters:")
		print("Left key:  %s" % left_key)
		print("Right key: %s" % right_key)
		print("Masters:   %s" % ", ".join([master.name for master in font.masters]))


GlobalKerningPairPanel()