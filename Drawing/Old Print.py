# MenuTitle: Old Print
# -*- coding: utf-8 -*-
# Compatibility: Glyphs 3 and 4, Python 3.

"""
Old Print — Clean v1.14
Glyphs 3 and Glyphs 4

True-preview workflow:
- Slider and effect-checkbox changes are temporary previews when Preview is on.
- Preview can be toggled off without losing the current settings.
- Closing the panel restores every previewed glyph/layer.
- Preset "Apply" loads the selected preset and previews it.
- Confirm commits the exact visible preview geometry without re-running filters.
- Apply re-runs the effect from the clean source inside an undo group, then
  dismisses the panel.

Preview sources are kept only in memory. The tool does not write a safety
copy into the Glyphs background, so closing the panel leaves both foreground
and background unchanged.
"""

from GlyphsApp import Glyphs, GSPath, GSNode, GSControlLayer, CURVE, OFFCURVE
from Foundation import NSClassFromString, NSPoint
import vanilla
import traceback
import time
import math
import random
import json


# ===========================================================================
# Filter access
# ===========================================================================

def _filter_by_class_name(*class_names):
    """Return a loaded Glyphs filter object by class name."""
    wanted = set(class_names)

    try:
        filters = Glyphs.filters
    except Exception:
        filters = []

    for filter_object in filters:
        try:
            if filter_object.__class__.__name__ in wanted:
                return filter_object
        except Exception:
            pass

    return None


def _ensure_filters_loaded():
    """Nudge Glyphs into loading its bundled filter instances."""
    try:
        _ = Glyphs.delegate().filterInstances()
    except Exception:
        try:
            _ = Glyphs.filters
        except Exception:
            pass


# ===========================================================================
# Round Corner
# ===========================================================================

def _apply_round_corner_once(layer, radius):
    """
    Apply one Round Corner pass.

    Positive radius affects outward corners.
    Negative radius affects inward/concave corners.
    """
    if abs(float(radius)) < 0.001:
        return True

    _ensure_filters_loaded()

    round_filter = _filter_by_class_name(
        "GlyphsFilterRoundCorner",
        "RoundCorner",
    )

    errors = []

    # Preferred: Glyphs' public filter API.
    if round_filter is not None and hasattr(round_filter, "filter"):
        for arguments in (
            {0: float(radius), 1: 1},
            {0: float(radius), 1: True},
            {"radius": float(radius), "visualCorrection": True},
        ):
            try:
                round_filter.filter(layer, False, arguments)
                return True
            except Exception as error:
                errors.append("filter(%r): %r" % (arguments, error))

    # Compatibility path for older/bundled filter implementations.
    if round_filter is not None and hasattr(
        round_filter,
        "processLayer_withArguments_",
    ):
        for arguments in (
            ["GlyphsFilterRoundCorner", str(float(radius)), "1"],
            ["", str(float(radius)), "1"],
            [str(float(radius)), "1"],
        ):
            try:
                round_filter.processLayer_withArguments_(layer, arguments)
                return True
            except Exception as error:
                errors.append("processLayer(%r): %r" % (arguments, error))

    print(
        "Old Print warning: Round Corner pass %.1f was skipped.\n%s"
        % (
            radius,
            "\n".join(errors) if errors else "No Round Corner filter found.",
        )
    )
    return False


def apply_corner_roundness(layer, radius):
    """
    Apply the same magnitude to outer and inner corners.

    Two passes are intentional:
        +radius -> outward corners
        -radius -> inward corners
    """
    radius = abs(float(radius))
    if radius < 0.001:
        return

    _apply_round_corner_once(layer, radius)
    _apply_round_corner_once(layer, -radius)


# ===========================================================================
# Roughen
# ===========================================================================

def apply_roughen(layer, segment_length, offset_x, offset_y, angle=0.0):
    """
    Apply Glyphs' native Roughen filter.

    segment_length:
        Larger = fewer inserted points / broader texture.
        Smaller = more inserted points / finer texture.

    offset_x / offset_y:
        Distance/randomness of the inserted points.
    """
    segment_length = max(1.0, float(segment_length))
    offset_x = float(offset_x)
    offset_y = float(offset_y)
    angle = float(angle)

    _ensure_filters_loaded()

    rough_filter = _filter_by_class_name(
        "GlyphsFilterRoughenizer",
        "Roughenizer",
    )

    errors = []

    # Preferred: documented public filter interface.
    if rough_filter is not None and hasattr(rough_filter, "filter"):
        for arguments in (
            {
                0: segment_length,
                1: offset_x,
                2: offset_y,
                3: angle,
            },
            {
                "length": segment_length,
                "offsetX": offset_x,
                "offsetY": offset_y,
                "angle": angle,
            },
        ):
            try:
                rough_filter.filter(layer, False, arguments)
                return
            except Exception as error:
                errors.append("filter(%r): %r" % (arguments, error))

    # Compatibility path.
    if rough_filter is not None and hasattr(
        rough_filter,
        "processLayer_withArguments_",
    ):
        for arguments in (
            [
                "GlyphsFilterRoughenizer",
                str(segment_length),
                str(offset_x),
                str(offset_y),
                str(angle),
            ],
            [
                "",
                str(segment_length),
                str(offset_x),
                str(offset_y),
                str(angle),
            ],
            [
                str(segment_length),
                str(offset_x),
                str(offset_y),
                str(angle),
            ],
        ):
            try:
                rough_filter.processLayer_withArguments_(layer, arguments)
                return
            except Exception as error:
                errors.append("processLayer(%r): %r" % (arguments, error))

    # Last fallback: the established Roughenizer selector.
    filter_class = NSClassFromString("GlyphsFilterRoughenizer")
    if filter_class is not None:
        try:
            instance = filter_class.alloc().init()
            selector = (
                "roughenLayer_segmentLength_offsetX_offsetY_angle_"
                "shadowLayer_error_"
            )
            if hasattr(instance, selector):
                getattr(instance, selector)(
                    layer,
                    segment_length,
                    offset_x,
                    offset_y,
                    angle,
                    None,
                    None,
                )
                return
        except Exception as error:
            errors.append("private Roughen fallback: %r" % error)

    raise RuntimeError(
        "Could not run Glyphs Roughen filter.\n%s"
        % ("\n".join(errors) if errors else "No Roughen filter found.")
    )



