#MenuTitle: Symmetrify Selected Nodes in All Masters KP
# -*- coding: utf-8 -*-

# Original script by Tim Ahrens / Just Another Foundry
# https://github.com/justanotherfoundry/freemix-glyphsapp
#
# Glyphs 4 adaptation based on the current upstream script (2026), with:
# - explicit GlyphsApp imports
# - current font.selectedLayers API
# - Glyphs 4.1 per-layer horizontal/vertical grid-aware rounding
# - safer selection/empty-layer handling
# - batched layer changes and guaranteed undo/interface cleanup on errors
# - Glyphs-safe panel dismissal when an action is chosen
# - selected-node mapping across every master of the active glyph
# - graceful Vanilla dependency handling
#
# Original project is GPL-2.0 licensed. Keep the original attribution/license
# when redistributing modified versions.

__doc__ = """
Symmetrifies corresponding selected nodes in every master of the active glyph.

S - creates point reflection (180-degree rotational symmetry)
T - creates horizontal reflection symmetry
C - creates vertical reflection symmetry
H - creates 2-axis symmetry (all of the above)
* - creates 5-fold rotational symmetry (useful for asterisks)

Select at least two nodes on the same path in the active layer. The selected
path/node indices are applied to the corresponding nodes in every master.
The buttons are available only when all masters support the operation.
"""

import math
import traceback

from AppKit import NSPoint
from GlyphsApp import Glyphs, Message, OFFCURVE

try:
    from vanilla import Window, SquareButton
except ImportError:
    Message(
        "Symmetrify requires the Vanilla module. Install it from the Modules "
        "section of Glyphs’ Plugin Manager, restart Glyphs, and run the script again.",
        "Missing Vanilla module",
    )
    raise SystemExit


PERFECT_SYMMETRY = False
# True: guarantee exact symmetry when a center node makes half-unit placement
# ambiguous. False: prioritize retaining the original bounding box, matching
# the original script’s default behavior.

INSTANT_SYMMETRIFICATION = None
# Set to "S", "T", "C", "H" or "*" to run immediately without the dialog.

SMALL_NEG = -1.0 / 4096.0
SMALL_POS = 1.0 / 4096.0
VALID_ACTIONS = {"S", "T", "C", "H", "*"}


def point_add(p1, p2):
    """Return p1 + p2 without relying on legacy injected Glyphs globals."""
    return NSPoint(p1.x + p2.x, p1.y + p2.y)


def point_subtract(p1, p2):
    """Return p1 - p2 without relying on legacy injected Glyphs globals."""
    return NSPoint(p1.x - p2.x, p1.y - p2.y)


def swapped_if(values, do_swap):
    return (values[1], values[0]) if do_swap else values


