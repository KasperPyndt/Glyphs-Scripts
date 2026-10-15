# MenuTitle: Copy Selection as Vectors
# -*- coding: utf-8 -*-
# Compatibility: Glyphs 3 and 4, Python 3.
"""Copy selected Edit View text (or the entire tab) as editable AICB/SVG.

Glyphs 3 and 4, macOS, Python 3. Select text with the Text tool, run this script, then paste
into Illustrator or InDesign. Node selections do not limit the text.
The font is never modified or saved. Only the clipboard is replaced.
"""

import math
import traceback

OUTPUT_EM_SIZE = 100.0  # Em size in points, independent of Edit View zoom.
TITLE = "Copy Word as Vectors"


def number(value):
    """Preserve fractional values without exponential PDF number syntax."""
    if not math.isfinite(value):
        raise ValueError("An outline or position contains a non-finite coordinate.")
    result = format(value, ".10f").rstrip("0").rstrip(".")
    return "0" if result in ("", "-0") else result


def path_commands(path):
    """Detach native NSBezierPath elements into plain Python data."""
    commands = []
    current = start = None
    open_contour = False
    for index in range(path.elementCount()):
        # Bridge signatures differ between the installed Python runtimes.
        try:
            kind, native_points = path.elementAtIndex_associatedPoints_(index)
        except TypeError:
            kind, native_points = path.elementAtIndex_associatedPoints_(index, None)
        # NSBezierPath: move=0, line=1, cubic=2, close=3, quadratic=4.
        kind = int(kind)
        count = {0: 1, 1: 1, 2: 3, 3: 0, 4: 2}.get(kind)
        if count is None:
            raise ValueError("Unsupported native path element: %s" % kind)
        points = [(float(p.x), float(p.y)) for p in (native_points or ())[:count]]
        if kind == 0:
            if open_contour:
                raise ValueError("Open contours cannot be copied as filled outlines.")
            current = start = points[0]
            # A move with no following segment has no visible contour.
            # Native paths may append such a move after closepath.
            open_contour = False
            commands.append(("m", points))
        elif kind == 1:
            current = points[0]
            open_contour = True
            commands.append(("l", points))
        elif kind == 2:
            current = points[2]
            open_contour = True
            commands.append(("c", points))
        elif kind == 4:
            if current is None:
                raise ValueError("Quadratic curve has no starting point.")
            control, end = points
            first = tuple(current[i] + 2.0 / 3 * (control[i] - current[i]) for i in (0, 1))
            second = tuple(end[i] + 2.0 / 3 * (control[i] - end[i]) for i in (0, 1))
            commands.append(("c", [first, second, end]))
            current = end
            open_contour = True
        else:
            commands.append(("h", []))
            current = start
            open_contour = False
    if open_contour:
        raise ValueError("Open contours cannot be copied as filled outlines.")
    return commands


def normalize_artwork(artwork, scale):
    """Translate once, preserving all relative positions and fractional units.

    Control-point bounds include the full curves even when handles overshoot.
    Invisible edge spaces are trimmed; internal spaces stay in the positions.
    """
    points = [point for commands, _ in artwork for _, pts in commands for point in pts]
    if not points:
        raise ValueError("The selected text contains no outlines to copy.")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("The output size must be positive and finite.")
    if not all(math.isfinite(v) for point in points for v in point):
        raise ValueError("An outline or position contains a non-finite coordinate.")
    left, bottom = (min(p[i] for p in points) for i in (0, 1))
    right, top = (max(p[i] for p in points) for i in (0, 1))
    width, height = (right - left) * scale, (top - bottom) * scale
    if width <= 0 or height <= 0:
        raise ValueError("The selected outlines have no filled area.")
    result = []
    for commands, even_odd in artwork:
        transformed = []
        for operator, pts in commands:
            transformed.append((operator, [((x - left) * scale, (y - bottom) * scale) for x, y in pts]))
        result.append((transformed, even_odd))
    return result, width, height


def command_text(commands):
    return "\n".join(
        " ".join([number(v) for point in pts for v in point] + [operator])
        for operator, pts in commands
    )


def make_pdf(artwork, width, height):
    """A single-page PDF containing only filled vector paths."""
    stream = ["q", "0 0 0 1 k"]  # Process black, transparent background.
    for commands, even_odd in artwork:
        stream.extend((command_text(commands), "f*" if even_odd else "f"))
    stream.append("Q")
    content = ("\n".join(stream) + "\n").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %s %s] /Resources << >> /Contents 4 0 R >>"
         % (number(width), number(height))).encode("ascii"),
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"endstream",
    ]
    result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(("%d 0 obj\n" % index).encode("ascii") + obj + b"\nendobj\n")
    xref_offset = len(result)
    result.extend(("xref\n0 %d\n0000000000 65535 f \n" % len(offsets)).encode("ascii"))
    for offset in offsets[1:]:
        result.extend(("%010d 00000 n \n" % offset).encode("ascii"))
    result.extend(("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
                   % (len(offsets), xref_offset)).encode("ascii"))
    return bytes(result)


