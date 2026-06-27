#MenuTitle: Glyph Colouriser
# -*- coding: utf-8 -*-

__doc__ = """
Opens a panel where you can choose separate overview colours for:

1. Glyphs containing paths only
2. Glyphs containing components only
3. Glyphs with both paths and components
4. Glyphs that do not export

Empty exporting glyphs are ignored.
For Glyphs 3.
"""

from GlyphsApp import Glyphs
import vanilla
from AppKit import NSFont


COLOR_NAMES = [
    "Red",
    "Orange",
    "Brown",
    "Yellow",
    "Light Green",
    "Dark Green",
    "Light Blue",
    "Dark Blue",
    "Purple",
    "Magenta",
    "Light Gray",
    "Charcoal",
    "No Color",
]


def color_index_from_popup_index(index):
    if index == 12:
        return None
    return index


class ColourGlyphsByCategory(object):

    def __init__(self):
        margin = 15
        panel_width = 320
        dropdown_width = panel_width - margin * 2

        self.w = vanilla.FloatingWindow(
            (panel_width, 371),
            "",
            autosaveName="com.yourname.ColourGlyphsByCategory.mainwindow",
        )

        self.w.titleText = vanilla.TextBox(
            (margin, 16, -margin, 22),
            "Colour glyphs by category",
            sizeStyle="regular",
        )
        self.w.titleText.getNSTextField().setFont_(NSFont.boldSystemFontOfSize_(13))

        self.w.pathsOnlyText = vanilla.TextBox(
            (margin, 68, -margin, 20),
            "Glyphs containing paths only",
            sizeStyle="regular",
        )

        self.w.pathsOnlyColor = vanilla.PopUpButton(
            (margin, 92, dropdown_width, 22),
            COLOR_NAMES,
            sizeStyle="regular",
        )
        self.w.pathsOnlyColor.set(12)  # No Color

        self.w.componentsOnlyText = vanilla.TextBox(
            (margin, 128, -margin, 20),
            "Glyphs containing components only",
            sizeStyle="regular",
        )

        self.w.componentsOnlyColor = vanilla.PopUpButton(
            (margin, 152, dropdown_width, 22),
            COLOR_NAMES,
            sizeStyle="regular",
        )
        self.w.componentsOnlyColor.set(12)  # No Color

        self.w.mixedGlyphsText = vanilla.TextBox(
            (margin, 188, -margin, 20),
            "Glyphs with both paths and components",
            sizeStyle="regular",
        )

        self.w.mixedGlyphsColor = vanilla.PopUpButton(
            (margin, 212, dropdown_width, 22),
            COLOR_NAMES,
            sizeStyle="regular",
        )
        self.w.mixedGlyphsColor.set(12)  # No Color

        self.w.nonExportingText = vanilla.TextBox(
            (margin, 248, -margin, 20),
            "Glyphs that do not export",
            sizeStyle="regular",
        )

        self.w.nonExportingColor = vanilla.PopUpButton(
            (margin, 272, dropdown_width, 22),
            COLOR_NAMES,
            sizeStyle="regular",
        )
        self.w.nonExportingColor.set(12)  # No Color

        self.w.markButton = vanilla.Button(
            (margin, 326, -margin, 30),
            "Add colours 🎨",
            callback=self.markGlyphs,
            sizeStyle="regular",
        )
        self.w.markButton.getNSButton().setFont_(NSFont.boldSystemFontOfSize_(13))

        self.w.open()
        self.w.makeKey()

    def glyph_has_paths_or_components(self, glyph):
        master_layers = [layer for layer in glyph.layers if layer.isMasterLayer]

        if not master_layers:
            return False, False

        has_any_path = False
        has_any_component = False

        for layer in master_layers:
            if len(layer.paths) > 0:
                has_any_path = True

            if len(layer.components) > 0:
                has_any_component = True

        return has_any_path, has_any_component

    def markGlyphs(self, sender):
        font = Glyphs.font

        if not font:
            Glyphs.showNotification(
                "Colour Glyphs by Category",
                "No font open.",
            )
            return

        paths_only_color = color_index_from_popup_index(self.w.pathsOnlyColor.get())
        components_only_color = color_index_from_popup_index(self.w.componentsOnlyColor.get())
        mixed_glyphs_color = color_index_from_popup_index(self.w.mixedGlyphsColor.get())
        non_exporting_color = color_index_from_popup_index(self.w.nonExportingColor.get())

        paths_only_count = 0
        components_only_count = 0
        mixed_glyphs_count = 0
        non_exporting_count = 0
        ignored_empty_count = 0

        font.disableUpdateInterface()

        try:
            for glyph in font.glyphs:

                # Non-exporting glyphs take priority over construction type.
                if not glyph.export:
                    glyph.color = non_exporting_color
                    non_exporting_count += 1
                    continue

                has_any_path, has_any_component = self.glyph_has_paths_or_components(glyph)

                if has_any_path and has_any_component:
                    glyph.color = mixed_glyphs_color
                    mixed_glyphs_count += 1

                elif has_any_path:
                    glyph.color = paths_only_color
                    paths_only_count += 1

                elif has_any_component:
                    glyph.color = components_only_color
                    components_only_count += 1

                else:
                    ignored_empty_count += 1

        finally:
            font.enableUpdateInterface()

        message = (
            "Coloured glyphs containing paths only: %i\n"
            "Coloured glyphs containing components only: %i\n"
            "Coloured glyphs with both paths and components: %i\n"
            "Coloured glyphs that do not export: %i\n"
            "Ignored empty exporting glyphs: %i"
            % (
                paths_only_count,
                components_only_count,
                mixed_glyphs_count,
                non_exporting_count,
                ignored_empty_count,
            )
        )

        print("Done.")
        print(message)

        Glyphs.showNotification(
            "Colour Glyphs by Category",
            message,
        )


ColourGlyphsByCategory()