# MenuTitle: Align to Horizontal Center, all masters
# -*- coding: utf-8 -*-
"""
Centers the complete foreground of every master layer of each selected glyph
horizontally inside that master's existing glyph width.

This companion action is intended for its own Option-added keyboard shortcut.

The regular script's current-layer mode handles selections as follows:
- Selected contour/path: centers the selected contour(s) as one group.
- Selected component(s): centers them as part of the same selection group.
- Selected on-curve node(s) or off-curve handle(s): centers those selected points.
- Selected anchors are supported too.
- If nothing is selected, all editable foreground content is centered as one group.
- The layer width is never changed.
- Italic layers are centered on the italic center axis using the layer's italic
  angle and the master's slant height.

This all-masters action ignores in-layer selections and centers the full
foreground of each master independently.

The script uses Glyphs' native layer transformation methods rather than
manually rewriting individual object positions. This is safer for mixed
selections and lets Glyphs handle its own selection bookkeeping.
"""

ALIGN_ALL_MASTERS = True

from math import isfinite, radians, tan

from AppKit import NSAffineTransform
from GlyphsApp import Glyphs


EPSILON = 1e-7


def unique_selected_layers(font):
    """Return selected layers once each, preserving their UI order."""
    layers = []
    seen = set()

    for layer in font.selectedLayers:
        if layer is None:
            continue

        glyph = getattr(layer, "parent", None)
        glyph_id = getattr(glyph, "id", None)
        layer_id = getattr(layer, "layerId", None)

        # IDs are preferable, but Python object identity is a safe fallback.
        key = (
            str(glyph_id) if glyph_id is not None else id(glyph),
            str(layer_id) if layer_id is not None else id(layer),
        )

        if key not in seen:
            seen.add(key)
            layers.append(layer)

    return layers


def layers_to_align(font):
    selected_layers = unique_selected_layers(font)
    if not ALIGN_ALL_MASTERS:
        return selected_layers

    result = []
    seen_glyphs = set()
    for selected_layer in selected_layers:
        glyph = getattr(selected_layer, "parent", None)
        if glyph is None:
            continue
        glyph_id = getattr(glyph, "id", None)
        key = str(glyph_id) if glyph_id is not None else id(glyph)
        if key in seen_glyphs:
            continue
        seen_glyphs.add(key)

        master_layers = {
            str(layer.layerId): layer
            for layer in glyph.layers
            if layer is not None and getattr(layer, "layerId", None) is not None
        }
        for master in font.masters:
            layer = master_layers.get(str(master.id))
            if layer is not None:
                result.append(layer)
    return result


def rect_is_usable(rect):
    """Accept point selections (zero-size rects), reject null/invalid rects."""
    if rect is None:
        return False

    try:
        values = (
            float(rect.origin.x),
            float(rect.origin.y),
            float(rect.size.width),
            float(rect.size.height),
        )
    except Exception:
        return False

    return all(isfinite(value) for value in values)


def rect_center(rect):
    return (
        float(rect.origin.x) + float(rect.size.width) * 0.5,
        float(rect.origin.y) + float(rect.size.height) * 0.5,
    )


def layer_has_selection(layer):
    try:
        return len(layer.selection) > 0
    except Exception:
        try:
            return bool(list(layer.selection))
        except Exception:
            return False


def layer_has_drawable_content(layer):
    """Bounds are meaningful when there is at least a path or component."""
    try:
        return len(layer.paths) > 0 or len(layer.components) > 0
    except Exception:
        return True


def selection_bounds(layer):
    """Glyphs 4 selection bounds, with a compatibility fallback."""
    try:
        return layer.selectionBounds
    except Exception:
        try:
            return layer.boundsOfSelection()
        except Exception:
            return None


def content_bounds(layer):
    try:
        return layer.bounds
    except Exception:
        try:
            return layer.bounds()
        except Exception:
            return None


def italic_angle_for_layer(layer):
    """Use the effective layer angle, falling back to its associated master."""
    angle = None

    try:
        angle = float(layer.italicAngle)
    except Exception:
        pass

    if angle is None or not isfinite(angle):
        try:
            angle = float(layer.master.italicAngleForLayer_(layer))
        except Exception:
            try:
                angle = float(layer.master.italicAngle)
            except Exception:
                angle = 0.0

    return angle if isfinite(angle) else 0.0


