# Glyphs Scripts

Python scripts by Kasper Pyndt (Approximate Type) for drawing, spacing, proofing, and producing fonts in [Glyphs 4](https://glyphsapp.com/). This collection brings together small everyday utilities and tools for working across masters, preparing exports, and exploring letterforms.

[Installation](#installation) — [Script catalogue](#script-catalogue) — [Production workflows](#production-workflows) — [Experimental tools](#experimental-tools) — [Contact](#contact)

<br>

## Installation

1. Download this repository using **Code → Download ZIP** on GitHub and unzip it, or clone it with Git.
2. In Glyphs, choose **Script → Open Scripts Folder**.
3. Copy the collection into that folder. Keep the category folders together to preserve their organization in the Script menu.
4. Hold **Option** and choose **Script → Reload Scripts**.

Many tools with a panel use **Vanilla**. Install the Python 3 runtime and Vanilla, if needed, from the **Modules** tab in Glyphs’ Plugin Manager. See the official [scripts guide](https://handbook.glyphsapp.com/scripts/) and [extension setup guide](https://glyphsapp.com/learn/extending-glyphs) for details.

<br>

## Script catalogue

- [Alignment](#alignment)
- [Anchors](#anchors)
- [Coherency](#coherency)
- [Colours](#colours)
- [Components](#components)
- [Copy Paste](#copy-paste)
- [Diacritics](#diacritics)
- [Drawing](#drawing)
- [Production](#production)
- [Proofing](#proofing)
- [Show](#show)
- [Spacing & Kerning](#spacing--kerning)
- [Variable Fonts](#variable-fonts)
- [Experimental tools](#experimental-tools)

<br>

### Alignment

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Alignment/Align%20to%20Horizontal%20Center.py">Align to Horizontal Center</a></td>
<td valign="top">Centers selected nodes, paths, components, or anchors within the existing width, accounting for italics. With no selection, centers all paths.</td>
<td valign="top">Selected layers.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Alignment/Align%20to%20Horizontal%20Center%20-%20All%20Masters.py">Align to Horizontal Center,<br>all masters</a></td>
<td valign="top">Centers each master’s drawn paths within its existing width, accounting for italics. Ignores selections.</td>
<td valign="top">All masters of selected glyphs.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Alignment/Align%20to%20Vertical%20Center.py">Align to Vertical Center</a></td>
<td valign="top">Centers selected geometry between baseline and cap height. With no selection, moves the whole layer.</td>
<td valign="top">Selected layers.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Alignment/Align%20to%20Vertical%20Center%20-%20All%20Masters.py">Align to Vertical Center,<br>all masters</a></td>
<td valign="top">Centers each master’s whole foreground between baseline and cap height.</td>
<td valign="top">All masters of selected glyphs.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Alignment/Align%20to%20Vertical%20Center%20of%20Hyphen.py">Align to Vertical Center<br>of Hyphen</a></td>
<td valign="top">Matches each selected layer’s vertical center to the hyphen in the same master.</td>
<td valign="top">Selected layers; requires a drawn <code>hyphen</code>.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Alignment/Center%20Anchor%20to%20Selection.py">Center Anchor to Selection</a></td>
<td valign="top">Centers one selected anchor within the bounds of at least two selected nodes or one component.</td>
<td valign="top">First selected layer.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Alignment/Equalise%20sidebearings.py">Equalise sidebearings</a></td>
<td valign="top">Equalises left and right sidebearings by shifting the drawn shapes; preserves advance width.</td>
<td valign="top">Selected layers.</td>
</tr>
</tbody>
</table>

### Anchors

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Anchors/Move%20Anchor%20in%20All%20Masters.py">Move Anchor<br>in All Masters 2</a></td>
<td valign="top">Moves the selected anchor by a specified amount wherever it exists. Vertical moves follow each master’s italic angle.</td>
<td valign="top">All masters of selected glyphs.</td>
</tr>
</tbody>
</table>

### Coherency

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Coherency/Show%20Relatives.py">Show Possible Relatives</a></td>
<td valign="top">Shows structural relatives, English sample words, or all relative groups. Replaces the current tab text, or opens a new tab.</td>
<td valign="top">Proofing text; leaves outlines unchanged.</td>
</tr>
</tbody>
</table>

### Colours

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Colours/Glyph%20Colouriser.py">Glyph Colouriser</a></td>
<td valign="top">Colours glyphs by construction: paths, components, mixed, or non-exporting. Non-exporting takes priority; empty exporting glyphs are skipped.</td>
<td valign="top">Glyph colours across the whole font.</td>
</tr>
</tbody>
</table>

### Components

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Components/Disable%20Automatic%20Alignment%20for%20Components.py">Disable Auto Alignment<br>for Components<br>in Selected Glyphs</a></td>
<td valign="top">Disables component auto-alignment for manual positioning.</td>
<td valign="top">All masters of selected glyphs.</td>
</tr>
</tbody>
</table>

### Copy Paste

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Copy%20Paste/Copy%20Word%20as%20Vectors.py">Copy Selection as Vectors</a></td>
<td valign="top">Copies displayed text as editable Illustrator/InDesign vectors, preserving placement. Text-tool selection defines the copy; otherwise copies the whole tab.</td>
<td valign="top">Clipboard only; leaves the font unchanged.</td>
</tr>
</tbody>
</table>

### Diacritics

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Diacritics/Show%20Glyphs%20Using%20Selected%20Diacritic.py">Show Glyphs Using<br>Selected Diacritic</a></td>
<td valign="top">Opens glyphs that directly use the first selected glyph as a component in any master. Works with any component source.</td>
<td valign="top">Searches all glyphs’ master layers; leaves outlines unchanged.</td>
</tr>
</tbody>
</table>

### Drawing

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Drawing/Clear%20Selected%20Glyphs.py">Clear Selected Glyphs</a></td>
<td valign="top">Clears artwork, anchors, guides, annotations, and backgrounds in the current master or all masters.</td>
<td valign="top">Glyphs selected in Font View.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Drawing/Find%20Inflections.py">Find Inflections</a></td>
<td valign="top">Opens glyphs with true cubic Bézier inflections. Checks paths without decomposing components.</td>
<td valign="top">Whole font, current master; leaves outlines unchanged.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Drawing/Fix%20Inflections.py">Fix Inflections</a></td>
<td valign="top">Removes inflections by shortening a handle while preserving on-curve points and tangent directions. Leaves unrepairable segments unchanged. Hold <strong>Option</strong> for all masters.</td>
<td valign="top">Highlighted characters in Edit View; displayed layers by default.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Drawing/Old%20Print.py">Old Print</a></td>
<td valign="top">Simulates irregular print with rounding, wonkiness, detail, unevenness, and optional smoothing.</td>
<td valign="top">Selected layers.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Drawing/Unround%20Corner.py">Unround Corner</a></td>
<td valign="top">Replaces a rounded cubic corner with the intersection of its adjoining tangents. Select exactly the two endpoint on-curve nodes.</td>
<td valign="top">Selected corner in the active layer.</td>
</tr>
</tbody>
</table>

### Production

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Production/Export%20Package%20Builder.py">Export Package Builder</a></td>
<td valign="top">Builds configurable Desktop, Web, and Variable folders with OTF/TTF, WOFF/WOFF2, and variable TTF/WOFF2 output.</td>
<td valign="top">Export instances; active instances by default.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Production/Set%20Export%20Names%20Based%20on%20Family%20Name.py">Set Export Names<br>Based on Family Name</a></td>
<td valign="top">Generates family, full, PostScript, file, folder, and variable-prefix names from the family name. Handles trials, duplicates, and name-length limits.</td>
<td valign="top">All export instances, including inactive ones; updates naming settings.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Production/Set%20Family%20Alignment.py">Set Family Alignment</a></td>
<td valign="top">Copies the active master’s alignment zones to the font’s <code>Family Alignment Zones</code> custom parameter.</td>
<td valign="top">Font-level custom parameter.</td>
</tr>
</tbody>
</table>

### Proofing

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Proofing/Check%20Vertical%20Disalignments.py">Check Vertical<br>Disalignments</a></td>
<td valign="top">Finds on-curve nodes within 3 units of metrics or zone edges, excluding exact hits. Opens matches and prints a report; checks decomposed component copies where available.</td>
<td valign="top">Whole font, current master; leaves outlines unchanged.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Proofing/Generate%20Samples%20in%20All%20Masters.py">Generate Samples<br>in All Masters</a></td>
<td valign="top">Shows multiple masters’ sample text in one tab, with master selection, ordering, and shared or individual strings.</td>
<td valign="top">Proofing tab using existing master layers.</td>
</tr>
</tbody>
</table>

### Show

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Show/Open%20All%20Drawn%20Glyphs.py">Open All Drawn Glyphs</a></td>
<td valign="top">Groups drawn, exporting glyphs into basic letters, extended letters, numbers, punctuation, and symbols. Excludes spaces, standalone marks, and the fraction slash.</td>
<td valign="top">Whole font, current master; leaves outlines unchanged.</td>
</tr>
</tbody>
</table>

### Spacing & Kerning

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Spacing%20%26%20Kerning/Apply%3ARemove%20Kern%20Pairs%20Globally.py">Apply/Remove Kern Pairs<br>Globally</a></td>
<td valign="top">Copies the active master’s current pair value to all masters, or removes the pair from the current master or all masters.</td>
<td valign="top">Current left-to-right pair; may affect kerning groups.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Spacing%20%26%20Kerning/Assign%20UC%20Kern%20Groups%20to%20Small%20Caps.py">Assign Uppercase<br>Kerning Groups<br>to Small Caps</a></td>
<td valign="top">Derives <code>.sc</code> groups from uppercase counterparts: <code>H</code> becomes <code>h.sc</code>. Clears the corresponding small-cap group when the source group is missing.</td>
<td valign="top">All glyphs whose names end in <code>.sc</code>.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Spacing%20%26%20Kerning/Copy%20Kerning%20from%20Source%20Pair.py">Copy Kerning<br>From Source Pair</a></td>
<td valign="top">Copies a typed source pair’s kerning to the current Edit View pair, with an optional adjustment. Doesn't apply the source pairs kern groups, only applies values.</td>
<td valign="top">Current master or all masters; all masters enabled by default.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Spacing%20%26%20Kerning/Show%20Glyphs%20Missing%20Kern%20Groups.py">Show Glyphs Missing<br>Kern Groups</a></td>
<td valign="top">Opens exporting glyphs missing either kerning group.</td>
<td valign="top">Whole font; displays the current master.</td>
</tr>
<tr>
<td valign="top" nowrap><a href="./Spacing%20%26%20Kerning/Show%20Positive%20Kern%20Pairs.py">Show Positive Kern Pairs</a></td>
<td valign="top">Opens stored positive kerning pairs, choosing representative glyphs for group pairs.</td>
<td valign="top">Current master; leaves kerning unchanged.</td>
</tr>
</tbody>
</table>

### Variable Fonts

<table width="100%">
<thead>
<tr>
<th width="35%" align="left">Script</th>
<th width="45%" align="left">What it does</th>
<th width="20%" align="left">Scope</th>
</tr>
</thead>
<tbody>
<tr>
<td valign="top" nowrap><a href="./Variable%20Fonts/Font%20Axes%20Player.py">Font Axes Player</a></td>
<td valign="top">Animates selected Font Axes sliders in the active Edit tab at a chosen speed. Pause holds the preview; Restore returns to the opening preview.</td>
<td valign="top">Interpolation preview only; leaves masters, instances, and outlines unchanged.</td>
</tr>
</tbody>
</table>

<br>

## Production workflows

<br>

### Generate names from one family name

Set the family name in **Font Info → Font**, then run **Set Export Names Based on Family Name**. The script uses existing instance style names and native variable export types to generate the remaining default names.

Trial exports are recognized by an existing **UNLICENSED TRIAL** family designation. That designation survives subsequent family renames. Explicit translations are preserved; the script manages default-language names.

For example, with the family `Example Sans`:

| Export | Generated filename, before the extension |
| --- | --- |
| Regular | `Example-Sans-Regular` |
| Regular Trial | `Example-Sans-Regular-UNLICENSED-TRIAL` |
| Variable Font | `Example-Sans-Variable` |
| Variable Font Trial | `Example-Sans-Variable-UNLICENSED-TRIAL` |

<br>

### Build an export package

Use **Export Package Builder** for configurable desktop, web, and variable font file delivery. Choose a destination, select formats, and configure the package and subfolder names. Variable output requires a Variable Font Setting in Font Info’s Exports section; variable WOFF2 is attempted as an optional export.

<br>

## Contact

Questions, bug reports, and suggestions are welcome at [mail@approxtype.com](mailto:mail@approxtype.com). For a bug report, include the Glyphs version, what was selected, and any error message.

Thanks a lot! 😊
