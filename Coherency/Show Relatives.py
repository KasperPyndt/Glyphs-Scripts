# MenuTitle: Show Possible Relatives
# Shows all potential relatives (conventionally) to selected glyph, and adds the option to generate a few sample words in English with said glyphs.


# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
from AppKit import NSBeep

try:
	from vanilla import FloatingWindow, Button
except Exception:
	FloatingWindow = None
	Button = None


# ------------------------
# Data
# ------------------------

RELATIVES = {
	# Lowercase round / bowl logic
	"o": ["o", "c", "e", "a", "g", "b", "d", "p", "q"],
	"c": ["c", "o", "e", "a", "g"],
	"e": ["e", "o", "c", "a", "g"],
	"a": ["a", "o", "c", "e", "g", "d", "q"],
	"g": ["g", "o", "c", "e", "a", "q"],

	"b": ["b", "d", "p", "q", "o", "a", "h", "l"],
	"d": ["d", "b", "p", "q", "o", "a"],
	"p": ["p", "b", "d", "q", "o"],
	"q": ["q", "b", "d", "p", "o", "g", "a"],

	# Lowercase shoulder / arch logic
	"n": ["n", "h", "m", "r", "u"],
	"h": ["h", "n", "m", "r", "u", "b"],
	"m": ["m", "n", "h", "r"],
	"r": ["r", "n", "h", "m", "f", "t"],
	"u": ["u", "n", "h", "m", "y"],

	# Lowercase stems / simple verticals
	"i": ["i", "l", "j", "f", "t"],
	"l": ["l", "i", "j", "f", "t", "h", "b"],
	"j": ["j", "i", "l"],
	"f": ["f", "t", "i", "l", "r"],
	"t": ["t", "f", "i", "l", "r"],

	# Lowercase diagonals / angular logic
	"v": ["v", "w", "y", "x", "k", "z"],
	"w": ["w", "v", "y", "x", "k", "z"],
	"y": ["y", "v", "w", "x", "k", "u"],
	"x": ["x", "v", "w", "y", "k", "z"],
	"k": ["k", "x", "v", "w", "y", "z", "h"],
	"z": ["z", "v", "w", "x", "k"],

	# Lowercase special
	"s": ["s", "a", "c", "e", "g"],

	# Uppercase round
	"O": ["O", "C", "G", "Q", "D"],
	"C": ["C", "O", "G", "Q", "S"],
	"G": ["G", "O", "C", "Q", "S"],
	"Q": ["Q", "O", "C", "G"],

	# Uppercase stem + bowl
	"D": ["D", "O", "B", "P", "R"],
	"B": ["B", "P", "R", "D"],
	"P": ["P", "B", "R", "D"],
	"R": ["R", "P", "B", "D", "K"],

	# Uppercase vertical / horizontal
	"E": ["E", "F", "H", "I", "L", "T"],
	"F": ["F", "E", "H", "I", "L", "T"],
	"H": ["H", "E", "F", "I", "L", "T", "N"],
	"I": ["I", "H", "L", "T", "E", "F"],
	"L": ["L", "E", "F", "I", "T"],
	"T": ["T", "E", "F", "I", "L"],

	# Uppercase diagonal
	"A": ["A", "V", "W", "Y", "M", "N", "X", "K"],
	"V": ["V", "W", "Y", "A", "X", "K", "M"],
	"W": ["W", "V", "Y", "A", "X", "M"],
	"Y": ["Y", "V", "W", "A", "X", "K"],
	"X": ["X", "V", "W", "Y", "A", "K", "Z"],
	"K": ["K", "X", "R", "A", "V", "Y", "N"],
	"M": ["M", "N", "A", "V", "W"],
	"N": ["N", "M", "A", "H", "K", "Z"],
	"Z": ["Z", "X", "K", "N"],

	# Uppercase special curves
	"S": ["S", "C", "G", "O"],
	"J": ["J", "U", "I"],
	"U": ["U", "J", "O"],

	# Figures
	"zero": ["zero", "six", "eight", "nine", "O", "o"],
	"one": ["one", "I", "l", "i"],
	"two": ["two", "three", "five", "seven", "Z"],
	"three": ["three", "two", "five", "eight"],
	"four": ["four", "seven", "A", "V", "Y"],
	"five": ["five", "two", "three", "six"],
	"six": ["six", "zero", "eight", "nine", "five"],
	"seven": ["seven", "four", "two", "Z"],
	"eight": ["eight", "zero", "six", "nine", "three"],
	"nine": ["nine", "zero", "six", "eight"],
}


