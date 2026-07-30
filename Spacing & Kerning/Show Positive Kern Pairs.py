# MenuTitle: Show Positive Kern Pairs
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
from vanilla.dialogs import message


def glyph_for_kerning_key(font, key, side, group_cache):
	"""Return a display glyph for a glyph ID or kerning-group key."""
	if not key:
		return None

	if not key.startswith("@"):
		glyph = font.glyphForId_(key)
		if glyph:
			return glyph
		return font.glyphs[key]

	cache_key = (side, key)
	if cache_key in group_cache:
		return group_cache[cache_key]

	group_name = key.split("_", 2)[-1]
	group_attribute = (
		"rightKerningGroup" if side == "left" else "leftKerningGroup"
	)
	candidates = [
		glyph
		for glyph in font.glyphs
		if getattr(glyph, group_attribute) == group_name
	]

	# Prefer the glyph whose name matches the group, then an exporting glyph.
	glyph = next(
		(candidate for candidate in candidates if candidate.name == group_name),
		None,
	)
	if not glyph:
		glyph = next(
			(candidate for candidate in candidates if candidate.export),
			None,
		)
	if not glyph and candidates:
		glyph = candidates[0]

	group_cache[cache_key] = glyph
	return glyph


def show_positive_kern_pairs():
	font = Glyphs.font

	if not font:
		message("No font open", "Open a font and try again.")
		return

	master = font.selectedFontMaster
	if not master:
		message("No active master", "Could not determine the active master.")
		return

	try:
		master_kerning = font.kerning[master.id]
	except Exception:
		master_kerning = None

	if not master_kerning:
		message(
			"No positive kern pairs",
			'The active master "%s" has no positive kern pairs.' % master.name,
		)
		return

	group_cache = {}
	pairs = []

	for left_key, right_pairs in master_kerning.items():
		for right_key, value in right_pairs.items():
			if value <= 0:
				continue

			left_glyph = glyph_for_kerning_key(
				font, left_key, "left", group_cache
			)
			right_glyph = glyph_for_kerning_key(
				font, right_key, "right", group_cache
			)

			if left_glyph and right_glyph:
				pairs.append((left_glyph.name, right_glyph.name))

	if not pairs:
		message(
			"No positive kern pairs",
			'The active master "%s" has no displayable positive kern pairs.'
			% master.name,
		)
		return

	pairs.sort(key=lambda pair: (pair[0].lower(), pair[1].lower()))
	tab_text = "\n".join(
		"/%s/%s" % (left_name, right_name)
		for left_name, right_name in pairs
	)
	font.newTab(tab_text)


show_positive_kern_pairs()