PRESET_DEFAULTS_KEY = "com.oldprinttool.clean.presets.v1"



# ===========================================================================
# Curve-safe wonkiness
# ===========================================================================

def _curve_safe_wonkiness(path, amount, seed):
    """
    Broadly warp an existing closed path WITHOUT changing its structure.

    Important properties:
    - no nodes are added or removed
    - LINE stays LINE
    - CURVE stays CURVE
    - OFFCURVE handles move with their owning anchor
    - deformation is broad/coherent rather than independent per-node jitter
    """
    amount = max(0.0, float(amount))

    if amount <= 0.001 or not path.closed:
        return

    nodes = list(path.nodes)
    oncurve_indices = [
        index
        for index, node in enumerate(nodes)
        if node.type != OFFCURVE
    ]

    if len(oncurve_indices) < 3:
        return

    anchors = [
        (float(nodes[index].x), float(nodes[index].y))
        for index in oncurve_indices
    ]

    # Approximate position along contour using anchor-to-anchor distances.
    cumulative = [0.0]
    total = 0.0

    for index in range(1, len(anchors)):
        dx = anchors[index][0] - anchors[index - 1][0]
        dy = anchors[index][1] - anchors[index - 1][1]
        total += math.hypot(dx, dy)
        cumulative.append(total)

    dx = anchors[0][0] - anchors[-1][0]
    dy = anchors[0][1] - anchors[-1][1]
    total += math.hypot(dx, dy)

    if total <= 0.0001:
        return

    rng = random.Random(int(seed))
    phase_1 = rng.uniform(0.0, math.tau)
    phase_2 = rng.uniform(0.0, math.tau)
    phase_3 = rng.uniform(0.0, math.tau)

    deltas = {}

    for position, node_index in enumerate(oncurve_indices):
        previous_anchor = anchors[(position - 1) % len(anchors)]
        current_anchor = anchors[position]
        next_anchor = anchors[(position + 1) % len(anchors)]

        tangent_x = next_anchor[0] - previous_anchor[0]
        tangent_y = next_anchor[1] - previous_anchor[1]
        tangent_length = math.hypot(tangent_x, tangent_y)

        if tangent_length <= 0.0001:
            deltas[node_index] = (0.0, 0.0)
            continue

        tangent_x /= tangent_length
        tangent_y /= tangent_length

        # Right-hand normal.
        normal_x = tangent_y
        normal_y = -tangent_x

        u = cumulative[position] / total

        # Broad, low-frequency field.
        # This gives the general shape a warped/printed feeling without
        # introducing fine roughness or changing node count.
        field = (
            0.62 * math.sin(math.tau * u + phase_1)
            + 0.28 * math.sin(math.tau * 2.0 * u + phase_2)
            + 0.10 * math.sin(math.tau * 3.0 * u + phase_3)
        )

        # Very small tangential component makes the warp less mechanically
        # perpendicular while still preserving the contour structure.
        tangential = (
            0.10
            * math.sin(math.tau * 1.5 * u + phase_2)
            * amount
        )

        normal_amount = field * amount

        delta_x = (
            normal_x * normal_amount
            + tangent_x * tangential
        )
        delta_y = (
            normal_y * normal_amount
            + tangent_y * tangential
        )

        deltas[node_index] = (delta_x, delta_y)

    node_count = len(nodes)

    # Apply all anchor deltas only after calculating them.
    for node_index, (delta_x, delta_y) in deltas.items():
        anchor = nodes[node_index]

        anchor.x = float(anchor.x) + delta_x
        anchor.y = float(anchor.y) + delta_y

        # Incoming handle directly before the anchor.
        previous_index = (node_index - 1) % node_count
        previous_node = nodes[previous_index]

        if previous_node.type == OFFCURVE:
            previous_node.x = float(previous_node.x) + delta_x
            previous_node.y = float(previous_node.y) + delta_y

        # Outgoing handle directly after the anchor.
        next_index = (node_index + 1) % node_count
        next_node = nodes[next_index]

        if next_node.type == OFFCURVE:
            next_node.x = float(next_node.x) + delta_x
            next_node.y = float(next_node.y) + delta_y