WORD_BANK = [
	# Broad everyday / proofing words
	"about", "above", "across", "action", "active", "actual", "adjust", "after",
	"again", "almost", "always", "among", "amount", "animal", "answer", "appear",
	"around", "artist", "aspect", "author", "balance", "basic", "battle", "beauty",
	"before", "begin", "behind", "better", "between", "beyond", "border", "bottom",
	"branch", "bright", "broken", "build", "camera", "canvas", "careful", "center",
	"chance", "change", "choice", "circle", "clean", "client", "close", "colour",
	"column", "common", "complex", "corner", "create", "custom", "damage", "decide",
	"define", "degree", "design", "detail", "device", "direct", "double", "drawn",
	"early", "effect", "either", "energy", "enough", "escape", "evening", "example",
	"expert", "fabric", "factor", "family", "famous", "figure", "filter", "final",
	"finish", "flower", "follow", "forest", "format", "friend", "future", "garden",
	"gather", "gentle", "global", "golden", "ground", "handle", "happen", "height",
	"hidden", "history", "human", "image", "inside", "island", "letter", "level",
	"light", "linear", "little", "machine", "margin", "market", "master", "matter",
	"method", "middle", "modern", "moment", "motion", "natural", "normal", "notice",
	"number", "object", "office", "option", "orange", "origin", "outside", "panel",
	"paper", "parent", "pattern", "people", "period", "place", "planet", "point",
	"possible", "press", "print", "proper", "public", "quality", "quarter", "quick",
	"quiet", "random", "rather", "reader", "reason", "record", "reduce", "regular",
	"relate", "remove", "render", "result", "return", "rhythm", "sample", "screen",
	"script", "second", "select", "series", "shape", "signal", "simple", "smooth",
	"special", "square", "steady", "string", "stroke", "strong", "style", "system",
	"target", "textile", "thread", "through", "title", "toward", "travel", "unique",
	"update", "useful", "value", "vector", "version", "visible", "weight", "window",
	"wonder", "yellow",

	# Round / bowl useful
	"cocoa", "decade", "beacon", "caboodle", "opaque", "dagger", "bodega",
	"cabbage", "decode", "cocoon", "garage", "agenda", "pageant", "baggage",
	"goggles", "abode", "badge", "caged", "begged", "bogged", "cooped", "doodle",
	"queued", "accede", "beaded", "dogged", "goaded", "copied", "dogma",

	# Shoulder / arch useful
	"minimum", "murmur", "hammer", "runner", "manner", "humane", "hunger", "summer",
	"murmuring", "humming", "unhurried", "honour", "rumour", "narrow", "humour",

	# Stems / crossbars useful
	"rift", "tilt", "lilt", "fritter", "flitter", "lift", "trifle", "fitted",
	"fillet", "jitter", "teller", "filler",

	# Diagonal / angular useful
	"valley", "waxwork", "voyage", "keyway", "skywalk", "zigzag", "vex", "vixen",
	"woven", "waxy", "yolk", "zephyr", "waltz", "vivid", "kayak", "wizard",
	"awkward", "view", "wake", "wave", "yawn", "zonal", "kiosk",

	# S-curve / mixed useful
	"season", "assess", "success", "cascade", "sauce", "cease", "access", "glass",
	"grass", "sagas", "cases", "essence", "secure", "sponge", "cosmos",

	# Type-specific proofing words
	"align", "alternate", "baseline", "counter", "contrast", "curvature", "glyph",
	"kerning", "optical", "spacing", "terminal", "tracking", "width",
]


# ------------------------
# Helpers
# ------------------------

def beep(message=None):
	NSBeep()
	if message:
		print(message)


def split_suffix(glyph_name):
	"""
	Returns base name and suffix.

	Examples:
	a          -> ("a", "")
	a.ss01     -> ("a", ".ss01")
	a.ss01.alt -> ("a", ".ss01.alt")
	"""
	if "." not in glyph_name:
		return glyph_name, ""

	base_name = glyph_name.split(".")[0]
	suffix = glyph_name[len(base_name):]
	return base_name, suffix


def unique_preserve_order(items):
	seen = set()
	output = []

	for item in items:
		if item not in seen:
			seen.add(item)
			output.append(item)

	return output


def current_font():
	font = Glyphs.font

	if not font:
		beep("No font open.")
		return None

	return font


