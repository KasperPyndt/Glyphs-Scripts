# MenuTitle: Build Rough Draft
# -*- coding: utf-8 -*-
"""Build rough Latin drafts from a small, progressively unlocked source set."""

import hashlib
import math
from math import ceil, exp, floor
import traceback

import objc

from AppKit import (
	NSButtonTypePushOnPushOff,
	NSAlert,
	NSAlertFirstButtonReturn,
	NSAlertSecondButtonReturn,
	NSAlertStyleWarning,
	NSColor,
	NSFont,
	NSFontAttributeName,
	NSForegroundColorAttributeName,
	NSMaxYEdge,
	NSMoveToBezierPathElement,
	NSLineToBezierPathElement,
	NSCurveToBezierPathElement,
	NSClosePathBezierPathElement,
	NSNoBorder,
	NSPopover,
	NSPopoverBehaviorApplicationDefined,
	NSTextField,
	NSTrackingArea,
	NSTrackingActiveInActiveApp,
	NSTrackingInVisibleRect,
	NSTrackingMouseEnteredAndExited,
	NSView,
	NSViewController,
	NSWindowCollectionBehaviorCanJoinAllSpaces,
	NSWindowCollectionBehaviorFullScreenAuxiliary,
	NSWindowSharingReadOnly,
)
from Foundation import (
	NSAttributedString, NSMutableAttributedString, NSObject,
	NSRunLoop, NSRunLoopCommonModes, NSTimer,
)

try:
	import vanilla
except ImportError:
	vanilla = None

from GlyphsApp import (
	Glyphs,
	GSGlyph,
	GSLayer,
	GSNode,
	GSPath,
	GSComponent,
	GSMetricsTypeBaseline,
	GSMetricsTypeDescender,
	GSMetricsTypexHeight,
	CURVE,
	QCURVE,
	LINE,
	OFFCURVE,
	Message,
	intersectPaths,
)


TITLE = "Build Rough Draft"
PREF_DOMAIN = "com.approximatetype.buildRoughDraft"
USER_DATA_KEY = PREF_DOMAIN + ".provenance"
VERSION = "0.14.93"

ALPHABET = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")

CHARACTERS = (
	"A", "B", "C", "D", "E", "F", "G", "I", "J", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
	"a", "b", "c", "d", "e", "f", "g", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
)
BASE_GLYPHS = ("H", "O", "h")
ALL_CHARACTERS_LABEL = "All possible characters"
GENERATION_OPTIONS = (ALL_CHARACTERS_LABEL,) + CHARACTERS

R_SHOULDER_CUT = 0.35
R_OPEN_CORNER_OFFSET = 100.0
C_OPEN_CORNER_OFFSET = 100.0
U_OUTER_JOIN_DROP_RATIO = 0.03
U_SANS_CONTRAST_THRESHOLD = 0.85
U_BOTTOM_WEIGHT_GAIN = 0.10
U_BOTTOM_SHIFT_GAIN = 0.05
U_TRANSITION_WEIGHT_POSITION = 0.50
J_WIDTH_FACTOR = 0.94
P_BOWL_SCALE = 0.60
PB_BOWL_SHOULDER_PULL = 0.25
P_HORIZONTAL_EXTENSION = 1.20
P_WIDTH_FACTOR = 0.96
B_WIDTH_FACTOR = 0.94
B_UPPER_WIDTH_FACTOR = 0.97
S_WIDTH_FACTOR = 0.94
S_UPPER_WIDTH_FACTOR = 0.94
S_BOWL_HEIGHT_FACTOR = 0.50
S_UPPER_BOWL_HEIGHT_FACTOR = 0.473
S_TERMINAL_EXTENSION = 0.08
S_SPINE_HANDLE_REACH = 0.0825
S_OUTER_SHOULDER_HANDLE_FACTOR = 0.87
S_SIDE_WEIGHT_FACTOR = 0.84
Q_TAIL_COUNTER_DROP_FACTOR = 0.10
X_WIDTH_FACTOR = 1.05
V_WIDTH_FACTOR = 1.05
Y_STEM_HEIGHT_FACTOR = 0.36
Y_CONTRAST_JUNCTION_RISE = 0.14
M_WIDTH_FACTOR = 1.00
M_OUTLINE_WIDTH_GAIN = 1.08
M_DIAGONAL_INSET_FACTOR = 0.08
W_OUTLINE_WIDTH_GAIN = 0.86
K_INK_WIDTH_FACTOR = 1.032
K_ARM_MIDDLE_CLEARANCE_FACTOR = 0.095
K_LEG_JOINT_RISE_FACTOR = 1.0 / 6.0
LOWERCASE_O_WIDTH_FACTOR = 1.08
LOWERCASE_O_STROKE_FACTOR = 0.98
LOWERCASE_C_WIDTH_FACTOR = 1.08
LOWERCASE_C_STROKE_FACTOR = 0.98
LOWERCASE_C_TERMINAL_VERTICAL_FACTOR = 1.10
LOWERCASE_V_WIDTH_FACTOR = 1.08
LOWERCASE_V_STROKE_FACTOR = 0.98
LOWERCASE_X_WIDTH_FACTOR = 1.08
LOWERCASE_X_STROKE_FACTOR = 0.98
LOWERCASE_S_WIDTH_FACTOR = 1.08
LOWERCASE_S_STROKE_FACTOR = 0.98
LOWERCASE_K_WIDTH_FACTOR = 1.08
LOWERCASE_K_STROKE_FACTOR = 0.98
LOWERCASE_Z_WIDTH_FACTOR = 1.08
LOWERCASE_Z_STROKE_FACTOR = 0.98
LOWERCASE_J_HOOK_WIDTH = 0.55
LOWERCASE_J_HOOK_LENGTH_GAIN = 1.20
LOWERCASE_J_TERMINAL_WEIGHT_FACTOR = 0.98
LOWERCASE_FT_CROSSBAR_WEIGHT_FACTOR = 0.98
LOWERCASE_FT_CROSSBAR_HEIGHT_FACTOR = 0.90
LOWERCASE_FT_CROSSBAR_LEFT_OVERHANG = 0.90
LOWERCASE_T_HEIGHT_FACTOR = 1.16
LOWERCASE_DOT_MIN_SIZE = 0.07
LOWERCASE_DOT_GAP = 0.12
ROUND_DOT_SIZE_FACTOR = 1.128
DOT_SHAPE_KEY = PREF_DOMAIN + ".dotShape"
DOT_SHAPES = ("round", "square")
V_PROFILE_POSITIONS = (0.22, 0.40, 0.58, 0.76)

EPSILON = 0.01
W_STROKE_TOLERANCE = 0.5
LOCKED_BUTTON_ALPHA = 0.58
LETTER_TOOLTIP_DELAY = 0.15
ACTION_BUTTON_CONTENT_PADDING = 12.0
ACTION_BUTTON_GAP = 20.0
SELECTED_BUTTON_COLOR = NSColor.blackColor()
SELECTED_TITLE_COLOR = NSColor.whiteColor()
SOURCE_TITLE_COLOR = NSColor.systemBlueColor()
BUILT_TITLE_COLOR = NSColor.systemGreenColor()
UNBUILT_TITLE_COLOR = NSColor.systemRedColor()

_SOURCE_LAYER_OVERRIDES = {}


class GenerationError(Exception):
	"""A construction problem that can be shown without a traceback."""


def _bounds_values(obj):
	bounds = obj.bounds
	x_min = float(bounds.origin.x)
	y_min = float(bounds.origin.y)
	return (
		x_min,
		y_min,
		x_min + float(bounds.size.width),
		y_min + float(bounds.size.height),
	)


def _bounds_area(path):
	width = float(path.bounds.size.width)
	height = float(path.bounds.size.height)
	return abs(width * height)


def _oncurve_nodes(path):
	return [node for node in path.nodes if node.type != OFFCURVE]


def _adjacent_nodes(path, node):
	nodes = list(path.nodes)
	index = nodes.index(node)
	return nodes[(index - 1) % len(nodes)], nodes[(index + 1) % len(nodes)]


def _point(node):
	return float(node.x), float(node.y)


def _new_node(point, node_type=LINE, smooth=False):
	node = GSNode((float(point[0]), float(point[1])), node_type)
	node.smooth = bool(smooth)
	return node


def _rectangle_path(x_min, y_min, x_max, y_max):
	if x_max <= x_min or y_max <= y_min:
		raise GenerationError("Cannot build a zero-size construction rectangle.")
	path = GSPath()
	path.closed = True
	for point in (
		(x_min, y_min),
		(x_min, y_max),
		(x_max, y_max),
		(x_max, y_min),
	):
		path.nodes.append(_new_node(point, LINE))
	return path


def _layer_from_paths(paths, width):
	layer = GSLayer()
	for path in paths:
		layer.shapes.append(path.copy())
	layer.width = round(float(width))
	return layer


def _scan_x_intersections(layer, y):
	x_min, _y_min, x_max, _y_max = _bounds_values(layer)
	padding = max(1000.0, x_max - x_min)
	points = layer.intersectionsBetweenPoints(
		(x_min - padding, float(y)),
		(x_max + padding, float(y)),
	)
	values = sorted(float(point.x) for point in points[1:-1])
	result = []
	for value in values:
		if not result or abs(value - result[-1]) > 0.5:
			result.append(value)
	return result


def _scan_y_intersections(layer, x):
	_x_min, y_min, _x_max, y_max = _bounds_values(layer)
	padding = max(1000.0, y_max - y_min)
	points = layer.intersectionsBetweenPoints(
		(float(x), y_min - padding),
		(float(x), y_max + padding),
	)
	values = sorted(float(point.y) for point in points[1:-1])
	result = []
	for value in values:
		if not result or abs(value - result[-1]) > 0.5:
			result.append(value)
	return result


def _measure_stems(layer, scan_y):
	intersections = _scan_x_intersections(layer, scan_y)
	if len(intersections) < 4:
		raise GenerationError(
			"Expected two vertical stems at y=%g, but found %i intersections."
			% (scan_y, len(intersections))
		)
	return (
		(intersections[0], intersections[1]),
		(intersections[-2], intersections[-1]),
	)


def _measure_h_source(layer, master):
	copy = _copy_decomposed(layer)
	left_stem, right_stem = _measure_stems(copy, float(master.xHeight) * 0.20)
	return copy, left_stem, right_stem


def _measure_H_source(layer, master):
	copy = _copy_decomposed(layer)
	left_stem, right_stem = _measure_stems(copy, float(master.capHeight) * 0.15)
	center_x = (left_stem[1] + right_stem[0]) * 0.5
	crossbar = _scan_y_intersections(copy, center_x)
	if len(crossbar) < 2:
		raise GenerationError("Could not measure the crossbar of H.")
	return copy, left_stem, right_stem, (crossbar[0], crossbar[-1])


def _lower_ascender_stem(
	layer, stem_interval, x_height, shoulder_top=None, stem_slope=0.0,
	allow_extend=False,
):
	"""Shorten h's ascender by translating its complete top feature."""
	stem_left, stem_right = stem_interval
	paths = [path for path in layer.paths if path.closed]
	if not paths:
		raise GenerationError("The h source has no closed ascender contour.")
	path = max(paths, key=_bounds_area)
	oncurves = _oncurve_nodes(path)
	top_y = max(float(node.y) for node in oncurves)
	if abs(top_y - float(x_height)) <= EPSILON or (
		not allow_extend and top_y <= float(x_height) + EPSILON
	):
		return
	stem_width = max(EPSILON, stem_right - stem_left)
	tolerance = max(2.0, stem_width * 0.25)
	if shoulder_top is None:
		# n/u only need h's ascender shortened; they do not need to parse the
		# shoulder itself. Measure the junction locally on the inside edge of
		# the left stem so curved, faceted, and all-line shoulders all work.
		junction_candidates = [
			node
			for node in oncurves
			if abs(float(node.x) - stem_right) <= tolerance
			and float(node.y) <= float(x_height) + EPSILON
			and float(node.y) > min(float(item.y) for item in oncurves) + EPSILON
		]
		if junction_candidates:
			shoulder_top = max(
				float(node.y) for node in junction_candidates
			)
		else:
			# A conservative threshold still limits the operation to the
			# ascender when an unusually slanted stem has no local landmark.
			shoulder_top = float(x_height)
	shoulder_top = float(shoulder_top)
	delta_y = float(x_height) - top_y
	outer_candidates = [
		node
		for node in oncurves
		if abs(float(node.x) - stem_left) <= tolerance
		and float(node.y) > shoulder_top + EPSILON
	]
	inner_candidates = [
		node
		for node in oncurves
		if abs(float(node.x) - stem_right) <= tolerance
		and float(node.y) > shoulder_top + EPSILON
	]
	feature = None
	if outer_candidates and inner_candidates:
		outer_join = min(outer_candidates, key=lambda node: float(node.y))
		inner_join = min(inner_candidates, key=lambda node: float(node.y))
		forward = [outer_join] + _forward_between(path, outer_join, inner_join)
		reverse = [inner_join] + _forward_between(path, inner_join, outer_join)
		top_nodes = [
			node for node in oncurves
			if abs(float(node.y) - top_y) <= EPSILON
		]
		candidates = [
			arc for arc in (forward, reverse)
			if all(node in arc for node in top_nodes)
		]
		if candidates:
			feature = min(candidates, key=len)
	if feature is None:
		# Conservative fallback for unusual outlines: include everything safely
		# above the measured shoulder, including serif handles and overhangs.
		feature = [
			node for node in path.nodes
			if float(node.y) > shoulder_top + EPSILON
		]
	for node in feature:
		node.x = float(node.x) + delta_y * float(stem_slope)
		node.y = float(node.y) + delta_y


def _lerp(point_a, point_b, factor):
	return (
		point_a[0] + (point_b[0] - point_a[0]) * factor,
		point_a[1] + (point_b[1] - point_a[1]) * factor,
	)


def _split_cubic(points, factor):
	p0, p1, p2, p3 = points
	q0 = _lerp(p0, p1, factor)
	q1 = _lerp(p1, p2, factor)
	q2 = _lerp(p2, p3, factor)
	r0 = _lerp(q0, q1, factor)
	r1 = _lerp(q1, q2, factor)
	s = _lerp(r0, r1, factor)
	return (p0, q0, r0, s), (s, r1, q2, p3)


def _split_cubic_at_y(points, target_y):
	"""Split a vertically monotonic cubic without changing its geometry."""
	start_y = float(points[0][1])
	end_y = float(points[3][1])
	target_y = float(target_y)
	if not min(start_y, end_y) < target_y < max(start_y, end_y):
		raise GenerationError("The C opening falls outside O's right-side curves.")
	increasing = end_y > start_y
	low, high = 0.0, 1.0
	for _step in range(60):
		factor = (low + high) * 0.5
		one_minus = 1.0 - factor
		y = (
			one_minus ** 3 * points[0][1]
			+ 3.0 * one_minus ** 2 * factor * points[1][1]
			+ 3.0 * one_minus * factor ** 2 * points[2][1]
			+ factor ** 3 * points[3][1]
		)
		if (y < target_y) == increasing:
			low = factor
		else:
			high = factor
	return _split_cubic(points, (low + high) * 0.5)


def _cubic_point(points, factor):
	one_minus = 1.0 - factor
	return (
		one_minus ** 3 * points[0][0]
		+ 3.0 * one_minus ** 2 * factor * points[1][0]
		+ 3.0 * one_minus * factor ** 2 * points[2][0]
		+ factor ** 3 * points[3][0],
		one_minus ** 3 * points[0][1]
		+ 3.0 * one_minus ** 2 * factor * points[1][1]
		+ 3.0 * one_minus * factor ** 2 * points[2][1]
		+ factor ** 3 * points[3][1],
	)


def _cubic_tangent(points, factor):
	"""Return the derivative vector of a cubic at ``factor``."""
	one_minus = 1.0 - factor
	return (
		3.0 * one_minus ** 2 * (points[1][0] - points[0][0])
		+ 6.0 * one_minus * factor * (points[2][0] - points[1][0])
		+ 3.0 * factor ** 2 * (points[3][0] - points[2][0]),
		3.0 * one_minus ** 2 * (points[1][1] - points[0][1])
		+ 6.0 * one_minus * factor * (points[2][1] - points[1][1])
		+ 3.0 * factor ** 2 * (points[3][1] - points[2][1]),
	)


def _split_cubic_at_ray(points, center, direction):
	"""Split a cubic where it crosses a line through ``center``."""
	def signed_distance(factor):
		point = _cubic_point(points, factor)
		return _cross(
			direction,
			(point[0] - center[0], point[1] - center[1]),
		)

	low, high = 0.0, 1.0
	low_value = signed_distance(low)
	high_value = signed_distance(high)
	if abs(low_value) <= EPSILON:
		return _split_cubic(points, low)
	if abs(high_value) <= EPSILON:
		return _split_cubic(points, high)
	if low_value * high_value > 0.0:
		raise GenerationError("The angled C cut does not cross the inner contour.")
	for _step in range(60):
		factor = (low + high) * 0.5
		value = signed_distance(factor)
		if abs(value) <= EPSILON:
			low = high = factor
			break
		if low_value * value <= 0.0:
			high = factor
		else:
			low = factor
			low_value = value
	return _split_cubic(points, (low + high) * 0.5)


def _shared_parallel_cut_center(
	inner_points, outer_points, desired_center, direction
):
	"""Shift a parallel cut until it crosses both stroke boundaries.

	A C-defined terminal can be much more horizontal or vertical than the local
	normal of another glyph.  Keeping its direction is the design invariant; the
	cut may therefore need to slide slightly along its normal to cross both sides
	of the target stroke cleanly.
	"""
	dx = float(direction[0])
	dy = float(direction[1])
	length = (dx * dx + dy * dy) ** 0.5
	if length <= EPSILON:
		raise GenerationError("C contains an undefined terminal direction.")
	direction = (dx / length, dy / length)
	normal = (-direction[1], direction[0])

	def scalar_range(points):
		values = []
		for step in range(129):
			point = _cubic_point(points, step / 128.0)
			values.append(point[0] * normal[0] + point[1] * normal[1])
		return min(values), max(values)

	inner_range = scalar_range(inner_points)
	outer_range = scalar_range(outer_points)
	low = max(inner_range[0], outer_range[0])
	high = min(inner_range[1], outer_range[1])
	if high - low <= EPSILON:
		raise GenerationError(
			"C's terminal direction cannot cross both sides of the target stroke."
		)
	desired_scalar = (
		float(desired_center[0]) * normal[0]
		+ float(desired_center[1]) * normal[1]
	)
	margin = min((high - low) * 0.10, max(EPSILON, 1.0))
	safe_low = low + margin
	safe_high = high - margin
	if safe_low > safe_high:
		target_scalar = (low + high) * 0.5
	elif safe_low <= desired_scalar <= safe_high:
		target_scalar = desired_scalar
	else:
		target_scalar = (safe_low + safe_high) * 0.5
	shift = target_scalar - desired_scalar
	return (
		float(desired_center[0]) + normal[0] * shift,
		float(desired_center[1]) + normal[1] * shift,
	)


def _forward_between(path, start, end):
	nodes = list(path.nodes)
	start_index = nodes.index(start)
	result = []
	for offset in range(1, len(nodes) + 1):
		node = nodes[(start_index + offset) % len(nodes)]
		result.append(node)
		if node is end:
			return result
	return []


def _arc_cubic_segments(arc):
	"""Return cubic segments, with their arc indices, from a raw node arc."""
	segments = []
	start = arc[0]
	start_index = 0
	offcurves = []
	for index, node in enumerate(arc[1:], 1):
		if node.type == OFFCURVE:
			offcurves.append(node)
			continue
		if node.type == CURVE and len(offcurves) == 2:
			segments.append(
				(
					start,
					node,
					(
						_point(start),
						_point(offcurves[0]),
						_point(offcurves[1]),
						_point(node),
					),
					start_index,
					index,
				)
			)
		start = node
		start_index = index
		offcurves = []
	return segments


def _arc_drawable_segments(arc):
	"""Return cubic and straight segments from a raw contour arc.

	Straight segments are represented as collinear cubics for geometric
	calculations, while the final boolean flag records that they must remain
	straight in the generated outline.
	"""
	segments = []
	start = arc[0]
	start_index = 0
	offcurves = []
	for index, node in enumerate(arc[1:], 1):
		if node.type == OFFCURVE:
			offcurves.append(node)
			continue
		if node.type == CURVE and len(offcurves) == 2:
			points = (
				_point(start),
				_point(offcurves[0]),
				_point(offcurves[1]),
				_point(node),
			)
			segments.append(
				(start, node, points, start_index, index, True)
			)
		elif node.type == LINE and not offcurves:
			start_point = _point(start)
			end_point = _point(node)
			points = (
				start_point,
				_lerp(start_point, end_point, 1.0 / 3.0),
				_lerp(start_point, end_point, 2.0 / 3.0),
				end_point,
			)
			segments.append(
				(start, node, points, start_index, index, False)
			)
		start = node
		start_index = index
		offcurves = []
	return segments


def _segment_sequence(arc):
	"""Return geometry-preserving line/cubic segments for an oriented arc."""
	return [
		(
			segment[2],
			segment[5],
			bool(segment[0].smooth),
			bool(segment[1].smooth),
		)
		for segment in _arc_drawable_segments(arc)
	]


def _reverse_segment_sequence(segments):
	return [
		(
			tuple(reversed(points)),
			is_curve,
			end_smooth,
			start_smooth,
		)
		for points, is_curve, start_smooth, end_smooth in reversed(segments)
	]


def _without_degenerate_sequence_segments(segments):
	"""Drop zero-length source fragments without removing real line detail."""
	cleaned = []
	for segment in segments:
		points = segment[0]
		x_values = [float(point[0]) for point in points]
		y_values = [float(point[1]) for point in points]
		if (
			max(x_values) - min(x_values) <= EPSILON
			and max(y_values) - min(y_values) <= EPSILON
		):
			continue
		cleaned.append(segment)
	return cleaned


def _fit_sequence_horizontally(segments, start_x, end_x):
	"""Fit a complete arc between two x landmarks with one affine mapping.

	Moving only an endpoint and its handle leaves a residual source segment when
	the target is much wider or narrower.  Transforming every point distributes
	the width change through the complete O-derived curve and keeps its segments
	continuous.  Y coordinates remain untouched, so the bottom stroke and
	vertical overshoot of O are preserved.
	"""
	segments = _without_degenerate_sequence_segments(segments)
	if not segments:
		raise GenerationError("The O-derived bowl arc has no drawable segments.")
	source_start = float(segments[0][0][0][0])
	source_end = float(segments[-1][0][3][0])
	source_span = source_end - source_start
	if abs(source_span) <= EPSILON:
		raise GenerationError("The O-derived bowl arc has no horizontal span.")
	target_start = float(start_x)
	target_end = float(end_x)
	scale = (target_end - target_start) / source_span
	fitted = []
	for points, is_curve, start_smooth, end_smooth in segments:
		fitted.append((
			tuple(
				(
					target_start
					+ (float(point[0]) - source_start) * scale,
					float(point[1]),
				)
				for point in points
			),
			is_curve,
			start_smooth,
			end_smooth,
		))
	return fitted


def _straighten_sequence_endpoint_vertically(segments, at_start):
	"""Make a curve endpoint truly tangent to its adjoining vertical stem."""
	segments = list(segments)
	index = 0 if at_start else -1
	points, is_curve, start_smooth, end_smooth = segments[index]
	if not is_curve:
		return segments
	points = list(points)
	endpoint_index = 0 if at_start else 3
	handle_index = 1 if at_start else 2
	points[handle_index] = (
		float(points[endpoint_index][0]),
		float(points[handle_index][1]),
	)
	segments[index] = (
		tuple(points), is_curve, start_smooth, end_smooth
	)
	return segments


def _move_sequence_bottom_extrema(segments, dx, dy):
	"""Move bottom on-curves and their adjacent handles as one feature."""
	segments = list(segments)
	bottom_y = min(
		float(points[index][1])
		for points, _is_curve, _start_smooth, _end_smooth in segments
		for index in (0, 3)
	)
	moved = []
	for points, is_curve, start_smooth, end_smooth in segments:
		points = [tuple(point) for point in points]
		if abs(float(points[0][1]) - bottom_y) <= EPSILON:
			points[0] = (points[0][0] + dx, points[0][1] + dy)
			if is_curve:
				points[1] = (points[1][0] + dx, points[1][1] + dy)
		if abs(float(points[3][1]) - bottom_y) <= EPSILON:
			points[3] = (points[3][0] + dx, points[3][1] + dy)
			if is_curve:
				points[2] = (points[2][0] + dx, points[2][1] + dy)
		moved.append((tuple(points), is_curve, start_smooth, end_smooth))
	return moved


def _sequence_segment_nodes(segment):
	"""Build temporary nodes for perpendicular boundary measurement."""
	points, is_curve, _start_smooth, _end_smooth = segment
	if is_curve:
		return [
			_new_node(points[0], LINE),
			_new_node(points[1], OFFCURVE),
			_new_node(points[2], OFFCURVE),
			_new_node(points[3], CURVE),
		]
	return [
		_new_node(points[0], LINE),
		_new_node(points[3], LINE),
	]


def _sequence_pair_thickness(inner_segment, outer_segment):
	return _shoulder_group_thickness((
		_sequence_segment_nodes(inner_segment),
		_sequence_segment_nodes(outer_segment),
		(bool(inner_segment[1]), bool(outer_segment[1])),
	))


def _compensate_U_right_transition(outer_arc, inner_arc, right_weight):
	"""Prevent a thin spot between U's weighted bottom and thin right stem.

	O's outer silhouette remains untouched. Only the two existing inner handles
	move, and they stay on the bottom-horizontal and right-vertical tangent axes.
	The search is driven by true local-normal thickness rather than x/y distance.
	"""
	outer_arc = list(outer_arc)
	inner_arc = list(inner_arc)
	if not outer_arc or not inner_arc:
		return inner_arc
	outer_segment = outer_arc[-1]
	inner_segment = _reverse_segment_sequence([inner_arc[0]])[0]
	if not outer_segment[1] or not inner_segment[1]:
		return inner_arc
	outer_points = [tuple(point) for point in outer_segment[0]]
	inner_points = [tuple(point) for point in inner_segment[0]]
	outer_bottom = outer_points[0]
	inner_bottom = inner_points[0]
	# Apply this bounded quarter-transition correction only when the paired
	# segments actually run from the lower extrema into the right stem.
	outer_floor = min(
		float(segment[0][index][1])
		for segment in outer_arc for index in (0, 3)
	)
	inner_floor = min(
		float(segment[0][index][1])
		for segment in inner_arc for index in (0, 3)
	)
	if (
		abs(float(outer_bottom[1]) - outer_floor) > EPSILON
		or abs(float(inner_bottom[1]) - inner_floor) > EPSILON
	):
		return inner_arc
	bottom_weight = abs(float(inner_bottom[1]) - float(outer_bottom[1]))
	target = float(right_weight) + (
		bottom_weight - float(right_weight)
	) * U_TRANSITION_WEIGHT_POSITION
	try:
		current = _sequence_pair_thickness(inner_segment, outer_segment)
	except GenerationError:
		return inner_arc
	if current >= target - W_STROKE_TOLERANCE:
		return inner_arc

	def candidate(factor):
		points = list(inner_points)
		# Preserve horizontal and vertical extrema tangents exactly.
		points[1] = (
			_lerp(inner_points[1], inner_points[0], factor)[0],
			float(inner_bottom[1]),
		)
		points[2] = (
			float(inner_points[3][0]),
			_lerp(inner_points[2], inner_points[3], factor)[1],
		)
		return (
			tuple(points), inner_segment[1],
			inner_segment[2], inner_segment[3],
		)

	try:
		limit = candidate(0.85)
		limit_width = _sequence_pair_thickness(limit, outer_segment)
	except GenerationError:
		return inner_arc
	if limit_width <= current + EPSILON:
		return inner_arc
	if limit_width < target:
		inner_arc[0] = _reverse_segment_sequence([limit])[0]
		return inner_arc

	low, high = 0.0, 0.85
	best = inner_segment
	for _iteration in range(18):
		middle = (low + high) * 0.5
		trial = candidate(middle)
		try:
			width = _sequence_pair_thickness(trial, outer_segment)
		except GenerationError:
			break
		best = trial
		if abs(width - target) <= W_STROKE_TOLERANCE:
			break
		if width < target:
			low = middle
		else:
			high = middle
	inner_arc[0] = _reverse_segment_sequence([best])[0]
	return inner_arc


def _split_segment_sequence(segments, segment_index, factor):
	points, is_curve, start_smooth, end_smooth = segments[segment_index]
	before_cubic, after_cubic = _split_cubic(points, factor)
	before = list(segments[:segment_index]) + [
		(before_cubic, is_curve, start_smooth, False)
	]
	after = [
		(after_cubic, is_curve, False, end_smooth)
	] + list(segments[segment_index + 1:])
	return before, after


def _split_segment_sequence_at_y(segments, target_y):
	"""Split an arbitrary line/cubic arc at a requested y coordinate."""
	target_y = float(target_y)
	for index, segment in enumerate(segments):
		points = segment[0]
		previous_factor = 0.0
		previous_value = float(points[0][1]) - target_y
		if abs(previous_value) <= EPSILON:
			return list(segments[:index]), list(segments[index:])
		for step in range(1, 65):
			factor = step / 64.0
			value = _cubic_point(points, factor)[1] - target_y
			if abs(value) <= EPSILON or previous_value * value < 0.0:
				low, high = previous_factor, factor
				low_value = previous_value
				for _refinement in range(60):
					middle = (low + high) * 0.5
					middle_value = _cubic_point(points, middle)[1] - target_y
					if abs(middle_value) <= EPSILON:
						low = high = middle
						break
					if low_value * middle_value <= 0.0:
						high = middle
					else:
						low = middle
						low_value = middle_value
				return _split_segment_sequence(
					segments, index, (low + high) * 0.5
				)
			previous_factor = factor
			previous_value = value
	raise GenerationError("The C opening falls outside O's right-side segments.")


def _split_segment_sequence_at_line(segments, center, direction):
	"""Split an arbitrary arc where it crosses a line through ``center``."""
	def distance(points, factor):
		point = _cubic_point(points, factor)
		return _cross(
			direction,
			(point[0] - center[0], point[1] - center[1]),
		)

	for index, segment in enumerate(segments):
		points = segment[0]
		previous_factor = 0.0
		previous_value = distance(points, previous_factor)
		if abs(previous_value) <= EPSILON:
			return list(segments[:index]), list(segments[index:])
		for step in range(1, 65):
			factor = step / 64.0
			value = distance(points, factor)
			if abs(value) <= EPSILON or previous_value * value < 0.0:
				low, high = previous_factor, factor
				low_value = previous_value
				for _refinement in range(60):
					middle = (low + high) * 0.5
					middle_value = distance(points, middle)
					if abs(middle_value) <= EPSILON:
						low = high = middle
						break
					if low_value * middle_value <= 0.0:
						high = middle
					else:
						low = middle
						low_value = middle_value
				return _split_segment_sequence(
					segments, index, (low + high) * 0.5
				)
			previous_factor = factor
			previous_value = value
	raise GenerationError("The C terminal cut does not cross O's outer contour.")


def _append_segment_sequence(path, segments):
	for points, is_curve, _start_smooth, end_smooth in segments:
		if is_curve:
			path.nodes.append(_new_node(points[1], OFFCURVE))
			path.nodes.append(_new_node(points[2], OFFCURVE))
			path.nodes.append(_new_node(points[3], CURVE, end_smooth))
		else:
			path.nodes.append(_new_node(points[3], LINE, end_smooth))


def _retarget_sequence_endpoint(segments, at_start, point):
	"""Move a cut endpoint and its adjacent handle without altering the arc."""
	segments = list(segments)
	index = 0 if at_start else -1
	points, is_curve, start_smooth, end_smooth = segments[index]
	points = list(points)
	point_index = 0 if at_start else 3
	handle_index = 1 if at_start else 2
	dx = float(point[0]) - float(points[point_index][0])
	dy = float(point[1]) - float(points[point_index][1])
	points[point_index] = (float(point[0]), float(point[1]))
	if is_curve:
		points[handle_index] = (
			float(points[handle_index][0]) + dx,
			float(points[handle_index][1]) + dy,
		)
	segments[index] = (
		tuple(points), is_curve, start_smooth, end_smooth
	)
	return segments


def _right_side_arc(path, start, end):
	"""Orient an arc from ``start`` to ``end`` without traversing the left side."""
	left_x = min(float(node.x) for node in _oncurve_nodes(path))
	for _attempt in range(2):
		arc = [start] + _forward_between(path, start, end)
		interior = [node for node in arc[1:-1] if node.type != OFFCURVE]
		if not any(abs(float(node.x) - left_x) <= EPSILON for node in interior):
			return arc
		path.reverse()
	raise GenerationError("Could not isolate O's right-side segments.")


def _right_top_bottom(path):
	"""Choose the right-hand nodes on flat or pointed top/bottom plateaus."""
	oncurves = _oncurve_nodes(path)
	top_y = max(float(node.y) for node in oncurves)
	bottom_y = min(float(node.y) for node in oncurves)
	top = max(
		(node for node in oncurves if abs(float(node.y) - top_y) <= EPSILON),
		key=lambda node: float(node.x),
	)
	bottom = max(
		(node for node in oncurves if abs(float(node.y) - bottom_y) <= EPSILON),
		key=lambda node: float(node.x),
	)
	return top, bottom


def _lower_arc_sequence(path, target_y):
	"""Return the left-to-right lower arc cut at ``target_y``."""
	top, bottom = _right_top_bottom(path)
	right = _segment_sequence(_right_side_arc(path, top, bottom))
	_left_top, right_cut_to_bottom = _split_segment_sequence_at_y(
		right, target_y
	)
	left = _segment_sequence(_left_arc_nodes(path, bottom, top))
	bottom_to_left_cut, _left_top = _split_segment_sequence_at_y(
		left, target_y
	)
	return (
		_reverse_segment_sequence(bottom_to_left_cut)
		+ _reverse_segment_sequence(right_cut_to_bottom)
	)


def _h_shoulder_arc(path, left_stem, right_stem, x_height):
	"""Find h's shoulder by contour events rather than fixed coordinates.

	This remains stable with slant, serif overhangs, extra extrema, and short
	line segments at either shoulder junction.
	"""
	for _attempt in range(2):
		nodes = list(path.nodes)
		oncurves = _oncurve_nodes(path)
		if len(oncurves) < 6:
			break
		top = max(oncurves, key=lambda node: float(node.y))
		bottom_y = min(float(node.y) for node in oncurves)
		rightmost = max(oncurves, key=lambda node: float(node.x))
		between_stems = (
			(left_stem[0] + left_stem[1] + right_stem[0] + right_stem[1])
			* 0.25
		)
		candidates = []
		for start in oncurves:
			if not (
				bottom_y + EPSILON < float(start.y) < float(x_height) * 1.10
				and float(start.x) < between_stems
			):
				continue
			for end in oncurves:
				if end is start:
					continue
				if (
					float(end.x) >= between_stems
					or float(end.y) <= float(start.y)
				):
					continue
				arc = [start] + _forward_between(path, start, end)
				if not arc or arc[-1] is not end:
					continue
				if rightmost not in arc or top in arc:
					continue
				if not any(
					node.type != OFFCURVE
					and abs(float(node.y) - bottom_y) <= EPSILON
					for node in arc
				):
					continue
				score = (
					abs(float(start.x) - float(left_stem[1]))
					+ abs(float(end.x) - float(left_stem[1]))
					+ len(arc) * 0.01
				)
				candidates.append((score, start, end, arc))
		if candidates:
			_score, start, end, arc = min(candidates, key=lambda item: item[0])
			return start, end, arc
		path.reverse()
	raise GenerationError("Could not identify h's shoulder contour.")


def _h_left_stem_path(layer, left_stem, right_stem, x_height):
	"""Keep h's original left stem and remove its shoulder/right stem.

	The complementary contour retains every serif, curved foot, slant, and
	intermediate node from h.  Only the two shoulder junctions are joined by a
	new straight segment along the stem's inside edge.
	"""
	closed_paths = [path for path in layer.paths if path.closed]
	if not closed_paths:
		raise GenerationError("The h source has no closed outline for its stem.")
	path = max(closed_paths, key=_bounds_area)
	inner_cut, outer_cut, _shoulder = _h_shoulder_arc(
		path, left_stem, right_stem, x_height
	)
	stem_arc = [outer_cut] + _forward_between(path, outer_cut, inner_cut)
	if not stem_arc or stem_arc[-1] is not inner_cut:
		raise GenerationError("Could not isolate h's left stem contour.")
	stem = GSPath()
	stem.closed = True
	for index, node in enumerate(stem_arc):
		stem.nodes.append(
			_copy_node(
				node,
				LINE if index == 0 else node.type,
				False if index in (0, len(stem_arc) - 1) else node.smooth,
			)
		)
	return stem


def _cubic_points_between(path, start, end):
	direct = _forward_between(path, start, end)
	if len(direct) == 3 and direct[0].type == OFFCURVE and direct[1].type == OFFCURVE:
		return (_point(start), _point(direct[0]), _point(direct[1]), _point(end))
	reverse = _forward_between(path, end, start)
	if len(reverse) == 3 and reverse[0].type == OFFCURVE and reverse[1].type == OFFCURVE:
		return (_point(start), _point(reverse[1]), _point(reverse[0]), _point(end))
	raise GenerationError("Expected a single cubic segment between landmarks.")


def _next_oncurve(path, node):
	for candidate in _forward_between(path, node, node)[:-1]:
		if candidate.type != OFFCURVE:
			return candidate
	raise GenerationError("Could not find the next on-curve landmark.")


def _previous_oncurve(path, node):
	nodes = list(path.nodes)
	index = nodes.index(node)
	for offset in range(1, len(nodes)):
		candidate = nodes[(index - offset) % len(nodes)]
		if candidate.type != OFFCURVE:
			return candidate
	raise GenerationError("Could not find the previous on-curve landmark.")


def _segment_handles(path, start, end):
	"""Return the two handles in start-to-end order for one cubic segment."""
	direct = _forward_between(path, start, end)
	if (
		len(direct) == 3
		and direct[0].type == OFFCURVE
		and direct[1].type == OFFCURVE
	):
		return direct[0], direct[1]
	reverse = _forward_between(path, end, start)
	if (
		len(reverse) == 3
		and reverse[0].type == OFFCURVE
		and reverse[1].type == OFFCURVE
	):
		return reverse[1], reverse[0]
	raise GenerationError("Expected a cubic segment between bowl extrema.")


def _move_extreme_with_handles(path, node, dx=0.0, dy=0.0):
	node.x = float(node.x) + dx
	node.y = float(node.y) + dy
	for neighbor in _adjacent_nodes(path, node):
		if neighbor.type == OFFCURVE:
			neighbor.x = float(neighbor.x) + dx
			neighbor.y = float(neighbor.y) + dy


def _straighten_horizontal_extrema_handles(layer):
	"""Make every curved top/bottom extremum genuinely horizontal."""
	for path in layer.paths:
		oncurves = _oncurve_nodes(path)
		if not oncurves:
			continue
		top = max(float(node.y) for node in oncurves)
		bottom = min(float(node.y) for node in oncurves)
		for node in oncurves:
			if not (
				abs(float(node.y) - top) <= EPSILON
				or abs(float(node.y) - bottom) <= EPSILON
			):
				continue
			for neighbor in _adjacent_nodes(path, node):
				if neighbor.type == OFFCURVE:
					neighbor.y = float(node.y)
			node.smooth = any(
				neighbor.type == OFFCURVE
				for neighbor in _adjacent_nodes(path, node)
			)


def _path_signed_area(path):
	nodes = _oncurve_nodes(path)
	if len(nodes) < 3:
		return 0.0
	return sum(
		float(node.x) * float(next_node.y)
		- float(next_node.x) * float(node.y)
		for node, next_node in zip(nodes, nodes[1:] + nodes[:1])
	) * 0.5


def _ensure_opposing_round_directions(layer):
	"""Ensure the counter winds opposite to the outer round contour."""
	outer, inner = _outer_and_inner_paths(layer)
	outer_area = _path_signed_area(outer)
	inner_area = _path_signed_area(inner)
	if abs(outer_area) <= EPSILON or abs(inner_area) <= EPSILON:
		raise GenerationError("O contains a contour with no measurable direction.")
	if outer_area * inner_area > 0.0:
		inner.reverse()


def _copy_decomposed(layer):
	try:
		return layer.copyDecomposedLayer()
	except Exception:
		copy = layer.copy()
		copy.decomposeComponents()
		return copy


def _require_bezier_source(layer, glyph_name):
	"""Validate the supported input format without changing the source."""
	# Decompose only a copy so quadratic curves inside components are detected.
	copy = _copy_decomposed(layer)
	if any(node.type == QCURVE for path in copy.paths for node in path.nodes):
		raise GenerationError(
			"%s contains TrueType curves. This script uses cubic Bezier curves "
			"and straight lines. Convert the source curves in Glyphs before building; "
			"the script does not convert them automatically." % glyph_name
		)


def _source_layer(font, glyph_name, master_id):
	override = _SOURCE_LAYER_OVERRIDES.get((glyph_name, master_id))
	if override is not None:
		_require_bezier_source(override, glyph_name)
		return override
	glyph = font.glyphs[glyph_name]
	if glyph is None:
		raise GenerationError("The source glyph %s does not exist." % glyph_name)
	layer = glyph.layers[master_id]
	if layer is None or not layer.shapes:
		raise GenerationError(
			"%s has no artwork in master %s."
			% (glyph_name, layer.name if layer is not None else master_id)
		)
	_require_bezier_source(layer, glyph_name)
	return layer


def _target_glyph(font, glyph_name):
	glyph = font.glyphs[glyph_name]
	if glyph is None:
		glyph = GSGlyph(glyph_name)
		font.glyphs.append(glyph)
		try:
			glyph.updateGlyphInfo()
		except Exception:
			pass
	return glyph


def _outer_and_inner_paths(o_layer):
	paths = [path for path in o_layer.paths if path.closed]
	if len(paths) != 2:
		raise GenerationError(
			"The round source must contain exactly two closed contours after components are "
			"decomposed (an outer contour and a counter)."
		)
	ordered = sorted(paths, key=_bounds_area, reverse=True)
	outer, inner = ordered[0], ordered[1]
	if _bounds_area(inner) <= EPSILON:
		raise GenerationError("The counter of o has zero area.")
	return outer, inner


def _translate_paths(paths, dx, dy=0.0):
	for path in paths:
		for node in path.nodes:
			node.x = float(node.x) + float(dx)
			node.y = float(node.y) + float(dy)


def _align_stem_interval(layer, source_interval, target_interval):
	"""Place one stem on another while matching both measured edges."""
	source_left, source_right = source_interval
	target_left, target_right = target_interval
	source_width = source_right - source_left
	if source_width <= EPSILON:
		raise GenerationError("Cannot align a zero-width stem.")
	for path in layer.paths:
		for node in path.nodes:
			x = float(node.x)
			if x <= source_left:
				node.x = x + target_left - source_left
			elif x >= source_right:
				node.x = x + target_right - source_right
			else:
				node.x = target_left + (
					(x - source_left)
					* (target_right - target_left)
					/ source_width
				)


def _align_bowl_to_left_stem(stem_layer, o_layer, stem_interval=None, extreme_tolerance=EPSILON):
	"""Align o's inner and outer left extremes to a left stem."""
	outer, inner = _outer_and_inner_paths(o_layer)
	if stem_interval is None:
		stem_left, _stem_bottom, stem_right, _stem_top = _bounds_values(
			stem_layer
		)
	else:
		stem_left, stem_right = stem_interval
	inner_left = _bounds_values(inner)[0]

	# Step 2: translate the complete o so its counter touches the stem edge.
	dx = stem_right - inner_left
	_translate_paths(o_layer.paths, dx)

	# Step 3: independently bring the outer-left curve extreme onto the
	# outside of the source stem. Moving its adjacent handles preserves the local
	# tangent instead of creating a kink.
	outer_left = _bounds_values(outer)[0]
	left_nodes = [
		node
		for node in _oncurve_nodes(outer)
		if abs(float(node.x) - outer_left) <= extreme_tolerance
	]
	if not left_nodes:
		raise GenerationError("Could not identify the outer-left extreme of o.")

	outer_shift = stem_left - outer_left
	moved = set()
	for node in left_nodes:
		node.x = float(node.x) + outer_shift
		moved.add(objc.pyobjc_id(node))
		for neighbor in _adjacent_nodes(outer, node):
			if neighbor.type == OFFCURVE and objc.pyobjc_id(neighbor) not in moved:
				neighbor.x = float(neighbor.x) + outer_shift
				moved.add(objc.pyobjc_id(neighbor))


def _remove_bowl_facing_bottom_serif(path, stem_interval):
	"""Replace only the lower, bowl-facing serif with a square stem corner."""
	_stem_left, stem_right = stem_interval
	oncurves = _oncurve_nodes(path)
	bottom_y = min(float(node.y) for node in oncurves)
	bottom_nodes = [
		node
		for node in oncurves
		if abs(float(node.y) - bottom_y) <= EPSILON
	]
	if not bottom_nodes:
		return
	bottom_right = max(bottom_nodes, key=lambda node: float(node.x))

	# The first low on-curve nearest the measured inside edge is the point where
	# the serif rejoins the vertical stem. This also handles bracketed serifs
	# containing more than one on-curve node.
	stem_width = max(EPSILON, stem_right - stem_interval[0])
	side_candidates = [
		node
		for node in oncurves
		if node is not bottom_right
		and float(node.y) > bottom_y + EPSILON
		and abs(float(node.x) - stem_right) <= stem_width * 0.75
	]
	if not side_candidates:
		# A plain sans stem may already end in a square corner.
		bottom_right.x = stem_right
		return
	side = min(
		side_candidates,
		key=lambda node: (
			float(node.y) - bottom_y,
			abs(float(node.x) - stem_right),
		),
	)

	forward = [bottom_right] + _forward_between(path, bottom_right, side)
	backward = [side] + _forward_between(path, side, bottom_right)
	if len(forward) <= len(backward):
		remove = forward[1:-1]
		line_end = side
	else:
		remove = backward[1:-1]
		line_end = bottom_right
	for node in remove:
		index = list(path.nodes).index(node)
		del path.nodes[index]

	bottom_right.x = stem_right
	bottom_right.smooth = False
	line_end.type = LINE
	line_end.smooth = False


def _straighten_stem_inner_edge(path, stem_interval):
	"""Remove h's obsolete shoulder landmarks from the isolated stem edge."""
	stem_left, stem_right = stem_interval
	stem_width = max(EPSILON, stem_right - stem_left)
	# In a hairline master, a fixed five-unit tolerance can include the opposite
	# stem edge and collapse its rectangle to a triangle.
	tolerance = min(max(5.0, stem_width * 0.08), stem_width * 0.4)
	oncurves = _oncurve_nodes(path)
	edge_nodes = [
		node
		for node in oncurves
		if abs(float(node.x) - stem_right) <= tolerance
	]
	if len(edge_nodes) < 2:
		raise GenerationError("Could not identify the isolated stem's inner edge.")
	bottom = min(edge_nodes, key=lambda node: float(node.y))
	top = max(edge_nodes, key=lambda node: float(node.y))

	bottom_to_top = [bottom] + _forward_between(path, bottom, top)
	top_to_bottom = [top] + _forward_between(path, top, bottom)

	def edge_score(nodes):
		# The shoulder-remnant route stays close to the measured stem edge;
		# the opposite route travels around the outside stem and its serifs.
		return (
			max(abs(float(node.x) - stem_right) for node in nodes),
			sum(abs(float(node.x) - stem_right) for node in nodes),
			len(nodes),
		)

	if edge_score(bottom_to_top) <= edge_score(top_to_bottom):
		remove = bottom_to_top[1:-1]
		line_end = top
	else:
		remove = top_to_bottom[1:-1]
		line_end = bottom
	for node in remove:
		index = list(path.nodes).index(node)
		del path.nodes[index]

	bottom.x = stem_right
	top.x = stem_right
	bottom.smooth = False
	top.smooth = False
	line_end.type = LINE


def _fit_left_bowl_curves_at_half(outer):
	"""Apply Glyphs' 50% Fit Curve geometry to the two left bowl segments."""
	top, _right, bottom = _round_extrema(outer)
	left = min(_oncurve_nodes(outer), key=lambda node: float(node.x))

	for extreme in (top, bottom):
		left_handle, extreme_handle = _segment_handles(outer, left, extreme)
		# The tangents at round extrema meet at (left.x, extreme.y). A 50%
		# fit places each selected handle halfway from its on-curve node to
		# that intersection, exactly matching the four-handle recipe.
		left_handle.x = float(left.x)
		left_handle.y = (float(left.y) + float(extreme.y)) * 0.5
		extreme_handle.x = (float(left.x) + float(extreme.x)) * 0.5
		extreme_handle.y = float(extreme.y)

	# Move the outer top and bottom nodes to the midpoint of their handles.
	# Deliberately do not move either handle.
	for extreme in (top, bottom):
		handles = [
			node
			for node in _adjacent_nodes(outer, extreme)
			if node.type == OFFCURVE
		]
		if len(handles) != 2:
			raise GenerationError(
				"Could not identify both handles at an outer bowl extreme."
			)
		extreme.x = (float(handles[0].x) + float(handles[1].x)) * 0.5
		extreme.y = (float(handles[0].y) + float(handles[1].y)) * 0.5
		extreme.smooth = True


def _compensate_angular_bowl_joins(outer, outer_arc, inner_arc, target):
	"""Offset only the left diamond edges; intersect with unchanged right edges."""
	def line(first, second):
		dx, dy = float(second.x - first.x), float(second.y - first.y)
		length = (dx * dx + dy * dy) ** 0.5
		if length <= EPSILON:
			raise GenerationError("o's angular bowl contains a zero-length edge.")
		normal = (-dy / length, dx / length)
		return normal, normal[0] * float(first.x) + normal[1] * float(first.y)

	def intersection(first, second):
		(a, b), c = first
		(d, e), f = second
		determinant = a * e - b * d
		if abs(determinant) <= EPSILON:
			raise GenerationError("o's angular bowl has parallel adjacent edges.")
		return ((c * e - b * f) / determinant, (a * f - c * d) / determinant)

	lines = []
	for index in range(len(inner_arc) - 1):
		normal, constant = line(inner_arc[index], inner_arc[index + 1])
		gap = (float(outer_arc[index].x - inner_arc[index].x),
			float(outer_arc[index].y - inner_arc[index].y))
		sign = 1.0 if sum(normal[j] * gap[j] for j in (0, 1)) >= 0 else -1.0
		lines.append((normal, constant + sign * target))
	# Moving an angular top node at fixed y would alter the opposite o edge and
	# taper it to a hairline. Intersect with that original edge instead, preserving
	# its slope and weight. This moves corners, never adds handles or nodes.
	positions = []
	for index, node in enumerate(outer_arc):
		if index in (0, len(outer_arc) - 1):
			neighbor = max(_adjacent_nodes(outer, node), key=lambda n: float(n.x))
			positions.append(intersection(
				lines[0 if index == 0 else -1], line(node, neighbor)
			))
		else:
			first, second = lines[index-1], lines[index]
			if abs(_cross(first[0],second[0])) <= EPSILON:
				# A collinear subdivision is not a corner. Project it onto the
				# offset edge and retain the extra node instead of rejecting it.
				normal, constant = first
				shift = constant-normal[0]*float(node.x)-normal[1]*float(node.y)
				positions.append((float(node.x)+normal[0]*shift,float(node.y)+normal[1]*shift))
			else:
				positions.append(intersection(first, second))
	for node, (x, y) in zip(outer_arc, positions):
		node.x, node.y = x, y


def _bowl_stem_source_weight(h_layer, group):
	"""Measure h's shoulder normally, allowing a normal to cross an extra join."""
	try:
		return _shoulder_group_thickness(group)
	except GenerationError:
		# In heavy h's, the two attachments can be at very different heights.
		# A valid local normal then crosses an adjacent segment rather than
		# the corresponding single cubic. Use the actual closed h outline,
		# not an extrapolated cubic or a guessed vertical/horizontal width.
		inner, outer = _boundary_group_cubics(group)
		center = tuple(_lerp(a, b, 0.5) for a, b in zip(inner, outer))
		weights = []
		for factor in (0.35, 0.5, 0.65):
			try:
				weight = _S_normal_thickness(h_layer, _cubic_point(center, factor),
					_cubic_tangent(center, factor))
			except GenerationError:
				continue
			if weight > EPSILON:
				weights.append(weight)
		if len(weights) < 2:
			raise GenerationError("Could not measure h's shoulder weight for b/p/d/q.")
		weights.sort()
		return weights[len(weights) // 2]


def _apply_bowl_stem_join_recipe(o_layer, stem_interval, h_layer, right_stem, x_height, stroke_factor=1.0):
	"""Use h's shoulder weight at both bowl/stem joins, retaining o's bowl."""
	outer, inner = _outer_and_inner_paths(o_layer)
	outer_left = min(_oncurve_nodes(outer), key=lambda node: float(node.x))
	stem_center = (float(stem_interval[0]) + float(stem_interval[1])) * 0.5
	_move_extreme_with_handles(
		outer,
		outer_left,
		dx=stem_center - float(outer_left.x),
	)
	# The old independent 50% fit could pull the outer curve almost onto the
	# counter in thin masters. Start with o's own handles instead, then restore
	# the actual perpendicular weight of h's first (stem-facing) shoulder segment.
	shoulder = _h_shoulder_boundary_pairs(
		max((path for path in h_layer.paths if path.closed), key=_bounds_area),
		stem_interval, right_stem, x_height, ignore_stem_join_connectors=True
	)
	target = _bowl_stem_source_weight(h_layer, shoulder[0]) * stroke_factor
	outer_top, _outer_right, outer_bottom = _round_extrema(outer)
	inner_top, _inner_right, inner_bottom = _round_extrema(inner)
	outer_arc = _left_arc_nodes(outer, outer_top, outer_bottom)
	inner_arc = _left_arc_nodes(inner, inner_top, inner_bottom)
	outer_segments = _arc_drawable_segments(outer_arc)
	inner_segments = _arc_drawable_segments(inner_arc)
	if len(outer_segments) != len(inner_segments):
		raise GenerationError("o's left bowl boundaries need corresponding segments for b/p/d/q.")
	if all(node.type == LINE for path in (outer, inner) for node in path.nodes):
		_compensate_angular_bowl_joins(outer, outer_arc, inner_arc, target)
	else:
		_compensate_bowl_handles(
			outer_arc, inner_arc, [target] * len(outer_segments), "b/p/d/q"
		)

def _cross(vector_a, vector_b):
	return vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0]


def _remove_redundant_line_nodes(layer):
	"""Delete collinear line nodes such as o's old left extreme on the stem."""
	for path in layer.paths:
		changed = True
		while changed and len(path.nodes) > 3:
			changed = False
			nodes = list(path.nodes)
			for index, node in enumerate(nodes):
				previous = nodes[(index - 1) % len(nodes)]
				next_node = nodes[(index + 1) % len(nodes)]
				if (
					node.type != LINE
					or previous.type == OFFCURVE
					or next_node.type == OFFCURVE
				):
					continue
				incoming = (
					float(node.x) - float(previous.x),
					float(node.y) - float(previous.y),
				)
				outgoing = (
					float(next_node.x) - float(node.x),
					float(next_node.y) - float(node.y),
				)
				scale = max(
					1.0,
					abs(incoming[0]) + abs(incoming[1]),
					abs(outgoing[0]) + abs(outgoing[1]),
				)
				if abs(_cross(incoming, outgoing)) > EPSILON * scale:
					continue
				if incoming[0] * outgoing[0] + incoming[1] * outgoing[1] <= 0:
					continue
				del path.nodes[index]
				changed = True
				break


def _finish_candidate(layer, remove_overlap=True):
	# Newly constructed rectangles have no glyph context yet, so normalize their
	# winding before asking Glyphs to union them. Without this, two overlapping
	# bars can be interpreted as an intersection (most visibly in L).
	layer.correctPathDirection()
	if remove_overlap:
		layer.removeOverlap()
	_remove_redundant_line_nodes(layer)
	layer.roundCoordinates()
	layer.correctPathDirection()
	return layer


def _H_left_stem_paths(copy, left_stem, right_stem, crossbar):
	"""Clip H to its left stem while retaining top and bottom serif overhangs."""
	left, bottom, _right, top = _bounds_values(copy)
	middle = (left_stem[1] + right_stem[0]) * 0.5
	padding = max(1000.0, top - bottom)
	mask = _layer_from_paths(
		[
			_rectangle_path(
				left - padding,
				bottom - padding,
				left_stem[1],
				top + padding,
			),
			_rectangle_path(
				left - padding,
				crossbar[1],
				middle,
				top + padding,
			),
			_rectangle_path(
				left - padding,
				bottom - padding,
				middle,
				crossbar[0],
			),
		],
		0,
	)
	mask = _finish_candidate(mask)
	result = intersectPaths(
		[path.copy() for path in copy.paths],
		[path.copy() for path in mask.paths],
	)
	if not result:
		raise GenerationError("Could not isolate H's left stem.")
	return result


def _build_H_derived(font, master, character):
	source = _source_layer(font, "H", master.id)
	copy, left_stem, right_stem, crossbar = _measure_H_source(source, master)
	left, _bottom, right, _top = _bounds_values(copy)
	span = right - left
	bar_height = crossbar[1] - crossbar[0]
	cap_height = float(master.capHeight)
	left_margin = left
	right_margin = float(source.width) - right
	if character == "I":
		# I is exactly H's measured left stem. Building it directly avoids the
		# one-unit Boolean clipping jogs left at H's crossbar boundaries.
		paths = [
			_rectangle_path(
				left_stem[0], 0.0, left_stem[1], cap_height
			)
		]
		width = left_margin * 2.0 + (left_stem[1] - left_stem[0])
		return _finish_candidate(_layer_from_paths(paths, width))

	stem_paths = _H_left_stem_paths(
		copy, left_stem, right_stem, crossbar
	)
	paths = [path.copy() for path in stem_paths]
	stem_bounds = _bounds_values(_layer_from_paths(stem_paths, 0))

	if character == "T":
		center = (left + right) * 0.5
		stem_center = (stem_bounds[0] + stem_bounds[2]) * 0.5
		_translate_paths(paths, center - stem_center)
		paths.append(_rectangle_path(left, cap_height - bar_height, right, cap_height))
		width = float(source.width)
	else:
		full_end = left + span * (0.82 if character in ("E", "F") else 0.78)
		middle_end = left + span * 0.68
		if character in ("E", "F"):
			paths.append(
				_rectangle_path(left, cap_height - bar_height, full_end, cap_height)
			)
			paths.append(
				_rectangle_path(left, crossbar[0], middle_end, crossbar[1])
			)
		if character in ("E", "L"):
			paths.append(_rectangle_path(left, 0.0, full_end, bar_height))
		width = full_end + right_margin

	return _finish_candidate(_layer_from_paths(paths, width))


def _diagonal_strip_path(left, right, bottom, top, thickness, ascending):
	"""Make a flat-ended diagonal with exact perpendicular thickness."""
	span = float(right) - float(left)
	height = float(top) - float(bottom)
	if min(span, height, float(thickness)) <= EPSILON:
		raise GenerationError("Cannot build an X diagonal from zero-size geometry.")
	horizontal_width = float(thickness)
	for _iteration in range(20):
		center_span = span - horizontal_width
		if center_span <= EPSILON:
			raise GenerationError("H's stem is too wide for the requested X.")
		slope = center_span / height
		updated = float(thickness) * (1.0 + slope * slope) ** 0.5
		if abs(updated - horizontal_width) <= 0.0001:
			horizontal_width = updated
			break
		horizontal_width = updated
	half = horizontal_width * 0.5
	if ascending:
		bottom_center = float(left) + half
		top_center = float(right) - half
	else:
		bottom_center = float(right) - half
		top_center = float(left) + half
	path = GSPath()
	path.closed = True
	for point in (
		(bottom_center - half, bottom),
		(bottom_center + half, bottom),
		(top_center + half, top),
		(top_center - half, top),
	):
		path.nodes.append(_new_node(point, LINE))
	return path


def _single_diagonal_profile(path, positions=V_PROFILE_POSITIONS):
	"""Measure a single diagonal contour perpendicular to its centerline."""
	layer = _layer_from_paths([path], 0)
	_left, bottom, _right, top = _bounds_values(path)
	height = top - bottom
	if height <= EPSILON:
		raise GenerationError("X contains a diagonal with no measurable height.")
	delta = max(0.5, height * 0.015)
	profile = []
	for progress in positions:
		y = bottom + height * float(progress)
		before_y = max(bottom + 0.01, y - delta)
		after_y = min(top - 0.01, y + delta)
		before = _scan_x_intersections(layer, before_y)
		after = _scan_x_intersections(layer, after_y)
		middle = _scan_x_intersections(layer, y)
		if min(len(before), len(after), len(middle)) < 2:
			raise GenerationError("Could not measure one of X's diagonal strokes.")
		center_before = (before[0] + before[-1]) * 0.5
		center_after = (after[0] + after[-1]) * 0.5
		slope = (center_after - center_before) / (after_y - before_y)
		horizontal_width = middle[-1] - middle[0]
		profile.append(horizontal_width / (1.0 + slope * slope) ** 0.5)
	return tuple(profile)


def _diagonal_center_at_y(path, y):
	layer = _layer_from_paths([path], 0)
	_left, bottom, _right, top = _bounds_values(path)
	probe_y = min(top - 0.01, max(bottom + 0.01, float(y)))
	intersections = _scan_x_intersections(layer, probe_y)
	if len(intersections) < 2:
		raise GenerationError("Could not locate X's diagonal centerline.")
	return (intersections[0] + intersections[-1]) * 0.5


def _compensate_single_diagonal(path, factors):
	"""Adjust cross-stroke width while retaining the sheared centerline."""
	reference = path.copy()
	_left, bottom, _right, top = _bounds_values(reference)
	height = top - bottom
	for node in path.nodes:
		progress = (float(node.y) - bottom) / max(EPSILON, height)
		factor = _interpolate_profile_value(
			progress, V_PROFILE_POSITIONS, factors
		)
		center = _diagonal_center_at_y(reference, node.y)
		node.x = center + (float(node.x) - center) * factor


def _V_left_diagonal_path(layer):
	"""Return V's left, descending diagonal without assuming node topology."""
	candidates = []
	for path in _copy_decomposed(layer).paths:
		if not path.closed:
			continue
		oncurves = _oncurve_nodes(path)
		if not oncurves:
			continue
		bottom = min(float(node.y) for node in oncurves)
		top = max(float(node.y) for node in oncurves)
		if top - bottom <= EPSILON:
			continue
		bottom_nodes = [
			node for node in oncurves
			if abs(float(node.y) - bottom) <= EPSILON
		]
		top_nodes = [
			node for node in oncurves
			if abs(float(node.y) - top) <= EPSILON
		]
		bottom_center = sum(float(node.x) for node in bottom_nodes) / len(bottom_nodes)
		top_center = sum(float(node.x) for node in top_nodes) / len(top_nodes)
		if top_center < bottom_center - EPSILON:
			candidates.append((top - bottom, bottom_center - top_center, path))
	if not candidates:
		raise GenerationError("V has no identifiable left descending diagonal.")
	return max(candidates, key=lambda item: (item[0], item[1]))[2].copy()


def _remap_diagonal_centerline(
	source_path, target_top_center, target_top_y, target_bottom_center,
	target_bottom_y=0.0,
):
	"""Remap a diagonal while retaining every node's perpendicular offset."""
	source = source_path.copy()
	oncurves = _oncurve_nodes(source)
	if not oncurves:
		raise GenerationError("V's left diagonal is empty.")
	source_bottom = min(float(node.y) for node in oncurves)
	source_top = max(float(node.y) for node in oncurves)
	source_height = source_top - source_bottom
	target_height = float(target_top_y) - float(target_bottom_y)
	if min(source_height, target_height) <= EPSILON:
		raise GenerationError("R's diagonal leg has no usable height.")
	source_bottom_nodes = [
		node for node in oncurves
		if abs(float(node.y) - source_bottom) <= EPSILON
	]
	source_top_nodes = [
		node for node in oncurves
		if abs(float(node.y) - source_top) <= EPSILON
	]
	source_bottom_center = sum(
		float(node.x) for node in source_bottom_nodes
	) / len(source_bottom_nodes)
	source_top_center = sum(
		float(node.x) for node in source_top_nodes
	) / len(source_top_nodes)
	source_slope = (source_top_center - source_bottom_center) / source_height
	target_slope = (
		float(target_top_center) - float(target_bottom_center)
	) / target_height
	source_normal_scale = (1.0 + source_slope * source_slope) ** 0.5
	target_normal_scale = (1.0 + target_slope * target_slope) ** 0.5
	for node in source.nodes:
		progress = (float(node.y) - source_bottom) / source_height
		source_center = (
			source_bottom_center
			+ (source_top_center - source_bottom_center) * progress
		)
		perpendicular_offset = (
			float(node.x) - source_center
		) / source_normal_scale
		target_center = (
			float(target_bottom_center)
			+ (float(target_top_center) - float(target_bottom_center)) * progress
		)
		node.x = target_center + perpendicular_offset * target_normal_scale
		node.y = float(target_bottom_y) + target_height * progress
	return source


def _build_R_leg(V_source, top_center, top_y, target_right):
	"""Place V's left diagonal as R's leg and preserve its stroke profile."""
	source_path = _V_left_diagonal_path(V_source)
	target_profile = _single_diagonal_profile(source_path)
	bottom_center = float(target_right)
	for _placement_iteration in range(12):
		leg = _remap_diagonal_centerline(
			source_path,
			float(top_center),
			float(top_y),
			bottom_center,
			0.0,
		)
		for _compensation_iteration in range(12):
			current_profile = _single_diagonal_profile(leg)
			profile_error = max(
				abs(current - target)
				for current, target in zip(current_profile, target_profile)
			)
			if profile_error <= W_STROKE_TOLERANCE:
				break
			factors = tuple(
				max(0.90, min(1.10, target / current))
				for current, target in zip(current_profile, target_profile)
			)
			_compensate_single_diagonal(leg, factors)
		else:
			raise GenerationError(
				"R's perpendicular leg compensation did not converge."
			)
		oncurves = _oncurve_nodes(leg)
		bottom = min(float(node.y) for node in oncurves)
		bottom_nodes = [
			node for node in oncurves
			if abs(float(node.y) - bottom) <= EPSILON
		]
		bottom_right = max(float(node.x) for node in bottom_nodes)
		placement_error = float(target_right) - bottom_right
		if abs(placement_error) <= 0.0001:
			return leg
		bottom_center += placement_error
	raise GenerationError("R's leg could not align with P's right edge.")


def _correct_X_diagonal_directions(layer):
	"""Treat both overlapping diagonals as filled outer contours, not counters."""
	for path in layer.paths:
		if not path.closed:
			continue
		# Whole-layer correction can classify one crossing strip as a counter.
		# Normalize each strip independently and retain the two editable shapes.
		single = _layer_from_paths([path], 0)
		single.correctPathDirection()
		if path.direction != single.paths[0].direction:
			path.reverse()
	return layer


def _build_X(font, master):
	"""Build X from H's horizontal and vertical perpendicular stem weights."""
	H_source = _source_layer(font, "H", master.id)
	H_copy, left_stem, _right_stem, crossbar = _measure_H_source(
		H_source, master
	)
	left, _bottom, right, _top = _bounds_values(H_copy)
	center = (left + right) * 0.5
	target_width = (right - left) * X_WIDTH_FACTOR
	left = center - target_width * 0.5
	right = center + target_width * 0.5
	cap_height = float(master.capHeight)
	horizontal_weight = crossbar[1] - crossbar[0]
	vertical_weight = left_stem[1] - left_stem[0]
	ascending = _diagonal_strip_path(
		left, right, 0.0, cap_height, horizontal_weight, True
	)
	descending = _diagonal_strip_path(
		left, right, 0.0, cap_height, vertical_weight, False
	)
	candidate = _layer_from_paths(
		[ascending, descending], float(H_source.width)
	)
	return _correct_X_diagonal_directions(candidate)


def _align_V_diagonal_join(paths, axis=None):
	"""Align the bottom-right landmarks by translating whole diagonal contours.

	Compensation can separate this join even when it was aligned in the source.
	Never repair it by dragging individual nodes or changing either angle.
	Joined single-contour sources already have a shared outline and need no move.
	"""
	paths = list(paths)
	if len(paths) != 2 or any(not path.closed for path in paths):
		return

	def end_nodes(path, at_top):
		oncurves = _oncurve_nodes(path)
		if not oncurves:
			raise GenerationError("Cannot align an empty V diagonal.")
		y = (max if at_top else min)(float(node.y) for node in oncurves)
		return [node for node in oncurves if abs(float(node.y) - y) <= EPSILON]

	left, right = sorted(
		paths,
		key=lambda path: sum(float(node.x) for node in end_nodes(path, True))
		/ len(end_nodes(path, True)),
	)
	left_bottom = end_nodes(left, False)
	right_bottom = end_nodes(right, False)
	if abs(float(left_bottom[0].y) - float(right_bottom[0].y)) > EPSILON:
		raise GenerationError("V's diagonal bottoms must share the same baseline.")
	dx = max(float(node.x) for node in right_bottom) - max(
		float(node.x) for node in left_bottom
	)
	_translate_paths([left], dx)
	if axis is None:
		return
	center = (
		min(float(node.x) for node in left_bottom + right_bottom)
		+ max(float(node.x) for node in left_bottom + right_bottom)
	) * 0.5
	_translate_paths(paths, float(axis) - center)


def _build_V(font, master):
	"""Build V at 105% of H's outline width, retaining X's stroke weights."""
	X_source = _source_layer(font, "X", master.id)
	H_source = _source_layer(font, "H", master.id)
	X_copy = _copy_decomposed(X_source)
	paths = sorted(
		(path for path in X_copy.paths if path.closed),
		key=_bounds_area,
		reverse=True,
	)
	if len(paths) != 2:
		raise GenerationError(
			"X must contain two separate closed diagonal contours to build V."
		)
	left, _bottom, right, _top = _bounds_values(X_copy)
	h_left, _h_bottom, h_right, _h_top = _bounds_values(H_source)
	axis = (left + right) * 0.5
	target_width = (h_right - h_left) * V_WIDTH_FACTOR
	target_left = axis - target_width * 0.5
	target_right = axis + target_width * 0.5
	bottom_target = axis
	for _placement_iteration in range(8):
		result_paths = []
		for source_path in paths:
			target_profile = _single_diagonal_profile(source_path)
			source_oncurves = _oncurve_nodes(source_path)
			source_top = max(float(node.y) for node in source_oncurves)
			source_top_nodes = [
				node for node in source_oncurves
				if abs(float(node.y) - source_top) <= EPSILON
			]
			is_left = (
				sum(float(node.x) for node in source_top_nodes)
				/ len(source_top_nodes)
				< axis
			)
			target_outer = target_left if is_left else target_right
			path = source_path.copy()
			for _iteration in range(20):
				oncurves = _oncurve_nodes(path)
				if not oncurves:
					raise GenerationError("X contains an empty diagonal contour.")
				path_bottom = min(float(node.y) for node in oncurves)
				path_top = max(float(node.y) for node in oncurves)
				bottom_nodes = [
					node for node in oncurves
					if abs(float(node.y) - path_bottom) <= EPSILON
				]
				bottom_right = max(float(node.x) for node in bottom_nodes)
				path_left, _b, path_right, _t = _bounds_values(path)
				current_outer = path_left if is_left else path_right
				bottom_shift = bottom_target - bottom_right
				outer_shift = target_outer - current_outer
				path_height = max(EPSILON, path_top - path_bottom)
				for node in path.nodes:
					progress = max(
						0.0,
						min(1.0, (float(node.y) - path_bottom) / path_height),
					)
					node.x = (
						float(node.x)
						+ bottom_shift * (1.0 - progress)
						+ outer_shift * progress
					)
				current_profile = _single_diagonal_profile(path)
				error = max(
					abs(current - target)
					for current, target in zip(current_profile, target_profile)
				)
				updated_bottom_right = max(
					float(node.x) for node in bottom_nodes
				)
				updated_left, _b, updated_right, _t = _bounds_values(path)
				updated_outer = updated_left if is_left else updated_right
				if (
					error <= W_STROKE_TOLERANCE
					and abs(updated_bottom_right - bottom_target) <= EPSILON
					and abs(updated_outer - target_outer) <= EPSILON
				):
					break
				factors = tuple(
					max(0.95, min(1.05, target / current))
					for current, target in zip(current_profile, target_profile)
				)
				_compensate_single_diagonal(path, factors)
			else:
				raise GenerationError(
					"V's perpendicular stroke compensation did not converge."
				)
			result_paths.append(path)

		bottom_nodes = []
		for path in result_paths:
			oncurves = _oncurve_nodes(path)
			path_bottom = min(float(node.y) for node in oncurves)
			bottom_nodes.extend(
				node for node in oncurves
				if abs(float(node.y) - path_bottom) <= EPSILON
			)
		bottom_center = (
			min(float(node.x) for node in bottom_nodes)
			+ max(float(node.x) for node in bottom_nodes)
		) * 0.5
		centering_error = axis - bottom_center
		if abs(centering_error) <= EPSILON:
			break
		bottom_target += centering_error
	else:
		raise GenerationError("V's bottom nodes could not be centered.")
	_align_V_diagonal_join(result_paths, axis)
	candidate = _layer_from_paths(result_paths, float(X_source.width))
	return _correct_X_diagonal_directions(candidate)


def _align_and_trim_Y_fork(paths, stem_left, stem_right):
	"""Match the visible stem corners, then trim the exposed diagonal tip.

	The fork's bottom and the stem's top share the SAME y coordinate. Aligning
	below that seam creates shoulders, even when the bottom nodes look aligned.
	Round the strips before calling this helper so their shared corners remain
	exact after installation; placement is a rigid horizontal translation.
	"""
	def end_nodes(path, top):
		nodes = _oncurve_nodes(path)
		y = (max if top else min)(float(node.y) for node in nodes)
		return sorted(
			[node for node in nodes if abs(float(node.y) - y) <= EPSILON],
			key=lambda node: float(node.x),
		)

	left_path, right_path = sorted(
		paths,
		key=lambda path: sum(float(node.x) for node in end_nodes(path, True))
		/ len(end_nodes(path, True)),
	)
	_translate_paths([left_path], stem_left - float(end_nodes(left_path, False)[0].x))
	_translate_paths([right_path], stem_right - float(end_nodes(right_path, False)[-1].x))
	# Even the thinner diagonal can overhang the opposite stem corner in a
	# low-contrast design. Clip BOTH strips to the fork's outside envelope.
	for path, opposing, keep_left in (
		(left_path, right_path, True), (right_path, left_path, False),
	):
		if any(node.type != LINE for node in path.nodes):
			raise GenerationError("Y's tip trim needs straight-sided V diagonals.")
		edge_index = -1 if keep_left else 0
		a = _point(end_nodes(opposing, False)[edge_index])
		b = _point(end_nodes(opposing, True)[edge_index])
		if b[1] - a[1] <= EPSILON:
			raise GenerationError("Could not identify Y's opposing diagonal edge.")

		def distance(point):
			edge_x = a[0] + (point[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
			return edge_x - point[0] if keep_left else point[0] - edge_x

		points = [_point(node) for node in path.nodes]
		clipped = []
		previous = points[-1]
		previous_distance = distance(previous)
		for current in points:
			current_distance = distance(current)
			if (previous_distance >= 0.0) != (current_distance >= 0.0):
				progress = previous_distance / (previous_distance - current_distance)
				clipped.append(_lerp(previous, current, progress))
			if current_distance >= 0.0:
				clipped.append(current)
			previous, previous_distance = current, current_distance
		# Round each sliced corner's y first and quantise x inward at that y,
		# so nearest-grid rounding cannot leave a protrusion after clipping.
		quantised = []
		for x, y in clipped:
			y = round(y)
			edge_x = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
			x = min(round(x), floor(edge_x + 1e-9)) if keep_left else max(round(x), ceil(edge_x - 1e-9))
			point = (x, y)
			if not quantised or point != quantised[-1]:
				quantised.append(point)
		if len(quantised) > 1 and quantised[0] == quantised[-1]:
			quantised.pop()
		if len(quantised) < 3:
			raise GenerationError("Y's diagonal tip is too small for the font-unit grid.")
		for index in range(len(path.nodes) - 1, -1, -1):
			del path.nodes[index]
		for point in quantised:
			path.nodes.append(_new_node(point, LINE))


def _build_Y(font, master):
	"""Meet a compensated V fork precisely with a short H-weight upright."""
	V_source = _source_layer(font, "V", master.id)
	H_source = _source_layer(font, "H", master.id)
	_H_copy, left_stem, _right_stem, crossbar = _measure_H_source(
		H_source, master
	)
	stem_weight = float(left_stem[1]) - float(left_stem[0])
	cap_height = float(master.capHeight)
	horizontal_weight = float(crossbar[1]) - float(crossbar[0])
	contrasty = horizontal_weight / stem_weight < U_SANS_CONTRAST_THRESHOLD
	stem_top = round(cap_height * (
		Y_STEM_HEIGHT_FACTOR + (Y_CONTRAST_JUNCTION_RISE if contrasty else 0.0)
	))
	source = _copy_decomposed(V_source)
	if len(source.paths) != 2 or any(not path.closed for path in source.paths):
		raise GenerationError("V needs two separate closed diagonals to build Y.")
	left, bottom, right, top = _bounds_values(source)
	if min(top - bottom, cap_height - stem_top, stem_weight) <= EPSILON:
		raise GenerationError("Y needs positive cap height and usable V/H strokes.")
	# Terminate both strips at the actual visible seam, not below it. Their
	# bottom edges cover the upright's cap while their inner edges form the
	# crotch above it. This avoids exposed shoulders and buried extra corners.
	fork_bottom = stem_top
	axis = (left + right) * 0.5
	candidate = source.copy()
	getter = getattr(candidate, "temporarilyDisableRounding", None)
	setter = getattr(candidate, "setTemporarilyDisableRounding_", None)
	if getter is None or not callable(setter):
		raise GenerationError("Y's stroke compensation needs Glyphs' native precision API.")
	previous_rounding = bool(getter() if callable(getter) else getter)
	setter(True)
	try:
		_transform_paths_affinely(
			candidate.paths,
			(axis, (bottom + top) * 0.5),
			(axis, (fork_bottom + cap_height) * 0.5),
			1.0,
			(cap_height - fork_bottom) / (top - bottom),
		)
		for source_path, path in zip(source.paths, candidate.paths):
			target_profile = _single_diagonal_profile(source_path)
			for _iteration in range(20):
				current_profile = _single_diagonal_profile(path)
				if max(
					abs(current - target)
					for current, target in zip(current_profile, target_profile)
				) <= min(W_STROKE_TOLERANCE, 0.1):
					break
				_compensate_single_diagonal(path, tuple(
					max(0.95, min(1.05, target / current))
					for current, target in zip(current_profile, target_profile)
				))
			else:
				raise GenerationError("Y's perpendicular stroke compensation did not converge.")
	finally:
		setter(previous_rounding)
	# Quantise first, then share integer landmarks. This applies equally to
	# low-contrast and contrasty designs; independent rounding must not shift
	# a diagonal away from the stem corner.
	_round_candidate_geometry(candidate)
	stem_left = round(axis - stem_weight * 0.5)
	stem_right = stem_left + round(stem_weight)
	_align_and_trim_Y_fork(candidate.paths, stem_left, stem_right)
	seam_probe = _layer_from_paths([path.copy() for path in candidate.paths], 0)
	_correct_X_diagonal_directions(seam_probe)
	seam_probe.removeOverlap()
	seam_probe = _layer_from_paths([path.copy() for path in seam_probe.paths], 0)
	coverage = _scan_x_intersections(seam_probe, stem_top + 0.02)
	if len(coverage) != 2:
		raise GenerationError("Y's V strokes are too thin to cover its H-weight stem at the join.")
	# Read fresh geometry: copied layers can retain their source's cached bounds.
	candidate = _layer_from_paths([path.copy() for path in candidate.paths], 0)
	final_left, _bottom, final_right, _top = _bounds_values(candidate)
	# The same landmarks used for diagonal placement define the upright.
	candidate.shapes.append(_rectangle_path(
		stem_left, 0.0, stem_right, stem_top,
	))
	_translate_paths(candidate.paths, round(left - final_left))
	candidate = _layer_from_paths(
		[path.copy() for path in candidate.paths],
		final_right - final_left + left + float(V_source.width) - right,
	)
	return _correct_X_diagonal_directions(candidate)


def _M_diagonal_paths(V_source, target_left, target_right, axis):
	"""Spread V's two contours for M while preserving their local weights."""
	V_copy = _copy_decomposed(V_source)
	paths = sorted(
		(path for path in V_copy.paths if path.closed),
		key=_bounds_area,
		reverse=True,
	)
	if len(paths) != 2:
		raise GenerationError(
			"V must contain two separate closed diagonal contours to build M."
		)
	source_left, _bottom, source_right, _top = _bounds_values(V_copy)
	source_axis = (source_left + source_right) * 0.5
	bottom_target = float(axis)
	for _placement_iteration in range(8):
		result_paths = []
		for source_path in paths:
			target_profile = _single_diagonal_profile(source_path)
			source_oncurves = _oncurve_nodes(source_path)
			source_top = max(float(node.y) for node in source_oncurves)
			source_top_nodes = [
				node for node in source_oncurves
				if abs(float(node.y) - source_top) <= EPSILON
			]
			is_left = (
				sum(float(node.x) for node in source_top_nodes)
				/ len(source_top_nodes)
				< source_axis
			)
			target_outer = target_left if is_left else target_right
			path = source_path.copy()
			for _iteration in range(20):
				oncurves = _oncurve_nodes(path)
				if not oncurves:
					raise GenerationError("V contains an empty diagonal contour.")
				path_bottom = min(float(node.y) for node in oncurves)
				path_top = max(float(node.y) for node in oncurves)
				bottom_nodes = [
					node for node in oncurves
					if abs(float(node.y) - path_bottom) <= EPSILON
				]
				bottom_right = max(float(node.x) for node in bottom_nodes)
				path_left, _b, path_right, _t = _bounds_values(path)
				current_outer = path_left if is_left else path_right
				bottom_shift = bottom_target - bottom_right
				outer_shift = target_outer - current_outer
				path_height = max(EPSILON, path_top - path_bottom)
				for node in path.nodes:
					progress = max(
						0.0,
						min(
							1.0,
							(float(node.y) - path_bottom) / path_height,
						),
					)
					node.x = (
						float(node.x)
						+ bottom_shift * (1.0 - progress)
						+ outer_shift * progress
					)
				current_profile = _single_diagonal_profile(path)
				profile_error = max(
					abs(current - target)
					for current, target in zip(
						current_profile, target_profile
					)
				)
				updated_bottom_right = max(
					float(node.x) for node in bottom_nodes
				)
				updated_left, _b, updated_right, _t = _bounds_values(path)
				updated_outer = updated_left if is_left else updated_right
				if (
					profile_error <= W_STROKE_TOLERANCE
					and abs(updated_bottom_right - bottom_target) <= EPSILON
					and abs(updated_outer - target_outer) <= EPSILON
				):
					break
				factors = tuple(
					max(0.95, min(1.05, target / current))
					for current, target in zip(
						current_profile, target_profile
					)
				)
				_compensate_single_diagonal(path, factors)
			else:
				raise GenerationError(
					"M's perpendicular stroke compensation did not converge."
				)
			result_paths.append(path)

		bottom_nodes = []
		for path in result_paths:
			oncurves = _oncurve_nodes(path)
			path_bottom = min(float(node.y) for node in oncurves)
			bottom_nodes.extend(
				node for node in oncurves
				if abs(float(node.y) - path_bottom) <= EPSILON
			)
		bottom_center = (
			min(float(node.x) for node in bottom_nodes)
			+ max(float(node.x) for node in bottom_nodes)
		) * 0.5
		centering_error = float(axis) - bottom_center
		if abs(centering_error) <= EPSILON:
			return result_paths
		bottom_target += centering_error
	raise GenerationError("M's bottom nodes could not be centered.")


def _build_M_at_width(font, master, diagonal_width=None):
	"""Build M from H-weight stems around a compensated V-derived middle."""
	H_source = _source_layer(font, "H", master.id)
	V_source = _source_layer(font, "V", master.id)
	H_copy, left_stem, _right_stem, crossbar = _measure_H_source(
		H_source, master
	)
	H_left, _bottom, H_right, _top = _bounds_values(H_copy)
	cap_height = float(master.capHeight)
	horizontal_weight = float(crossbar[1]) - float(crossbar[0])
	vertical_weight = float(left_stem[1]) - float(left_stem[0])
	if min(horizontal_weight, vertical_weight) <= EPSILON:
		raise GenerationError("H has no usable stem weights for M.")

	# First place only the V-derived middle. The stems are positioned afterward
	# from the finished top-node landmarks, so contrast cannot pull a stem away
	# from its diagonal and no contour needs to be distorted or trimmed.
	axis = float(H_source.width) * 0.5
	target_width = (
		(H_right - H_left) * M_WIDTH_FACTOR
		if diagonal_width is None else float(diagonal_width)
	)
	target_left = axis - target_width * 0.5
	target_right = axis + target_width * 0.5
	diagonal_inset = (
		min(horizontal_weight, vertical_weight)
		* M_DIAGONAL_INSET_FACTOR
	)
	diagonals = _M_diagonal_paths(
		V_source,
		target_left + diagonal_inset,
		target_right - diagonal_inset,
		axis,
	)
	_align_V_diagonal_join(diagonals, axis)
	def top_nodes(path):
		oncurves = _oncurve_nodes(path)
		top = max(float(node.y) for node in oncurves)
		return [
			node for node in oncurves
			if abs(float(node.y) - top) <= EPSILON
		]

	diagonals_by_center = sorted(
		diagonals,
		key=lambda path: sum(float(node.x) for node in top_nodes(path))
		/ len(top_nodes(path)),
	)
	left_diagonal, right_diagonal = diagonals_by_center
	left_top = top_nodes(left_diagonal)
	right_top = top_nodes(right_diagonal)
	# Match the user's join landmarks by rigidly placing the complete rectangles:
	# the left diagonal's outer top node sits at the thin stem's centre, while
	# the heavy stem's inner edge sits at the right diagonal's top centre.
	left_stem_center = min(float(node.x) for node in left_top)
	right_stem_left = sum(float(node.x) for node in right_top) / len(right_top)
	left_path = _rectangle_path(
		left_stem_center - horizontal_weight * 0.5,
		0.0,
		left_stem_center + horizontal_weight * 0.5,
		cap_height,
	)
	right_path = _rectangle_path(
		right_stem_left,
		0.0,
		right_stem_left + vertical_weight,
		cap_height,
	)
	reference = diagonals[0]
	for path in diagonals[1:] + [left_path, right_path]:
		if _path_signed_area(path) * _path_signed_area(reference) < 0.0:
			path.reverse()
	paths = diagonals + [right_path, left_path]
	preliminary = _layer_from_paths(paths, 0)
	current_left, _bottom, _current_right, _top = _bounds_values(preliminary)
	_translate_paths(paths, H_left - current_left)
	final_right = _bounds_values(_layer_from_paths(paths, 0))[2]
	# Preserve H's left sidebearing on both sides, as in the adjusted reference.
	candidate = _layer_from_paths(paths, final_right + H_left)
	return candidate


def _build_M(font, master):
	"""Widen M's complete ink, not its stems or their compensated weights."""
	baseline = _build_M_at_width(font, master)
	left, _bottom, right, _top = _bounds_values(baseline)
	target = (right - left) * M_OUTLINE_WIDTH_GAIN
	H_source = _source_layer(font, "H", master.id)
	H_copy, _left_stem, _right_stem, _crossbar = _measure_H_source(H_source, master)
	H_left, _bottom, H_right, _top = _bounds_values(H_copy)
	diagonal_width = (H_right - H_left) * M_WIDTH_FACTOR + target - (right - left)
	for _iteration in range(8):
		candidate = _build_M_at_width(font, master, diagonal_width)
		left, _bottom, right, _top = _bounds_values(candidate)
		error = target - (right - left)
		if abs(error) <= 0.25:
			return candidate
		diagonal_width += error
	raise GenerationError("M's 8% widening did not converge.")


def _build_N(font, master):
	"""Build N from H with contrast-aware verticals and an H-vertical diagonal."""
	H_source = _source_layer(font, "H", master.id)
	H_copy, left_stem, right_stem, crossbar = _measure_H_source(
		H_source, master
	)
	H_left, _bottom, H_right, _top = _bounds_values(H_copy)
	cap_height = float(master.capHeight)
	left_vertical = float(left_stem[1]) - float(left_stem[0])
	right_vertical = float(right_stem[1]) - float(right_stem[0])
	horizontal = float(crossbar[1]) - float(crossbar[0])
	if min(left_vertical, right_vertical, horizontal) <= EPSILON:
		raise GenerationError("H has no usable stem weights for N.")

	contrast_ratio = horizontal / left_vertical
	if contrast_ratio >= U_SANS_CONTRAST_THRESHOLD:
		left_weight = left_vertical
		right_weight = right_vertical
	else:
		left_weight = horizontal
		right_weight = horizontal

	left_path = _rectangle_path(
		H_left, 0.0, H_left + left_weight, cap_height
	)
	right_path = _rectangle_path(
		H_right - right_weight, 0.0, H_right, cap_height
	)
	# Build the descending diagonal from H's canonical vertical weight. The helper
	# solves its horizontal cap width from the centerline angle, so the actual
	# thickness—not its canvas width—matches H in both contrast regimes.
	diagonal = _diagonal_strip_path(
		H_left,
		H_right,
		0.0,
		cap_height,
		left_vertical,
		False,
	)
	for path in (right_path, diagonal):
		if _path_signed_area(path) * _path_signed_area(left_path) < 0.0:
			path.reverse()
	return _finish_candidate(
		_layer_from_paths(
			[left_path, diagonal, right_path], float(H_source.width)
		),
		remove_overlap=False,
	)


def _build_Z(font, master):
	"""90%-H-wide Z with H bars and an H-vertical normal-weight diagonal."""
	H_source = _source_layer(font, "H", master.id)
	H_copy, left_stem, _right_stem, crossbar = _measure_H_source(H_source, master)
	left, _bottom, right, _top = _bounds_values(H_copy)
	right = left + (right - left) * 0.90
	cap_height = float(master.capHeight)
	bar_height = float(crossbar[1]) - float(crossbar[0])
	diagonal_weight = float(left_stem[1]) - float(left_stem[0])
	span = right - left
	lower_join, upper_join = bar_height, cap_height - bar_height
	join_height = upper_join - lower_join
	if min(join_height, diagonal_weight, bar_height) <= EPSILON:
		raise GenerationError("H's crossbar leaves no room for Z's diagonal.")
	if diagonal_weight >= span - EPSILON:
		raise GenerationError("H's vertical stem is too wide for Z's outline.")
	# The diagonal's horizontal cap width and centerline angle depend on each
	# other. Solve t = cap / sqrt(1 + ((span - cap) / join_height)^2), so its
	# true perpendicular weight matches H rather than its canvas width.
	low, high = diagonal_weight, span
	for _iteration in range(50):
		cap = (low + high) * 0.5
		slope = (span - cap) / join_height
		measured = cap / (1.0 + slope * slope) ** 0.5
		if measured < diagonal_weight:
			low = cap
		else:
			high = cap
	cap = (low + high) * 0.5
	path = GSPath()
	path.closed = True
	# One ten-node contour keeps the joins exact, with no Boolean remnants or
	# overlapping strip that could accidentally acquire a counter direction.
	for point in (
		(left, cap_height), (right, cap_height), (right, upper_join),
		(left + cap, lower_join), (right, lower_join), (right, 0.0),
		(left, 0.0), (left, lower_join), (right - cap, upper_join),
		(left, upper_join),
	):
		path.nodes.append(_new_node(point, LINE, False))
	return _finish_candidate(
		_layer_from_paths([path], H_source.width), remove_overlap=False
	)


def _X_diagonal_path(layer, ascending):
	"""Find one X diagonal by its centerline direction, independent of topology."""
	candidates = []
	for path in _copy_decomposed(layer).paths:
		if not path.closed:
			continue
		oncurves = _oncurve_nodes(path)
		if not oncurves:
			continue
		bottom = min(float(node.y) for node in oncurves)
		top = max(float(node.y) for node in oncurves)
		if top - bottom <= EPSILON:
			continue
		bottom_nodes = [
			node for node in oncurves
			if abs(float(node.y) - bottom) <= EPSILON
		]
		top_nodes = [
			node for node in oncurves
			if abs(float(node.y) - top) <= EPSILON
		]
		bottom_center = sum(
			float(node.x) for node in bottom_nodes
		) / len(bottom_nodes)
		top_center = sum(
			float(node.x) for node in top_nodes
		) / len(top_nodes)
		is_ascending = top_center > bottom_center + EPSILON
		if is_ascending == bool(ascending):
			candidates.append((top - bottom, abs(top_center - bottom_center), path))
	if not candidates:
		direction = "ascending" if ascending else "descending"
		raise GenerationError("X has no identifiable %s diagonal." % direction)
	return max(candidates, key=lambda item: (item[0], item[1]))[2].copy()


def _remap_compensated_diagonal(
	source_path, top_center, top_y, bottom_center, bottom_y,
):
	"""Remap a diagonal and restore its complete perpendicular weight profile."""
	target_profile = _single_diagonal_profile(source_path)
	path = _remap_diagonal_centerline(
		source_path, top_center, top_y, bottom_center, bottom_y
	)
	for _iteration in range(8):
		current_profile = _single_diagonal_profile(path)
		error = max(
			abs(current - target)
			for current, target in zip(current_profile, target_profile)
		)
		if error <= W_STROKE_TOLERANCE:
			return path
		factors = tuple(
			max(0.95, min(1.05, target / current))
			for current, target in zip(current_profile, target_profile)
		)
		_compensate_single_diagonal(path, factors)
	raise GenerationError("K's perpendicular stroke compensation did not converge.")


def _align_diagonal_right_endpoint(
	source_path, top_center, top_y, bottom_center, bottom_y,
	endpoint, target_right,
):
	"""Align one horizontal diagonal ending without editing its source contour."""
	top_center = float(top_center)
	bottom_center = float(bottom_center)
	for _iteration in range(20):
		path = _remap_compensated_diagonal(
			source_path,
			top_center,
			float(top_y),
			bottom_center,
			float(bottom_y),
		)
		oncurves = _oncurve_nodes(path)
		if endpoint == "top":
			end_y = max(float(node.y) for node in oncurves)
		else:
			end_y = min(float(node.y) for node in oncurves)
		end_nodes = [
			node for node in oncurves
			if abs(float(node.y) - end_y) <= EPSILON
		]
		current_right = max(float(node.x) for node in end_nodes)
		error = float(target_right) - current_right
		if abs(error) <= 0.0001:
			return path
		if endpoint == "top":
			top_center += error
		else:
			bottom_center += error
	raise GenerationError("K's diagonal ending could not be aligned.")


def _build_K(font, master):
	"""Build K as three clean H/X-derived contours without Boolean nodes."""
	H_source = _source_layer(font, "H", master.id)
	X_source = _source_layer(font, "X", master.id)
	H_copy, left_stem, right_stem, crossbar = _measure_H_source(
		H_source, master
	)
	H_left, _H_bottom, H_right, _H_top = _bounds_values(H_copy)
	cap_height = float(master.capHeight)
	# Glyph coordinates are positive here; use half-up rounding so a half-unit
	# H-stem centre lands on the same integer side as the drawn reference.
	stem_center = int((left_stem[0] + left_stem[1]) * 0.5 + 0.5)
	junction_y = (crossbar[0] + crossbar[1]) * 0.5
	ascending = _X_diagonal_path(X_source, True)
	descending = _X_diagonal_path(X_source, False)
	arm_profile = _single_diagonal_profile(ascending)
	leg_profile = _single_diagonal_profile(descending)
	arm_weight = sum(arm_profile) / len(arm_profile)
	leg_weight = sum(leg_profile) / len(leg_profile)
	H_ink_width = H_right - H_left
	K_right = round(H_left + H_ink_width * K_INK_WIDTH_FACTOR)
	overhang = K_right - H_right

	# Use the old H-width arm only as a direction guide for the leg's diagonal
	# terminal. It is never installed and therefore cannot contribute nodes.
	arm_guide = _align_diagonal_right_endpoint(
		ascending,
		H_right,
		cap_height,
		stem_center,
		junction_y,
		"top",
		H_right,
	)
	guide_oncurves = _oncurve_nodes(arm_guide)
	guide_bottom = min(float(node.y) for node in guide_oncurves)
	guide_top = max(float(node.y) for node in guide_oncurves)
	guide_bottom_nodes = [
		node for node in guide_oncurves
		if abs(float(node.y) - guide_bottom) <= EPSILON
	]
	guide_top_nodes = [
		node for node in guide_oncurves
		if abs(float(node.y) - guide_top) <= EPSILON
	]
	guide_bottom_center = sum(
		float(node.x) for node in guide_bottom_nodes
	) / len(guide_bottom_nodes)
	guide_top_center = sum(
		float(node.x) for node in guide_top_nodes
	) / len(guide_top_nodes)
	guide_slope = (
		(guide_top_center - guide_bottom_center)
		/ (guide_top - guide_bottom)
	)

	# Construct the arm directly as one four-node parallelogram. Its stem-side
	# edge is vertical, and even its upper node ends below H's optical middle.
	arm_inner_y = round(
		junction_y - arm_weight * K_ARM_MIDDLE_CLEARANCE_FACTOR
	)
	arm_run = K_right - stem_center

	def arm_equation(slope):
		return (
			slope * (cap_height - arm_inner_y)
			+ arm_weight * (1.0 + slope * slope) ** 0.5
			- arm_run
		)

	low, high = 0.001, 10.0
	if arm_equation(low) >= 0.0 or arm_equation(high) <= 0.0:
		raise GenerationError("K's arm angle could not be solved.")
	for _iteration in range(60):
		middle = (low + high) * 0.5
		if arm_equation(middle) < 0.0:
			low = middle
		else:
			high = middle
	arm_slope = (low + high) * 0.5
	arm_cap_width = arm_weight * (1.0 + arm_slope * arm_slope) ** 0.5
	arm_stem_height = arm_cap_width / arm_slope
	# Quantise the terminal depth before subtracting it. This keeps the vertical
	# stem-side ending clean instead of allowing two independent rounded points
	# to change its depth by a unit.
	arm_outer_y = arm_inner_y - int(arm_stem_height)
	arm = GSPath()
	arm.closed = True
	for point in (
		(stem_center, arm_outer_y),
		(K_right, cap_height),
		(round(K_right - arm_cap_width), cap_height),
		(stem_center, arm_inner_y),
	):
		arm.nodes.append(_new_node(point, LINE))

	# The leg is another direct four-node contour. Its left terminal begins just
	# beyond the stem and the opposite terminal follows the X-remapped arm guide,
	# so the leg enters the arm without reaching the stem or adding cut nodes.
	leg_inner_x = round(left_stem[1] + overhang + 1.0)
	leg_inner_y = round(
		junction_y + arm_weight * K_LEG_JOINT_RISE_FACTOR
	)

	def leg_equation(slope):
		return (
			K_right
			- leg_weight * (1.0 + slope * slope) ** 0.5
			+ slope * leg_inner_y
			- leg_inner_x
		)

	low, high = -10.0, -0.001
	if leg_equation(low) >= 0.0 or leg_equation(high) <= 0.0:
		raise GenerationError("K's leg angle could not be solved.")
	for _iteration in range(60):
		middle = (low + high) * 0.5
		if leg_equation(middle) < 0.0:
			low = middle
		else:
			high = middle
	leg_slope = (low + high) * 0.5
	leg_cap_width = leg_weight * (1.0 + leg_slope * leg_slope) ** 0.5
	denominator = guide_slope - leg_slope
	if denominator <= EPSILON:
		raise GenerationError("K's leg cannot intersect its arm terminal.")
	leg_outer_y = (
		K_right - leg_inner_x + guide_slope * leg_inner_y
	) / denominator
	leg_outer_x = K_right + leg_slope * leg_outer_y
	leg = GSPath()
	leg.closed = True
	for point in (
		(round(K_right - leg_cap_width), 0.0),
		(K_right, 0.0),
		(round(leg_outer_x), round(leg_outer_y)),
		(leg_inner_x, leg_inner_y),
	):
		leg.nodes.append(_new_node(point, LINE))

	# The old H-width guide can differ slightly from the actual arm, especially
	# with contrasting X strokes. Extend the intact leg along its own centreline
	# until its terminal is buried in the actual arm. This retains its angle and
	# perpendicular weight, its baseline ending, and the four-node construction.
	terminal_nodes = list(leg.nodes)[-2:]
	arm_points = [_point(node) for node in arm.nodes]
	orientation = 1.0 if _path_signed_area(arm) > 0 else -1.0
	extension_min, extension_max = 0.0, float("inf")
	for node in terminal_nodes:
		for a, b in zip(arm_points, arm_points[1:] + arm_points[:1]):
			edge = (b[0] - a[0], b[1] - a[1])
			clearance = (edge[0] ** 2 + edge[1] ** 2) ** 0.5
			current = orientation * _cross(edge, (float(node.x) - a[0], float(node.y) - a[1]))
			change = orientation * _cross(edge, (leg_slope, 1.0))
			if change > EPSILON:
				extension_min = max(extension_min, (clearance - current) / change)
			elif change < -EPSILON:
				extension_max = min(extension_max, (clearance - current) / change)
			elif current < clearance:
				raise GenerationError("K's leg cannot meet the arm at this stroke weight.")
	if extension_min > extension_max:
		raise GenerationError("K's arm has no room for the leg joint at this stroke weight.")
	if extension_min > 0.0:
		for node in terminal_nodes:
			node.x = round(float(node.x) + leg_slope * extension_min)
			node.y = round(float(node.y) + extension_min)

	# Confirm containment against the final quantised arm, not the direction guide.
	arm_layer = _layer_from_paths([arm], 0)
	for node in list(leg.nodes)[-2:]:
		intersections = _scan_x_intersections(arm_layer, float(node.y))
		if (
			len(intersections) < 2
			or float(node.x) < intersections[0] - EPSILON
			or float(node.x) > intersections[-1] + EPSILON
		):
			raise GenerationError("K's leg terminal does not fit inside its arm.")

	stem_paths = _H_left_stem_paths(
		H_copy, left_stem, right_stem, crossbar
	)
	if len(stem_paths) != 1:
		raise GenerationError("H's left stem must resolve to one clean K contour.")
	stem_layer = _layer_from_paths([stem_paths[0].copy()], 0)
	_remove_redundant_line_nodes(stem_layer)
	reference = stem_layer.paths[0]
	for path in (arm, leg):
		if _path_signed_area(path) * _path_signed_area(reference) < 0.0:
			path.reverse()
	candidate = GSLayer()
	candidate.shapes.append(reference.copy())
	candidate.shapes.append(arm)
	candidate.shapes.append(leg)
	# K keeps H's advance but allows the conventional slight diagonal overhang.
	candidate.width = float(H_source.width)
	return candidate


def _diagonal_stroke_centers(layer, source_name):
	"""Measure the left and right strokes near a V-shaped source's top."""
	_left, bottom, _right, top = _bounds_values(layer)
	height = top - bottom
	if height <= EPSILON:
		raise GenerationError("%s has no measurable height." % source_name)
	scan_y = top - max(1.0, height * 0.05)
	intersections = _scan_x_intersections(layer, scan_y)
	if len(intersections) < 4:
		raise GenerationError(
			"Could not identify both diagonal strokes in %s." % source_name
		)
	return (
		(intersections[0] + intersections[1]) * 0.5,
		(intersections[-2] + intersections[-1]) * 0.5,
	)


def _v_split_y(layer):
	"""Locate the height where a joined V first separates into two strokes."""
	_left, bottom, _right, top = _bounds_values(layer)
	height = top - bottom
	if height <= EPSILON:
		raise GenerationError("The V source has no measurable height.")
	previous_y = bottom
	for step in range(1, 81):
		probe_y = bottom + height * step / 81.0
		if len(_scan_x_intersections(layer, probe_y)) >= 4:
			low, high = previous_y, probe_y
			for _refinement in range(24):
				middle = (low + high) * 0.5
				if len(_scan_x_intersections(layer, middle)) >= 4:
					high = middle
				else:
					low = middle
			return high
		previous_y = probe_y
	return bottom


def _condense_v_preserving_stems(layer, source_width, factor=0.85):
	"""Narrow a V without horizontally scaling its diagonal strokes.

	Each half receives a progressive x translation: zero at the bottom join and
	the full condensation at the top. Points across either diagonal at the same
	height move by the same amount, so the source stem thickness is retained.
	"""
	left, bottom, right, top = _bounds_values(layer)
	height = top - bottom
	outline_width = right - left
	if height <= EPSILON or outline_width <= EPSILON:
		raise GenerationError("The V source has no measurable outline.")
	reference = layer.copy()
	maximum_shift = outline_width * (1.0 - float(factor)) * 0.5
	# Locate the height where the joined bottom first separates into two
	# diagonal stems. Keeping that junction fixed avoids distorting notches or
	# other custom construction details around the point of the V.
	split_y = _v_split_y(reference)
	active_height = max(EPSILON, top - split_y)
	for path in layer.paths:
		for node in path.nodes:
			node_y = float(node.y)
			# Extrapolate the same shear below the split. This keeps both edges
			# of each diagonal under one affine transform, preserving its width.
			vertical_factor = min(1.0, (node_y - split_y) / active_height)
			probe_y = min(top - 0.01, max(split_y + 0.01, node_y))
			intersections = _scan_x_intersections(reference, probe_y)
			if len(intersections) >= 4:
				divider = (intersections[1] + intersections[2]) * 0.5
			else:
				divider = (left + right) * 0.5
			if float(node.x) < divider - EPSILON:
				node.x = float(node.x) + maximum_shift * vertical_factor
			elif float(node.x) > divider + EPSILON:
				node.x = float(node.x) - maximum_shift * vertical_factor

	# Give the condensed copy proportionally scaled sidebearings without
	# subjecting any outline point to a second geometric scale.
	new_left, _bottom, _right, _top = _bounds_values(layer)
	_translate_paths(layer.paths, left * float(factor) - new_left)
	layer.width = round(float(source_width) * float(factor))
	return split_y


def _diagonal_stem_measurements(layer, split_y):
	"""Return perpendicular mid-stem widths for V's two diagonals."""
	closed_paths = [path for path in layer.paths if path.closed]
	if len(closed_paths) == 2:
		ordered = sorted(
			closed_paths,
			key=lambda path: _diagonal_center_at_y(
				path, _bounds_values(path)[3]
			),
		)
		return tuple(
			sum(_single_diagonal_profile(path))
			/ len(V_PROFILE_POSITIONS)
			for path in ordered
		)
	_left, bottom, _right, top = _bounds_values(layer)
	active_height = top - float(split_y)
	if active_height <= EPSILON:
		raise GenerationError("Could not measure V's diagonal stems.")
	y1 = float(split_y) + active_height * 0.30
	y2 = float(split_y) + active_height * 0.70
	y_mid = (y1 + y2) * 0.5
	first = _scan_x_intersections(layer, y1)
	second = _scan_x_intersections(layer, y2)
	middle = _scan_x_intersections(layer, y_mid)
	if min(len(first), len(second), len(middle)) < 4:
		raise GenerationError("Could not measure both V diagonals at mid-stem.")
	measurements = []
	for left_index, right_index in ((0, 1), (-2, -1)):
		center_1 = (first[left_index] + first[right_index]) * 0.5
		center_2 = (second[left_index] + second[right_index]) * 0.5
		slope = (center_2 - center_1) / (y2 - y1)
		horizontal_width = middle[right_index] - middle[left_index]
		perpendicular_width = horizontal_width / (1.0 + slope * slope) ** 0.5
		measurements.append(perpendicular_width)
	return tuple(measurements)


def _diagonal_stroke_profile(layer, split_y, positions=V_PROFILE_POSITIONS):
	"""Measure both V diagonals at matching semantic positions.

	Multiple local measurements preserve deliberate contrast and taper instead
	of flattening the source into one representative mid-stem value.
	"""
	_left, _bottom, _right, top = _bounds_values(layer)
	active_height = top - float(split_y)
	if active_height <= EPSILON:
		raise GenerationError("Could not measure V's diagonal stroke profile.")
	delta = max(0.5, active_height * 0.015)
	profile = []
	for progress in positions:
		y = float(split_y) + active_height * float(progress)
		before_y = max(float(split_y) + 0.01, y - delta)
		after_y = min(top - 0.01, y + delta)
		before = _scan_x_intersections(layer, before_y)
		middle = _scan_x_intersections(layer, y)
		after = _scan_x_intersections(layer, after_y)
		if min(len(before), len(middle), len(after)) < 4:
			raise GenerationError(
				"Could not measure both V diagonals at %.0f%% of their length."
				% (float(progress) * 100.0)
			)
		measurements = []
		for left_index, right_index in ((0, 1), (-2, -1)):
			center_before = (
				before[left_index] + before[right_index]
			) * 0.5
			center_after = (
				after[left_index] + after[right_index]
			) * 0.5
			slope = (center_after - center_before) / (after_y - before_y)
			horizontal_width = middle[right_index] - middle[left_index]
			measurements.append(
				horizontal_width / (1.0 + slope * slope) ** 0.5
			)
		profile.append(tuple(measurements))
	return tuple(profile)


def _interpolate_profile_value(progress, positions, values):
	progress = float(progress)
	if progress <= float(positions[0]):
		return float(values[0])
	if progress >= float(positions[-1]):
		return float(values[-1])
	for index in range(len(positions) - 1):
		start = float(positions[index])
		end = float(positions[index + 1])
		if progress <= end:
			factor = (progress - start) / max(EPSILON, end - start)
			return float(values[index]) + (
				float(values[index + 1]) - float(values[index])
			) * factor
	return float(values[-1])


def _thin_v_diagonals(layer, split_y, factors):
	"""Compensate each complete V diagonal around its local centerline.

	The correction must continue through the lower join.  Fading it out at the
	crotch preserves the mid-stem measurement but creates an artificial taper,
	because the scaled lower edges stay lighter than the rest of the stroke.
	"""
	_left, _bottom, _right, top = _bounds_values(layer)
	moves = []
	for path in layer.paths:
		for node in path.nodes:
			probe_y = min(
				top - 0.01,
				max(float(split_y) + 0.01, float(node.y)),
			)
			intersections = _scan_x_intersections(layer, probe_y)
			if len(intersections) < 4:
				continue
			divider = (intersections[1] + intersections[-2]) * 0.5
			# A single shared inner-crotch node belongs to both diagonals. Keep it
			# centered while the two outer join edges receive the compensation.
			if abs(float(node.x) - divider) <= EPSILON:
				continue
			if float(node.x) < divider:
				center = (intersections[0] + intersections[1]) * 0.5
				factor = factors[0]
				# Below the split, the inner edge is already the faithfully scaled
				# crotch construction (and may cross the opposite inner edge). Do not
				# collapse that detail while compensating the exposed outer edge.
				if (
					float(node.y) <= float(split_y) + EPSILON
					and float(node.x) >= center
				):
					continue
			else:
				center = (intersections[-2] + intersections[-1]) * 0.5
				factor = factors[1]
				if (
					float(node.y) <= float(split_y) + EPSILON
					and float(node.x) <= center
				):
					continue
			moves.append((node, center + (float(node.x) - center) * factor))
	for node, new_x in moves:
		node.x = new_x


def _compensate_v_diagonals_outward(
	layer, split_y, positions, factor_profile
):
	"""Change V stroke weight while anchoring its inner edges and crotch.

	Moving both boundaries symmetrically is mathematically tidy but pushes the
	inner edges together when a lowercase v approaches uppercase stem weight.
	Here the complete correction is assigned to each exposed outer boundary;
	the faithfully scaled counter and crotch therefore remain unchanged.
	"""
	_left, bottom, _right, top = _bounds_values(layer)
	active_height = max(EPSILON, top - float(split_y))
	probe_floor = float(split_y) + max(0.5, active_height * 0.01)
	reference = layer.copy()
	moves = []
	for path in layer.paths:
		for node in path.nodes:
			at_bottom_join = abs(float(node.y) - bottom) <= EPSILON
			progress = (
				(float(node.y) - float(split_y)) / active_height
			)
			probe_y = min(
				top - 0.01,
				max(probe_floor, float(node.y)),
			)
			intersections = _scan_x_intersections(reference, probe_y)
			if len(intersections) < 4:
				continue
			divider = (intersections[1] + intersections[-2]) * 0.5
			if abs(float(node.x) - divider) <= EPSILON:
				continue
			if float(node.x) < divider:
				center = (intersections[0] + intersections[1]) * 0.5
				if float(node.x) >= center and not at_bottom_join:
					continue
				factor = _interpolate_profile_value(
					progress,
					positions,
					[values[0] for values in factor_profile],
				)
			else:
				center = (intersections[-2] + intersections[-1]) * 0.5
				if float(node.x) <= center and not at_bottom_join:
					continue
				factor = _interpolate_profile_value(
					progress,
					positions,
					[values[1] for values in factor_profile],
				)
			# One moving boundary must provide the width change that two boundaries
			# would normally share: q on total width becomes (2q - 1) from center.
			outer_factor = max(0.25, 2.0 * float(factor) - 1.0)
			anchor = divider if at_bottom_join else center
			moves.append((
				node,
				anchor + (float(node.x) - anchor) * outer_factor,
			))
	for node, new_x in moves:
		node.x = new_x


def _top_diagonal_stroke_centers(layer, source_name):
	"""Measure V's two top stroke centers from its actual top nodes."""
	oncurves = [
		node for path in layer.paths for node in _oncurve_nodes(path)
	]
	top = max(float(node.y) for node in oncurves)
	top_x = sorted(
		float(node.x) for node in oncurves
		if abs(float(node.y) - top) <= 0.5
	)
	if len(top_x) < 4:
		return _diagonal_stroke_centers(layer, source_name)
	return (
		(top_x[0] + top_x[1]) * 0.5,
		(top_x[-2] + top_x[-1]) * 0.5,
	)


def _top_diagonal_node_pairs(layer, source_name):
	"""Return the two top-node pairs that define V's diagonal strokes."""
	oncurves = [
		node for path in layer.paths for node in _oncurve_nodes(path)
	]
	top = max(float(node.y) for node in oncurves)
	top_nodes = sorted(
		(
			node for node in oncurves
			if abs(float(node.y) - top) <= 0.5
		),
		key=lambda node: float(node.x),
	)
	if len(top_nodes) < 4:
		raise GenerationError(
			"%s needs two top nodes on each diagonal to build aligned W joins."
			% source_name
		)
	return tuple(top_nodes[:2]), tuple(top_nodes[-2:])


def _build_A(font, master):
	V_source = _source_layer(font, "V", master.id)
	H_source = _source_layer(font, "H", master.id)
	legs = _copy_decomposed(V_source)
	_align_V_diagonal_join(legs.paths)
	cap_height = float(master.capHeight)
	for path in legs.paths:
		for node in path.nodes:
			node.x = float(V_source.width) - float(node.x)
			node.y = cap_height - float(node.y)
	legs.correctPathDirection()

	_H_copy, _left_stem, _right_stem, crossbar = _measure_H_source(
		H_source, master
	)
	bar_height = crossbar[1] - crossbar[0]
	bar_center_y = float(master.capHeight) * 0.30
	bar_bottom = bar_center_y - bar_height * 0.5
	bar_top = bar_center_y + bar_height * 0.5
	intersections = _scan_x_intersections(legs, bar_center_y)
	if len(intersections) < 4:
		raise GenerationError(
			"Could not identify both A legs at H's crossbar height."
		)
	left_stroke_center = (intersections[0] + intersections[1]) * 0.5
	right_stroke_center = (intersections[-2] + intersections[-1]) * 0.5
	bar = _rectangle_path(
		left_stroke_center, bar_bottom, right_stroke_center, bar_top
	)
	legs.shapes.append(bar)
	legs.width = V_source.width
	return _finish_candidate(legs, remove_overlap=False)


def _build_v(font, master):
	"""Scale V to lowercase metrics while retaining perpendicular stem weight."""
	source = _source_layer(font, "V", master.id)
	source_copy = _copy_decomposed(source)
	source_left, source_bottom, source_right, source_top = _bounds_values(
		source_copy
	)
	source_outline_width = source_right - source_left
	source_outline_height = source_top - source_bottom
	cap_height = float(master.capHeight)
	x_height = float(master.xHeight)
	if min(source_outline_width, source_outline_height, cap_height, x_height) <= EPSILON:
		raise GenerationError("V needs measurable bounds and positive master metrics.")
	proportion_scale = x_height / cap_height
	width_scale = proportion_scale * LOWERCASE_V_WIDTH_FACTOR
	target_bounds = (
		source_left * width_scale,
		0.0,
		source_right * width_scale,
		x_height,
	)
	source_center = (
		(source_left + source_right) * 0.5,
		(source_bottom + source_top) * 0.5,
	)
	target_center = (
		(target_bounds[0] + target_bounds[2]) * 0.5,
		(target_bounds[1] + target_bounds[3]) * 0.5,
	)
	target_outline_width = target_bounds[2] - target_bounds[0]
	target_outline_height = target_bounds[3] - target_bounds[1]
	working_x = target_outline_width / source_outline_width
	working_y = target_outline_height / source_outline_height
	tolerance = W_STROKE_TOLERANCE
	if len(source_copy.paths) == 2:
		candidate = _copy_decomposed(source)
		_transform_paths_affinely(
			candidate.paths,
			source_center,
			target_center,
			working_x,
			working_y,
		)
		for source_path, candidate_path in zip(
			source_copy.paths, candidate.paths
		):
			target_profile = tuple(
				width * LOWERCASE_V_STROKE_FACTOR
				for width in _single_diagonal_profile(source_path)
			)
			for _weight_iteration in range(60):
				current_profile = _single_diagonal_profile(candidate_path)
				if max(
					abs(current - target)
					for current, target in zip(
						current_profile, target_profile
					)
				) <= tolerance:
					break
				factors = tuple(
					max(0.95, min(1.05, target / current))
					for current, target in zip(
						current_profile, target_profile
					)
				)
				_compensate_single_diagonal(candidate_path, factors)
			else:
				raise GenerationError(
					"v's separate diagonal compensation did not converge."
				)
		_align_V_diagonal_join(candidate.paths, target_center[0])
		current_left, current_bottom, current_right, _current_top = (
			_bounds_values(candidate)
		)
		_translate_paths(
			candidate.paths,
			target_bounds[0] - current_left,
			target_bounds[1] - current_bottom,
		)
		right_sidebearing = (
			float(source.width) - source_right
		) * width_scale
		candidate.width = round(
			target_bounds[0]
			+ (current_right - current_left)
			+ right_sidebearing
		)
		return _correct_X_diagonal_directions(candidate)

	source_split_y = _v_split_y(source_copy)
	source_profile = _diagonal_stroke_profile(
		source_copy, source_split_y
	)
	target_profile = tuple(
		tuple(width * LOWERCASE_V_STROKE_FACTOR for width in sample)
		for sample in source_profile
	)
	candidate = _copy_decomposed(source)
	_transform_paths_affinely(
		candidate.paths,
		source_center,
		target_center,
		working_x,
		working_y,
	)
	target_split_y = (
		target_center[1]
		+ (source_split_y - source_center[1]) * working_y
	)
	for _weight_iteration in range(60):
		current_profile = _diagonal_stroke_profile(
			candidate, target_split_y
		)
		if max(
			abs(current - target)
			for current_sample, target_sample in zip(
				current_profile, target_profile
			)
			for current, target in zip(current_sample, target_sample)
		) <= tolerance:
			break
		factor_profile = tuple(
			tuple(
				max(0.95, min(1.05, target / current))
				for current, target in zip(current_sample, target_sample)
			)
			for current_sample, target_sample in zip(
				current_profile, target_profile
			)
		)
		_compensate_v_diagonals_outward(
			candidate,
			target_split_y,
			V_PROFILE_POSITIONS,
			factor_profile,
		)
	else:
		raise GenerationError(
			"v's outward diagonal-stroke compensation did not converge "
			"(%s target, %s measured)."
			% (
				", ".join(
					"%.2f" % value
					for sample in target_profile for value in sample
				),
				", ".join(
					"%.2f" % value
					for sample in current_profile for value in sample
				),
			)
		)
	current_left, current_bottom, current_right, current_top = (
		_bounds_values(candidate)
	)

	_translate_paths(
		candidate.paths,
		target_bounds[0] - current_left,
		target_bounds[1] - current_bottom,
	)
	# Preserve scaled source sidebearings while allowing the added weight to
	# increase the ink width. Forcing the heavier outline back to the earlier
	# width is exactly what caused the pinched crotch.
	right_sidebearing = (float(source.width) - source_right) * width_scale
	candidate.width = round(
		target_bounds[0]
		+ (current_right - current_left)
		+ right_sidebearing
	)
	candidate.correctPathDirection()
	candidate.roundCoordinates()
	candidate.correctPathDirection()
	rounded_split_y = target_split_y + target_bounds[1] - current_bottom
	rounded_profile = _diagonal_stroke_profile(candidate, rounded_split_y)
	# Integer-grid rounding can move opposite edges by one unit. Keep that
	# bounded grid effect distinct from the continuous compensation tolerance.
	rounded_tolerance = max(
		1.0,
		max(width for sample in target_profile for width in sample) * 0.001,
	)
	if max(
		abs(current - target)
		for current_sample, target_sample in zip(
			rounded_profile, target_profile
		)
		for current, target in zip(current_sample, target_sample)
	) > rounded_tolerance:
		raise GenerationError(
			"v's perpendicular stroke weight changed after rounding "
			"(%s target, %s measured)."
			% (
				", ".join(
					"%.2f" % value
					for sample in target_profile for value in sample
				),
				", ".join(
					"%.2f" % value
					for sample in rounded_profile for value in sample
				),
			)
		)
	return candidate


def _build_x(font, master):
	"""Scale X to lowercase metrics and retain 98% diagonal weights."""
	source = _source_layer(font, "X", master.id)
	source_copy = _copy_decomposed(source)
	paths = tuple(path for path in source_copy.paths if path.closed)
	if len(paths) != 2 or len(paths) != len(source_copy.paths):
		raise GenerationError(
			"X must contain two separate closed diagonal contours to build x."
		)
	source_left, source_bottom, source_right, source_top = _bounds_values(
		source_copy
	)
	source_width = source_right - source_left
	source_height = source_top - source_bottom
	cap_height = float(master.capHeight)
	x_height = float(master.xHeight)
	if min(source_width, source_height, cap_height, x_height) <= EPSILON:
		raise GenerationError("X needs measurable bounds and positive master metrics.")
	proportion_scale = x_height / cap_height
	width_scale = proportion_scale * LOWERCASE_X_WIDTH_FACTOR
	target_left = source_left * width_scale
	target_width = source_width * width_scale
	source_center = (
		(source_left + source_right) * 0.5,
		(source_bottom + source_top) * 0.5,
	)
	target_center = (
		target_left + target_width * 0.5,
		x_height * 0.5,
	)
	working_width = target_width
	for _width_iteration in range(10):
		candidate = _copy_decomposed(source)
		_transform_paths_affinely(
			candidate.paths,
			source_center,
			target_center,
			working_width / source_width,
			x_height / source_height,
		)
		for source_path, candidate_path in zip(
			source_copy.paths, candidate.paths
		):
			target_profile = tuple(
				width * LOWERCASE_X_STROKE_FACTOR
				for width in _single_diagonal_profile(source_path)
			)
			for _weight_iteration in range(60):
				current_profile = _single_diagonal_profile(candidate_path)
				if max(
					abs(current - target)
					for current, target in zip(
						current_profile, target_profile
					)
				) <= W_STROKE_TOLERANCE:
					break
				factors = tuple(
					max(0.95, min(1.05, target / current))
					for current, target in zip(
						current_profile, target_profile
					)
				)
				_compensate_single_diagonal(candidate_path, factors)
			else:
				raise GenerationError(
					"x's perpendicular stroke compensation did not converge."
				)
		current_left, current_bottom, current_right, _current_top = (
			_bounds_values(candidate)
		)
		current_width = current_right - current_left
		width_error = target_width - current_width
		if abs(width_error) <= EPSILON:
			break
		working_width += width_error
	else:
		raise GenerationError("x's final outline width did not converge.")
	_translate_paths(
		candidate.paths,
		target_left - current_left,
		-current_bottom,
	)
	right_sidebearing = (float(source.width) - source_right) * width_scale
	candidate.width = round(
		target_left + target_width + right_sidebearing
	)
	return _correct_X_diagonal_directions(candidate)


def _condense_separate_V_profiles(layer, source, factor):
	"""Shear each whole diagonal, then restore its matched local-normal profile."""
	left, bottom, right, top = _bounds_values(source)
	maximum_shift = (right - left) * (1.0 - float(factor)) * 0.5
	for source_path, path in zip(source.paths, layer.paths):
		nodes = _oncurve_nodes(source_path)
		top_nodes = [node for node in nodes if abs(float(node.y) - top) <= EPSILON]
		bottom_nodes = [node for node in nodes if abs(float(node.y) - bottom) <= EPSILON]
		if not top_nodes or not bottom_nodes:
			raise GenerationError("W needs full-height diagonals to preserve its stroke profile.")
		top_center = sum(float(node.x) for node in top_nodes) / len(top_nodes)
		bottom_center = sum(float(node.x) for node in bottom_nodes) / len(bottom_nodes)
		direction = 1.0 if top_center < bottom_center else -1.0
		for node in path.nodes:
			node.x = float(node.x) + direction * maximum_shift * (float(node.y) - bottom) / (top - bottom)
		target_profile = _single_diagonal_profile(source_path)
		for _iteration in range(12):
			profile = _single_diagonal_profile(path)
			if max(abs(current - target) for current, target in zip(profile, target_profile)) <= 0.1:
				break
			_compensate_single_diagonal(path, tuple(
				max(0.95, min(1.05, target / current))
				for current, target in zip(profile, target_profile)
			))
		else:
			raise GenerationError("W's local diagonal-stroke compensation did not converge.")
	return bottom


def _build_double_v_at_factor(font, master, character, factor=0.85, preserve_profile=False):
	source_name = "V" if character == "W" else "v"
	source = _source_layer(font, source_name, master.id)
	first = _copy_decomposed(source)
	second = _copy_decomposed(source)
	# Preserve every source contour and stem weight. Only the placement of each
	# diagonal half changes. Re-measure the new angles before assembling W.
	separate_profiles = preserve_profile and len(first.paths) == 2
	if separate_profiles:
		split_y = _condense_separate_V_profiles(first, source, factor)
		_condense_separate_V_profiles(second, source, factor)
	else:
		split_y = _condense_v_preserving_stems(first, source.width, factor)
		_condense_v_preserving_stems(second, source.width, factor)
	source_widths = _diagonal_stem_measurements(source, split_y)
	# Re-measure after each correction and require absolute convergence in font
	# units. This follows the perpendicular-stroke compensation recipe rather
	# than accepting a merely small change between two iterations.
	for _iteration in range(5):
		condensed_widths = _diagonal_stem_measurements(first, split_y)
		if max(
			abs(condensed_widths[index] - source_widths[index])
			for index in range(2)
		) <= W_STROKE_TOLERANCE:
			break
		compensation = tuple(
			max(
				0.95,
				min(1.05, source_widths[index] / condensed_widths[index]),
			)
			for index in range(2)
		)
		_thin_v_diagonals(first, split_y, compensation)
		_thin_v_diagonals(second, split_y, compensation)
	final_widths = _diagonal_stem_measurements(first, split_y)
	final_error = max(
		abs(final_widths[index] - source_widths[index])
		for index in range(2)
	)
	if final_error > W_STROKE_TOLERANCE:
		raise GenerationError(
			"%s stroke compensation did not converge (maximum error %.2f units)."
			% (character, final_error)
		)

	# Align the central top-stroke centers after rounding. Contrasted V sources
	# may deliberately have different left/right top spans, so forcing both
	# edges to coincide would destroy their source stroke weights.
	first.roundCoordinates()
	second.roundCoordinates()
	_align_V_diagonal_join(first.paths)
	_align_V_diagonal_join(second.paths)
	rounded_widths = _diagonal_stem_measurements(first, split_y)
	rounded_error = max(
		abs(rounded_widths[index] - source_widths[index])
		for index in range(2)
	)
	rounded_tolerance = max(
		1.0,
		max(source_widths) * 0.001,
	)
	if rounded_error > rounded_tolerance:
		raise GenerationError(
			"%s stroke compensation left %.2f units of error after rounding."
			% (character, rounded_error)
		)
	if separate_profiles:
		for source_path, path in zip(source.paths, first.paths):
			if max(
				abs(current - target)
				for current, target in zip(_single_diagonal_profile(path), _single_diagonal_profile(source_path))
			) > rounded_tolerance:
				raise GenerationError("W's local stroke profile changed after integer rounding.")
	_left_center, right_center = _top_diagonal_stroke_centers(
		first, source_name
	)
	second_left_center, _second_right_center = _top_diagonal_stroke_centers(
		second, source_name
	)
	offset = right_center - second_left_center
	if offset <= EPSILON:
		raise GenerationError(
			"Could not determine the spacing between %s's diagonals."
			% source_name
		)
	_translate_paths(second.paths, offset)
	candidate = GSLayer()
	for path in first.paths:
		candidate.shapes.append(path.copy())
	for path in second.paths:
		candidate.shapes.append(path.copy())

	# Re-establish sidebearings from the actual final outline. The earlier width
	# formula could leave a negative right sidebearing after the central overlap.
	source_left, _source_bottom, source_right, _source_top = _bounds_values(source)
	desired_left = source_left * factor
	desired_right = (float(source.width) - source_right) * factor
	candidate_left, _bottom, candidate_right, _top = _bounds_values(candidate)
	_translate_paths(candidate.paths, desired_left - candidate_left)
	outline_width = candidate_right - candidate_left
	candidate.width = round(desired_left + outline_width + desired_right)
	return _correct_X_diagonal_directions(candidate)


def _build_double_v(font, master, character):
	baseline = _build_double_v_at_factor(font, master, character)
	if character != "W":
		return baseline
	left, _bottom, right, _top = _bounds_values(baseline)
	baseline_width = right - left
	target = baseline_width * W_OUTLINE_WIDTH_GAIN
	factor = 0.85 * W_OUTLINE_WIDTH_GAIN
	for _iteration in range(8):
		candidate = _build_double_v_at_factor(font, master, character, factor, preserve_profile=True)
		left, _bottom, right, _top = _bounds_values(candidate)
		error = target - (right - left)
		# The builder snaps construction landmarks to the font grid first.
		if abs(error) <= 1.0:
			return candidate
		factor += error * 0.85 / baseline_width
		if not 0.1 < factor < 1.0:
			raise GenerationError("W's requested width leaves no usable diagonal joins.")
	raise GenerationError("W's 14% narrowing did not converge.")


def _normalize_round_vertical_extrema(layer, baseline, cap_height):
	outer, inner = _outer_and_inner_paths(layer)
	outer_oncurves = _oncurve_nodes(outer)
	outer_top_y = max(float(node.y) for node in outer_oncurves)
	outer_bottom_y = min(float(node.y) for node in outer_oncurves)
	top_delta = float(cap_height) - outer_top_y
	bottom_delta = float(baseline) - outer_bottom_y
	for path in (outer, inner):
		oncurves = _oncurve_nodes(path)
		top_y = max(float(node.y) for node in oncurves)
		bottom_y = min(float(node.y) for node in oncurves)
		moves = [
			(
				[node for node in oncurves if abs(float(node.y) - top_y) <= EPSILON],
				top_delta,
			),
			(
				[node for node in oncurves if abs(float(node.y) - bottom_y) <= EPSILON],
				bottom_delta,
			),
		]
		moved = set()
		for extrema, delta_y in moves:
			for node in extrema:
				if objc.pyobjc_id(node) not in moved:
					node.y = float(node.y) + delta_y
					moved.add(objc.pyobjc_id(node))
				for neighbor in _adjacent_nodes(path, node):
					if neighbor.type == OFFCURVE and objc.pyobjc_id(neighbor) not in moved:
						neighbor.y = float(neighbor.y) + delta_y
						moved.add(objc.pyobjc_id(neighbor))
	return outer, inner


def _right_arc_nodes(path, start_at_top):
	"""Return one contour's right half in a predictable top/bottom order."""
	for _attempt in range(2):
		oncurves = _oncurve_nodes(path)
		top = max(oncurves, key=lambda node: float(node.y))
		bottom = min(oncurves, key=lambda node: float(node.y))
		right = max(oncurves, key=lambda node: float(node.x))
		start, end = (top, bottom) if start_at_top else (bottom, top)
		arc = [start] + _forward_between(path, start, end)
		if right in arc:
			return arc
		path.reverse()
	raise GenerationError("Could not isolate the right half of O.")


def _left_arc_nodes(path, start, end):
	"""Orient a contour so the forward arc crosses its left extreme."""
	for _attempt in range(2):
		left = min(_oncurve_nodes(path), key=lambda node: float(node.x))
		arc = [start] + _forward_between(path, start, end)
		if left in arc:
			return arc
		path.reverse()
	raise GenerationError("Could not isolate the left side of the round source.")


def _append_cubic(path, cubic, smooth=True):
	"""Append one cubic tuple returned by _split_cubic."""
	path.nodes.append(_new_node(cubic[1], OFFCURVE))
	path.nodes.append(_new_node(cubic[2], OFFCURVE))
	path.nodes.append(_new_node(cubic[3], CURVE, smooth))


def _round_extrema(path):
	oncurves = _oncurve_nodes(path)
	return (
		max(oncurves, key=lambda node: float(node.y)),
		max(oncurves, key=lambda node: float(node.x)),
		min(oncurves, key=lambda node: float(node.y)),
	)


def _right_terminal_line_runs(path):
	"""Return right-side line chains that can describe C terminals.

	A plain terminal is one line segment. Glyphs Open Corners expands the same
	feature into several consecutive line segments. Grouping the complete chain
	therefore works with or without Open Corners and also with all-line C shapes.
	"""
	oncurves = _oncurve_nodes(path)
	if len(oncurves) < 4:
		raise GenerationError("C does not contain enough terminal geometry.")
	left = min(float(node.x) for node in oncurves)
	right = max(float(node.x) for node in oncurves)
	# A heavy C's inner terminal may cross the bounds midpoint. Requiring both
	# cap sides to be in the right half loses it after lowercase compensation.
	terminal_left_limit = left + (right - left) * 0.25
	bottom = min(float(node.y) for node in oncurves)
	top = max(float(node.y) for node in oncurves)
	# Faceted counters have their own cap/baseline corners. Those are body
	# extrema too, even though they do not reach the outer contour's bounds.
	# Do not absorb their long diagonals into an Open Corner terminal chain.
	body_extrema = set()
	for index, node in enumerate(oncurves):
		previous = oncurves[(index - 1) % len(oncurves)]
		next_node = oncurves[(index + 1) % len(oncurves)]
		local_extreme = (
			float(node.y) > max(float(previous.y), float(next_node.y)) + EPSILON
			or float(node.y) < min(float(previous.y), float(next_node.y)) - EPSILON
		)
		lengths = [
			((float(other.x) - float(node.x)) ** 2
			+ (float(other.y) - float(node.y)) ** 2) ** 0.5
			for other in (previous, next_node)
		]
		if local_extreme and all(
			neighbor.type != OFFCURVE for neighbor in _adjacent_nodes(path, node)
		) and (
			min(lengths) > max(lengths) * 0.5
			and min(lengths) > (top - bottom) * 0.08
		) and (
			min(float(previous.x), float(next_node.x)) + EPSILON
			< float(node.x)
			< max(float(previous.x), float(next_node.x)) - EPSILON
		):
			body_extrema.add(id(node))
	flags = []
	for index, node in enumerate(oncurves):
		next_node = oncurves[(index + 1) % len(oncurves)]
		flags.append(
			next_node.type == LINE
			and min(float(node.x), float(next_node.x)) > terminal_left_limit + EPSILON
			# A diamond's cap/baseline corner can sit to the right of the bounds
			# midpoint. Its long body edge is not part of the terminal line run.
			and not any(
				(id(endpoint) in body_extrema
					or abs(float(endpoint.y) - top) <= EPSILON
					or abs(float(endpoint.y) - bottom) <= EPSILON)
				and float(other.x) > float(endpoint.x) + EPSILON
				for endpoint, other in ((node, next_node), (next_node, node))
			)
		)
	if not any(flags):
		raise GenerationError("Could not identify C's right-side terminal lines.")
	if all(flags):
		raise GenerationError("Could not separate C's terminals from its body.")
	start = next(index for index, flag in enumerate(flags) if not flag)
	runs = []
	current = []
	for offset in range(1, len(flags) + 1):
		index = (start + offset) % len(flags)
		if flags[index]:
			if not current:
				current = [oncurves[index]]
			current.append(oncurves[(index + 1) % len(oncurves)])
		elif current:
			runs.append(current)
			current = []
	if current:
		runs.append(current)
	return runs


def _oriented_C_terminal_runs(path):
	"""Return C's upper/lower terminal nodes ordered outer-to-inner."""
	oncurves = _oncurve_nodes(path)
	left = min(float(node.x) for node in oncurves)
	right = max(float(node.x) for node in oncurves)
	bottom = min(float(node.y) for node in oncurves)
	top = max(float(node.y) for node in oncurves)
	center = ((left + right) * 0.5, (bottom + top) * 0.5)
	runs = _right_terminal_line_runs(path)
	top_runs = [
		run for run in runs
		if sum(float(node.y) for node in run) / len(run) > center[1]
	]
	bottom_runs = [
		run for run in runs
		if sum(float(node.y) for node in run) / len(run) < center[1]
	]
	if not top_runs or not bottom_runs:
		raise GenerationError("Could not identify both terminals in C.")
	selected = {
		"top": max(
			top_runs,
			key=lambda run: sum(float(node.y) for node in run) / len(run),
		),
		"bottom": min(
			bottom_runs,
			key=lambda run: sum(float(node.y) for node in run) / len(run),
		),
	}
	for label, run in tuple(selected.items()):
		run = list(run)
		first_radius = (
			(float(run[0].x) - center[0]) ** 2
			+ (float(run[0].y) - center[1]) ** 2
		)
		last_radius = (
			(float(run[-1].x) - center[0]) ** 2
			+ (float(run[-1].y) - center[1]) ** 2
		)
		if first_radius < last_radius:
			run.reverse()
		# Keep the whole chain. A terminal's curve-side anchor need not be its
		# nearest node to the glyph center (Open Corners are the common example).
		# Body extrema were excluded above; radial trimming loses real cap nodes.
		selected[label] = tuple(run)
	return selected, center


def _C_terminal_curve_endpoints(path, terminal_run):
	"""Return a terminal's original outer and inner curve-side anchors."""
	run = list(terminal_run)
	if len(run) < 2:
		raise GenerationError(
			"C's expanded terminal needs both outer and inner corner nodes."
		)
	return run[0], run[-1]


def _complete_C_terminal_runs(path):
	"""Return complete outer-to-inner terminal chains without topology guesses."""
	return _oriented_C_terminal_runs(path)


def _C_terminal_cut_edge(run):
	"""Find the actual across-stroke cut, merging collinear subdivisions."""
	chains = []
	start = run[0]
	previous = run[0]
	direction = None
	for node in run[1:]:
		vector = (float(node.x - previous.x), float(node.y - previous.y))
		length = (vector[0] ** 2 + vector[1] ** 2) ** 0.5
		if length <= EPSILON:
			continue
		unit = (vector[0] / length, vector[1] / length)
		if direction is not None and (
			abs(_cross(direction, unit)) > 0.00001
			or sum(direction[i] * unit[i] for i in range(2)) < 0.0
		):
			chains.append((start, previous))
			start = previous
		direction = unit
		previous = node
	chains.append((start, previous))
	a, b = max(chains, key=lambda pair: (
		abs(float(pair[1].x - pair[0].x)),
		float(pair[1].y - pair[0].y) ** 2,
	))
	return (a, b) if float(a.x) >= float(b.x) else (b, a)


def _sharpen_C_terminal_corners(path, terminal_run):
	"""Close an expanded terminal between its existing curve endpoints.

	Removing only the Open Corner expansion joins the two original curve-side
	anchors directly, without moving any curve node or handle.
	"""
	run = list(terminal_run)
	outer, inner = _C_terminal_curve_endpoints(path, run)
	if len(run) == 2:
		return outer, inner
	path_nodes = list(path.nodes)
	expansion_nodes = [node for node in run[1:] if node is not inner]
	for index in sorted(
		(path_nodes.index(node) for node in expansion_nodes), reverse=True
	):
		del path.nodes[index]
	return outer, inner


def _C_terminal_signatures(font, master):
	"""Extract normalized upper/lower terminal profiles from the current C."""
	source = _source_layer(font, "C", master.id)
	copy = _copy_decomposed(source)
	closed = [path for path in copy.paths if path.closed]
	if len(closed) != 1:
		raise GenerationError(
			"C must have one closed contour to define related terminals."
		)
	path = closed[0]
	selected, center = _complete_C_terminal_runs(path)
	signatures = {}
	for label, run in selected.items():
		points = [_point(node) for node in run]
		outer = points[0]
		inner = points[-1]
		dx = inner[0] - outer[0]
		dy = inner[1] - outer[1]
		length = (dx * dx + dy * dy) ** 0.5
		if length <= EPSILON:
			raise GenerationError("C contains a zero-length terminal.")
		axis = (dx / length, dy / length)
		normal = (-axis[1], axis[0])
		normalized = []
		for point in points:
			relative = (point[0] - outer[0], point[1] - outer[1])
			normalized.append((
				(relative[0] * axis[0] + relative[1] * axis[1]) / length,
				(relative[0] * normal[0] + relative[1] * normal[1]) / length,
			))
		signatures[label] = {
			"direction": axis,
			"points": tuple(normalized),
			"sourceThickness": length,
			# Retain actual curve-side tangents, not a node-count proxy for the
			# terminal style. Plain angled cuts and expanded caps may both have
			# several nodes, but their curve attachments are quite different.
			"bodyTangents": tuple(
				next((
					(
						(float(handle.x) - float(anchor.x)) * axis[0]
						+ (float(handle.y) - float(anchor.y)) * axis[1],
						(float(handle.x) - float(anchor.x)) * normal[0]
						+ (float(handle.y) - float(anchor.y)) * normal[1],
					)
					for handle in _adjacent_nodes(path, anchor)
					if handle.type == OFFCURVE
				), None)
				for anchor in (run[0], run[-1])
			),
		}
	return signatures


def _terminal_profile_points(signature, outer_point, inner_point):
	"""Map a normalized C terminal onto explicit outer/inner landmarks."""
	outer = (float(outer_point[0]), float(outer_point[1]))
	inner = (float(inner_point[0]), float(inner_point[1]))
	dx = inner[0] - outer[0]
	dy = inner[1] - outer[1]
	length = (dx * dx + dy * dy) ** 0.5
	if length <= EPSILON:
		raise GenerationError("The target terminal has no measurable thickness.")
	axis = (dx / length, dy / length)
	normal = (-axis[1], axis[0])
	return tuple(
		(
			outer[0] + (u * axis[0] + v * normal[0]) * length,
			outer[1] + (u * axis[1] + v * normal[1]) * length,
		)
		for u, v in signature["points"]
	)


def _extend_terminal_profile_vertically(points, factor):
	"""Scale a terminal's complete line profile vertically around its midpoint."""
	if not points:
		return tuple()
	center_y = (float(points[0][1]) + float(points[-1][1])) * 0.5
	return tuple(
		(
			float(point[0]),
			center_y + (float(point[1]) - center_y) * float(factor),
		)
		for point in points
	)


def _arc_segment_route(path, start, end, prefer_smaller_min_x):
	"""Return an oriented contour route and its drawable node groups.

	The second candidate travels against path direction. Its segment node lists
	are reversed explicitly so the endpoint node types do not need to be changed.
	"""
	forward_arc = [start] + _forward_between(path, start, end)
	forward_segments = _arc_drawable_segments(forward_arc)
	forward_groups = [
		(
			list(forward_arc[segment[3]:segment[4] + 1]),
			bool(segment[5]),
		)
		for segment in forward_segments
	]
	reverse_native_arc = [end] + _forward_between(path, end, start)
	reverse_native_segments = _arc_drawable_segments(reverse_native_arc)
	reverse_groups = [
		(
			list(reversed(
				reverse_native_arc[segment[3]:segment[4] + 1]
			)),
			bool(segment[5]),
		)
		for segment in reversed(reverse_native_segments)
	]
	reverse_arc = [start] + list(reversed(reverse_native_arc[1:-1])) + [end]
	candidates = (
		(forward_arc, forward_groups),
		(reverse_arc, reverse_groups),
	)
	key = lambda item: min(float(node.x) for node in item[0])
	return (min if prefer_smaller_min_x else max)(candidates, key=key)


def _C_contour_groups(layer, terminal_runs=None):
	"""Pair C's outer and counter arcs without including either terminal."""
	closed = [path for path in layer.paths if path.closed]
	if len(closed) != 1:
		raise GenerationError(
			"C must have one closed contour to build lowercase c."
		)
	path = closed[0]
	terminal_runs = terminal_runs if terminal_runs is not None else _complete_C_terminal_runs(path)[0]
	outer_arc, outer_segments = _arc_segment_route(
		path,
		terminal_runs["top"][0],
		terminal_runs["bottom"][0],
		True,
	)
	inner_arc, inner_segments = _arc_segment_route(
		path,
		terminal_runs["top"][-1],
		terminal_runs["bottom"][-1],
		False,
	)
	if len(outer_segments) != len(inner_segments) or not outer_segments:
		raise GenerationError(
			"C's outer and inner arcs need corresponding segment topology to "
			"preserve stroke weight in c."
		)
	groups = []
	for outer_segment, inner_segment in zip(outer_segments, inner_segments):
		outer_nodes, outer_is_curve = outer_segment
		inner_nodes, inner_is_curve = inner_segment
		groups.append((
			inner_nodes,
			outer_nodes,
			(inner_is_curve, outer_is_curve),
		))
	return groups, path, terminal_runs


def _transform_paths_affinely(
	paths, source_center, target_center, factor_x, factor_y
):
	for path in paths:
		for node in path.nodes:
			node.x = (
				float(target_center[0])
				+ (float(node.x) - float(source_center[0])) * float(factor_x)
			)
			node.y = (
				float(target_center[1])
				+ (float(node.y) - float(source_center[1])) * float(factor_y)
			)


def _apply_C_terminal_profiles(path, terminal_runs, signatures, vertical_factor):
	"""Reproduce all C terminal nodes between compensated arc endpoints."""
	for label in ("top", "bottom"):
		run = tuple(terminal_runs[label])
		outer, inner = _point(run[0]), _point(run[-1])
		center = _lerp(outer, inner, 0.5)
		length = ((inner[0] - outer[0]) ** 2 + (inner[1] - outer[1]) ** 2) ** 0.5
		axis = signatures[label]["direction"]
		# Unequal boundary compensation can rotate their endpoint chord. Keep
		# C's terminal angle/profile instead of tilting a formerly flat cap.
		outer = tuple(center[i] - axis[i] * length * 0.5 for i in range(2))
		inner = tuple(center[i] + axis[i] * length * 0.5 for i in range(2))
		profile = _terminal_profile_points(
			signatures[label], outer, inner
		)
		profile = _extend_terminal_profile_vertically(
			profile, vertical_factor
		)
		for node, point in ((run[0], profile[0]), (run[-1], profile[-1])):
			_move_extreme_with_handles(
				path,
				node,
				float(point[0]) - float(node.x),
				float(point[1]) - float(node.y),
			)
		for node, point in zip(run[1:-1], profile[1:-1]):
			node.x = float(point[0])
			node.y = float(point[1])


def _C_counter_center_x(path, terminal_runs):
	"""Measure the horizontal center of C's open counter from its inner arc."""
	top_inner = terminal_runs["top"][-1]
	bottom_inner = terminal_runs["bottom"][-1]
	first = [bottom_inner] + _forward_between(path, bottom_inner, top_inner)
	second = [top_inner] + _forward_between(path, top_inner, bottom_inner)
	candidates = []
	for arc in (first, second):
		oncurves = [node for node in arc if node.type != OFFCURVE]
		if oncurves:
			candidates.append(oncurves)
	if len(candidates) != 2:
		raise GenerationError("Could not isolate C's inner counter arc.")
	# The inner arc has the less-leftward minimum; the other route traverses
	# C's outside contour before returning to the second terminal.
	inner_arc = max(
		candidates,
		key=lambda arc: min(float(node.x) for node in arc),
	)
	left = min(float(node.x) for node in inner_arc)
	right = max(float(node.x) for node in inner_arc)
	if right - left <= EPSILON:
		raise GenerationError("C's counter has no measurable horizontal span.")
	return (left + right) * 0.5


def _round_contour_groups(layer):
	"""Pair every corresponding outer/inner segment of a round glyph."""
	outer, inner = _outer_and_inner_paths(layer)
	outer_top, outer_bottom = _right_top_bottom(outer)
	inner_top, inner_bottom = _right_top_bottom(inner)
	arc_pairs = (
		(
			_right_side_arc(outer, outer_top, outer_bottom),
			_right_side_arc(inner, inner_top, inner_bottom),
		),
		(
			_left_arc_nodes(outer, outer_bottom, outer_top),
			_left_arc_nodes(inner, inner_bottom, inner_top),
		),
	)
	groups = []
	for outer_arc, inner_arc in arc_pairs:
		outer_segments = _arc_drawable_segments(outer_arc)
		inner_segments = _arc_drawable_segments(inner_arc)
		if len(outer_segments) != len(inner_segments) or not outer_segments:
			raise GenerationError(
				"O's outer and inner contours need corresponding segment topology "
				"to preserve stroke weight in o."
			)
		for outer_segment, inner_segment in zip(
			outer_segments, inner_segments
		):
			outer_nodes = list(
				outer_arc[outer_segment[3]:outer_segment[4] + 1]
			)
			inner_nodes = list(
				inner_arc[inner_segment[3]:inner_segment[4] + 1]
			)
			groups.append((
				inner_nodes,
				outer_nodes,
				(bool(inner_segment[5]), bool(outer_segment[5])),
			))
	return groups, outer, inner


def _cubic_approximate_length(points, steps=24):
	previous = _cubic_point(points, 0.0)
	total = 0.0
	for step in range(1, steps + 1):
		current = _cubic_point(points, step / float(steps))
		total += (
			(current[0] - previous[0]) ** 2
			+ (current[1] - previous[1]) ** 2
		) ** 0.5
		previous = current
	return total


def _round_boundary_model(path):
	"""Describe one round boundary from top around right, bottom, and left."""
	top, bottom = _right_top_bottom(path)
	right_arc = _right_side_arc(path, top, bottom)
	left_arc = _left_arc_nodes(path, bottom, top)
	segments = []
	for arc in (right_arc, left_arc):
		for segment in _arc_drawable_segments(arc):
			nodes = list(arc[segment[3]:segment[4] + 1])
			segments.append({
				"nodes": nodes,
				"points": segment[2],
				"curve": bool(segment[5]),
				"length": _cubic_approximate_length(segment[2]),
			})
	total = sum(segment["length"] for segment in segments)
	if total <= EPSILON:
		raise GenerationError("O contains a zero-length contour.")
	progress = 0.0
	for segment in segments:
		segment["start"] = progress / total
		progress += segment["length"]
		segment["end"] = progress / total
	return segments


def _boundary_model_from_node_groups(groups):
	segments = []
	for nodes, is_curve in groups:
		points = tuple(_point(node) for node in nodes)
		if is_curve:
			if len(points) != 4:
				raise GenerationError("A curved boundary segment needs four nodes.")
		else:
			if len(points) != 2:
				raise GenerationError("A straight boundary segment needs two nodes.")
			points = (
				points[0],
				_lerp(points[0], points[1], 1.0 / 3.0),
				_lerp(points[0], points[1], 2.0 / 3.0),
				points[1],
			)
		segments.append({
			"nodes": list(nodes),
			"points": points,
			"curve": bool(is_curve),
			"length": _cubic_approximate_length(points),
		})
	total = sum(segment["length"] for segment in segments)
	if total <= EPSILON:
		raise GenerationError("The stroke boundary has zero length.")
	progress = 0.0
	for segment in segments:
		segment["start"] = progress / total
		progress += segment["length"]
		segment["end"] = progress / total
	return segments


def _C_boundary_models(layer, terminal_runs=None):
	closed = [path for path in layer.paths if path.closed]
	if len(closed) != 1:
		raise GenerationError("C must have one closed contour to build c.")
	path = closed[0]
	runs = terminal_runs if terminal_runs is not None else _complete_C_terminal_runs(path)[0]
	_outer_arc, outer_groups = _arc_segment_route(
		path, runs["top"][0], runs["bottom"][0], True
	)
	_inner_arc, inner_groups = _arc_segment_route(
		path, runs["top"][-1], runs["bottom"][-1], False
	)
	return (
		_boundary_model_from_node_groups(outer_groups),
		_boundary_model_from_node_groups(inner_groups),
		path,
		runs,
	)


def _boundary_model_point(model, progress):
	progress = max(0.0, min(1.0, float(progress)))
	segment = model[-1]
	for candidate in model:
		# Progress is dimensionless. The coordinate tolerance would clamp a
		# whole 1% of an arc at every extra node, producing zero local tangents.
		if progress <= candidate["end"] + 1e-10:
			segment = candidate
			break
	span = max(1e-12, segment["end"] - segment["start"])
	factor = max(0.0, min(1.0, (progress - segment["start"]) / span))
	return _cubic_point(segment["points"], factor)


def _boundary_models_center(*models):
	points = []
	for model in models:
		points.extend(
			_boundary_model_point(model, step / 64.0)
			for step in range(65)
		)
	return (
		(min(point[0] for point in points) + max(point[0] for point in points)) * 0.5,
		(min(point[1] for point in points) + max(point[1] for point in points)) * 0.5,
	)


def _boundary_model_radial_point(model, center, reference):
	"""Find the opposite-boundary point on the same ray from the glyph center."""
	reference_vector = (
		float(reference[0]) - float(center[0]),
		float(reference[1]) - float(center[1]),
	)
	reference_length = (
		reference_vector[0] ** 2 + reference_vector[1] ** 2
	) ** 0.5
	if reference_length <= EPSILON:
		return _boundary_model_point(model, 0.5)

	def score(progress):
		point = _boundary_model_point(model, progress)
		vector = (point[0] - center[0], point[1] - center[1])
		length = (vector[0] ** 2 + vector[1] ** 2) ** 0.5
		if length <= EPSILON:
			return 10.0
		cross = abs(_cross(reference_vector, vector)) / (
			reference_length * length
		)
		dot = reference_vector[0] * vector[0] + reference_vector[1] * vector[1]
		return cross + (2.0 if dot < 0.0 else 0.0)

	steps = 128
	best_step = min(range(steps + 1), key=lambda step: score(step / float(steps)))
	low = max(0.0, (best_step - 1) / float(steps))
	high = min(1.0, (best_step + 1) / float(steps))
	for _iteration in range(18):
		first = low + (high - low) / 3.0
		second = high - (high - low) / 3.0
		if score(first) <= score(second):
			high = second
		else:
			low = first
	return _boundary_model_point(model, (low + high) * 0.5)


def _boundary_model_thickness(outer_model, inner_model):
	"""Median perpendicular thickness from semantically matched arc samples."""
	center = _boundary_models_center(outer_model, inner_model)
	values = []
	for progress in (0.08, 0.16, 0.28, 0.38, 0.62, 0.72, 0.84, 0.92):
		outer = _boundary_model_point(outer_model, progress)
		inner = _boundary_model_radial_point(inner_model, center, outer)
		before_progress = max(0.0, progress - 0.005)
		after_progress = min(1.0, progress + 0.005)
		before_outer = _boundary_model_point(outer_model, before_progress)
		after_outer = _boundary_model_point(outer_model, after_progress)
		before = _lerp(
			before_outer,
			_boundary_model_radial_point(inner_model, center, before_outer),
			0.5,
		)
		after = _lerp(
			after_outer,
			_boundary_model_radial_point(inner_model, center, after_outer),
			0.5,
		)
		tangent = (after[0] - before[0], after[1] - before[1])
		length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
		if length <= EPSILON:
			continue
		normal = (-tangent[1] / length, tangent[0] / length)
		vector = (inner[0] - outer[0], inner[1] - outer[1])
		values.append(abs(vector[0] * normal[0] + vector[1] * normal[1]))
	if not values:
		raise GenerationError("Could not measure O's perpendicular stroke weight.")
	values.sort()
	return (values[len(values) // 2 - 1] + values[len(values) // 2]) * 0.5


def _transform_unmatched_round_boundaries(
	source_outer_model,
	source_inner_model,
	target_outer_model,
	target_inner_model,
	source_center,
	target_center,
	factor_x,
	factor_y,
	weight_factor,
	anchor_inner=False,
):
	"""Map unequal boundary topologies by normalized arc position."""
	proposals = {}
	radial_center = _boundary_models_center(
		source_outer_model, source_inner_model
	)
	for is_outer, source_model, target_model, opposite_model in (
		(True, source_outer_model, target_outer_model, source_inner_model),
		(False, source_inner_model, target_inner_model, source_outer_model),
	):
		for source_segment, target_segment in zip(source_model, target_model):
			control_factors = (
				(0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0)
				if source_segment["curve"] else (0.0, 1.0)
			)
			for source_node, target_node, control_factor in zip(
				source_segment["nodes"],
				target_segment["nodes"],
				control_factors,
			):
				progress = (
					source_segment["start"]
					+ (source_segment["end"] - source_segment["start"])
					* control_factor
				)
				self_point = _point(source_node)
				if anchor_inner and not is_outer:
					position = (
						float(target_center[0])
						+ (self_point[0] - float(source_center[0]))
						* float(factor_x),
						float(target_center[1])
						+ (self_point[1] - float(source_center[1]))
						* float(factor_y),
					)
					proposals.setdefault(
						id(target_node), (target_node, [])
					)[1].append(position)
					continue
				opposite = _boundary_model_radial_point(
					opposite_model, radial_center, self_point
				)
				if anchor_inner:
					mapped_inner = (
						float(target_center[0])
						+ (opposite[0] - float(source_center[0]))
						* float(factor_x),
						float(target_center[1])
						+ (opposite[1] - float(source_center[1]))
						* float(factor_y),
					)
					position = (
						mapped_inner[0]
						+ (self_point[0] - opposite[0]) * weight_factor,
						mapped_inner[1]
						+ (self_point[1] - opposite[1]) * weight_factor,
					)
					proposals.setdefault(
						id(target_node), (target_node, [])
					)[1].append(position)
					continue
				center = _lerp(self_point, opposite, 0.5)
				mapped_center = (
					float(target_center[0])
					+ (center[0] - float(source_center[0])) * float(factor_x),
					float(target_center[1])
					+ (center[1] - float(source_center[1])) * float(factor_y),
				)
				half = (
					(self_point[0] - opposite[0]) * 0.5 * weight_factor,
					(self_point[1] - opposite[1]) * 0.5 * weight_factor,
				)
				position = (mapped_center[0] + half[0], mapped_center[1] + half[1])
				proposals.setdefault(id(target_node), (target_node, []))[1].append(
					position
				)
	for node, positions in proposals.values():
		node.x = sum(point[0] for point in positions) / len(positions)
		node.y = sum(point[1] for point in positions) / len(positions)


def _transform_round_anchored_inner(
	source_groups,
	target_groups,
	source_center,
	target_center,
	factor_x,
	factor_y,
	target_widths,
):
	"""Keep the scaled counter faithful; restore stroke weight outward."""
	weight_factors = [1.0 for _group in source_groups]
	tolerances = [max(0.5, width * 0.001) for width in target_widths]
	for _iteration in range(8):
		proposals = {}
		for source_group, target_group, weight_factor in zip(
			source_groups, target_groups, weight_factors
		):
			source_inner, source_outer = _boundary_group_cubics(source_group)
			target_inner_nodes, target_outer_nodes, _target_curve = target_group
			inner_positions = []
			outer_positions = []
			for source_i, source_o in zip(source_inner, source_outer):
				inner_point = (
					float(target_center[0])
					+ (float(source_i[0]) - float(source_center[0]))
					* float(factor_x),
					float(target_center[1])
					+ (float(source_i[1]) - float(source_center[1]))
					* float(factor_y),
				)
				outer_point = (
					inner_point[0]
					+ (float(source_o[0]) - float(source_i[0]))
					* weight_factor,
					inner_point[1]
					+ (float(source_o[1]) - float(source_i[1]))
					* weight_factor,
				)
				inner_positions.append(inner_point)
				outer_positions.append(outer_point)
			for nodes, positions in (
				(target_inner_nodes, inner_positions),
				(target_outer_nodes, outer_positions),
			):
				indices = (0, 1, 2, 3) if len(nodes) == 4 else (0, 3)
				for node, position_index in zip(nodes, indices):
					proposals.setdefault(id(node), (node, []))[1].append(
						positions[position_index]
					)
		for node, positions in proposals.values():
			node.x = sum(point[0] for point in positions) / len(positions)
			node.y = sum(point[1] for point in positions) / len(positions)
		current_widths = [
			_shoulder_group_thickness(group) for group in target_groups
		]
		if all(
			abs(current - target) <= tolerance
			for current, target, tolerance in zip(
				current_widths, target_widths, tolerances
			)
		):
			return current_widths, tolerances
		for index, (current, target) in enumerate(
			zip(current_widths, target_widths)
		):
			weight_factors[index] *= max(
				0.95, min(1.05, target / current)
			)
	raise GenerationError("P's anchored D-bowl compensation did not converge.")


def _transform_round_centerlines(
	source_groups,
	target_groups,
	source_center,
	target_center,
	factor_x,
	factor_y,
	target_widths,
	allow_unmeasurable=False,
	tolerance_floor=0.5,
	align_tangents=None,
	measure_group=None,
	iteration_limit=12,
):
	"""Scale round centerlines while retaining perpendicular source weight."""
	weight_factors = [1.0 for _group in source_groups]
	tolerances = [max(tolerance_floor, width * 0.001) for width in target_widths]
	for _iteration in range(iteration_limit):
		proposals = {}
		for source_group, target_group, weight_factor in zip(
			source_groups, target_groups, weight_factors
		):
			source_inner, source_outer = _boundary_group_cubics(source_group)
			target_inner_nodes, target_outer_nodes, _target_curve = target_group
			target_positions = ([], [])
			for source_i, source_o in zip(source_inner, source_outer):
				center = _lerp(source_i, source_o, 0.5)
				mapped_center = (
					float(target_center[0])
					+ (center[0] - float(source_center[0])) * float(factor_x),
					float(target_center[1])
					+ (center[1] - float(source_center[1])) * float(factor_y),
				)
				half_vector = (
					(float(source_i[0]) - float(source_o[0])) * 0.5,
					(float(source_i[1]) - float(source_o[1])) * 0.5,
				)
				inner_point = (
					mapped_center[0] + half_vector[0] * weight_factor,
					mapped_center[1] + half_vector[1] * weight_factor,
				)
				outer_point = (
					mapped_center[0] - half_vector[0] * weight_factor,
					mapped_center[1] - half_vector[1] * weight_factor,
				)
				target_positions[0].append(inner_point)
				target_positions[1].append(outer_point)
			for nodes, positions in zip(
				(target_inner_nodes, target_outer_nodes), target_positions
			):
				indices = (0, 1, 2, 3) if len(nodes) == 4 else (0, 3)
				for node, position_index in zip(nodes, indices):
					proposals.setdefault(id(node), (node, []))[1].append(
						positions[position_index]
					)
		for node, positions in proposals.values():
			node.x = sum(point[0] for point in positions) / len(positions)
			node.y = sum(point[1] for point in positions) / len(positions)
		if align_tangents is not None:
			align_tangents()
		current_widths = []
		for group in target_groups:
			try:
				current_widths.append(_shoulder_group_thickness(group) if measure_group is None
					else measure_group(group))
			except GenerationError:
				if not allow_unmeasurable:
					raise
				# Shared corners can make a straight connector's temporary
				# centerline degenerate while its two boundaries remain valid.  Its
				# original half-vectors were already copied unchanged above.
				current_widths.append(None)
		if all(
			current is None or abs(current - target) <= tolerance
			for current, target, tolerance in zip(
				current_widths, target_widths, tolerances
			)
		):
			return current_widths, tolerances
		for index, (current, target) in enumerate(
			zip(current_widths, target_widths)
		):
			if current is None:
				continue
			weight_factors[index] *= max(
				0.95, min(1.05, target / current)
			)
	raise GenerationError(
		"o's curved-stroke compensation did not converge (%s → %s)."
		% (
			", ".join("%.2f" % value for value in target_widths),
			", ".join("%.2f" % value for value in current_widths),
		)
	)


def _master_metric_zone(master, metric_type, fallback_position):
	"""Return a master metric's reference position and overshoot boundary."""
	store = None
	try:
		store = master.defaultMetricValueForType_(metric_type)
	except Exception:
		pass
	if store is None:
		return float(fallback_position), float(fallback_position)
	try:
		position = float(store.position)
	except Exception:
		position = float(fallback_position)
	try:
		overshoot = float(store.overshoot)
	except Exception:
		overshoot = 0.0
	return position, position + overshoot


def _build_o_unmatched_topology(font, master):
	"""Scale any two-contour O while preserving every source node and handle."""
	source = _source_layer(font, "O", master.id)
	source_copy = _copy_decomposed(source)
	source_outer, source_inner = _outer_and_inner_paths(source_copy)
	source_outer_model = _round_boundary_model(source_outer)
	source_inner_model = _round_boundary_model(source_inner)
	source_thickness = _boundary_model_thickness(
		source_outer_model, source_inner_model
	)
	target_thickness = source_thickness * LOWERCASE_O_STROKE_FACTOR
	outer_left, outer_bottom, outer_right, outer_top = _bounds_values(source_outer)
	cap_height = float(master.capHeight)
	x_height = float(master.xHeight)
	if cap_height <= EPSILON or x_height <= EPSILON:
		raise GenerationError("The master needs positive cap and x-heights for o.")
	proportion_scale = x_height / cap_height
	width_scale = proportion_scale * LOWERCASE_O_WIDTH_FACTOR
	_baseline_position, bottom_overshoot = _master_metric_zone(
		master, GSMetricsTypeBaseline, 0.0
	)
	_x_height_position, top_overshoot = _master_metric_zone(
		master, GSMetricsTypexHeight, x_height
	)
	target_bounds = (
		outer_left * width_scale,
		bottom_overshoot,
		outer_right * width_scale,
		top_overshoot,
	)
	source_center = (
		(outer_left + outer_right) * 0.5,
		(outer_bottom + outer_top) * 0.5,
	)
	target_center = (
		(target_bounds[0] + target_bounds[2]) * 0.5,
		(target_bounds[1] + target_bounds[3]) * 0.5,
	)
	source_width = outer_right - outer_left
	source_height = outer_top - outer_bottom
	target_width = target_bounds[2] - target_bounds[0]
	target_height = target_bounds[3] - target_bounds[1]
	if min(source_width, source_height, target_width, target_height) <= EPSILON:
		raise GenerationError("O has no measurable bounds for o.")
	working_x = target_width / source_width
	working_y = target_height / source_height
	tolerance = max(0.75, target_thickness * 0.001)

	for _width_iteration in range(10):
		candidate = _copy_decomposed(source)
		candidate_outer, candidate_inner = _outer_and_inner_paths(candidate)
		candidate_outer_model = _round_boundary_model(candidate_outer)
		candidate_inner_model = _round_boundary_model(candidate_inner)
		weight_factor = LOWERCASE_O_STROKE_FACTOR
		for _weight_iteration in range(20):
			_transform_unmatched_round_boundaries(
				source_outer_model,
				source_inner_model,
				candidate_outer_model,
				candidate_inner_model,
				source_center,
				target_center,
				working_x,
				working_y,
				weight_factor,
			)
			# Horizontal extrema are part of the requested finished geometry, so
			# include that constraint in the compensation loop rather than changing
			# the measured stroke only after convergence.
			_straighten_horizontal_extrema_handles(candidate)
			candidate_outer_model = _round_boundary_model(candidate_outer)
			candidate_inner_model = _round_boundary_model(candidate_inner)
			measured = _boundary_model_thickness(
				candidate_outer_model, candidate_inner_model
			)
			if abs(measured - target_thickness) <= tolerance:
				break
			weight_factor *= max(
				0.95, min(1.05, target_thickness / measured)
			)
		else:
			raise GenerationError(
				"o's arbitrary-topology stroke compensation did not converge."
			)
		current_left, current_bottom, current_right, current_top = _bounds_values(
			candidate_outer
		)
		width_error = target_width - (current_right - current_left)
		height_error = target_height - (current_top - current_bottom)
		if abs(width_error) <= 0.25 and abs(height_error) <= 0.25:
			break
		working_x += width_error / source_width
		working_y += height_error / source_height
	else:
		raise GenerationError("o's arbitrary-topology proportions did not converge.")

	_translate_paths(
		candidate.paths,
		target_bounds[0] - current_left,
		target_bounds[1] - current_bottom,
	)
	candidate.width = round(float(source.width) * width_scale)
	_straighten_horizontal_extrema_handles(candidate)
	candidate.correctPathDirection()
	_ensure_opposing_round_directions(candidate)
	candidate.roundCoordinates()
	_straighten_horizontal_extrema_handles(candidate)
	candidate.correctPathDirection()
	_ensure_opposing_round_directions(candidate)
	final_outer, final_inner = _outer_and_inner_paths(candidate)
	final_thickness = _boundary_model_thickness(
		_round_boundary_model(final_outer), _round_boundary_model(final_inner)
	)
	if abs(final_thickness - target_thickness) > tolerance:
		raise GenerationError(
			"o's perpendicular stroke weight changed after rounding "
			"(%.2f target, %.2f measured)."
			% (target_thickness, final_thickness)
		)
	# Boundary-model inspection may reverse contours internally to establish a
	# semantic top-right-bottom-left traversal. Restore fill winding last.
	_ensure_opposing_round_directions(candidate)
	return candidate


def _build_o(font, master):
	"""Scale O's centerlines to x-height while preserving its stroke system."""
	source = _source_layer(font, "O", master.id)
	source_copy = _copy_decomposed(source)
	try:
		source_groups, source_outer, source_inner = _round_contour_groups(
			source_copy
		)
	except GenerationError as error:
		if "corresponding segment topology" not in str(error):
			raise
		return _build_o_unmatched_topology(font, master)
	source_widths = [
		_shoulder_group_thickness(group) for group in source_groups
	]
	target_widths = [
		width * LOWERCASE_O_STROKE_FACTOR for width in source_widths
	]
	outer_left, outer_bottom, outer_right, outer_top = _bounds_values(
		source_outer
	)
	inner_left, inner_bottom, inner_right, inner_top = _bounds_values(
		source_inner
	)
	cap_height = float(master.capHeight)
	x_height = float(master.xHeight)
	if cap_height <= EPSILON or x_height <= EPSILON:
		raise GenerationError("The master needs positive cap and x-heights for o.")
	proportion_scale = x_height / cap_height
	width_scale = proportion_scale * LOWERCASE_O_WIDTH_FACTOR
	_baseline_position, bottom_overshoot = _master_metric_zone(
		master, GSMetricsTypeBaseline, 0.0
	)
	_x_height_position, top_overshoot = _master_metric_zone(
		master, GSMetricsTypexHeight, x_height
	)
	if top_overshoot <= bottom_overshoot + EPSILON:
		raise GenerationError(
			"The master's lowercase top and bottom overshoot zones overlap."
		)
	target_outer = (
		outer_left * width_scale,
		bottom_overshoot,
		outer_right * width_scale,
		top_overshoot,
	)

	left_stroke = (inner_left - outer_left) * LOWERCASE_O_STROKE_FACTOR
	right_stroke = (outer_right - inner_right) * LOWERCASE_O_STROKE_FACTOR
	bottom_stroke = (inner_bottom - outer_bottom) * LOWERCASE_O_STROKE_FACTOR
	top_stroke = (outer_top - inner_top) * LOWERCASE_O_STROKE_FACTOR
	if min(left_stroke, right_stroke, bottom_stroke, top_stroke) <= EPSILON:
		raise GenerationError(
			"O's counter must sit completely inside its outer contour."
		)

	source_centers = (
		(outer_left + inner_left) * 0.5,
		(outer_bottom + inner_bottom) * 0.5,
		(outer_right + inner_right) * 0.5,
		(outer_top + inner_top) * 0.5,
	)
	target_centers = (
		target_outer[0] + left_stroke * 0.5,
		target_outer[1] + bottom_stroke * 0.5,
		target_outer[2] - right_stroke * 0.5,
		target_outer[3] - top_stroke * 0.5,
	)
	source_center_width = source_centers[2] - source_centers[0]
	source_center_height = source_centers[3] - source_centers[1]
	target_center_width = target_centers[2] - target_centers[0]
	target_center_height = target_centers[3] - target_centers[1]
	if min(
		source_center_width,
		source_center_height,
		target_center_width,
		target_center_height,
	) <= EPSILON:
		raise GenerationError(
			"O's strokes are too heavy to fit inside the requested x-height."
		)
	source_center = (
		(source_centers[0] + source_centers[2]) * 0.5,
		(source_centers[1] + source_centers[3]) * 0.5,
	)
	target_center = (
		(target_centers[0] + target_centers[2]) * 0.5,
		(target_centers[1] + target_centers[3]) * 0.5,
	)
	working_x = target_center_width / source_center_width
	working_y = target_center_height / source_center_height
	target_outer_width = target_outer[2] - target_outer[0]
	target_outer_height = target_outer[3] - target_outer[1]
	compensation_widths = list(target_widths)

	for _iteration in range(12):
		candidate = _copy_decomposed(source)
		target_groups, target_outer_path, _target_inner_path = (
			_round_contour_groups(candidate)
		)
		final_widths, tolerances = _transform_round_centerlines(
			source_groups,
			target_groups,
			source_center,
			target_center,
			working_x,
			working_y,
			compensation_widths,
			tolerance_floor=0.1,
		)
		_straighten_horizontal_extrema_handles(candidate)
		target_groups, target_outer_path, _target_inner_path = (
			_round_contour_groups(candidate)
		)
		final_widths = [
			_shoulder_group_thickness(group) for group in target_groups
		]
		tolerances = [max(0.5, width * 0.001) for width in target_widths]
		current_left, current_bottom, current_right, current_top = (
			_bounds_values(target_outer_path)
		)
		width_error = target_outer_width - (current_right - current_left)
		height_error = target_outer_height - (current_top - current_bottom)
		weights_ok = all(
			abs(current - target) <= tolerance
			for current, target, tolerance in zip(
				final_widths, target_widths, tolerances
			)
		)
		if (
			abs(width_error) <= 0.25
			and abs(height_error) <= 0.25
			and weights_ok
		):
			break
		# Damped coupled updates prevent thin strokes from alternating across
		# the inner solver's tolerance band instead of reaching the dimensions.
		working_x += 0.5 * width_error / source_center_width
		working_y += 0.5 * height_error / source_center_height
		compensation_widths = [
			working_target * (max(0.95, min(1.05, target / current)) ** 0.5)
			for working_target, target, current in zip(
				compensation_widths, target_widths, final_widths
			)
		]
	else:
		raise GenerationError(
			"o's target proportions and stroke weight did not converge."
		)

	_translate_paths(
		candidate.paths,
		target_outer[0] - current_left,
		target_outer[1] - current_bottom,
	)
	if any(
		abs(current - target_width) > tolerance
		for current, target_width, tolerance in zip(
			final_widths, target_widths, tolerances
		)
	):
		raise GenerationError(
			"o did not reach 98% of O's perpendicular stroke weight."
		)
	candidate.width = round(float(source.width) * width_scale)
	_straighten_horizontal_extrema_handles(candidate)
	candidate.correctPathDirection()
	_ensure_opposing_round_directions(candidate)
	candidate.roundCoordinates()
	_straighten_horizontal_extrema_handles(candidate)
	candidate.correctPathDirection()
	_ensure_opposing_round_directions(candidate)
	validation_copy = candidate.copy()
	final_groups, _final_outer, _final_inner = _round_contour_groups(
		validation_copy
	)
	rounded_widths = [
		_shoulder_group_thickness(group) for group in final_groups
	]
	grid_tolerances = [max(0.75, width * 0.001) for width in target_widths]
	if any(
		abs(current - target_width) > tolerance
		for current, target_width, tolerance in zip(
			rounded_widths, target_widths, grid_tolerances
		)
	):
		raise GenerationError(
			"o's rounded outline no longer preserves O's stroke weight (%s → %s)."
			% (
				", ".join("%.2f" % value for value in target_widths),
				", ".join("%.2f" % value for value in rounded_widths),
			)
		)
	# _round_contour_groups may orient paths for measurement; winding is a
	# rendering property, so enforce it after all validation has finished.
	_ensure_opposing_round_directions(candidate)
	return candidate


def _build_c_unmatched_topology(font, master):
	"""Scale a complete C whose outer/counter arcs have unrelated topology."""
	source = _source_layer(font, "C", master.id)
	source_copy = _copy_decomposed(source)
	(
		source_outer_model,
		source_inner_model,
		source_path,
		_source_runs,
	) = _C_boundary_models(source_copy)
	signatures = _C_terminal_signatures(font, master)
	source_thickness = _boundary_model_thickness(
		source_outer_model, source_inner_model
	)
	target_thickness = source_thickness * LOWERCASE_C_STROKE_FACTOR
	source_left, source_bottom, source_right, source_top = _bounds_values(source_path)
	cap_height = float(master.capHeight)
	x_height = float(master.xHeight)
	if min(cap_height, x_height) <= EPSILON:
		raise GenerationError("The master needs positive cap and x-heights for c.")
	proportion_scale = x_height / cap_height
	width_scale = proportion_scale * LOWERCASE_C_WIDTH_FACTOR
	_baseline_position, bottom_overshoot = _master_metric_zone(
		master, GSMetricsTypeBaseline, 0.0
	)
	_x_height_position, top_overshoot = _master_metric_zone(
		master, GSMetricsTypexHeight, x_height
	)
	target_bounds = (
		source_left * width_scale,
		bottom_overshoot,
		source_right * width_scale,
		top_overshoot,
	)
	source_center = (
		(source_left + source_right) * 0.5,
		(source_bottom + source_top) * 0.5,
	)
	target_center = (
		(target_bounds[0] + target_bounds[2]) * 0.5,
		(target_bounds[1] + target_bounds[3]) * 0.5,
	)
	source_width = source_right - source_left
	source_height = source_top - source_bottom
	target_width = target_bounds[2] - target_bounds[0]
	target_height = target_bounds[3] - target_bounds[1]
	working_x = target_width / source_width
	working_y = target_height / source_height
	tolerance = max(0.75, target_thickness * 0.001)

	for _width_iteration in range(14):
		candidate = source_copy.copy()
		(
			candidate_outer_model,
			candidate_inner_model,
			candidate_path,
			candidate_runs,
		) = _C_boundary_models(candidate)
		weight_factor = LOWERCASE_C_STROKE_FACTOR
		for _weight_iteration in range(20):
			_transform_unmatched_round_boundaries(
				source_outer_model,
				source_inner_model,
				candidate_outer_model,
				candidate_inner_model,
				source_center,
				target_center,
				working_x,
				working_y,
				weight_factor,
			)
			# Intermediate cap nodes must follow their transformed boundary anchors
			# before we identify the contour again. Leaving them at source size
			# makes a valid expanded/faceted terminal look like a broken body arc.
			_apply_C_terminal_profiles(
				candidate_path, candidate_runs, signatures,
				LOWERCASE_C_TERMINAL_VERTICAL_FACTOR,
			)
			_straighten_horizontal_extrema_handles(candidate)
			# Topology does not change during fitting. Keep semantic boundary roles
			# and node references stable rather than reclassifying a temporary cap
			# while its geometry is still being compensated.
			candidate_outer_model, candidate_inner_model = tuple(
				_boundary_model_from_node_groups([
					(segment["nodes"], segment["curve"]) for segment in model
				])
				for model in (candidate_outer_model, candidate_inner_model)
			)
			measured = _boundary_model_thickness(
				candidate_outer_model, candidate_inner_model
			)
			if abs(measured - target_thickness) <= tolerance:
				break
			weight_factor *= max(
				0.95, min(1.05, target_thickness / measured)
			)
		else:
			raise GenerationError(
				"c's arbitrary-topology stroke compensation did not converge "
				"(%.2f target, %.2f measured)."
				% (target_thickness, measured)
			)
		current_left, current_bottom, current_right, current_top = _bounds_values(
			candidate_path
		)
		width_error = target_width - (current_right - current_left)
		height_error = target_height - (current_top - current_bottom)
		if abs(width_error) <= 0.25 and abs(height_error) <= 0.25:
			break
		working_x += width_error / source_width
		working_y += height_error / source_height
	else:
		raise GenerationError("c's arbitrary-topology proportions did not converge.")

	_translate_paths(
		candidate.paths,
		target_bounds[0] - current_left,
		target_bounds[1] - current_bottom,
	)
	candidate.width = round(float(source.width) * width_scale)
	_straighten_horizontal_extrema_handles(candidate)
	candidate.correctPathDirection()
	candidate.roundCoordinates()
	_straighten_horizontal_extrema_handles(candidate)
	candidate.correctPathDirection()
	return candidate


def _build_c(font, master):
	"""Scale the complete user-defined C to lowercase proportions and weight."""
	source = _source_layer(font, "C", master.id)
	source_copy = _copy_decomposed(source)
	try:
		source_groups, source_path, _source_runs = _C_contour_groups(source_copy)
	except GenerationError as error:
		if "corresponding segment topology" not in str(error):
			raise
		return _build_c_unmatched_topology(font, master)
	signatures = _C_terminal_signatures(font, master)
	source_widths = [
		_shoulder_group_thickness(group) for group in source_groups
	]
	target_widths = [
		width * LOWERCASE_C_STROKE_FACTOR for width in source_widths
	]
	source_left, source_bottom, source_right, source_top = _bounds_values(
		source_path
	)
	cap_height = float(master.capHeight)
	x_height = float(master.xHeight)
	if cap_height <= EPSILON or x_height <= EPSILON:
		raise GenerationError("The master needs positive cap and x-heights for c.")
	proportion_scale = x_height / cap_height
	width_scale = proportion_scale * LOWERCASE_C_WIDTH_FACTOR
	_baseline_position, bottom_overshoot = _master_metric_zone(
		master, GSMetricsTypeBaseline, 0.0
	)
	_x_height_position, top_overshoot = _master_metric_zone(
		master, GSMetricsTypexHeight, x_height
	)
	if top_overshoot <= bottom_overshoot + EPSILON:
		raise GenerationError(
			"The master's lowercase top and bottom overshoot zones overlap."
		)
	target_bounds = (
		source_left * width_scale,
		bottom_overshoot,
		source_right * width_scale,
		top_overshoot,
	)
	source_center = (
		(source_left + source_right) * 0.5,
		(source_bottom + source_top) * 0.5,
	)
	target_center = (
		(target_bounds[0] + target_bounds[2]) * 0.5,
		(target_bounds[1] + target_bounds[3]) * 0.5,
	)
	source_outline_width = source_right - source_left
	source_outline_height = source_top - source_bottom
	target_outline_width = target_bounds[2] - target_bounds[0]
	target_outline_height = target_bounds[3] - target_bounds[1]
	if min(
		source_outline_width,
		source_outline_height,
		target_outline_width,
		target_outline_height,
	) <= EPSILON:
		raise GenerationError("C has no measurable outline bounds for c.")
	working_x = target_outline_width / source_outline_width
	working_y = target_outline_height / source_outline_height
	compensation_widths = list(target_widths)
	validation_indices = tuple(
		range(1, len(target_widths) - 1)
		if len(target_widths) > 2
		else range(len(target_widths))
	)

	for _iteration in range(12):
		candidate = source_copy.copy()
		_transform_paths_affinely(
			candidate.paths,
			source_center,
			target_center,
			working_x,
			working_y,
		)
		target_groups, target_path, terminal_runs = _C_contour_groups(candidate)
		final_widths, tolerances = _transform_round_centerlines(
			source_groups,
			target_groups,
			source_center,
			target_center,
			working_x,
			working_y,
			compensation_widths,
			tolerance_floor=0.1,
		)
		_apply_C_terminal_profiles(
			target_path,
			terminal_runs,
			signatures,
			LOWERCASE_C_TERMINAL_VERTICAL_FACTOR,
		)
		_straighten_horizontal_extrema_handles(candidate)
		measured_groups, target_path, terminal_runs = _C_contour_groups(
			candidate
		)
		final_widths = [
			_shoulder_group_thickness(group) for group in measured_groups
		]
		tolerances = [max(0.5, width * 0.001) for width in target_widths]
		current_left, current_bottom, current_right, current_top = (
			_bounds_values(target_path)
		)
		width_error = target_outline_width - (current_right - current_left)
		height_error = target_outline_height - (current_top - current_bottom)
		weights_ok = all(
			abs(final_widths[index] - target_widths[index])
			<= tolerances[index]
			for index in validation_indices
		)
		if (
			abs(width_error) <= 0.25
			and abs(height_error) <= 0.25
			and weights_ok
		):
			break
		working_x += 0.5 * width_error / source_outline_width
		working_y += 0.5 * height_error / source_outline_height
		for index in validation_indices:
			compensation_widths[index] *= max(
				0.95,
				min(1.05, target_widths[index] / final_widths[index]),
			) ** 0.5
	else:
		raise GenerationError(
			"c's target proportions and stroke weight did not converge."
		)

	_translate_paths(
		candidate.paths,
		target_bounds[0] - current_left,
		target_bounds[1] - current_bottom,
	)
	if any(
		abs(final_widths[index] - target_widths[index]) > tolerances[index]
		for index in validation_indices
	):
		raise GenerationError(
			"c did not reach 98% of C's perpendicular stroke weight."
		)
	candidate.width = round(float(source.width) * width_scale)
	# Keep C's complete node structure—including deliberately retained line
	# detail and expanded Open Corners—rather than applying the general line-node
	# cleanup used by constructed glyphs.
	_straighten_horizontal_extrema_handles(candidate)
	candidate.correctPathDirection()
	candidate.roundCoordinates()
	_straighten_horizontal_extrema_handles(candidate)
	candidate.correctPathDirection()
	validation_groups, _validation_path, _validation_runs = _C_contour_groups(
		candidate.copy()
	)
	validation_indices = (
		range(1, len(validation_groups) - 1)
		if len(validation_groups) > 2
		else range(len(validation_groups))
	)
	for index in validation_indices:
		measured = _shoulder_group_thickness(validation_groups[index])
		tolerance = max(0.75, target_widths[index] * 0.001)
		if abs(measured - target_widths[index]) > tolerance:
			raise GenerationError(
				"c's perpendicular stroke weight changed after rounding "
				"(%.2f target, %.2f measured)."
				% (target_widths[index], measured)
			)
	return candidate


def _build_C(font, master, character):
	source_name = "O" if character == "C" else "o"
	source = _source_layer(font, source_name, master.id)
	terminal_signatures = (
		_C_terminal_signatures(font, master)
		if character == "c"
		else None
	)
	round_layer = _copy_decomposed(source)
	outer, inner = _outer_and_inner_paths(round_layer)
	body_height = float(master.capHeight if character == "C" else master.xHeight)
	bottom_cut_y = body_height / 3.0
	top_cut_y = body_height * 2.0 / 3.0

	# Work with the complete right side as an arbitrary sequence of drawable
	# segments. This preserves extra extrema and handles, faceted rounds, and
	# fully square O/o sources instead of assuming one cubic per quadrant.
	outer_top, outer_bottom = _right_top_bottom(outer)
	inner_top, inner_bottom = _right_top_bottom(inner)
	outer_right = _segment_sequence(
		_right_side_arc(outer, outer_top, outer_bottom)
	)
	inner_right = _segment_sequence(
		_right_side_arc(inner, inner_top, inner_bottom)
	)
	outer_left = _segment_sequence(
		_left_arc_nodes(outer, outer_top, outer_bottom)
	)
	inner_left = _segment_sequence(
		_left_arc_nodes(inner, inner_bottom, inner_top)
	)

	# Establish each cut on the inner contour first. C uses a local normal as its
	# initial neutral construction. Lowercase c instead inherits the direction
	# and complete line profile of the user's current uppercase C terminals.
	inner_top_to_cut, inner_after_top = _split_segment_sequence_at_y(
		inner_right, top_cut_y
	)
	_inner_middle, inner_cut_to_bottom = _split_segment_sequence_at_y(
		inner_after_top, bottom_cut_y
	)
	if not inner_top_to_cut or not inner_cut_to_bottom:
		raise GenerationError("Could not establish C's inner terminal cuts.")
	top_inner_cut = inner_top_to_cut[-1][0][3]
	bottom_inner_cut = inner_cut_to_bottom[0][0][0]
	if terminal_signatures is None:
		top_points = inner_after_top[0][0]
		bottom_points = inner_cut_to_bottom[0][0]
		top_tangent = (
			top_points[1][0] - top_points[0][0],
			top_points[1][1] - top_points[0][1],
		)
		bottom_tangent = (
			bottom_points[1][0] - bottom_points[0][0],
			bottom_points[1][1] - bottom_points[0][1],
		)
		top_cut_direction = (-top_tangent[1], top_tangent[0])
		bottom_cut_direction = (-bottom_tangent[1], bottom_tangent[0])
	else:
		top_cut_direction = terminal_signatures["top"]["direction"]
		bottom_cut_direction = terminal_signatures["bottom"]["direction"]
	outer_top_to_cut, outer_after_top = _split_segment_sequence_at_line(
		outer_right,
		top_inner_cut,
		top_cut_direction,
	)
	_outer_middle, outer_cut_to_bottom = _split_segment_sequence_at_line(
		outer_after_top,
		bottom_inner_cut,
		bottom_cut_direction,
	)
	if not outer_top_to_cut or not outer_cut_to_bottom:
		raise GenerationError("Could not establish C's outer terminal cuts.")

	path = GSPath()
	path.closed = True
	outer_cut_to_top = _reverse_segment_sequence(outer_top_to_cut)
	outer_bottom_to_cut = _reverse_segment_sequence(outer_cut_to_bottom)
	path.nodes.append(_new_node(outer_cut_to_top[0][0][0], LINE, False))
	top_outer_corner = path.nodes[-1]
	_append_segment_sequence(path, outer_cut_to_top)
	_append_segment_sequence(path, outer_left)
	_append_segment_sequence(path, outer_bottom_to_cut)
	bottom_outer_corner = path.nodes[-1]
	bottom_outer_corner.smooth = False
	if terminal_signatures is None:
		path.nodes.append(_new_node(bottom_inner_cut, LINE, False))
	else:
		bottom_profile = _terminal_profile_points(
			terminal_signatures["bottom"],
			_point(bottom_outer_corner),
			bottom_inner_cut,
		)
		bottom_profile = _extend_terminal_profile_vertically(
			bottom_profile,
			LOWERCASE_C_TERMINAL_VERTICAL_FACTOR,
		)
		bottom_outer_target = bottom_profile[0]
		_move_extreme_with_handles(
			path,
			bottom_outer_corner,
			bottom_outer_target[0] - float(bottom_outer_corner.x),
			bottom_outer_target[1] - float(bottom_outer_corner.y),
		)
		inner_cut_to_bottom = _retarget_sequence_endpoint(
			inner_cut_to_bottom,
			True,
			bottom_profile[-1],
		)
		for point in bottom_profile[1:]:
			path.nodes.append(_new_node(point, LINE, False))
	bottom_inner_corner = path.nodes[-1]
	_append_segment_sequence(path, inner_cut_to_bottom)
	_append_segment_sequence(path, inner_left)
	_append_segment_sequence(path, inner_top_to_cut)
	top_inner_corner = path.nodes[-1]
	top_inner_corner.smooth = False
	if terminal_signatures is not None:
		top_profile = _terminal_profile_points(
			terminal_signatures["top"],
			_point(top_outer_corner),
			top_inner_cut,
		)
		top_profile = _extend_terminal_profile_vertically(
			top_profile,
			LOWERCASE_C_TERMINAL_VERTICAL_FACTOR,
		)
		top_outer_target = top_profile[0]
		_move_extreme_with_handles(
			path,
			top_outer_corner,
			top_outer_target[0] - float(top_outer_corner.x),
			top_outer_target[1] - float(top_outer_corner.y),
		)
		top_inner_target = top_profile[-1]
		_move_extreme_with_handles(
			path,
			top_inner_corner,
			top_inner_target[0] - float(top_inner_corner.x),
			top_inner_target[1] - float(top_inner_corner.y),
		)
		for point in tuple(reversed(top_profile))[1:-1]:
			path.nodes.append(_new_node(point, LINE, False))

	if terminal_signatures is None:
		# C's neutral first build gets editable Open Corners. Once the user has
		# refined them, descendants copy either that expanded profile or a plain
		# two-corner terminal if the Open Corners were removed.
		for node in (
			top_outer_corner,
			bottom_outer_corner,
			bottom_inner_corner,
			top_inner_corner,
		):
			path.openCornerAtNode_offset_(node, C_OPEN_CORNER_OFFSET)
	candidate = _layer_from_paths([path], source.width)
	return _finish_candidate(candidate, remove_overlap=False)


def _S_compensated_C(source, factor_x, factor_y, measure_complete_outline=False,
	stroke_factor=1.0, terminal_node_indices=None):
	"""Resize a detached C's centerlines, retaining its measured modulation."""
	reference = _copy_decomposed(source)
	path = reference.paths[0]
	runs = ({label: tuple(path.nodes[i] for i in indices)
		for label, indices in terminal_node_indices.items()} if terminal_node_indices is not None
		else _oriented_C_terminal_runs(path)[0])
	for run in runs.values():
		_sharpen_C_terminal_corners(path, run)
	if terminal_node_indices is not None:
		runs = {label: (run[0],run[-1]) for label,run in runs.items()}
	left, bottom, right, top = _bounds_values(reference)
	center = ((left + right) * 0.5, (bottom + top) * 0.5)
	candidate = reference.copy()
	candidate_runs = ({label: tuple(candidate.paths[0].nodes[list(path.nodes).index(n)] for n in run)
		for label,run in runs.items()} if terminal_node_indices is not None
		else _complete_C_terminal_runs(candidate.paths[0])[0])
	terminal_indices = {
		label: tuple(list(candidate.paths[0].nodes).index(node) for node in run)
		for label, run in candidate_runs.items()
	}
	try:
		groups, _path, _runs = _C_contour_groups(reference, runs if terminal_node_indices is not None else None)
		targets = [_shoulder_group_thickness(group)*stroke_factor for group in groups]
		target_groups, _path, _runs = _C_contour_groups(candidate, candidate_runs if terminal_node_indices is not None else None)
		final, _tolerances = _transform_round_centerlines(
			groups, target_groups, center, center,
			factor_x, factor_y, targets,
			measure_group=(lambda group: _bowl_stem_source_weight(
				_layer_from_paths(candidate.paths, source.width), group))
				if measure_complete_outline else None,
			iteration_limit=24 if measure_complete_outline else 12,
		)
	except GenerationError as error:
		if "corresponding segment topology" not in str(error):
			raise
		outer, inner, _path, _runs = _C_boundary_models(reference, runs if terminal_node_indices is not None else None)
		target_outer, target_inner, _path, _runs = _C_boundary_models(candidate, candidate_runs if terminal_node_indices is not None else None)
		target = _boundary_model_thickness(outer, inner)*stroke_factor
		weight_factor = stroke_factor
		for _iteration in range(12):
			_transform_unmatched_round_boundaries(
				outer, inner, target_outer, target_inner,
				center, center, factor_x, factor_y, weight_factor,
			)
			measured_outer, measured_inner = tuple(
				_boundary_model_from_node_groups([
					(segment["nodes"], segment["curve"]) for segment in model
				]) for model in (target_outer, target_inner)
			)
			measured = _boundary_model_thickness(measured_outer, measured_inner)
			if abs(measured - target) <= max(0.5, target * 0.001):
				break
			weight_factor *= max(0.95, min(1.05, target / measured))
		else:
			raise GenerationError("S's C-bowl compensation did not converge.")
		targets, final = [target], [measured]
	_straighten_horizontal_extrema_handles(candidate)
	# Reattach copied paths to invalidate Glyphs' cached pre-transform bounds.
	return _layer_from_paths(candidate.paths, float(source.width)), targets, final, terminal_indices


def _S_C_bowl_arcs(body, upper, terminal_indices=None):
	"""Keep C's upper half, or reflect its lower half into S's lower bowl."""
	runs = None if terminal_indices is None else {
		label: tuple(body.paths[0].nodes[index] for index in indices)
		for label, indices in terminal_indices.items()
	}
	outer, inner, _path, _runs = _C_boundary_models(body, runs)
	result = []
	for model in (outer, inner):
		segments = [
			(segment["points"], segment["curve"],
				bool(segment["nodes"][0].smooth), bool(segment["nodes"][-1].smooth))
			for segment in model
		]
		# The left extreme is a semantic join, independently on each boundary;
		# an edited counter need not have the outer contour's node placement.
		left = min(float(p[0]) for segment in segments for p in (segment[0][0], segment[0][3]))
		middle_y = (max(float(p[1]) for segment in segments for p in (segment[0][0], segment[0][3]))
			+ min(float(p[1]) for segment in segments for p in (segment[0][0], segment[0][3]))) * 0.5
		flat_split = None
		for index, segment in enumerate(segments):
			points = segment[0]
			if (abs(points[0][0] - left) <= EPSILON
				and abs(points[3][0] - left) <= EPSILON
				and points[3][1] < middle_y < points[0][1]):
				before, after = _split_segment_sequence_at_y([segment], middle_y)
				flat_split = (segments[:index] + before, after + segments[index + 1:])
				break
		if flat_split is not None:
			result.append(flat_split[0] if upper else flat_split[1])
		else:
			join = min(range(1, len(segments)),
				key=lambda index: (abs(float(segments[index][0][0][0]) - left),
					abs(float(segments[index][0][0][1]) - middle_y)))
			result.append(segments[:join] if upper else segments[join:])
	return tuple(result)


def _S_normal_thickness(layer, center, tangent):
	"""Intersect a local normal with the nearest filled stroke boundaries."""
	length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
	if length <= EPSILON:
		raise GenerationError("S has a degenerate stroke tangent.")
	normal = (-tangent[1] / length, tangent[0] / length)
	points = layer.intersectionsBetweenPoints(
		(center[0] - normal[0] * 2000.0, center[1] - normal[1] * 2000.0),
		(center[0] + normal[0] * 2000.0, center[1] + normal[1] * 2000.0),
	)
	values = sorted((float(p.x) - center[0]) * normal[0]
		+ (float(p.y) - center[1]) * normal[1] for p in points[1:-1])
	negative = [v for v in values if v <= 0.0]
	positive = [v for v in values if v >= 0.0]
	if not negative or not positive:
		raise GenerationError("S's spine has crossing or missing stroke boundaries.")
	return min(positive) - max(negative)


def _S_C_weight(source):
	"""Measure C's thick left body stroke, away from its bowls and terminals."""
	outer, inner, _path, _runs = _C_boundary_models(source)
	left, bottom, right, top = _bounds_values(source)
	origin = ((left + right) * 0.5, (bottom + top) * 0.5)

	def center(t):
		a = _boundary_model_point(outer, t)
		b = _boundary_model_radial_point(inner, origin, a)
		return _lerp(a, b, 0.5)

	weights = []
	# Near a faceted, high-contrast bowl a radial correspondence can point at
	# the neighboring stroke instead of the intended side. The central body
	# samples measure the left-side reference used by this recipe, not the caps.
	for step in range(5, 12):
		t = step / 16.0
		before, after = center(t - 0.002), center(t + 0.002)
		weights.append(_S_normal_thickness(source, center(t),
			(after[0] - before[0], after[1] - before[1])))
	return max(weights)


def _S_extend_terminal(outer, inner, at_start, shift_y, source_path, source_run):
	"""Lengthen the terminal and preserve C's cut angle relative to its stroke.

	Open Corner expansion points are not curve anchors. Read their actual cut
	line, then reopen both corners after constructing the unexpanded outline.
	"""
	index, anchor, handle = (0, 0, 1) if at_start else (-1, 3, 2)
	run = list(source_run)
	a, b = max(zip(run, run[1:]),
		key=lambda pair: (pair[1].x - pair[0].x) ** 2 + (pair[1].y - pair[0].y) ** 2)
	cut = (float(b.x - a.x), float(b.y - a.y))
	source_anchors = _C_terminal_curve_endpoints(source_path, run)
	source_tangents = []
	for node in source_anchors:
		neighbor = next(n for n in _adjacent_nodes(source_path, node) if n not in run)
		source_tangents.append((float(neighbor.x - node.x), float(neighbor.y - node.y)))
	old_tangent = tuple(sum(v[i] for v in source_tangents) for i in (0, 1))
	old_length = (old_tangent[0] ** 2 + old_tangent[1] ** 2) ** 0.5
	cut_length = (cut[0] ** 2 + cut[1] ** 2) ** 0.5
	# Express C's cut in its own tangent/normal frame.
	along = (cut[0] * old_tangent[0] + cut[1] * old_tangent[1]) / (cut_length * old_length)
	across = _cross(old_tangent, cut) / (cut_length * old_length)
	points = [list(sequence[index][0]) for sequence in (outer, inner)]
	for p in points:
		p[anchor] = (p[anchor][0], p[anchor][1] + shift_y)
		p[handle] = (p[handle][0], p[handle][1] + shift_y * 0.4)
	tangent = tuple(sum(p[handle][i] - p[anchor][i] for p in points) for i in (0, 1))
	length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
	unit = (tangent[0] / length, tangent[1] / length)
	direction = (along * unit[0] - across * unit[1],
		along * unit[1] + across * unit[0])
	center = _lerp(points[0][anchor], points[1][anchor], 0.5)
	gap = tuple(points[1][anchor][i] - points[0][anchor][i] for i in (0, 1))
	thickness = (gap[0] ** 2 + gap[1] ** 2) ** 0.5
	if gap[0] * direction[0] + gap[1] * direction[1] < 0:
		direction = (-direction[0], -direction[1])
	for side, p in zip((-0.5, 0.5), points):
		new_anchor = tuple(center[i] + side * thickness * direction[i] for i in (0, 1))
		p[handle] = tuple(p[handle][i] + new_anchor[i] - p[anchor][i] for i in (0, 1))
		p[anchor] = new_anchor
	result = []
	for sequence, p in zip((outer, inner), points):
		sequence = list(sequence)
		sequence[index] = (tuple(p),) + sequence[index][1:]
		result.append(sequence)
	return tuple(result)


def _S_pull_join_handle(sequence, at_start):
	"""Shorten the outer bowl's vertical join handle without moving its extreme."""
	sequence = list(sequence)
	index, anchor, handle = (0, 0, 1) if at_start else (-1, 3, 2)
	points = list(sequence[index][0])
	points[handle] = _lerp(points[anchor], points[handle], S_OUTER_SHOULDER_HANDLE_FACTOR)
	sequence[index] = (tuple(points),) + sequence[index][1:]
	return sequence


def _S_set_side_width(outer, inner, at_start, width):
	"""Set a bowl/spine join's horizontal weight and retain vertical tangents."""
	index, anchor = (0, 0) if at_start else (-1, 3)
	a, b = outer[index][0][anchor], inner[index][0][anchor]
	center_x = (a[0] + b[0]) * 0.5
	width = max(1, round(width))
	left_x = round(center_x - width * 0.5)
	outer_x, inner_x = ((left_x, left_x + width) if a[0] < b[0]
		else (left_x + width, left_x))
	return (
		_retarget_sequence_endpoint(outer, at_start, (outer_x, a[1])),
		_retarget_sequence_endpoint(inner, at_start, (inner_x, b[1])),
	)


def _S_spine(upper_outer, upper_inner, lower_outer, lower_inner, target):
	"""One cubic per side; vertical extrema handles, no intermediate nodes."""
	starts = (upper_inner[-1][0][3], upper_outer[-1][0][3])
	ends = (lower_outer[0][0][0], lower_inner[0][0][0])
	start, end = _lerp(*starts, 0.5), _lerp(*ends, 0.5)
	dx, dy = end[0] - start[0], start[1] - end[1]
	if min(dx, dy) <= EPSILON:
		raise GenerationError("C's bowls leave no room for S's spine.")
	# Longer vertical spine handles flatten the middle, matching the edited S.
	# Compensation below preserves weight around this revised centerline.
	centerline = (start, (start[0], start[1] - dy * (0.59 + S_SPINE_HANDLE_REACH)),
		(end[0], end[1] + dy * (0.575 + S_SPINE_HANDLE_REACH)), end)
	tangent = _cubic_tangent(centerline, 0.5)
	length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
	normal = (-tangent[1] / length, tangent[0] / length)

	def boundaries(spread):
		result = []
		for side, a, b in zip((0.5, -0.5), starts, ends):
			result.append((a,
				(a[0], centerline[1][1] + a[1] - start[1] + side * spread),
				(b[0], centerline[2][1] + b[1] - end[1] + side * spread), b))
		return result

	uncompensated = boundaries(0.0)
	gap = tuple(_cubic_point(uncompensated[0], 0.5)[i]
		- _cubic_point(uncompensated[1], 0.5)[i] for i in (0, 1))
	# Initial normal projection, then exact intersections. Coupled handle shifts
	# keep the centerline and all four extrema fixed throughout compensation.
	spread = (target - sum(gap[i] * normal[i] for i in (0, 1))) / (0.75 * normal[1])
	for _iteration in range(6):
		a, b = boundaries(spread)
		path = GSPath()
		path.closed = True
		path.nodes.append(_new_node(a[0], LINE))
		_append_segment_sequence(path, [(a, True, True, True)])
		path.nodes.append(_new_node(b[3], LINE))
		_append_segment_sequence(path, [(tuple(reversed(b)), True, True, True)])
		stroke = _layer_from_paths([path], 0)
		measured = _S_normal_thickness(stroke, _cubic_point(centerline, 0.5), tangent)
		if abs(measured - target) <= max(0.25, target * 0.001):
			return ([(a, True, True, True)], [(b, True, True, True)], centerline)
		correction = max(-target * 0.05, min(target * 0.05, target - measured))
		spread += correction / (0.75 * normal[1])
	raise GenerationError("S's single-curve spine could not match C's weight.")


def _S_fit_finished_spine(candidate, spine_a, spine_b, shift_x, target):
	"""Recheck the assembled, gridded spine, keeping its centerline and joins."""
	path = candidate.paths[0]
	first = _oncurve_nodes(path)[0]
	arc = [first] + _forward_between(path, first, first)
	segments = _arc_drawable_segments(arc)
	groups = []
	for sequence in (spine_a, spine_b):
		points = tuple((p[0] + shift_x, p[1]) for p in sequence[0][0])
		choices = []
		for start, end, cubic, i, j, curve in segments:
			if not curve:
				continue
			for reversed_order in (False, True):
				ordered = tuple(reversed(cubic)) if reversed_order else cubic
				error = sum((ordered[k][axis] - points[k][axis]) ** 2
					for k in (0, 3) for axis in (0, 1))
				nodes = list(arc[i:j + 1])
				choices.append((error, list(reversed(nodes)) if reversed_order else nodes))
		error, nodes = min(choices, key=lambda item: item[0])
		if error > 4.0:
			raise GenerationError("Could not locate S's finished spine boundaries.")
		groups.append(nodes)
	centerline = tuple(_lerp(_point(a), _point(b), 0.5) for a, b in zip(*groups))
	center = _cubic_point(centerline, 0.5)
	tangent = _cubic_tangent(centerline, 0.5)
	def measure():
		return _S_normal_thickness(candidate, center, tangent)
	tolerance = max(1.0, target * 0.01)
	for _iteration in range(6):
		current = measure()
		if abs(current - target) <= tolerance:
			return current
		original = [(_point(nodes[1]), _point(nodes[2])) for nodes in groups]
		def place(delta):
			for nodes, points, sign in zip(groups, original, (1.0, -1.0)):
				for node, point in zip(nodes[1:3], points):
					node.position = (point[0], point[1] + sign * delta)
		place(0.5)
		response = (measure() - current) / 0.5
		place(0.0)
		if abs(response) <= 0.00001:
			break
		delta = max(-target * 0.05, min(target * 0.05, (target - current) / response))
		for _backtrack in range(8):
			place(delta)
			if abs(measure() - target) < abs(current - target):
				break
			place(0.0)
			delta *= 0.5
		else:
			break
		for nodes in groups:
			for node in nodes[1:3]:
				node.position = (round(float(node.x)), round(float(node.y)))
	return measure()


def _build_S(font, master):
	"""C-derived bowls and long open terminals around a clean two-curve spine."""
	source = _source_layer(font, "C", master.id)
	left, bottom, right, top = _bounds_values(source)
	upper, _targets, _final, upper_terminals = _S_compensated_C(
		source, S_WIDTH_FACTOR * S_UPPER_WIDTH_FACTOR, S_UPPER_BOWL_HEIGHT_FACTOR)
	lower, _targets, _final, lower_terminals = _S_compensated_C(
		source, S_WIDTH_FACTOR, S_BOWL_HEIGHT_FACTOR)
	_translate_paths(upper.paths, (right - left) * 0.015, top - _bounds_values(upper)[3])
	_translate_paths(lower.paths, 0.0, bottom - _bounds_values(lower)[1])
	upper_outer, upper_inner = _S_C_bowl_arcs(upper, True, upper_terminals)
	lower_outer, lower_inner = _S_C_bowl_arcs(lower, False, lower_terminals)
	reference = _copy_decomposed(source)
	source_path = reference.paths[0]
	runs, _center = _oriented_C_terminal_runs(source_path)
	extension = (top - bottom) * S_TERMINAL_EXTENSION
	upper_outer, upper_inner = _S_extend_terminal(
		upper_outer, upper_inner, True, -extension, source_path, runs["top"])
	lower_outer, lower_inner = _S_extend_terminal(
		lower_outer, lower_inner, False, extension, source_path, runs["bottom"])
	reflection_x = left + right
	lower_outer, lower_inner = tuple([
		(tuple((reflection_x - p[0], p[1]) for p in points), curve, sm0, sm1)
		for points, curve, sm0, sm1 in sequence
	] for sequence in (lower_outer, lower_inner))
	upper_outer = _straighten_sequence_endpoint_vertically(upper_outer, False)
	upper_inner = _straighten_sequence_endpoint_vertically(upper_inner, False)
	lower_outer = _straighten_sequence_endpoint_vertically(lower_outer, True)
	lower_inner = _straighten_sequence_endpoint_vertically(lower_inner, True)
	upper_outer = _S_pull_join_handle(upper_outer, False)
	lower_outer = _S_pull_join_handle(lower_outer, True)
	# These two horizontal extrema pairs follow the actual thick left-side
	# node distance in C, independently of the perpendicular spine weight.
	source_outer, source_inner = _S_C_bowl_arcs(reference, True)
	side_width = S_SIDE_WEIGHT_FACTOR * abs(
		source_outer[-1][0][3][0] - source_inner[-1][0][3][0])
	upper_outer, upper_inner = _S_set_side_width(
		upper_outer, upper_inner, False, side_width)
	lower_outer, lower_inner = _S_set_side_width(
		lower_outer, lower_inner, True, side_width)
	weight = _S_C_weight(source)
	spine_a, spine_b, centerline = _S_spine(
		upper_outer, upper_inner, lower_outer, lower_inner, weight)
	boundary_a = upper_inner + spine_a + lower_outer
	boundary_b = upper_outer + spine_b + lower_inner
	path = GSPath()
	path.closed = True
	path.nodes.append(_new_node(boundary_b[0][0][0], LINE))
	terminal_nodes = [path.nodes[0]]
	_append_segment_sequence(path, boundary_b)
	path.nodes[-1].smooth = False
	terminal_nodes.append(path.nodes[-1])
	path.nodes.append(_new_node(boundary_a[-1][0][3], LINE))
	terminal_nodes.append(path.nodes[-1])
	_append_segment_sequence(path, _reverse_segment_sequence(boundary_a))
	path.nodes[-1].smooth = False
	terminal_nodes.append(path.nodes[-1])
	# Open both corners of each terminal, not just the outer corner.
	# Faceted body corners and extra curve nodes are not terminal corners.
	for node in terminal_nodes:
		path.openCornerAtNode_offset_(node, C_OPEN_CORNER_OFFSET)
	candidate = _layer_from_paths([path], 0)
	current_left, _bottom, current_right, _top = _bounds_values(candidate)
	shift_x = left - current_left
	_translate_paths(candidate.paths, shift_x)
	candidate.width = round(current_right + shift_x + float(source.width) - right)
	candidate = _round_candidate_geometry(candidate)
	# Give each inner/outer extrema pair one shared X position, centered
	# between its two handle-pair midpoints. Keep all four handles fixed.
	# Locate the bowl extrema themselves, not the first/last green nodes. An
	# angular bowl has no handles there; extra curve subdivisions may put other
	# green nodes above the inner extreme. Neither should move spine joins.
	bowl_pairs = (
		(upper_outer, upper_inner, max),
		(lower_outer, lower_inner, min),
	)
	for outer_bowl, inner_bowl, choose in bowl_pairs:
		pair = []
		for bowl in (outer_bowl, inner_bowl):
			point = choose(
				(p for segment in bowl for p in (segment[0][0], segment[0][3])),
				key=lambda p: p[1],
			)
			target_point = (point[0] + shift_x, point[1])
			pair.append(min(_oncurve_nodes(candidate.paths[0]), key=lambda node:
				(float(node.x) - target_point[0]) ** 2 + (float(node.y) - target_point[1]) ** 2))
		if not all(all(handle.type == OFFCURVE for handle in
			_adjacent_nodes(candidate.paths[0], node)) for node in pair):
			continue
		midpoints = []
		for node in pair:
			previous, following = _adjacent_nodes(candidate.paths[0], node)
			midpoints.append((float(previous.x) + float(following.x)) * 0.5)
		shared_x = round(sum(midpoints) / len(midpoints))
		for node in pair:
			node.x = shared_x
	candidate.correctPathDirection()
	measured = _S_fit_finished_spine(candidate, spine_a, spine_b, shift_x, weight)
	if abs(measured - weight) > max(1.0, weight * 0.01):
		raise GenerationError("S's rounded spine lost C's perpendicular weight (%.2f / %.2f)."
			% (measured, weight))
	return candidate


def _s_terminal_runs(path):
	"""Find S's two stroke caps, including Open Corners and all-line models.

	A terminal turns from one stroke boundary onto the opposite boundary. Score
	that reversal and the transverse cut, not a fixed node count or handle type.
	"""
	oncurves = _oncurve_nodes(path)
	if len(oncurves) < 6:
		raise GenerationError("S needs a closed, two-terminal stroke outline for s.")
	left = min(float(node.x) for node in oncurves)
	right = max(float(node.x) for node in oncurves)
	bottom = min(float(node.y) for node in oncurves)
	top = max(float(node.y) for node in oncurves)
	center = ((left + right) * 0.5, (bottom + top) * 0.5)
	width, height = right - left, top - bottom
	candidates = {"top": [], "bottom": []}
	for index, start in enumerate(oncurves):
		run = [start]
		for count in range(1, len(oncurves) - 3):
			end = oncurves[(index + count) % len(oncurves)]
			if end.type != LINE:
				break
			run.append(end)
			midpoint = _lerp(_point(start), _point(end), 0.5)
			if midpoint[0] > center[0] + width * 0.05 and midpoint[1] > center[1] + height * 0.05:
				label = "top"
			elif midpoint[0] < center[0] - width * 0.05 and midpoint[1] < center[1] - height * 0.05:
				label = "bottom"
			else:
				continue
			previous = _adjacent_nodes(path, start)[0]
			following = _adjacent_nodes(path, end)[1]
			vectors = (
				(float(start.x - previous.x), float(start.y - previous.y)),
				(float(following.x - end.x), float(following.y - end.y)),
				(float(end.x - start.x), float(end.y - start.y)),
			)
			lengths = [(vector[0] ** 2 + vector[1] ** 2) ** 0.5 for vector in vectors]
			if min(lengths) <= EPSILON or lengths[2] > min(width, height) * 0.45:
				continue
			incoming, outgoing, cut = [
				(vector[0] / length, vector[1] / length)
				for vector, length in zip(vectors, lengths)
			]
			reversal = -(incoming[0] * outgoing[0] + incoming[1] * outgoing[1])
			transverse = (abs(_cross(incoming, cut)) + abs(_cross(outgoing, cut))) * 0.5
			if reversal < 0.25 or transverse < 0.4:
				continue
			curve_anchors = int(previous.type == OFFCURVE) + int(following.type == OFFCURVE)
			score = 2.0 * reversal + transverse + curve_anchors - count * 0.001
			candidates[label].append((score, tuple(run)))
	if not all(candidates.values()):
		raise GenerationError("Could not identify S's upper-right and lower-left terminals.")
	return {label: max(items, key=lambda item: item[0])[1] for label, items in candidates.items()}


def _s_body_models(layer):
	closed = [path for path in layer.paths if path.closed]
	if len(closed) != 1 or len(layer.paths) != 1:
		raise GenerationError("S needs one closed stroke contour to build s.")
	path = closed[0]
	runs = _s_terminal_runs(path)
	top, bottom = runs["top"], runs["bottom"]
	first_arc = [top[-1]] + _forward_between(path, top[-1], bottom[0])
	reverse_arc = [bottom[-1]] + _forward_between(path, bottom[-1], top[0])
	def groups(arc, reverse=False):
		result = [
			(list(arc[segment[3]:segment[4] + 1]), bool(segment[5]))
			for segment in _arc_drawable_segments(arc)
		]
		if reverse:
			result = [(list(reversed(nodes)), curve) for nodes, curve in reversed(result)]
		merged = []
		for nodes, curved in result:
			if merged and not curved and not merged[-1][1] and _s_collinear(
				_point(merged[-1][0][0]), _point(nodes[0]), _point(nodes[-1])):
				# One virtual measurement segment; all actual nodes are retained.
				merged[-1] = ([merged[-1][0][0], nodes[-1]], False)
			else:
				merged.append((nodes, curved))
		return merged
	return groups(first_arc), groups(reverse_arc, True), path, runs


def _s_contour_groups(layer):
	first, second, path, runs = _s_body_models(layer)
	if not first or len(first) != len(second):
		raise GenerationError("S's two stroke boundaries have unmatched segment topology.")
	return [
		(a, b, (curve_a, curve_b))
		for (a, curve_a), (b, curve_b) in zip(first, second)
	], path, runs


def _s_terminal_signatures(runs):
	result = {}
	for label, run in runs.items():
		a, b = _point(run[0]), _point(run[-1])
		dx, dy = b[0] - a[0], b[1] - a[1]
		length = (dx * dx + dy * dy) ** 0.5
		axis = (dx / length, dy / length)
		normal = (-axis[1], axis[0])
		result[label] = {"points": tuple(
			(((node.x - a[0]) * axis[0] + (node.y - a[1]) * axis[1]) / length,
			 ((node.x - a[0]) * normal[0] + (node.y - a[1]) * normal[1]) / length)
			for node in run
		)}
	return result


def _s_align_source_tangents(source_path, target_path, factor_x, factor_y):
	"""Retain smooth source joins without imposing smoothness on angular S's."""
	for source_node, node in zip(source_path.nodes, target_path.nodes):
		if source_node.type == OFFCURVE or not source_node.smooth:
			continue
		previous, following = _adjacent_nodes(source_path, source_node)
		if previous.type != OFFCURVE or following.type != OFFCURVE:
			continue
		incoming = (source_node.x - previous.x, source_node.y - previous.y)
		outgoing = (following.x - source_node.x, following.y - source_node.y)
		lengths = [(v[0] ** 2 + v[1] ** 2) ** 0.5 for v in (incoming, outgoing)]
		if min(lengths) <= EPSILON:
			continue
		# A flagged but deliberately non-collinear source join is copied as drawn.
		if abs(_cross(incoming, outgoing)) / (lengths[0] * lengths[1]) > 0.01:
			continue
		tangent = (
			(incoming[0] / lengths[0] + outgoing[0] / lengths[1]) * factor_x,
			(incoming[1] / lengths[0] + outgoing[1] / lengths[1]) * factor_y,
		)
		length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
		if length <= EPSILON:
			continue
		unit = (tangent[0] / length, tangent[1] / length)
		for handle in _adjacent_nodes(target_path, node):
			projection = (handle.x - node.x) * unit[0] + (handle.y - node.y) * unit[1]
			handle.x = node.x + projection * unit[0]
			handle.y = node.y + projection * unit[1]
	_s_restore_collinear_nodes(source_path, target_path)


def _s_collinear(a, b, c):
	first, second = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
	length = ((first[0] ** 2 + first[1] ** 2) * (second[0] ** 2 + second[1] ** 2)) ** 0.5
	return length <= EPSILON or (abs(_cross(first, second)) <= length * 1e-8
		and first[0] * second[0] + first[1] * second[1] > 0.0)


def _s_restore_collinear_nodes(source_path, target_path):
	"""Extra nodes along straight edges follow that edge, rather than add joins."""
	nodes = list(source_path.nodes)
	extra = set()
	for index, node in enumerate(nodes):
		previous, following = nodes[index - 1], nodes[(index + 1) % len(nodes)]
		if node.type == LINE and following.type == LINE and previous.type != OFFCURVE:
			if _s_collinear(_point(previous), _point(node), _point(following)):
				extra.add(index)
	if len(extra) == len(nodes):
		return
	for index in extra:
		left, right = (index - 1) % len(nodes), (index + 1) % len(nodes)
		while left in extra:
			left = (left - 1) % len(nodes)
		while right in extra:
			right = (right + 1) % len(nodes)
		a, b, p = _point(nodes[left]), _point(nodes[right]), _point(nodes[index])
		dx, dy = b[0] - a[0], b[1] - a[1]
		length_squared = dx * dx + dy * dy
		factor = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / max(EPSILON, length_squared)
		position = _lerp(_point(target_path.nodes[left]), _point(target_path.nodes[right]), factor)
		target_path.nodes[index].x, target_path.nodes[index].y = position


def _s_normal_opposite(model, point, tangent):
	"""Find the nearest opposite boundary on this local stroke normal."""
	hits = []
	for segment in model:
		def signed_distance(t):
			p = _cubic_point(segment["points"], t)
			return (p[0] - point[0]) * tangent[0] + (p[1] - point[1]) * tangent[1]
		last_t, last_value = 0.0, signed_distance(0.0)
		for step in range(1, 49):
			t = step / 48.0
			value = signed_distance(t)
			if last_value * value < 0.0 or min(abs(value), abs(last_value)) < 1e-7:
				lo, hi = last_t, t
				if abs(last_value) < 1e-7:
					hi = lo
				elif abs(value) < 1e-7:
					lo = hi
				else:
					for _iteration in range(28):
						middle = (lo + hi) * 0.5
						if signed_distance(lo) * signed_distance(middle) <= 0.0:
							hi = middle
						else:
							lo = middle
				p = _cubic_point(segment["points"], (lo + hi) * 0.5)
				distance = ((p[0] - point[0]) ** 2 + (p[1] - point[1]) ** 2) ** 0.5
				hits.append((distance, p))
			last_t, last_value = t, value
	if not hits:
		raise GenerationError("Cannot pair S's stroke boundaries along a normal.")
	return min(hits, key=lambda item: item[0])[1]


def _s_normal_models(layer):
	first, second, path, runs = _s_body_models(layer)
	return [_boundary_model_from_node_groups(groups) for groups in (first, second)], path, runs


def _s_normal_widths(layer, models):
	"""Sample each actual source segment, independent of opposite node count."""
	widths = []
	for side, model in enumerate(models):
		values = []
		for segment in model:
			samples = []
			for t in (0.35, 0.5, 0.65):
				p = _cubic_point(segment["points"], t)
				tangent = _cubic_tangent(segment["points"], t)
				q = _s_normal_opposite(models[1 - side], p, tangent)
				samples.append(_S_normal_thickness(layer, _lerp(p, q, 0.5), tangent))
			values.append(sorted(samples)[1])
		widths.append(values)
	return widths


def _s_transform_normals(reference, candidate, source_center, target_center, factor_x, factor_y):
	"""Compensate unequal topologies without adding, deleting or guessing nodes."""
	source_models, source_path, source_runs = _s_normal_models(reference)
	source_widths = _s_normal_widths(reference, source_models)
	factors = [[LOWERCASE_S_STROKE_FACTOR for segment in model] for model in source_models]
	signatures = _s_terminal_signatures(source_runs)
	for _iteration in range(12):
		target_models, path, runs = _s_normal_models(candidate)
		proposals = {}
		for side, model in enumerate(source_models):
			for index, segment in enumerate(model):
				samples = []
				for t in (0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0):
					p = _cubic_point(segment["points"], t)
					tangent = _cubic_tangent(segment["points"], t)
					if index == 0 and t == 0.0:
						q = source_models[1 - side][0]["points"][0]
					elif index == len(model) - 1 and t == 1.0:
						q = source_models[1 - side][-1]["points"][-1]
					else:
						# Probe just inside a segment at sharp corners, where the
						# endpoint normal can miss the finite opposite boundary.
						probe_t = max(0.002, min(0.998, t))
						probe = _cubic_point(segment["points"], probe_t)
						q = _s_normal_opposite(source_models[1 - side], probe,
							_cubic_tangent(segment["points"], probe_t))
						q = (q[0] + p[0] - probe[0], q[1] + p[1] - probe[1])
					center = _lerp(p, q, 0.5)
					half = (p[0] - center[0], p[1] - center[1])
					length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
					if length <= EPSILON:
						raise GenerationError("S has a zero-length stroke tangent.")
					unit = (tangent[0] / length, tangent[1] / length)
					normal = (-unit[1], unit[0])
					mapped = (factor_x * unit[0], factor_y * unit[1])
					mapped_length = (mapped[0] ** 2 + mapped[1] ** 2) ** 0.5
					mapped_unit = (mapped[0] / mapped_length, mapped[1] / mapped_length)
					mapped_normal = (-mapped_unit[1], mapped_unit[0])
					along = (half[0] * unit[0] + half[1] * unit[1]) * mapped_length
					across = (half[0] * normal[0] + half[1] * normal[1]) * factors[side][index]
					samples.append((
						target_center[0] + (center[0] - source_center[0]) * factor_x
						+ along * mapped_unit[0] + across * mapped_normal[0],
						target_center[1] + (center[1] - source_center[1]) * factor_y
						+ along * mapped_unit[1] + across * mapped_normal[1],
					))
				start, p, q, end = samples
				positions = [start, end]
				if segment["curve"]:
					# Fit the existing cubic through its two compensated samples.
					r = [27.0 * p[k] - 8.0 * start[k] - end[k] for k in (0, 1)]
					u = [27.0 * q[k] - start[k] - 8.0 * end[k] for k in (0, 1)]
					positions = [start, tuple((2.0 * r[k] - u[k]) / 18.0 for k in (0, 1)),
						tuple((2.0 * u[k] - r[k]) / 18.0 for k in (0, 1)), end]
				for node, position in zip(target_models[side][index]["nodes"], positions):
					proposals.setdefault(node.index, (node, []))[1].append(position)
		for node, positions in proposals.values():
			node.x = sum(p[0] for p in positions) / len(positions)
			node.y = sum(p[1] for p in positions) / len(positions)
		_s_align_source_tangents(source_path, path, factor_x, factor_y)
		for label, run in runs.items():
			points = _terminal_profile_points(signatures[label], _point(run[0]), _point(run[-1]))
			for node, point in zip(run[1:-1], points[1:-1]):
				node.x, node.y = point
		measured = _s_normal_widths(candidate, _s_normal_models(candidate)[0])
		if all(abs(current - source * LOWERCASE_S_STROKE_FACTOR) <= max(1.0, source * 0.001)
			for values, sources in zip(measured, source_widths) for current, source in zip(values, sources)):
			return
		for side, values in enumerate(measured):
			for index, current in enumerate(values):
				factors[side][index] *= max(0.95, min(1.05,
					source_widths[side][index] * LOWERCASE_S_STROKE_FACTOR / current))
	raise GenerationError("s's local normal-based stroke compensation did not converge.")


def _build_s(font, master):
	"""Resize the user's S, preserving its topology, modulation and open caps."""
	source = _source_layer(font, "S", master.id)
	reference = _copy_decomposed(source)
	reference.correctPathDirection()
	first, second, _path, source_runs = _s_body_models(reference)
	if not first or not second:
		raise GenerationError("S needs two measurable stroke boundaries to build s.")
	matched = len(first) == len(second)
	source_groups = None
	target_widths = None
	if matched:
		source_groups = _s_contour_groups(reference)[0]
		try:
			target_widths = [_shoulder_group_thickness(group) * LOWERCASE_S_STROKE_FACTOR
				for group in source_groups]
		except GenerationError:
			# Equal counts do not guarantee corresponding node positions.
			matched = False
	signatures = _s_terminal_signatures(source_runs)
	left, bottom, right, top = _bounds_values(reference)
	cap_height, x_height = float(master.capHeight), float(master.xHeight)
	if min(cap_height, x_height, right - left, top - bottom) <= EPSILON:
		raise GenerationError("S and its master need positive dimensions for s.")
	width_scale = x_height / cap_height * LOWERCASE_S_WIDTH_FACTOR
	_baseline, target_bottom = _master_metric_zone(master, GSMetricsTypeBaseline, 0.0)
	_x_height, target_top = _master_metric_zone(master, GSMetricsTypexHeight, x_height)
	source_center = ((left + right) * 0.5, (bottom + top) * 0.5)
	target_center = (source_center[0] * width_scale, (target_bottom + target_top) * 0.5)
	target_width, target_height = (right - left) * width_scale, target_top - target_bottom
	working_x, working_y = width_scale, target_height / (top - bottom)
	for _iteration in range(8):
		candidate = reference.copy()
		if matched:
			groups, path, runs = _s_contour_groups(candidate)
			try:
				_transform_round_centerlines(
					source_groups, groups, source_center, target_center,
					working_x, working_y, target_widths,
					align_tangents=lambda: _s_align_source_tangents(
						_path, path, working_x, working_y),
				)
			except GenerationError:
				matched = False
				candidate = reference.copy()
		if not matched:
			_s_transform_normals(reference, candidate,
				source_center, target_center, working_x, working_y)
			_first, _second, path, runs = _s_body_models(candidate)
		# Keep every cap node, including the user's expanded Open Corners.
		for label, run in runs.items():
			profile = _terminal_profile_points(signatures[label], _point(run[0]), _point(run[-1]))
			for node, point in zip(run[1:-1], profile[1:-1]):
				node.x, node.y = point
		# Detached Glyphs layers can retain cached pre-transform bounds.
		candidate = _layer_from_paths(candidate.paths, candidate.width)
		current_left, current_bottom, current_right, current_top = _bounds_values(candidate)
		width_error = target_width - (current_right - current_left)
		height_error = target_height - (current_top - current_bottom)
		if max(abs(width_error), abs(height_error)) <= 0.25:
			break
		working_x += width_error / (right - left)
		working_y += height_error / (top - bottom)
	else:
		raise GenerationError("s's compensated proportions did not converge.")
	_translate_paths(candidate.paths, left * width_scale - current_left, target_bottom - current_bottom)
	candidate.width = round(float(source.width) * width_scale)
	candidate = _round_candidate_geometry(candidate)
	candidate.correctPathDirection()
	return candidate


def _build_Q(font, master):
	"""Build Q from a live O component and an H-horizontal-weight tail."""
	O_source = _source_layer(font, "O", master.id)
	H_source = _source_layer(font, "H", master.id)
	O_copy = _copy_decomposed(O_source)
	outer, inner = _outer_and_inner_paths(O_copy)
	outer_left, outer_bottom, outer_right, outer_top = _bounds_values(outer)
	inner_left, inner_bottom, inner_right, inner_top = _bounds_values(inner)
	outer_width = outer_right - outer_left
	outer_height = outer_top - outer_bottom
	counter_width = inner_right - inner_left
	counter_height = inner_top - inner_bottom
	if min(outer_width, outer_height, counter_width, counter_height) <= EPSILON:
		raise GenerationError("O needs measurable outer and inner contours for Q.")

	_H_copy, _left_stem, _right_stem, crossbar = _measure_H_source(
		H_source, master
	)
	# Extruding this amount along the diagonal's normal makes its true
	# perpendicular weight exactly H's horizontal stem thickness.
	tail_thickness = float(crossbar[1]) - float(crossbar[0])
	if tail_thickness <= EPSILON:
		raise GenerationError("H's horizontal stem has no measurable thickness.")

	# Preserve Q's existing 45-degree centerline. Its inner terminal is centered
	# in O's counter; solve the other endpoint so the finished outline, including
	# half its perpendicular thickness, still ends at O's rightmost ink.
	start = (
		(inner_left + inner_right) * 0.5,
		(inner_bottom + inner_top) * 0.5,
	)
	unit = (2.0 ** -0.5, -(2.0 ** -0.5))
	half = tail_thickness * 0.5
	normal = (-unit[1] * half, unit[0] * half)
	end_center_x = outer_right - abs(normal[0])
	centerline_length = (end_center_x - start[0]) / unit[0]
	if centerline_length <= EPSILON:
		raise GenerationError("O's counter leaves no room for Q's diagonal tail.")
	end = (
		start[0] + unit[0] * centerline_length,
		start[1] + unit[1] * centerline_length,
	)
	dx = end[0] - start[0]
	dy = end[1] - start[1]
	length = (dx * dx + dy * dy) ** 0.5
	if length <= EPSILON:
		raise GenerationError("Could not establish Q's diagonal tail direction.")
	normal = (-dy / length * half, dx / length * half)
	tail = GSPath()
	tail.closed = True
	for point in (
		(start[0] + normal[0], start[1] + normal[1]),
		(end[0] + normal[0], end[1] + normal[1]),
		(end[0] - normal[0], end[1] - normal[1]),
		(start[0] - normal[0], start[1] - normal[1]),
	):
		tail.nodes.append(_new_node(point, LINE))
	# Match O's filled contour winding. This reverses the old tail direction
	# that produced a knockout where the two shapes overlapped.
	if _path_signed_area(tail) * _path_signed_area(outer) < 0.0:
		tail.reverse()
	# Reposition the intact rectangle by its terminal centers: the inner end
	# sits just below the counter center, the outer end halfway down the
	# descender. Solve its rotation from these heights, keeping length/weight.
	placed_start = (
		start[0] - outer_width * 0.10,
		start[1] - counter_height * Q_TAIL_COUNTER_DROP_FACTOR,
	)
	lower_y = float(master.descender) * 0.5
	vertical_span = placed_start[1] - lower_y
	# Extremely condensed O outlines cannot reach both anchors at this fixed
	# length. Approach the lower anchor without stretching or going vertical.
	vertical_span = max(0.0, min(length * 0.99, vertical_span))
	placed_unit = ((1.0 - (vertical_span / length) ** 2) ** 0.5,
		-vertical_span / length)
	placed_normal = (-placed_unit[1], placed_unit[0])
	for node in tail.nodes:
		x, y = float(node.x) - start[0], float(node.y) - start[1]
		along = x * unit[0] + y * unit[1]
		across = -x * unit[1] + y * unit[0]
		node.position = (
			placed_start[0] + along * placed_unit[0] + across * placed_normal[0],
			placed_start[1] + along * placed_unit[1] + across * placed_normal[1],
		)
	candidate = GSLayer()
	component = GSComponent("O")
	try:
		component.automaticAlignment = False
	except Exception:
		pass
	candidate.shapes.append(component)
	candidate.shapes.append(tail)
	tail_right = max(float(node.x) for node in tail.nodes)
	right_sidebearing = max(0.0, float(O_source.width) - outer_right)
	candidate.width = round(
		max(float(O_source.width), tail_right + right_sidebearing)
	)
	return candidate


def _build_G(font, master):
	"""Place an intact C plus an H-horizontal bar and a terminal-width join."""
	C_source = _source_layer(font, "C", master.id)
	H_source = _source_layer(font, "H", master.id)
	candidate = _copy_decomposed(C_source)
	if len(candidate.paths) != 1 or not candidate.paths[0].closed:
		raise GenerationError(
			"C must have one closed contour to build G."
		)
	path = candidate.paths[0]
	terminal_runs, _center = _oriented_C_terminal_runs(path)
	source_bottom = terminal_runs["bottom"]
	# Measure the counter from C's curve-side anchors, but leave both terminal
	# contours untouched. In particular, Open Corner nodes at the lower cut
	# must remain in G: they are part of the user's original C construction.
	top_curve_endpoints = _C_terminal_curve_endpoints(
		path, terminal_runs["top"]
	)
	lower_curve_endpoints = _C_terminal_curve_endpoints(path, source_bottom)
	measurement_runs = {
		"top": top_curve_endpoints,
		"bottom": lower_curve_endpoints,
	}
	counter_center_x = _C_counter_center_x(path, measurement_runs)
	# Meet the actual across-stroke cut, not whichever two nodes happen to be
	# last. Open Corner attachments and extra collinear nodes are not the cut.
	junction_right, junction_left = _C_terminal_cut_edge(source_bottom)
	module_right = float(junction_right.x)
	_H_copy, _left_stem, _right_stem, crossbar = _measure_H_source(
		H_source, master
	)
	bar_height = crossbar[1] - crossbar[0]
	bar_center_y = float(master.capHeight) * 0.5
	bar_bottom = bar_center_y - bar_height * 0.5
	bar_top = bar_center_y + bar_height * 0.5
	if counter_center_x >= module_right - EPSILON:
		raise GenerationError("C's counter center falls outside its filled outline.")
	horizontal_box = _rectangle_path(
		counter_center_x, bar_bottom, module_right, bar_top
	)
	if horizontal_box.direction != path.direction:
		horizontal_box.reverse()

	vertical_width = module_right - float(junction_left.x)
	if vertical_width <= EPSILON:
		raise GenerationError("C's lower terminal has no measurable thickness.")
	terminal_y = float(junction_right.y)
	if abs(terminal_y - bar_center_y) <= EPSILON:
		raise GenerationError("C's lower terminal coincides with G's bar center.")
	# Follow the actual lower cut, whether flat or angled. The one-unit overlap
	# avoids a hairline gap without changing C's nodes or either stroke angle.
	inner_x = float(junction_left.x)
	inner_y = float(junction_left.y)
	if inner_x >= module_right - EPSILON:
		raise GenerationError("C's lower terminal does not face G's vertical stroke.")
	if max(inner_y, terminal_y) >= bar_center_y - EPSILON:
		raise GenerationError("C's lower terminal leaves no room for G's vertical stroke.")
	vertical_box = GSPath()
	vertical_box.closed = True
	for point in (
		(inner_x, inner_y - 1.0),
		(inner_x, bar_center_y),
		(module_right, bar_center_y),
		(module_right, terminal_y - 1.0),
	):
		vertical_box.nodes.append(_new_node(point, LINE))
	if vertical_box.direction != path.direction:
		vertical_box.reverse()

	# Keep all three modules independent. This reproduces the placement recipe
	# literally and leaves their overlaps available for later manual refinement.
	candidate.shapes.append(horizontal_box)
	candidate.shapes.append(vertical_box)
	candidate.width = C_source.width
	return candidate


def _build_D(font, master):
	H_source = _source_layer(font, "H", master.id)
	O_source = _source_layer(font, "O", master.id)
	H_copy, left_stem, _right_stem, _crossbar = _measure_H_source(H_source, master)
	cap_height = float(master.capHeight)
	# Let the finished bowl overlap the stem by one unit. This makes Glyphs'
	# Boolean union dependable without visibly changing the stem width.
	join_x = left_stem[1] - 1.0
	stem = _layer_from_paths(
		[_rectangle_path(left_stem[0], 0.0, left_stem[1], cap_height)],
		0,
	)
	bowl = _copy_decomposed(O_source)
	outer, inner = _normalize_round_vertical_extrema(bowl, 0.0, cap_height)

	# Match D's actual outline width to H's actual outline width. Sidebearings
	# do not participate in this proportion. The curve itself is not scaled:
	# only the four horizontal joining segments change length.
	H_left, _H_bottom, H_right, _H_top = _bounds_values(H_copy)
	target_outline_width = round(H_right - H_left)
	right_sidebearing = float(O_source.width) - _bounds_values(O_source)[2]
	target_bowl_right = float(left_stem[0]) + target_outline_width
	target_width = round(target_bowl_right + right_sidebearing)
	_translate_paths(
		bowl.paths,
		target_bowl_right - _bounds_values(bowl)[2],
	)

	# Open both O contours at their top and bottom extrema and retain only the
	# right halves. Importantly, the inner extrema stay at the counter height;
	# moving them to cap height/baseline would collapse the joining strokes.
	outer_top_landmark, outer_bottom_landmark = _right_top_bottom(outer)
	inner_top_landmark, inner_bottom_landmark = _right_top_bottom(inner)
	outer_arc = _right_side_arc(
		outer, outer_top_landmark, outer_bottom_landmark
	)
	inner_arc = _right_side_arc(
		inner, inner_bottom_landmark, inner_top_landmark
	)
	outer_top = outer_arc[0]
	outer_bottom = outer_arc[-1]
	inner_bottom = inner_arc[0]
	inner_top = inner_arc[-1]

	# Reproduce the manual operation literally: extend all four open endpoints
	# horizontally to the stem, close the outer/inner pairs vertically, then
	# close the resulting bowl contour. The first node is LINE because the final
	# top horizontal segment closes back into it.
	bowl_path = GSPath()
	bowl_path.closed = True
	for index, node in enumerate(outer_arc):
		bowl_path.nodes.append(
			_copy_node(
				node,
				LINE if index == 0 else node.type,
				node.smooth,
			)
		)
	bowl_path.nodes.append(_new_node((join_x, float(outer_bottom.y)), LINE))
	bowl_path.nodes.append(_new_node((join_x, float(inner_bottom.y)), LINE))
	bowl_path.nodes.append(
		_copy_node(inner_bottom, node_type=LINE, smooth=inner_bottom.smooth)
	)
	for node in inner_arc[1:]:
		bowl_path.nodes.append(
			_copy_node(node)
		)
	bowl_path.nodes.append(_new_node((join_x, float(inner_top.y)), LINE))
	bowl_path.nodes.append(_new_node((join_x, float(outer_top.y)), LINE))

	candidate = GSLayer()
	for path in stem.paths:
		candidate.shapes.append(path.copy())
	candidate.shapes.append(bowl_path)
	candidate.width = target_width
	candidate = _finish_candidate(candidate)
	_straighten_horizontal_extrema_handles(candidate)
	candidate.correctPathDirection()
	if len(candidate.paths) != 2:
		raise GenerationError(
			"Merging the H stem with the right half of O did not preserve the D counter."
		)
	return candidate


def _right_bowl_arcs(layer):
	"""Isolate D's stemless right side without assuming node topology."""
	outer, inner = _outer_and_inner_paths(layer)
	outer_top, outer_bottom = _right_top_bottom(outer)
	inner_top, inner_bottom = _right_top_bottom(inner)
	outer_arc = _right_side_arc(outer, outer_top, outer_bottom)
	inner_arc = _right_side_arc(inner, inner_top, inner_bottom)
	return outer, inner, outer_arc, inner_arc


def _right_bowl_groups(layer):
	"""Return corresponding D right-side segments without assuming curves."""
	outer, inner, outer_arc, inner_arc = _right_bowl_arcs(layer)
	outer_segments = _arc_drawable_segments(outer_arc)
	inner_segments = _arc_drawable_segments(inner_arc)
	if len(outer_segments) != len(inner_segments) or not outer_segments:
		raise GenerationError(
			"D's right outer and inner bowl sides use different segment structures."
		)
	if any(
		bool(outer_segment[5]) != bool(inner_segment[5])
		for outer_segment, inner_segment in zip(
			outer_segments, inner_segments
		)
	):
		raise GenerationError(
			"D's right bowl mixes curve and line boundary segments."
		)
	groups = []
	for outer_segment, inner_segment in zip(
		outer_segments, inner_segments
	):
		outer_nodes = list(
			outer_arc[outer_segment[3]:outer_segment[4] + 1]
		)
		inner_nodes = list(
			inner_arc[inner_segment[3]:inner_segment[4] + 1]
		)
		groups.append((
			inner_nodes,
			outer_nodes,
			(bool(inner_segment[5]), bool(outer_segment[5])),
		))
	return groups, outer, inner, outer_arc, inner_arc


def _right_arc_boundary_model(arc):
	groups = []
	for segment in _arc_drawable_segments(arc):
		groups.append((
			list(arc[segment[3]:segment[4] + 1]),
			bool(segment[5]),
		))
	return _boundary_model_from_node_groups(groups)


def _pull_bowl_shoulders_left(path, arc, join_x, factor=PB_BOWL_SHOULDER_PULL):
	"""Round a compressed bowl by pulling both curve junctions toward its stem.

	Each endpoint and its adjoining handle move as one unit, then the handle is
	pinned to the endpoint's y coordinate. The right-side extrema and all other
	D-derived nodes remain untouched, so width and compensated weight survive.
	"""
	factor = max(0.0, min(1.0, float(factor)))
	for node in (arc[0], arc[-1]):
		span = float(node.x) - float(join_x)
		if span <= EPSILON:
			continue
		_move_extreme_with_handles(path, node, dx=-span * factor)
		for neighbor in _adjacent_nodes(path, node):
			if neighbor.type == OFFCURVE:
				neighbor.y = float(node.y)
		if any(neighbor.type == OFFCURVE for neighbor in _adjacent_nodes(path, node)):
			node.smooth = True


def _restore_bowl_horizontal_handle_ratios(source_arc, target_arc):
	"""Keep D's handle reach relative to each widened P/B curve's horizontal span.

	A shoulder moved left needs a longer horizontal handle, not its old short
	reach. Otherwise a wide P pinches at the right extreme. Vertical handle
	lengths, endpoints and compensated cardinal weights stay unchanged.
	"""
	for source_segment, target_segment in zip(
		_arc_drawable_segments(source_arc), _arc_drawable_segments(target_arc)
	):
		source_nodes = list(source_arc[source_segment[3]:source_segment[4] + 1])
		target_nodes = list(target_arc[target_segment[3]:target_segment[4] + 1])
		if len(source_nodes) != 4 or len(target_nodes) != 4:
			continue
		source_span = float(source_nodes[-1].x) - float(source_nodes[0].x)
		target_span = float(target_nodes[-1].x) - float(target_nodes[0].x)
		if abs(source_span) <= EPSILON:
			continue
		for handle_index, anchor_index in ((1, 0), (2, 3)):
			target_nodes[handle_index].x = float(target_nodes[anchor_index].x) + (
				float(source_nodes[handle_index].x) - float(source_nodes[anchor_index].x)
			) * target_span / source_span


def _compensate_bowl_handles(outer_arc, inner_arc, target_widths, character="P"):
	"""Restore local-normal weight using handles, retaining nodes and tangents."""
	groups = []
	for outer_segment, inner_segment in zip(
		_arc_drawable_segments(outer_arc), _arc_drawable_segments(inner_arc)
	):
		groups.append((
			list(inner_arc[inner_segment[3]:inner_segment[4] + 1]),
			list(outer_arc[outer_segment[3]:outer_segment[4] + 1]),
			(bool(inner_segment[5]), bool(outer_segment[5])),
		))
	if len(groups) != len(target_widths):
		return
	# A polygonal D has no handles to adjust. Offset its straight edges by the
	# measured source weight and intersect those offsets at the existing corners.
	# Keep the cap/waist/baseline y landmarks fixed, and add no nodes or curves.
	if groups and all(len(i) == len(o) == 2 for i, o, _flags in groups):
		lines = []
		for (inner_nodes, outer_nodes, _flags), target in zip(groups, target_widths):
			dx = float(inner_nodes[1].x - inner_nodes[0].x)
			dy = float(inner_nodes[1].y - inner_nodes[0].y)
			length = (dx * dx + dy * dy) ** 0.5
			if length <= EPSILON:
				raise GenerationError("%s's straight bowl contains a zero-length edge." % character)
			normal = (-dy / length, dx / length)
			gap = (float(outer_nodes[0].x - inner_nodes[0].x),
				float(outer_nodes[0].y - inner_nodes[0].y))
			if normal[0] * gap[0] + normal[1] * gap[1] < 0:
				normal = (-normal[0], -normal[1])
			constant = normal[0] * float(inner_nodes[0].x) + normal[1] * float(inner_nodes[0].y) + target
			lines.append((normal, constant))
		positions = []
		for index, node in enumerate(outer_arc):
			if index in (0, len(outer_arc) - 1):
				normal, constant = lines[0 if index == 0 else -1]
				if abs(normal[0]) <= EPSILON:
					raise GenerationError("%s's straight bowl cannot meet its horizontal stroke." % character)
				positions.append(((constant - normal[1] * float(node.y)) / normal[0], float(node.y)))
			else:
				(a, b), first = lines[index - 1]
				(c, d), second = lines[index]
				determinant = a * d - b * c
				if abs(determinant) <= EPSILON:
					# Collinear subdivisions are harmless when their offsets agree.
					if abs(first - second) > 0.5:
						raise GenerationError("%s's straight bowl has incompatible collinear edges." % character)
					delta = first - a * float(node.x) - b * float(node.y)
					positions.append((float(node.x) + a * delta, float(node.y) + b * delta))
				else:
					positions.append(((first * d - b * second) / determinant,
						(a * second - first * c) / determinant))
		for node, (x, y) in zip(outer_arc, positions):
			node.x, node.y = x, y
		return
	# Mixed line/curve boundaries retain their existing line compensation; only
	# cubic groups can be adjusted by the handle pass below.
	curve_groups = [(group, target) for group, target in zip(groups, target_widths)
		if len(group[0]) == len(group[1]) == 4]
	if not curve_groups:
		return
	groups, target_widths = zip(*curve_groups)
	for _iteration in range(12):
		widths = [_shoulder_group_thickness(group) for group in groups]
		if all(abs(current - target) <= max(0.5, target * 0.001)
			for current, target in zip(widths, target_widths)):
			return
		for group, current, target in zip(groups, widths, target_widths):
			inner_nodes, outer_nodes, _flags = group
			if len(inner_nodes) != 4 or len(outer_nodes) != 4:
				continue
			inner, outer = _boundary_group_cubics(group)
			centerline = tuple(_lerp(a, b, 0.5) for a, b in zip(inner, outer))
			tangent = _cubic_tangent(centerline, 0.5)
			length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
			if length <= EPSILON:
				continue
			normal = (-tangent[1] / length, tangent[0] / length)
			gap = tuple(_cubic_point(outer, 0.5)[j] - _cubic_point(inner, 0.5)[j]
				for j in (0, 1))
			if sum(gap[j] * normal[j] for j in (0, 1)) < 0:
				normal = (-normal[0], -normal[1])
			freedoms = []
			for handle, anchor in ((1, 0), (2, 3)):
				x = float(outer_nodes[handle].x - outer_nodes[anchor].x)
				y = float(outer_nodes[handle].y - outer_nodes[anchor].y)
				length = (x * x + y * y) ** 0.5
				if length <= EPSILON:
					continue
				unit = (x / length, y / length)
				projection = sum(unit[j] * normal[j] for j in (0, 1))
				freedoms.append((handle, unit, projection))
			denominator = 0.375 * sum(item[2] ** 2 for item in freedoms)
			if denominator <= EPSILON:
				continue
			step = max(-target * 0.05, min(target * 0.05, target - current)) / denominator
			for handle, unit, projection in freedoms:
				outer_nodes[handle].x += unit[0] * projection * step
				outer_nodes[handle].y += unit[1] * projection * step
	raise GenerationError("%s's smooth-bowl handle compensation did not converge." % character)


def _transform_B_bowl_half(
	D_source,
	source_groups,
	source_inner_left,
	source_inner_bottom,
	source_inner_height,
	horizontal_scale,
	source_right_weight,
	target_outer_bottom,
	target_outer_top,
	target_inner_bottom,
	target_inner_top,
):
	"""Fit one intact D bowl half while restoring its perpendicular weight."""
	bowl = _copy_decomposed(D_source)
	(
		target_outer,
		target_inner,
		target_outer_arc,
		target_inner_arc,
	) = _right_bowl_arcs(bowl)
	if target_inner_top <= target_inner_bottom + EPSILON:
		raise GenerationError("B has no room for its counter at H's crossbar.")

	# With compatible boundaries, keep D's scaled counter literal and rebuild the
	# outside from locally measured perpendicular source weights. This is the same
	# compensation model used by P, but B changes only the vertical proportion.
	matched_succeeded = False
	if source_groups is not None:
		try:
			target_groups, _to, _ti, target_outer_arc, target_inner_arc = (
				_right_bowl_groups(bowl)
			)
			source_widths = [
				_shoulder_group_thickness(group) for group in source_groups
			]
			factor_y = (
				(target_inner_top - target_inner_bottom)
				/ source_inner_height
			)
			_transform_round_anchored_inner(
				source_groups,
				target_groups,
				(source_inner_left, source_inner_bottom),
				(source_inner_left, target_inner_bottom),
				horizontal_scale,
				factor_y,
				source_widths,
			)
			matched_succeeded = True
		except GenerationError:
			matched_succeeded = False

	if not matched_succeeded:
		# A failed iterative pass may have moved some nodes before rejecting the
		# result. Restart from an untouched D before applying the safe fallback.
		bowl = _copy_decomposed(D_source)
		(
			target_outer,
			target_inner,
			target_outer_arc,
			target_inner_arc,
		) = _right_bowl_arcs(bowl)
		# Unequal outer/counter topology (for example a cubic outside and a
		# polygonal counter) is matched by normalized boundary progress. Every
		# source node and handle survives, while an iterative local-normal check
		# restores the source's median perpendicular weight.
		source_copy = _copy_decomposed(D_source)
		_so, _si, source_outer_arc, source_inner_arc = _right_bowl_arcs(
			source_copy
		)
		source_outer_model = _right_arc_boundary_model(source_outer_arc)
		source_inner_model = _right_arc_boundary_model(source_inner_arc)
		target_outer_model = _right_arc_boundary_model(target_outer_arc)
		target_inner_model = _right_arc_boundary_model(target_inner_arc)
		source_thickness = _boundary_model_thickness(
			source_outer_model, source_inner_model
		)
		factor_y = (
			(target_inner_top - target_inner_bottom) / source_inner_height
		)
		weight_factor = 1.0
		tolerance = max(0.5, source_thickness * 0.001)
		unmatched_succeeded = False
		for _iteration in range(12):
			_transform_unmatched_round_boundaries(
				source_outer_model,
				source_inner_model,
				target_outer_model,
				target_inner_model,
				(source_inner_left, source_inner_bottom),
				(source_inner_left, target_inner_bottom),
				horizontal_scale,
				factor_y,
				weight_factor,
				anchor_inner=True,
			)
			# The waist/cap landmarks are part of the finished geometry, so include
			# their exact placement in every compensation measurement.
			for path, node, target_y in (
				(target_outer, target_outer_arc[0], target_outer_top),
				(target_outer, target_outer_arc[-1], target_outer_bottom),
				(target_inner, target_inner_arc[0], target_inner_top),
				(target_inner, target_inner_arc[-1], target_inner_bottom),
			):
				_move_extreme_with_handles(
					path, node, dy=float(target_y) - float(node.y)
				)
			target_outer_model = _right_arc_boundary_model(target_outer_arc)
			target_inner_model = _right_arc_boundary_model(target_inner_arc)
			current_thickness = _boundary_model_thickness(
				target_outer_model, target_inner_model
			)
			if abs(current_thickness - source_thickness) <= tolerance:
				unmatched_succeeded = True
				break
			if current_thickness <= EPSILON:
				break
			weight_factor *= max(
				0.95, min(1.05, source_thickness / current_thickness)
			)

	if not matched_succeeded and not unmatched_succeeded:
		# Retain a bounded cardinal-stroke fallback for pathological outlines whose
		# local normals cannot be paired reliably.
		bowl = _copy_decomposed(D_source)
		(
			target_outer,
			target_inner,
			target_outer_arc,
			target_inner_arc,
		) = _right_bowl_arcs(bowl)
		outer_left, outer_bottom, outer_right, outer_top = _bounds_values(
			target_outer
		)
		inner_left, inner_bottom, inner_right, inner_top = _bounds_values(
			target_inner
		)
		outer_height = outer_top - outer_bottom
		inner_height = inner_top - inner_bottom
		if min(outer_height, inner_height) <= EPSILON:
			raise GenerationError("D's bowl has no measurable vertical extent.")
		_transform_paths_affinely(
			[target_outer],
			(source_inner_left, outer_bottom),
			(source_inner_left, target_outer_bottom),
			horizontal_scale,
			(target_outer_top - target_outer_bottom) / outer_height,
		)
		_transform_paths_affinely(
			[target_inner],
			(source_inner_left, inner_bottom),
			(source_inner_left, target_inner_bottom),
			horizontal_scale,
			(target_inner_top - target_inner_bottom) / inner_height,
		)
		# Independent affine scaling also narrows the cardinal right stroke. Move
		# only the counter back inward so that D's original right weight is restored.
		target_outer_right = _bounds_values(target_outer)[2]
		target_inner_right = _bounds_values(target_inner)[2]
		_translate_paths(
			[target_inner],
			(target_outer_right - source_right_weight) - target_inner_right,
		)
		# Cardinal restoration is only the starting point. Re-measure the complete
		# curved stroke along its local normals and make a small bounded correction
		# by translating the intact counter horizontally.
		try:
			for _iteration in range(8):
				current_thickness = _boundary_model_thickness(
					_right_arc_boundary_model(target_outer_arc),
					_right_arc_boundary_model(target_inner_arc),
				)
				if abs(current_thickness - source_thickness) <= tolerance:
					break
				maximum_step = max(1.0, source_thickness * 0.05)
				correction = (current_thickness - source_thickness) * 0.9
				_translate_paths(
					[target_inner],
					max(-maximum_step, min(maximum_step, correction)),
				)
		except GenerationError:
			pass

	# Pin the four horizontal-stroke landmarks exactly. The compensation loop can
	# finish within sub-unit tolerance; B's shared waist must instead be identical.
	for path, node, target_y in (
		(target_outer, target_outer_arc[0], target_outer_top),
		(target_outer, target_outer_arc[-1], target_outer_bottom),
		(target_inner, target_inner_arc[0], target_inner_top),
		(target_inner, target_inner_arc[-1], target_inner_bottom),
	):
		_move_extreme_with_handles(
			path, node, dy=float(target_y) - float(node.y)
		)
	return {
		"layer": bowl,
		"outer": target_outer,
		"inner": target_inner,
		"outer_arc": target_outer_arc,
		"inner_arc": target_inner_arc,
	}


def _B_bowl_path(half, join_x):
	"""Close one transformed right bowl against H's stem overlap."""
	outer_arc = half["outer_arc"]
	inner_arc = half["inner_arc"]
	outer_sequence = _segment_sequence(outer_arc)
	inner_bottom_to_top = _reverse_segment_sequence(
		_segment_sequence(inner_arc)
	)
	path = GSPath()
	path.closed = True
	path.nodes.append(
		_new_node(outer_sequence[0][0][0], LINE, outer_arc[0].smooth)
	)
	_append_segment_sequence(path, outer_sequence)
	path.nodes.append(
		_new_node((join_x, float(outer_arc[-1].y)), LINE)
	)
	path.nodes.append(
		_new_node((join_x, float(inner_arc[-1].y)), LINE)
	)
	path.nodes.append(
		_new_node(
			inner_bottom_to_top[0][0][0], LINE, inner_arc[-1].smooth
		)
	)
	_append_segment_sequence(path, inner_bottom_to_top)
	path.nodes.append(
		_new_node((join_x, float(inner_arc[0].y)), LINE)
	)
	path.nodes.append(
		_new_node((join_x, float(outer_arc[0].y)), LINE)
	)
	return path


def _build_B(font, master):
	"""Build B from H's stem and D bowls, with a slightly narrower upper bowl."""
	D_source = _copy_decomposed(_source_layer(font, "D", master.id))
	_straighten_horizontal_extrema_handles(D_source)
	H_source = _source_layer(font, "H", master.id)
	source = _copy_decomposed(D_source)
	(
		source_outer,
		source_inner,
		source_outer_arc,
		source_inner_arc,
	) = _right_bowl_arcs(source)
	outer_left, outer_bottom, outer_right, outer_top = _bounds_values(
		source_outer
	)
	inner_left, inner_bottom, inner_right, inner_top = _bounds_values(
		source_inner
	)
	outer_height = outer_top - outer_bottom
	inner_height = inner_top - inner_bottom
	top_weight = outer_top - inner_top
	bottom_weight = inner_bottom - outer_bottom
	right_weight = outer_right - inner_right
	if min(
		outer_height,
		inner_height,
		top_weight,
		bottom_weight,
		right_weight,
	) <= EPSILON:
		raise GenerationError("D's bowl strokes have no usable thickness for B.")

	_H_copy, left_stem, _right_stem, crossbar = _measure_H_source(
		H_source, master
	)
	cap_height = float(master.capHeight)
	waist_center = (float(crossbar[0]) + float(crossbar[1])) * 0.5
	# The two D horizontal weights can differ. Their mean provides one shared
	# middle stroke; the cap and baseline retain D's respective exact weights.
	waist_weight = (top_weight + bottom_weight) * 0.5
	waist_bottom = waist_center - waist_weight * 0.5
	waist_top = waist_center + waist_weight * 0.5
	if (
		waist_bottom <= bottom_weight + EPSILON
		or waist_top >= cap_height - top_weight - EPSILON
	):
		raise GenerationError("H's crossbar leaves no room for B's two counters.")
	# Scale each counter uniformly from D. An average OUTER-height scale for x
	# combined with the smaller COUNTER-height scale for y flattens the curves,
	# especially in heavier styles. The two bowls may have different heights;
	# each needs its own x/y ratio, not a shared horizontal scale.
	upper_scale = (cap_height - top_weight - waist_top) / inner_height
	lower_scale = (waist_bottom - bottom_weight) / inner_height
	if min(upper_scale, lower_scale) <= EPSILON:
		raise GenerationError("D's bowl cannot be proportionally scaled for B.")

	try:
		source_groups = _right_bowl_groups(source)[0]
	except GenerationError:
		source_groups = None

	upper = _transform_B_bowl_half(
		D_source,
		source_groups,
		inner_left,
		inner_bottom,
		inner_height,
		upper_scale,
		right_weight,
		waist_bottom,
		cap_height,
		waist_top,
		cap_height - top_weight,
	)
	lower = _transform_B_bowl_half(
		D_source,
		source_groups,
		inner_left,
		inner_bottom,
		inner_height,
		lower_scale,
		right_weight,
		0.0,
		waist_top,
		bottom_weight,
		waist_bottom,
	)

	# Keep each scaled, compensated D curve module intact. Move the complete
	# modules outward until B's actual outline width matches H's actual outline
	# width; the four newly constructed horizontal runs absorb that extension.
	# This retains D's right-side character instead of stretching its curves.
	join_x = left_stem[1] - 1.0
	H_left, _H_bottom, H_right, _H_top = _bounds_values(_H_copy)
	target_outline_width = H_right - H_left
	target_bowl_right = left_stem[0] + target_outline_width
	for half in (upper, lower):
		current_right = _bounds_values(half["outer"])[2]
		_translate_paths(
			half["layer"].paths, target_bowl_right - current_right
		)

	# Keep D's normalized counter points and handle proportions intact. Pulling
	# endpoints toward the stem (as in P) stretches the otherwise proportional
	# B curves again. Width belongs in the horizontal connections, not the bowls.
	for half in (upper, lower):
		_restore_bowl_horizontal_handle_ratios(source_outer_arc, half["outer_arc"])
		_restore_bowl_horizontal_handle_ratios(source_inner_arc, half["inner_arc"])
		if source_groups is not None:
			_compensate_bowl_handles(half["outer_arc"], half["inner_arc"],
				[_shoulder_group_thickness(group) for group in source_groups], "B")

	# Narrow only the horizontal joins. Finish every bowl-shaping/compensation
	# step at its original width first, then translate each intact module left.
	# An integer shift also preserves every relative node/handle position after
	# the final grid rounding. The stem and shared waist landmarks stay intact.
	current_outline_width = max(
		_bounds_values(half["outer"])[2] for half in (upper, lower)
	) - left_stem[0]
	width_reduction = round(current_outline_width * (1.0 - B_WIDTH_FACTOR))
	upper_reduction = round(
		(current_outline_width - width_reduction) * (1.0 - B_UPPER_WIDTH_FACTOR)
	)
	for half in (upper, lower):
		total_reduction = width_reduction + (upper_reduction if half is upper else 0)
		if any(float(node.x) - total_reduction <= join_x + EPSILON
			for arc in (half["outer_arc"], half["inner_arc"])
			for node in (arc[0], arc[-1])):
			raise GenerationError(
				"B's horizontal joins are too short to narrow without changing its bowls."
			)
	for half in (upper, lower):
		_translate_paths(half["layer"].paths, -width_reduction)
	# Keep the compensated upper curve module unchanged; only its horizontal
	# connections to the stem become shorter. The lower bowl and advance stay put.
	_translate_paths(upper["layer"].paths, -upper_reduction)
	target_bowl_right -= width_reduction

	upper_path = _B_bowl_path(upper, join_x)
	lower_path = _B_bowl_path(lower, join_x)
	stem_path = _rectangle_path(
		left_stem[0], 0.0, left_stem[1], cap_height
	)
	for path in (upper_path, lower_path):
		if _path_signed_area(stem_path) * _path_signed_area(path) < 0.0:
			path.reverse()

	candidate = GSLayer()
	candidate.shapes.append(stem_path)
	candidate.shapes.append(upper_path)
	candidate.shapes.append(lower_path)
	right_sidebearing = max(0.0, float(H_source.width) - H_right)
	candidate.width = round(target_bowl_right + right_sidebearing)
	# Normalize winding only after the stem and both overlapping bowl modules are
	# assembled, so Glyphs evaluates their final containment relationship.
	candidate.correctPathDirection()
	return candidate


def _build_P(font, master):
	"""Build P from H's stem and D's compensated, stemless right bowl."""
	D_source = _copy_decomposed(_source_layer(font, "D", master.id))
	# Sanitize inherited extrema on this detached copy as well, so older D
	# builds cannot pass a stray bottom handle or corner flag into P.
	_straighten_horizontal_extrema_handles(D_source)
	H_source = _source_layer(font, "H", master.id)
	source = _copy_decomposed(D_source)
	(
		source_outer,
		source_inner,
		source_outer_arc,
		source_inner_arc,
	) = _right_bowl_arcs(source)
	outer_left, outer_bottom, outer_right, outer_top = _bounds_values(
		source_outer
	)
	inner_left, inner_bottom, inner_right, inner_top = _bounds_values(
		source_inner
	)
	if inner_left <= outer_left + EPSILON or inner_right >= outer_right - EPSILON:
		raise GenerationError("D's counter must sit inside its outer outline.")

	# Scaling is applied to D's bowl centerline first. Stroke thickness is then
	# restored per corresponding segment, as measured perpendicular to the curve.
	# Because P anchors the counter and grows the weight outward, its counter must
	# be slightly smaller than 60% for the *finished outer bowl* to equal a
	# symmetrically compensated 60% D. This single uniform factor keeps every
	# counter handle and node in exactly D's original proportion.
	outer_height = outer_top - outer_bottom
	inner_height = inner_top - inner_bottom
	if min(outer_height, inner_height) <= EPSILON:
		raise GenerationError("D's bowl has no measurable vertical extent.")
	centerline_height = (outer_height + inner_height) * 0.5
	desired_outer_height = (
		centerline_height * P_BOWL_SCALE
		+ (outer_height - inner_height) * 0.5
	)
	outer_scale = desired_outer_height / outer_height
	counter_scale = (
		desired_outer_height - (outer_height - inner_height)
	) / inner_height
	if counter_scale <= EPSILON:
		raise GenerationError("D's stroke is too heavy for a 60% P bowl.")
	source_center = (
		(outer_left + inner_left + outer_right + inner_right) * 0.25,
		(outer_bottom + inner_bottom + outer_top + inner_top) * 0.25,
	)
	target_center = (
		source_center[0] * counter_scale,
		source_center[1] * counter_scale,
	)
	matched_succeeded = False
	try:
		source_groups, _so, _si, _source_outer_arc, _source_inner_arc = (
			_right_bowl_groups(source)
		)
		source_widths = [
			_shoulder_group_thickness(group) for group in source_groups
		]
		bowl = _copy_decomposed(D_source)
		target_groups, target_outer, target_inner, target_outer_arc, target_inner_arc = (
			_right_bowl_groups(bowl)
		)
		_transform_round_anchored_inner(
			source_groups,
			target_groups,
			source_center,
			target_center,
			counter_scale,
			counter_scale,
			source_widths,
		)
		matched_succeeded = True
	except GenerationError:
		matched_succeeded = False

	if not matched_succeeded:
		# A curved outer path and polygonal counter have no reliable point-to-point
		# normal correspondence. Transform each contour as an intact shape instead
		# of deriving outer handles from counter edges. This preserves every handle
		# direction and uses the unambiguous top, bottom, and right cardinal strokes
		# for compensation.
		bowl = _copy_decomposed(D_source)
		(
			target_outer,
			target_inner,
			target_outer_arc,
			target_inner_arc,
		) = _right_bowl_arcs(bowl)
		_transform_paths_affinely(
			[target_outer], (0.0, 0.0), (0.0, 0.0), outer_scale, outer_scale
		)
		_transform_paths_affinely(
			[target_inner], (0.0, 0.0), (0.0, 0.0), counter_scale, counter_scale
		)
		target_outer_bounds = _bounds_values(target_outer)
		target_inner_bounds = _bounds_values(target_inner)
		source_top_weight = outer_top - inner_top
		source_bottom_weight = inner_bottom - outer_bottom
		source_right_weight = outer_right - inner_right
		if min(
			source_top_weight, source_bottom_weight, source_right_weight
		) <= EPSILON:
			raise GenerationError("D's bowl strokes have no usable thickness.")
		_translate_paths(
			[target_inner],
			(target_outer_bounds[2] - source_right_weight)
			- target_inner_bounds[2],
			(target_outer_bounds[3] - source_top_weight)
			- target_inner_bounds[3],
		)
		# The scale was solved from both vertical strokes, so aligning the top also
		# restores the bottom. Keep a guard here for irregular extrema.
		final_inner_bounds = _bounds_values(target_inner)
		if abs(
			(final_inner_bounds[1] - target_outer_bounds[1])
			- source_bottom_weight
		) > 0.5:
			raise GenerationError(
				"D's asymmetric counter cannot preserve both horizontal P strokes."
			)

	_H_copy, left_stem, _right_stem, _crossbar = _measure_H_source(
		H_source, master
	)
	cap_height = float(master.capHeight)
	join_x = left_stem[1] - 1.0
	# Keep the counter untouched and put the small endpoint correction entirely
	# on the outer boundary so D's horizontal weights remain exact.
	source_top_weight = (
		float(source_outer_arc[0].y) - float(source_inner_arc[0].y)
	)
	source_bottom_weight = (
		float(source_inner_arc[-1].y) - float(source_outer_arc[-1].y)
	)
	if min(source_top_weight, source_bottom_weight) <= EPSILON:
		raise GenerationError("D's horizontal bowl strokes have no usable thickness.")
	_move_extreme_with_handles(
		target_outer,
		target_outer_arc[0],
		dy=(float(target_inner_arc[0].y) + source_top_weight)
		- float(target_outer_arc[0].y),
	)
	_move_extreme_with_handles(
		target_outer,
		target_outer_arc[-1],
		dy=(float(target_inner_arc[-1].y) - source_bottom_weight)
		- float(target_outer_arc[-1].y),
	)
	# Keep the scaled, compensated D curve untouched and move the whole module
	# outward until P reaches 96% of H's actual ink width. Only the four
	# replacement horizontal runs change; the compensated D curve stays intact.
	H_left, _H_bottom, H_right, _H_top = _bounds_values(_H_copy)
	target_outline_width = (H_right - H_left) * P_WIDTH_FACTOR
	target_bowl_right = left_stem[0] + target_outline_width
	dx = target_bowl_right - _bounds_values(target_outer)[2]
	dy = cap_height - float(target_outer_arc[0].y)
	_translate_paths(bowl.paths, dx, dy)

	# Pull P's four curve junctions left without disturbing the right extrema or
	# compensated D-derived stroke. Moving the attached handles with the nodes,
	# then pinning their y positions, keeps every green-node tangent horizontal.
	_pull_bowl_shoulders_left(target_outer, target_outer_arc, join_x)
	_pull_bowl_shoulders_left(target_inner, target_inner_arc, join_x)
	_restore_bowl_horizontal_handle_ratios(source_outer_arc, target_outer_arc)
	_restore_bowl_horizontal_handle_ratios(source_inner_arc, target_inner_arc)
	if matched_succeeded:
		_compensate_bowl_handles(target_outer_arc, target_inner_arc, source_widths)

	# Re-read the same semantic arcs after translation, then create one stemless
	# bowl contour. The closing edges sit inside H's stem overlap, so the visible
	# result has one black silhouette and one open counter.
	outer_top = target_outer_arc[0]
	outer_bottom = target_outer_arc[-1]
	inner_top = target_inner_arc[0]
	inner_bottom = target_inner_arc[-1]
	outer_sequence = _segment_sequence(target_outer_arc)
	inner_bottom_to_top = _reverse_segment_sequence(
		_segment_sequence(target_inner_arc)
	)
	bowl_path = GSPath()
	bowl_path.closed = True
	bowl_path.nodes.append(
		_new_node(outer_sequence[0][0][0], LINE, outer_top.smooth)
	)
	_append_segment_sequence(bowl_path, outer_sequence)
	bowl_path.nodes.append(_new_node((join_x, float(outer_bottom.y)), LINE))
	bowl_path.nodes.append(_new_node((join_x, float(inner_bottom.y)), LINE))
	bowl_path.nodes.append(
		_new_node(inner_bottom_to_top[0][0][0], LINE, inner_bottom.smooth)
	)
	_append_segment_sequence(bowl_path, inner_bottom_to_top)
	bowl_path.nodes.append(_new_node((join_x, float(inner_top.y)), LINE))
	bowl_path.nodes.append(_new_node((join_x, float(outer_top.y)), LINE))

	stem_path = _rectangle_path(
		left_stem[0], 0.0, left_stem[1], cap_height
	)
	if _path_signed_area(stem_path) * _path_signed_area(bowl_path) < 0.0:
		bowl_path.reverse()
	candidate = GSLayer()
	candidate.shapes.append(stem_path)
	candidate.shapes.append(bowl_path)
	right_sidebearing = max(0.0, float(H_source.width) - H_right)
	candidate.width = round(target_bowl_right + right_sidebearing)
	return candidate


def _R_P_landmarks(P_source, master):
	"""Measure R's attachment from P's visible counter and lower bowl stroke."""
	decomposed = _copy_decomposed(P_source)
	paths = [path for path in decomposed.paths if path.closed]
	if len(paths) < 2:
		raise GenerationError("P must contain a stem and a closed bowl for R.")
	cap_height = float(master.capHeight)
	stem_candidates = []
	for path in paths:
		left, bottom, right, top = _bounds_values(path)
		if bottom <= EPSILON and top >= cap_height - EPSILON:
			stem_candidates.append((right, right - left, path))
	if not stem_candidates:
		raise GenerationError("P has no full-height stem for R.")
	stem = min(stem_candidates, key=lambda item: (item[0], item[1]))[2]
	bowl_candidates = [path for path in paths if path is not stem]
	if not bowl_candidates:
		raise GenerationError("P has no bowl contour for R.")
	bowl = max(
		bowl_candidates,
		key=lambda path: (_bounds_values(path)[2], _bounds_area(path)),
	)

	horizontal_levels = []
	for node in _oncurve_nodes(bowl):
		if node.type != LINE:
			continue
		previous = _previous_oncurve(bowl, node)
		if (
			abs(float(previous.y) - float(node.y)) <= EPSILON
			and abs(float(previous.x) - float(node.x)) > EPSILON
		):
			horizontal_levels.append(float(node.y))
	levels = []
	for value in sorted(horizontal_levels):
		if not levels or abs(value - levels[-1]) > EPSILON:
			levels.append(value)
	if len(levels) < 4:
		raise GenerationError(
			"P's bowl needs four horizontal junctions to place R's leg."
		)
	outer_bottom = levels[0]
	inner_bottom = levels[1]
	inner_top = levels[-2]
	if not (outer_bottom < inner_bottom < inner_top):
		raise GenerationError("P's lower bowl stroke is not measurable for R.")
	attachment_y = (outer_bottom + inner_bottom) * 0.5
	counter_probe_y = (inner_bottom + inner_top) * 0.5
	intersections = _scan_x_intersections(
		_layer_from_paths([bowl], 0), counter_probe_y
	)
	if len(intersections) < 2:
		raise GenerationError("P's counter is not measurable for R.")
	stem_right = _bounds_values(stem)[2]
	inner_right = intersections[-2]
	if inner_right <= stem_right + EPSILON:
		raise GenerationError("P's counter has no usable horizontal width for R.")
	counter_center = (stem_right + inner_right) * 0.5
	P_right = _bounds_values(decomposed)[2]
	right_sidebearing = max(0.0, float(P_source.width) - P_right)
	return (
		attachment_y,
		counter_center,
		P_right,
		right_sidebearing,
		stem,
	)


def _build_R(font, master):
	"""Build R as a live P component plus V's compensated left diagonal."""
	P_source = _source_layer(font, "P", master.id)
	V_source = _source_layer(font, "V", master.id)
	(
		attachment_y,
		counter_center,
		P_right,
		right_sidebearing,
		P_stem,
	) = _R_P_landmarks(P_source, master)
	leg = _build_R_leg(
		V_source,
		counter_center,
		attachment_y,
		P_right,
	)
	if _path_signed_area(leg) * _path_signed_area(P_stem) < 0.0:
		leg.reverse()

	candidate = GSLayer()
	component = GSComponent("P")
	try:
		component.automaticAlignment = False
	except Exception:
		pass
	candidate.shapes.append(component)
	candidate.shapes.append(leg)
	leg_right = _bounds_values(leg)[2]
	candidate.width = round(
		max(float(P_source.width), leg_right + right_sidebearing)
	)
	return candidate


def _set_side_extreme(path, side, target_x, target_y):
	oncurves = _oncurve_nodes(path)
	if side == "left":
		node = min(oncurves, key=lambda item: float(item.x))
	else:
		node = max(oncurves, key=lambda item: float(item.x))
	_move_extreme_with_handles(
		path,
		node,
		dx=float(target_x) - float(node.x),
		dy=float(target_y) - float(node.y),
	)
	return node


def _copy_node(node, node_type=None, smooth=None):
	return _new_node(
		_point(node),
		node.type if node_type is None else node_type,
		node.smooth if smooth is None else smooth,
	)


def _build_U(font, master):
	H_source = _source_layer(font, "H", master.id)
	O_source = _source_layer(font, "O", master.id)
	_H_copy, left_stem, right_stem, crossbar = _measure_H_source(H_source, master)
	left_weight = left_stem[1] - left_stem[0]
	horizontal_weight = float(crossbar[1]) - float(crossbar[0])
	if min(left_weight, horizontal_weight) <= EPSILON:
		raise GenerationError("H does not provide measurable stems for U.")
	contrast_ratio = horizontal_weight / left_weight
	if contrast_ratio >= U_SANS_CONTRAST_THRESHOLD:
		# Sans construction: equalize the two verticals while preserving U's
		# outside right edge and therefore its overall width.
		right_weight = left_weight
		contrast_difference = 0.0
	else:
		# Contrast construction: H's crossbar supplies the conventional thin
		# right stem; the left keeps H's heavy vertical weight.
		right_weight = horizontal_weight
		contrast_difference = left_weight - right_weight
	right_stem = (right_stem[1] - right_weight, right_stem[1])
	bowl = _copy_decomposed(O_source)
	# U inherits O's lower geometry literally, including any overshoot.  Unlike
	# D, it must not normalize O's extrema to the baseline and cap height.
	outer, inner = _outer_and_inner_paths(bowl)
	H_center = (left_stem[0] + right_stem[1]) * 0.5
	O_left, _O_bottom, O_right, _O_top = _bounds_values(outer)
	_translate_paths(bowl.paths, H_center - (O_left + O_right) * 0.5)
	inner_join_y = float(master.capHeight) * 0.5
	# Let the outside curves begin lower than the counter curves. The stagger is
	# proportional to cap height, so the U keeps the same construction across
	# masters rather than relying on a fixed-unit correction.
	outer_join_y = inner_join_y - (
		float(master.capHeight) * U_OUTER_JOIN_DROP_RATIO
	)
	outer_arc = _lower_arc_sequence(outer, outer_join_y)
	inner_arc = _reverse_segment_sequence(
		_lower_arc_sequence(inner, inner_join_y)
	)
	outer_arc = _fit_sequence_horizontally(
		outer_arc, left_stem[0], right_stem[1]
	)
	inner_arc = _fit_sequence_horizontally(
		inner_arc, right_stem[0], left_stem[1]
	)
	if contrast_difference > EPSILON:
		# A small master-specific correction makes the bottom fractionally heavier
		# than O and shifts its counter extremum toward the thin stem. Moving the
		# complete extremum feature preserves every adjacent handle relationship.
		inner_arc = _move_sequence_bottom_extrema(
			inner_arc,
			contrast_difference * U_BOTTOM_SHIFT_GAIN,
			contrast_difference * U_BOTTOM_WEIGHT_GAIN,
		)
	# The four bowl/stem junctions are smooth nodes only when the adjacent
	# curve handles are collinear with the vertical stem segments.  Setting a
	# node's smooth flag alone does not straighten its handles in Glyphs.
	outer_arc = _straighten_sequence_endpoint_vertically(outer_arc, True)
	outer_arc = _straighten_sequence_endpoint_vertically(outer_arc, False)
	inner_arc = _straighten_sequence_endpoint_vertically(inner_arc, True)
	inner_arc = _straighten_sequence_endpoint_vertically(inner_arc, False)
	if contrast_difference > EPSILON:
		inner_arc = _compensate_U_right_transition(
			outer_arc, inner_arc, right_weight
		)

	path = GSPath()
	path.closed = True
	path.nodes.append(_new_node((left_stem[0], master.capHeight), LINE))
	path.nodes.append(_new_node((left_stem[0], outer_join_y), LINE))
	_append_segment_sequence(path, outer_arc)
	path.nodes.append(_new_node((right_stem[1], master.capHeight), LINE))
	path.nodes.append(_new_node((right_stem[0], master.capHeight), LINE))
	path.nodes.append(_new_node((right_stem[0], inner_join_y), LINE))
	_append_segment_sequence(path, inner_arc)
	path.nodes.append(_new_node((left_stem[1], master.capHeight), LINE))
	candidate = _layer_from_paths([path], H_source.width)
	candidate = _finish_candidate(candidate, remove_overlap=False)
	for candidate_path in candidate.paths:
		for node in _oncurve_nodes(candidate_path):
			node.smooth = True
	return candidate


def _J_hook_groups(body, right_outer_top, right_inner_top):
	"""Pair U's complete outer/inner hook segments from left to right."""
	outer_top_index = body.index(right_outer_top)
	inner_top_index = body.index(right_inner_top)
	if outer_top_index >= inner_top_index:
		raise GenerationError("Could not orient U's right stem for J.")
	outer_join_index = next(
		(
			index for index in range(outer_top_index - 1, -1, -1)
			if body[index].type != OFFCURVE
		),
		None,
	)
	inner_join_index = next(
		(
			index for index in range(inner_top_index + 1, len(body))
			if body[index].type != OFFCURVE
		),
		None,
	)
	if outer_join_index is None or inner_join_index is None:
		raise GenerationError("Could not identify U's right bowl junctions for J.")
	outer_arc = list(body[:outer_join_index + 1])
	# Keep the inner arc in the contour's real direction for the final path.
	# Pairing reverses its segment order and each segment's node view below;
	# reversing the raw node list would leave Glyphs' incoming segment types on
	# the wrong endpoints (most visibly turning the right half into a line).
	inner_arc = list(body[inner_join_index:])
	outer_segments = _arc_drawable_segments(outer_arc)
	inner_segments = list(reversed(_arc_drawable_segments(inner_arc)))
	if len(outer_segments) != len(inner_segments) or not outer_segments:
		raise GenerationError(
			"U's inner and outer hook need matching segment topology to build J."
		)
	groups = []
	for outer_segment, inner_segment in zip(outer_segments, inner_segments):
		if bool(outer_segment[5]) != bool(inner_segment[5]):
			raise GenerationError(
				"U's inner and outer hook segments do not correspond for J."
			)
		outer_nodes = list(
			outer_arc[outer_segment[3]:outer_segment[4] + 1]
		)
		inner_nodes = list(reversed(
			inner_arc[inner_segment[3]:inner_segment[4] + 1]
		))
		if len(outer_nodes) != len(inner_nodes):
			raise GenerationError(
				"U's inner and outer hook nodes do not correspond for J."
			)
		groups.append((inner_nodes, outer_nodes, bool(outer_segment[5])))
	return groups, outer_arc, inner_arc


def _J_hook_group_thickness(group):
	"""Measure curved hooks normally, and facets away from their cap joins."""
	if group[2]:
		return _shoulder_group_thickness(group)
	inner_nodes, outer_nodes, _is_curve = group
	start = _lerp(_point(inner_nodes[0]), _point(outer_nodes[0]), 0.5)
	end = _lerp(_point(inner_nodes[-1]), _point(outer_nodes[-1]), 0.5)
	center = _lerp(start, end, 0.5)
	tangent = (end[0] - start[0], end[1] - start[1])
	length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
	if length <= EPSILON:
		raise GenerationError("J's angular hook has no measurable length.")
	normal = (-tangent[1] / length, tangent[0] / length)
	distances = []
	for nodes in (inner_nodes, outer_nodes):
		first, last = _point(nodes[0]), _point(nodes[-1])
		edge = (last[0] - first[0], last[1] - first[1])
		determinant = _cross(normal, edge)
		if abs(determinant) <= EPSILON:
			raise GenerationError("J's angular hook has an ambiguous normal.")
		relative = (first[0] - center[0], first[1] - center[1])
		factor = _cross(relative, normal) / determinant
		if not -EPSILON <= factor <= 1.0 + EPSILON:
			raise GenerationError("J's angular hook boundaries do not overlap at their middle.")
		distances.append(_cross(relative, edge) / determinant)
	return abs(distances[1] - distances[0])


def _compensate_J_curve_handles(group, target):
	"""Fit normal weight with paired tangent-preserving handle adjustments.

	A fixed ratio iteration converges too slowly after an angled C cut. Fit the
	actual response instead, keeping both endpoints and paired handle centers
	fixed. Bounded steps and backtracking prevent overshoots or reversed handles.
	"""
	inner_nodes, outer_nodes, _is_curve = group
	tolerance = max(0.25, target * 0.001)
	pairs = []
	for index, anchor_index in ((1, 0), (2, 3)):
		pair = []
		for nodes, sign in ((inner_nodes, 1.0), (outer_nodes, -1.0)):
			anchor = _point(nodes[anchor_index])
			point = _point(nodes[index])
			handle = tuple(point[i] - anchor[i] for i in range(2))
			reach = (handle[0] ** 2 + handle[1] ** 2) ** 0.5
			if reach <= EPSILON:
				raise GenerationError("J's hook contains a zero-length handle.")
			unit = tuple(value / reach for value in handle)
			other = _point(nodes[3 - anchor_index])
			span = sum((other[i] - anchor[i]) * unit[i] for i in range(2))
			if span <= EPSILON:
				raise GenerationError("J's hook handle points away from its curve.")
			pair.append((nodes[index], anchor, unit, reach, span, sign))
		pairs.append(pair)
	def place(deltas):
		for pair, delta in zip(pairs, deltas):
			for node, anchor, unit, reach, span, sign in pair:
				adjusted = reach + sign * delta
				if not 0.05 * span <= adjusted <= 0.90 * span:
					raise GenerationError("J's compensated hook would reverse or overextend a handle.")
				node.position = tuple(anchor[i] + unit[i] * adjusted for i in range(2))
	deltas = [0.0, 0.0]
	for _iteration in range(8):
		current = _shoulder_group_thickness(group)
		if abs(current - target) <= tolerance:
			return current
		step = max(0.1, target * 0.001)
		gradient = []
		for index in (0, 1):
			sample = list(deltas)
			sample[index] += step
			place(sample)
			gradient.append((_shoulder_group_thickness(group) - current) / step)
			place(deltas)
		norm = sum(value * value for value in gradient)
		if norm <= EPSILON ** 2:
			break
		changes = [(target - current) * value / norm for value in gradient]
		scale = min(1.0, target * 0.05 / max(abs(value) for value in changes))
		for _backtrack in range(8):
			trial = [value + change * scale for value, change in zip(deltas, changes)]
			try:
				place(trial)
				improved = abs(_shoulder_group_thickness(group) - target) < abs(current - target)
			except GenerationError:
				improved = False
			if improved:
				deltas = trial
				break
			place(deltas)
			scale *= 0.5
		else:
			break
	raise GenerationError(
		"J's final hook compensation did not converge (%.2f → %.2f)."
		% (target, current)
	)


def _set_J_terminal_cut(groups, terminal_signature, target_widths):
	"""Place C's intact terminal on the full U hook, with matching tangency."""
	inner_nodes, outer_nodes, is_curve = groups[0]
	inner_points, outer_points = _boundary_group_cubics(groups[0])
	center = _lerp(outer_points[0], inner_points[0], 0.5)
	axis = tuple(float(value) for value in terminal_signature["direction"])
	chord = tuple(inner_points[0][i] - outer_points[0][i] for i in range(2))
	if sum(axis[i] * chord[i] for i in range(2)) < 0.0:
		axis = (-axis[0], -axis[1])
	weight = float(terminal_signature["sourceThickness"])
	# Extend the return enough to retain U's shorter curve-side junction.
	# The old intersection cut removed much of Light's hook and could not cross
	# Bold's two boundaries. Placement preserves C's angle/weight/profile exactly.
	center = (center[0], center[1] + abs(axis[1] * weight) * 0.5)
	outer_anchor = tuple(center[i] - axis[i] * weight * 0.5 for i in range(2))
	inner_anchor = tuple(center[i] + axis[i] * weight * 0.5 for i in range(2))
	profile = _terminal_profile_points(terminal_signature, outer_anchor, inner_anchor)
	if not is_curve:
		# A faceted U retains its diagonal strokes and real sharp joins. Connect
		# those endpoints to the cap instead of distorting them into smooth curves.
		outer_nodes[0].smooth = inner_nodes[0].smooth = False
		points = [outer_points[0]]
		for point in tuple(profile) + (inner_points[0],):
			if sum((point[i] - points[-1][i]) ** 2 for i in range(2)) > EPSILON ** 2:
				points.append(point)
		return tuple(points)

	for side, nodes, points, anchor, neighbor in (
		(0, outer_nodes, outer_points, outer_anchor, profile[1]),
		(1, inner_nodes, inner_points, inner_anchor, profile[-2]),
	):
		# Collinear subdivisions are still a plain cut, however many nodes the
		# designer added. Only a genuinely bent profile has attachment edges.
		bent_profile = any(abs(point[1]) > EPSILON for point in terminal_signature["points"])
		body_tangent = terminal_signature.get("bodyTangents", (None, None))[side]
		if body_tangent is not None:
			normal = (-axis[1], axis[0])
			tangent = tuple(
				body_tangent[0] * axis[i] + body_tangent[1] * normal[i]
				for i in range(2)
			)
			attachment = (anchor[0] - neighbor[0], anchor[1] - neighbor[1])
			cross = tangent[0] * attachment[1] - tangent[1] * attachment[0]
			dot = sum(tangent[i] * attachment[i] for i in range(2))
			smooth = dot > EPSILON and abs(cross) <= abs(dot) * 0.001
		elif bent_profile:
			# Open Corners end with their own straight attachment edges. The hook
			# handle must follow that edge, not the chord across C's curve anchors.
			tangent = (anchor[0] - neighbor[0], anchor[1] - neighbor[1])
			smooth = True
		else:
			tangent = (-axis[1], axis[0])
			old_tangent = tuple(points[1][i] - points[0][i] for i in range(2))
			if sum(tangent[i] * old_tangent[i] for i in range(2)) < 0.0:
				tangent = (-tangent[0], -tangent[1])
			smooth = False  # A true terminal cut remains a corner.
		length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
		if length <= EPSILON:
			raise GenerationError("C's terminal contains a zero-length attachment edge.")
		tangent = tuple(value / length for value in tangent)
		old_handle = tuple(points[1][i] - points[0][i] for i in range(2))
		reach = (old_handle[0] ** 2 + old_handle[1] ** 2) ** 0.5
		if reach <= EPSILON:
			raise GenerationError("U's hook contains a zero-length terminal handle.")
		old_axis = tuple(value / reach for value in old_handle)
		old_span = sum((points[3][i] - points[0][i]) * old_axis[i] for i in range(2))
		new_span = sum((points[3][i] - anchor[i]) * tangent[i] for i in range(2))
		if min(old_span, new_span) <= EPSILON:
			raise GenerationError("C's terminal attachment points away from J's hook.")
		# Retain U's relative handle reach instead of transplanting its absolute
		# length onto a differently placed anchor, which can cause overshoots.
		reach = min(reach * new_span / old_span, new_span * 0.85)
		nodes[1].position = tuple(anchor[i] + tangent[i] * reach for i in range(2))
		nodes[0].position = anchor
		nodes[0].smooth = smooth

	for group, target in zip(groups, target_widths):
		if group[2]:
			_compensate_J_curve_handles(group, target)
	return profile


def _restore_J_landmarks(
	source_outer_arc,
	source_inner_arc,
	outer_arc,
	inner_arc,
	right_outer_top,
	right_inner_top,
	right_outer_top_copy,
	right_inner_top_copy,
	center_x,
	factor,
):
	"""Anchor U's bottom stroke and right stem after hook compensation."""
	for source_arc, copied_arc in (
		(source_outer_arc, outer_arc),
		(source_inner_arc, inner_arc),
	):
		bottom_index = min(
			(
				index for index, node in enumerate(source_arc)
				if node.type != OFFCURVE
			),
			key=lambda index: float(source_arc[index].y),
		)
		for index in (bottom_index - 1, bottom_index, bottom_index + 1):
			if 0 <= index < len(source_arc):
				copied_arc[index].y = float(source_arc[index].y)

	source_stem_center = (
		float(right_outer_top.x) + float(right_inner_top.x)
	) * 0.5
	source_stem_width = float(right_outer_top.x) - float(right_inner_top.x)
	target_stem_center = float(center_x) + (
		source_stem_center - float(center_x)
	) * float(factor)
	outer_x = target_stem_center + source_stem_width * 0.5
	inner_x = target_stem_center - source_stem_width * 0.5
	for node in (right_outer_top_copy, outer_arc[-1]):
		node.x = outer_x
	for node in (right_inner_top_copy, inner_arc[0]):
		node.x = inner_x
	if len(outer_arc) > 1 and outer_arc[-2].type == OFFCURVE:
		outer_arc[-2].x = outer_x
	if len(inner_arc) > 1 and inner_arc[1].type == OFFCURVE:
		inner_arc[1].x = inner_x


def _compensate_J_angular_corner(groups, targets):
	"""Fit a faceted counter corner while retaining the outside baseline corner."""
	corner = groups[0][0][-1]
	if len(groups) != 2 or corner is not groups[1][0][0]:
		raise GenerationError("J's faceted hook needs a shared counter corner.")
	tolerance = max(0.25, max(targets) * 0.001)
	for _iteration in range(8):
		current = [_J_hook_group_thickness(group) for group in groups]
		errors = [target - value for target, value in zip(targets, current)]
		if max(abs(error) for error in errors) <= tolerance:
			return current
		position = _point(corner)
		derivatives = []
		for axis in ("x", "y"):
			setattr(corner, axis, float(getattr(corner, axis)) + 0.1)
			derivatives.append([
				(_J_hook_group_thickness(group) - value) / 0.1
				for group, value in zip(groups, current)
			])
			corner.position = position
		a, c = derivatives[0]
		b, d = derivatives[1]
		determinant = a * d - b * c
		if abs(determinant) <= 0.000001:
			raise GenerationError("J's faceted hook weight is ambiguous.")
		dx = (errors[0] * d - b * errors[1]) / determinant
		dy = (a * errors[1] - errors[0] * c) / determinant
		scale = min(1.0, max(targets) * 0.05 / max(abs(dx), abs(dy), EPSILON))
		corner.position = (position[0] + dx * scale, position[1] + dy * scale)
	raise GenerationError("J's faceted hook compensation did not converge.")


def _transform_J_hook(
	source_groups, copied_groups, center_x, factor, target_widths,
	restore_landmarks=None,
):
	"""Condense J's whole hook centerline, then restore perpendicular weight."""
	weight_factors = [1.0 for _group in source_groups]
	tolerances = [max(0.5, width * 0.001) for width in target_widths]
	for _iteration in range(12):
		proposals = {}
		for source_group, copied_group, weight_factor in zip(
			source_groups, copied_groups, weight_factors
		):
			source_inner, source_outer, _source_curve = source_group
			copied_inner, copied_outer, _copied_curve = copied_group
			for source_i, source_o, copied_i, copied_o in zip(
				source_inner, source_outer, copied_inner, copied_outer
			):
				source_center = _lerp(_point(source_i), _point(source_o), 0.5)
				target_center = (
					float(center_x)
					+ (source_center[0] - float(center_x)) * float(factor),
					source_center[1],
				)
				half_vector = (
					(float(source_i.x) - float(source_o.x)) * 0.5,
					(float(source_i.y) - float(source_o.y)) * 0.5,
				)
				target_i = (
					target_center[0] + half_vector[0] * weight_factor,
					target_center[1] + half_vector[1] * weight_factor,
				)
				target_o = (
					target_center[0] - half_vector[0] * weight_factor,
					target_center[1] - half_vector[1] * weight_factor,
				)
				proposals.setdefault(id(copied_i), (copied_i, []))[1].append(target_i)
				proposals.setdefault(id(copied_o), (copied_o, []))[1].append(target_o)
		for node, positions in proposals.values():
			node.x = sum(point[0] for point in positions) / len(positions)
			node.y = sum(point[1] for point in positions) / len(positions)
		if restore_landmarks is not None:
			restore_landmarks()
		if all(not group[2] for group in copied_groups):
			return (
				_compensate_J_angular_corner(copied_groups, target_widths),
				tolerances,
			)
		current_widths = [
			_J_hook_group_thickness(group) for group in copied_groups
		]
		if all(
			abs(current - target) <= tolerance
			for current, target, tolerance in zip(
				current_widths, target_widths, tolerances
			)
		):
			return current_widths, tolerances
		for index, (current, target) in enumerate(
			zip(current_widths, target_widths)
		):
			weight_factors[index] *= max(
				0.95, min(1.05, target / current)
			)
	raise GenerationError(
		"J's curved-stroke compensation did not converge (%s → %s)."
		% (
			", ".join("%.2f" % value for value in target_widths),
			", ".join("%.2f" % value for value in current_widths),
		)
	)


def _build_J(font, master):
	"""Narrow U into J, retaining its full hook and C's complete top terminal."""
	U_source = _source_layer(font, "U", master.id)
	copy = _copy_decomposed(U_source)
	closed = [path for path in copy.paths if path.closed]
	if len(closed) != 1:
		raise GenerationError("U must have one closed contour to derive J.")
	path = closed[0]
	oncurves = _oncurve_nodes(path)
	cap_height = float(master.capHeight)
	tolerance = max(2.0, abs(cap_height) * 0.01)
	top_nodes = [
		node for node in oncurves
		if abs(float(node.y) - cap_height) <= tolerance
	]
	if len(top_nodes) != 4:
		raise GenerationError(
			"U must retain its four cap-height stem corners to derive J."
		)
	top_nodes.sort(key=lambda node: float(node.x))
	left_outer_top, left_inner_top, right_inner_top, right_outer_top = top_nodes

	# Use the long route between U's two left cap corners to locate the two
	# actual bowl junctions. J starts at those junctions, not at the cap-height
	# corners: this removes the complete left stem before C's terminal cut is
	# applied to the first curved hook segment.
	forward = _forward_between(path, left_outer_top, left_inner_top)[:-1]
	reverse = _forward_between(path, left_inner_top, left_outer_top)[:-1]
	if len(forward) < len(reverse):
		path.reverse()
	left_route = [left_outer_top] + _forward_between(
		path, left_outer_top, left_inner_top
	)
	junctions = [
		node for node in left_route[1:-1] if node.type != OFFCURVE
	]
	if len(junctions) < 2:
		raise GenerationError("Could not identify U's left bowl junctions for J.")
	left_outer_join = junctions[0]
	left_inner_join = junctions[-1]
	body = [left_outer_join] + _forward_between(
		path, left_outer_join, left_inner_join
	)
	if len(body) < 2 or body[0].type == OFFCURVE or body[-1].type == OFFCURVE:
		raise GenerationError("Could not isolate U's hook and right stem for J.")

	source_groups, source_outer_arc, source_inner_arc = (
		_J_hook_groups(body, right_outer_top, right_inner_top)
	)
	H_source = _source_layer(font, "H", master.id)
	_H_copy, H_left_stem, _H_right_stem, H_crossbar = _measure_H_source(H_source, master)
	vertical_weight = float(H_left_stem[1]) - float(H_left_stem[0])
	horizontal_weight = float(H_crossbar[1]) - float(H_crossbar[0])
	if horizontal_weight / vertical_weight < U_SANS_CONTRAST_THRESHOLD:
		# J retains the heavy H vertical, even when U's right stem is thin.
		# Anchor the outside edge and move the counter junction plus its handle
		# together; the hook retains its horizontal bottom and vertical tangent.
		inner_x = float(right_outer_top.x) - vertical_weight
		if inner_x <= float(left_inner_join.x) + EPSILON:
			raise GenerationError("J's H-weight stem would close its hook counter.")
		right_inner_top.x = inner_x
		source_inner_arc[0].x = inner_x
		if len(source_inner_arc) > 1 and source_inner_arc[1].type == OFFCURVE:
			source_inner_arc[1].x = inner_x
	source_widths = [
		_J_hook_group_thickness(group) for group in source_groups
	]
	tolerances = [max(0.5, width * 0.001) for width in source_widths]
	source_left = min(float(node.x) for node in oncurves)
	source_right = max(float(node.x) for node in oncurves)
	source_outline_width = source_right - source_left
	if source_outline_width <= EPSILON:
		raise GenerationError("U has no measurable outline width for J.")
	center_x = (source_left + source_right) * 0.5
	target_outline_width = source_outline_width * J_WIDTH_FACTOR
	delta = source_outline_width - target_outline_width
	terminal_signature = _C_terminal_signatures(font, master)["top"]
	working_factor = J_WIDTH_FACTOR
	# Scale every x coordinate, then compensate both sides of the curved hook
	# and re-anchor U's unscaled bottom and right-stem thicknesses. Rebuild until
	# the final C-profiled outline, rather than only one side, is exactly 6%
	# narrower than U.
	for _iteration in range(12):
		body_copies = [_copy_node(node) for node in body]
		node_copies = {
			id(source_node): copy_node
			for source_node, copy_node in zip(body, body_copies)
		}
		copied_groups, outer_arc, inner_arc = _J_hook_groups(
			body_copies,
			node_copies[id(right_outer_top)],
			node_copies[id(right_inner_top)],
		)
		for node in body_copies:
			node.x = center_x + (float(node.x) - center_x) * working_factor
		def restore_landmarks():
			_restore_J_landmarks(
				source_outer_arc, source_inner_arc, outer_arc, inner_arc,
				right_outer_top, right_inner_top,
				node_copies[id(right_outer_top)], node_copies[id(right_inner_top)],
				center_x, working_factor,
			)
		interim_widths, _interim_tolerances = _transform_J_hook(
			source_groups,
			copied_groups,
			center_x,
			working_factor,
			source_widths,
			restore_landmarks,
		)
		terminal_points = _set_J_terminal_cut(
			copied_groups, terminal_signature, source_widths
		)
		outline_x = [
			float(node.x) for node in body_copies if node.type != OFFCURVE
		] + [float(point[0]) for point in terminal_points]
		current_outline_width = max(outline_x) - min(outline_x)
		width_error = target_outline_width - current_outline_width
		if abs(width_error) <= 0.25:
			break
		working_factor += width_error / source_outline_width
	else:
		raise GenerationError("J's whole-shape 6% narrowing did not converge.")

	# Validate the actual finished hook, after terminal placement and landmark
	# alignment. Checking the earlier intermediate outline concealed weight loss.
	final_widths = [_J_hook_group_thickness(group) for group in copied_groups]
	if any(
		abs(current - source) > tolerance
		for current, source, tolerance in zip(
			final_widths, source_widths, tolerances
		)
	):
		raise GenerationError(
			"J hook compensation did not preserve U's stroke thickness "
			"(%s → %s)."
			% (
				", ".join("%.2f" % value for value in source_widths),
				", ".join("%.2f" % value for value in final_widths),
			)
		)

	J_path = GSPath()
	J_path.closed = True
	for index, node in enumerate(body_copies):
		J_path.nodes.append(
			_copy_node(
				node,
				node_type=LINE if index == 0 else node.type,
				smooth=node.smooth,
			)
		)
	# The body runs outer-to-inner around U, so the closing terminal returns
	# through C's profile in the opposite (inner-to-outer) order.
	for point in reversed(terminal_points[1:-1]):
		J_path.nodes.append(_new_node(point, LINE, False))

	# Keep U's sidebearings while reducing both the complete outline and advance
	# by the same amount. This translation does not alter any stroke measurement.
	_translate_paths([J_path], source_left - min(outline_x))
	candidate = _layer_from_paths(
		[J_path], round(float(U_source.width) - delta)
	)
	return _finish_candidate(candidate, remove_overlap=False)


def _lowercase_stem_profile(layer, x_height, fractions=(0.30, 0.70)):
	"""Measure the isolated upright's width, center and actual slant."""
	levels = tuple(float(x_height) * fraction for fraction in fractions)
	intervals = []
	for level in levels:
		intersections = _scan_x_intersections(layer, level)
		if len(intersections) != 2:
			raise GenerationError("Could not isolate the lowercase upright for i/j.")
		intervals.append(tuple(intersections))
	centers = [sum(interval) * 0.5 for interval in intervals]
	slope = (centers[1] - centers[0]) / (levels[1] - levels[0])
	weight = sum(interval[1] - interval[0] for interval in intervals) * 0.5
	return weight, centers[0], levels[0], slope


def _lowercase_dot_path(center, size, dot_shape):
	"""An optically equivalent square or four-extrema cubic circle."""
	if dot_shape not in DOT_SHAPES:
		raise GenerationError("Choose Round or Square dots for i/j.")
	x, y = center
	if dot_shape == "square":
		half = float(size) * 0.5
		return _rectangle_path(x - half, y - half, x + half, y + half)
	radius = float(size) * ROUND_DOT_SIZE_FACTOR * 0.5
	reach = radius * 0.5522847498307936
	path = GSPath()
	path.closed = True
	for point, node_type in (
		((x + radius, y), CURVE),
		((x + radius, y + reach), OFFCURVE),
		((x + reach, y + radius), OFFCURVE),
		((x, y + radius), CURVE),
		((x - reach, y + radius), OFFCURVE),
		((x - radius, y + reach), OFFCURVE),
		((x - radius, y), CURVE),
		((x - radius, y - reach), OFFCURVE),
		((x - reach, y - radius), OFFCURVE),
		((x, y - radius), CURVE),
		((x + reach, y - radius), OFFCURVE),
		((x + radius, y - reach), OFFCURVE),
	):
		path.nodes.append(_new_node(point, node_type, node_type == CURVE))
	return path


def _add_lowercase_dot(body, h_source, master, dot_shape):
	x_height = float(master.xHeight)
	weight, center, level, slope = _lowercase_stem_profile(body, x_height)
	size = max(weight, x_height * LOWERCASE_DOT_MIN_SIZE)
	# Use h's real ascender, not a cap-height guess. A circle has the same ink
	# area as the square and a small optical overshoot around the same center.
	ascender = _bounds_values(h_source)[3]
	radius = size * (ROUND_DOT_SIZE_FACTOR if dot_shape == "round" else 1.0) * 0.5
	center_y = max(ascender - size * 0.5,
		x_height + x_height * LOWERCASE_DOT_GAP + radius)
	center_x = center + (center_y - level) * slope
	body.shapes.append(_lowercase_dot_path((center_x, center_y), size, dot_shape))
	body.userData[DOT_SHAPE_KEY] = dot_shape
	return _finish_candidate(body, remove_overlap=False)


def _build_l(font, master):
	"""Keep h's full ascender stem, including its original feet and slant."""
	source = _source_layer(font, "h", master.id)
	copy, left_stem, right_stem = _measure_h_source(source, master)
	stem = _h_left_stem_path(copy, left_stem, right_stem, float(master.xHeight))
	return _finish_candidate(_layer_from_paths([stem], source.width), remove_overlap=False)


def _build_e(font, master):
	"""Keep compensated c intact, closing its upper bowl with G-like modules."""
	candidate = _build_c(font, master)
	path = candidate.paths[0]
	try:
		runs, _center = _oriented_C_terminal_runs(path)
	except GenerationError:
		# Compensation can bring a faceted inner counter into the terminal's
		# search region. Carry the original C's semantic node correspondence
		# forward instead of mistaking that counter edge for a longer cap.
		reference = _copy_decomposed(_source_layer(font, "C", master.id))
		reference.correctPathDirection()
		source_path = reference.paths[0]
		if tuple(n.type for n in source_path.nodes) != tuple(n.type for n in path.nodes):
			raise GenerationError("Could not retain C's terminal correspondence for e.")
		source_runs, _center = _oriented_C_terminal_runs(source_path)
		runs = {label: tuple(path.nodes[node.index] for node in run)
			for label, run in source_runs.items()}
	a, b = _C_terminal_cut_edge(runs["top"])
	outer, inner = sorted((a, b), key=lambda n: n.x, reverse=True)
	H = _source_layer(font, "H", master.id)
	_copy, _left, _right, crossbar = _measure_H_source(H, master)
	weight = (crossbar[1] - crossbar[0]) * LOWERCASE_C_STROKE_FACTOR
	center = float(master.xHeight) * 0.5
	left_hits = _scan_x_intersections(candidate, center)
	if len(left_hits) < 2 or inner.x >= outer.x - EPSILON:
		raise GenerationError("Could not identify c's counter and upper terminal for e.")
	# Long/heavy caps can leave less aperture than H's bar is thick. Raise the
	# bar just enough to retain an opening above the intact lower terminal;
	# the short join may connect upwards or downwards to the upper cap.
	lower_cut = _C_terminal_cut_edge(runs["bottom"])
	lower_top = max(float(n.y) for n in lower_cut)
	center = max(center, lower_top + weight * 0.5 + float(master.xHeight) * 0.04)
	if center + weight * 0.5 >= _bounds_values(candidate)[3]:
		raise GenerationError("c's terminals leave no room for e's crossbar and opening.")
	left_hits = _scan_x_intersections(candidate, center)
	bar = _rectangle_path(left_hits[1] - 1.0, center - weight * 0.5,
		float(outer.x), center + weight * 0.5)
	join = GSPath()
	join.closed = True
	for point in ((inner.x, center), (inner.x, inner.y + 1.0),
		(outer.x, outer.y + 1.0), (outer.x, center)):
		join.nodes.append(_new_node(point, LINE))
	for module in (bar, join):
		if _path_signed_area(module) * _path_signed_area(path) < 0.0:
			module.reverse()
		candidate.shapes.append(module)
	return _finish_candidate(candidate, remove_overlap=False)


def _build_k(font, master):
	"""Resize K to x-height and retain an upright reaching h's ascender."""
	source = _copy_decomposed(_source_layer(font, "K", master.id))
	cap_height, x_height = float(master.capHeight), float(master.xHeight)
	if min(cap_height, x_height) <= EPSILON:
		raise GenerationError("k needs positive cap-height and x-height metrics.")
	fx, fy = x_height / cap_height * LOWERCASE_K_WIDTH_FACTOR, x_height / cap_height
	if len(source.paths) == 1:
		return _build_k_complete_outline(font, master, source, fx, fy)
	stem = _build_l(font, master)
	if len(source.paths) == 2:
		return _build_k_joined_fork(source, stem, cap_height, x_height, fx, fy)
	diagonals, uprights = [], []
	for path in source.paths:
		if not path.closed:
			continue
		left, bottom, right, top = _bounds_values(path)
		if top - bottom <= EPSILON:
			continue
		low = _diagonal_center_at_y(path, bottom + (top - bottom) * 0.3)
		high = _diagonal_center_at_y(path, bottom + (top - bottom) * 0.7)
		if abs(high - low) > (top - bottom) * 0.04:
			diagonals.append((high > low, path))
		else:
			uprights.append(path)
	if len(diagonals) != 2 or len(uprights) != 1 or {item[0] for item in diagonals} != {True, False}:
		raise GenerationError("K needs a separate upright and two diagonal contours to build k.")
	source_center = _diagonal_center_at_y(uprights[0], cap_height * 0.3)
	_weight, target_center, level, slope = _lowercase_stem_profile(stem, x_height)
	target_center += (0.0 - level) * slope
	for ascending, reference in diagonals:
		path = reference.copy()
		_transform_paths_affinely([path], (source_center, 0.0), (target_center, 0.0), fx, fy)
		# K's angled join can occupy much of a heavy arm's lower end. Compare
		# the straight stroke interiors, not that deliberately tapered join.
		positions = (0.50, 0.56, 0.62, 0.68) if ascending else (0.30, 0.36, 0.42, 0.48)
		targets = tuple(t * LOWERCASE_K_STROKE_FACTOR for t in _single_diagonal_profile(reference, positions))
		for _iteration in range(60):
			current = _single_diagonal_profile(path, positions)
			if max(abs(a - b) for a, b in zip(current, targets)) <= 0.5:
				break
			_compensate_k_diagonal(path, tuple(max(0.95, min(1.05, b / a))
				for a, b in zip(current, targets)), positions)
		else:
			raise GenerationError("k's diagonal weight compensation did not converge.")
		# All three shapes are positive ink, including their intentional overlap.
		if _path_signed_area(path) * _path_signed_area(stem.paths[0]) < 0.0:
			path.reverse()
		stem.shapes.append(path)
	return _finish_candidate(stem, remove_overlap=False)


def _k_complete_diagonal_samples(layer, height, upper):
	"""Measure the rightmost ink interval, excluding the joined upright."""
	result = []
	# Joined heavy arms can already merge into the upright around 20–30%
	# cap height. Sample the clear interiors, not that intentional ink overlap.
	for progress in ((0.85, 0.875, 0.90) if upper else (0.10, 0.125, 0.15)):
		y, delta = height * progress, height * 0.005
		rows = [_scan_x_intersections(layer, probe) for probe in (y - delta, y, y + delta)]
		if any(len(row) < 4 or len(row) % 2 for row in rows):
			raise GenerationError("Could not measure K's diagonal away from its stem junction.")
		rows = [row[-2:] for row in rows]
		slope = (sum(rows[2]) - sum(rows[0])) / (4.0 * delta)
		result.append((y, sum(rows[1]) * 0.5,
			(rows[1][1] - rows[1][0]) / (1.0 + slope * slope) ** 0.5))
	return result


def _build_k_complete_outline(font, master, source, factor_x, factor_y):
	"""Copy a joined K intact, compensate its strokes, and extend its upright.

	No separate contours, fixed node counts, or prescribed arm joins are
	required. The two diagonal interiors and left upright are identified by
	ink intersections. All existing contour events survive the transform.
	"""
	reference = _copy_decomposed(source)
	path = reference.paths[0]
	cap_height, x_height = float(master.capHeight), float(master.xHeight)
	levels = (cap_height * 0.20, cap_height * 0.80)
	rows = [_scan_x_intersections(reference, y) for y in levels]
	if any(len(row) < 4 or len(row) % 2 for row in rows):
		raise GenerationError("Could not identify K's upright away from its arm junction.")
	intervals = [row[:2] for row in rows]
	centers = [sum(row) * 0.5 for row in intervals]
	width = sum(row[1] - row[0] for row in intervals) * 0.5
	slope = (centers[1] - centers[0]) / (levels[1] - levels[0])
	axis_zero = centers[0] - levels[0] * slope
	normal_weight = width / (1.0 + slope * slope) ** 0.5
	stem_nodes = [n.x <= axis_zero + n.y * slope + width * 0.5 + 0.01 for n in path.nodes]
	branch = {n.index: int(n.y > cap_height * 0.5) for n in path.nodes}
	for start in _oncurve_nodes(path):
		end = _next_oncurve(path, start)
		if abs(end.y - start.y) >= cap_height * 0.25 and abs(end.x - start.x) > cap_height * 0.01:
			side = int((end.x - start.x) * (end.y - start.y) > 0.0)
			for node in [start] + _forward_between(path, start, end):
				branch[node.index] = side
	source_samples = [_k_complete_diagonal_samples(reference, cap_height, upper) for upper in (False, True)]
	left, bottom, right, top = _bounds_values(reference)
	target_width = (right - left) * factor_x
	ascender = _bounds_values(_source_layer(font, "h", master.id))[3]
	working_x = factor_x
	for _width_iteration in range(12):
		raw = reference.copy()
		_transform_paths_affinely(raw.paths, (0, 0), (0, 0), working_x, factor_y)
		raw_samples = [_k_complete_diagonal_samples(raw, x_height, upper) for upper in (False, True)]
		candidate = raw.copy()
		base = [_point(n) for n in raw.paths[0].nodes]
		factors = [1.0, 1.0]
		stem_slope = slope * working_x / factor_y
		stem_factor = (normal_weight * LOWERCASE_K_STROKE_FACTOR
			* (1.0 + stem_slope * stem_slope) ** 0.5 / (width * working_x))
		for _weight_iteration in range(60):
			for node, point in zip(candidate.paths[0].nodes, base):
				if stem_nodes[node.index]:
					axis = axis_zero * working_x + point[1] * stem_slope
					node.x = axis + (point[0] - axis) * stem_factor
					node.y = point[1]
					if path.nodes[node.index].y > top - cap_height * 0.10:
						delta = ascender - top * factor_y
						node.y += delta
						node.x += delta * stem_slope
				else:
					side = branch[node.index]
					measurements = raw_samples[side]
					line_slope = ((measurements[-1][1] - measurements[0][1])
						/ (measurements[-1][0] - measurements[0][0]))
					axis = measurements[0][1] + (point[1] - measurements[0][0]) * line_slope
					node.x = axis + (point[0] - axis) * factors[side]
					node.y = point[1]
			_s_align_source_tangents(path, candidate.paths[0], working_x, factor_y)
			measured = [_k_complete_diagonal_samples(candidate, x_height, upper) for upper in (False, True)]
			errors = [max(abs(a[2] - b[2] * LOWERCASE_K_STROKE_FACTOR)
				for a, b in zip(current, original)) for current, original in zip(measured, source_samples)]
			if max(errors) <= 0.5:
				break
			for side in (0, 1):
				factors[side] *= max(0.95, min(1.05,
					sum(r[2] for r in source_samples[side]) * LOWERCASE_K_STROKE_FACTOR
					/ sum(r[2] for r in measured[side])))
		else:
			raise GenerationError("k's complete-outline stroke compensation did not converge.")
		# Native detached layers can retain source-size cached bounds after edits.
		candidate = _layer_from_paths(candidate.paths, candidate.width)
		bounds = _bounds_values(candidate)
		error = target_width - (bounds[2] - bounds[0])
		if abs(error) <= 0.25:
			break
		working_x += error / (right - left)
	else:
		raise GenerationError("k's compensated width did not converge.")
	_translate_paths(candidate.paths, left * factor_x - bounds[0], -bottom * factor_y)
	candidate.width = round(float(source.width) * factor_x)
	return _finish_candidate(candidate, remove_overlap=False)


def _compensate_k_diagonal(path, factors, positions):
	"""Use interior centerline samples even when a slanted end narrows to a tip."""
	reference = path.copy()
	_left, bottom, _right, top = _bounds_values(reference)
	y0, y1 = bottom + (top - bottom) * 0.3, bottom + (top - bottom) * 0.7
	x0, x1 = _diagonal_center_at_y(reference, y0), _diagonal_center_at_y(reference, y1)
	slope = (x1 - x0) / (y1 - y0)
	for node in path.nodes:
		progress = (node.y - bottom) / (top - bottom)
		factor = _interpolate_profile_value(progress, positions, factors)
		center = x0 + (node.y - y0) * slope
		node.x = center + (node.x - center) * factor


def _k_fork_samples(layer, height, upper):
	"""Sample only the arm/leg interior, not the curved fork junction."""
	result = []
	for progress in ((0.70, 0.80, 0.90) if upper else (0.10, 0.20, 0.30)):
		y, delta = height * progress, height * 0.005
		hits = [_scan_x_intersections(layer, probe) for probe in (y - delta, y, y + delta)]
		if any(len(row) != 2 for row in hits):
			raise GenerationError("Could not isolate K's arm/leg for normal-weight measurement.")
		slope = (sum(hits[2]) - sum(hits[0])) / (4.0 * delta)
		result.append((y, sum(hits[1]) * 0.5,
			(hits[1][1] - hits[1][0]) / (1.0 + slope * slope) ** 0.5))
	return result


def _build_k_joined_fork(source, stem, cap_height, x_height, fx, fy):
	"""Retain a K fork whose arm and leg share one contour, including handles."""
	upright, fork = sorted(source.paths, key=lambda p: _bounds_values(p)[0])
	source_center = _diagonal_center_at_y(upright, cap_height * 0.3)
	_weight, center, level, slope = _lowercase_stem_profile(stem, x_height)
	center -= level * slope
	ref = _layer_from_paths([fork], 0)
	source_samples = [_k_fork_samples(ref, cap_height, upper) for upper in (False, True)]
	path = fork.copy()
	_transform_paths_affinely([path], (source_center, 0), (center, 0), fx, fy)
	base = [_point(node) for node in path.nodes]
	branch = {node.index: int(node.y > cap_height * 0.5) for node in fork.nodes}
	oncurves = _oncurve_nodes(fork)
	for start in oncurves:
		end = _next_oncurve(fork, start)
		if abs(end.y - start.y) >= cap_height * 0.25:
			ascending = (end.x - start.x) * (end.y - start.y) > 0.0
			for node in [start] + _forward_between(fork, start, end):
				branch[node.index] = int(ascending)
	raw = _layer_from_paths([path], 0)
	raw_samples = [_k_fork_samples(raw, x_height, upper) for upper in (False, True)]
	working = _layer_from_paths([path], 0)
	factors = [1.0, 1.0]
	for _iteration in range(60):
		for node, point in zip(working.paths[0].nodes, base):
			progress = point[1] / x_height
			side = branch[node.index]
			samples = raw_samples[side]
			line_slope = (samples[-1][1] - samples[0][1]) / (samples[-1][0] - samples[0][0])
			axis = samples[0][1] + (point[1] - samples[0][0]) * line_slope
			# Apply one affine cross-stroke correction to each complete branch,
			# including its join handles, rather than tapering a straight edge.
			node.x = axis + (point[0] - axis) * factors[side]
		current = [_k_fork_samples(working, x_height, upper) for upper in (False, True)]
		errors = [max(abs(a[2] - b[2] * LOWERCASE_K_STROKE_FACTOR)
			for a, b in zip(measured, original)) for measured, original in zip(current, source_samples)]
		if max(errors) <= 0.5:
			break
		for side in (0, 1):
			target = sum(row[2] for row in source_samples[side]) * LOWERCASE_K_STROKE_FACTOR
			measured = sum(row[2] for row in current[side])
			factors[side] *= max(0.95, min(1.05, target / measured))
	else:
		raise GenerationError("k's joined arm/leg compensation did not converge.")
	path = working.paths[0].copy()
	if _path_signed_area(path) * _path_signed_area(stem.paths[0]) < 0:
		path.reverse()
	stem.shapes.append(path)
	return _finish_candidate(stem, remove_overlap=False)


def _z_stroke_data(layer):
	"""Locate flat bars and both diagonal edges without a fixed node count."""
	if len(layer.paths) != 1 or not layer.paths[0].closed:
		raise GenerationError("Z needs one closed outline with horizontal bars to build z.")
	left, bottom, right, top = _bounds_values(layer)
	levels = _scan_y_intersections(layer, (left + right) * 0.5)
	if len(levels) < 4:
		# A heavy diagonal may fill the entire middle column. Its bars are
		# still identifiable from their flat inner edges, not an empty counter.
		flat_levels = []
		for node in _oncurve_nodes(layer.paths[0]):
			end = _next_oncurve(layer.paths[0], node)
			if end.type == LINE and abs(node.y - end.y) <= 0.01 and abs(node.x - end.x) > (right - left) * 0.05:
				if bottom + 0.01 < node.y < top - 0.01:
					flat_levels.append(float(node.y))
		if len(set(flat_levels)) < 2:
			raise GenerationError("Could not identify Z's two horizontal bars.")
		lower, upper = min(flat_levels), max(flat_levels)
	else:
		lower, upper = levels[1], levels[-2]
	if not bottom < lower < upper < top:
		raise GenerationError("Z's horizontal bars leave no measurable diagonal.")
	path = layer.paths[0]
	rows = [[n for n in _oncurve_nodes(path) if abs(n.y - y) <= 0.01
		and any(lower - 0.01 <= other.y <= upper + 0.01 and abs(other.y - y) > 0.01
			for other in (_previous_oncurve(path, n), _next_oncurve(path, n)))]
		for y in (lower, upper)]
	if any(not row for row in rows):
		raise GenerationError("Z's horizontal bars need identifiable diagonal joins.")
	# The inner horizontal edges locate the two inside joins. The opposite
	# boundary may meet its bar at a DIFFERENT height, with small straight or
	# curved transition segments. Follow the native contour until it leaves
	# the body band instead of requiring both endpoints on one exact row.
	inside_bottom = max(rows[0], key=lambda n: n.x)
	inside_top = min(rows[1], key=lambda n: n.x)
	def edge(start):
		nodes = list(path.nodes)
		choices = []
		for direction in (1, -1):
			arc = [start]
			for offset in range(1, len(nodes)):
				node = nodes[(start.index + direction * offset) % len(nodes)]
				if node.type != OFFCURVE and not lower - 0.01 <= node.y <= upper + 0.01:
					break
				arc.append(node)
			# Never retain dangling handles belonging to the bar-side curve.
			while arc and arc[-1].type == OFFCURVE:
				arc.pop()
			oncurves = [n for n in arc if n.type != OFFCURVE]
			span = max(n.y for n in oncurves) - min(n.y for n in oncurves)
			choices.append((span, arc))
		span, arc = max(choices, key=lambda item: item[0])
		if span < (upper - lower) * 0.70:
			raise GenerationError("Could not follow Z's diagonal between its bars.")
		return arc
	return (bottom, lower, upper, top), (edge(inside_top), edge(inside_bottom))


def _z_diagonal_profile(layer, lower, upper):
	"""Measure Z's diagonal normally, away from both bar joins."""
	profile = []
	for progress in (0.30, 0.50, 0.70):
		y = lower + (upper - lower) * progress
		delta = max(0.1, (upper - lower) * 0.01)
		before, middle, after = [_scan_x_intersections(layer, probe) for probe in (y - delta, y, y + delta)]
		if any(len(hits) != 2 for hits in (before, middle, after)):
			raise GenerationError("Could not isolate Z's diagonal for normal-weight measurement.")
		slope = (sum(after) - sum(before)) / (4.0 * delta)
		profile.append((middle[1] - middle[0]) / (1.0 + slope * slope) ** 0.5)
	return tuple(profile)


def _build_z(font, master):
	"""Copy Z to x-height, widen it 8%, then restore bars and diagonal weight."""
	source = _source_layer(font, "Z", master.id)
	reference = _copy_decomposed(source)
	levels, edges = _z_stroke_data(reference)
	bottom, lower, upper, top = levels
	left, _bottom, right, _top = _bounds_values(reference)
	cap_height, x_height = float(master.capHeight), float(master.xHeight)
	if min(cap_height, x_height, right - left) <= EPSILON:
		raise GenerationError("Z and its master need positive dimensions for z.")
	fx = x_height / cap_height * LOWERCASE_Z_WIDTH_FACTOR
	bar_bottom = (lower - bottom) * LOWERCASE_Z_STROKE_FACTOR
	bar_top = (top - upper) * LOWERCASE_Z_STROKE_FACTOR
	new_levels = (0.0, bar_bottom, x_height - bar_top, x_height)
	if new_levels[2] <= new_levels[1]:
		raise GenerationError("Z's compensated bars leave no room at x-height.")
	targets = tuple(t * LOWERCASE_Z_STROKE_FACTOR for t in _z_diagonal_profile(reference, lower, upper))
	candidate = reference.copy()
	def map_y(y):
		index = 0 if y <= lower else 2 if y >= upper else 1
		return new_levels[index] + (y - levels[index]) * (new_levels[index + 1] - new_levels[index]) / (levels[index + 1] - levels[index])
	for a, b in zip(reference.paths[0].nodes, candidate.paths[0].nodes):
		b.position = (a.x * fx, map_y(a.y))
	base = [_point(n) for n in candidate.paths[0].nodes]
	def place(delta):
		for side, arc in enumerate(edges):
			arc_bottom = min(n.y for n in arc if n.type != OFFCURVE)
			arc_top = max(n.y for n in arc if n.type != OFFCURVE)
			for node in arc:
				progress = (node.y - arc_bottom) / (arc_top - arc_bottom)
				shift = -progress if side == 0 else 1.0 - progress
				candidate.paths[0].nodes[node.index].x = base[node.index][0] + delta * shift
		_s_restore_collinear_nodes(reference.paths[0], candidate.paths[0])
	# Keep the outer width, bar height and all cap positions fixed. Only the
	# diagonal's inner join reach changes, retaining its center and clean edges.
	delta = 0.0
	for _iteration in range(40):
		place(delta)
		current = _z_diagonal_profile(candidate, new_levels[1], new_levels[2])
		error = sum(b - a for a, b in zip(current, targets)) / len(targets)
		if max(abs(a - b) for a, b in zip(current, targets)) <= 0.5:
			break
		place(delta + 0.5)
		probe = _z_diagonal_profile(candidate, new_levels[1], new_levels[2])
		response = sum(b - a for a, b in zip(current, probe)) / (0.5 * len(targets))
		if abs(response) <= EPSILON:
			raise GenerationError("z's diagonal compensation has no measurable response.")
		limit = max(targets) * 0.05
		delta += max(-limit, min(limit, error / response))
	else:
		raise GenerationError("z's diagonal weight compensation did not converge.")
	candidate.width = round(float(source.width) * fx)
	return _finish_candidate(candidate, remove_overlap=False)


def _build_i(font, master, dot_shape="round"):
	source = _source_layer(font, "h", master.id)
	copy, left_stem, right_stem = _measure_h_source(source, master)
	x_height = float(master.xHeight)
	stem = _h_left_stem_path(copy, left_stem, right_stem, x_height)
	body = _layer_from_paths([stem], source.width)
	_weight, _center, _level, slope = _lowercase_stem_profile(body, x_height)
	_lower_ascender_stem(body, left_stem, x_height,
		shoulder_top=x_height, stem_slope=slope)
	return _add_lowercase_dot(body, copy, master, dot_shape)


def _j_hook_strip(outer, inner):
	"""Detached curved stroke for true local-normal thickness measurements."""
	path = GSPath()
	path.closed = True
	path.nodes.append(_new_node(outer[0], LINE, False))
	for point in outer[1:3]:
		path.nodes.append(_new_node(point, OFFCURVE, False))
	path.nodes.append(_new_node(outer[3], CURVE, False))
	path.nodes.append(_new_node(inner[3], LINE, False))
	for point in reversed(inner[1:3]):
		path.nodes.append(_new_node(point, OFFCURVE, False))
	path.nodes.append(_new_node(inner[0], CURVE, False))
	return _layer_from_paths([path], 0)


def _compensate_j_hook(outer, inner, stem_weight, tip_weight):
	"""Fit normal weight without moving the centerline, joins or terminal.

	Only paired handle reaches change, along their existing endpoint tangents.
	That preserves the green stem joins and the terminal's perpendicular cut.
	The transition to H's horizontal-bar weight is intentional; slant-induced
	thinning and the quarter-turn's small weight loss are compensated.
	"""
	centers = tuple(_lerp(a, b, 0.5) for a, b in zip(outer, inner))
	def unit(vector):
		length = (vector[0] ** 2 + vector[1] ** 2) ** 0.5
		if length <= EPSILON:
			raise GenerationError("j's hook has a zero-length tangent.")
		return vector[0] / length, vector[1] / length
	directions = (unit((centers[1][0] - centers[0][0], centers[1][1] - centers[0][1])),
		unit((centers[3][0] - centers[2][0], centers[3][1] - centers[2][1])))
	fractions = (0.30, 0.70)
	targets = [stem_weight + (tip_weight - stem_weight) * t * t * (3.0 - 2.0 * t)
		for t in fractions]
	def modified(deltas):
		outer_points, inner_points = list(outer), list(inner)
		for index, delta, direction in zip((1, 2), deltas, directions):
			for points, sign in ((outer_points, 1.0), (inner_points, -1.0)):
				points[index] = (points[index][0] + sign * delta * direction[0],
					points[index][1] + sign * delta * direction[1])
		return tuple(outer_points), tuple(inner_points)
	def measure(deltas):
		points = modified(deltas)
		strip = _j_hook_strip(*points)
		return [_S_normal_thickness(strip, _cubic_point(centers, t),
			_cubic_tangent(centers, t)) for t in fractions]
	deltas = [0.0, 0.0]
	# Half a unit is the meaningful fitting tolerance on the final integer grid.
	tolerance = max(0.50, stem_weight * 0.001)
	for _iteration in range(12):
		current = measure(deltas)
		errors = [target - actual for target, actual in zip(targets, current)]
		if max(abs(error) for error in errors) <= tolerance:
			result = modified(deltas)
			for points in result:
				for index, anchor, direction, sign in (
					(1, 0, directions[0], 1.0), (2, 3, directions[1], -1.0)):
					vector = (points[index][0] - points[anchor][0], points[index][1] - points[anchor][1])
					if sign * sum(a * b for a, b in zip(vector, direction)) <= EPSILON:
						raise GenerationError("j's compensated hook would reverse a terminal handle.")
			return result
		step = max(0.25, stem_weight * 0.01)
		jacobian = []
		for column in (0, 1):
			sample = list(deltas)
			sample[column] += step
			measured = measure(sample)
			jacobian.append([(value - base) / step for value, base in zip(measured, current)])
		determinant = jacobian[0][0] * jacobian[1][1] - jacobian[1][0] * jacobian[0][1]
		if abs(determinant) < 0.00001:
			raise GenerationError("Could not measure j's hook-weight compensation reliably.")
		changes = ((errors[0] * jacobian[1][1] - jacobian[1][0] * errors[1]) / determinant,
			(jacobian[0][0] * errors[1] - errors[0] * jacobian[0][1]) / determinant)
		# Bound the paired adjustment together: clipping each handle separately
		# destroys the fitting direction on broad, heavy or slanted hooks.
		scale = min(1.0, stem_weight * 0.10 / max(abs(change) for change in changes))
		baseline_error = sum(error * error for error in errors)
		for _backtrack in range(10):
			trial = [value + change * scale for value, change in zip(deltas, changes)]
			try:
				trial_error = sum((target - value) ** 2 for target, value in zip(targets, measure(trial)))
			except GenerationError:
				trial_error = baseline_error
			if trial_error < baseline_error:
				deltas = trial
				break
			scale *= 0.5
		else:
			raise GenerationError("Could not improve j hook-weight compensation safely.")
	raise GenerationError("j's hook-weight compensation did not converge.")


def _j_angular_hook_boundaries(outer, inner, start_weight, end_weight):
	"""Offset an angular hook along local normals, not its canvas axes."""
	centers = [_lerp(i, o, 0.5) for i, o in zip(inner, outer)]
	normals = []
	for start, end in zip(centers, centers[1:]):
		dx, dy = end[0] - start[0], end[1] - start[1]
		length = (dx * dx + dy * dy) ** 0.5
		if length <= EPSILON:
			raise GenerationError("j's angular hook has a zero-length edge.")
		normals.append((-dy / length, dx / length))
	result = [[], []]
	for index, center in enumerate(centers):
		if index == 0:
			# Keep the exact upright-to-hook join, including its slant.
			result[0].append(outer[0])
			result[1].append(inner[0])
			continue
		fraction = index / float(len(centers) - 1)
		# Keep the first complete segment at upright weight. Besides avoiding
		# a kink at the join, this leaves the same removable collinear root
		# nodes at different stroke weights and in all masters.
		weight = start_weight if index == 1 else (
			start_weight + (end_weight - start_weight) * fraction)
		if index == len(centers) - 1:
			miter = normals[-1]
		else:
			before, after = normals[index - 1], normals[index]
			miter = (before[0] + after[0], before[1] + after[1])
			denominator = miter[0] * after[0] + miter[1] * after[1]
			if denominator <= EPSILON:
				raise GenerationError("j's angular hook folds back on itself.")
			miter = (miter[0] / denominator, miter[1] / denominator)
		for points, sign in zip(result, (1.0, -1.0)):
			points.append((center[0] + sign * miter[0] * weight * 0.5,
				center[1] + sign * miter[1] * weight * 0.5))
	return tuple(result[0]), tuple(result[1])


def _j_hook_body(stem_body, h_source, master, horizontal_weight):
	"""One blunt quarter-turn, ending at 98% of H's horizontal-bar thickness.

	The upright remains h's original stem. The hook is constructed separately:
	copying r's terminal also copied C's curl and expanded corners into j.
	There is no contrast cutoff or alternate model. H sets the terminal pair's
	distance independently for each master, rounded to the font's whole units.
	"""
	x_height = float(master.xHeight)
	depth = -float(master.descender)
	if depth <= EPSILON:
		raise GenerationError("Set a descender below the baseline to build j.")
	width, axis, level, slope = _lowercase_stem_profile(stem_body, x_height)
	weight = width / (1.0 + slope * slope) ** 0.5
	if horizontal_weight <= EPSILON:
		raise GenerationError("H's horizontal bar has no measurable thickness.")
	tip_weight = max(1.0, round(horizontal_weight * LOWERCASE_J_TERMINAL_WEIGHT_FACTOR))
	root_y = -depth * 0.12
	root_x = axis + (root_y - level) * slope
	# Leave room for the counter turn in a heavy master without thinning
	# the hook. Raising only the bend preserves the upright's proportions.
	bottom = float(master.descender)
	inner_bottom = bottom + tip_weight
	root_y = max(root_y, bottom + weight * 1.75, inner_bottom + depth * 0.10)
	if root_y >= x_height * 0.30:
		raise GenerationError("h's stem is too heavy for j at this descender depth.")
	root_x = axis + (root_y - level) * slope
	# Extend the complete bend before fitting its paired tangents and normal
	# weight. This lengthens the hook smoothly, not just its final anchors.
	hook_length = max(depth * LOWERCASE_J_HOOK_WIDTH, weight * 1.5)
	tip_x = root_x - hook_length * LOWERCASE_J_HOOK_LENGTH_GAIN
	reach = 0.5522847498307936
	outer = ((root_x + width * 0.5, root_y),
		(root_x + width * 0.5, root_y - (root_y - bottom) * reach),
		(tip_x + (root_x + width * 0.5 - tip_x) * reach, bottom),
		(tip_x, bottom))
	inner = ((root_x - width * 0.5, root_y),
		(root_x - width * 0.5, root_y - (root_y - inner_bottom) * reach),
		(tip_x + (root_x - width * 0.5 - tip_x) * reach, inner_bottom),
		(tip_x, inner_bottom))
	# Carry the original upright slant into the hook exactly once. The join's
	# handles remain on the same stem edge, never kink away from the green node.
	outer = tuple((p[0] + (p[1] - root_y) * slope, p[1]) for p in outer)
	inner = tuple((p[0] + (p[1] - root_y) * slope, p[1]) for p in inner)
	# Slant the hook, not the cut. Place the two terminal anchors directly
	# above one another so their actual Euclidean distance is the requested
	# 98%, not a longer slanted vector. Move the adjacent handles with them.
	terminal_x = (outer[-1][0] + inner[-1][0]) * 0.5
	def align_terminal(points):
		points = list(points)
		delta = terminal_x - points[-1][0]
		for index in (2, 3):
			points[index] = (points[index][0] + delta, points[index][1])
		return tuple(points)
	outer, inner = align_terminal(outer), align_terminal(inner)
	curved = any(node.type == OFFCURVE for path in h_source.paths for node in path.nodes)
	if curved:
		outer, inner = _compensate_j_hook(outer, inner, weight, tip_weight)
	else:
		outer, inner = _j_angular_hook_boundaries(outer, inner, weight, tip_weight)
		# Normal offsets at angular mitres can overshoot the designed descender.
		shift = float(master.descender) - min(p[1] for p in outer + inner)
		outer = tuple((p[0] + shift * slope, p[1] + shift) if index else p
			for index, p in enumerate(outer))
		inner = tuple((p[0] + shift * slope, p[1] + shift) if index else p
			for index, p in enumerate(inner))
	path = max(stem_body.paths, key=_bounds_area)
	oncurves = _oncurve_nodes(path)
	bottom = min(float(node.y) for node in oncurves)
	foot_x = axis + (bottom - level) * slope
	feet = [min(oncurves, key=lambda node:
		abs(float(node.y) - bottom) + abs(float(node.x) - (foot_x + sign * width * 0.5)))
		for sign in (-1.0, 1.0)]
	arc = [feet[0]] + _forward_between(path, feet[0], feet[1])
	if max(oncurves, key=lambda node: float(node.y)) not in arc:
		path.reverse()
		arc = [feet[0]] + _forward_between(path, feet[0], feet[1])
	result = GSPath()
	result.closed = True
	for node in arc:
		result.nodes.append(_copy_node(node))
	result.nodes[0].position = inner[0]
	result.nodes[0].type = CURVE if curved else LINE
	result.nodes[0].smooth = curved
	result.nodes[-1].position = outer[0]
	result.nodes[-1].smooth = curved
	for point in outer[1:-1]:
		result.nodes.append(_new_node(point, OFFCURVE if curved else LINE, False))
	outer_terminal = _new_node(outer[-1], CURVE if curved else LINE, False)
	inner_terminal = _new_node(inner[-1], LINE, False)
	terminal_index = len(result.nodes)
	result.nodes.append(outer_terminal)
	result.nodes.append(inner_terminal)
	for point in reversed(inner[1:-1]):
		result.nodes.append(_new_node(point, OFFCURVE if curved else LINE, False))
	body = _layer_from_paths([result], stem_body.width)
	# _layer_from_paths copies its paths; keep references to the attached copy,
	# not the temporary construction nodes, for the final landmark alignment.
	attached = body.paths[0]
	return body, (attached.nodes[terminal_index], attached.nodes[terminal_index + 1])


def _align_j_terminal_pair(pair, horizontal_weight):
	"""Enforce the requested final-node distance after native grid rounding."""
	outer, inner = pair
	distance = max(1, round(horizontal_weight * LOWERCASE_J_TERMINAL_WEIGHT_FACTOR))
	x = round((float(outer.x) + float(inner.x)) * 0.5)
	bottom = round(float(outer.y))
	for node, y in ((outer, bottom), (inner, bottom + distance)):
		dx = x - float(node.x)
		for neighbor in _adjacent_nodes(node.parent, node):
			if neighbor.type == OFFCURVE:
				neighbor.position = (round(float(neighbor.x) + dx), y)
		node.position = (x, y)


def _build_j(font, master, dot_shape="round"):
	"""Keep h's upright/dot and end one hook model at 98% of H's bar weight."""
	h_source, left_stem, right_stem = _measure_h_source(
		_source_layer(font, "h", master.id), master)
	_H, _H_left, _H_right, crossbar = _measure_H_source(
		_source_layer(font, "H", master.id), master)
	horizontal_weight = crossbar[1] - crossbar[0]
	x_height = float(master.xHeight)
	stem = _h_left_stem_path(h_source, left_stem, right_stem, x_height)
	body = _layer_from_paths([stem], h_source.width)
	_weight, _center, _level, slope = _lowercase_stem_profile(body, x_height)
	_lower_ascender_stem(body, left_stem, x_height,
		shoulder_top=x_height, stem_slope=slope)
	body = _finish_candidate(body, remove_overlap=False)
	body, terminal_pair = _j_hook_body(body, h_source, master, horizontal_weight)
	body = _add_lowercase_dot(body, h_source, master, dot_shape)
	_align_j_terminal_pair(terminal_pair, horizontal_weight)
	body.correctPathDirection()
	return body


def _j_body_for_ft(font, master):
	"""Copy j's descending body, excluding its dot without counting nodes."""
	source = _copy_decomposed(_source_layer(font, "j", master.id))
	paths = [path for path in source.paths if path.closed
		and min(float(node.y) for node in _oncurve_nodes(path)) < -EPSILON
		and max(float(node.y) for node in _oncurve_nodes(path)) > float(master.xHeight) * 0.5]
	if not paths:
		raise GenerationError("j needs an upright and a descending hook to build f/t.")
	body = _layer_from_paths([max(paths, key=_bounds_area)], source.width)
	path = body.paths[0]
	# The blunt terminal is the short, vertical straight cut below baseline.
	# Read that construction landmark, not a Bézier bounding-box extremum.
	pairs = []
	for node in path.nodes:
		if node.type == OFFCURVE:
			continue
		for neighbor in _adjacent_nodes(path, node):
			if neighbor.type == OFFCURVE or node == neighbor:
				continue
			if (abs(float(node.x) - float(neighbor.x)) <= EPSILON
				and max(float(node.y), float(neighbor.y)) < -EPSILON
				and abs(float(node.y) - float(neighbor.y)) > EPSILON):
				pairs.append((node, neighbor))
	if not pairs:
		raise GenerationError("Could not identify j's blunt terminal cut below baseline.")
	terminal = min(pairs, key=lambda pair: sum(float(node.x) for node in pair))
	return body, terminal


def _build_ft(font, master, character):
	"""Rigidly reuse j's hook, then overlap a whole-unit H-weight crossbar."""
	body, terminal = _j_body_for_ft(font, master)
	x_height = float(master.xHeight)
	width, axis, level, slope = _lowercase_stem_profile(body, x_height)
	_H, _left, _right, crossbar = _measure_H_source(
		_source_layer(font, "H", master.id), master)
	bar_weight = max(1, round((crossbar[1] - crossbar[0])
		* LOWERCASE_FT_CROSSBAR_WEIGHT_FACTOR))
	h_source = _copy_decomposed(_source_layer(font, "h", master.id))
	ascender = _bounds_values(h_source)[3]
	if ascender <= x_height + EPSILON:
		raise GenerationError("h needs an ascender above x-height to build f/t.")
	bottom = _bounds_values(body)[1]
	bar_y = round(x_height * LOWERCASE_FT_CROSSBAR_HEIGHT_FACTOR)
	top = ascender if character == "f" else min(ascender,
		max(x_height * LOWERCASE_T_HEIGHT_FACTOR, bar_y + bar_weight * 1.5))
	# Move only the original upright cap to obtain the required body height.
	# The lower hook and every one of its handles remain untouched.
	_lower_ascender_stem(body, (axis - width * 0.5, axis + width * 0.5),
		top + bottom, shoulder_top=x_height * 0.60, stem_slope=slope,
		allow_extend=True)
	for path in body.paths:
		for node in path.nodes:
			x, y = _point(node)
			node.position = (2.0 * axis - x,
				top + bottom - y if character == "f" else y - bottom)
	body.correctPathDirection()
	bar_right = round(sum(float(node.x) for node in terminal) * 0.5)
	# Measure the final grid-fitted stem so rounding a slanted outline cannot
	# change the requested left/right overhang ratio after construction.
	body = _round_candidate_geometry(body)
	interval = _scan_x_intersections(body, bar_y)
	if len(interval) < 2:
		raise GenerationError("Could not locate f/t's upright at its crossbar.")
	right_overhang = bar_right - interval[-1]
	if right_overhang <= EPSILON:
		raise GenerationError("j's terminal needs to project past the upright to build f/t.")
	bar_left = round(interval[0] - right_overhang * LOWERCASE_FT_CROSSBAR_LEFT_OVERHANG)
	bar_bottom = round(bar_y - bar_weight * 0.5)
	bar = _layer_from_paths([_rectangle_path(bar_left, bar_bottom,
		bar_right, bar_bottom + bar_weight)], body.width)
	bar.correctPathDirection()
	body.shapes.append(bar.paths[0].copy())
	# Keep the requested two clean, correctly wound overlapping shapes.
	return _finish_candidate(body, remove_overlap=False)


def _build_n(font, master):
	source = _source_layer(font, "h", master.id)
	copy, left_stem, _right_stem = _measure_h_source(source, master)
	_lower_ascender_stem(copy, left_stem, float(master.xHeight))
	copy.width = source.width
	return _finish_candidate(copy)


def _h_shoulder_boundary_pairs(
	path, left_stem, right_stem, x_height, ignore_stem_join_connectors=False,
):
	"""Pair corresponding inner/outer drawable segments of h's shoulder."""
	_inner_cut, _outer_cut, shoulder = _h_shoulder_arc(
		path, left_stem, right_stem, x_height
	)
	segments = _arc_drawable_segments(shoulder)
	bottom_index = min(
		(
			index
			for index, node in enumerate(shoulder)
			if node.type != OFFCURVE
		),
		key=lambda index: float(shoulder[index].y),
	)
	inner_segments = [
		segment for segment in segments
		if segment[4] < bottom_index
		and segment[2][3][0] > segment[2][0][0] + EPSILON
	]
	outer_segments = [
		segment for segment in segments
		if segment[3] > bottom_index
		and segment[2][3][0] < segment[2][0][0] - EPSILON
	]
	if ignore_stem_join_connectors:
		# b/p/d/q only borrow the weight of h's first shoulder stroke. A short
		# ledge at the stem is a junction detail, not an extra stroke
		# boundary. Exclude it from measurement, without deleting/moving nodes
		# or changing m/r's existing topology requirements. Keep actual angular
		# shoulders (including square horizontal shoulders) in the measurement.
		join_tolerance = max(2.0, (left_stem[1] - left_stem[0]) * 0.10)

		def is_stem_join_connector(segment, endpoint_index):
			start, end = segment[2][0], segment[2][3]
			return (
				not segment[5]
				and (segment[3] == endpoint_index or segment[4] == endpoint_index)
				and ((start[0] - end[0]) ** 2
					+ (start[1] - end[1]) ** 2) ** 0.5 <= join_tolerance + EPSILON
				and max(abs(start[0] - left_stem[1]),
					abs(end[0] - left_stem[1])) <= join_tolerance + EPSILON
			)

		inner_segments = [segment for segment in inner_segments
			if not is_stem_join_connector(segment, 0)]
		outer_segments = [segment for segment in outer_segments
			if not is_stem_join_connector(segment, len(shoulder) - 1)]
	if not inner_segments or len(inner_segments) != len(outer_segments):
		raise GenerationError(
			"Could not pair h's inner and outer shoulder segments."
		)
	pairs = []
	for inner_segment, outer_segment in zip(
		inner_segments, reversed(outer_segments)
	):
		inner_nodes = list(
			shoulder[inner_segment[3]:inner_segment[4] + 1]
		)
		outer_nodes = list(reversed(
			shoulder[outer_segment[3]:outer_segment[4] + 1]
		))
		if (
			len(inner_nodes) != len(outer_nodes)
			or bool(inner_segment[5]) != bool(outer_segment[5])
		):
			raise GenerationError(
				"h's shoulder boundaries do not have matching segment topology."
			)
		pairs.append((inner_nodes, outer_nodes, bool(inner_segment[5])))
	return pairs


def _boundary_group_cubics(group):
	inner_nodes, outer_nodes, curve_types = group
	inner_points = tuple(_point(node) for node in inner_nodes)
	outer_points = tuple(_point(node) for node in outer_nodes)
	if isinstance(curve_types, tuple):
		inner_is_curve, outer_is_curve = curve_types
	else:
		inner_is_curve = outer_is_curve = bool(curve_types)

	def cubic_points(points, is_curve):
		if is_curve:
			if len(points) != 4:
				raise GenerationError(
					"Expected four nodes for a cubic stroke boundary."
				)
			return points
		if len(points) != 2:
			raise GenerationError(
				"Expected two nodes for a straight stroke boundary."
			)
		return (
			points[0],
			_lerp(points[0], points[1], 1.0 / 3.0),
			_lerp(points[0], points[1], 2.0 / 3.0),
			points[1],
		)

	return (
		cubic_points(inner_points, inner_is_curve),
		cubic_points(outer_points, outer_is_curve),
	)


def _shoulder_group_thickness(group):
	"""Median true perpendicular thickness from local normal intersections."""
	inner, outer = _boundary_group_cubics(group)
	center = tuple(
		_lerp(inner_point, outer_point, 0.5)
		for inner_point, outer_point in zip(inner, outer)
	)

	def normal_intersection(points, center_point, normal, guess):
		def value(factor):
			point = _cubic_point(points, factor)
			return _cross(
				normal,
				(point[0] - center_point[0], point[1] - center_point[1]),
			)

		roots = []
		previous_factor = 0.0
		previous_value = value(previous_factor)
		if abs(previous_value) <= EPSILON:
			roots.append(previous_factor)
		for step in range(1, 65):
			factor = step / 64.0
			current_value = value(factor)
			if abs(current_value) <= EPSILON:
				roots.append(factor)
			elif previous_value * current_value < 0.0:
				low, high = previous_factor, factor
				low_value = previous_value
				for _refinement in range(50):
					middle = (low + high) * 0.5
					middle_value = value(middle)
					if abs(middle_value) <= EPSILON:
						low = high = middle
						break
					if low_value * middle_value <= 0.0:
						high = middle
					else:
						low = middle
						low_value = middle_value
				roots.append((low + high) * 0.5)
			previous_factor = factor
			previous_value = current_value
		if not roots:
			raise GenerationError(
				"Could not intersect a normal with h's shoulder boundaries."
			)
		factor = min(roots, key=lambda item: abs(item - guess))
		return _cubic_point(points, factor)

	values = []
	for factor in (0.35, 0.5, 0.65):
		center_point = _cubic_point(center, factor)
		tangent = _cubic_tangent(center, factor)
		length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
		if length <= EPSILON:
			continue
		normal = (-tangent[1] / length, tangent[0] / length)
		inner_point = normal_intersection(
			inner, center_point, normal, factor
		)
		outer_point = normal_intersection(
			outer, center_point, normal, factor
		)
		values.append((
			(inner_point[0] - outer_point[0]) ** 2
			+ (inner_point[1] - outer_point[1]) ** 2
		) ** 0.5)
	if not values:
		raise GenerationError("Could not measure h's shoulder thickness.")
	values.sort()
	return values[len(values) // 2]


def _compensate_line_shoulder_corner(groups, target_widths):
	"""Fit a faceted arch's shared corner without shifting its stem joins.

	The two facets have different normals. Averaging their corrections loses
	weight on one side; solve both perpendicular measurements together instead.
	Only the inner/outer corner pair moves, symmetrically about its centerline.
	"""
	inner = groups[0][0][-1]
	outer = groups[0][1][-1]
	tolerances = [max(0.5, target * 0.001) for target in target_widths]
	for _iteration in range(5):
		current = [_shoulder_group_thickness(group) for group in groups]
		if all(abs(value - target) <= tolerance for value, target, tolerance in zip(current, target_widths, tolerances)):
			return current, tolerances
		positions = (_point(inner), _point(outer))
		derivatives = []
		for axis in ("x", "y"):
			setattr(inner, axis, float(getattr(inner, axis)) + 0.1)
			setattr(outer, axis, float(getattr(outer, axis)) - 0.1)
			derivatives.append([
				(_shoulder_group_thickness(group) - value) / 0.1
				for group, value in zip(groups, current)
			])
			inner.x, inner.y = positions[0]
			outer.x, outer.y = positions[1]
		a, c = derivatives[0]
		b, d = derivatives[1]
		determinant = a * d - b * c
		if abs(determinant) < 0.000001:
			raise GenerationError("h's faceted shoulder has ambiguous stroke normals.")
		e0, e1 = [target - value for target, value in zip(target_widths, current)]
		dx = (d * e0 - b * e1) / determinant
		dy = (a * e1 - c * e0) / determinant
		length = (dx * dx + dy * dy) ** 0.5
		limit = max(0.5, max(target_widths) * 0.05)
		factor = min(1.0, limit / max(EPSILON, length))
		inner.x += dx * factor
		inner.y += dy * factor
		outer.x -= dx * factor
		outer.y -= dy * factor
	final = [_shoulder_group_thickness(group) for group in groups]
	if any(abs(value - target) > tolerance for value, target, tolerance in zip(final, target_widths, tolerances)):
		raise GenerationError("Could not preserve h's faceted shoulder weight for m.")
	return final, tolerances


def _compensate_shoulder_groups(groups, target_widths, fixed_nodes=(), tangent_axes=()):
	"""Restore curved stroke weight while preserving each segment centerline."""
	if (
		fixed_nodes and len(groups) == 2
		and all(not group[2] for group in groups)
		and groups[0][0][-1].index == groups[1][0][0].index
		and groups[0][1][-1].index == groups[1][1][0].index
	):
		return _compensate_line_shoulder_corner(groups, target_widths)
	fixed_positions = [(node, _point(node)) for node in fixed_nodes]
	for _iteration in range(5):
		current_widths = [
			_shoulder_group_thickness(group) for group in groups
		]
		tolerances = [
			max(0.5, target * 0.001) for target in target_widths
		]
		if all(
			abs(current - target) <= tolerance
			for current, target, tolerance in zip(
				current_widths, target_widths, tolerances
			)
		):
			return current_widths, tolerances
		proposals = {}
		for group, target, current in zip(
			groups, target_widths, current_widths
		):
			# With fixed attachments, only the interior of a segment moves.
			# A line has just its other end available, so compensate its half
			# contribution rather than repeatedly under-correcting the weight.
			gain = 2.5 if fixed_positions and not group[2] else 1.5 if fixed_positions else 1.0
			factor = max(0.95, min(1.05, (target / current) ** gain))
			inner_nodes, outer_nodes, _is_curve = group
			centers = [
				_lerp(_point(inner), _point(outer), 0.5)
				for inner, outer in zip(inner_nodes, outer_nodes)
			]
			for index, (inner, outer) in enumerate(
				zip(inner_nodes, outer_nodes)
			):
				if index == 0:
					tangent = (
						centers[1][0] - centers[0][0],
						centers[1][1] - centers[0][1],
					)
				elif index == len(centers) - 1:
					tangent = (
						centers[-1][0] - centers[-2][0],
						centers[-1][1] - centers[-2][1],
					)
				else:
					tangent = (
						centers[index + 1][0] - centers[index - 1][0],
						centers[index + 1][1] - centers[index - 1][1],
					)
				length = (tangent[0] ** 2 + tangent[1] ** 2) ** 0.5
				if length <= EPSILON:
					continue
				tangent = (tangent[0] / length, tangent[1] / length)
				normal = (-tangent[1], tangent[0])
				center = centers[index]
				vector = (
					float(inner.x) - center[0],
					float(inner.y) - center[1],
				)
				along = vector[0] * tangent[0] + vector[1] * tangent[1]
				across = vector[0] * normal[0] + vector[1] * normal[1]
				new_inner = (
					center[0] + along * tangent[0] + across * factor * normal[0],
					center[1] + along * tangent[1] + across * factor * normal[1],
				)
				new_outer = (
					2.0 * center[0] - new_inner[0],
					2.0 * center[1] - new_inner[1],
				)
				# PyObjC can return a different Python wrapper for the same GSNode.
				# Its contour index is stable, unlike id(), and merges proposals at
				# shared shoulder extrema instead of applying them twice.
				proposals.setdefault(int(inner.index), (inner, []))[1].append(new_inner)
				proposals.setdefault(int(outer.index), (outer, []))[1].append(new_outer)
		for node, positions in proposals.values():
			node.x = sum(point[0] for point in positions) / len(positions)
			node.y = sum(point[1] for point in positions) / len(positions)
		# Stem attachments must not be compensated into a taper or a kink.
		for node, point in fixed_positions:
			node.x, node.y = point
		for anchor, handles, axis in tangent_axes:
			for handle in handles:
				setattr(handle, axis, float(getattr(anchor, axis)))
	final_widths = [_shoulder_group_thickness(group) for group in groups]
	tolerances = [max(0.5, target * 0.001) for target in target_widths]
	if any(
		abs(current - target) > tolerance
		for current, target, tolerance in zip(
			final_widths, target_widths, tolerances
		)
	):
		raise GenerationError(
			"Curved-stroke compensation did not converge within %.2f units "
			"(%s → %s)."
			% (
				max(tolerances),
				", ".join("%.2f" % value for value in target_widths),
				", ".join("%.2f" % value for value in final_widths),
			)
		)
	return final_widths, tolerances


def _narrow_h_shoulder(layer, left_stem, right_stem, x_height, factor=0.90):
	"""Narrow h's shoulder centerline while retaining its curved stroke weight."""
	path = max((path for path in layer.paths if path.closed), key=_bounds_area)
	groups = _h_shoulder_boundary_pairs(
		path, left_stem, right_stem, x_height
	)
	source_widths = [_shoulder_group_thickness(group) for group in groups]
	first_inner, first_outer, _first_curve = groups[0]
	last_inner, last_outer, _last_curve = groups[-1]
	left_center = (
		float(first_inner[0].x) + float(first_outer[0].x)
	) * 0.5
	right_center = (
		float(last_inner[-1].x) + float(last_outer[-1].x)
	) * 0.5
	span = right_center - left_center
	if span <= EPSILON:
		raise GenerationError("Could not measure h's shoulder width for m.")
	delta = -span * (1.0 - float(factor))
	attachments = (first_inner[0], first_outer[0], last_inner[-1], last_outer[-1])
	tangent_axes = []
	for node in path.nodes:
		if node.type == OFFCURVE:
			continue
		handles = [item for item in _adjacent_nodes(path, node) if item.type == OFFCURVE]
		for axis in ("x", "y"):
			if handles and all(
				abs(float(getattr(item, axis)) - float(getattr(node, axis))) <= EPSILON
				for item in handles
			):
				tangent_axes.append((node, handles, axis))
				break
	# Isolate the entire right stem by contour order, not a scanline x cutoff.
	# A one-unit slant or a serif can put its foot left of the measured edge.
	stem_nodes = [last_inner[-1]] + _forward_between(path, last_inner[-1], last_outer[-1])
	stem_indices = {int(node.index) for node in stem_nodes}
	# Calculate every displacement from the unchanged source. Shared extrema
	# belong to two segment groups, and fresh PyObjC wrappers do not have a
	# stable Python identity. Track their contour indices instead.
	displacements = {}
	for inner_nodes, outer_nodes, _is_curve in groups:
		for inner, outer in zip(inner_nodes, outer_nodes):
			center_x = (float(inner.x) + float(outer.x)) * 0.5
			progress = max(0.0, min(1.0, (center_x - left_center) / span))
			for node in (inner, outer):
				displacements.setdefault(int(node.index), delta * progress)
	for node in path.nodes:
		index = int(node.index)
		if index in stem_indices:
			node.x = float(node.x) + delta
		elif index in displacements:
			node.x = float(node.x) + displacements[index]
	_compensate_shoulder_groups(groups, source_widths, attachments, tangent_axes)
	return (
		(float(right_stem[0]) + delta, float(right_stem[1]) + delta),
		delta,
		source_widths,
		[_shoulder_group_thickness(group) for group in groups],
	)


def _build_m(font, master):
	source = _source_layer(font, "h", master.id)
	first, left_stem, right_stem = _measure_h_source(source, master)
	x_height = float(master.xHeight)
	lower_stem, _unused = _measure_stems(first, x_height * 0.10)
	stem_slope = (
		(sum(left_stem) - sum(lower_stem)) * 0.5 / (x_height * 0.10)
	)
	right_stem, shoulder_delta, _source_widths, _final_widths = (
		_narrow_h_shoulder(
			first, left_stem, right_stem, float(master.xHeight), 0.94
		)
	)
	second = first.copy()

	# Identify the shoulder while the ascender is still taller than the arch.
	# The topology test is independent of stem slant, serif overhang, and extra
	# extrema, unlike the former exact-x comparison.
	closed_paths = [path for path in second.paths if path.closed]
	if not closed_paths:
		raise GenerationError("The h source has no closed outline for m.")
	second_path = max(closed_paths, key=_bounds_area)
	inner_cut, outer_cut, shoulder_nodes = _h_shoulder_arc(
		second_path, left_stem, right_stem, float(master.xHeight)
	)
	shoulder_top = max(float(node.y) for node in shoulder_nodes if node.type != OFFCURVE)
	# Translate the cap along the actual stem direction. Moving it vertically
	# alone makes a slanted left stem thinner when its ascender is shortened.
	_lower_ascender_stem(first, left_stem, x_height, shoulder_top, stem_slope)
	# Resolve only the ascender feature's self-overlap. The two separate m
	# shapes still remain deliberately unmerged in the final candidate.
	first = _finish_candidate(first)

	# The h's two stems can differ slightly, especially in heavier masters.
	# Match both edges rather than reusing a fixed or single-edge offset.
	_align_stem_interval(second, left_stem, right_stem)

	# Pull only the outer cut point into the shared stem. Its handle stays where
	# h placed it, matching the manual recipe and retaining the shoulder curve.
	stem_width = right_stem[1] - right_stem[0]
	outer_cut.x = float(right_stem[1]) - max(1.0, stem_width * 0.20)
	shoulder = GSPath()
	shoulder.closed = True
	for index, node in enumerate(shoulder_nodes):
		shoulder.nodes.append(
			_copy_node(
				node,
				LINE if index == 0 else node.type,
				False if index in (0, len(shoulder_nodes) - 1) else node.smooth,
			)
		)

	candidate = GSLayer()
	for path in first.paths:
		candidate.shapes.append(path.copy())
	candidate.shapes.append(shoulder)
	candidate.width = round(
		float(source.width)
		+ shoulder_delta
		+ right_stem[1]
		- left_stem[1]
	)
	return _finish_candidate(candidate, remove_overlap=False)


def _build_u(font, master):
	candidate = _build_n(font, master)
	x_height = float(master.xHeight)
	advance = float(candidate.width)
	for path in candidate.paths:
		for node in path.nodes:
			node.y = x_height - float(node.y)
			node.x = advance - float(node.x)
	candidate.correctPathDirection()
	return candidate


def _C_terminal_stroke_direction(font, master, label):
	"""Direction toward C's cut, from handles or straight neighboring edges."""
	copy = _copy_decomposed(_source_layer(font, "C", master.id))
	closed = [path for path in copy.paths if path.closed]
	if len(closed) != 1:
		raise GenerationError("C must have one closed contour to define r's cut.")
	path = closed[0]
	run = _complete_C_terminal_runs(path)[0][label]
	vectors = []
	for anchor in (run[0], run[-1]):
		neighbors = [node for node in _adjacent_nodes(path, anchor) if node not in run]
		if len(neighbors) != 1:
			raise GenerationError("Could not identify C's stroke direction at its terminal.")
		vectors.append((float(anchor.x - neighbors[0].x), float(anchor.y - neighbors[0].y)))
	direction = tuple(sum(vector[index] for vector in vectors) for index in (0, 1))
	length = (direction[0] ** 2 + direction[1] ** 2) ** 0.5
	if length <= EPSILON:
		raise GenerationError("C's terminal stroke has no measurable direction.")
	return direction[0] / length, direction[1] / length


def _build_r(font, master, stem_slope=0.0):
	source = _source_layer(font, "h", master.id)
	terminal_signature = _C_terminal_signatures(font, master)["top"]
	copy, left_stem, right_stem = _measure_h_source(source, master)
	if len(copy.paths) != 1:
		raise GenerationError("h must have one closed contour to derive r.")
	path = copy.paths[0]
	bounds = _bounds_values(copy)
	_inner_cut, _outer_cut, shoulder_arc = _h_shoulder_arc(
		path, left_stem, right_stem, float(master.xHeight)
	)
	segments = _arc_drawable_segments(shoulder_arc)
	bottom_index = min(
		(
			index
			for index, node in enumerate(shoulder_arc)
			if node.type != OFFCURVE
		),
		key=lambda index: float(shoulder_arc[index].y),
	)
	inner_segments = [
		segment for segment in segments
		if segment[4] < bottom_index
		and segment[2][3][0] > segment[2][0][0]
		and segment[2][3][1] < segment[2][0][1]
	]
	outer_segments = [
		segment for segment in segments
		if segment[3] > bottom_index
		and segment[2][3][0] < segment[2][0][0]
		and segment[2][3][1] > segment[2][0][1]
	]
	if inner_segments and outer_segments:
		inner_segment = max(
			inner_segments,
			key=lambda segment: max(segment[2][0][1], segment[2][3][1]),
		)
		outer_segment = max(
			outer_segments,
			key=lambda segment: max(segment[2][0][1], segment[2][3][1]),
		)
		inner_peak = inner_segment[0]
		outer_peak = outer_segment[1]
		inner_is_curve = inner_segment[5]
		outer_is_curve = outer_segment[5]
		inner_points = inner_segment[2]
		outer_points = tuple(reversed(outer_segment[2]))
	else:
		# A square h can have a horizontal shoulder followed by a vertical
		# stem, with no descending diagonal at all. Cut its last paired shoulder
		# segment directly; a straight source must remain straight in r.
		group = _h_shoulder_boundary_pairs(
			path, left_stem, right_stem, float(master.xHeight)
		)[-1]
		inner_nodes, outer_nodes, curve_types = group
		inner_peak, outer_peak = inner_nodes[0], outer_nodes[0]
		if isinstance(curve_types, tuple):
			inner_is_curve, outer_is_curve = curve_types
		else:
			inner_is_curve = outer_is_curve = bool(curve_types)
		inner_points, outer_points = _boundary_group_cubics(group)
	outer_left_bottom = min(
		_oncurve_nodes(path),
		key=lambda node: (
			abs(float(node.y) - bounds[1]),
			abs(float(node.x) - left_stem[0]),
		),
	)
	# Keep h's shoulder and C's complete corner profile. Carry C's cut angle
	# relative to its stroke, not its absolute canvas angle: C's nearly horizontal
	# cut would run along r's shoulder and turn expanded corners into a spike.
	center_points = tuple(
		_lerp(inner_point, outer_point, 0.5)
		for inner_point, outer_point in zip(inner_points, outer_points)
	)
	center_point = _cubic_point(center_points, R_SHOULDER_CUT)
	source_direction = _C_terminal_stroke_direction(font, master, "top")
	target_direction = _cubic_tangent(center_points, R_SHOULDER_CUT)
	target_length = (target_direction[0] ** 2 + target_direction[1] ** 2) ** 0.5
	if target_length <= EPSILON:
		raise GenerationError("h's shoulder has no measurable direction for r's cut.")
	target_direction = tuple(value / target_length for value in target_direction)
	cosine = sum(source_direction[index] * target_direction[index] for index in (0, 1))
	sine = _cross(source_direction, target_direction)
	dx, dy = terminal_signature["direction"]
	cut_direction = (dx * cosine - dy * sine, dx * sine + dy * cosine)
	center_point = _shared_parallel_cut_center(
		inner_points, outer_points, center_point, cut_direction
	)
	inner_left_curve, _inner_discarded = _split_cubic_at_ray(
		inner_points, center_point, cut_direction
	)
	outer_left_curve, _outer_discarded = _split_cubic_at_ray(
		outer_points, center_point, cut_direction
	)
	terminal_profile = _terminal_profile_points(
		terminal_signature,
		outer_left_curve[3],
		inner_left_curve[3],
	)
	initial = [outer_left_bottom] + _forward_between(
		path, outer_left_bottom, inner_peak
	)
	shoulder_top = max(
		float(node.y) for node in shoulder_arc if node.type != OFFCURVE
	)

	def candidate_with_profile(profile):
		new_path = GSPath()
		new_path.closed = True
		for node in initial:
			new_path.nodes.append(_copy_node(node))
		if inner_is_curve:
			new_path.nodes.append(_new_node(inner_left_curve[1], OFFCURVE))
			new_path.nodes.append(_new_node(inner_left_curve[2], OFFCURVE))
			new_path.nodes.append(_new_node(inner_left_curve[3], CURVE, False))
		else:
			new_path.nodes.append(_new_node(inner_left_curve[3], LINE, False))
		for point in tuple(reversed(profile))[1:]:
			new_path.nodes.append(_new_node(point, LINE, False))
		if outer_is_curve:
			new_path.nodes.append(_new_node(outer_left_curve[2], OFFCURVE))
			new_path.nodes.append(_new_node(outer_left_curve[1], OFFCURVE))
			new_path.nodes.append(_new_node(outer_left_curve[0], CURVE, True))
		else:
			new_path.nodes.append(_new_node(outer_left_curve[0], LINE, False))
		for node in _forward_between(path, outer_peak, outer_left_bottom)[:-1]:
			new_path.nodes.append(_copy_node(node))
		candidate = _layer_from_paths(
			[new_path], max(point[0] for point in profile)
			+ (float(source.width) - bounds[2]),
		)
		_lower_ascender_stem(candidate, left_stem, float(master.xHeight),
			shoulder_top=shoulder_top, stem_slope=stem_slope)
		return _round_candidate_geometry(_finish_candidate(candidate, remove_overlap=False))

	# A large C opening can still be oversized for a short, heavy r shoulder.
	# Bound just the corner extensions, keeping the cut anchors, curves, angle,
	# stroke weight and node topology fixed. Never close the source C's corners.
	for opening_scale in (1.0, 0.75, 0.5, 0.25, 0.125, 0.0625):
		profile = []
		for index, point in enumerate(terminal_profile):
			if index in (0, len(terminal_profile) - 1):
				profile.append(point)
			else:
				anchor = terminal_profile[0 if terminal_signature["points"][index][0] < 0.5 else -1]
				profile.append(_lerp(anchor, point, opening_scale))
		candidate = candidate_with_profile(profile)
		_left, bottom, _right, top = _bounds_values(candidate)
		if bottom < bounds[1] - 1.0 or top > max(shoulder_top, float(master.xHeight)) + 1.0:
			continue
		resolved = candidate.copy()
		resolved.removeOverlap()
		if len([contour for contour in resolved.paths if contour.direction == -1]) == 1:
			return candidate
	raise GenerationError("C's open-corner extensions cannot fit h's shoulder for r.")


def _build_bowl_stem(font, master, character):
	if character in ("d", "q"):
		# Mirror the proven left-stem construction. Besides keeping the family
		# relationship exact, this avoids weight-dependent Boolean splits on the
		# right side and guarantees the same contour topology as b/p.
		candidate = _build_bowl_stem(
			font, master, "b" if character == "d" else "p"
		)
		advance = float(candidate.width)
		for path in candidate.paths:
			for node in path.nodes:
				node.x = advance - float(node.x)
		candidate.correctPathDirection()
		return candidate
	if character == "p":
		# p is the vertical reflection of the complete b construction.  This
		# carries h's top and baseline serif logic to the x-height and descender
		# without inventing a replacement stem.
		candidate = _build_bowl_stem(font, master, "b")
		x_height = float(master.xHeight)
		for path in candidate.paths:
			for node in path.nodes:
				node.y = x_height - float(node.y)
		candidate.correctPathDirection()
		candidate.roundCoordinates()
		return candidate

	h_source = _source_layer(font, "h", master.id)
	o_source = _source_layer(font, "o", master.id)
	h_copy, left_stem, right_stem = _measure_h_source(h_source, master)
	bowl = _copy_decomposed(o_source)

	stem_path = _h_left_stem_path(
		h_copy,
		left_stem,
		right_stem,
		float(master.xHeight),
	)
	_remove_bowl_facing_bottom_serif(stem_path, left_stem)
	_straighten_stem_inner_edge(stem_path, left_stem)
	stem = _layer_from_paths([stem_path], 0)
	_align_bowl_to_left_stem(stem, bowl, stem_interval=left_stem)
	_apply_bowl_stem_join_recipe(
		bowl, left_stem, h_copy, right_stem, float(master.xHeight)
	)
	right_sidebearing = float(o_source.width) - _bounds_values(o_source)[2]
	width = _bounds_values(bowl)[2] + right_sidebearing

	candidate = GSLayer()
	for path in stem.paths:
		candidate.shapes.append(path.copy())
	for path in bowl.paths:
		candidate.shapes.append(path.copy())
	candidate.width = round(width)
	return _finish_candidate(candidate, remove_overlap=False)


def _refine_lowercase_arc_pair(first, second):
	"""Add exact subdivisions on copies, retaining every original landmark.

	Correspondence is by normalized arc length, not by source node count.
	Lines remain lines; cubic subdivisions use de Casteljau, not refitting.
	"""
	models = [_right_arc_boundary_model(arc) for arc in (first, second)]
	if len(models[0]) == len(models[1]):
		return first, second
	breaks = sorted(set([0.0, 1.0] + [s["end"] for model in models for s in model]))
	result = []
	for arc, model in zip((first, second), models):
		nodes = [arc[0]]
		for segment in model:
			span = segment["end"]-segment["start"]
			cuts = [max(0.0, min(1.0, (p-segment["start"])/span))
				for p in breaks if segment["start"]+1e-9 < p < segment["end"]-1e-9]
			points, previous = segment["points"], 0.0
			for factor in cuts+[1.0]:
				if factor < 1.0:
					piece, remainder = _split_cubic(points, (factor-previous)/(1.0-previous))
				else:
					piece, remainder = points, None
				if segment["curve"]:
					nodes.extend([_new_node(piece[1], OFFCURVE), _new_node(piece[2], OFFCURVE)])
				nodes.append(segment["nodes"][-1] if factor == 1.0 else
					_new_node(piece[3], CURVE if segment["curve"] else LINE, segment["curve"]))
				points, previous = remainder, factor
		result.append(nodes)
	return tuple(result)


def _replace_lowercase_arc(path, original, refined):
	# Keep original endpoints and the untouched complementary contour.
	start, end = original[0], original[-1]
	if [start]+_forward_between(path, start, end) != original:
		path.reverse()
	complement = _forward_between(path, end, start)[:-1]
	path.nodes = list(refined)+complement


def _refine_lowercase_round(layer):
	"""Synchronize only unequal o quadrants before new a/g construction."""
	outer, inner = _outer_and_inner_paths(layer)
	landmarks = []
	for path in (outer, inner):
		top, right, bottom = _round_extrema(path)
		left = min(_oncurve_nodes(path), key=lambda n: float(n.x))
		landmarks.append((top, right, bottom, left))
	for quadrant in range(4):
		arcs = []
		for path, points in zip((outer, inner), landmarks):
			start, end = points[quadrant], points[(quadrant+1)%4]
			forward = [start]+_forward_between(path, start, end)
			reverse = list(reversed([end]+_forward_between(path, end, start)))
			arcs.append(min((forward, reverse), key=lambda arc:
				sum(_cubic_approximate_length(s[2]) for s in _arc_drawable_segments(arc))))
		refined = _refine_lowercase_arc_pair(*arcs)
		for path, arc, nodes in zip((outer, inner), arcs, refined):
			if nodes is not arc:
				_replace_lowercase_arc(path, arc, nodes)
	return layer


def _lowercase_join_recipe(bowl, stem, h, right_stem, x_height, stroke_factor=1.0):
	"""Reuse h's join recipe, with subdivision-tolerant shoulder measurement."""
	try:
		_apply_bowl_stem_join_recipe(bowl, stem, h, right_stem, x_height, stroke_factor)
		return
	except GenerationError as error:
		if "shoulder" not in str(error):
			raise
	path = max((p for p in h.paths if p.closed), key=_bounds_area)
	_start, _end, arc = _h_shoulder_arc(path, stem, right_stem, x_height)
	segments = _arc_drawable_segments(arc)
	bottom = min((i for i,n in enumerate(arc) if n.type != OFFCURVE), key=lambda i: float(arc[i].y))
	inside = [s for s in segments if s[4] < bottom and s[2][3][0] > s[2][0][0]+EPSILON]
	outside = [s for s in segments if s[3] > bottom and s[2][3][0] < s[2][0][0]-EPSILON]
	if not inside or not outside:
		raise GenerationError("Could not identify h's shoulder stroke for a/g.")
	inner_arc = list(arc[inside[0][3]:inside[-1][4]+1])
	outer_arc = list(reversed(arc[outside[0][3]:outside[-1][4]+1]))
	inner_model, outer_model = (_right_arc_boundary_model(a) for a in (inner_arc, outer_arc))
	weights = []
	for t in (0.15, 0.25, 0.35):
		def center(p):
			return _lerp(_boundary_model_point(inner_model,p), _boundary_model_point(outer_model,p),0.5)
		before, after = center(t-0.005), center(t+0.005)
		weights.append(_S_normal_thickness(h,center(t),(after[0]-before[0],after[1]-before[1])))
	target = sorted(weights)[1] * stroke_factor
	outer, inner = _outer_and_inner_paths(bowl)
	ot, _or, ob = _round_extrema(outer)
	it, _ir, ib = _round_extrema(inner)
	oa, ia = _left_arc_nodes(outer,ot,ob), _left_arc_nodes(inner,it,ib)
	if all(n.type == LINE for p in bowl.paths for n in p.nodes):
		_compensate_angular_bowl_joins(outer,oa,ia,target)
	else:
		_compensate_bowl_handles(oa,ia,[target]*len(_arc_drawable_segments(oa)),"a/g")


def _lowercase_a_belly(source, height, width_factor=0.94, stroke_factor=1.0):
	"""Compress o's centerlines, not its stroke thickness, for a's lower bowl."""
	reference = _refine_lowercase_round(_copy_decomposed(source))
	groups, outer, _inner = _round_contour_groups(reference)
	targets = [_shoulder_group_thickness(group) * stroke_factor for group in groups]
	# A heavy o cannot retain its weight inside an arbitrarily short belly.
	# Leave counter room instead of silently thinning it or crossing boundaries.
	height = max(float(height), max(targets) * 2.35)
	left, bottom, right, top = _bounds_values(outer)
	center = ((left + right) * 0.5, (bottom + top) * 0.5)
	fx, fy = float(width_factor), float(height) / (top - bottom)
	for _iteration in range(12):
		candidate = reference.copy()
		paired, _outer, _inner = _round_contour_groups(candidate)
		_transform_round_centerlines(groups, paired, center, center, fx, fy, targets,
			measure_group=lambda group: _bowl_stem_source_weight(
				_layer_from_paths(candidate.paths, source.width), group))
		candidate = _layer_from_paths(candidate.paths, source.width)
		bounds = _bounds_values(candidate)
		error = float(height) - (bounds[3] - bounds[1])
		if abs(error) <= 0.25:
			_translate_paths(candidate.paths, 0.0, bottom - bounds[1])
			return candidate
		fy += error / (top - bottom) * 0.6
		if fy <= EPSILON:
			break
	raise GenerationError("o's strokes cannot fit a's lower bowl height.")


def _lowercase_line_landmarks(source):
	"""Carry collinear subdivisions through facet construction by edge fraction.

	The working landmarks describe the same polygon. The returned restorer
	puts every extra point back on its transformed edge, so an extra point does
	not acquire an independent compensation factor and bend a straight facet.
	"""
	working = _copy_decomposed(source)
	saved = [list(p.nodes) for p in working.paths]
	for path in working.paths:
		_lowercase_collinear_landmarks(path)
	_round_contour_groups(working)
	mappings = []
	for original,path in zip(saved,working.paths):
		corners = list(path.nodes)
		entries = []
		for node in original:
			if node in corners:
				entries.append((corners.index(node),None,None))
				continue
			for i,first in enumerate(corners):
				last = corners[(i+1)%len(corners)]
				dx,dy = last.x-first.x,last.y-first.y
				length2 = dx*dx+dy*dy
				if length2 <= EPSILON:
					continue
				t = ((node.x-first.x)*dx+(node.y-first.y)*dy)/length2
				if 0 <= t <= 1 and abs(_cross((dx,dy),(node.x-first.x,node.y-first.y))) <= EPSILON:
					entries.append((i,(i+1)%len(corners),t))
					break
			else:
				raise GenerationError("Could not retain o's extra facet node.")
		mappings.append((corners,entries))
	def restore(candidate):
		for path,(corners,entries) in zip(candidate.paths,mappings):
			# Pair by original semantic order before any native overlap clipping.
			current = list(path.nodes)
			if len(current) != len(corners):
				raise GenerationError("o's facet landmarks changed during construction.")
			path.nodes = [_copy_node(current[i]) if j is None else
				_new_node(_lerp(_point(current[i]),_point(current[j]),t),LINE,False)
				for i,j,t in entries]
		return candidate
	return working,restore


def _lowercase_right_bowl(font, master, belly_height=None, belly_width_factor=0.94, stroke_factor=1.0,
	straight_attachment=False):
	"""A short mirrored b: both attachments retain h's shoulder weight."""
	h_source = _source_layer(font, "h", master.id)
	o_source = _source_layer(font, "o", master.id)
	h_copy, left_stem, right_stem = _measure_h_source(h_source, master)
	x_height = float(master.xHeight)
	restore_facets = None
	if all(n.type == LINE for p in o_source.paths for n in p.nodes):
		o_source,restore_facets = _lowercase_line_landmarks(o_source)
	bowl = (_refine_lowercase_round(_copy_decomposed(o_source)) if belly_height is None
		else _lowercase_a_belly(o_source, belly_height, belly_width_factor, stroke_factor))
	stem_path = _h_left_stem_path(h_copy, left_stem, right_stem, x_height)
	_remove_bowl_facing_bottom_serif(stem_path, left_stem)
	_straighten_stem_inner_edge(stem_path, left_stem)
	stem = _layer_from_paths([stem_path], 0)
	stem_top = x_height if belly_height is None else min(x_height * 0.72,
		x_height * 0.58 + max(0.0, _bounds_values(bowl)[3]-_bounds_values(bowl)[1]
			-x_height*0.60)*0.9)
	_lower_ascender_stem(stem, left_stem, stem_top, shoulder_top=stem_top * 0.5)
	_align_bowl_to_left_stem(stem, bowl, stem_interval=left_stem,
		extreme_tolerance=0.5 if belly_height is not None else EPSILON)
	pristine = bowl.copy() if straight_attachment else None
	try:
		_lowercase_join_recipe(bowl, left_stem, h_copy, right_stem, x_height, stroke_factor)
	except GenerationError:
		if not straight_attachment:
			raise
		# a replaces this side with a straight entry and an optical lower
		# attachment. A rigid handle-only fit at every extra subdivision can
		# be over-constrained there. Restart from the compensated o, whose
		# normal weights were already verified, not the partly failed fit.
		bowl = pristine
		outer,_inner = _outer_and_inner_paths(bowl)
		left = min(_oncurve_nodes(outer),key=lambda node:node.x)
		_move_extreme_with_handles(outer,left,dx=(left_stem[0]+left_stem[1])*0.5-left.x)
	if restore_facets is not None:
		bowl = restore_facets(bowl)
	# An angular o's offset edges can meet beyond the stem's outside edge.
	# Clip that tip rather than rotating the facets or narrowing the stem.
	bow_left, bow_bottom, bow_right, bow_top = _bounds_values(bowl)
	if bow_left < left_stem[0]-EPSILON and all(
		n.type == LINE for p in bowl.paths for n in p.nodes
	):
		padding = max(1000.0, bow_top-bow_bottom, bow_right-bow_left)
		mask = _layer_from_paths([_rectangle_path(left_stem[0],
			bow_bottom-padding, bow_right+padding, bow_top+padding)], 0)
		mask.correctPathDirection()
		bowl.correctPathDirection()
		clipped = intersectPaths([p.copy() for p in bowl.paths],
			[p.copy() for p in mask.paths])
		if not clipped:
			raise GenerationError("Could not align the angular bowl with h's stem.")
		bowl = _layer_from_paths(clipped, bowl.width)
		bowl.correctPathDirection()
	advance = _bounds_values(bowl)[2] + float(o_source.width) - _bounds_values(o_source)[2]
	candidate = _layer_from_paths(list(stem.paths) + list(bowl.paths), advance)
	for path in candidate.paths:
		for node in path.nodes:
			node.x = advance - float(node.x)
	candidate.correctPathDirection()
	return candidate, (advance - left_stem[1], advance - left_stem[0]), stem_top


def _lowercase_collinear_landmarks(landmark):
	"""Simplify only exact collinear points on a temporary landmark model."""
	for _attempt in range(len(landmark.nodes)):
		removed = False
		nodes = list(landmark.nodes)
		for i,n in enumerate(nodes):
			previous, following = nodes[(i-1)%len(nodes)],nodes[(i+1)%len(nodes)]
			if n.type != LINE or following.type != LINE or previous.type == OFFCURVE:
				continue
			a = (n.x-previous.x,n.y-previous.y)
			b = (following.x-n.x,following.y-n.y)
			if abs(_cross(a,b)) < 1e-6 and a[0]*b[0]+a[1]*b[1] > 0:
				del landmark.nodes[i]
				removed = True
				break
		if not removed:
			break
	return landmark


def _lowercase_terminal_runs(path):
	"""Recognize cap landmarks independently of harmless line subdivisions."""
	landmark = _lowercase_collinear_landmarks(path.copy())
	original = list(path.nodes)
	selected = _complete_C_terminal_runs(landmark)[0]
	result = {}
	for label, run in selected.items():
		anchors = [min(original,key=lambda n: (n.x-p.x)**2+(n.y-p.y)**2) for p in (run[0],run[-1])]
		forward = [anchors[0]]+_forward_between(path,*anchors)
		reverse = list(reversed([anchors[1]]+_forward_between(path,anchors[1],anchors[0])))
		result[label] = tuple(min((forward,reverse),key=len))
	return result


def _lowercase_visible_outline(layer):
	"""Validation copy of Glyphs' drawn contour, with invisible corners resolved.

	Raw removeOverlap treats editable Open Corners as separate tiny triangles.
	Use the native drawing contour for intersection checks; never replace the
	editable construction with this copy.
	"""
	bezier = layer.bezierPath
	paths, path = [], None
	for index in range(bezier.elementCount()):
		kind, points = bezier.elementAtIndex_associatedPoints_(index)
		if kind == NSMoveToBezierPathElement:
			path = GSPath()
			path.nodes.append(_new_node((points[0].x, points[0].y)))
		elif kind == NSLineToBezierPathElement:
			path.nodes.append(_new_node((points[0].x, points[0].y)))
		elif kind == NSCurveToBezierPathElement:
			for point in points[:2]:
				path.nodes.append(_new_node((point.x, point.y), OFFCURVE))
			path.nodes.append(_new_node((points[2].x, points[2].y), CURVE))
		elif kind == NSClosePathBezierPathElement:
			nodes = list(path.nodes)
			if len(nodes) > 1 and _point(nodes[0]) == _point(nodes[-1]):
				nodes[0].type = nodes[-1].type
				del path.nodes[len(nodes)-1]
			path.closed = True
			paths.append(path)
			path = None
		else:
			raise GenerationError("Unsupported element in Glyphs' drawn contour.")
	# Glyphs' native Path can end with a move-only subpath after closepath.
	if path is not None and len(path.nodes) > 1:
		raise GenerationError("Glyphs' drawn contour is not closed.")
	return _layer_from_paths(paths, layer.width)


def _lowercase_c_half(font, master, upper, stem_interval, root_y, height, width,
	optical_height=None, weight_factor=1.0, top_weight=None):
	"""Mirror a compensated c half, keeping its complete terminal profile.

	Only the stem-facing attachment is retargeted. The source's facets stay
	facets; cubic body tangents stay cubic, including subdivided contours.
	"""
	source = _source_layer(font, "c", master.id)
	reference = _copy_decomposed(source)
	path = reference.paths[0]
	# Exact straight-edge subdivisions carry no shape information. Collapse
	# them on this detached construction copy so native Open Corner detection
	# sees the original corner edges; preserve all actual bends and cubics.
	_lowercase_collinear_landmarks(path)
	runs = _lowercase_terminal_runs(path)
	terminal_indices = {label: tuple(list(path.nodes).index(n) for n in run) for label,run in runs.items()}
	run = runs["top" if upper else "bottom"]
	a, b = _point(run[0]), _point(run[-1])
	dx, dy = b[0] - a[0], b[1] - a[1]
	length2 = dx * dx + dy * dy
	if length2 <= EPSILON * EPSILON:
		raise GenerationError("c has a zero-length terminal profile.")
	# Store every cap node in its own chord frame before the compensated
	# body helper temporarily sharpens Open Corner expansion points.
	profile = [(((n.x-a[0])*dx + (n.y-a[1])*dy) / length2,
		((n.x-a[0])*(-dy) + (n.y-a[1])*dx) / length2) for n in run]
	# An Open Corner's flank can run BACK along its body tangent. Retain
	# signed tangent/normal offsets rather than treating it as a positive reach.
	corner_frames = []
	for anchor in (run[0], run[-1]):
		neighbor = next(n for n in _adjacent_nodes(path, anchor) if n not in run)
		vector = (anchor.x-neighbor.x, anchor.y-neighbor.y)
		length = (vector[0]**2+vector[1]**2)**0.5
		if length <= EPSILON:
			raise GenerationError("c's terminal has a zero-length body tangent.")
		corner_frames.append((_point(anchor), (vector[0]/length, vector[1]/length)))
	left, bottom, right, top = _bounds_values(reference)
	fx, fy = float(width) / (right-left), float(height)*2.0 / (top-bottom)
	# a's short upper arch needs optical relief in the heaviest weights. Its
	# belly keeps o's weight; never close the opening just to keep a c-sized arch.
	stroke_factor = float(weight_factor)
	if upper or optical_height is not None:
		sharp = reference.copy()
		sharp_runs = {label: tuple(sharp.paths[0].nodes[i] for i in indices) for label,indices in terminal_indices.items()}
		for terminal in sharp_runs.values():
			_sharpen_C_terminal_corners(sharp.paths[0], terminal)
		outer_model, inner_model, _path, _runs = _C_boundary_models(sharp,
			{label:(run[0],run[-1]) for label,run in sharp_runs.items()})
		weight = _boundary_model_thickness(outer_model, inner_model)
		stroke_factor = min(stroke_factor, float(height if optical_height is None else optical_height)/(weight*1.30))
	stem_left, stem_right = stem_interval
	for _iteration in range(20):
		body, _targets, _final, indices = _S_compensated_C(reference, fx, fy,
			measure_complete_outline=True, stroke_factor=stroke_factor,
			terminal_node_indices=terminal_indices)
		outer, inner = _S_C_bowl_arcs(body, upper, indices)
		if upper:
			outer, inner = _reverse_segment_sequence(outer), _reverse_segment_sequence(inner)
		root = _lerp(outer[0][0][0], inner[0][0][0], 0.5)
		target_root = ((stem_left+stem_right)*0.5, float(root_y))
		def mirror(sequence):
			return [(tuple((target_root[0]-(p[0]-root[0]),
				target_root[1]+p[1]-root[1]) for p in points), curve, s, e)
				for points, curve, s, e in sequence]
		outer, inner = mirror(outer), mirror(inner)
		outer = _retarget_sequence_endpoint(outer, True, (stem_right, root_y))
		inner = _retarget_sequence_endpoint(inner, True, (stem_left, root_y))
		outer = _straighten_sequence_endpoint_vertically(outer, True)
		inner = _straighten_sequence_endpoint_vertically(inner, True)
		if upper and top_weight is not None:
			outer_peak=max(max(p[1] for p in points) for points,_curve,_s,_e in outer)
			inner_peak=max(max(p[1] for p in points) for points,_curve,_s,_e in inner)
			span=inner_peak-root_y
			target_span=outer_peak-float(top_weight)-root_y
			if min(span,target_span)<=EPSILON:
				raise GenerationError("o's top stroke cannot fit a's upper arch.")
			inner=[(tuple((p[0],root_y+(p[1]-root_y)*target_span/span)
				for p in points),curve,s,e) for points,curve,s,e in inner]
		oa, ia = outer[-1][0][3], inner[-1][0][3]
		chord = (ia[0]-oa[0], ia[1]-oa[1])
		# Reflection reverses the cap frame's handedness.
		cap = [(oa[0]+u*chord[0]+v*chord[1],
			oa[1]+u*chord[1]-v*chord[0]) for u, v in profile]
		# Transport expansion points in the local body frame, preserving their
		# signed direction and reflection. A positive-only extension closes the
		# source's re-entrant Open Corners and leaves a redundant tip node.
		for index in range(1, len(cap)-1):
			u, _v = profile[index]
			if 0.0 <= u <= 1.0:
				continue
			sequence, anchor = (outer, oa) if u < 0.0 else (inner, ia)
			points, curved, _s, _e = sequence[-1]
			tangent = (points[3][0]-points[2 if curved else 0][0],
				points[3][1]-points[2 if curved else 0][1])
			length = (tangent[0]**2+tangent[1]**2)**0.5
			if length > EPSILON:
				source_anchor, source_tangent = corner_frames[0 if u < 0.0 else 1]
				offset = (run[index].x-source_anchor[0], run[index].y-source_anchor[1])
				along = sum(offset[i]*source_tangent[i] for i in (0, 1))
				across = _cross(source_tangent, offset)
				tx, ty = tangent[0]/length, tangent[1]/length
				scale = ((chord[0]**2+chord[1]**2)/length2)**0.5
				cap[index] = (anchor[0]+scale*(along*tx+across*ty),
					anchor[1]+scale*(along*ty-across*tx))
		# A long Open Corner expansion can cross the resized body. Bound only
		# that expansion, retaining every cap node and its across-stroke cut.
		for opening in (1.0, 0.75, 0.5, 0.25, 0.125, 0.0625):
			fitted_cap = [point if index in (0, len(cap)-1) else _lerp(
				cap[0 if profile[index][0] < 0.5 else -1], point, opening)
				for index, point in enumerate(cap)]
			# An angled upper cap may legitimately reach into the last 10% of
			# the arch. Reject only crossing the attachment, not optical padding;
			# the visible-outline check below still rejects actual self-crossings.
			if upper and min(p[1] for p in fitted_cap) <= root_y+EPSILON:
				continue
			if not upper and max(p[1] for p in fitted_cap) > root_y-height*0.10:
				continue
			hook = GSPath()
			hook.closed = True
			hook.nodes.append(_new_node(outer[0][0][0], LINE, False))
			_append_segment_sequence(hook, outer)
			for point in fitted_cap[1:]:
				hook.nodes.append(_new_node(point, LINE, False))
			_append_segment_sequence(hook, _reverse_segment_sequence(inner))
			hook.nodes[-1].smooth = False
			layer = _layer_from_paths([hook], source.width)
			layer.correctPathDirection()
			resolved = _lowercase_visible_outline(layer)
			resolved.removeOverlap()
			if len(resolved.paths) == 1:
				break
		else:
			raise GenerationError("c's corner extensions cross the resized hook.")
		bounds = _bounds_values(layer)
		actual_height = (bounds[3]-root_y) if upper else (root_y-bounds[1])
		actual_width = stem_right-bounds[0]
		height_error, width_error = height-actual_height, width-actual_width
		if abs(height_error) <= 0.5 and abs(width_error) <= 0.75:
			return layer.paths[0].copy()
		fy += 0.5 * height_error * 2.0 / (top-bottom)
		# Only the left half is used; its horizontal response is half the full c.
		fx += width_error / (right-left)
		if min(fx, fy) <= EPSILON:
			break
	raise GenerationError("c's strokes cannot fit the requested %s hook (%.2f/%.2f high, %.2f/%.2f wide)." % (
		"upper" if upper else "lower", actual_height, height, actual_width, width))


def _a_stem_path(candidate, stem, root_y):
	anchors = [(x,root_y) for x in stem]
	for path in candidate.paths:
		if all(any((n.x-x)**2+(n.y-y)**2 < 0.01 for n in path.nodes) for x,y in anchors):
			return path
	raise GenerationError("Could not identify a's stem attachment.")


def _a_arc_away_from_edge(path, first, last):
	arc = [first]+_forward_between(path,first,last)
	axis = (last.x-first.x,last.y-first.y)
	length2 = sum(v*v for v in axis)
	straight_edge = all(abs(_cross(axis,(n.x-first.x,n.y-first.y)))<=EPSILON*max(1.0,length2**0.5)
		and -EPSILON<=sum(axis[k]*(_point(n)[k]-_point(first)[k]) for k in (0,1))<=length2+EPSILON for n in arc)
	return _segment_sequence(arc) if not straight_edge else _reverse_segment_sequence(
		_segment_sequence([last]+_forward_between(path,last,first)))


def _a_attach_top(candidate, arch, stem, root_y):
	"""Fuse only the upper arch and upright; leave the belly separate."""
	stem_path = _a_stem_path(candidate,stem,root_y)
	def anchors(path):
		return [min(_oncurve_nodes(path),key=lambda n:(n.x-x)**2+(n.y-root_y)**2) for x in stem]
	sa,sb = anchors(stem_path);aa,ab = anchors(arch)
	stem_arc = _a_arc_away_from_edge(stem_path,sb,sa)
	arch_arc = _a_arc_away_from_edge(arch,aa,ab)
	path = GSPath();path.closed = True
	path.nodes.append(_new_node(_point(sb),LINE,bool(arch_arc[-1][1])))
	_append_segment_sequence(path,stem_arc)
	path.nodes[-1].smooth = bool(arch_arc[0][1])
	_append_segment_sequence(path,arch_arc)
	path.nodes[0].type = path.nodes[-1].type
	path.nodes[0].smooth = bool(arch_arc[-1][1])
	del path.nodes[len(path.nodes)-1]
	return _layer_from_paths([p for p in candidate.paths if p is not stem_path]+[path],candidate.width)


# Isolated, frozen normal-based compensation core from Optical Glyph Scaler
# 0.2.2. Used by a/g; no external script dependency or UI is loaded.
_A_SCALE_EPS = 1e-7


class _AOutlineScaleError(ValueError):
    pass


def _a_scale_point(node):
    return float(node.x), float(node.y)


def _a_scale_lerp(a, b, t):
    return tuple(a[k] + (b[k] - a[k]) * t for k in (0, 1))


def _a_scale_dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _a_scale_unit(v):
    length = math.hypot(*v)
    if length < _A_SCALE_EPS:
        raise _AOutlineScaleError("A zero-length segment needs repairing before scaling.")
    return v[0] / length, v[1] / length


def _a_scale_cubic(p, t):
    u = 1 - t
    return tuple(u**3*p[0][k] + 3*u*u*t*p[1][k] + 3*u*t*t*p[2][k] + t**3*p[3][k] for k in (0, 1))


def _a_scale_tangent(p, t):
    u = 1 - t
    return tuple(3*u*u*(p[1][k]-p[0][k]) + 6*u*t*(p[2][k]-p[1][k]) + 3*t*t*(p[3][k]-p[2][k]) for k in (0, 1))


def _a_scale_fresh(paths, width=0):
    """New native layer: detached Glyphs layers can retain stale path caches."""
    result = GSLayer()
    for path in paths:
        result.shapes.append(path.copy())
    result.width = width
    return result


def _a_scale_bounds(layer):
    b = layer.bounds
    return b.origin.x, b.origin.y, b.size.width, b.size.height


def _a_scale_segments(layer):
    result = []
    for pi, path in enumerate(layer.paths):
        nodes = list(path.nodes)
        if not path.closed:
            raise _AOutlineScaleError("Close open paths first. This version scales filled outlines.")
        start = next((i for i,n in enumerate(nodes) if n.type != OFFCURVE), None)
        if start is None:
            raise _AOutlineScaleError("A contour has no on-curve nodes.")
        cycle = nodes[start:] + nodes[:start] + [nodes[start]]
        previous = 0
        for i in range(1, len(cycle)):
            if cycle[i].type == OFFCURVE:
                continue
            group = cycle[previous:i+1]
            curved = len(group) == 4 and all(n.type == OFFCURVE for n in group[1:-1])
            if len(group) != 2 and not curved:
                raise _AOutlineScaleError("Only straight lines and cubic Béziers are supported; convert quadratic curves first.")
            a, b = _a_scale_point(group[0]), _a_scale_point(group[-1])
            pts = [_a_scale_point(n) for n in group] if curved else [a, _a_scale_lerp(a,b,1/3), _a_scale_lerp(a,b,2/3), b]
            if math.hypot(b[0]-a[0],b[1]-a[1]) < _A_SCALE_EPS and not curved:
                raise _AOutlineScaleError("Remove duplicate consecutive nodes before scaling.")
            result.append((pi, [n.index for n in group], pts, curved))
            previous = i
    return result


def _a_scale_correct_directions(layer):
    """Containment, not overlap: Glyphs' generic fixer can invert one X arm."""
    samples = [[] for p in layer.paths]
    for pi,ids,ps,curved in _a_scale_segments(layer):
        samples[pi].extend(_a_scale_cubic(ps,t) for t in (0.,.25,.5,.75))
    paths = list(layer.paths)
    for i,path in enumerate(paths):
        depth = 0
        for j,other in enumerate(paths):
            if i==j:
                continue
            ink = other.bezierPath
            if all(ink.containsPoint_(p) for p in samples[i]):
                depth += 1
        wanted = -1 if depth%2==0 else 1
        if path.direction!=wanted:
            path.reverse()
    return layer


def _a_scale_ink_section(layer, p, t):
    """First filled interval along the local normal, not a bounding-box gap."""
    u = _a_scale_unit(t)
    n = (-u[1], u[0])
    ink = layer.bezierPath
    probe = .04
    filled = [bool(ink.containsPoint_((p[0]+n[0]*sign*probe,p[1]+n[1]*sign*probe))) for sign in (-1,1)]
    if filled[0] == filled[1]:
        return None  # Hidden overlap edge, or unsupported stroke style.
    sign = -1 if filled[0] else 1
    span = max(2000., 4*max(_a_scale_bounds(layer)[2:]))
    hits = layer.intersectionsBetweenPoints((p[0]-n[0]*span,p[1]-n[1]*span),(p[0]+n[0]*span,p[1]+n[1]*span))
    distances = sorted(((h.x-p[0])*n[0]+(h.y-p[1])*n[1])*sign for h in hits[1:-1])
    for d in distances:
        if d > .08 and not ink.containsPoint_((p[0]+n[0]*sign*(d+probe),p[1]+n[1]*sign*(d+probe))):
            return (p[0]+n[0]*sign*d,p[1]+n[1]*sign*d), d
    return None


def _a_scale_median(values):
    s = sorted(values)
    return s[len(s)//2] if s else None


def _a_scale_affine(source, fx, fy):
    result = _a_scale_fresh(source.paths, source.width)
    x,y,w,h = _a_scale_bounds(source)
    cx = x+w/2
    for path in result.paths:
        for node in path.nodes:
            node.x = cx+(node.x-cx)*fx
            node.y *= fy
    return _a_scale_fresh(result.paths,result.width)


def _a_scale_closest_location(model, q, allowed=None):
    """Find a boundary location, retaining its segment identity for tracking."""
    best = (float('inf'),None,None)
    for si,(_,_,ps,curved) in enumerate(model):
        if allowed is not None and si not in allowed:
            continue
        if not curved:
            d = (ps[-1][0]-ps[0][0],ps[-1][1]-ps[0][1])
            t = max(0.,min(1.,_a_scale_dot((q[0]-ps[0][0],q[1]-ps[0][1]),d)/max(_A_SCALE_EPS,_a_scale_dot(d,d))))
        else:
            t = min((i/20. for i in range(21)),key=lambda t:sum((_a_scale_cubic(ps,t)[k]-q[k])**2 for k in (0,1)))
            lo,hi = max(0.,t-.05),min(1.,t+.05)
            for _ in range(24):
                a,b = (2*lo+hi)/3,(lo+2*hi)/3
                da = sum((_a_scale_cubic(ps,a)[k]-q[k])**2 for k in (0,1))
                db = sum((_a_scale_cubic(ps,b)[k]-q[k])**2 for k in (0,1))
                if da<db:hi=b
                else:lo=a
            t = (lo+hi)/2
        p = _a_scale_cubic(ps,t)
        distance = math.hypot(p[0]-q[0],p[1]-q[1])
        if distance<best[0]:best = distance,si,t
    return best


def _a_scale_plane_parameter(ps, center, along, reference):
    """Intersect a tracked segment with the centerline's normal plane."""
    def f(t):
        p = _a_scale_cubic(ps,t)
        return _a_scale_dot((p[0]-center[0],p[1]-center[1]),along)
    t = reference
    for _ in range(12):
        value = f(t)
        if abs(value)<1e-5:return t
        derivative = _a_scale_dot(_a_scale_tangent(ps,t),along)
        if abs(derivative)<1e-7:break
        nxt = t-value/derivative
        if not 0<=nxt<=1:break
        t = nxt
    candidates=[]
    lo,fl = 0.,f(0.)
    for j in range(1,17):
        hi=j/16.;fh=f(hi)
        if fl*fh<=0:
            a,b=lo,hi
            for _ in range(22):
                m=(a+b)/2;fm=f(m)
                if fl*fm<=0:b=m
                else:a=m;fl=fm
            candidates.append((a+b)/2)
        lo,fl=hi,fh
    if not candidates:return None
    return min(candidates,key=lambda t:abs(t-reference))


def _a_scale_tracked_section(model, pair):
    """Re-measure on the SAME two edges, normal to their mean centerline.

    Parameters can slide along those edges, but never jump to a bar, serif or
    different bowl. This prevents a normal-ray intersection from changing the
    identity of the stroke halfway through compensation.
    """
    si,ta,sj,tb = pair[:4]
    a,b=model[si][2],model[sj][2]
    p,q=_a_scale_cubic(a,ta),_a_scale_cubic(b,tb)
    center=_a_scale_lerp(p,q,.5)
    for _ in range(4):
        u,v=_a_scale_unit(_a_scale_tangent(a,ta)),_a_scale_unit(_a_scale_tangent(b,tb))
        parallel=abs(_a_scale_dot(u,v))
        if parallel<.75:return None
        if _a_scale_dot(u,v)<0:v=(-v[0],-v[1])
        along=_a_scale_unit((u[0]+v[0],u[1]+v[1]))
        na,nb=_a_scale_plane_parameter(a,center,along,ta),_a_scale_plane_parameter(b,center,along,tb)
        if na is None or nb is None:return None
        ta,tb=na,nb
        p,q=_a_scale_cubic(a,ta),_a_scale_cubic(b,tb)
        center=_a_scale_lerp(p,q,.5)
    d=(q[0]-p[0],q[1]-p[1])
    n=(-along[1],along[0])
    if _a_scale_dot(d,n)<0:n=(-n[0],-n[1])
    thickness=_a_scale_dot(d,n)
    if thickness<=.08:return None
    return ta,tb,p,q,center,along,n,thickness,parallel


def _a_scale_stroke_pairs(source, model):
    pairs=[]
    for si,(_,_,ps,_) in enumerate(model):
        for t in (.2,.35,.5,.65,.8):
            p=_a_scale_cubic(ps,t);tan=_a_scale_tangent(ps,t)
            if math.hypot(*tan)<_A_SCALE_EPS:continue
            section=_a_scale_ink_section(source,p,tan)
            if section is None:continue
            # Check actual neighboring rays as well as tracked paired edges.
            # Keeping the opposite parameter fixed can halve a neighbor's
            # movement, accidentally leaving all three samples inside a join.
            nearby=[_a_scale_ink_section(source,_a_scale_cubic(ps,t+dt),_a_scale_tangent(ps,t+dt)) for dt in (-.045,.045)]
            if not all(v and .75<section[1]/v[1]<1.33 for v in nearby):continue
            distance,sj,tb=_a_scale_closest_location(model,section[0])
            if sj is None or si==sj or distance>.1:continue
            pair=(si,t,sj,tb)
            measured=_a_scale_tracked_section(model,pair)
            if measured is None:continue
            ta,tb,p,q,center,along,n,thickness,parallel=measured
            if parallel<.96 or min(ta,tb)<.08 or max(ta,tb)>.92:continue
            if not model[si][3] and not model[sj][3]:
                lengths=[math.hypot(model[j][2][-1][0]-model[j][2][0][0],model[j][2][-1][1]-model[j][2][0][1]) for j in (si,sj)]
                if thickness>min(lengths)*1.25:continue  # Caps/joins, not representative stroke sides.
            # Terminal cuts and joins are not representative stroke sections.
            if not source.bezierPath.containsPoint_(center):continue
            actual=_a_scale_ink_section(source,p,along)
            if actual is None or abs(actual[1]-thickness)>max(.35,thickness*.015):continue
            neighbor=[]
            for dt in (-.045,.045):
                test=_a_scale_tracked_section(model,(si,max(.001,min(.999,ta+dt)),sj,tb))
                if test:neighbor.append(test[7])
            if len(neighbor)<2 or not all(.75<thickness/v<1.33 for v in neighbor):continue
            if any(math.hypot(center[0]-r[5][0],center[1]-r[5][1])<max(1.,thickness*.08) and {si,sj}=={r[0],r[2]} for r in pairs):continue
            pairs.append((si,ta,sj,tb,thickness,center,parallel))
    if not pairs:raise _AOutlineScaleError("No reliable paired stroke edges could be measured. Try ordinary scaling.")
    return pairs


def _a_scale_least_squares(rows, regularization, size):
    """Sparse, diagonally preconditioned normal solve; no numpy dependency."""
    diagonal=regularization[:]
    rhs=[0.]*size
    for cs,value,strength in rows:
        for i,c in cs:
            rhs[i]+=strength*c*value
            diagonal[i]+=strength*c*c
    def product(x):
        out=[regularization[i]*x[i] for i in range(size)]
        for cs,_,strength in rows:
            v=sum(c*x[i] for i,c in cs)*strength
            for i,c in cs:out[i]+=c*v
        return out
    x=[0.]*size;r=rhs[:]
    z=[r[i]/max(_A_SCALE_EPS,diagonal[i]) for i in range(size)];p=z[:]
    rz=sum(a*b for a,b in zip(r,z));initial=max(_A_SCALE_EPS,sum(v*v for v in rhs))
    for _ in range(min(600,size*5)):
        ap=product(p);den=sum(a*b for a,b in zip(p,ap))
        if den<_A_SCALE_EPS:break
        alpha=rz/den
        x=[a+alpha*b for a,b in zip(x,p)];r=[a-alpha*b for a,b in zip(r,ap)]
        if sum(v*v for v in r)<initial*1e-14:break
        z=[r[i]/max(_A_SCALE_EPS,diagonal[i]) for i in range(size)]
        new=sum(a*b for a,b in zip(r,z));beta=new/max(_A_SCALE_EPS,rz)
        p=[a+beta*b for a,b in zip(z,p)];rz=new
    return x


def _a_scale_flat_foot_levels(source):
    """Flat feet retain their authored vertical stations.

    A cap's two adjoining edges depart toward the same side. This excludes
    internal crossbars and smooth bowl extrema; counter contours are excluded
    too. Coordinates come from this source, not a guessed baseline or metric.
    Consequently raised feet, overshoots and descender levels stay intentional.
    """
    model=_a_scale_segments(source)
    incoming={(pi,ids[-1]):ps for pi,ids,ps,curved in model}
    outgoing={(pi,ids[0]):ps for pi,ids,ps,curved in model}
    levels={}
    for pi,ids,ps,curved in model:
        if curved or source.paths[pi].direction!= -1 or abs(ps[0][1]-ps[-1][1])>_A_SCALE_EPS:
            continue
        before=_a_scale_tangent(incoming[(pi,ids[0])],1.)
        after=_a_scale_tangent(outgoing[(pi,ids[-1])],0.)
        if min(math.hypot(*before),math.hypot(*after))<_A_SCALE_EPS:continue
        away_before=-_a_scale_unit(before)[1];away_after=_a_scale_unit(after)[1]
        if min(away_before,away_after)<.5:
            continue
        # A concave crossbar edge has the same corner pattern, but its ink
        # lies opposite the departing stem edges. It is not a terminal cap.
        middle=_a_scale_lerp(ps[0],ps[-1],.5);sign=1 if away_before>0 else -1
        ink=source.paths[pi].bezierPath
        if not ink.containsPoint_((middle[0],middle[1]+sign*.04)) or ink.containsPoint_((middle[0],middle[1]-sign*.04)):
            continue
        # In a separate horizontal bar, these are long stroke boundaries, not
        # its ends. Baseline/descender foot surfaces remain anchored even when
        # broad (e.g. a serif or an E's bottom arm).
        neighbors=[incoming[(pi,ids[0])],outgoing[(pi,ids[-1])]]
        longest=max(math.hypot(p[-1][0]-p[0][0],p[-1][1]-p[0][1]) for p in neighbors)
        if ps[0][1]>_A_SCALE_EPS and abs(ps[-1][0]-ps[0][0])>longest*1.25:continue
        for ni in ids:levels[(pi,ni)]=source.paths[pi].nodes[ni].y
    return levels


def _a_scale_validate_foot_levels(source,result,fy):
    for (pi,ni),y in _a_scale_flat_foot_levels(source).items():
        if abs(result.paths[pi].nodes[ni].y-y*fy)>1e-5:
            raise _AOutlineScaleError("A flat stroke end lost its vertical alignment. Original outline is unchanged.")


def _a_scale_embedded_joins(source,model):
    """Retain hidden flat closures embedded in another part of a contour.

    Self-overlapping constructions can hide a short cap inside a bowl or stem.
    Thickness alone cannot keep that cap buried. Track its signed clearance
    from the same nonincident boundary, without a glyph-specific node recipe.
    """
    joins=[];hidden_segments=[]
    for si,(pi,ids,ps,curved) in enumerate(model):
        if curved:continue
        u=_a_scale_unit(_a_scale_tangent(ps,.5));n=(-u[1],u[0])
        hidden=True
        for t in (.2,.5,.8):
            p=_a_scale_cubic(ps,t)
            if not all(source.bezierPath.containsPoint_((p[0]+sign*n[0]*.1,p[1]+sign*n[1]*.1)) for sign in (-1,1)):
                hidden=False;break
        if hidden:hidden_segments.append(si)
    # Merge collinear subdivisions into one closure. Extra nodes should not
    # turn a rigid cap into unrelated tips or become their own witnesses.
    remaining=set(hidden_segments)
    while remaining:
        first=min(remaining);chain=[first];pi=model[first][0]
        def neighbor(si,before):
            edge=model[si];endpoint=edge[1][0 if before else -1]
            return next((j for j in remaining if j!=si and model[j][0]==pi
                         and model[j][1][-1 if before else 0]==endpoint
                         and _a_scale_dot(_a_scale_unit(_a_scale_tangent(edge[2],.5)),_a_scale_unit(_a_scale_tangent(model[j][2],.5)))>.99999),None)
        while True:
            prev=neighbor(chain[0],True)
            if prev is None or prev in chain:break
            chain.insert(0,prev)
        while True:
            nxt=neighbor(chain[-1],False)
            if nxt is None or nxt in chain:break
            chain.append(nxt)
        remaining.difference_update(chain)
        capids={ni for j in chain for ni in model[j][1]}
        start,end=model[chain[0]][1][0],model[chain[-1]][1][-1]
        before=next(s for s in model if s[0]==pi and s[1][-1]==start)
        after=next(s for s in model if s[0]==pi and s[1][0]==end)
        rigid=not before[3] and not after[3] and abs(_a_scale_dot(_a_scale_unit(_a_scale_tangent(before[2],1.)),_a_scale_unit(_a_scale_tangent(after[2],0.))))>.995
        if not rigid:continue  # Only parallel-sided caps admit shape-safe extension.
        allowed=[j for j,(pj,js,_,_) in enumerate(model) if pj!=pi or not capids&set(js)]
        # a's belly bar closes inside a straight upright. In heavy a's its
        # upper cap lies just above the upright/arch tangent station: the
        # nearest curved arch is not the closure's supporting stem edge.
        # Track an existing parallel straight witness when one is present;
        # clamp its endpoint parameter but measure cross-stroke depth only.
        cap_axis=_a_scale_unit(_a_scale_tangent(model[chain[0]][2],.5))
        parallel_edges=[j for j in allowed if not model[j][3]
                        and abs(_a_scale_dot(cap_axis,_a_scale_unit(_a_scale_tangent(model[j][2],.5))))>.995]
        if parallel_edges:allowed=parallel_edges
        cap=[]
        for si in chain:
            ps=model[si][2]
            for t in (0.,.25,.5,.75,1.):
                p=_a_scale_cubic(ps,t);distance,sj,tb=_a_scale_closest_location(model,p,allowed)
                if sj is None or distance<.25:continue
                q=_a_scale_cubic(model[sj][2],tb);v=_a_scale_unit(_a_scale_tangent(model[sj][2],tb));normal=(-v[1],v[0])
                sign=1. if _a_scale_dot((p[0]-q[0],p[1]-q[1]),normal)>0 else -1.
                normal=(normal[0]*sign,normal[1]*sign)
                # The witness may itself be covered by the intersecting bar.
                depth=_a_scale_dot((p[0]-q[0],p[1]-q[1]),normal)
                if depth>.25:cap.append((si,t,sj,tb,depth,sign,tuple(chain),rigid))
        if cap:joins.extend(cap)
    return joins


def _a_scale_join_clearance(model,join):
    si,t,sj,reference,depth,sign=join[:6]
    p=_a_scale_cubic(model[si][2],t)
    _,_,tb=_a_scale_closest_location(model,p,[sj])
    q=_a_scale_cubic(model[sj][2],tb);v=_a_scale_unit(_a_scale_tangent(model[sj][2],tb))
    normal=(-v[1]*sign,v[0]*sign)
    return tb,normal,_a_scale_dot((p[0]-q[0],p[1]-q[1]),normal)


def _a_scale_restore_embedded_joins(source,result,weight):
    """Slide a buried cap along its adjoining stroke, never reshape the bowl.

    Parallel straight boundaries admit a rigid cap translation that extends
    their overlap without changing their thickness or angle. Curved junctions
    are outside this operation. The complete paired-weight check follows it.
    """
    sm=_a_scale_segments(source);joins=_a_scale_embedded_joins(source,sm)
    grouped={}
    for join in joins:grouped.setdefault(join[6],[]).append(join)
    out=_a_scale_fresh(result.paths,result.width);moved=0
    for chain,group in grouped.items():
        pi=sm[chain[0]][0]
        ids=[sm[chain[0]][1][0]]+[sm[si][1][-1] for si in chain]
        before_si=next(j for j,s in enumerate(sm) if s[0]==pi and s[1][-1]==ids[0])
        after_si=next(j for j,s in enumerate(sm) if s[0]==pi and s[1][0]==ids[-1])
        before,after=sm[before_si],sm[after_si]
        for iteration in range(12):
            model=_a_scale_segments(out)
            # The a recipe requires a hidden closure, not an identical
            # numerical burial depth. If the complete cap still has ink on
            # both sides, moving it would unnecessarily alter a heavy join.
            ink=out.bezierPath
            def buried(si,t):
                ps=model[si][2];p=_a_scale_cubic(ps,t)
                axis=_a_scale_unit(_a_scale_tangent(ps,t));normal=(-axis[1],axis[0])
                return all(ink.containsPoint_((p[0]+sign*normal[0]*.1,
                    p[1]+sign*normal[1]*.1)) for sign in (-1,1))
            if all(buried(si,t) for si in chain for t in (.2,.5,.8)):
                break
            measures=[(join,_a_scale_join_clearance(model,join)) for join in group]
            if all(section[2]>=join[4]*weight-.05 for join,section in measures):break
            u=_a_scale_unit(_a_scale_tangent(model[before_si][2],1.));v=_a_scale_unit(_a_scale_tangent(model[after_si][2],0.))
            if abs(_a_scale_dot(u,v))<.995:
                raise _AOutlineScaleError("An embedded join has incompatible adjoining edges. Try less compensation.")
            # Choose the along-stroke direction that buries the cap deeper.
            if sum(_a_scale_dot(section[1],u) for _,section in measures)<0:u=(-u[0],-u[1])
            projections=[_a_scale_dot(section[1],u) for _,section in measures]
            if min(projections)<.25:
                raise _AOutlineScaleError("An embedded join cannot be aligned without distorting its stroke.")
            step=max((join[4]*weight-section[2])/projection for (join,section),projection in zip(measures,projections))
            for ni in ids:
                node=out.paths[pi].nodes[ni];node.x+=u[0]*step;node.y+=u[1]*step
            out=_a_scale_fresh(out.paths,out.width)
            if iteration==0:moved+=1
        else:raise _AOutlineScaleError("An embedded join could not retain its overlap. Original outline is unchanged.")
    return out,moved


def _a_scale_validate_embedded_joins(source,result,weight,rounded=False):
    model=_a_scale_segments(result)
    for join in _a_scale_embedded_joins(source,_a_scale_segments(source)):
        ps=model[join[0]][2];p=_a_scale_cubic(ps,join[1])
        axis=_a_scale_unit(_a_scale_tangent(ps,join[1]));normal=(-axis[1],axis[0])
        if all(result.bezierPath.containsPoint_((p[0]+sign*normal[0]*.1,
            p[1]+sign*normal[1]*.1)) for sign in (-1,1)):
            continue
        clearance=_a_scale_join_clearance(model,join)[2]
        limit=max(0.,join[4]*weight-(1.5 if rounded else .05))
        if clearance<=0 or clearance<limit:
            raise _AOutlineScaleError("A hidden stroke closure would pull out of its join. Original outline is unchanged.")


def _a_scale_verify_paired_weight(source,result,weight,before=None):
    """Recheck weight after landmark alignment, not only before it."""
    pairs=_a_scale_stroke_pairs(source,_a_scale_segments(source));model=_a_scale_segments(result)
    previous=_a_scale_segments(before) if before is not None else None
    measured=[];missing=0;covered=set()
    groups={}
    for pair in pairs:
        key=tuple(sorted((pair[0],pair[2])));groups[key]=groups.get(key,0)+1
    for pair in pairs:
        tracked=pair
        if previous is not None:
            old=_a_scale_tracked_section(previous,pair)
            if old:
                # Extending a straight edge changes its parameterization, not
                # the exposed stroke. Retain the same physical section rather
                # than sampling a different taper at the old raw parameter.
                parameters=[old[0],old[1]]
                for side,si in enumerate((pair[0],pair[2])):
                    if not model[si][3] and model[si][2]!=previous[si][2]:
                        parameters[side]=_a_scale_closest_location(model,old[2+side],[si])[2]
                tracked=(pair[0],parameters[0],pair[2],parameters[1])+pair[4:]
        section=_a_scale_tracked_section(model,tracked)
        if section is None or not result.bezierPath.containsPoint_(section[4]):missing+=1;continue
        error=abs(section[7]-pair[4]*weight);tol=max(1.,pair[4]*weight*.015)
        if error>tol:raise _AOutlineScaleError("Aligning a join would change stroke weight. Try less compensation.")
        measured.append(error)
        covered.add(tuple(sorted((pair[0],pair[2]))))
    if missing>max(1,len(pairs)*.12) or len(measured)<len(pairs)*.88 or any(count>=3 and group not in covered for group,count in groups.items()):
        raise _AOutlineScaleError("Stroke pairs became ambiguous after join alignment. Original outline is unchanged.")
    return max(measured,default=0.)


def _a_scale_compensate(source,fx,fy,weight,numerical=False,level_scale=None,tolerance_floor=1.0):
    level_scale=fy if level_scale is None else level_scale
    outer=[(pi,p) for pi,p in enumerate(source.paths) if p.direction==-1]
    holes=[(pi,p) for pi,p in enumerate(source.paths) if p.direction==1]
    if len(outer)>1:
        groups=[[pi] for pi,p in outer]
        for hi,hole in holes:
            hb=hole.bounds;center=(hb.origin.x+hb.size.width/2,hb.origin.y+hb.size.height/2)
            matches=[(p.bounds.size.width*p.bounds.size.height,i) for i,(_,p) in enumerate(outer) if p.bezierPath.containsPoint_(center)]
            if not matches:raise _AOutlineScaleError("A counter cannot be paired with its outer contour.")
            groups[min(matches)[1]].append(hi)
        center=_a_scale_bounds(source)[0]+_a_scale_bounds(source)[2]/2
        paths,reports=[None]*len(source.paths),[]
        for group in groups:
            part=_a_scale_fresh([source.paths[pi] for pi in group],source.width);pc=_a_scale_bounds(part)[0]+_a_scale_bounds(part)[2]/2
            out,report=_a_scale_compensate(part,fx,fy,weight,numerical=numerical,level_scale=level_scale,tolerance_floor=tolerance_floor)
            for pi,path in zip(group,out.paths):
                for node in path.nodes:node.x+=(pc-center)*(fx-1)
                paths[pi]=path
            reports.append(report)
        return _a_scale_fresh(paths,source.width),{"maxError":max(r['maxError'] for r in reports),"iterations":max(r['iterations'] for r in reports),"samples":sum(r['samples'] for r in reports)}
    sm=_a_scale_segments(source);pairs=_a_scale_stroke_pairs(source,sm)
    typical=_a_scale_median([r[4] for r in pairs])
    keys=[(pi,n.index) for pi,p in enumerate(source.paths) for n in p.nodes]
    index={key:i for i,key in enumerate(keys)};size=len(keys)*2
    def coefficients(si,t):
        pi,ids,_,curved=sm[si]
        values=((1-t)**3,3*(1-t)**2*t,3*(1-t)*t*t,t**3) if curved else (1-t,t)
        return [(index[(pi,i)],c) for i,c in zip(ids,values)]
    base=_a_scale_affine(source,fx,fy)
    levels={key:y*level_scale for key,y in _a_scale_flat_foot_levels(source).items()}
    fixed={2*index[key]+1 for key in levels}
    for (pi,ni),y in levels.items():base.paths[pi].nodes[ni].y=y
    base=_a_scale_fresh(base.paths,base.width);result=_a_scale_fresh(base.paths,base.width)
    # With authored endpoints fixed, the bowl's center reference is secondary
    # to its measured stroke weight. Do not fight the locked terminal stations.
    center_strength=.005 if levels else .02
    regularization=[.0003 if source.paths[pi].nodes[ni].type!=OFFCURVE else .0001 for pi,ni in keys for _ in (0,1)]
    baseflat=[v for pi,ni in keys for v in _a_scale_point(base.paths[pi].nodes[ni])]
    cx=_a_scale_bounds(source)[0]+_a_scale_bounds(source)[2]/2
    def evaluate(layer):
        model=_a_scale_segments(layer);measurements=[];missing=0
        for pair in pairs:
            section=_a_scale_tracked_section(model,pair)
            if section is None or not layer.bezierPath.containsPoint_(section[4]):
                missing+=1;continue
            desired=pair[4]*weight;tol=max(tolerance_floor,desired*.015)
            measurements.append((pair,section,desired,tol))
        errors=[abs(s[7]-d) for _,s,d,_ in measurements]
        normalized=[e/m[3] for e,m in zip(errors,measurements)]
        score=sum(v*v for v in normalized)/max(1,len(normalized))+missing*10
        return model,measurements,missing,errors,normalized,score
    best_score=float('inf');best=None
    for iteration in range(28):
        model,measurements,missing,errors,normalized,score=evaluate(result)
        if score<best_score:best_score,best=score,_a_scale_fresh(result.paths,result.width)
        group_counts={}
        for pair in pairs:
            key=tuple(sorted((pair[0],pair[2])));group_counts[key]=group_counts.get(key,0)+1
        measured_groups={tuple(sorted((m[0][0],m[0][2]))) for m in measurements}
        covered=all(count<3 or group in measured_groups for group,count in group_counts.items())
        if covered and missing<=max(1,len(pairs)*.12) and len(measurements)>=len(pairs)*.88 and max(normalized,default=99)<=1:
            return result,{"maxError":max(errors,default=0.),"iterations":iteration+1,"samples":len(measurements),"omitted":missing,"tolerance":max(m[3] for m in measurements),"source":[m[0][4] for m in measurements],"final":[m[1][7] for m in measurements]}
        flat=[v for pi,ni in keys for v in _a_scale_point(result.paths[pi].nodes[ni])]
        rows=[]
        for pair,section,desired,tol in measurements:
            ta,tb,p,q,center,along,n,current,parallel=section
            ca,cb=coefficients(pair[0],ta),coefficients(pair[2],tb)
            # Differentiate the actual tracked measurement, not a frozen
            # boundary normal. In a modulated curve the measuring plane can
            # slide as handles move; ignoring that produced false failures.
            cs=[(2*i+k,-c*n[k]) for i,c in ca for k in (0,1)]+[(2*i+k,c*n[k]) for i,c in cb for k in (0,1)]
            if numerical:
                cs=[]
                for coordinate in sorted({2*i+k for i,c in ca+cb for k in (0,1)}):
                    nodekey=keys[coordinate//2];axis=coordinate%2;modified=list(model)
                    for si in (pair[0],pair[2]):
                        pi,ids,ps,curved=model[si]
                        if pi==nodekey[0] and nodekey[1] in ids:
                            ps=list(ps);j=ids.index(nodekey[1])
                            if curved:
                                probe_point=list(ps[j]);probe_point[axis]+=.05;ps[j]=tuple(probe_point)
                            else:
                                endpoints=[ps[0],ps[3]]
                                probe_point=list(endpoints[j]);probe_point[axis]+=.05;endpoints[j]=tuple(probe_point)
                                ps=[endpoints[0],_a_scale_lerp(endpoints[0],endpoints[1],1/3.),_a_scale_lerp(endpoints[0],endpoints[1],2/3.),endpoints[1]]
                            modified[si]=(pi,ids,ps,curved)
                    probe=_a_scale_tracked_section(modified,pair)
                    if probe:cs.append((coordinate,(probe[7]-current)/.05))
            # Paired correction moves both edges symmetrically, not independent
            # outline normals. The affine stroke center remains the reference.
            rows.append((cs,desired-current,1./max(1.,tol*tol)))
            reference=(cx+(pair[5][0]-cx)*fx,pair[5][1]*fy)
            for k in (0,1):
                cs=[(2*i+k,.5*c) for i,c in ca+cb]
                rows.append((cs,reference[k]-center[k],center_strength/max(1.,tol*tol)))
        def align(pi,a,b,u):
            n=(-u[1],u[0]);cs=[(2*index[(pi,a)]+k,-n[k]) for k in (0,1)]+[(2*index[(pi,b)]+k,n[k]) for k in (0,1)]
            rows.append((cs,-sum(c*flat[i] for i,c in cs),100.))
        for pi,ids,ps,curved in sm:
            if not curved:align(pi,ids[0],ids[-1],_a_scale_unit(((ps[-1][0]-ps[0][0])*fx,(ps[-1][1]-ps[0][1])*fy)))
        for pi,path in enumerate(result.paths):
            original=list(source.paths[pi].nodes);nodes=list(path.nodes)
            for i,node in enumerate(nodes):
                if node.type==OFFCURVE or not original[i].smooth:continue
                a,b=nodes[i-1],nodes[(i+1)%len(nodes)]
                oa,ob=original[i-1],original[(i+1)%len(nodes)]
                av,bv=(original[i].x-oa.x,original[i].y-oa.y),(ob.x-original[i].x,ob.y-original[i].y)
                if min(math.hypot(*av),math.hypot(*bv))<_A_SCALE_EPS or _a_scale_dot(_a_scale_unit(av),_a_scale_unit(bv))<.999:continue
                if a.type==OFFCURVE and b.type==OFFCURVE:u=_a_scale_unit((b.x-a.x,b.y-a.y))
                else:u=_a_scale_unit((av[0]*fx,av[1]*fy))
                if a.type==OFFCURVE:align(pi,a.index,i,u)
                if b.type==OFFCURVE:align(pi,i,b.index,u)
        # A small return-to-affine term regularizes unmeasured serif tips and
        # handles without forcing the bowl back to its uncompensated width.
        for i in range(size):rows.append(([(i,1.)],baseflat[i]-flat[i],regularization[i]*.15))
        # Fixed cap coordinates have zero displacement, not a soft preference.
        # Remove these degrees of freedom from every constraint before solving.
        if fixed:rows=[([(i,c) for i,c in cs if i not in fixed],v,s) for cs,v,s in rows]
        delta=_a_scale_least_squares(rows,regularization,size)
        limit=max(2.,typical*.16)
        peak=max((math.hypot(delta[i],delta[i+1]) for i in range(0,size,2)),default=0.)
        if peak>limit:delta=[v*limit/peak for v in delta]
        accepted=None
        for step in (1.,.5,.25,.125):
            trial=_a_scale_fresh(result.paths,result.width)
            for (pi,ni),i in index.items():
                node=trial.paths[pi].nodes[ni];node.x+=delta[2*i]*step;node.y+=delta[2*i+1]*step
            for (pi,ni),y in levels.items():trial.paths[pi].nodes[ni].y=y
            trial=_a_scale_fresh(trial.paths,trial.width)
            trial_score=evaluate(trial)[-1]
            if trial_score<score-1e-7:accepted=trial;break
        if accepted is None:break
        result=accepted
    _,measurements,missing,errors,normalized,_=evaluate(best)
    if missing>max(1,len(pairs)*.12):
        raise _AOutlineScaleError("Too many stroke pairs became ambiguous at these settings. Reduce the change or turn off compensation.")
    raise _AOutlineScaleError("Paired stroke compensation did not converge (error %.1f units). Reduce the change or turn off compensation."%max(errors,default=0.))


def _a_scale_validate_topology(source, result):
    """Reject flipped contours or counters escaping their original solid."""
    if len(source.paths)!=len(result.paths):
        raise _AOutlineScaleError("Compensation changed the contour structure.")
    for original,candidate in zip(source.paths,result.paths):
        if original.direction!=candidate.direction:
            raise _AOutlineScaleError("A contour collapsed or inverted. Reduce the change or turn off compensation.")
    sm,rm=_a_scale_segments(source),_a_scale_segments(result)
    def samples(model,pi):
        return [_a_scale_cubic(ps,t) for index,_,ps,curved in model if index==pi
                for t in ((0.,.25,.5,.75) if curved else (0.,.5))]
    for hi,hole in enumerate(source.paths):
        if hole.direction!=1:continue
        points=samples(sm,hi)
        parents=[(path.bounds.size.width*path.bounds.size.height,pi)
                 for pi,path in enumerate(source.paths) if path.direction==-1
                 and all(path.bezierPath.containsPoint_(p) for p in points)]
        if parents:
            pi=min(parents)[1]
            if not all(result.paths[pi].bezierPath.containsPoint_(p) for p in samples(rm,hi)):
                raise _AOutlineScaleError("A counter no longer fits inside its outline. Reduce the change or turn off compensation.")


def _a_scale_scale_outline(source, height=100, width=100, weight=100, optical=True,tolerance_floor=1.0):
    if not source.paths:
        raise _AOutlineScaleError("Choose a glyph with outlines. Components must be decomposed first.")
    if not all(math.isfinite(v) and 50 <= v <= 200 for v in (height,width,weight)):
        raise _AOutlineScaleError("Enter percentages between 50 and 200.")
    source = _a_scale_fresh(source.paths,source.width)
    _a_scale_correct_directions(source)
    _a_scale_segments(source)  # Validate before any preview or mutation.
    fx,fy = width/100.,height/100.
    if optical and (fx,fy,weight)!=(1.,1.,100):
        sx,sy,sw,sh = _a_scale_bounds(source)
        # Fast paired-normal solve first. If its local approximation stalls,
        # retry from the same frozen outline using measured derivatives.
        # Both strategies must satisfy the SAME stroke and dimension checks.
        for numerical in (False,True):
            internal_x,internal_y = fx,fy
            try:
                for fit in range(24):
                    candidate,report = _a_scale_compensate(source,internal_x,internal_y,weight/100.,numerical=numerical,level_scale=fy,tolerance_floor=tolerance_floor)
                    tx,ty,tw,th = _a_scale_bounds(candidate)
                    if max(abs(tw-sw*fx),abs(th-sh*fy))<.6:
                        break
                    internal_x *= (sw*fx/tw)**.5
                    internal_y *= (sh*fy/th)**.5
                else:
                    raise _AOutlineScaleError("The requested dimensions and stroke weight conflict. Try less compensation.")
                _a_scale_validate_topology(source,candidate)
                report['numericalRetry']=numerical
                break
            except _AOutlineScaleError:
                if numerical:raise
        # Do not recenter away from authored foot landmarks. Outlines with
        # no such landmarks retain the existing round/overshoot placement.
        cy = 0. if _a_scale_flat_foot_levels(source) else (sy+sh/2)*fy-(ty+th/2)
        for path in candidate.paths:
            for node in path.nodes:
                node.y += cy
        candidate = _a_scale_fresh(candidate.paths,candidate.width)
        before_alignment=candidate
        candidate,moved=_a_scale_restore_embedded_joins(source,candidate,weight/100.)
        _a_scale_validate_embedded_joins(source,candidate,weight/100.)
        report['alignedJoins']=moved
        if moved:
            report['maxError']=_a_scale_verify_paired_weight(source,candidate,weight/100.,before=before_alignment)
            cb=_a_scale_bounds(candidate)
            if max(abs(cb[2]-sw*fx),abs(cb[3]-sh*fy))>=.6:
                raise _AOutlineScaleError("An embedded join cannot retain the requested dimensions safely.")
    else:
        candidate,report = _a_scale_affine(source,fx,fy), {"maxError":0.,"iterations":0}
    sx,sy,sw,sh = _a_scale_bounds(source)
    tx,ty,tw,th = _a_scale_bounds(candidate)
    # Preserve the source's left/right spacing, not its old advance width.
    for path in candidate.paths:
        for node in path.nodes:
            node.x += sx-tx
    candidate = _a_scale_fresh(candidate.paths, source.width-sw+tw)
    _a_scale_validate_foot_levels(source,candidate,fy)
    _a_scale_validate_topology(source,candidate)
    return candidate,report


def _a_reference_belly(source, stem, left, root_y, left_weight, top_weight, bottom_weight):
	"""Retarget o's actual arcs into one separate, sharp-ended belly contour.

	Each quadrant carries all of its source segments, including facets and
	additional cubic subdivisions. No ellipse, fillet or node-count template
	is substituted. The two ends overlap the upright without being fused to it.
	"""
	outer, inner = _outer_and_inner_paths(_copy_decomposed(source))
	ot, _or, ob = _round_extrema(outer)
	it, ir, ib = _round_extrema(inner)
	ol = min(_oncurve_nodes(outer), key=lambda n: n.x)
	il = min(_oncurve_nodes(inner), key=lambda n: n.x)
	width = stem[1]-left
	bottom = float(ob.y)
	upper_y = root_y+0.015*(ot.y-ob.y)
	inner_upper_y, inner_bottom_y = upper_y-top_weight, bottom+bottom_weight
	if inner_upper_y <= inner_bottom_y+EPSILON:
		raise GenerationError("o's strokes leave no room for a's counter.")
	end_x = stem[0]+(stem[1]-stem[0])*0.20
	bar_x = stem[0]+(stem[1]-stem[0])*0.15
	outer_points = ((left+width*0.46, upper_y),
		(left, (upper_y+bottom)*0.5), (left+width*0.38,bottom),
		(end_x,bottom+(upper_y-bottom)*0.21))
	inner_points = ((left+width*0.48,inner_upper_y),
		(left+left_weight,(inner_upper_y+inner_bottom_y)*0.5),
		(left+width*0.48,inner_bottom_y),
		# The two return endpoints must stay a stroke-width apart. Using a
		# fraction of counter height creates a large dark wedge in thin a's.
		(end_x,outer_points[3][1]+bottom_weight*0.95))
	if inner_points[1][0] >= inner_points[0][0]-EPSILON:
		raise GenerationError("o's left stroke cannot fit a's belly width.")
	def quadrant(path, start, end, target_start, target_end):
		arc=[start]+_forward_between(path,start,end)
		# Choose the geometric quadrant, not the shortest node list: a quarter
		# with extra subdivisions may contain more nodes than the other route.
		landmarks=set(_round_extrema(path))|{min(_oncurve_nodes(path),key=lambda n:n.x)}
		if any(n in landmarks and n not in (start,end) for n in arc):
			path.reverse();arc=[start]+_forward_between(path,start,end)
		x_span,y_span = end.x-start.x,end.y-start.y
		if abs(x_span)<=EPSILON or abs(y_span)<=EPSILON:
			raise GenerationError("o needs distinct top, side and bottom landmarks for a.")
		fx=(target_end[0]-target_start[0])/x_span
		fy=(target_end[1]-target_start[1])/y_span
		sequence=[]
		for points,curve,s,e in _segment_sequence(arc):
			mapped=[]
			for x,y in points:
				xx=target_start[0]+(x-start.x)*fx
				yy=target_start[1]+(y-start.y)*fy
				mapped.append((xx,yy))
			sequence.append((tuple(mapped),curve,s,e))
		return sequence
	# Affine shear keeps both landmarks fixed and the left tangent vertical,
	# while aligning the upper tangent to the straight bar. Being affine, it
	# gives identical geometry when the source curve has extra subdivisions.
	def upper_arc(path, top, side, points):
		seq=quadrant(path,top,side,points[0],points[1])
		x0,y0=points[0];x1,y1=points[1]
		def shifted(p):
			return (p[0],p[1]+0.035*((p[0]-x0)-(x1-x0)*(p[1]-y0)/(y1-y0)))
		return [(tuple(shifted(p) for p in ps),curve,s,e) for ps,curve,s,e in seq]
	def lower_return(path, bottom_node, right, points):
		seq=quadrant(path,bottom_node,right,points[2],points[3])
		# A full o quadrant ends vertically. a's belly should instead flow
		# obliquely into the overlapping stem, as in the edited reference.
		# Use one endpoint-preserving affine shear across the whole arc:
		# subdivisions remain exact, C1 joins stay aligned, facets stay facets.
		if not seq[-1][1]:
			return seq
		x0,y0=points[2];x1,y1=points[3]
		ps=seq[-1][0]
		dx,dy=ps[3][0]-ps[2][0],ps[3][1]-ps[2][1]
		# Preserve an already oblique source tangent. Otherwise take the
		# natural tangent just before o's vertical side becomes a bowl return.
		# This is measured geometrically, not by a fixed angle or node index.
		if abs(dx)>0.10*max(EPSILON,(dx*dx+dy*dy)**0.5):
			return seq
		approach,_unused=_split_segment_sequence_at_line(seq,
			(x0+0.92*(x1-x0),y0),(0.0,1.0))
		sample=approach[-1][0]
		tx,ty=sample[3][0]-sample[2][0],sample[3][1]-sample[2][1]
		if min(tx,ty)<=EPSILON:
			return seq
		tangent_ratio=tx/ty
		denominator=dy-(y1-y0)*dx/(x1-x0)
		if abs(denominator)<=EPSILON:
			return seq
		shear=(tangent_ratio*dy-dx)/denominator
		def shifted(p):
			return (p[0]+shear*((p[1]-y0)-(y1-y0)*(p[0]-x0)/(x1-x0)),p[1])
		return [(tuple(shifted(p) for p in ps),curve,s,e) for ps,curve,s,e in seq]
	def sequence(path, top, side, bottom_node, right, points):
		return (upper_arc(path,top,side,points)
			+quadrant(path,side,bottom_node,points[1],points[2])
			+lower_return(path,bottom_node,right,points))
	outer_seq=sequence(outer,ot,ol,ob,_round_extrema(outer)[1],outer_points)
	inner_seq=sequence(inner,it,il,ib,ir,inner_points)
	belly=GSPath();belly.closed=True
	belly.nodes.append(_new_node(outer_points[0],LINE,bool(outer_seq[0][1])))
	_append_segment_sequence(belly,outer_seq)
	belly.nodes[-1].smooth=False
	belly.nodes.append(_new_node(inner_points[3],LINE,False))
	_append_segment_sequence(belly,_reverse_segment_sequence(inner_seq))
	belly.nodes[-1].smooth=bool(inner_seq[0][1])
	for point in ((bar_x,inner_upper_y+0.035*(bar_x-inner_points[0][0])),
		(bar_x,upper_y+0.035*(bar_x-outer_points[0][0]))):
		belly.nodes.append(_new_node(point,LINE,False))
	return belly


def _build_a_reference(font, master):
	"""Reference a: c arch, 95% h upright, and o-derived separate belly."""
	x_height=float(master.xHeight)
	o_source=_source_layer(font,"o",master.id)
	_h,left_stem,_right_stem=_measure_h_source(_source_layer(font,"h",master.id),master)
	outer,inner=_outer_and_inner_paths(_copy_decomposed(o_source))
	ot,_right,ob=_round_extrema(outer);it,_right,ib=_round_extrema(inner)
	top_weight=float(ot.y-it.y);bottom_weight=float(ib.y-ob.y)
	o_left=min(_oncurve_nodes(outer),key=lambda n:n.x)
	xs=_scan_x_intersections(o_source,float(o_left.y))
	if len(xs)<2: raise GenerationError("Could not measure o's left stroke for a.")
	left_weight=0.95*(xs[1]-xs[0])
	left,_bottom,right,_top=_bounds_values(o_source)
	width=(right-left)*0.94
	stem=(left+width-0.95*(left_stem[1]-left_stem[0]),left+width)
	root_y=x_height*0.58
	arch=_lowercase_c_half(font,master,True,stem,root_y,x_height-root_y,width,
		weight_factor=0.90,top_weight=0.90*top_weight)
	stem_path=_rectangle_path(stem[0],0.0,stem[1],root_y)
	belly=_a_reference_belly(o_source,stem,left,root_y,left_weight,
		0.78*top_weight,0.90*bottom_weight)
	candidate=_layer_from_paths([stem_path,belly],o_source.width)
	candidate=_a_attach_top(candidate,arch,stem,root_y)
	return _finish_candidate(candidate,remove_overlap=False)


def _build_a(font, master):
	"""Condense the complete reference a by 8%, preserving normal stroke weight."""
	reference=_build_a_reference(font,master)
	try:
		candidate,_report=_a_scale_scale_outline(reference,height=100,width=92,weight=100)
	except _AOutlineScaleError as error:
		raise GenerationError("a's width compensation: %s" % error)
	# Place the complete compensated arch at the outer x-height zone edge,
	# not the nominal x-height. Translate its geometry; keep the flat stem
	# foot on the baseline and leave the separate belly untouched.
	upper=max(candidate.paths,key=lambda p:_bounds_values(p)[3])
	foot_y=min(n.y for n in _oncurve_nodes(upper))
	feet=[n for n in _oncurve_nodes(upper) if abs(n.y-foot_y)<=EPSILON]
	_zone_position,zone_top=_master_metric_zone(master,GSMetricsTypexHeight,float(master.xHeight))
	shift=zone_top-_bounds_values(upper)[3]
	for node in upper.nodes:node.y=float(node.y)+shift
	for node in feet:node.y=foot_y
	return _finish_candidate(candidate,remove_overlap=False)


def _build_g(font, master):
	"""94% compensated bowl; the actual compensated a arch flipped vertically."""
	if float(master.descender)>=-EPSILON:
		raise GenerationError("The master needs a descender below the baseline for g.")
	# Use a's final upper contour, not another independently fitted c half.
	# Only its upright is lengthened; every curve, cap and Open Corner is the
	# vertically reflected a construction, including its width compensation.
	a_reference=_round_candidate_geometry(_build_a(font,master))
	upper=max(a_reference.paths,key=lambda p:_bounds_values(p)[3]).copy()
	foot_y=min(n.y for n in _oncurve_nodes(upper))
	feet=[n for n in _oncurve_nodes(upper) if abs(n.y-foot_y)<=EPSILON]
	if len(feet)!=2:
		raise GenerationError("Could not identify a's flat stem end for g.")
	_zone_position,zone_bottom=_master_metric_zone(master,GSMetricsTypeDescender,float(master.descender))
	reflection_y=zone_bottom+_bounds_values(upper)[3]
	for node in upper.nodes:node.y=reflection_y-float(node.y)
	for node in feet:node.y=float(master.xHeight)
	stem_center=sum(float(n.x) for n in feet)/len(feet)
	stem_inner=min(float(n.x) for n in feet)

	# Copy o's actual contour, including facets and arbitrary subdivisions.
	# Reflect it as in the old right-stem g, but do not refit its handles to h:
	# the shared upright provides the attachment. Scale the bowl independently
	# of that upright/tail, preserving its original local normal weights.
	bowl_reference=_copy_decomposed(_source_layer(font,"o",master.id))
	for path in bowl_reference.paths:
		for node in path.nodes:node.x=float(bowl_reference.width)-float(node.x)
	bowl_reference.correctPathDirection()
	try:
		bowl,_report=_a_scale_scale_outline(bowl_reference,height=94,width=94,weight=100,tolerance_floor=0.25)
	except _AOutlineScaleError as error:
		raise GenerationError("g's bowl compensation: %s" % error)
	_zone_position,zone_top=_master_metric_zone(master,GSMetricsTypexHeight,float(master.xHeight))
	_outer,_inner=_outer_and_inner_paths(bowl)
	bowl_join=max(_oncurve_nodes(_outer),key=lambda n:float(n.x))
	counter_join=max(_oncurve_nodes(_inner),key=lambda n:float(n.x))
	top=_bounds_values(bowl)[3]
	# Establish the bowl's position from the counter: its right side stays at
	# the left edge of the upright. Do not translate the bowl to its centre.
	_translate_paths(bowl.paths,stem_inner-float(counter_join.x),zone_top-top)
	# As in b, adjust only the outer side landmark and its attached handles.
	# The counter and all other bowl nodes retain their anchored positions.
	_move_extreme_with_handles(_outer,bowl_join,dx=stem_center-float(bowl_join.x))
	candidate=_layer_from_paths([upper]+list(bowl.paths),a_reference.width)
	return _finish_candidate(candidate,remove_overlap=False)


def _build_y(font, master):
	"""Keep v intact and extend its rising right stroke along the same axis."""
	source = _source_layer(font, "v", master.id)
	candidate = _copy_decomposed(source)
	x_height, depth = float(master.xHeight), abs(float(master.descender))
	if min(x_height, depth) <= EPSILON:
		raise GenerationError("The master needs positive x-height and descender depth for y.")
	profiles = []
	for fraction in (0.40, 0.55, 0.70):
		y = x_height * fraction
		xs = _scan_x_intersections(candidate, y)
		if len(xs) < 4:
			raise GenerationError("v needs an identifiable right diagonal for y.")
		profiles.append((y, xs[-2], xs[-1]))
	slope = (profiles[-1][2]-profiles[0][2]) / (profiles[-1][0]-profiles[0][0])
	if slope <= EPSILON:
		raise GenerationError("v's right stroke must rise to the right for y.")
	outer_axis = profiles[1][2]-slope*profiles[1][0]
	# Normal thickness is horizontal scan width / sqrt(1+slope^2).
	# The continuation preserves that thickness and the original angle exactly.
	width = profiles[0][2]-profiles[0][1]
	root_y, bottom_y = profiles[0][0], -depth
	tail = GSPath()
	tail.closed = True
	for y, offset in ((root_y,-width), (root_y,0), (bottom_y,0), (bottom_y,-width)):
		tail.nodes.append(_new_node((outer_axis+slope*y+offset, y), LINE, False))
	candidate.shapes.append(tail)
	_correct_X_diagonal_directions(candidate)
	return _round_candidate_geometry(candidate)


BUILDERS = {
	"A": _build_A,
	"B": _build_B,
	"C": lambda font, master: _build_C(font, master, "C"),
	"G": _build_G,
	"E": lambda font, master: _build_H_derived(font, master, "E"),
	"F": lambda font, master: _build_H_derived(font, master, "F"),
	"I": lambda font, master: _build_H_derived(font, master, "I"),
	"J": _build_J,
	"K": _build_K,
	"L": lambda font, master: _build_H_derived(font, master, "L"),
	"M": _build_M,
	"N": _build_N,
	"P": _build_P,
	"Q": _build_Q,
	"R": _build_R,
	"S": _build_S,
	"T": lambda font, master: _build_H_derived(font, master, "T"),
	"D": _build_D,
	"U": _build_U,
	"V": _build_V,
	"W": lambda font, master: _build_double_v(font, master, "W"),
	"X": _build_X,
	"Y": _build_Y,
	"Z": _build_Z,
	"a": _build_a,
	"c": _build_c,
	"e": _build_e,
	"f": lambda font, master: _build_ft(font, master, "f"),
	"g": _build_g,
	"i": _build_i,
	"j": _build_j,
	"k": _build_k,
	"l": _build_l,
	"n": _build_n,
	"m": _build_m,
	"o": _build_o,
	"r": _build_r,
	"s": _build_s,
	"t": lambda font, master: _build_ft(font, master, "t"),
	"u": _build_u,
	"v": _build_v,
	"w": lambda font, master: _build_double_v(font, master, "w"),
	"x": _build_x,
	"y": _build_y,
	"z": _build_z,
	"b": lambda font, master: _build_bowl_stem(font, master, "b"),
	"d": lambda font, master: _build_bowl_stem(font, master, "d"),
	"p": lambda font, master: _build_bowl_stem(font, master, "p"),
	"q": lambda font, master: _build_bowl_stem(font, master, "q"),
}


BUILD_SOURCES = {
	"a": ("h", "o", "c"), "g": ("h", "o", "c"), "y": ("v",),
	"A": ("V", "H"),
	"B": ("H", "D"),
	"C": ("O",), "G": ("C", "H"), "c": ("C",),
	"E": ("H",), "F": ("H",), "I": ("H",), "K": ("H", "X"), "L": ("H",), "M": ("H", "V"), "N": ("H",), "T": ("H",),
	"D": ("H", "O"), "P": ("D", "H"), "U": ("H", "O"), "J": ("U", "C", "H"),
	"Q": ("O", "H"), "R": ("P", "V"), "S": ("C",), "s": ("S",),
	"X": ("H",), "V": ("X",), "Y": ("V", "H"), "Z": ("H",),
	"W": ("V",), "v": ("V",), "w": ("v",), "x": ("X",),
	"n": ("h",), "m": ("h",), "o": ("O",), "r": ("h", "C"), "u": ("h",),
	"i": ("h",), "j": ("h", "H"),
	"e": ("C", "H"),
	"k": ("K", "h"), "l": ("h",), "z": ("Z",),
	"f": ("j", "H", "h"), "t": ("j", "H", "h"),
	"b": ("h", "o"), "d": ("h", "o"), "p": ("h", "o"), "q": ("h", "o"),
}


def _compatibility_signature(layer):
	return tuple(
		(
			bool(path.closed),
			tuple(str(node.type) for node in path.nodes),
		)
		for path in layer.paths
	)


def _layer_fingerprint(layer):
	"""Fingerprint geometry and width so generated layers can be edited safely."""
	record = [("width", round(float(layer.width), 4))]
	for shape in layer.shapes:
		if hasattr(shape, "nodes"):
			record.append(
				(
					"path",
					bool(shape.closed),
					tuple(
						(
							str(node.type),
							bool(node.smooth),
							round(float(node.x), 4),
							round(float(node.y), 4),
						)
						for node in shape.nodes
					),
				)
			)
		else:
			transform = getattr(shape, "transform", None)
			try:
				transform_record = tuple(round(float(value), 6) for value in transform)
			except Exception:
				transform_record = repr(transform)
			record.append(
				(
					shape.__class__.__name__,
					str(getattr(shape, "componentName", "")),
					transform_record,
				)
			)
	payload = repr(tuple(record)).encode("utf-8")
	return hashlib.sha256(payload).hexdigest()


def _provenance_value(layer, key):
	try:
		provenance = layer.userData[USER_DATA_KEY]
	except Exception:
		return None
	if provenance is None:
		return None
	try:
		return provenance.get(key)
	except Exception:
		try:
			return provenance[key]
		except Exception:
			return None


def _overwrite_conflicts(font, characters, masters):
	"""Return existing layers whose generated geometry cannot be verified."""
	conflicts = []
	for character in characters:
		try:
			glyph = font.glyphs[character]
		except (KeyError, IndexError):
			glyph = None
		if glyph is None:
			continue
		for master in masters:
			layer = glyph.layers[master.id]
			if layer is None or not layer.shapes:
				continue
			saved = _provenance_value(layer, "fingerprint")
			if saved is None or str(saved) != _layer_fingerprint(layer):
				conflicts.append((character, master.name))
	return conflicts


def _confirm_overwrite(font, characters, masters):
	conflicts = _overwrite_conflicts(font, characters, masters)
	if not conflicts:
		return
	labels = ["%s — %s" % item for item in conflicts[:8]]
	if len(conflicts) > len(labels):
		labels.append("…and %i more" % (len(conflicts) - len(labels)))
	alert = NSAlert.alloc().init()
	alert.setAlertStyle_(NSAlertStyleWarning)
	alert.setMessageText_("Overwrite manually modified outlines?")
	alert.setInformativeText_(
		"Build Rough Draft cannot verify that these layers still match its last "
		"build:\n\n%s\n\nOverwrite them with newly built outlines?"
		% "\n".join(labels)
	)
	alert.addButtonWithTitle_("Overwrite")
	alert.addButtonWithTitle_("Cancel")
	if alert.runModal() != NSAlertFirstButtonReturn:
		raise GenerationError("Build cancelled; no outlines were changed.")


def _replace_shapes(target, candidate, character):
	for index in range(len(target.shapes) - 1, -1, -1):
		del target.shapes[index]
	for shape in candidate.shapes:
		target.shapes.append(shape.copy())
	target.width = candidate.width
	target.userData[USER_DATA_KEY] = {
		"version": VERSION,
		"sources": list(BUILD_SOURCES[character]),
		"fingerprint": _layer_fingerprint(target),
	}
	if character in ("i", "j"):
		record = dict(target.userData[USER_DATA_KEY])
		record["dotShape"] = str(candidate.userData[DOT_SHAPE_KEY])
		target.userData[USER_DATA_KEY] = record


def _round_candidate_geometry(candidate):
	"""Snap every generated coordinate to whole font units before installation."""
	for shape in candidate.shapes:
		# PyObjC can return concrete GSPath subclasses/proxies whose Python
		# isinstance result varies, so use the path's stable node interface.
		if hasattr(shape, "nodes"):
			for index, node in enumerate(list(shape.nodes)):
				# Replacing the node is deliberate: Glyphs can retain a tiny affine
				# residue when an attached node is moved in place. A fresh node stores
				# the integer coordinate exactly. Preserve semantic node metadata.
				replacement = _new_node(
					(round(float(node.x)), round(float(node.y))),
					node.type,
					node.smooth,
				)
				try:
					node_name = node.name
					if node_name and str(node_name) != "None":
						replacement.name = node_name
				except Exception:
					pass
				try:
					for key in node.userData.keys():
						replacement.userData[key] = node.userData[key]
				except Exception:
					pass
				shape.nodes[index] = replacement
		elif isinstance(shape, GSComponent):
			try:
				position = shape.position
				shape.position = (
					round(float(position.x)),
					round(float(position.y)),
				)
			except Exception:
				pass
	candidate.width = round(float(candidate.width))
	return candidate


def _masters_for_generation(font, all_masters):
	if font is None:
		raise GenerationError("No font is open.")
	if all_masters:
		return list(font.masters)
	master = font.selectedFontMaster
	if master is None:
		raise GenerationError("Could not determine the current master.")
	return [master]


def _spacing_outline(font, layer, master_id, visiting=()):
	"""Resolve measurement-only outlines, including not-yet-installed components."""
	paths = []
	for shape in layer.shapes:
		if hasattr(shape, "nodes"):
			paths.append(shape.copy())
		elif isinstance(shape, GSComponent):
			name = str(shape.componentName)
			if name in visiting:
				raise GenerationError("Cyclic component reference while spacing %s." % name)
			source = _source_layer(font, name, master_id)
			resolved = _spacing_outline(font, source, master_id, visiting + (name,))
			xx, yx, xy, yy, dx, dy = tuple(shape.transform)
			for path in resolved.paths:
				for node in path.nodes:
					x, y = float(node.x), float(node.y)
					node.position = (xx * x + xy * y + dx, yx * x + yy * y + dy)
				paths.append(path.copy())
	return _layer_from_paths(paths, float(layer.width))


def _optical_edge_recession(outline, height):
	"""Measure each side's near-edge whitespace, not counters or distant apertures.

	A bounded falloff keeps a wide open side or diagonal from requesting huge
	negative bearings. The H and O measurements calibrate this to the actual font.
	"""
	left, _bottom, right, _top = _bounds_values(outline)
	reach = max(1.0, float(height) * 0.12)
	values = [[], []]
	for index in range(40):
		y = float(height) * (index + 0.5) / 40.0
		intersections = _scan_x_intersections(outline, y)
		if not intersections:
			gaps = (reach, reach)
		else:
			gaps = (
				reach * (1.0 - exp(-max(0.0, intersections[0] - left) / reach)),
				reach * (1.0 - exp(-max(0.0, right - intersections[-1]) / reach)),
			)
		for side in (0, 1):
			values[side].append(gaps[side])
	return tuple(sum(side) / len(side) for side in values)


def _apply_HO_optical_spacing(font, candidate, character, master):
	"""Calibrate both sidebearings to the user's H/O, independently per master."""
	try:
		H = _spacing_outline(font, _source_layer(font, "H", master.id), master.id)
		O = _spacing_outline(font, _source_layer(font, "O", master.id), master.id)
	except GenerationError:
		# Do not add a new prerequisite to recipes unlocked by h or other sources.
		return candidate
	height = float(master.xHeight if character.islower() else master.capHeight)
	if height <= EPSILON or float(master.capHeight) <= EPSILON:
		return candidate
	if character.islower():
		# Reference the same HO spacing density at the lowercase body size.
		scale = height / float(master.capHeight)
		for reference in (H, O):
			_transform_paths_affinely(reference.paths, (0, 0), (0, 0), scale, scale)
			reference.width = float(reference.width) * scale
		H = _layer_from_paths(list(H.paths), H.width)
		O = _layer_from_paths(list(O.paths), O.width)
	H_left, _bottom, H_right, _top = _bounds_values(H)
	O_left, _bottom, O_right, _top = _bounds_values(O)
	H_margins = (H_left, float(H.width) - H_right)
	O_margins = (O_left, float(O.width) - O_right)
	H_edges = _optical_edge_recession(H, height)
	O_edges = _optical_edge_recession(O, height)
	outline = _spacing_outline(font, candidate, master.id)
	if not outline.paths:
		return candidate
	left, _bottom, right, _top = _bounds_values(outline)
	edges = _optical_edge_recession(outline, height)
	margins = []
	for side in (0, 1):
		calibration = O_edges[side] - H_edges[side]
		if abs(calibration) <= 1.0:
			# Square O styles provide no reliable curvature calibration.
			margin = H_margins[side]
		else:
			ratio = max(0.0, (edges[side] - H_edges[side]) / calibration)
			difference = H_margins[side] - O_margins[side]
			if ratio <= 1.0:
				margin = H_margins[side] - difference * ratio
			else:
				# Tighten angled/open sides conservatively beyond the round reference.
				# Adding the same amount to HO therefore adds it to every result too.
				margin = O_margins[side] - difference * 0.5 * (1.0 - exp(1.0 - ratio))
		margins.append(round(max(min(0.0, *H_margins, *O_margins), margin)))
	dx = round(margins[0] - left)
	for shape in candidate.shapes:
		if hasattr(shape, "nodes"):
			_translate_paths([shape], dx)
		elif isinstance(shape, GSComponent):
			position = shape.position
			shape.position = (float(position.x) + dx, float(position.y))
	candidate.width = round((right - left) + margins[0] + margins[1])
	return candidate


def _build_candidates(font, character, masters, dot_shape="round"):
	if character not in BUILDERS:
		raise GenerationError("Unsupported target: %s." % character)

	# Build every result off-canvas before touching the target. A geometry error in one
	# master therefore cannot leave the destination partially regenerated.
	candidates = []
	for master in masters:
		try:
			if character in ("i", "j"):
				candidate = BUILDERS[character](font, master, dot_shape=dot_shape)
			else:
				candidate = BUILDERS[character](font, master)
			candidate = _round_candidate_geometry(candidate)
			if character in ("A", "M", "V", "W", "Y", "v", "w", "y", "X", "x", "e", "k"):
				_correct_X_diagonal_directions(candidate)
			else:
				candidate.correctPathDirection()
			candidate = _apply_HO_optical_spacing(font, candidate, character, master)
		except GenerationError as error:
			raise GenerationError(
				"%s — %s: %s" % (character, master.name, error)
			)
		candidates.append((master, candidate))

	if len(candidates) > 1:
		reference_master, reference = candidates[0]
		reference_signature = _compatibility_signature(reference)
		for master, candidate in candidates[1:]:
			if _compatibility_signature(candidate) != reference_signature:
				raise GenerationError(
					"%s is not interpolation-compatible between %s and %s. "
					"Check that its %s sources have matching topology."
					% (
						character,
						reference_master.name,
						master.name,
						" + ".join(BUILD_SOURCES[character]),
					)
				)

	return candidates


def _install_candidates(font, character, candidates):
	glyph = _target_glyph(font, character)
	glyph.beginUndo()
	try:
		for master, candidate in candidates:
			target = glyph.layers[master.id]
			if target is None:
				target = GSLayer()
				target.layerId = master.id
				target.associatedMasterId = master.id
				glyph.layers[master.id] = target
			target.beginChanges()
			try:
				_replace_shapes(target, candidate, character)
			finally:
				target.endChanges()
	finally:
		glyph.endUndo()


def _clear_glyph_paths(font, characters, master):
	"""Clear paths only in the explicit master; preserve components and metrics."""
	targets = []
	for character in dict.fromkeys(characters):
		glyph = font.glyphs[character]
		layer = glyph.layers[master.id] if glyph is not None else None
		if layer is not None and len(layer.paths):
			targets.append((character, glyph, layer))
	removed = 0
	font.disableUpdateInterface()
	try:
		for _character, glyph, layer in targets:
			glyph.beginUndo()
			layer.beginChanges()
			try:
				for index in range(len(layer.shapes) - 1, -1, -1):
					if hasattr(layer.shapes[index], "nodes"):
						del layer.shapes[index]
						removed += 1
				layer.userData[USER_DATA_KEY] = None
			finally:
				layer.endChanges()
				glyph.endUndo()
	finally:
		font.enableUpdateInterface()
	Glyphs.redraw()
	return tuple(character for character, _glyph, _layer in targets), removed


def generate(font, character, all_masters, dot_shape="round"):
	masters = _masters_for_generation(font, all_masters)
	candidates = _build_candidates(font, character, masters, dot_shape=dot_shape)
	_confirm_overwrite(font, (character,), masters)
	if hasattr(font, "disableUpdateInterface"):
		font.disableUpdateInterface()
	try:
		_install_candidates(font, character, candidates)
	finally:
		if hasattr(font, "enableUpdateInterface"):
			font.enableUpdateInterface()

	Glyphs.redraw()
	return [master.name for master, _candidate in candidates]


def _missing_sources(font, character, masters):
	missing = []
	for source_name in BUILD_SOURCES[character]:
		try:
			glyph = font.glyphs[source_name] if font is not None else None
		except (KeyError, IndexError):
			glyph = None
		if glyph is None:
			missing.append(source_name)
			continue
		for master in masters:
			layer = glyph.layers[master.id]
			if layer is None or not layer.shapes:
				missing.append(source_name)
				break
	return tuple(missing)


def _available_characters(font, masters):
	return tuple(
		character
		for character in CHARACTERS
		if not _missing_sources(font, character, masters)
	)


def _dependency_order(characters):
	"""Order selected recipes so generated sources precede their descendants."""
	requested = set(characters)
	ordered = []
	visiting = set()
	visited = set()

	def visit(character):
		if character in visited:
			return
		if character in visiting:
			raise GenerationError("Build recipes contain a dependency cycle at %s." % character)
		visiting.add(character)
		for source_name in BUILD_SOURCES.get(character, ()):
			if source_name in requested:
				visit(source_name)
		visiting.remove(character)
		visited.add(character)
		ordered.append(character)

	for character in characters:
		visit(character)
	return tuple(ordered)


def _build_candidate_batch(font, characters, masters, dot_shape="round"):
	"""Preflight a dependency-ordered batch without mutating the font."""
	global _SOURCE_LAYER_OVERRIDES
	ordered = _dependency_order(characters)
	overrides = {}
	all_candidates = []
	previous_overrides = _SOURCE_LAYER_OVERRIDES
	_SOURCE_LAYER_OVERRIDES = overrides
	try:
		for character in ordered:
			candidates = _build_candidates(font, character, masters, dot_shape=dot_shape)
			all_candidates.append((character, candidates))
			for master, candidate in candidates:
				overrides[(character, master.id)] = candidate
	finally:
		_SOURCE_LAYER_OVERRIDES = previous_overrides
	return all_candidates


def generate_all(font, all_masters, characters=None, dot_shape="round"):
	masters = _masters_for_generation(font, all_masters)
	characters = tuple(CHARACTERS if characters is None else characters)
	if not characters:
		raise GenerationError("Draw at least one base glyph to unlock its relatives.")
	all_candidates = _build_candidate_batch(font, characters, masters, dot_shape=dot_shape)
	_confirm_overwrite(font, characters, masters)

	if hasattr(font, "disableUpdateInterface"):
		font.disableUpdateInterface()
	try:
		for character, candidates in all_candidates:
			_install_candidates(font, character, candidates)
	finally:
		if hasattr(font, "enableUpdateInterface"):
			font.enableUpdateInterface()

	Glyphs.redraw()
	return [master.name for master in masters]


def _tab_text_tokens(text):
	"""Tokenize Glyphs edit text while keeping slash-escaped names intact."""
	tokens = []
	index = 0
	while index < len(text):
		if text[index] != "/":
			tokens.append(text[index])
			index += 1
			continue
		end = index + 1
		while end < len(text) and text[end] not in "/\n\r\t ":
			end += 1
		tokens.append(text[index:end])
		index = end
	return tokens


def _glyph_tab_tokens(font, glyph_name):
	"""Return the literal and slash-escaped tokens that display one glyph."""
	result = {"/%s" % glyph_name}
	try:
		glyph = font.glyphs[glyph_name]
	except (KeyError, IndexError):
		glyph = None
	if glyph is not None:
		unicode_value = getattr(glyph, "unicode", None)
		if unicode_value:
			try:
				result.add(chr(int(str(unicode_value), 16)))
			except (TypeError, ValueError):
				pass
	if len(glyph_name) == 1:
		result.add(glyph_name)
	return result


def _show_in_current_tab(font, glyph_names):
	"""Insert missing glyphs beside the active glyph; retain existing instances."""
	tab = getattr(font, "currentTab", None)
	if tab is None:
		return
	active_tool = getattr(font, "tool", None)
	tokens = _tab_text_tokens(tab.text or "")
	token_set = set(tokens)
	missing_names = [
		glyph_name
		for glyph_name in glyph_names
		if not (_glyph_tab_tokens(font, glyph_name) & token_set)
	]
	if not missing_names:
		return
	generated_text = "".join(
		glyph_name if len(glyph_name) == 1 else "/%s" % glyph_name
		for glyph_name in missing_names
	)
	insertion_point = max(0, min(int(tab.textCursor), len(tokens)))
	selection = getattr(tab, "selectedTextRange", None)
	selection_length = int(selection.length) if selection is not None else 0
	if selection_length:
		insertion_point = min(
			len(tokens), int(selection.location) + selection_length
		)
	elif getattr(font, "tool", "") == "SelectTool" and tokens:
		# In the Select tool textCursor identifies the edited glyph, not a gap.
		insertion_point = min(len(tokens), insertion_point + 1)
	tab.text = (
		"".join(tokens[:insertion_point])
		+ generated_text
		+ "".join(tokens[insertion_point:])
	)
	if active_tool is not None:
		try:
			font.tool = active_tool
		except Exception:
			pass
	try:
		tab.textCursor = insertion_point
	except Exception:
		pass


try:
	_DependencyMenuDelegate = objc.lookUpClass(
		"ATBuildBasicShapesDependencyMenuDelegateV2"
	)
except objc.nosuchclass_error:
	class ATBuildBasicShapesDependencyMenuDelegateV2(NSObject):
		"""Refresh availability immediately before Cocoa opens the popup menu."""

		def menuNeedsUpdate_(self, _menu):
			controller = getattr(self, "controller", None)
			if controller is not None:
				controller._refresh_character_menu()

		def menu_willHighlightItem_(self, _menu, item):
			controller = getattr(self, "controller", None)
			if controller is not None:
				controller._menu_highlighted(item)

	_DependencyMenuDelegate = ATBuildBasicShapesDependencyMenuDelegateV2


class GenerateBasicGlyphsWindowController:
	def __init__(self):
		if Glyphs.font is None:
			raise GenerationError("Open a font in Glyphs, then run the script again.")

		self.w = vanilla.FloatingWindow(
			(400, 176),
			TITLE,
			autosaveName=PREF_DOMAIN + ".window",
		)
		margin = 18
		label_width = 88
		field_left = margin + label_width

		self.w.prerequisite = vanilla.TextBox(
			(margin, 16, -margin, 20),
			"Before building relatives, manually draw H, O, h.",
			sizeStyle="small",
		)
		self.w.characterLabel = vanilla.TextBox(
			(margin, 52, label_width, 20), "Build:"
		)
		self.w.character = vanilla.PopUpButton(
			(field_left, 48, -margin, 24),
			list(GENERATION_OPTIONS),
			callback=self._character_changed,
		)
		saved_target = self._pref("target", "E")
		try:
			self.w.character.set(GENERATION_OPTIONS.index(saved_target))
		except ValueError:
			self.w.character.set(GENERATION_OPTIONS.index("E"))
		self.w.allMasters = vanilla.CheckBox(
			(margin, 88, -margin, 20),
			"Build in all masters",
			value=bool(self._pref("allMasters", True)),
			callback=self._scope_changed,
		)
		self.w.status = vanilla.TextBox(
			(margin, 129, -140, 20), "Ready.", sizeStyle="small"
		)
		self.w.generateButton = vanilla.Button(
			(-126, -38, -margin, 24), "Build", callback=self.generate_clicked
		)
		self._busy = False
		popup = self.w.character.getNSPopUpButton()
		self._character_menu = popup.menu()
		self._character_menu.setAutoenablesItems_(False)
		self._menu_delegate = _DependencyMenuDelegate.alloc().init()
		self._menu_delegate.controller = self
		self._character_menu.setDelegate_(self._menu_delegate)
		self._refresh_character_menu(select_available=True)
		self.w.setDefaultButton(self.w.generateButton)
		self.w.open()
		self._configure_native_window()
		self.w.makeKey()

	def _configure_native_window(self):
		window = self.w.getNSWindow()
		if window is None:
			return
		# Stay above Glyphs' documents, but hide when another application activates.
		window.setHidesOnDeactivate_(True)
		window.setSharingType_(NSWindowSharingReadOnly)
		window.setCollectionBehavior_(
			(window.collectionBehavior() & ~NSWindowCollectionBehaviorCanJoinAllSpaces)
			| NSWindowCollectionBehaviorFullScreenAuxiliary
		)

	@staticmethod
	def _pref_key(key):
		return "%s.%s" % (PREF_DOMAIN, key)

	def _pref(self, key, fallback):
		value = Glyphs.defaults[self._pref_key(key)]
		return fallback if value is None else value

	def _selected_masters(self):
		return _masters_for_generation(
			Glyphs.font, bool(self.w.allMasters.get())
		)

	@staticmethod
	def _unlock_tooltip(missing):
		if len(missing) == 1:
			return "Draw %s to build" % missing[0]
		return "Draw %s to build" % " + ".join(missing)

	def _refresh_character_menu(self, select_available=False):
		if self._busy or Glyphs.font is None:
			return
		try:
			masters = self._selected_masters()
		except GenerationError:
			return
		available = _available_characters(Glyphs.font, masters)
		available_set = set(available)
		self._option_unlocked = {}
		self._option_messages = {}
		for index, option in enumerate(GENERATION_OPTIONS):
			item = self._character_menu.itemAtIndex_(index)
			if option == ALL_CHARACTERS_LABEL:
				enabled = bool(available)
				tooltip = (
					"Build all currently unlocked characters"
					if enabled
					else "Draw H, O, or h to build"
				)
			else:
				missing = _missing_sources(Glyphs.font, option, masters)
				enabled = option in available_set
				tooltip = (
					"Build %s from %s"
					% (option, " + ".join(BUILD_SOURCES[option]))
					if enabled
					else self._unlock_tooltip(missing)
				)
			self._option_unlocked[option] = enabled
			self._option_messages[option] = tooltip
			# Cocoa does not highlight disabled menu items. Keep locked entries
			# active for mouse tracking, but draw their titles with the disabled
			# text color and prevent building them below.
			attributes = (
				{}
				if enabled
				else {NSForegroundColorAttributeName: NSColor.disabledControlTextColor()}
			)
			item.setAttributedTitle_(
				NSAttributedString.alloc().initWithString_attributes_(
					option, attributes
				)
			)
			item.setEnabled_(True)
			item.setToolTip_(tooltip)

		selected_index = int(self.w.character.get())
		selected_option = GENERATION_OPTIONS[selected_index]
		selected_unlocked = self._option_unlocked.get(selected_option, False)
		self.w.generateButton.enable(selected_unlocked)
		if not selected_unlocked:
			self.w.status.set(self._option_messages[selected_option])

	def _menu_highlighted(self, item):
		if item is None:
			return
		option = str(item.title())
		message = self._option_messages.get(option)
		if message:
			self.w.status.set(message)

	def _character_changed(self, _sender):
		self._refresh_character_menu()
		option = GENERATION_OPTIONS[int(self.w.character.get())]
		self.w.status.set(self._option_messages.get(option, "Ready."))

	def _scope_changed(self, _sender):
		self._refresh_character_menu(select_available=True)

	def _set_busy(self, busy, status):
		self._busy = bool(busy)
		for control in (
			self.w.character,
			self.w.allMasters,
			self.w.generateButton,
		):
			control.enable(not busy)
		self.w.status.set(status)
		if not busy:
			self._refresh_character_menu(select_available=True)

	def generate_clicked(self, _sender):
		try:
			self._refresh_character_menu(select_available=True)
			target = GENERATION_OPTIONS[self.w.character.get()]
			if not self._option_unlocked.get(target, False):
				raise GenerationError(self._option_messages[target])
			all_masters = bool(self.w.allMasters.get())
			Glyphs.defaults[self._pref_key("target")] = target
			Glyphs.defaults[self._pref_key("allMasters")] = all_masters
			if target == ALL_CHARACTERS_LABEL:
				masters = _masters_for_generation(Glyphs.font, all_masters)
				characters = _available_characters(Glyphs.font, masters)
				self._set_busy(True, "Building %i characters…" % len(characters))
				master_names = generate_all(
					Glyphs.font, all_masters, characters=characters
				)
				self._set_busy(
					False,
					"Built %i characters in %s."
					% (len(characters), ", ".join(master_names)),
				)
				_show_in_current_tab(Glyphs.font, characters)
			else:
				self._set_busy(True, "Building…")
				master_names = generate(Glyphs.font, target, all_masters)
				self._set_busy(
					False,
					"Built %s in %s." % (target, ", ".join(master_names)),
				)
				_show_in_current_tab(Glyphs.font, (target,))
		except GenerationError as error:
			self._set_busy(False, str(error))
			Message(title=TITLE, message=str(error), OKButton=None)
		except Exception:
			self._set_busy(False, "Unexpected error; see Macro window.")
			Glyphs.showMacroWindow()
			print("%s failed:\n%s" % (TITLE, traceback.format_exc()))
			Message(
				title=TITLE,
				message="An unexpected error occurred. Details are in the Macro window.",
				OKButton=None,
			)


try:
	_LetterHoverTips = objc.lookUpClass("ATBuildRoughDraftLetterHoverTipsV1")
except objc.nosuchclass_error:
	class ATBuildRoughDraftLetterHoverTipsV1(NSObject):
		"""Panel-local hover tips, including genuinely disabled letter buttons."""

		def init(self):
			self = objc.super(ATBuildRoughDraftLetterHoverTipsV1, self).init()
			if self is not None:
				self._timer = None
				self._view = None
				self._popover = None
			return self

		def attachToButton_(self, button):
			area = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
				button.bounds(),
				NSTrackingMouseEnteredAndExited
				| NSTrackingActiveInActiveApp | NSTrackingInVisibleRect,
				self, {"view": button},
			)
			button.addTrackingArea_(area)

		def mouseEntered_(self, event):
			self.hideTip_(None)
			self._view = event.trackingArea().userInfo()["view"]
			self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
				LETTER_TOOLTIP_DELAY, self, "showTip:", None, False,
			)
			NSRunLoop.mainRunLoop().addTimer_forMode_(
				self._timer, NSRunLoopCommonModes,
			)

		def mouseExited_(self, event):
			if self._view == event.trackingArea().userInfo()["view"]:
				self.hideTip_(None)

		def showTip_(self, _timer):
			self._timer = None
			view = self._view
			if view is None or view.window() is None or not view.window().isVisible():
				return
			message = view.accessibilityHelp()
			if not message:
				return
			field = NSTextField.alloc().initWithFrame_(((10, 8), (320, 20)))
			field.setStringValue_(message)
			field.setFont_(NSFont.systemFontOfSize_(11.0))
			field.setTextColor_(NSColor.labelColor())
			field.setEditable_(False)
			field.setSelectable_(False)
			field.setBezeled_(False)
			field.setDrawsBackground_(False)
			field.sizeToFit()
			width = min(320.0, float(field.frame().size.width))
			field.cell().setWraps_(True)
			field.cell().setScrollable_(False)
			height = float(field.cell().cellSizeForBounds_(((0, 0), (width, 1000))).height)
			field.setFrame_(((10, 8), (width, height)))
			content = NSView.alloc().initWithFrame_(((0, 0), (width + 20, height + 16)))
			content.addSubview_(field)
			controller = NSViewController.alloc().init()
			controller.setView_(content)
			self._popover = NSPopover.alloc().init()
			self._popover.setContentViewController_(controller)
			self._popover.setAnimates_(False)
			self._popover.setBehavior_(NSPopoverBehaviorApplicationDefined)
			self._popover.showRelativeToRect_ofView_preferredEdge_(
				view.bounds(), view, NSMaxYEdge,
			)

		def hideTip_(self, _sender):
			if self._timer is not None:
				self._timer.invalidate()
				self._timer = None
			if self._popover is not None:
				self._popover.close()
				self._popover = None
			self._view = None

	_LetterHoverTips = ATBuildRoughDraftLetterHoverTipsV1


def _dot_shape_alert(characters):
	"""A compact native choice shown only when a build includes i or j."""
	letters = tuple(character for character in ("i", "j") if character in characters)
	alert = NSAlert.alloc().init()
	alert.setMessageText_("Dot shape for %s" % " + ".join(letters))
	alert.setInformativeText_(
		"Choose a dot shape to build these letters. "
		"The same choice applies to all selected masters."
	)
	round_button = alert.addButtonWithTitle_("Round")
	square_button = alert.addButtonWithTitle_("Square")
	cancel_button = alert.addButtonWithTitle_("Cancel")
	last_choice = Glyphs.defaults[DOT_SHAPE_KEY] or "round"
	round_button.setKeyEquivalent_("\r" if last_choice != "square" else "")
	square_button.setKeyEquivalent_("\r" if last_choice == "square" else "")
	cancel_button.setKeyEquivalent_("\x1b")
	return alert


def _choose_dot_shape(characters):
	if not any(character in ("i", "j") for character in characters):
		return "round"
	response = _dot_shape_alert(characters).runModal()
	if response == NSAlertFirstButtonReturn:
		choice = "round"
	elif response == NSAlertSecondButtonReturn:
		choice = "square"
	else:
		return None
	Glyphs.defaults[DOT_SHAPE_KEY] = choice
	return choice


class BuildRoughDraftWindowController:
	def __init__(self):
		if Glyphs.font is None:
			raise GenerationError("Open a font in Glyphs, then run the script again.")

		self._busy = False
		self._selected_characters = set()
		self._available_characters = set()
		self._built_characters = set()
		self._letter_buttons = {}
		self._hover_tips = _LetterHoverTips.alloc().init()
		self._dependencies_window = None
		self.w = vanilla.FloatingWindow(
			(500, 346),
			TITLE,
			autosaveName=PREF_DOMAIN + ".window",
		)
		margin = 18
		cell = 32
		gap = 4

		self.w.prerequisite = vanilla.TextBox(
			(margin, 14, -52, 20),
			"Before building relatives, manually draw H, O, h.",
			sizeStyle="small",
		)
		self.w.helpButton = vanilla.HelpButton(
			(-margin - 21, 12, 21, 20), callback=self._show_dependencies,
		)
		self.w.helpButton.getNSButton().setAccessibilityLabel_(
			"Show glyph dependencies"
		)
		self.w.helpButton.getNSButton().setToolTip_("Show glyph dependencies")
		legend_text = (
			"● Source glyphs   ● Generated glyphs   ● Not yet generated"
		)
		self.w.legend = vanilla.TextBox(
			(margin, 35, -margin, 14), legend_text, sizeStyle="mini"
		)
		legend = NSMutableAttributedString.alloc().initWithString_(legend_text)
		legend.addAttribute_value_range_(
			NSFontAttributeName,
			NSFont.systemFontOfSize_(9.0),
			(0, len(legend_text)),
		)
		legend_ranges = (
			("● Source glyphs", SOURCE_TITLE_COLOR),
			("● Generated glyphs", BUILT_TITLE_COLOR),
			("● Not yet generated", UNBUILT_TITLE_COLOR),
		)
		for text, color in legend_ranges:
			start = legend_text.index(text)
			legend.addAttribute_value_range_(
				NSForegroundColorAttributeName,
				color,
				(start, len(text)),
			)
		self.w.legend.getNSTextField().setAttributedStringValue_(legend)
		self.w.uppercaseLabel = vanilla.TextBox(
			(margin, 59, 80, 16), "A–Z", sizeStyle="mini"
		)
		self.w.lowercaseLabel = vanilla.TextBox(
			(margin, 153, 80, 16), "a–z", sizeStyle="mini"
		)

		rows = (
			(ALPHABET[:13], 76),
			(ALPHABET[13:26], 112),
			(ALPHABET[26:39], 170),
			(ALPHABET[39:], 206),
		)
		for row_letters, top in rows:
			for column, character in enumerate(row_letters):
				position = (margin + column * (cell + gap), top, cell, cell)
				attribute_name = "letter_%s" % ord(character)
				button = vanilla.SquareButton(
					position,
					character,
					callback=self._letter_clicked,
					sizeStyle="small",
				)
				setattr(self.w, attribute_name, button)
				button = getattr(self.w, attribute_name)
				button._build_character = character
				native_button = button.getNSButton()
				native_button.setButtonType_(NSButtonTypePushOnPushOff)
				native_button.setFont_(NSFont.boldSystemFontOfSize_(14.0))
				self._hover_tips.attachToButton_(native_button)
				self._letter_buttons[character] = button

		self.w.allMasters = vanilla.CheckBox(
			(margin, 255, 145, 20),
			"Build in all masters",
			value=bool(self._pref("allMasters", True)),
			callback=self._scope_changed,
		)
		self.w.selectAll = vanilla.CheckBox(
			(176, 255, 90, 20),
			"Select all",
			value=False,
			callback=self._select_all_changed,
		)
		self.w.deselectAll = vanilla.Button(
			(276, 251, 104, 24),
			"Deselect all",
			callback=self._deselect_all_clicked,
			sizeStyle="small",
		)
		self.w.status = vanilla.TextBox(
			(margin, 311, -208, 20),
			"Select a letter to build.",
			sizeStyle="small",
		)
		self.w.clearButton = vanilla.Button(
			(-198, -38, 68, 24), "Scrap", callback=self.clear_clicked,
		)
		self.w.clearButton.getNSButton().setToolTip_(
			"Remove paths from selected glyphs in the current master only. Undo is available."
		)
		self.w.clearButton.getNSButton().setAccessibilityHelp_(
			"Remove paths in the current master. Components and other masters are preserved."
		)
		self.w.buildButton = vanilla.Button(
			(-106, -38, -margin, 24),
			"Build",
			callback=self.build_clicked,
		)
		self._layout_action_buttons()
		self.w.setDefaultButton(self.w.buildButton)
		self.w.bind("became key", self._window_became_key)
		self.w.bind("resigned key", self._hide_hover_tips)
		self.w.bind("close", self._panel_closed)
		self._refresh_grid()
		self.w.open()
		self._configure_native_window()
		self.w.makeKey()

	def _layout_action_buttons(self):
		"""Give both native action titles equal compact horizontal padding."""
		widths = []
		for button in (self.w.clearButton, self.w.buildButton):
			native = button.getNSButton()
			title = NSAttributedString.alloc().initWithString_attributes_(
				str(native.title()), {NSFontAttributeName: native.font()},
			)
			widths.append(float(title.size().width) + 2.0 * ACTION_BUTTON_CONTENT_PADDING)
		margin = 18.0
		scrap_width, build_width = widths
		self.w.buildButton.setPosSize((-margin - build_width, -38, build_width, 24))
		self.w.clearButton.setPosSize((
			-margin - build_width - ACTION_BUTTON_GAP - scrap_width,
			-38, scrap_width, 24,
		))

	def _configure_native_window(self):
		window = self.w.getNSWindow()
		if window is None:
			return
		window.setHidesOnDeactivate_(True)
		window.setSharingType_(NSWindowSharingReadOnly)
		window.setCollectionBehavior_(
			(window.collectionBehavior() & ~NSWindowCollectionBehaviorCanJoinAllSpaces)
			| NSWindowCollectionBehaviorFullScreenAuxiliary
		)

	@staticmethod
	def _dependency_description(character):
		if character in BASE_GLYPHS:
			return "Source glyph — draw manually"
		sources = BUILD_SOURCES.get(character)
		if character in BUILDERS and sources:
			return "Built from %s" % " + ".join(sources)
		return "No build recipe yet"

	def _show_dependencies(self, _sender):
		self._hide_hover_tips(None)
		if self._dependencies_window is not None:
			self._dependencies_window.makeKey()
			return
		window = vanilla.FloatingWindow(
			(460, 660), "Glyph dependencies",
			minSize=(460, 420), maxSize=(460, 850),
		)
		self._dependencies_window = window
		window.bind("close", self._dependencies_closed)
		window.introText = vanilla.TextBox(
			(18, 14, -18, 20),
			"Direct sources for each recipe. Source glyphs are drawn manually.",
			sizeStyle="small",
		)
		for name, left, title in (
			("uppercase", 18, "Uppercase"),
			("lowercase", 238, "Lowercase"),
		):
			label = vanilla.TextBox((left, 42, 204, 18), title)
			setattr(window, name, label)
			label.getNSTextField().setFont_(NSFont.boldSystemFontOfSize_(12.0))
		content = vanilla.Group((0, 0, 424, 26 * 22))
		for characters, left in ((ALPHABET[:26], 0), (ALPHABET[26:], 220)):
			for row, character in enumerate(characters):
				top = row * 22
				letter = vanilla.TextBox((left, top, 24, 20), character)
				setattr(content, "letter_%s" % ord(character), letter)
				letter.getNSTextField().setFont_(NSFont.boldSystemFontOfSize_(13.0))
				if character in BASE_GLYPHS:
					letter.getNSTextField().setTextColor_(SOURCE_TITLE_COLOR)
				setattr(
					content, "sources_%s" % ord(character),
					vanilla.TextBox(
						(left + 28, top + 1, 176, 20),
						self._dependency_description(character),
						selectable=True, sizeStyle="small",
					),
				)
		window._dependency_content = content
		window.dependencies = vanilla.ScrollView(
			(18, 64, -18, -18), content.getNSView(),
			hasHorizontalScroller=False, hasVerticalScroller=True,
			autohidesScrollers=True, drawsBackground=False,
		)
		window.dependencies.getNSScrollView().setBorderType_(NSNoBorder)
		window.open()
		window.getNSWindow().setHidesOnDeactivate_(True)
		window.getNSWindow().setSharingType_(NSWindowSharingReadOnly)
		window.makeKey()

	def _dependencies_closed(self, _sender):
		self._dependencies_window = None

	def _panel_closed(self, _sender):
		self._hide_hover_tips(None)
		if self._dependencies_window is not None:
			self._dependencies_window.getNSWindow().performClose_(None)

	@staticmethod
	def _pref_key(key):
		return "%s.%s" % (PREF_DOMAIN, key)

	def _pref(self, key, fallback):
		value = Glyphs.defaults[self._pref_key(key)]
		return fallback if value is None else value

	def _selected_masters(self):
		return _masters_for_generation(
			Glyphs.font, bool(self.w.allMasters.get())
		)

	@staticmethod
	def _unlock_message(missing):
		if len(missing) == 1:
			return "Draw %s to build" % missing[0]
		return "Draw %s to build" % " + ".join(missing)

	def _button_availability(self, character, masters):
		if character in BASE_GLYPHS:
			return False, "%s is a source glyph; draw it manually" % character
		if character not in BUILDERS:
			return False, "No build recipe for %s yet" % character
		missing = _missing_sources(Glyphs.font, character, masters)
		if missing:
			return False, self._unlock_message(missing)
		return (
			True,
			"Build %s from %s"
			% (character, " + ".join(BUILD_SOURCES[character])),
		)

	def _refresh_grid(self):
		if self._busy or Glyphs.font is None:
			return
		try:
			masters = self._selected_masters()
		except GenerationError:
			return
		available = set()
		built = set()
		for character in ALPHABET:
			enabled, tooltip = self._button_availability(character, masters)
			button = self._letter_buttons[character]
			# Source glyphs are informational rather than build targets. Keep
			# them interactive enough to retain their full-color treatment and
			# tooltip; the click handler still prevents selecting them.
			button.enable(enabled or character in BASE_GLYPHS)
			# Keep native disabled semantics. Our tracking areas still receive
			# hover events, without a second, delayed macOS tooltip appearing.
			button.getNSButton().setToolTip_(None)
			button.getNSButton().setAccessibilityHelp_(tooltip)
			try:
				glyph = Glyphs.font.glyphs[character]
			except (KeyError, IndexError):
				glyph = None
			if glyph is not None and all(
				glyph.layers[master.id] is not None
				and bool(glyph.layers[master.id].shapes)
				for master in masters
			):
				built.add(character)
			if enabled:
				available.add(character)
		self._available_characters = available
		self._built_characters = built
		if self.w.selectAll.get():
			self._selected_characters = set(available)
		else:
			self._selected_characters.intersection_update(available)
		self._sync_selection()

	def _sync_selection(self):
		for character, button in self._letter_buttons.items():
			native_button = button.getNSButton()
			is_source = character in BASE_GLYPHS
			available = character in self._available_characters
			selected = available and character in self._selected_characters
			built = character in self._built_characters
			unbuilt = not is_source and not built
			native_button.setState_(1 if selected else 0)
			native_button.setAlphaValue_(
				1.0 if available or is_source or built else LOCKED_BUTTON_ALPHA
			)
			native_button.setBezelColor_(
				SELECTED_BUTTON_COLOR
				if selected
				else None
			)
			title_color = (
				SELECTED_TITLE_COLOR
				if selected
				else SOURCE_TITLE_COLOR
				if is_source
				else BUILT_TITLE_COLOR
				if built
				else UNBUILT_TITLE_COLOR
				if unbuilt
				else NSColor.labelColor()
			)
			native_button.setAttributedTitle_(
				NSAttributedString.alloc().initWithString_attributes_(
					character,
					{
						NSFontAttributeName: NSFont.boldSystemFontOfSize_(14.0),
						NSForegroundColorAttributeName: title_color,
					},
				)
			)
		self.w.selectAll.set(
			bool(self._available_characters)
			and self._selected_characters == self._available_characters
		)
		self.w.buildButton.enable(
			bool(self._selected_characters) and not self._busy
		)
		self.w.clearButton.enable(self._can_clear_selection())
		self.w.deselectAll.enable(
			bool(self._selected_characters) and not self._busy
		)

	def _letter_clicked(self, sender):
		self._hide_hover_tips(None)
		character = sender._build_character
		self._refresh_grid()
		if character not in self._available_characters:
			self._sync_selection()
			return
		if character in self._selected_characters:
			self._selected_characters.remove(character)
		else:
			self._selected_characters.add(character)
		self._sync_selection()
		if not self._selected_characters:
			self.w.status.set("Select one or more letters to build.")
		elif len(self._selected_characters) == 1:
			self.w.status.set(
				"Selected %s." % next(iter(self._selected_characters))
			)
		else:
			self.w.status.set(
				"Selected %i letters." % len(self._selected_characters)
			)

	def _can_clear_selection(self):
		if self._busy or Glyphs.font is None:
			return False
		master = Glyphs.font.selectedFontMaster
		if master is None:
			return False
		for character in self._selected_characters:
			glyph = Glyphs.font.glyphs[character]
			layer = glyph.layers[master.id] if glyph is not None else None
			if layer is not None and len(layer.paths):
				return True
		return False

	def _select_all_changed(self, _sender):
		select_all = bool(self.w.selectAll.get())
		if not select_all:
			self._selected_characters.clear()
		self._refresh_grid()
		if select_all:
			self._selected_characters = set(self._available_characters)
			self.w.status.set(
				"Selected %i buildable letters."
				% len(self._selected_characters)
			)
		else:
			self._selected_characters.clear()
			self.w.status.set("Select a letter to build.")
		self._sync_selection()

	def _deselect_all_clicked(self, _sender):
		self._selected_characters.clear()
		self.w.selectAll.set(False)
		self._sync_selection()
		self.w.status.set("Select a letter to build.")

	def _scope_changed(self, _sender):
		Glyphs.defaults[self._pref_key("allMasters")] = bool(
			self.w.allMasters.get()
		)
		self._refresh_grid()

	def _window_became_key(self, _sender):
		self._refresh_grid()

	def _hide_hover_tips(self, _sender):
		self._hover_tips.hideTip_(None)

	def _set_busy(self, busy, status):
		self._busy = bool(busy)
		self._hide_hover_tips(None)
		self.w.allMasters.enable(not busy)
		self.w.selectAll.enable(not busy)
		self.w.deselectAll.enable(not busy and bool(self._selected_characters))
		for character, button in self._letter_buttons.items():
			button.enable(
				not busy
				and (
					character in self._available_characters
					or character in BASE_GLYPHS
				)
			)
		self.w.buildButton.enable(not busy and bool(self._selected_characters))
		self.w.clearButton.enable(self._can_clear_selection())
		self.w.status.set(status)
		if not busy:
			self._refresh_grid()

	def clear_clicked(self, _sender):
		try:
			if self._busy:
				return
			font = Glyphs.font
			master = _masters_for_generation(font, False)[0]
			characters = tuple(character for character in ALPHABET
				if character in self._selected_characters)
			if not characters:
				return
			self._set_busy(True, "Scrapping paths…")
			cleared, removed = _clear_glyph_paths(font, characters, master)
			self._set_busy(False,
				"Scrapped %s. Undo available." % (
					cleared[0] if len(cleared) == 1 else "%i glyphs" % len(cleared)
				)
				if removed else "No paths in the current master.")
		except GenerationError as error:
			self._set_busy(False, str(error))
		except Exception:
			self._set_busy(False, "Scrap failed; see Macro window.")
			Glyphs.showMacroWindow()
			print("%s scrap failed:\n%s" % (TITLE, traceback.format_exc()))

	def build_clicked(self, _sender):
		try:
			if self._busy:
				return
			self._refresh_grid()
			characters = tuple(
				character
				for character in ALPHABET
				if character in self._selected_characters
			)
			if not characters:
				raise GenerationError("Select at least one buildable letter.")
			all_masters = bool(self.w.allMasters.get())
			if any(character in ("i", "j") for character in characters):
				self._set_busy(True, "Choose dots…")
			dot_shape = _choose_dot_shape(characters)
			if dot_shape is None:
				self._set_busy(False, "Build cancelled; no outlines changed.")
				return
			self._set_busy(
				True,
				"Building %i letter%s…"
				% (len(characters), "" if len(characters) == 1 else "s"),
			)
			master_names = generate_all(
				Glyphs.font, all_masters, characters=characters, dot_shape=dot_shape
			)
			self._set_busy(
				False,
				"Built %s in %s."
				% ("".join(characters), ", ".join(master_names)),
			)
			_show_in_current_tab(Glyphs.font, characters)
		except GenerationError as error:
			self._set_busy(False, str(error))
			Message(title=TITLE, message=str(error), OKButton=None)
		except Exception:
			self._set_busy(False, "Unexpected error; see Macro window.")
			Glyphs.showMacroWindow()
			print("%s failed:\n%s" % (TITLE, traceback.format_exc()))
			Message(
				title=TITLE,
				message="An unexpected error occurred. Details are in the Macro window.",
				OKButton=None,
			)


def main():
	if float(Glyphs.versionNumber) < 3.0:
		Message(title=TITLE, message="Glyphs 3 or later is required.", OKButton=None)
		return
	if vanilla is None:
		Message(
			title=TITLE,
			message=(
				"Install the Vanilla module in Window → Plugin Manager → Modules, "
				"restart Glyphs, and run the script again."
			),
			OKButton=None,
		)
		return
	try:
		BuildRoughDraftWindowController()
	except GenerationError as error:
		Message(title=TITLE, message=str(error), OKButton=None)
	except Exception:
		Glyphs.showMacroWindow()
		print("%s failed:\n%s" % (TITLE, traceback.format_exc()))
		Message(
			title=TITLE,
			message="Could not open the panel. Details are in the Macro window.",
			OKButton=None,
		)


if __name__ == "__main__":
	main()
