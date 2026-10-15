# Glyphs Scripts

Python scripts by Kasper Pyndt (Approximate Type) for drawing, spacing, proofing, and producing fonts in [Glyphs 4](https://glyphsapp.com/). This collection brings together small everyday utilities and tools for working across masters, preparing exports, and exploring letterforms.

[Installation](#installation) — [Script catalogue](#script-catalogue) — [Production workflows](#production-workflows) — [Experimental tools](#experimental-tools) — [Contact](#contact)

## Installation

1. Download this repository using **Code → Download ZIP** on GitHub and unzip it, or clone it with Git.
2. In Glyphs, choose **Script → Open Scripts Folder**.
3. Copy the collection into that folder. Keep the category folders together to preserve their organization in the Script menu.
4. Hold **Option** and choose **Script → Reload Scripts**. The scripts will appear under **Script** in their corresponding folders.

Many tools with a panel use **Vanilla**. Install the Python 3 runtime and Vanilla, if needed, from the **Modules** tab in Glyphs’ Plugin Manager. See the official [scripts guide](https://handbook.glyphsapp.com/scripts/) and [extension setup guide](https://glyphsapp.com/learn/extending-glyphs) for details.

### Compatibility

The collection includes scripts written or adapted for Glyphs 4. Check individual script headers for version requirements.

## Script catalogue

- [Alignment](#alignment)
- [Anchors](#anchors)
- [Coherency](#coherency)
- [Colours](#colours)
- [Components](#components)
- [Copy Paste](#copy-paste)
- [Diacritics](#diacritics)
- [Drawing](#drawing)
- [Layers](#layers)
- [Production](#production)
- [Proofing](#proofing)
- [Show](#show)
- [Spacing & Kerning](#spacing--kerning)
- [Variable Fonts](#variable-fonts)
- [Experimental tools](#experimental-tools)

### Alignment

| Script | What it does | Scope |
| --- | --- | --- |
| [Align to Horizontal Center](./Alignment/Align%20to%20Horizontal%20Center.py) | Centers selected nodes, paths, components, or anchors within the glyph width. With no internal selection, centers the whole foreground. Preserves width and accounts for italic slant. | Selected layers. |
| [Align to Horizontal Center, all masters](./Alignment/Align%20to%20Horizontal%20Center%20-%20All%20Masters.py) | Centers each master’s complete foreground within its existing glyph width, accounting for italic slant. Ignores internal node selections. | All masters of selected glyphs. |
| [Align to Vertical Center](./Alignment/Align%20to%20Vertical%20Center.py) | Centers selected geometry halfway between the baseline and cap height. With no internal selection, moves the whole layer. | Selected layers. |
| [Align to Vertical Center, all masters](./Alignment/Align%20to%20Vertical%20Center%20-%20All%20Masters.py) | Centers the complete foreground between each master’s baseline and cap height. | All masters of selected glyphs. |
| [Align to Vertical Center of Hyphen](./Alignment/Align%20to%20Vertical%20Center%20of%20Hyphen.py) | Aligns the vertical center of each selected layer to the hyphen in its associated master. Useful for punctuation and mathematical symbols. | Selected layers; requires a drawn `hyphen`. |
| [Center Anchor to Selection](./Alignment/Center%20Anchor%20to%20Selection.py) | Moves one selected anchor to the center of the bounding box defined by selected nodes or components. Select at least two nodes or one component together with the anchor. | First selected layer. |
| [Equalise sidebearings](./Alignment/Equalise%20sidebearings.py) | Makes left and right sidebearings equal by shifting the foreground, while keeping the advance width unchanged. | Selected layers. |

### Anchors

| Script | What it does | Scope |
| --- | --- | --- |
| [Move Anchor in All Masters 2](./Anchors/Move%20Anchor%20in%20All%20Masters.py) | Moves the selected anchor name by a chosen number of units using arrow buttons. Applies the same relative move wherever that anchor exists; vertical moves follow each master’s italic angle. | All masters of selected glyphs. |

### Coherency

| Script | What it does | Scope |
| --- | --- | --- |
| [Show Possible Relatives](./Coherency/Show%20Relatives.py) | Shows predefined structural relatives of the selected glyph, generates English sample words for the group, or opens all relative groups. Replaces the current tab’s text, or creates a tab if none is open. | Proofing text; leaves outlines unchanged. |

### Colours

| Script | What it does | Scope |
| --- | --- | --- |
| [Glyph Colouriser](./Colours/Glyph%20Colouriser.py) | Assigns separate overview colours to glyphs with paths only, components only, mixed construction, or export disabled. Non-exporting status takes priority; empty exporting glyphs are skipped. | Glyph colours across the whole font. |

### Components

| Script | What it does | Scope |
| --- | --- | --- |
| [Disable Auto Alignment for Components in Selected Glyphs](./Components/Disable%20Automatic%20Alignment%20for%20Components.py) | Turns off automatic alignment for every component in the selected glyphs, allowing manual positioning. | All layers of selected glyphs. |

### Copy Paste

| Script | What it does | Scope |
| --- | --- | --- |
| [Copy Word as Vectors](./Copy%20Paste/Copy%20Word%20as%20Vectors.py) | Copies displayed text as editable vector artwork for pasting into Illustrator or InDesign, retaining its displayed placement. Select text with the Text tool to limit the copy; otherwise the whole tab is used. Run from an editable master rather than an interpolation preview. | Clipboard only; leaves the font unchanged. |

### Diacritics

| Script | What it does | Scope |
| --- | --- | --- |
| [Show Glyphs Using Selected Diacritic](./Diacritics/Show%20Glyphs%20Using%20Selected%20Diacritic.py) | Finds glyphs that directly use the first selected glyph as a component in any master, then opens the matches in a new tab. Also works with component sources other than diacritics. | Searches all glyphs’ master layers; leaves outlines unchanged. |
| [Show All Glyphs Missing Kerning Groups](./Diacritics/Show%20All%20Glyphs%20Without%20Kern%20Groups.py) | Opens every glyph missing a left or right kerning group, including non-exporting glyphs. | Whole font; displays the current master. |

### Drawing

| Script | What it does | Scope |
| --- | --- | --- |
| [Clear Selected Glyphs](./Drawing/Clear%20Selected%20Glyphs.py) | Clears selected glyphs’ layer contents, including foreground artwork, anchors, guides, annotations, and backgrounds. Choose the current master or all masters in the panel. | Glyphs selected in Font View. |
| [Find Inflections](./Drawing/Find%20Inflections.py) | Finds glyphs with true inflections in cubic Bézier curves and opens them in a new tab. Checks outline paths without decomposing components. | Whole font, current master; leaves outlines unchanged. |
| [Fix Inflections](./Drawing/Fix%20Inflections.py) | Removes inflections by shortening a control handle, keeping on-curve points and endpoint tangent directions fixed. Segments that cannot be repaired this way are left alone. Hold **Option** when running to process all masters. | Highlighted characters in Edit View; displayed layers by default. |
| [Old Print](./Drawing/Old%20Print.py) | Creates an irregular printed appearance with corner rounding, wonkiness, detail, unevenness, and optional smoothing. Includes reusable presets and a temporary preview that is committed with Confirm or discarded when the panel closes. | Selected layers, or the first selected layer; Font View selection uses the current master. |
| [Symmetrify KP](./Drawing/Symmetrify%20KP.py) | Applies reflection or rotational symmetry, including fivefold symmetry where the node structure permits it. Selecting at least two nodes on a path limits that path’s operation to those nodes; otherwise complete paths are used. | First selected layer. |
| [Symmetrify Selected Nodes in All Masters KP](./Drawing/Symmetrify%20Selected%20Nodes%20in%20All%20Masters%20KP.py) | Applies symmetry to corresponding selected nodes across masters. Select at least two nodes on the same path; masters must have corresponding paths and nodes. | All masters of the active glyph. |
| [Unround Corner](./Drawing/Unround%20Corner.py) | Replaces one rounded cubic corner with a sharp corner at the intersection of its adjoining tangents. Select exactly the two on-curve nodes at the ends of the rounded segment. | Selected corner in the active layer. |

### Layers

| Script | What it does | Scope |
| --- | --- | --- |
| [Clear Background Layers](./Layers/Clear%20Background%20Layers.py) | Removes background contents, including paths, components, anchors, and guides. | **All layers of every glyph in the font.** |
| [Save Backup Layer](./Layers/Save%20Backup%20Layer.py) | Duplicates the first selected layer as a timestamped backup layer associated with the same master. | First selected layer; adds a layer inside the font. |

### Production

| Script | What it does | Scope |
| --- | --- | --- |
| [Export Package Builder](./Production/Export%20Package%20Builder.py) | Builds a configurable package with Desktop, Web, and Variable folders. Offers static OTF/TTF, web WOFF/WOFF2, and variable TTF/WOFF2 exports. | Export instances; active instances by default. Writes files to a chosen destination. |
| [Set Export Names Based on Family Name](./Production/Set%20Export%20Names%20Based%20on%20Family%20Name.py) | Generates default family names, full names, PostScript names, filenames, export folders, and variable prefixes from the family name. Handles trial designations, duplicate names, and long names automatically. | All export instances, including inactive ones; updates naming settings without exporting or saving. |
| [Set Family Alignment](./Production/Set%20Family%20Alignment.py) | Copies the active master’s alignment zones into the font’s `Family Alignment Zones` custom parameter. | Font-level custom parameter. |

### Proofing

| Script | What it does | Scope |
| --- | --- | --- |
| [Check Vertical Disalignments](./Proofing/Check%20Vertical%20Disalignments.py) | Finds on-curve nodes within 3 units of vertical metrics or related alignment-zone edges, excluding exact hits by default. Opens matching glyphs and prints a detailed report; component outlines are checked using decomposed copies where available. | Whole font, current master; leaves outlines unchanged. |
| [Generate Samples in All Masters](./Proofing/Generate%20Samples%20in%20All%20Masters.py) | Opens sample text for multiple masters together in one tab. Choose which masters to show, reorder them, and use shared or individual sample strings. | Proofing tab using existing master layers. |

### Show

| Script | What it does | Scope |
| --- | --- | --- |
| [Open All Drawn Glyphs](./Show/Open%20All%20Drawn%20Glyphs.py) | Opens drawn, exporting glyphs in sections for basic letters, extended letters, numbers, punctuation, and symbols. Excludes spaces, standalone marks, and the fraction slash. | Whole font, current master; leaves outlines unchanged. |

### Spacing & Kerning

| Script | What it does | Scope |
| --- | --- | --- |
| [Apply/Remove Kern Pairs Globally](./Spacing%20%26%20Kerning/Apply%3ARemove%20Kern%20Pairs%20Globally.py) | Copies the current pair’s kerning value from the active master to all masters, or removes that pair from the current master or all masters. | Current left-to-right pair; may affect kerning groups. |
| [Assign Uppercase Kerning Groups to Small Caps](./Spacing%20%26%20Kerning/Assign%20UC%20Kern%20Groups%20to%20Small%20Caps.py) | Derives `.sc` kerning groups from each small cap’s uppercase counterpart. For example, an uppercase group `H` becomes `h.sc`; a missing source group clears the corresponding small-cap group. | All glyphs whose names end in `.sc`. |
| [Copy Kerning From Source Pair](./Spacing%20%26%20Kerning/Copy%20Kerning%20from%20Source%20Pair.py) | Copies kerning from a typed source pair to the current Edit View pair, with an optional positive or negative adjustment. Uses target groups where available and glyph-level keys otherwise. | Current master or all masters; all masters enabled by default. |
| [Reduce Metrics by 10% — All Masters](./Spacing%20%26%20Kerning/Reduce%20Metrics%2010%20Percent.py) | Multiplies both sidebearings by 0.9 and rounds down to whole units. Adjusts spacing rather than scaling outlines. | All masters of selected glyphs. |
| [Show Glyphs Missing Kern Groups](./Spacing%20%26%20Kerning/Show%20Glyphs%20Missing%20Kern%20Groups.py) | Opens exporting glyphs that lack a left or right kerning group. Unlike the version in Diacritics, this skips non-exporting glyphs. | Whole font; displays the current master. |
| [Show Positive Kern Pairs](./Spacing%20%26%20Kerning/Show%20Positive%20Kern%20Pairs.py) | Opens stored kerning pairs with positive values in a new tab, using representative glyphs for group pairs. | Current master; leaves kerning unchanged. |

### Variable Fonts

| Script | What it does | Scope |
| --- | --- | --- |
| [Font Axes Player](./Variable%20Fonts/Font%20Axes%20Player.py) | Animates the Font Axes sliders in the active Edit tab. Choose axes and playback speed, pause at a preview, or restore the preview captured when the panel opened. | Interpolation preview only; leaves masters, instances, and outlines unchanged. |

## Production workflows

### Generate names from one family name

Set the family name in **Font Info → Font**, then run **Set Export Names Based on Family Name**. The script uses existing instance style names and native variable export types to generate the remaining default names.

Trial exports are recognized by an existing **UNLICENSED TRIAL** family designation. That designation survives subsequent family renames. Explicit translations are preserved; the script manages default-language names.

For example, with the family `Example Sans`:

| Export | Generated filename, before the extension |
| --- | --- |
| Static Regular | `Example-Sans-Regular` |
| Trial static Regular | `Example-Sans-Regular-UNLICENSED-TRIAL` |
| Single retail variable export | `Example-Sans-Variable` |
| Single trial variable export | `Example-Sans-Variable-UNLICENSED-TRIAL` |

When several variable exports share a retail or trial category, their style names distinguish the filenames. Additional collisions receive numeric suffixes. Overlong machine names are shortened with a stable hash suffix.

### Build a delivery package

Use **Export Package Builder** for configurable desktop, web, and variable delivery. Choose a destination, select formats, and configure the package and subfolder names. Variable output requires a Variable Font Setting in Font Info’s Exports section; variable WOFF2 is attempted as an optional export.

Use **Approximate Type Package Builder** for static deliveries containing complete-family and individual-style folders, each with a ZIP archive. It uses lowercase folder names, joins family-name words, hyphenates style-name words, and omits a leading `AT` family prefix. Exported font filenames are preserved.

Both builders have replacement options. The general builder can replace its named package; the Approximate Type builder can replace the destination’s `desktop` and `web` folders.

## Experimental tools

These scripts live in **In Progress**. Their behaviour and interfaces are still being developed; use a working copy of the font when trying them.

| Script | What it does | Scope |
| --- | --- | --- |
| [Build Rough Draft](./In%20Progress/Build%20Rough%20Draft.py) | Builds rough Latin letterforms from a progressively unlocked source set, starting with glyphs such as `H`, `O`, and `h`. More letters become available as their source glyphs are drawn or generated. The panel can also clear generated targets. | Chosen target glyphs, in the current master or all masters; creates or replaces outlines. |
| [Optical Glyph Scaler](./In%20Progress/Optical%20Glyph%20Scaler.py) | Adjusts a glyph’s proportions with stroke-weight compensation and an overlay preview. Recalculates from a captured source rather than accumulating transformations; Apply commits the result. Requires unhinted outlines without components. | One glyph’s current master layer. |

## Credits

The Symmetrify tools are adapted from **Tim Ahrens / Just Another Foundry’s** [freemix-glyphsapp](https://github.com/justanotherfoundry/freemix-glyphsapp). Their source headers retain the original attribution and identify the upstream project as GPL-2.0 licensed.

## Contact

Questions, bug reports, and suggestions are welcome at [mail@approxtype.com](mailto:mail@approxtype.com). For a bug report, include the script name, Glyphs version, what was selected, and any error message.