def selected_glyph_name():
	font = current_font()

	if not font:
		return None

	if not font.selectedLayers:
		beep("No glyph selected.")
		return None

	layer = font.selectedLayers[0]

	if not layer or not layer.parent:
		beep("No glyph selected.")
		return None

	return layer.parent.name


def glyph_token(glyph_name):
	return "/" + glyph_name


def glyph_line(glyph_names):
	return "".join(glyph_token(name) for name in glyph_names)


def glyph_exists(font, glyph_name):
	return glyph_name in font.glyphs


def relatives_for_glyph(font, selected_name):
	base_name, suffix = split_suffix(selected_name)

	if base_name not in RELATIVES:
		if glyph_exists(font, selected_name):
			return [selected_name]
		return []

	output = []

	if glyph_exists(font, selected_name):
		output.append(selected_name)

	for relative_base in RELATIVES[base_name]:
		suffixed_name = relative_base + suffix

		if suffix and glyph_exists(font, suffixed_name):
			output.append(suffixed_name)
		elif glyph_exists(font, relative_base):
			output.append(relative_base)

	return unique_preserve_order(output)


def relatives_line_for_glyph(font, selected_name):
	names = relatives_for_glyph(font, selected_name)

	if not names:
		return None, []

	return glyph_line(names), names


def selected_glyph_line(selected_name):
	return glyph_token(selected_name)


def selected_plus_relatives_text(font, selected_name):
	relatives_text, names = relatives_line_for_glyph(font, selected_name)

	if not relatives_text:
		return None, []

	return selected_glyph_line(selected_name) + "\n\n" + relatives_text, names


def all_relatives_groups_text(font):
	group_lines = []

	for base_name in RELATIVES.keys():
		if not glyph_exists(font, base_name):
			continue

		group_names = relatives_for_glyph(font, base_name)

		if len(group_names) < 2:
			continue

		group_lines.append(glyph_line(group_names))

	return "\n\n".join(group_lines)


def simple_letters_from_glyph_names(glyph_names):
	letters = []

	for glyph_name in glyph_names:
		base_name, suffix = split_suffix(glyph_name)

		if len(base_name) == 1 and base_name.isalpha():
			letters.append(base_name.lower())

	return sorted(set(letters))


def word_letters(word):
	return set([char for char in word.lower() if char.isalpha()])


def word_contains_outside_group(word, related_letters):
	letters = word_letters(word)
	return bool(letters.difference(set(related_letters)))


def word_score(word, related_letters, selected_letter, uncovered_letters=None):
	letters = word_letters(word)
	related_letters = set(related_letters)
	uncovered_letters = set(uncovered_letters or [])

	related_hits = letters.intersection(related_letters)
	uncovered_hits = letters.intersection(uncovered_letters)
	outside_hits = letters.difference(related_letters)

	score = 0

	# Prefer words that help cover letters not yet represented.
	score += len(uncovered_hits) * 35

	# Reward words containing some relatives, but not necessarily all.
	score += len(related_hits) * 8

	# Reward the selected glyph, but not too much.
	score += word.lower().count(selected_letter) * 5

	# Reward words that mix in other letters outside the group.
	score += min(len(outside_hits), 4) * 6

	# Prefer practical proofing word lengths.
	if 4 <= len(word) <= 9:
		score += 8

	if len(word) > 12:
		score -= 6

	# Avoid words that are too concentrated on only group letters.
	if not outside_hits:
		score -= 100

	return score


