from GlyphsApp import Glyphs, GSAlignmentZone, Message

font = Glyphs.font

if not font:
    Message("No font open", "Open a font first.")

else:
    master = font.selectedFontMaster

    zones = [
        GSAlignmentZone(zone.position, zone.size)
        for zone in master.alignmentZones
    ]

    if not zones:
        Message(
            "No Alignment Zones",
            f'The master "{master.name}" does not contain any alignment zones.'
        )

    else:
        font.customParameters["Family Alignment Zones"] = zones

        print(f'Family Alignment Zones copied from: {master.name}')

        for zone in zones:
            print(f'  {zone.position:g}, {zone.size:g}')

        Glyphs.showNotification(
            font.familyName,
            f'Family Alignment Zones copied from {master.name}'
        )