def apply_curve_safe_wonkiness(layer, amount, variation=0):
    """
    Apply curve-safe wonkiness to every path in the layer.

    Uses deterministic per-glyph/per-layer seeds so repeated previews with the
    same variation are stable. New Variation changes the seed.
    """
    amount = max(0.0, float(amount))

    if amount <= 0.001:
        return

    glyph = layer.parent
    glyph_name = glyph.name if glyph is not None else ""
    layer_id = str(layer.layerId)

    base_seed = 2166136261

    seed_text = "%s|%s|%d" % (
        glyph_name,
        layer_id,
        int(variation),
    )

    for character in seed_text:
        base_seed ^= ord(character)
        base_seed = (
            base_seed * 16777619
        ) & 0xFFFFFFFF

    for path_index, path in enumerate(list(layer.paths)):
        _curve_safe_wonkiness(
            path,
            amount,
            base_seed + path_index * 7919,
        )


# ===========================================================================
# Smoothen shape
# ===========================================================================

def _smooth_cubic_path(path, partial=False):
    """
    Rebuild a closed path as cubic curves.

    Full smoothing:
        Every on-curve is smooth=True (green) and gets handles.

    Partial smoothing:
        Alternating on-curves are smooth=True (green). The others remain
        smooth=False (blue) with their local handles collapsed onto the node,
        so only roughly half the nodes are actually smoothened.
    """
    if not path.closed:
        return path.copy()

    oncurves = [
        node for node in path.nodes
        if node.type != OFFCURVE
    ]

    if len(oncurves) < 3:
        return path.copy()

    points = [
        (float(node.x), float(node.y))
        for node in oncurves
    ]
    count = len(points)

    smooth_flags = (
        [(index % 2 == 0) for index in range(count)]
        if partial
        else [True] * count
    )

    incoming_handles = []
    outgoing_handles = []

    for index, point in enumerate(points):
        previous_point = points[(index - 1) % count]
        next_point = points[(index + 1) % count]

        tangent_x = next_point[0] - previous_point[0]
        tangent_y = next_point[1] - previous_point[1]
        tangent_length = (tangent_x ** 2 + tangent_y ** 2) ** 0.5

        if tangent_length > 0.0001:
            tangent_x /= tangent_length
            tangent_y /= tangent_length
        else:
            tangent_x = 0.0
            tangent_y = 0.0

        if smooth_flags[index]:
            incoming_distance = (
                (
                    (point[0] - previous_point[0]) ** 2
                    + (point[1] - previous_point[1]) ** 2
                ) ** 0.5
            ) * 0.30

            outgoing_distance = (
                (
                    (next_point[0] - point[0]) ** 2
                    + (next_point[1] - point[1]) ** 2
                ) ** 0.5
            ) * 0.30

            incoming_handles.append(
                (
                    point[0] - tangent_x * incoming_distance,
                    point[1] - tangent_y * incoming_distance,
                )
            )
            outgoing_handles.append(
                (
                    point[0] + tangent_x * outgoing_distance,
                    point[1] + tangent_y * outgoing_distance,
                )
            )
        else:
            # Preserve this anchor as a blue corner node.
            incoming_handles.append(point)
            outgoing_handles.append(point)

    new_path = GSPath()
    new_nodes = []

    first = GSNode(NSPoint(*points[0]), type=CURVE)
    first.smooth = bool(smooth_flags[0])
    new_nodes.append(first)

    for index in range(count):
        next_index = (index + 1) % count

        new_nodes.append(
            GSNode(
                NSPoint(*outgoing_handles[index]),
                type=OFFCURVE,
            )
        )
        new_nodes.append(
            GSNode(
                NSPoint(*incoming_handles[next_index]),
                type=OFFCURVE,
            )
        )

        if next_index != 0:
            end_node = GSNode(
                NSPoint(*points[next_index]),
                type=CURVE,
            )
            end_node.smooth = bool(smooth_flags[next_index])
            new_nodes.append(end_node)

    # Batch node assignment: avoids repeated Python->Glyphs notifications.
    try:
        new_path.setNodesFast_(new_nodes)
    except Exception:
        try:
            new_path.setNodesFast(new_nodes)
        except Exception:
            new_path.nodes = new_nodes

    new_path.closed = True
    return new_path


def smoothen_layer(layer, partial=False):
    """
    Components are decomposed before this stage, so paths are the only
    foreground shapes that need rebuilding.
    """
    layer.shapes = [
        _smooth_cubic_path(path, partial=partial)
        for path in list(layer.paths)
    ]



# ===========================================================================
# Controller
# ===========================================================================