def slant_height_for_layer(layer):
    """Return Glyphs' slant origin height for this layer."""
    master = getattr(layer, "master", None)
    if master is None:
        return 0.0

    try:
        value = float(master.slantHeightForLayer_(layer))
        if isfinite(value):
            return value
    except Exception:
        pass

    # Glyphs' traditional fallback is half the x-height.
    try:
        value = float(master.xHeightForLayer_(layer)) * 0.5
        if isfinite(value):
            return value
    except Exception:
        pass

    try:
        value = float(master.xHeight) * 0.5
        if isfinite(value):
            return value
    except Exception:
        pass

    return 0.0


def italic_center_x(layer, y, width):
    """X coordinate of the italic center axis at vertical position y."""
    angle = italic_angle_for_layer(layer)
    if abs(angle) < EPSILON:
        return width * 0.5

    slant_height = slant_height_for_layer(layer)
    return width * 0.5 + (float(y) - slant_height) * tan(radians(angle))


def horizontal_translation(delta_x):
    transform = NSAffineTransform.new()
    transform.translateXBy_yBy_(float(delta_x), 0.0)
    return transform


def transform_selected_content(layer, transform):
    """Use Glyphs' native selection transform."""
    if hasattr(layer, "transformSelection_"):
        layer.transformSelection_(transform)
        return

    # Fallback for older Glyphs 4 builds.
    if hasattr(layer, "transform_checkForSelection_doComponents_"):
        layer.transform_checkForSelection_doComponents_(transform, True, True)
        return

    layer.transform_checkForSelection_(transform, True)


def transform_all_content(layer, transform):
    """Transform the layer's editable foreground content, including components."""
    if hasattr(layer, "transform_checkForSelection_doComponents_"):
        layer.transform_checkForSelection_doComponents_(transform, False, True)
        return

    layer.transform_checkForSelection_(transform, False)


def center_layer(layer, use_selection=True):
    """Center either the current selection or the whole layer as one group."""
    original_width = float(layer.width)
    has_selection = use_selection and layer_has_selection(layer)

    if has_selection:
        bounds = selection_bounds(layer)
    else:
        if not layer_has_drawable_content(layer):
            return False
        bounds = content_bounds(layer)

    if not rect_is_usable(bounds):
        # Important: if some unsupported object (for example a guide) is selected,
        # do not interpret that as "nothing selected" and unexpectedly move the glyph.
        return False

    center_x, center_y = rect_center(bounds)
    target_x = italic_center_x(layer, center_y, original_width)
    delta_x = target_x - center_x

    if abs(delta_x) < EPSILON:
        return False

    transform = horizontal_translation(delta_x)

    # Width should not be affected by a translation, but preserve it explicitly
    # so metric keys/component updates cannot accidentally alter the canvas width.
    try:
        if has_selection:
            transform_selected_content(layer, transform)
        else:
            transform_all_content(layer, transform)
    finally:
        if abs(float(layer.width) - original_width) > EPSILON:
            layer.width = original_width

    return True


def main():
    font = Glyphs.font
    if font is None:
        return

    layers = layers_to_align(font)
    if not layers:
        return

    errors = []
    font.disableUpdateInterface()

    try:
        for layer in layers:
            glyph = getattr(layer, "parent", None)
            if glyph is None:
                continue

            undo_started = False
            try:
                glyph.beginUndo()
                undo_started = True
                center_layer(layer, use_selection=not ALIGN_ALL_MASTERS)
            except Exception as error:
                glyph_name = getattr(glyph, "name", "<unknown glyph>")
                errors.append("{}: {}".format(glyph_name, error))
            finally:
                if undo_started:
                    try:
                        glyph.endUndo()
                    except Exception:
                        pass
    finally:
        font.enableUpdateInterface()
        Glyphs.redraw()

    if errors:
        Glyphs.showMacroWindow()
        print("Align to Horizontal Center — errors:\n")
        for error in errors:
            print("• " + error)


main()
