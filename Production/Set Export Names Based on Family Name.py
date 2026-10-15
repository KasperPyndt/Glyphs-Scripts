# MenuTitle: Set Export Names Based on Family Name
# -*- coding: utf-8 -*-
"""
Generate export names from Font Info > Font > Family Name.

Uses each instance's existing style name, native export type, and UNLICENSED
TRIAL family designation. All instances, including inactive ones, are updated.
Display names retain Unicode; file and PostScript names use safe ASCII.
Existing translated names are preserved; this manages the default language.
Does not export or save the font.
"""

from collections import Counter
import hashlib
import re
import unicodedata

from GlyphsApp import Glyphs, INSTANCETYPEVARIABLE


PS_NAME_LIMIT = 63
PREFIX_LIMIT = 40  # Leave room for generated variation coordinates/style names.
FILE_NAME_LIMIT = 180  # Leave room for file extensions and collision suffixes.
TRIAL_PATTERN = re.compile(r"\bunlicensed[\s_-]*trial\b", re.IGNORECASE)
TRANSLITERATION = str.maketrans({
    "Æ": "AE", "æ": "ae", "Ø": "O", "ø": "o", "Œ": "OE", "œ": "oe",
    "Ð": "D", "ð": "d", "Þ": "Th", "þ": "th", "Ł": "L", "ł": "l",
    "ß": "ss", "ẞ": "SS",
})


def display_name(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(value or ""))).strip()


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def ascii_name(value, keep_spaces=False):
    """Sanitize machine names without changing the display name."""
    text = unicodedata.normalize("NFKD", value.translate(TRANSLITERATION))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"['’‘]", "", text)
    text = re.sub(r"[^A-Za-z0-9\s-]+", "-", text)
    text = re.sub(r"\s+", " " if keep_spaces else "-", text)
    text = re.sub(r"-+", "-", text).strip(" -")
    return text or "Font-" + digest(value)


def shorten(value, limit, separator="-"):
    if len(value) <= limit:
        return value
    suffix = separator + digest(value)
    return value[:limit - len(suffix)].rstrip(" -") + suffix


def unique_name(value, used, limit, separator="-"):
    """Resolve collisions deterministically in font instance order."""
    candidate = shorten(value, limit, separator)
    number = 2
    while candidate.casefold() in used:
        suffix = separator + str(number)
        candidate = shorten(value, limit - len(suffix), separator) + suffix
        number += 1
    used.add(candidate.casefold())
    return candidate


def get_family(instance, base_family):
    # The native accessor avoids depending on internal property object fields.
    return (
        instance.defaultPropertyForName_("familyNames")
        or instance.customParameters["familyName"]
        or base_family
    )