def make_svg(artwork, width, height):
    paths = []
    svg_operator = {"m": "M", "l": "L", "c": "C", "h": "Z"}
    for commands, even_odd in artwork:
        data = " ".join(
            " ".join([svg_operator[op]] + [number(v) for point in pts for v in point])
            for op, pts in commands
        )
        paths.append('<path fill-rule="%s" d="%s"/>' % ("evenodd" if even_odd else "nonzero", data))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%spt" height="%spt" viewBox="0 0 %s %s">'
        '<g fill="#000000" transform="translate(0 %s) scale(1 -1)">%s</g></svg>'
        % (number(width), number(height), number(width), number(height), number(height), "".join(paths))
    ).encode("utf-8")


def closed_contours(commands):
    """Keep real closed contours; drop native trailing move-only subpaths."""
    contours = []
    current = []
    for op, points in commands:
        if op == "m":
            if len(current) > 1:
                raise ValueError("An open contour cannot be copied as filled artwork.")
            current = [(op, points)]
        elif op == "h":
            if len(current) > 1:
                contours.append(current)
            current = []
        else:
            if not current:
                raise ValueError("A path segment has no starting point.")
            current.append((op, points))
    if len(current) > 1:
        raise ValueError("An open contour cannot be copied as filled artwork.")
    return contours


def contour_signed_area(contour):
    """Exact signed area, including cubic curves and the closing edge.

    Work relative to the first point to avoid cancellation at large Edit
    View coordinates. Positive area means counterclockwise in font space.
    """
    origin = contour[0][1][0]
    current = (0.0, 0.0)
    area = 0.0
    for op, points in contour[1:]:
        shifted = [(p[0] - origin[0], p[1] - origin[1]) for p in points]
        end = shifted[-1]
        if op == "l":
            area += (current[0] * end[1] - current[1] * end[0]) / 2.0
        elif op == "c":
            control = [current] + shifted
            coefficients = []
            for axis in (0, 1):
                a, b, c, d = [p[axis] for p in control]
                coefficients.append((a, 3 * (b - a), 3 * (a - 2 * b + c),
                                     -a + 3 * b - 3 * c + d))
            x, y = coefficients
            area += sum((x[i] * j * y[j] - y[i] * j * x[j]) / (i + j)
                        for i in range(4) for j in range(1, 4)) / 2.0
        current = end
    # The final straight edge ends at the local origin, so its area is zero.
    return area


def make_aicb(artwork, width, height):
    """Adobe Illustrator clipboard data: editable paths, no placed artwork.

    AICB is an ASCII Illustrator document. Each glyph is a compound path,
    enclosed in one ordinary group for the whole copied word. Adobe's path
    Each contour explicitly returns to its first point before f. Illustrator
    otherwise invents a curved closing segment for some open-ended paths.
    *u/*U join counters and disconnected parts without changing geometry.
    """
    lines = [
        "%!PS-Adobe-3.0",
        "%%Creator: Adobe Illustrator(R) 6.0",
        "%%Title: (Glyphs Word Outlines)",
        f"%%BoundingBox: 0 0 {math.ceil(width)} {math.ceil(height)}",
        f"%%HiResBoundingBox: 0 0 {number(width)} {number(height)}",
        "%%DocumentProcessColors: Black",
        "%%DocumentSuppliedResources: procset Adobe_Illustrator_AI5 1.0 0",
        "%AI5_FileFormat 2.0",
        "%AI3_ColorUsage: Black&White",
        "%%EndComments",
        "%%BeginProlog",
        "%%BeginResource: procset Adobe_Illustrator_AI5 1.0 0",
        # InDesign executes the EPS language while importing AICB. Supply
        # every used operator rather than relying on Illustrator's procsets.
        "/Adobe_Illustrator_AI5 24 dict def Adobe_Illustrator_AI5 begin",
        "/initialize {Adobe_Illustrator_AI5 begin} bind def",
        "/terminate {end} bind def",
        "/compound false def /evenodd false def",
        "/m /moveto load def /L /lineto load def /C /curveto load def",
        "/k /setcmykcolor load def",
        "/A {pop} bind def /O {pop} bind def /R {pop} bind def",
        "/D {pop} bind def",
        "/u {} bind def /U {} bind def",
        "/XR {/evenodd exch 0 ne def} bind def",
        "/paint {evenodd {eofill} {fill} ifelse} bind def",
        "/f {closepath compound not {paint newpath} if} bind def",
        "/*u {/compound true def newpath} bind def",
        "/*U {paint newpath /compound false def} bind def",
        "end",
        "%%EndResource",
        "%%EndProlog",
        "%%BeginSetup",
        "Adobe_Illustrator_AI5 /initialize get exec",
        "%%EndSetup",
        "0 A", "0 O", "0 R", "0 0 0 1 k",
        "u",
    ]
    for commands, even_odd in artwork:
        contours = closed_contours(commands)
        if not contours:
            continue
        lines.append("%d XR" % int(even_odd))
        if len(contours) > 1:
            lines.append("*u")
        for contour in contours:
            lines.append("%d D" % int(contour_signed_area(contour) > 0))
            for op, points in contour:
                # Corner operators keep independent control handles intact.
                native_op = {"m": "m", "l": "L", "c": "C"}[op]
                lines.append(" ".join([number(v) for p in points for v in p] + [native_op]))
            first = contour[0][1][0]
            last = contour[-1][1][-1]
            if first != last:
                lines.append("%s %s L" % (number(first[0]), number(first[1])))
            lines.append("f")
        if len(contours) > 1:
            lines.append("*U")
    lines.extend(("U", "%%Trailer", "Adobe_Illustrator_AI5 /terminate get exec", "%%EOF"))
    return ("\n".join(lines) + "\n").encode("ascii")


