# MenuTitle: Set Postscript Names for Exports

# -*- coding: utf-8 -*-
__doc__ = """
Updates localized familyNames, PostScript names, fileNames, and Export Folders for all instances.
If the font’s global family name changes, this re-generates the localized familyNames
for both “Unlicensed Trial” and “Variable” instances so they reflect the new base family.
"""

from GlyphsApp import INSTANCETYPEVARIABLE
import unicodedata
import re

font = Glyphs.font
if not font:
    print("No font open.")
    raise SystemExit


# ---------- helpers ----------

def sanitize_name(s, for_folder=False, keep_spaces=False):
    if not s:
        return ""

    # normalize accents, quotes etc.
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))  # remove accents

    # replace typographic quotes/apostrophes and underscores
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("_", "-").replace("'", "")  # remove apostrophes entirely

    # replace non-alphanumeric symbols with hyphens
    s = re.sub(r"[^A-Za-z0-9\s-]+", "-", s)

    # normalize spaces/hyphens
    s = s.strip()
    s = re.sub(r"\s+", " " if (for_folder or keep_spaces) else "-", s)
    s = re.sub(r"-+", "-", s).strip("-").strip()

    return s

def get_localized_family(instance):
    """Return localized or fallback family name safely."""
    fam = None
    if instance.properties:
        for prop in instance.properties:
            if prop.key == "familyNames" and prop.defaultValue:
                fam = prop.defaultValue
                break
    if not fam:
        try:
            fam = instance.customParameters["familyName"]
        except Exception:
            pass
    return fam or font.familyName or ""


def is_trial_instance(instance):
    fam = get_localized_family(instance)
    return bool(re.search(r"unlicensed\s*trial", fam, re.IGNORECASE))


def is_variable_instance(instance):
    fam = get_localized_family(instance)
    return bool(re.search(r"\bvariable\b", fam, re.IGNORECASE))


# ---------- main ----------

updated_trials = 0
updated_variables = 0
updated_statics = 0

for instance in font.instances:
    family_name = get_localized_family(instance)
    style_name = instance.name or ""

    # detect
    is_trial = is_trial_instance(instance)
    is_variable = instance.type == INSTANCETYPEVARIABLE or is_variable_instance(instance)

    # --- build new family name depending on type ---
    base_family = sanitize_name(font.familyName, keep_spaces=True)

    if is_trial and is_variable:
        new_family_name = f"{base_family} UNLICENSED TRIAL Variable"
    elif is_trial:
        new_family_name = f"{base_family} UNLICENSED TRIAL"
    elif is_variable:
        new_family_name = f"{base_family} Variable"
    else:
        new_family_name = base_family

    # rebuild full + PS names
    full_name = sanitize_name(f"{new_family_name} {style_name}", keep_spaces=True)
    font_name = sanitize_name(full_name)

    # --- write localized + PS names ---
    instance.setProperty_value_languageTag_("postscriptFullNames", full_name, None)
    instance.fontName = font_name
    instance.customParameters["Export Folder"] = sanitize_name(new_family_name, for_folder=True)

    # fileName logic
    if is_variable and not is_trial:
        instance.customParameters["fileName"] = sanitize_name(f"{font.familyName}-Variable")
        instance.setProperty_value_languageTag_("familyNames", new_family_name, None)
    elif is_trial and not is_variable:
        instance.customParameters["fileName"] = sanitize_name(f"{font.familyName}-{style_name}-UNLICENSED-TRIAL")
        instance.setProperty_value_languageTag_("familyNames", new_family_name, None)
    elif is_trial and is_variable:
        instance.customParameters["fileName"] = sanitize_name(f"{font.familyName}-Variable-UNLICENSED-TRIAL")
        instance.setProperty_value_languageTag_("familyNames", new_family_name, None)
    else:
        instance.customParameters["fileName"] = sanitize_name(f"{font.familyName}-{style_name}")

    # --- set variable prefix (only for variables) ---
    if is_variable:
        prefix_base = re.sub(r"[\s-]+", "", font.familyName)
        variable_prefix = f"{prefix_base}Variable"
        instance.setProperty_value_languageTag_("variationsPostScriptNamePrefix", variable_prefix, None)

        instance.setProperty_value_languageTag_("styleMapFamilyNames", new_family_name, None)
        instance.setProperty_value_languageTag_("styleMapStyleNames", style_name, None)
        instance.setProperty_value_languageTag_("preferredFamilyNames", new_family_name, None)
        instance.setProperty_value_languageTag_("preferredSubfamilyNames", style_name, None)

    # count
    if is_trial and is_variable:
        updated_trials += 1
        updated_variables += 1
    elif is_trial:
        updated_trials += 1
    elif is_variable:
        updated_variables += 1
    else:
        updated_statics += 1


print(
    f"✅ Updated {updated_trials} trial, {updated_variables} variable, and {updated_statics} static instances.\n"
    f"All familyNames now reflect '{font.familyName}'."
)