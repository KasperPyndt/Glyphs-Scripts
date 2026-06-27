# MenuTitle: Check Vertical Disalignments
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs, OFFCURVE, Message

THRESHOLD = 3.0
INCLUDE_EXACTLY_ON_LINE = False  # Set to True if you also want nodes exactly on the lines included.

font = Glyphs.font

if not font:
	Message("No Font Open", "Please open a font first.")
	raise SystemExit

master = font.selectedFontMaster

if not master:
	Message("No Master Selected", "Please select a master first.")
	raise SystemExit


def close_enough(a, b, tolerance=0.001):
	return abs(float(a) - float(b)) <= tolerance


def distance_is_problem(distance):
	if INCLUDE_EXACTLY_ON_LINE:
		return distance <= THRESHOLD
	else:
		return 0 < distance <= THRESHOLD


def metric_values_for_master(master):
	"""
	Returns the key vertical metrics we care about.
	These are the 'baseline' positions of the alignment zones.
	"""
	return {
		"ascender": master.ascender,
		"cap height": master.capHeight,
		"x-height": master.xHeight,
		"baseline": 0,
		"descender": master.descender,
	}


def collect_vertical_check_lines(master):
	"""
	Collects:
	- ascender, cap height, x-height, baseline, descender
	- the overshoot edge of any alignment zone attached to those metrics

	For example:
		x-height zone at 500 with size 12 gives check lines 500 and 512
		baseline zone at 0 with size -12 gives check lines 0 and -12
	"""
	metrics = metric_values_for_master(master)

	check_lines = {}

	# Add the metric baselines themselves
	for metric_name, y_value in metrics.items():
		check_lines[float(y_value)] = metric_name

	# Add overshoot / zone extremum lines
	for zone in master.alignmentZones:
		z1 = float(zone.position)
		z2 = float(zone.position + zone.size)

		matching_metric_name = None

		for metric_name, metric_y in metrics.items():
			if close_enough(z1, metric_y) or close_enough(z2, metric_y):
				matching_metric_name = metric_name
				break

		if matching_metric_name:
			check_lines[z1] = "%s zone edge" % matching_metric_name
			check_lines[z2] = "%s overshoot edge" % matching_metric_name

	return check_lines


def decomposed_layer(layer):
	"""
	Uses a decomposed copy so glyphs built from components are checked by their actual resulting outlines.
	"""
	try:
		return layer.copyDecomposedLayer()
	except Exception:
		return layer


check_lines = collect_vertical_check_lines(master)

problem_glyph_names = []
report = []

Glyphs.clearLog()
print("Checking active master: %s" % master.name)
print("Threshold: within %s units" % THRESHOLD)
print("Exact hits included:", INCLUDE_EXACTLY_ON_LINE)
print("")
print("Check lines:")
for y_value in sorted(check_lines.keys(), reverse=True):
	print("  %s: %s" % (y_value, check_lines[y_value]))
print("")


for glyph in font.glyphs:
	layer = glyph.layers[master.id]

	if not layer:
		continue

	test_layer = decomposed_layer(layer)
	glyph_has_problem = False
	glyph_hits = []

	for path in test_layer.paths:
		for node in path.nodes:
			if node.type == OFFCURVE:
				continue

			node_y = float(node.y)

			for line_y, line_name in check_lines.items():
				distance = abs(node_y - line_y)

				if distance_is_problem(distance):
					glyph_has_problem = True
					glyph_hits.append(
						"node y=%s is %.2f units from %s at y=%s"
						% (
							round(node_y, 3),
							distance,
							line_name,
							round(line_y, 3),
						)
					)

	if glyph_has_problem:
		problem_glyph_names.append(glyph.name)
		report.append((glyph.name, glyph_hits))


if problem_glyph_names:
	tab_text = "/" + "/".join(problem_glyph_names)
	font.newTab(tab_text)
else:
	Message(
		"No Near-Miss Nodes Found",
		"No glyphs have on-curve nodes within %s units of the selected master’s vertical metrics or alignment zone edges."
		% THRESHOLD,
	)


print("Problem glyphs found:", len(problem_glyph_names))
print("")

for glyph_name, hits in report:
	print("/%s" % glyph_name)
	for hit in hits:
		print("  - %s" % hit)
	print("")

print("Done.")