def build_plan(font):
    """Read and validate every proposed name before the first font mutation."""
    base_family = display_name(font.familyName)
    if not base_family:
        raise ValueError("Enter a Family Name in Font Info before running this script.")

    rows = []
    for instance in font.instances:
        old_family = str(get_family(instance, base_family))
        rows.append({
            "instance": instance,
            "style": display_name(instance.name) or "Regular",
            "trial": bool(TRIAL_PATTERN.search(old_family)),
            "variable": instance.type == INSTANCETYPEVARIABLE,
        })

    variable_counts = Counter(row["trial"] for row in rows if row["variable"])
    used_ps_names, used_prefixes = set(), set()
    used_files = {}
    family_file = ascii_name(base_family)
    family_folder = ascii_name(base_family, keep_spaces=True)

    for row in rows:
        style, trial, variable = row["style"], row["trial"], row["variable"]
        family = base_family
        folder = family_folder
        if trial:
            family += " UNLICENSED TRIAL"
            folder += " UNLICENSED TRIAL"
        if variable:
            family += " Variable"
            folder += " Variable"

        full_name = family + " " + style
        # Build from separately sanitized tokens so non-Latin families retain
        # a stable, family-specific fallback rather than collapsing to a style.
        ps_parts = [family_file]
        if trial:
            ps_parts.append("UNLICENSED-TRIAL")
        if variable:
            ps_parts.append("Variable")
        ps_parts.append(ascii_name(style))

        file_parts = [family_file]
        if variable:
            file_parts.append("Variable")
            if variable_counts[trial] > 1:
                file_parts.append(ascii_name(style))
        else:
            file_parts.append(ascii_name(style))
        if trial:
            file_parts.append("UNLICENSED-TRIAL")

        folder = shorten(folder, FILE_NAME_LIMIT)
        row.update({
            "family": family,
            "full_name": full_name,
            "folder": folder,
            "ps_name": unique_name("-".join(ps_parts), used_ps_names, PS_NAME_LIMIT),
            "file_name": unique_name(
                "-".join(file_parts),
                used_files.setdefault(folder.casefold(), set()),
                FILE_NAME_LIMIT,
            ),
        })
        if variable:
            prefix = re.sub(r"[^A-Za-z0-9]", "", family_file)
            if trial:
                prefix += "UNLICENSEDTRIAL"
            prefix += "Variable"
            if variable_counts[trial] > 1:
                prefix += re.sub(r"[^A-Za-z0-9]", "", ascii_name(style))
            row["prefix"] = unique_name(prefix, used_prefixes, PREFIX_LIMIT, separator="")
            # Name ID 2 follows style linking, not an arbitrary export label.
            row["mapped_style"] = (
                "Bold Italic" if instance_flag(row, "isBold") and instance_flag(row, "isItalic")
                else "Bold" if instance_flag(row, "isBold")
                else "Italic" if instance_flag(row, "isItalic")
                else "Regular"
            )

    validate_plan(rows)
    return base_family, rows


def instance_flag(row, name):
    return bool(getattr(row["instance"], name))


def validate_plan(rows):
    ps_names, files, prefixes = set(), set(), set()
    for row in rows:
        ps_name = row["ps_name"]
        if not re.fullmatch(r"[A-Za-z0-9-]{1,63}", ps_name):
            raise ValueError("Invalid PostScript name: " + ps_name)
        file_key = (row["folder"].casefold(), row["file_name"].casefold())
        if ps_name.casefold() in ps_names or file_key in files:
            raise ValueError("Duplicate export name for " + row["style"])
        ps_names.add(ps_name.casefold())
        files.add(file_key)
        if row["variable"]:
            prefix = row["prefix"]
            if not re.fullmatch(r"[A-Za-z0-9]+", prefix) or prefix.casefold() in prefixes:
                raise ValueError("Invalid or duplicate variable prefix: " + prefix)
            prefixes.add(prefix.casefold())


def apply_plan(rows):
    for row in rows:
        instance = row["instance"]
        set_property = instance.setProperty_value_languageTag_
        set_property("familyNames", row["family"], None)
        set_property("postscriptFullNames", row["full_name"], None)
        set_property("preferredFamilyNames", row["family"], None)
        set_property("preferredSubfamilyNames", row["style"], None)
        instance.fontName = row["ps_name"]
        instance.customParameters["Export Folder"] = row["folder"]
        instance.customParameters["fileName"] = row["file_name"]
        # Keep legacy overrides consistent when a source still has them.
        if instance.customParameters["familyName"] is not None:
            instance.customParameters["familyName"] = row["family"]
        if row["variable"]:
            set_property("variationsPostScriptNamePrefix", row["prefix"], None)
            set_property("styleMapFamilyNames", row["family"], None)
            set_property("styleMapStyleNames", row["mapped_style"], None)


def main():
    font = Glyphs.font
    if font is None:
        print("No font open.")
        return
    try:
        base_family, rows = build_plan(font)
    except ValueError as error:
        print("No names changed: " + str(error))
        return

    apply_plan(rows)
    for row in rows:
        print("{}: {} / {}  [PS: {}]".format(
            row["style"], row["folder"], row["file_name"], row["ps_name"]
        ))
    trials = sum(row["trial"] for row in rows)
    variables = sum(row["variable"] for row in rows)
    print("Updated {} exports for '{}': {} static, {} variable; {} trial exports included.".format(
        len(rows), base_family, len(rows) - variables, variables, trials
    ))


if __name__ == "__main__":
    main()