def sample_words_for_glyph(font, selected_name, count=15):
	base_name, suffix = split_suffix(selected_name)

	if base_name not in RELATIVES:
		beep("No relatives defined for: %s" % selected_name)
		return []

	if len(base_name) != 1 or not base_name.isalpha():
		beep("Sample words are only generated for letter glyphs.")
		return []

	relative_names = relatives_for_glyph(font, selected_name)
	related_letters = simple_letters_from_glyph_names(relative_names)

	if not related_letters:
		beep("No usable letter relatives found for: %s" % selected_name)
		return []

	selected_letter = base_name.lower()
	related_set = set(related_letters)

	# Only use words that contain at least one relative and at least one outside letter.
	candidates = []

	for word in unique_preserve_order([w.lower() for w in WORD_BANK]):
		letters = word_letters(word)

		if not letters:
			continue

		if not letters.intersection(related_set):
			continue

		if not word_contains_outside_group(word, related_set):
			continue

		candidates.append(word)

	if not candidates:
		beep("No sample words found for: %s" % selected_name)
		return []

	# First pass: greedily choose words that cover all related letters over the full string.
	selected_words = []
	covered_letters = set()
	remaining_candidates = list(candidates)

	while related_set.difference(covered_letters) and remaining_candidates and len(selected_words) < count:
		uncovered = related_set.difference(covered_letters)

		best_word = max(
			remaining_candidates,
			key=lambda word: word_score(word, related_letters, selected_letter, uncovered)
		)

		selected_words.append(best_word)
		covered_letters.update(word_letters(best_word).intersection(related_set))
		remaining_candidates.remove(best_word)

	# Second pass: fill up to 15 words with mixed words that still contain relatives.
	while len(selected_words) < count and remaining_candidates:
		best_word = max(
			remaining_candidates,
			key=lambda word: word_score(word, related_letters, selected_letter)
		)

		selected_words.append(best_word)
		remaining_candidates.remove(best_word)

	# If the word bank could not cover every letter, report it in the macro window.
	if selected_words:
		represented_letters = set().union(*[word_letters(word) for word in selected_words])
	else:
		represented_letters = set()

	missing_letters = related_set.difference(represented_letters)

	if missing_letters:
		print("Warning: Could not represent these relatives in the sample words: %s" % ", ".join(sorted(missing_letters)))

	if base_name.isupper():
		selected_words = [word.upper() for word in selected_words]
	else:
		selected_words = [word.lower() for word in selected_words]

	return selected_words


def write_to_current_tab_or_new_tab(font, text):
	if font.currentTab:
		font.currentTab.text = text
	else:
		font.newTab(text)


# ------------------------
# Actions
# ------------------------

def show_possible_relatives(sender=None):
	font = current_font()
	selected_name = selected_glyph_name()

	if not font or not selected_name:
		return

	tab_text, names = selected_plus_relatives_text(font, selected_name)

	if not tab_text:
		beep("No relatives found for: %s" % selected_name)
		return

	write_to_current_tab_or_new_tab(font, tab_text)

	print("Possible relatives for %s:" % selected_name)
	print(" ".join(names))


def generate_sample_string(sender=None):
	font = current_font()
	selected_name = selected_glyph_name()

	if not font or not selected_name:
		return

	base_text, names = selected_plus_relatives_text(font, selected_name)

	if not base_text:
		beep("No relatives found for: %s" % selected_name)
		return

	words = sample_words_for_glyph(font, selected_name, count=15)

	if not words:
		return

	sample_text = " ".join(words)
	tab_text = base_text + "\n\n" + sample_text

	write_to_current_tab_or_new_tab(font, tab_text)

	print("Sample string for %s:" % selected_name)
	print(sample_text)


def open_all_groups_of_relatives(sender=None):
	font = current_font()

	if not font:
		return

	tab_text = all_relatives_groups_text(font)

	if not tab_text:
		beep("No relative groups found in this font.")
		return

	font.newTab(tab_text)

	print("Opened all groups of relatives.")


# ------------------------
# UI
# ------------------------

class ShowPossibleRelativesPalette(object):

	def __init__(self):
		if FloatingWindow is None:
			beep("Vanilla is not available. Running relatives action instead.")
			show_possible_relatives()
			return

		margin = 6
		button_gap = margin / 2
		button_width = 195
		button_height = 24

		window_width = button_width + margin * 2
		window_height = button_height * 3 + margin * 2 + button_gap * 2

		self.w = FloatingWindow(
			(window_width, window_height),
			"Relatives",
			minSize=(window_width, window_height),
			maxSize=(window_width, window_height),
			autosaveName="com.yourname.ShowPossibleRelatives.palette.v7"
		)

		self.w.relativesButton = Button(
			(margin, margin, -margin, button_height),
			"Show Relatives for this glyph",
			callback=show_possible_relatives,
			sizeStyle="small"
		)

		self.w.sampleButton = Button(
			(margin, margin + button_height + button_gap, -margin, button_height),
			"Generate string from this group",
			callback=generate_sample_string,
			sizeStyle="small"
		)

		self.w.allGroupsButton = Button(
			(margin, margin + (button_height + button_gap) * 2, -margin, button_height),
			"Open all groups of relatives",
			callback=open_all_groups_of_relatives,
			sizeStyle="small"
		)

		self.w.open()


ShowPossibleRelativesPalette()