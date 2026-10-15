# MenuTitle: Apply/Remove Kern Pairs Globally
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs, GSLTR
from vanilla import FloatingWindow, Button
from vanilla.dialogs import message


class GlobalKerningPairPanel(object):

	def __init__(self):
		self.margin = 6
		self.button_gap = self.margin / 2
		self.button_height = 32
		self.button_padding = 18

		self.apply_title = "🔮 Apply this kern pair to all masters"
		self.remove_master_title = "🧼 Remove kern pair from this master"
		self.remove_all_title = "💣 Remove kern pair from all masters"

		self.button_width = self.required_button_width([
			self.apply_title,
			self.remove_all_title,
			self.remove_master_title,
		])

		window_width = self.button_width + self.margin * 2
		window_height = (
			self.button_height * 3
			+ self.margin * 2
			+ self.button_gap * 2
		)

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

		self.w.removeAllButton = Button(
			(
				self.margin,
				self.margin + self.button_height + self.button_gap,
				self.button_width,
				self.button_height,
			),
			self.remove_all_title,
			callback=self.remove_all_callback
		)

		self.w.removeMasterButton = Button(
			(
				self.margin,
				self.margin + (self.button_height + self.button_gap) * 2,
				self.button_width,
				self.button_height,
			),
			self.remove_master_title,
			callback=self.remove_master_callback
		)

		self.set_button_color(self.w.applyButton, "BLUE")
		self.set_button_color(self.w.removeAllButton, "RED")
		self.set_button_color(self.w.removeMasterButton, "ORANGE")

		self.center_window_in_app()
		self.w.open()
		self.w.makeKey()

	def required_button_width(self, titles):
		"""Return a shared button width based on the longest title."""
		return max(
			[self.text_width(title) + self.button_padding for title in titles]
		)

	def text_width(self, text):
		"""Measure button text using the default macOS system font."""
		try:
			from AppKit import NSFont, NSString

			font = NSFont.systemFontOfSize_(13)
			size = (
				NSString.alloc()
				.initWithString_(text)
				.sizeWithAttributes_({"NSFont": font})
			)

			return int(size.width)

		except Exception:
			return len(text) * 7

	def set_button_color(self, button, color_name):
		"""Set the button bezel color where supported."""
		try:
			ns_color = Glyphs.colorObjectToNSColor(color_name)
			button.getNSButton().setBezelColor_(ns_color)
		except Exception:
			pass

	def center_window_in_app(self):
		"""Center the floating panel in the main Glyphs window."""
		try:
			main_window = Glyphs.font.parent.windowController().window()
			main_frame = main_window.frame()

			panel = self.w.getNSWindow()
			panel_frame = panel.frame()

			x = (
				main_frame.origin.x
				+ (main_frame.size.width - panel_frame.size.width) / 2
			)

			y = (
				main_frame.origin.y
				+ (main_frame.size.height - panel_frame.size.height) / 2
			)

			panel.setFrameOrigin_((x, y))

		except Exception:
			try:
				self.w.center()
			except Exception:
				pass

	def current_pair_layers(self, font):
		"""
		Return the two rendered layers around the cursor.

		layersCursor indexes the rendered glyph layers directly. This is
		important for oldstyle figures, slash-entered glyph names, ligatures,
		and glyphs produced through active OpenType features.
		"""
		tab = font.currentTab

		if not tab:
			return None, None

		layers = tab.layers

		if not layers:
			return None, None

		try:
			cursor_index = tab.layersCursor
		except Exception:
			message(
				"Glyphs version not supported",
				"This script requires a Glyphs version that supports layersCursor."
			)
			return None, None

		if cursor_index is None:
			return None, None

		left_index = cursor_index - 1
		right_index = cursor_index

		if left_index < 0 or right_index >= len(layers):
			return None, None

		left_layer = layers[left_index]
		right_layer = layers[right_index]

		if not left_layer or not right_layer:
			return None, None

		if not left_layer.parent or not right_layer.parent:
			return None, None

		return left_layer, right_layer

	def kerning_keys_for_pair(self, left_layer, right_layer):
		"""
		For a visual pair A V:

		- The left glyph contributes its right kerning key.
		- The right glyph contributes its left kerning key.
		"""
		left_glyph = left_layer.parent
		right_glyph = right_layer.parent

		left_key = left_glyph.rightKerningKey or left_glyph.name
		right_key = right_glyph.leftKerningKey or right_glyph.name

		return left_key, right_key

	def current_pair_data(self):
		"""
		Return the font, active master, pair keys, and active-master value.
		"""
		font = Glyphs.font

		if not font:
			message(
				"No font open",
				"Open a font and try again."
			)
			return None

		active_master = font.selectedFontMaster

		if not active_master:
			message(
				"No active master",
				"Could not determine the active master."
			)
			return None

		left_layer, right_layer = self.current_pair_layers(font)

		if not left_layer or not right_layer:
			message(
				"No kerning pair found",
				"Place the cursor between two glyphs in an Edit tab, "
				"then press a button."
			)
			return None

		left_key, right_key = self.kerning_keys_for_pair(
			left_layer,
			right_layer
		)

		value = font.kerningForPair(
			active_master.id,
			left_key,
			right_key,
			direction=GSLTR
		)

		return (
			font,
			active_master,
			left_key,
			right_key,
			value,
		)

	def apply_callback(self, sender):
		pair_data = self.current_pair_data()

		if not pair_data:
			return

		font, active_master, left_key, right_key, value = pair_data

		if value is None:
			message(
				"No kerning value found",
				"The current pair has no kerning value in the active master."
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
					direction=GSLTR
				)

		finally:
			font.enableUpdateInterface()

		Glyphs.showNotification(
			"Kerning applied to all masters",
			"%s / %s = %s" % (
				left_key,
				right_key,
				value
			)
		)

		print("Applied kern pair to all masters:")
		print("Left key:  %s" % left_key)
		print("Right key: %s" % right_key)
		print("Value:     %s" % value)
		print(
			"Masters:   %s"
			% ", ".join([master.name for master in font.masters])
		)

	def remove_master_callback(self, sender):
		pair_data = self.current_pair_data()

		if not pair_data:
			return

		font, active_master, left_key, right_key, value = pair_data

		font.disableUpdateInterface()

		try:
			font.removeKerningForPair(
				active_master.id,
				left_key,
				right_key,
				direction=GSLTR
			)

		finally:
			font.enableUpdateInterface()

		Glyphs.showNotification(
			"Kerning removed from this master",
			"%s / %s in %s" % (
				left_key,
				right_key,
				active_master.name
			)
		)

		print("Removed kern pair from this master:")
		print("Left key:  %s" % left_key)
		print("Right key: %s" % right_key)
		print("Master:    %s" % active_master.name)

	def remove_all_callback(self, sender):
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
					direction=GSLTR
				)

		finally:
			font.enableUpdateInterface()

		Glyphs.showNotification(
			"Kerning removed from all masters",
			"%s / %s" % (
				left_key,
				right_key
			)
		)

		print("Removed kern pair from all masters:")
		print("Left key:  %s" % left_key)
		print("Right key: %s" % right_key)
		print(
			"Masters:   %s"
			% ", ".join([master.name for master in font.masters])
		)


GlobalKerningPairPanel()