def capture_artwork(font):
    """Read native layout; never substitute width sums for rendered positions."""
    from Foundation import NSPoint
    tab = font.currentTab
    if tab is None:
        raise ValueError("Open an Edit tab and type a word first.")
    view = tab.graphicView()
    if hasattr(view, "isInterpolating") and view.isInterpolating():
        raise ValueError("Switch from the interpolation preview to an editable master layer first.")
    required = ("cachedLayerCount", "cachedLayerAtIndex_", "cachedPositionAtIndex_",
                "zoomTransformForPosition_doOffset_")
    if not all(hasattr(view, name) for name in required):
        raise ValueError("This Glyphs build does not expose the required Edit View layout API.")
    count = int(view.cachedLayerCount())
    if not count:
        raise ValueError("The Edit tab is empty. Type a word first.")
    start, length = 0, count
    # A selected glyph or selected nodes are not a text selection.
    if font.tool in ("TextTool", "GlyphsToolText"):
        selected = view.selectedLayerRange()
        if selected.length > 0:
            start, length = int(selected.location), int(selected.length)
    if start < 0 or length <= 0 or start + length > count:
        raise ValueError("The text selection is out of date. Select the word again.")
    # Native transforms handle scaled/flipped view coordinates. Undo the
    # common view transform to return to font units, independent of zoom.
    inverse = view.zoomTransformForPosition_doOffset_(NSPoint(0, 0), False).copy()
    inverse.invert()
    artwork = []
    names = []
    for index in range(start, start + length):
        layer = view.cachedLayerAtIndex_(index)
        if layer is None:
            raise ValueError("Glyphs could not resolve a displayed layer.")
        path = layer.completeBezierPath
        if path is None or path.elementCount() == 0:
            continue  # Spaces/control layers still contribute native positions.
        path = path.copy()
        transform = view.zoomTransformForPosition_doOffset_(view.cachedPositionAtIndex_(index), False)
        path.transformUsingAffineTransform_(transform)
        path.transformUsingAffineTransform_(inverse)
        artwork.append((path_commands(path), bool(path.windingRule())))
        names.append(layer.parent.name)
    return artwork, names


def main():
    from AppKit import NSPasteboard, NSPasteboardItem
    from Foundation import NSData
    from GlyphsApp import Glyphs, Message
    try:
        font = Glyphs.font
        if font is None:
            raise ValueError("Open a font and an Edit tab first.")
        artwork, names = capture_artwork(font)
        artwork, width, height = normalize_artwork(artwork, OUTPUT_EM_SIZE / float(font.upm))
        # No PDF representation: InDesign must import actual editable paths.
        aicb = make_aicb(artwork, width, height)
        svg = make_svg(artwork, width, height)
        item = NSPasteboardItem.alloc().init()
        for kind, payload in (("com.adobe.illustrator.aicb", aicb), ("public.svg-image", svg)):
            data = NSData.dataWithBytes_length_(payload, len(payload))
            if not item.setData_forType_(data, kind):
                raise RuntimeError("Could not prepare the %s clipboard representation." % kind)
        pasteboard = NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        if not pasteboard.writeObjects_([item]):
            raise RuntimeError("macOS could not write the vector artwork to the clipboard.")
        print("%s: copied %d outlined glyphs (%s), %.2f × %.2f pt. Paste in Illustrator or InDesign."
              % (TITLE, len(names), " ".join(names), width, height))
    except Exception as error:
        print(traceback.format_exc())
        Message(title=TITLE, message=str(error))


if __name__ == "__main__":
    main()
