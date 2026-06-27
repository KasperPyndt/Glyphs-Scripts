#MenuTitle: Open RMX Harmonizer
# -*- coding: utf-8 -*-

from __future__ import print_function

from AppKit import NSApp
from GlyphsApp import Message


MENU_TITLE = "RMX Harmonizer"


def find_menu_item(menu, title):
	for item in menu.itemArray():
		if item.title() == title:
			return item

		submenu = item.submenu()
		if submenu is not None:
			found_item = find_menu_item(submenu, title)
			if found_item is not None:
				return found_item

	return None


main_menu = NSApp.mainMenu()
menu_item = find_menu_item(main_menu, MENU_TITLE) if main_menu is not None else None

if menu_item is None:
	Message(
		title="Open RMX Harmonizer",
		message='Could not find the "%s" menu item. Is RMX Harmonizer installed and loaded?' % MENU_TITLE,
		OKButton="OK",
	)
else:
	NSApp.sendAction_to_from_(menu_item.action(), menu_item.target(), menu_item)
	print('Opened "%s".' % MENU_TITLE)