class SymmetrifyDialog:
    def __init__(self, font, layer):
        self.font = font
        self.active_layer = layer
        self.glyph = layer.parent
        self.layer = layer
        self.w = None
        self.targets = []
        self.contours = []
        self.cx = 0.0
        self.cy = 0.0
        self.all_x_oncurve = []
        self.all_y_oncurve = []
        self.grid_step_x = 0.0
        self.grid_step_y = 0.0

        if self.glyph is None:
            self.layer = None
            Message(
                "The active layer is not attached to a glyph.",
                "Nothing to symmetrify",
            )
            return

        selection_map = self.selected_node_map(layer)
        if not selection_map:
            self.layer = None
            Message(
                "Select at least two nodes on the same path in the active layer.",
                "No usable node selection",
            )
            return

        try:
            self.targets = self.build_master_targets(selection_map)
        except ValueError as error:
            self.layer = None
            Message(str(error), "Incompatible masters")
            return

        self.active_target = next(
            (target for target in self.targets if target[0] == self.active_layer),
            self.targets[0] if self.targets else None,
        )
        if self.active_target is None or not self.activate_target(self.active_target):
            self.layer = None
            Message(
                "The selected nodes must include at least one on-curve node.",
                "Nothing to symmetrify",
            )
            return

        button_titles = []
        if self.all_targets_support("S"):
            button_titles.append("S")
        if self.all_targets_support("*"):
            button_titles.append("*")
        if self.all_targets_support("T"):
            button_titles.extend(["T", "C", "H"])

        if not button_titles:
            self.layer = None
            Message(
                "The selected node structure does not support a common "
                "Symmetrify operation across all masters.",
                "Incompatible node structure",
            )
            return

        margin = 10
        size = 40
        width = len(button_titles) * (margin + size) + margin
        height = 2 * margin + size
        self.w = Window((width, height), "Symmetrify All Masters")

        left = margin
        top = margin
        for title in button_titles:
            button = SquareButton(
                (left, top, size, size),
                title,
                callback=self.button_callback,
            )
            setattr(self.w, "button_" + ("star" if title == "*" else title), button)
            left += size + margin

    @staticmethod
    def selected_node_map(layer):
        """Return selected node indices grouped by path index."""
        selection_map = []
        for path_index, path in enumerate(layer.paths):
            node_indices = [
                node_index
                for node_index, node in enumerate(path.nodes)
                if node.selected
            ]
            if len(node_indices) >= 2:
                selection_map.append((path_index, node_indices))
        return selection_map

    def build_master_targets(self, selection_map):
        """Map the active-layer selection to corresponding nodes in all masters."""
        source_paths = list(self.active_layer.paths)
        source_types = [
            [source_paths[path_index].nodes[index].type for index in node_indices]
            for path_index, node_indices in selection_map
        ]
        targets = []

        for master in self.font.masters:
            layer = self.glyph.layers[master.id]
            paths = list(layer.paths)
            contours = []

            for selection_index, (path_index, node_indices) in enumerate(selection_map):
                if path_index >= len(paths):
                    raise ValueError(
                        "%s does not contain path %d. Make the master outlines "
                        "compatible first." % (master.name, path_index + 1)
                    )

                nodes = list(paths[path_index].nodes)
                if any(node_index >= len(nodes) for node_index in node_indices):
                    raise ValueError(
                        "%s does not contain all corresponding nodes on path %d. "
                        "Make the master outlines compatible first."
                        % (master.name, path_index + 1)
                    )

                contour = [nodes[node_index] for node_index in node_indices]
                target_types = [node.type for node in contour]
                expected_types = source_types[selection_index]
                if [t == OFFCURVE for t in target_types] != [
                    t == OFFCURVE for t in expected_types
                ]:
                    raise ValueError(
                        "%s has different node types at the selected positions "
                        "on path %d. Make the master outlines compatible first."
                        % (master.name, path_index + 1)
                    )
                contours.append(contour)

            targets.append((layer, contours))

        return targets

    def activate_target(self, target):
        """Load one master target into the original geometry implementation."""
        self.layer, self.contours = target
        self.grid_step_x, self.grid_step_y = self._effective_grid_steps()
        return self.init_center()

    def all_targets_support(self, action):
        """Return whether every master supports an action for the mapped nodes."""
        try:
            for target in self.targets:
                if not self.activate_target(target):
                    return False
                if action == "S" and not self.can_rotate():
                    return False
                if action == "*" and not self.can_rotate5():
                    return False
                if action == "T" and not all(
                    self.get_flip_partner(contour, is_horizontal=False) is not None
                    for contour in self.contours
                ):
                    return False
            return True
        finally:
            self.activate_target(self.active_target)

    def _effective_grid_steps(self):
        """Return the layer's effective x/y grid intervals.

        Glyphs 4.1 grids can differ by master and by axis. Fall back to the
        legacy font-wide square grid for older Glyphs 4 builds or wrappers.
        """
        try:
            step_x = max(0.0, float(self.layer.gridLengthHorizontal()))
            step_y = max(0.0, float(self.layer.gridLengthVertical()))
            return step_x, step_y
        except Exception:
            pass

        try:
            master = self.layer.master
            step_x = float(master.gridMainHorizontal) / float(
                master.gridSubDivisionHorizontal
            )
            step_y = float(master.gridMainVertical) / float(
                master.gridSubDivisionVertical
            )
            return max(0.0, step_x), max(0.0, step_y)
        except Exception:
            pass

        try:
            step = max(0.0, float(self.font.gridLength))
            return step, step
        except Exception:
            return 0.0, 0.0

    def grid_step(self, is_x):
        return self.grid_step_x if is_x else self.grid_step_y

    def apply_grid(self, value, is_x):
        step = self.grid_step(is_x)
        if step > 0:
            return round(value / step) * step
        return value

    def apply_half_grid(self, value, is_x):
        return 0.5 * self.apply_grid(value * 2.0, is_x)

    def init_center(self):
        self.all_x_oncurve = [
            node.position.x
            for contour in self.contours
            for node in contour
            if node.type != OFFCURVE
        ]
        self.all_y_oncurve = [
            node.position.y
            for contour in self.contours
            for node in contour
            if node.type != OFFCURVE
        ]

        if not self.all_x_oncurve or not self.all_y_oncurve:
            return False

        self.cx = 0.5 * (max(self.all_x_oncurve) + min(self.all_x_oncurve))
        self.cy = 0.5 * (max(self.all_y_oncurve) + min(self.all_y_oncurve))
        return True

    def refine_center(self, current_is_horizontal):
        bbox_based = self.cx if current_is_horizontal else self.cy
        if bbox_based == self.apply_grid(bbox_based, current_is_horizontal):
            return bbox_based

        if PERFECT_SYMMETRY:
            for contour in self.contours:
                partner = self.get_flip_partner(contour, current_is_horizontal)
                if partner is not None and partner % 2 == 0:
                    return self.apply_grid(bbox_based, current_is_horizontal)

        prefer_center_on_grid = 0
        for contour in self.contours:
            partner_index = self.get_flip_partner(contour, current_is_horizontal)
            if partner_index is None:
                continue

            for point_index in range(len(contour)):
                if point_index == partner_index:
                    prefer_center_on_grid += 11
                elif point_index < partner_index:
                    n1 = contour[point_index]
                    n2 = contour[partner_index]
                    v1 = n1.x if current_is_horizontal else n1.y
                    v2 = n2.x if current_is_horizontal else n2.y
                    diff = v1 - v2
                    if diff == self.apply_grid(
                        diff / 2.0, current_is_horizontal
                    ) * 2.0:
                        prefer_center_on_grid += 5
                    else:
                        prefer_center_on_grid -= 11

                partner_index = (
                    len(contour) - 1 if partner_index == 0 else partner_index - 1
                )

        if prefer_center_on_grid <= 0:
            return self.apply_half_grid(bbox_based, current_is_horizontal)

        all_oncurve = (
            self.all_x_oncurve if current_is_horizontal else self.all_y_oncurve
        )
        center_of_gravity = sum(all_oncurve) / len(all_oncurve)
        return self.apply_grid(
            0.9 * center_of_gravity + 0.1 * bbox_based,
            current_is_horizontal,
        )

    def run(self):
        if self.w is not None:
            self.w.open()

    def get_flip_partner(self, contour, is_horizontal):
        """Return the best partner index for contour[0], or None if incompatible."""
        min_sum = float("inf")
        best_partner_index_for_0 = None

        for tested_partner_index_for_0 in range(len(contour)):
            current_sum = 0.0
            point_index = tested_partner_index_for_0

            for other_point_index in range(len(contour)):
                point = contour[point_index]
                other_point = contour[other_point_index]

                if (point.type == OFFCURVE) != (other_point.type == OFFCURVE):
                    break

                if is_horizontal:
                    current_sum += abs(other_point.x + point.x - 2.0 * self.cx)
                    current_sum += abs(other_point.y - point.y) * 2.0
                else:
                    current_sum += abs(other_point.y + point.y - 2.0 * self.cy)
                    current_sum += abs(other_point.x - point.x) * 2.0

                point_index = len(contour) - 1 if point_index == 0 else point_index - 1
            else:
                if current_sum < min_sum:
                    min_sum = current_sum
                    best_partner_index_for_0 = tested_partner_index_for_0

        return best_partner_index_for_0

    def flip(self, flip_horizontal, flip_vertical):
        self.cx = self.refine_center(True)
        self.cy = self.refine_center(False)

        flips = [True] * int(bool(flip_horizontal)) + [False] * int(bool(flip_vertical))
        for contour in self.contours:
            xy = [(point.x, point.y) for point in contour]

            for current_is_horizontal in flips:
                almost_one = (
                    32767.0 / 32768.0
                    if self.grid_step(current_is_horizontal) > 0
                    else 1.0
                )
                partner_index = self.get_flip_partner(contour, current_is_horizontal)
                if partner_index is None:
                    raise ValueError("Could not find a structurally compatible reflection partner.")

                for point_index in range(len(contour)):
                    if point_index <= partner_index:
                        x, y = swapped_if(xy[point_index], current_is_horizontal)
                        partner_x, partner_y = swapped_if(
                            xy[partner_index], current_is_horizontal
                        )
                        c_x, c_y = swapped_if(
                            (self.cx, self.cy), current_is_horizontal
                        )

                        # From here on, treat the operation as reflection across
                        # a horizontal axis; swapped_if maps it back if necessary.
                        correction_y = c_y - 0.5 * (partner_y + y)

                        if point_index == partner_index:
                            correction_y *= almost_one
                            xy[point_index] = swapped_if(
                                (x, y + correction_y), current_is_horizontal
                            )
                        else:
                            correction_x = 0.5 * (partner_x - x)
                            x += correction_x
                            y += correction_y
                            partner_y = 2.0 * c_y - y
                            xy[point_index] = swapped_if(
                                (x, y), current_is_horizontal
                            )
                            xy[partner_index] = swapped_if(
                                (x, partner_y), current_is_horizontal
                            )

                    partner_index = (
                        len(contour) - 1 if partner_index == 0 else partner_index - 1
                    )

            for point_index, point in enumerate(contour):
                new_x, new_y = xy[point_index]
                new_x += SMALL_POS if new_x > self.cx else SMALL_NEG
                new_y += SMALL_POS if new_y > self.cy else SMALL_NEG
                point.x = self.apply_grid(new_x, is_x=True)
                point.y = self.apply_grid(new_y, is_x=False)

    def can_rotate(self):
        for contour in self.contours:
            if len(contour) % 2 != 0:
                return False

            other_point_index = len(contour) // 2
            for point_index in range(other_point_index):
                point = contour[point_index]
                other_point = contour[other_point_index]
                if (point.type == OFFCURVE) != (other_point.type == OFFCURVE):
                    return False
                other_point_index = (other_point_index + 1) % len(contour)

        return bool(self.contours)

    def rotate(self):
        for contour in self.contours:
            other_point_index = len(contour) // 2

            for point_index in range(other_point_index):
                point = contour[point_index]
                other_point = contour[other_point_index]

                rx = 0.5 * (point.x - other_point.x)
                ry = 0.5 * (point.y - other_point.y)
                rx += SMALL_POS if rx > 0 else SMALL_NEG
                ry += SMALL_POS if ry > 0 else SMALL_NEG

                point.x = self.apply_grid(self.cx + rx, is_x=True)
                point.y = self.apply_grid(self.cy + ry, is_x=False)
                other_point.x = self.apply_grid(self.cx - rx, is_x=True)
                other_point.y = self.apply_grid(self.cy - ry, is_x=False)

                other_point_index = (other_point_index + 1) % len(contour)

    @staticmethod
    def blend_points(p0, p1, p2, p3, p4):
        return NSPoint(
            0.2 * (p0.x + p1.x + p2.x + p3.x + p4.x),
            0.2 * (p0.y + p1.y + p2.y + p3.y + p4.y),
        )

    @staticmethod
    def rotated_vector(point, angle, center=None):
        if center is None:
            center = NSPoint(0.0, 0.0)

        vx = point.x - center.x
        vy = point.y - center.y
        return NSPoint(
            vx * math.cos(angle) - vy * math.sin(angle),
            vx * math.sin(angle) + vy * math.cos(angle),
        )

    def can_rotate5(self):
        for contour in self.contours:
            if len(contour) % 5 != 0:
                return False

            i1 = len(contour) // 5
            i2 = 2 * i1
            i3 = 3 * i1
            i4 = 4 * i1

            for i0 in range(i1):
                type0_is_offcurve = contour[i0].type == OFFCURVE
                if type0_is_offcurve != (contour[i1].type == OFFCURVE):
                    return False
                if type0_is_offcurve != (contour[i2].type == OFFCURVE):
                    return False
                if type0_is_offcurve != (contour[i3].type == OFFCURVE):
                    return False
                if type0_is_offcurve != (contour[i4].type == OFFCURVE):
                    return False

                i1 = (i1 + 1) % len(contour)
                i2 = (i2 + 1) % len(contour)
                i3 = (i3 + 1) % len(contour)
                i4 = (i4 + 1) % len(contour)

        return bool(self.contours)

    def rotate5(self):
        fifth_circle = -math.pi * 2.0 / 5.0
        all_points = [point for contour in self.contours for point in contour]
        if not all_points:
            return

        cg = NSPoint(
            sum(point.x for point in all_points) / len(all_points),
            sum(point.y for point in all_points) / len(all_points),
        )

        for contour in self.contours:
            i1 = len(contour) // 5
            i2 = 2 * i1
            i3 = 3 * i1
            i4 = 4 * i1

            for i0 in range(i1):
                vector = self.blend_points(
                    point_subtract(contour[i0].position, cg),
                    self.rotated_vector(contour[i1].position, fifth_circle, cg),
                    self.rotated_vector(contour[i2].position, fifth_circle * 2.0, cg),
                    self.rotated_vector(contour[i3].position, fifth_circle * 3.0, cg),
                    self.rotated_vector(contour[i4].position, fifth_circle * 4.0, cg),
                )

                contour[i0].position = point_add(cg, vector)
                contour[i1].position = point_add(
                    cg, self.rotated_vector(vector, -fifth_circle)
                )
                contour[i2].position = point_add(
                    cg, self.rotated_vector(vector, -fifth_circle * 2.0)
                )
                contour[i3].position = point_add(
                    cg, self.rotated_vector(vector, -fifth_circle * 3.0)
                )
                contour[i4].position = point_add(
                    cg, self.rotated_vector(vector, -fifth_circle * 4.0)
                )

                i1 = (i1 + 1) % len(contour)
                i2 = (i2 + 1) % len(contour)
                i3 = (i3 + 1) % len(contour)
                i4 = (i4 + 1) % len(contour)

    def apply_action(self, action):
        """Apply one validated action to the currently active master target."""
        if action == "S":
            self.rotate()
        elif action == "T":
            self.flip(flip_horizontal=True, flip_vertical=False)
        elif action == "C":
            self.flip(flip_horizontal=False, flip_vertical=True)
        elif action == "H":
            self.flip(flip_horizontal=True, flip_vertical=True)
        elif action == "*":
            # Preserve Tim Ahrens' current five-fold construction sequence.
            for _ in range(4):
                self.rotate5()
                self.flip(flip_horizontal=True, flip_vertical=False)

    def perform_symmetrification(self, action):
        if action not in VALID_ACTIONS:
            raise ValueError("Unknown Symmetrify action: %r" % action)

        interface_disabled = False
        undo_started = False
        try:
            self.font.disableUpdateInterface()
            interface_disabled = True
            self.glyph.beginUndo()
            undo_started = True

            for target in self.targets:
                if not self.activate_target(target):
                    raise RuntimeError(
                        "A master no longer contains usable corresponding nodes."
                    )

                changes_started = False
                try:
                    self.layer.beginChanges()
                    changes_started = True
                    self.apply_action(action)
                    self.layer.syncMetrics()
                finally:
                    if changes_started:
                        self.layer.endChanges()

        finally:
            try:
                if undo_started:
                    self.glyph.endUndo()
            finally:
                try:
                    if interface_disabled:
                        self.font.enableUpdateInterface()
                finally:
                    self.activate_target(self.active_target)

        try:
            Glyphs.redraw()
        except Exception:
            pass

    def button_callback(self, sender):
        action = str(sender.getTitle())
        try:
            self.perform_symmetrification(action)
        except Exception as error:
            print("Symmetrify error:\n%s" % traceback.format_exc())
            try:
                Glyphs.showMacroWindow()
            except Exception:
                pass
            Message(
                "%s\n\nThe full traceback has been printed to the Macro window."
                % error,
                "Symmetrify error",
            )
        finally:
            self.dismiss_panel(sender)

    def dismiss_panel(self, sender=None):
        """Dismiss the one-shot panel without Vanilla's broken close bridge.

        In Glyphs 4.1, Vanilla's Window.close() can incorrectly bridge to an
        Objective-C selector that expects one argument. Using orderOut_ is the
        established Glyphs workaround and, crucially, cannot prevent the
        selected symmetry action from running.
        """
        window = self.w
        self.w = None
        if window is None:
            return

        try:
            window.getNSWindow().orderOut_(sender)
        except Exception:
            # Never let a UI-dismissal problem turn a completed geometry action
            # into an apparent failure. Keep a traceback available for diagnosis.
            print("Symmetrify panel dismissal error:\n%s" % traceback.format_exc())


def main():
    font = Glyphs.font
    if font is None:
        Message("Open a font first.", "Symmetrify All Masters")
        return

    try:
        selected_layers = list(font.selectedLayers)
    except Exception:
        selected_layers = []

    if not selected_layers:
        Message(
            "Open a glyph in Edit view, select nodes, and run the script again.",
            "No active layer",
        )
        return

    dialog = SymmetrifyDialog(font, selected_layers[0])
    if dialog.layer is None:
        return

    # Keep a global reference while the Vanilla window is alive. Glyphs runs
    # scripts in a shared Python context, so this is also intentionally replaced
    # on the next run rather than accumulating window objects.
    global _symmetrify_all_masters_dialog
    _symmetrify_all_masters_dialog = dialog

    if INSTANT_SYMMETRIFICATION:
        action = str(INSTANT_SYMMETRIFICATION).upper()
        try:
            dialog.perform_symmetrification(action)
        except Exception as error:
            print("Symmetrify error:\n%s" % traceback.format_exc())
            try:
                Glyphs.showMacroWindow()
            except Exception:
                pass
            Message(
                "%s\n\nThe full traceback has been printed to the Macro window."
                % error,
                "Symmetrify error",
            )
    else:
        dialog.run()


main()
