# MenuTitle: Open All Drawn Glyphs
# -*- coding: utf-8 -*-

"""Open a tab of drawn, exporting glyphs grouped into useful sections."""

from GlyphsApp import Glyphs, Message
import unicodedata


def unicode_character(glyph):
    """Return the glyph's first Unicode character, if it has one."""
    if not glyph.unicode:
        return None

    try:
        return chr(int(glyph.unicode, 16))
    except (TypeError, ValueError):
        return None


def unicode_category(glyph):
    character = unicode_character(glyph)
    return unicodedata.category(character) if character else ""


def has_content_in_master(glyph, master_id):
    """Only count paths and components in the selected master layer."""
    layer = glyph.layers[master_id]
    return bool(layer and (len(layer.paths) or len(layer.components)))


def is_space(glyph):
    return glyph.category == "Separator" or unicode_category(glyph).startswith("Z")


def is_independent_mark(glyph):
    return glyph.category == "Mark" or unicode_category(glyph).startswith("M")


def is_fraction_character(glyph):
    return glyph.name == "fraction" or unicode_character(glyph) == "\u2044"


def is_basic_letter(glyph):
    character = unicode_character(glyph)
    return bool(
        character
        and len(character) == 1
        and ("A" <= character <= "Z" or "a" <= character <= "z")
    )


def is_basic_number(glyph):
    character = unicode_character(glyph)
    return bool(character and len(character) == 1 and "0" <= character <= "9")


OVERVIEW_CATEGORIES = ("Letter", "Number", "Punctuation", "Symbol")


def is_overview_category(glyph, category, unicode_prefix):
    """Prefer Glyphs' overview category; use Unicode only as a fallback."""
    if glyph.category in OVERVIEW_CATEGORIES:
        return glyph.category == category
    return unicode_category(glyph).startswith(unicode_prefix)


def is_letter(glyph):
    """Include remaining letters in the diacritical/extended-letter section."""
    return is_overview_category(glyph, "Letter", "L")


def is_number(glyph):
    return is_overview_category(glyph, "Number", "N")


def is_punctuation(glyph):
    return is_overview_category(glyph, "Punctuation", "P")


def is_symbol(glyph):
    return is_overview_category(glyph, "Symbol", "S")


def tab_text(glyphs):
    return "".join("/%s" % glyph.name for glyph in glyphs)


font = Glyphs.font

if not font:
    Message("No Font Open", "Please open a font and run the script again.")
else:
    master = font.selectedFontMaster

    eligible_glyphs = [
        glyph
        for glyph in font.glyphs
        if glyph.export
        and not is_space(glyph)
        and not is_independent_mark(glyph)
        and not is_fraction_character(glyph)
        and has_content_in_master(glyph, master.id)
    ]

    basic_by_character = {}
    for glyph in eligible_glyphs:
        character = unicode_character(glyph)
        if (is_basic_letter(glyph) or is_basic_number(glyph)) and character not in basic_by_character:
            basic_by_character[character] = glyph

    # Show A-Z, a-z, and 0-9 on separate lines.
    uppercase_glyphs = [
        basic_by_character[character]
        for character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if character in basic_by_character
    ]
    lowercase_glyphs = [
        basic_by_character[character]
        for character in "abcdefghijklmnopqrstuvwxyz"
        if character in basic_by_character
    ]
    basic_number_glyphs = [
        basic_by_character[character]
        for character in "0123456789"
        if character in basic_by_character
    ]
    basic_glyphs = uppercase_glyphs + lowercase_glyphs + basic_number_glyphs
    used_names = set(glyph.name for glyph in basic_glyphs)

    def take_unused_glyphs(predicate):
        """Assign every glyph to no more than one output section."""
        matches = []
        for glyph in eligible_glyphs:
            if glyph.name not in used_names and predicate(glyph):
                matches.append(glyph)
                used_names.add(glyph.name)
        return matches

    # Iterating eligible_glyphs preserves the order shown in the font overview.
    diacritical_glyphs = take_unused_glyphs(
        lambda glyph: not is_basic_letter(glyph) and is_letter(glyph)
    )
    number_glyphs = take_unused_glyphs(
        lambda glyph: not is_basic_number(glyph) and is_number(glyph)
    )
    punctuation_glyphs = take_unused_glyphs(is_punctuation)
    symbol_glyphs = take_unused_glyphs(is_symbol)

    basic_section = "\n".join(
        tab_text(group)
        for group in (uppercase_glyphs, lowercase_glyphs, basic_number_glyphs)
        if group
    )

    sections = [
        basic_section,
        tab_text(diacritical_glyphs),
        tab_text(number_glyphs),
        tab_text(punctuation_glyphs),
        tab_text(symbol_glyphs),
    ]
    output = "\n\n".join(section for section in sections if section)

    if output:
        font.newTab(output)
    else:
        Message(
            "No Drawn Glyphs Found",
            "No exporting glyphs with paths or components were found in the selected master.",
        )
