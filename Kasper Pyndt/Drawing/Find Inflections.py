# MenuTitle: Find Inflections
# -*- coding: utf-8 -*-
"""
Open a new Edit tab containing every glyph whose layer in the currently
selected master has at least one true cubic Bezier inflection.

Compatible with Glyphs 3 and Glyphs 4. The script checks outline paths in the
master layers themselves; components are not decomposed or modified.
"""

from math import copysign, isfinite, sqrt
import traceback

try:
	from GlyphsApp import CURVE, OFFCURVE, Glyphs, Message
except ImportError:  # Allows geometry tests outside Glyphs.
	CURVE = "curve"
	OFFCURVE = "offcurve"
	Glyphs = None
	Message = None


TITLE = "Open Glyphs with Inflections"
EPSILON = 1.0e-12
PARAMETER_EPSILON = 1.0e-9


def subtract(point_a, point_b):
	return point_a[0] - point_b[0], point_a[1] - point_b[1]


def cross(vector_a, vector_b):
	return vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0]


def point_tuple(point):
	return float(point.x), float(point.y)


def polynomial_value(coefficients, parameter):
	a, b, c = coefficients
	return (a * parameter + b) * parameter + c


def curvature_polynomial(points):
	"""Return coefficients for the cubic's signed-curvature numerator."""
	p0, p1, p2, p3 = points
	a = (
		-p0[0] + 3.0 * p1[0] - 3.0 * p2[0] + p3[0],
		-p0[1] + 3.0 * p1[1] - 3.0 * p2[1] + p3[1],
	)
	b = (
		3.0 * p0[0] - 6.0 * p1[0] + 3.0 * p2[0],
		3.0 * p0[1] - 6.0 * p1[1] + 3.0 * p2[1],
	)
	c = (-3.0 * p0[0] + 3.0 * p1[0], -3.0 * p0[1] + 3.0 * p1[1])
	return -6.0 * cross(a, b), 6.0 * cross(c, a), 2.0 * cross(c, b)


def real_roots(coefficients):
	"""Solve a quadratic robustly and return its finite real roots."""
	a, b, c = coefficients
	scale = max(abs(a), abs(b), abs(c))
	if scale <= EPSILON:
		return []
	a, b, c = a / scale, b / scale, c / scale

	if abs(a) <= EPSILON:
		if abs(b) <= EPSILON:
			return []
		return [-c / b]

	discriminant = b * b - 4.0 * a * c
	tolerance = EPSILON * (b * b + abs(4.0 * a * c) + 1.0)
	if discriminant < -tolerance:
		return []
	if discriminant < 0.0:
		discriminant = 0.0

	root_discriminant = sqrt(discriminant)
	q = -0.5 * (b + copysign(root_discriminant, b))
	if abs(q) <= EPSILON:
		return [-b / (2.0 * a)]
	return [q / a, c / q]


def sign(value, tolerance=EPSILON):
	if value > tolerance:
		return 1
	if value < -tolerance:
		return -1
	return 0


def has_inflection(points):
	"""Return True only when signed curvature reverses inside the segment."""
	coefficients = curvature_polynomial(points)
	scale = max(abs(value) for value in coefficients)
	if scale <= EPSILON:
		return False
	normalized = tuple(value / scale for value in coefficients)

	roots = sorted(
		root
		for root in real_roots(normalized)
		if isfinite(root)
		and PARAMETER_EPSILON < root < 1.0 - PARAMETER_EPSILON
	)
	unique_roots = []
	for root in roots:
		if not unique_roots or abs(root - unique_roots[-1]) > PARAMETER_EPSILON:
			unique_roots.append(root)
	if not unique_roots:
		return False

	boundaries = [0.0] + unique_roots + [1.0]
	interval_signs = []
	for start, end in zip(boundaries[:-1], boundaries[1:]):
		midpoint = (start + end) * 0.5
		interval_signs.append(sign(polynomial_value(normalized, midpoint)))

	for before, after in zip(interval_signs[:-1], interval_signs[1:]):
		if before and after and before != after:
			return True
	return False


def previous_node(nodes, index, distance, closed):
	previous_index = index - distance
	if previous_index >= 0:
		return nodes[previous_index]
	if closed and nodes:
		return nodes[previous_index % len(nodes)]
	return None


def cubic_segments(path):
	"""Yield cubic segments as (start, handle1, handle2, end)."""
	nodes = list(path.nodes)
	for end_index, end in enumerate(nodes):
		if end.type != CURVE:
			continue
		handle_2 = previous_node(nodes, end_index, 1, path.closed)
		handle_1 = previous_node(nodes, end_index, 2, path.closed)
		start = previous_node(nodes, end_index, 3, path.closed)
		if any(node is None for node in (start, handle_1, handle_2)):
			continue
		if (
			handle_1.type == OFFCURVE
			and handle_2.type == OFFCURVE
			and start.type != OFFCURVE
		):
			yield start, handle_1, handle_2, end


def layer_has_inflection(layer):
	for path in layer.paths:
		for segment in cubic_segments(path):
			points = tuple(point_tuple(node.position) for node in segment)
			if has_inflection(points):
				return True
	return False


def show_message(message):
	if Message is not None:
		Message(message, title=TITLE)


def show_notification(message):
	method = getattr(Glyphs, "showNotification", None)
	if callable(method):
		method(TITLE, message)


def open_glyphs_with_inflections():
	if Glyphs is None or Glyphs.font is None:
		show_message("Open a font in Glyphs first.")
		return

	font = Glyphs.font
	master = font.selectedFontMaster
	if master is None:
		show_message("Select a font master first.")
		return

	matching_names = []
	for glyph in font.glyphs:
		if not glyph.name:
			continue
		try:
			layer = glyph.layers[master.id]
		except (KeyError, IndexError, TypeError):
			continue
		if layer is not None and layer_has_inflection(layer):
			matching_names.append(glyph.name)

	if not matching_names:
		show_message(
			'No glyphs with inflections were found in master "%s".' % master.name
		)
		return

	# Slash notation preserves non-Unicode and alternate glyph names.
	tab_text = "".join("/%s" % name for name in matching_names)
	tab = font.newTab(tab_text)
	try:
		tab.masterIndex = font.masterIndex
	except (AttributeError, TypeError):
		pass

	show_notification(
		'Opened %i glyph%s from master "%s".'
		% (
			len(matching_names),
			"" if len(matching_names) == 1 else "s",
			master.name,
		)
	)


if __name__ == "__main__":
	try:
		open_glyphs_with_inflections()
	except Exception:
		if Glyphs is not None:
			Glyphs.showMacroWindow()
		print(traceback.format_exc())
		show_message("The font could not be scanned. Details are in the Macro window.")
