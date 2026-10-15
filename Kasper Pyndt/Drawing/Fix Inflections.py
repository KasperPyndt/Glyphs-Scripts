# MenuTitle: Fix Inflections
# -*- coding: utf-8 -*-
"""
Remove unwanted inflections from cubic Bezier segments with minimal edits.

The script keeps every on-curve point fixed and keeps both endpoint tangent
directions fixed. It tests shortening either control handle, then applies the
smallest handle movement that removes the inflection.

Usage in Glyphs 3 or Glyphs 4:

1. Open text in Edit view.
2. Highlight the characters you want to repair. Every cubic segment in those
   character layers is checked. Repeated occurrences of one character layer
   are processed only once.
3. Choose Script > Fix Inflections.

Hold Option while choosing the script to repair the highlighted characters in
all font masters instead of only the currently displayed master.

Segments that cannot be repaired by shortening a single handle are left alone.
"""

from math import copysign, isfinite, sqrt
import traceback

try:
	from AppKit import NSEvent
	try:
		from AppKit import NSEventModifierFlagOption
	except ImportError:
		NSEventModifierFlagOption = 1 << 19
	from Foundation import NSPoint
	from GlyphsApp import CURVE, OFFCURVE, Glyphs, Message
except ImportError:  # Lets the geometry functions be tested outside Glyphs.
	NSEvent = None
	NSEventModifierFlagOption = 1 << 19
	NSPoint = None
	CURVE = "curve"
	OFFCURVE = "offcurve"
	Glyphs = None
	Message = None


TITLE = "Fix Inflections"
EPSILON = 1.0e-12
PARAMETER_EPSILON = 1.0e-9
SEARCH_STEPS = 256
SEARCH_ITERATIONS = 60
MINIMUM_HANDLE_SCALE = 1.0e-6
SAFETY_DISTANCE = 0.05  # Font units beyond the exact no-inflection boundary.


def subtract(point_a, point_b):
	return point_a[0] - point_b[0], point_a[1] - point_b[1]


def add(point_a, point_b):
	return point_a[0] + point_b[0], point_a[1] + point_b[1]


def multiply(vector, scalar):
	return vector[0] * scalar, vector[1] * scalar


def length(vector):
	return (vector[0] * vector[0] + vector[1] * vector[1]) ** 0.5


def cross(vector_a, vector_b):
	return vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0]


def point_tuple(point):
	return float(point.x), float(point.y)


def polynomial_value(coefficients, parameter):
	a, b, c = coefficients
	return (a * parameter + b) * parameter + c


def curvature_polynomial(points):
	"""Return coefficients for cross(B'(t), B''(t))."""
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
	discriminant_tolerance = EPSILON * (b * b + abs(4.0 * a * c) + 1.0)
	if discriminant < -discriminant_tolerance:
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
	"""Return True when signed curvature changes inside the cubic segment."""
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


def scale_handle(points, handle_index, scale):
	"""Shorten one handle while preserving its endpoint tangent direction."""
	result = list(points)
	anchor_index = 0 if handle_index == 1 else 3
	anchor = points[anchor_index]
	handle_vector = subtract(points[handle_index], anchor)
	result[handle_index] = add(anchor, multiply(handle_vector, scale))
	return tuple(result)


def nearest_safe_scale(points, handle_index):
	"""Find the largest shortening scale that removes all inflections."""
	if not has_inflection(points):
		return 1.0

	unsafe_scale = 1.0
	safe_scale = None
	span = 1.0 - MINIMUM_HANDLE_SCALE
	for step in range(1, SEARCH_STEPS + 1):
		scale = 1.0 - span * float(step) / float(SEARCH_STEPS)
		candidate = scale_handle(points, handle_index, scale)
		if has_inflection(candidate):
			unsafe_scale = scale
			continue
		safe_scale = scale
		break

	if safe_scale is None:
		return None

	# Refine the first safe/unsafe boundary. Safe is below the boundary and
	# unsafe is above it because this search only shortens handles.
	for _ in range(SEARCH_ITERATIONS):
		midpoint = (safe_scale + unsafe_scale) * 0.5
		if has_inflection(scale_handle(points, handle_index, midpoint)):
			unsafe_scale = midpoint
		else:
			safe_scale = midpoint

	anchor_index = 0 if handle_index == 1 else 3
	handle_length = length(subtract(points[handle_index], points[anchor_index]))
	if handle_length > EPSILON:
		safe_scale = max(
			MINIMUM_HANDLE_SCALE,
			safe_scale - SAFETY_DISTANCE / handle_length,
		)

	# Guard against numerical noise immediately at the boundary.
	while (
		safe_scale > MINIMUM_HANDLE_SCALE
		and has_inflection(scale_handle(points, handle_index, safe_scale))
	):
		safe_scale *= 0.999

	if has_inflection(scale_handle(points, handle_index, safe_scale)):
		return None
	return safe_scale


