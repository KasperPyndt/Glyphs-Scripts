#MenuTitle: Unround Corner
# -*- coding: utf-8 -*-
"""
Turns one selected rounded cubic corner back into a sharp corner.

Select exactly the two on-curve nodes at the ends of the rounded segment,
then run Script > Unround Corner. The script extends the two adjoining
tangents to their intersection and replaces the rounded segment with one
sharp, selected node.
"""

from math import isfinite
import traceback

from Foundation import NSPoint
from GlyphsApp import CURVE, OFFCURVE, Glyphs, Message


TITLE = "Unround Corner"
EPSILON = 1.0e-10


def show_error(message):
	Message(message, title=TITLE)


def point_tuple(point):
	return float(point.x), float(point.y)


def subtract(point_a, point_b):
	return point_a[0] - point_b[0], point_a[1] - point_b[1]


def length_squared(vector):
	return vector[0] * vector[0] + vector[1] * vector[1]


def cross(vector_a, vector_b):
	return vector_a[0] * vector_b[1] - vector_a[1] * vector_b[0]


def line_intersection(point_a, direction_a, point_b, direction_b):
	"""Return the intersection of two infinite lines, or None if parallel."""
	denominator = cross(direction_a, direction_b)
	scale = (length_squared(direction_a) * length_squared(direction_b)) ** 0.5
	if scale <= EPSILON or abs(denominator) <= EPSILON * scale:
		return None

	offset = subtract(point_b, point_a)
	distance = cross(offset, direction_b) / denominator
	intersection = (
		point_a[0] + distance * direction_a[0],
		point_a[1] + distance * direction_a[1],
	)
	if not all(isfinite(value) for value in intersection):
		return None
	return intersection


def node_before(nodes, index, closed):
	if index > 0:
		return nodes[index - 1]
	if closed and nodes:
		return nodes[-1]
	return None


def node_after(nodes, index, closed):
	if index + 1 < len(nodes):
		return nodes[index + 1]
	if closed and nodes:
		return nodes[0]
	return None


def forward_nodes_between(nodes, start_index, end_index, closed):
	"""Return nodes after start and before end in path direction."""
	if start_index < end_index:
		return nodes[start_index + 1:end_index]
	if closed:
		return nodes[start_index + 1:] + nodes[:end_index]
	return None


def rounded_segment(path, first_node, second_node):
	"""Find the directed cubic segment joining the two selected nodes."""
	nodes = list(path.nodes)
	first_index = nodes.index(first_node)
	second_index = nodes.index(second_node)
	candidates = []

	for start_index, end_index in (
		(first_index, second_index),
		(second_index, first_index),
	):
		between = forward_nodes_between(nodes, start_index, end_index, path.closed)
		if between is None:
			continue
		if (
			len(between) == 2
			and all(node.type == OFFCURVE for node in between)
			and nodes[end_index].type == CURVE
		):
			candidates.append((start_index, end_index, between))

	if len(candidates) != 1:
		return None

	start_index, end_index, handles = candidates[0]
	return {
		"nodes": nodes,
		"start": nodes[start_index],
		"start_index": start_index,
		"handle_1": handles[0],
		"handle_2": handles[1],
		"end": nodes[end_index],
		"end_index": end_index,
	}


def usable_direction(preferred, fallback):
	if preferred is not None and length_squared(preferred) > EPSILON:
		return preferred
	if fallback is not None and length_squared(fallback) > EPSILON:
		return fallback
	return None


def corner_intersection(path, segment):
	"""Intersect the tangents of the segments adjoining the rounded curve."""
	nodes = segment["nodes"]
	start = point_tuple(segment["start"].position)
	end = point_tuple(segment["end"].position)
	handle_1 = point_tuple(segment["handle_1"].position)
	handle_2 = point_tuple(segment["handle_2"].position)

	previous_node = node_before(nodes, segment["start_index"], path.closed)
	next_node = node_after(nodes, segment["end_index"], path.closed)

	# Prefer the tangents of the outline pieces that will remain. If the
	# rounded curve is at an open-path end, fall back to its own handles.
	incoming = None
	if previous_node is not None:
		incoming = subtract(start, point_tuple(previous_node.position))
	incoming = usable_direction(incoming, subtract(handle_1, start))

	outgoing = None
	if next_node is not None:
		outgoing = subtract(point_tuple(next_node.position), end)
	outgoing = usable_direction(outgoing, subtract(end, handle_2))

	if incoming is None or outgoing is None:
		return None
	return line_intersection(start, incoming, end, outgoing)


def selected_oncurve_nodes(layer):
	selected = []
	for path in layer.paths:
		for node in path.nodes:
			if node.type != OFFCURVE and node.selected:
				selected.append((path, node))
	return selected


def unround_corner():
	font = Glyphs.font
	if font is None:
		show_error("Open a font and select a rounded corner first.")
		return

	if not font.selectedLayers:
		show_error("Open a glyph in Edit view and select a rounded corner first.")
		return

	layer = font.selectedLayers[0]
	selected = selected_oncurve_nodes(layer)
	if len(selected) != 2:
		show_error(
			"Select exactly the two on-curve nodes at the ends of one "
			"rounded cubic corner. Handles may stay unselected."
		)
		return

	path_a, node_a = selected[0]
	path_b, node_b = selected[1]
	if path_a is not path_b:
		show_error("The two selected nodes must be on the same path.")
		return

	path = path_a
	segment = rounded_segment(path, node_a, node_b)
	if segment is None:
		show_error(
			"The selected nodes must be the endpoints of one cubic segment "
			"with exactly two handles between them."
		)
		return

	oncurve_count = sum(node.type != OFFCURVE for node in path.nodes)
	if oncurve_count < 3:
		show_error("This path has too few on-curve nodes to merge this segment safely.")
		return

	intersection = corner_intersection(path, segment)
	if intersection is None:
		show_error(
			"The adjoining tangents are parallel or too short, so they do not "
			"define a sharp corner."
		)
		return

	glyph = layer.parent
	glyph.beginUndo()
	try:
		kept_node = segment["start"]
		kept_node.position = NSPoint(intersection[0], intersection[1])
		kept_node.smooth = False

		indices_to_delete = [
			segment["handle_1"].index,
			segment["handle_2"].index,
			segment["end"].index,
		]
		for index in sorted(indices_to_delete, reverse=True):
			del path.nodes[index]

		layer.clearSelection()
		kept_node.selected = True
	finally:
		glyph.endUndo()

	Glyphs.redraw()


try:
	unround_corner()
except Exception:
	Glyphs.showMacroWindow()
	print(traceback.format_exc())
	show_error("The corner could not be changed. Details are in the Macro window.")