class OldPrintController(object):

    def __init__(self):
        self.clean_layers = {}
        self.preview_layers = {}
        self.committed_keys = set()
        self.variation = 0
        self._suppress_callbacks = False
        self.presets = self._load_presets()

        # Vanilla expands rounded NSButton frames beyond their logical bounds.
        # Leave room for those native bezels, including on newer macOS versions.
        margin = 14
        row_height = 29
        button_height = 20
        button_gap = 14
        preset_button_width = 64
        preset_y = margin + 3 * row_height + 32 + 28 + 40
        button_y = preset_y + 44
        panel_width = 480
        panel_height = button_y + button_height + margin

        self.w = vanilla.FloatingWindow(
            (panel_width, panel_height),
            "Old Print — Clean v1.14",
            minSize=(panel_width, panel_height),
            maxSize=(680, panel_height),
        )

        label_x = margin
        slider_x = 154
        slider_width = -62
        value_x = -50
        y = margin

        # 1. Corner radius
        self.w.cornerLabel = vanilla.TextBox(
            (label_x, y + 2, 130, 20),
            "Corner roundness",
        )
        self.w.corner = vanilla.Slider(
            (slider_x, y, slider_width, 23),
            minValue=0,
            maxValue=60,
            value=0,
            callback=self.slider_changed,
        )
        self.w.cornerValue = vanilla.TextBox(
            (value_x, y + 2, 36, 20),
            "0",
        )
        y += row_height

        # 2. Wonkiness
        self.w.wonkLabel = vanilla.TextBox(
            (label_x, y + 2, 130, 20),
            "Wonkiness",
        )
        self.w.wonk = vanilla.Slider(
            (slider_x, y, slider_width, 23),
            minValue=0,
            maxValue=20,
            value=0,
            callback=self.slider_changed,
        )
        self.w.wonkValue = vanilla.TextBox(
            (value_x, y + 2, 36, 20),
            "0.0",
        )
        y += row_height

        # 3. Detail / texture
        self.w.detailLabel = vanilla.TextBox(
            (label_x, y + 2, 130, 20),
            "Level of detail",
        )
        self.w.detail = vanilla.Slider(
            (slider_x, y, slider_width, 23),
            minValue=0,
            maxValue=100,
            value=0,
            callback=self.slider_changed,
        )
        self.w.detailValue = vanilla.TextBox(
            (value_x, y + 2, 36, 20),
            "0",
        )
        y += row_height

        # 4. Unevenness
        self.w.unevenLabel = vanilla.TextBox(
            (label_x, y + 2, 130, 20),
            "Unevenness",
        )
        self.w.uneven = vanilla.Slider(
            (slider_x, y, slider_width, 23),
            minValue=0,
            maxValue=14,
            value=0,
            callback=self.slider_changed,
        )
        self.w.unevenValue = vanilla.TextBox(
            (value_x, y + 2, 36, 20),
            "0.0",
        )
        y += 32

        # Separate smoothing, selection/preview, presets, and final actions.
        self.w.smoothen = vanilla.CheckBox(
            (margin, y, 164, 20),
            "Smoothen shape",
            value=False,
            callback=self.smoothing_changed,
        )

        self.w.partialSmoothen = vanilla.CheckBox(
            (190, y, -margin, 20),
            "Partially smoothen shape",
            value=False,
            callback=self.smoothing_changed,
        )
        y += 28

        self.w.allSelected = vanilla.CheckBox(
            (margin, y, 260, 20),
            "Apply to all selected layers",
            value=True,
            callback=self.option_changed,
        )
        self.w.previewToggle = vanilla.CheckBox(
            (-106, y, 92, 20),
            "Preview",
            value=True,
            callback=self.preview_toggle_changed,
        )
        self.w.presetDivider = vanilla.HorizontalLine(
            (margin, preset_y - 16, -margin, 1),
        )

        # The field grows with the window; buttons stay aligned to the right.
        preset_actions_width = 3 * (preset_button_width + button_gap)
        self.w.presetLabel = vanilla.TextBox(
            (margin, preset_y + 1, 44, 20),
            "Preset",
        )
        self.w.presetName = vanilla.ComboBox(
            (66, preset_y - 1, -(margin + preset_actions_width), 21),
            self._preset_names(),
            completes=True,
            continuous=False,
        )
        self.w.presetName.set("None")

        self.w.savePreset = vanilla.Button(
            (-(margin + 3 * preset_button_width + 2 * button_gap),
             preset_y, preset_button_width, button_height),
            "Save",
            callback=self.save_preset_callback,
        )
        self.w.deletePreset = vanilla.Button(
            (-(margin + 2 * preset_button_width + button_gap),
             preset_y, preset_button_width, button_height),
            "Delete",
            callback=self.delete_preset_callback,
        )
        self.w.applyPreset = vanilla.Button(
            (-(margin + preset_button_width),
             preset_y, preset_button_width, button_height),
            "Apply",
            callback=self.apply_preset_callback,
        )

        self.w.actionDivider = vanilla.HorizontalLine(
            (margin, button_y - 12, -margin, 1),
        )
        self.w.restore = vanilla.Button(
            (margin, button_y, 84, button_height),
            "Restore",
            callback=self.restore_callback,
        )
        self.w.variationButton = vanilla.Button(
            (margin + 84 + button_gap, button_y, 124, button_height),
            "New Variation",
            callback=self.new_variation_callback,
        )
        self.w.commitButton = vanilla.Button(
            (-110, button_y, 96, button_height),
            "Confirm",
            callback=self.commit_callback,
        )
        self.w.setDefaultButton(self.w.commitButton)

        # Recompute only when the user releases a slider.
        for slider in (
            self.w.corner,
            self.w.wonk,
            self.w.detail,
            self.w.uneven,
        ):
            try:
                slider.getNSSlider().setContinuous_(False)
            except Exception:
                pass

        # Compact hover help.
        tooltip_pairs = (
            (
                self.w.corner,
                "Rounds both outside and inside corners of the clean base shape.",
            ),
            (
                self.w.wonk,
                "Broadly warps the existing shape while preserving its curve segments and node structure.",
            ),
            (
                self.w.detail,
                "Controls the amount/density of the native detail pass.",
            ),
            (
                self.w.uneven,
                "Controls displacement/randomness in the detail pass.",
            ),
            (
                self.w.smoothen,
                "Makes every on-curve a smooth green node with handles.",
            ),
            (
                self.w.partialSmoothen,
                "Smoothens alternating nodes: approximately half green, half blue.",
            ),
            (
                self.w.allSelected,
                "Enabled by default: apply to all selected layers in the active tab. In Font View, apply to selected glyphs at the active master. Turn off to process only the first selected layer.",
            ),
            (
                self.w.previewToggle,
                "Toggle live preview. Turning it off restores the uncommitted preview while keeping your settings.",
            ),
            (
                self.w.presetName,
                "Type a new preset name or select an existing one.",
            ),
            (
                self.w.savePreset,
                "Save the current effect settings under this name.",
            ),
            (
                self.w.deletePreset,
                "Delete the selected saved preset. The built-in None option cannot be deleted.",
            ),
            (
                self.w.applyPreset,
                "Apply the selected preset to the controls and preview it; use Confirm to commit.",
            ),
            (
                self.w.commitButton,
                "Confirm the exact visible preview without generating a new variation, then dismiss the panel.",
            ),
        )

        for control, tooltip in tooltip_pairs:
            try:
                control.setToolTip(tooltip)
            except Exception:
                pass

        self.w.bind("close", self.window_closed)

        self._update_value_labels()
        self.w.open()

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def slider_changed(self, sender):
        if self._suppress_callbacks:
            return

        self._update_value_labels()

        if self.w.previewToggle.get():
            self.apply_preview()

    def option_changed(self, sender):
        if self._suppress_callbacks:
            return

        if self.w.previewToggle.get():
            self.apply_preview()

    def preview_toggle_changed(self, sender):
        """
        Preview ON:
            show the current settings temporarily.

        Preview OFF:
            restore every uncommitted live preview immediately, but keep all
            controls/preset values untouched.
        """
        if self._suppress_callbacks:
            return

        if self.w.previewToggle.get():
            self.apply_preview()
        else:
            self._restore_all_uncommitted_previews()
            Glyphs.redraw()

    def smoothing_changed(self, sender):
        """
        Full and partial smoothing are mutually exclusive.
        """
        if self._suppress_callbacks:
            return

        self._suppress_callbacks = True
        try:
            if sender is self.w.smoothen and self.w.smoothen.get():
                self.w.partialSmoothen.set(False)
            elif (
                sender is self.w.partialSmoothen
                and self.w.partialSmoothen.get()
            ):
                self.w.smoothen.set(False)
        finally:
            self._suppress_callbacks = False

        if self.w.previewToggle.get():
            self.apply_preview()

    def new_variation_callback(self, sender):
        self.variation += 1

        if self.w.previewToggle.get():
            self.apply_preview()

    def _update_value_labels(self):
        self.w.cornerValue.set(
            "%d" % round(self.w.corner.get())
        )
        self.w.wonkValue.set(
            "%.1f" % self.w.wonk.get()
        )
        self.w.detailValue.set(
            "%d" % round(self.w.detail.get())
        )
        self.w.unevenValue.set(
            "%.1f" % self.w.uneven.get()
        )

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def _load_presets(self):
        """
        Presets are stored as one JSON string in Glyphs.defaults. This avoids
        mutating bridged NSDictionary objects and keeps the stored value
        property-list-safe.
        """
        try:
            raw = Glyphs.defaults[PRESET_DEFAULTS_KEY]
        except Exception:
            raw = None

        if not raw:
            return {}

        try:
            data = json.loads(str(raw))
        except Exception:
            print("Old Print: saved preset data was unreadable; starting empty.")
            return {}

        clean = {}

        if not isinstance(data, dict):
            return clean

        for name, values in data.items():
            if not isinstance(values, dict):
                continue

            try:
                full_smooth = bool(
                    values.get("smoothen", False)
                )
                partial_smooth = bool(
                    values.get("partial_smoothen", False)
                ) and not full_smooth

                clean[str(name)] = {
                    "corner_radius": float(
                        values.get("corner_radius", 0.0)
                    ),
                    "wonkiness": float(
                        values.get("wonkiness", 0.0)
                    ),
                    "detail": float(
                        values.get("detail", 0.0)
                    ),
                    "unevenness": float(
                        values.get("unevenness", 0.0)
                    ),
                    "smoothen": full_smooth,
                    "partial_smoothen": partial_smooth,
                }
            except Exception:
                pass

        return clean

    def _save_presets_to_defaults(self):
        try:
            Glyphs.defaults[PRESET_DEFAULTS_KEY] = json.dumps(
                self.presets,
                sort_keys=True,
            )
        except Exception:
            Glyphs.showMacroWindow()
            print("Old Print: preset save error:\n")
            print(traceback.format_exc())

    def _preset_names(self):
        return ["None"] + sorted(
            (
                name
                for name in self.presets.keys()
                if str(name).strip().lower() != "none"
            ),
            key=lambda name: name.lower(),
        )

    def _refresh_preset_items(self):
        current = str(
            self.w.presetName.get() or "None"
        ).strip()

        self.w.presetName.setItems(
            self._preset_names()
        )

        if (
            current == "None"
            or current in self.presets
        ):
            self.w.presetName.set(current)
        else:
            self.w.presetName.set("None")

    def _next_preset_name(self):
        index = 1

        while True:
            name = "Preset %d" % index
            if name not in self.presets:
                return name
            index += 1

    def _current_preset_payload(self):
        return {
            "corner_radius": float(self.w.corner.get()),
            "wonkiness": float(self.w.wonk.get()),
            "detail": float(self.w.detail.get()),
            "unevenness": float(self.w.uneven.get()),
            "smoothen": bool(self.w.smoothen.get()),
            "partial_smoothen": bool(
                self.w.partialSmoothen.get()
            ),
        }

    def save_preset_callback(self, sender):
        name = str(
            self.w.presetName.get() or ""
        ).strip()

        # "None" is reserved as the built-in neutral/no-preset item.
        if not name or name.lower() == "none":
            name = self._next_preset_name()
            self.w.presetName.set(name)

        self.presets[name] = self._current_preset_payload()
        self._save_presets_to_defaults()
        self._refresh_preset_items()

        print(
            "Old Print: saved preset '%s'."
            % name
        )

    def delete_preset_callback(self, sender):
        name = str(
            self.w.presetName.get() or "None"
        ).strip()

        if not name or name.lower() == "none":
            print("Old Print: 'None' is built in and cannot be deleted.")
            self.w.presetName.set("None")
            return

        if name not in self.presets:
            print(
                "Old Print: no saved preset named '%s'."
                % name
            )
            return

        del self.presets[name]
        self._save_presets_to_defaults()

        self.w.presetName.set("None")
        self._refresh_preset_items()

        print(
            "Old Print: deleted preset '%s'."
            % name
        )

    def apply_preset_callback(self, sender):
        name = str(
            self.w.presetName.get() or "None"
        ).strip()

        if not name or name.lower() == "none":
            self.w.presetName.set("None")
            self._set_effect_controls(
                corner_radius=0.0,
                wonkiness=0.0,
                detail=0.0,
                unevenness=0.0,
                smoothen=False,
                partial_smoothen=False,
            )
            display_name = "None"
        else:
            preset = self.presets.get(name)

            if preset is None:
                print(
                    "Old Print: no saved preset named '%s'."
                    % name
                )
                return

            self._set_effect_controls(
                corner_radius=preset["corner_radius"],
                wonkiness=preset["wonkiness"],
                detail=preset["detail"],
                unevenness=preset["unevenness"],
                smoothen=preset["smoothen"],
                partial_smoothen=preset["partial_smoothen"],
            )
            display_name = name

        targets = self.selected_layers()

        if not targets:
            print("Old Print: no target glyphs/layers selected.")
            return

        print(
            "Old Print: applied preset '%s' for %d layer%s."
            % (
                display_name,
                len(targets),
                "" if len(targets) == 1 else "s",
            )
        )

        if self.w.previewToggle.get():
            self.apply_preview()
        else:
            # Applying a preset while Preview is off must not leave an older
            # preview visible.
            self._restore_all_uncommitted_previews()
            Glyphs.redraw()

    def _set_effect_controls(
        self,
        corner_radius=0.0,
        wonkiness=0.0,
        detail=0.0,
        unevenness=0.0,
        smoothen=False,
        partial_smoothen=False,
    ):
        self._suppress_callbacks = True

        try:
            self.w.corner.set(float(corner_radius))
            self.w.wonk.set(float(wonkiness))
            self.w.detail.set(float(detail))
            self.w.uneven.set(float(unevenness))

            full = bool(smoothen)
            partial = bool(partial_smoothen) and not full

            self.w.smoothen.set(full)
            self.w.partialSmoothen.set(partial)

        finally:
            self._suppress_callbacks = False

        self._update_value_labels()

    def _reset_effect_controls(self):
        """
        Restore should make the panel visually neutral again.
        Scope ("Apply to all selected layers") is intentionally preserved.
        """
        self.variation = 0

        self._set_effect_controls(
            corner_radius=0.0,
            wonkiness=0.0,
            detail=0.0,
            unevenness=0.0,
            smoothen=False,
            partial_smoothen=False,
        )

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def selected_layers(self):
        """
        Return the layers that should receive the current effect.

        Glyphs exposes two different kinds of selection:
        - font.selectedLayers: selected layers in the active Edit View
        - font.selection: selected glyphs in Font View

        All selected layers are enabled by default. An active Edit View uses
        only its own selection; Font View selections must not leak into it.
        Without an active Edit View, selected Font View glyphs are mapped to
        the currently selected master. Line breaks and other control layers
        are never effect targets.
        """
        font = Glyphs.font
        if font is None:
            return []

        # Text selection also includes GSControlLayer objects (line breaks).
        # They can have a dummy parent glyph but no Undo manager or editable
        # outlines. Exclude them before preview, single-layer mode or Confirm.
        edit_layers = [
            layer for layer in (font.selectedLayers or [])
            if layer is not None
            and not isinstance(layer, GSControlLayer)
            and layer.parent is not None
        ]

        # Single-layer mode preserves the original behavior.
        if not self.w.allSelected.get():
            if edit_layers:
                return [edit_layers[0]]
            return []

        result = []
        seen = set()

        def add_layer(layer):
            if (
                layer is None
                or isinstance(layer, GSControlLayer)
                or layer.parent is None
            ):
                return

            try:
                key = (
                    layer.parent.name,
                    str(layer.layerId),
                )
            except Exception:
                key = id(layer)

            if key in seen:
                return

            seen.add(key)
            result.append(layer)

        # 1. Multi-selection in Edit View.
        for layer in edit_layers:
            add_layer(layer)

        # An Edit View selection takes precedence over Font View selection.
        # Also keep an empty active tab from targeting stale Font View glyphs.
        if edit_layers or font.currentTab is not None:
            return result

        # 2. Multi-glyph selection in Font View.
        #
        # GSFont.selection returns selected GSGlyph objects. Apply the preset
        # to the active master's layer for each selected glyph.
        try:
            selected_glyphs = list(font.selection or [])
        except Exception:
            selected_glyphs = []

        if selected_glyphs:
            try:
                master_id = font.selectedFontMaster.id
            except Exception:
                master_id = None

            for glyph in selected_glyphs:
                layer = None

                if master_id is not None:
                    try:
                        layer = glyph.layers[master_id]
                    except Exception:
                        layer = None

                # Defensive fallback to the master index if necessary.
                if layer is None:
                    try:
                        layer = glyph.layers[font.masterIndex]
                    except Exception:
                        layer = None

                add_layer(layer)

        return result

    def layer_key(self, layer):
        glyph = layer.parent
        glyph_name = glyph.name if glyph is not None else ""
        return (glyph_name, str(layer.layerId))

    def clean_source(self, layer):
        """
        Remember the original foreground in memory only.

        Preview does not write to the Glyphs background. The live layer
        reference is retained so it can be restored even after selection
        changes.
        """
        key = self.layer_key(layer)

        if key not in self.clean_layers:
            clean = layer.copy()

            try:
                clean.background = None
            except Exception:
                pass

            self.clean_layers[key] = clean

        self.preview_layers[key] = layer
        return self.clean_layers[key]

    @staticmethod
    def restore_layer_from_copy(layer, clean):
        layer.shapes = [
            shape.copy()
            for shape in clean.shapes
        ]
        layer.width = clean.width

    # ------------------------------------------------------------------
    # Effect
    # ------------------------------------------------------------------

    def current_parameters(self):
        corner_radius = float(self.w.corner.get())
        wonkiness = float(self.w.wonk.get())
        detail = float(self.w.detail.get())
        unevenness = float(self.w.uneven.get())
        smoothen = bool(self.w.smoothen.get())
        partial_smoothen = bool(
            self.w.partialSmoothen.get()
        )

        if detail <= 0.0:
            detail_segment_length = None
        else:
            detail_segment_length = (
                86.0 - (detail / 100.0) * 79.0
            )
            detail_segment_length = max(
                7.0,
                detail_segment_length,
            )

        return {
            "corner_radius": corner_radius,
            "wonkiness": wonkiness,
            "detail": detail,
            "detail_segment_length": detail_segment_length,
            "unevenness": unevenness,
            "smoothen": smoothen,
            "partial_smoothen": partial_smoothen,
        }

    def _process_layer(self, layer, params, message_word="previewed"):
        """
        Rebuild one layer from the clean source and apply current settings.
        """
        glyph = layer.parent
        if glyph is None:
            return

        clean = self.clean_source(layer)
        original_width = float(clean.width)

        self.restore_layer_from_copy(
            layer,
            clean,
        )

        try:
            layer.decomposeComponents()
        except Exception:
            pass

        started = time.time()

        if params["corner_radius"] > 0.001:
            apply_corner_roundness(
                layer,
                params["corner_radius"],
            )

        if params["wonkiness"] > 0.001:
            apply_curve_safe_wonkiness(
                layer,
                params["wonkiness"],
                variation=self.variation,
            )

        if params["detail_segment_length"] is not None:
            detail_offset = max(
                0.02,
                params["unevenness"],
            )
            apply_roughen(
                layer,
                params["detail_segment_length"],
                detail_offset,
                detail_offset,
                0.0,
            )

        if params["smoothen"]:
            smoothen_layer(
                layer,
                partial=False,
            )
        elif params["partial_smoothen"]:
            smoothen_layer(
                layer,
                partial=True,
            )

        layer.width = original_width

        print(
            "Old Print: %s %s in %.3fs"
            % (
                glyph.name,
                message_word,
                time.time() - started,
            )
        )

    def _restore_preview_key(self, key):
        if key in self.committed_keys:
            return

        layer = self.preview_layers.get(key)
        clean = self.clean_layers.get(key)

        if layer is None or clean is None:
            return

        self.restore_layer_from_copy(
            layer,
            clean,
        )

    def _restore_all_uncommitted_previews(self, except_keys=None):
        except_keys = set(except_keys or [])

        for key in list(self.preview_layers.keys()):
            if key in except_keys:
                continue
            if key in self.committed_keys:
                continue
            self._restore_preview_key(key)

    def apply_preview(self):
        """
        Temporary live preview only.

        It intentionally does not create an undo group. Closing the window,
        pressing Restore, changing the target selection on the next preview,
        or a preview error rolls the foreground back to the in-memory source.
        """
        if not self.w.previewToggle.get():
            self._restore_all_uncommitted_previews()
            Glyphs.redraw()
            return

        layers = self.selected_layers()

        if not layers:
            self._restore_all_uncommitted_previews()
            Glyphs.redraw()
            return

        params = self.current_parameters()
        target_keys = {
            self.layer_key(layer)
            for layer in layers
            if layer is not None
        }

        self._restore_all_uncommitted_previews(
            except_keys=target_keys,
        )

        try:
            for layer in layers:
                if layer is None or layer.parent is None:
                    continue

                self.clean_source(layer)
                self._process_layer(
                    layer,
                    params,
                    message_word="previewed",
                )

            Glyphs.redraw()

        except Exception:
            self._restore_all_uncommitted_previews()
            Glyphs.redraw()
            Glyphs.showMacroWindow()
            print("Old Print preview error:\n")
            print(traceback.format_exc())

    def _commit_visible_preview_exactly(self, layer, visible_copy):
        """
        Commit an already-visible preview WITHOUT re-running any effect.

        Preview mutations themselves are intentionally not undo-grouped. To
        turn the exact visible result into a normal Glyphs edit with Undo:

        1. snapshot the visible preview before touching the layer;
        2. restore the original clean source inside beginUndo();
        3. write the captured preview geometry straight back;
        4. endUndo().

        No Round Corner, Roughen, wonkiness or smoothing code is called here.
        Therefore Confirm cannot create a new random variation.
        """
        glyph = layer.parent
        if glyph is None:
            return

        key = self.layer_key(layer)
        clean = self.clean_layers.get(key)

        if clean is None:
            # This should only happen if the layer was never previewed.
            clean = self.clean_source(layer)

        glyph.beginUndo()
        try:
            self.restore_layer_from_copy(
                layer,
                clean,
            )
            self.restore_layer_from_copy(
                layer,
                visible_copy,
            )
        finally:
            glyph.endUndo()

    def commit_callback(self, sender):
        """
        Confirm the current result.

        If Preview is ON and a target currently has a visible preview, capture
        that exact outline and commit it directly. Filters are NOT run again.

        If Preview is OFF (or a newly selected target has never been previewed),
        there is no visible processed geometry to preserve, so the current
        settings are processed once during Confirm.
        """
        layers = self.selected_layers()

        if not layers:
            print("Old Print: no target glyphs/layers selected.")
            return

        params = self.current_parameters()
        preview_enabled = bool(
            self.w.previewToggle.get()
        )

        target_keys = {
            self.layer_key(layer)
            for layer in layers
            if layer is not None
        }

        # ------------------------------------------------------------------
        # Capture the exact visible preview BEFORE any rollback.
        # ------------------------------------------------------------------
        visible_snapshots = {}

        if preview_enabled:
            for layer in layers:
                if layer is None or layer.parent is None:
                    continue

                key = self.layer_key(layer)

                # A key is considered visibly previewed only if the controller
                # has already captured its clean source and live layer.
                if (
                    key in self.clean_layers
                    and key in self.preview_layers
                    and key not in self.committed_keys
                ):
                    visible_snapshots[key] = layer.copy()

                    try:
                        visible_snapshots[key].background = None
                    except Exception:
                        pass

        try:
            # Restore previews that are not part of this Confirm operation.
            self._restore_all_uncommitted_previews(
                except_keys=set(visible_snapshots.keys())
            )

            for layer in layers:
                glyph = layer.parent
                if glyph is None:
                    continue

                key = self.layer_key(layer)

                if key in visible_snapshots:
                    # ------------------------------------------------------
                    # Exact visible-preview commit.
                    # ------------------------------------------------------
                    self._commit_visible_preview_exactly(
                        layer,
                        visible_snapshots[key],
                    )

                    print(
                        "Old Print: %s confirmed exactly from visible preview."
                        % glyph.name
                    )

                else:
                    # ------------------------------------------------------
                    # No visible preview exists for this target.
                    # Process once from clean source inside an undo group.
                    # This primarily covers Preview OFF.
                    # ------------------------------------------------------
                    self.clean_source(layer)

                    glyph.beginUndo()
                    try:
                        self._process_layer(
                            layer,
                            params,
                            message_word="confirmed",
                        )
                    finally:
                        glyph.endUndo()

            self.committed_keys.update(target_keys)
            Glyphs.redraw()

        except Exception:
            self.committed_keys.difference_update(target_keys)

            # Only restore layers that are still considered uncommitted.
            self._restore_all_uncommitted_previews()

            Glyphs.redraw()
            Glyphs.showMacroWindow()
            print("Old Print confirm error:\n")
            print(traceback.format_exc())
            return

        # Dismissal remains separate from geometry commit.
        self._dismiss_after_apply()

    def _dismiss_after_apply(self):
        """
        Dismiss the panel after a successful commit.

        In the Glyphs Python runtime, Vanilla's Window.close() can bridge to
        NSWindow incorrectly and raise:
            TypeError: Need 1 arguments, got 0

        Glyphs' own scripting guidance recommends orderOut_(sender) for
        dismissing a custom Vanilla window. This removes it from view without
        touching the already committed foreground.

        Do not route a dismissal failure through the apply rollback path:
        geometry has already been committed successfully at this point.
        """
        try:
            ns_window = self.w.getNSWindow()
            ns_window.orderOut_(self)
            return True
        except Exception:
            Glyphs.showMacroWindow()
            print("Old Print: effect was applied, but the panel could not be dismissed:\n")
            print(traceback.format_exc())
            return False

    def window_closed(self, sender):
        """
        Title-bar close behaves as Cancel. A successful Confirm marks only the
        committed target keys, so every other preview is still rolled back.
        """
        try:
            self._restore_all_uncommitted_previews()
            Glyphs.redraw()
        except Exception:
            Glyphs.showMacroWindow()
            print("Old Print close/rollback error:\n")
            print(traceback.format_exc())

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------

    def restore_callback(self, sender):
        """
        Cancel all temporary previews and reset effect controls to neutral.
        The Preview toggle itself is left as the user's UI preference.
        """
        try:
            self._restore_all_uncommitted_previews()
            self._reset_effect_controls()
            Glyphs.redraw()

        except Exception:
            Glyphs.showMacroWindow()
            print("Old Print restore error:\n")
            print(traceback.format_exc())


OldPrintController()