def minimal_handle_fix(points):
	"""Return (handle_index, new_position, movement), or None."""
	if not has_inflection(points):
		return None

	candidates = []
	for handle_index, anchor_index in ((1, 0), (2, 3)):
		scale = nearest_safe_scale(points, handle_index)
		if scale is None or scale >= 1.0:
			continue
		new_points = scale_handle(points, handle_index, scale)
		movement = length(subtract(points[handle_index], new_points[handle_index]))
		candidates.append((movement, handle_index, new_points[handle_index]))

	if not candidates:
		return None
	movement, handle_index, new_position = min(candidates, key=lambda item: item[0])
	return handle_index, new_position, movement


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


def show_message(message):
	if Message is not None:
		Message(message, title=TITLE)


def call_if_available(instance, method_name):
	"""Call an optional Glyphs 3/4 UI method and report whether it ran."""
	method = getattr(instance, method_name, None)
	if callable(method):
		method()
		return True
	return False


def unique_layers(layers):
	"""Deduplicate repeated characters in an Edit-view text selection."""
	result = []
	seen = set()
	for layer in layers:
		identity = id(layer)
		if identity in seen:
			continue
		seen.add(identity)
		result.append(layer)
	return result


def option_key_is_down():
	"""Read the Option-key state when the script is launched."""
	if NSEvent is None:
		return False
	try:
		return bool(NSEvent.modifierFlags() & NSEventModifierFlagOption)
	except (AttributeError, TypeError):
		return False


def selected_glyphs(layers):
	"""Return each glyph represented by the selection exactly once."""
	result = []
	seen = set()
	for layer in layers:
		glyph = getattr(layer, "parent", None)
		if glyph is None:
			continue
		identity = id(glyph)
		if identity in seen:
			continue
		seen.add(identity)
		result.append(glyph)
	return result


def all_master_layers(font, selection_layers):
	"""Expand selected glyphs to their master layers in master order."""
	result = []
	for glyph in selected_glyphs(selection_layers):
		for master in font.masters:
			try:
				layer = glyph.layers[master.id]
			except (KeyError, IndexError, TypeError):
				continue
			if layer is not None:
				result.append(layer)
	return unique_layers(result)


def fix_inflections():
	if Glyphs is None or Glyphs.font is None:
		show_message("Open a font in Glyphs first.")
		return
	font = Glyphs.font
	# In both Glyphs 3 and 4, selectedLayers represents the highlighted
	# characters in Edit view (and the selected glyphs in Font view).
	selection_layers = unique_layers(list(font.selectedLayers or []))
	if not selection_layers:
		show_message("Highlight one or more characters in Edit view first.")
		return
	all_masters = option_key_is_down()
	layers = (
		all_master_layers(font, selection_layers)
		if all_masters
		else selection_layers
	)

	segments_to_fix = []
	for layer in layers:
		for path in layer.paths:
			for segment in cubic_segments(path):
				points = tuple(point_tuple(node.position) for node in segment)
				if has_inflection(points):
					segments_to_fix.append((layer, segment, points))

	if not segments_to_fix:
		scope = "across all masters" if all_masters else "in the selected master"
		show_message("No inflections were found %s." % scope)
		return

	by_glyph = {}
	for layer, segment, points in segments_to_fix:
		by_glyph.setdefault(layer.parent, []).append((layer, segment, points))

	fixed_count = 0
	unresolved_count = 0
	total_movement = 0.0
	updates_disabled = call_if_available(font, "disableUpdateInterface")
	try:
		for glyph, items in by_glyph.items():
			undo_started = call_if_available(glyph, "beginUndo")
			try:
				for _layer, segment, points in items:
					fix = minimal_handle_fix(points)
					if fix is None:
						unresolved_count += 1
						continue
					handle_index, new_position, movement = fix
					handle = segment[handle_index]
					handle.position = NSPoint(new_position[0], new_position[1])
					fixed_count += 1
					total_movement += movement
			finally:
				if undo_started:
					call_if_available(glyph, "endUndo")
	finally:
		if updates_disabled:
			call_if_available(font, "enableUpdateInterface")

	Glyphs.redraw()
	result = "Fixed %i inflection%s." % (
		fixed_count,
		"" if fixed_count == 1 else "s",
	)
	if fixed_count:
		result += " Total handle movement: %.2f units." % total_movement
	if all_masters:
		result += " Applied across all masters."
	if unresolved_count:
		result += " %i segment%s could not be fixed by shortening one handle." % (
			unresolved_count,
			"" if unresolved_count == 1 else "s",
		)
	show_message(result)


if __name__ == "__main__":
	try:
		fix_inflections()
	except Exception:
		if Glyphs is not None:
			Glyphs.showMacroWindow()
		print(traceback.format_exc())
		show_message("The inflections could not be fixed. Details are in the Macro window.")
