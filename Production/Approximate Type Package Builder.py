# MenuTitle: Approximate Type Package Builder
# -*- coding: utf-8 -*-
"""
Build an Approximate Type desktop/web delivery for the frontmost Glyphs 3 font.

The export engine and the Vanilla window controller are intentionally separate,
following Export Package Builder. The delivery format is fixed:

	web/
		typefacename-complete/          all active styles as WOFF2
		typefacename-complete.zip
		typefacename-regular/           Regular as WOFF2
		typefacename-regular.zip
		typefacename-regular-italic/    Regular Italic as WOFF2
		typefacename-regular-italic.zip
		...
	desktop/
		typefacename-complete/          all active styles as OTF
		typefacename-complete.zip
		typefacename-regular/           Regular as OTF
		typefacename-regular.zip
		typefacename-regular-italic/    Regular Italic as OTF
		typefacename-regular-italic.zip
		...

Every generated folder name is lowercase. Family-name words are joined
("Example Sans" becomes "examplesans"), while style-name words are hyphenated
("Regular Italic" becomes "regular-italic"). Font filenames are preserved
exactly as Glyphs exports them, including any `fileName` custom parameter.
An Approximate Type `AT` family prefix is omitted from folder names. Variable
Font Settings are not part of this static-font delivery.
"""

import os
import re
import shutil
import traceback
import unicodedata
import uuid
import zipfile

from AppKit import NSFont, NSWorkspace
from Foundation import NSURL
from GlyphsApp import (
	GetFolder,
	Glyphs,
	INSTANCETYPESINGLE,
	Message,
	OTF,
	PLAIN,
	TTF,
	WOFF2,
)

try:
	import vanilla
except ImportError:
	vanilla = None


TITLE = "Approximate Type Package Builder"
PREF_DOMAIN = "com.atype.approximateTypePackageBuilder.directFolders"


class ExportPackageError(Exception):
	"""Base error shown to the user without an implementation traceback."""


class ExportFailedError(ExportPackageError):
	"""Raised when one or more required export operations fail."""

	def __init__(self, report):
		super().__init__("One or more exports failed.")
		self.report = report


class ExportOptions:
	"""Value object shared by the UI and the export engine."""

	def __init__(
		self,
		destination,
		active_only=True,
		replace_existing=True,
		reveal_result=True,
	):
		self.destination = destination
		self.active_only = bool(active_only)
		self.replace_existing = bool(replace_existing)
		self.reveal_result = bool(reveal_result)


class ExportReport:
	"""Collect output paths, recoverable warnings, and fatal export errors."""

	def __init__(self, package_path):
		self.package_path = package_path
		self.produced_files = []
		self.warnings = []
		self.errors = []

	def add_warning(self, message):
		self.warnings.append(message)

	def add_error(self, message):
		self.errors.append(message)


class ExportTask:
	"""One Glyphs instance/format/container operation."""

	def __init__(
		self,
		instance,
		style_name,
		style_key,
		kind,
		output_folder,
		outline_format,
		container,
		expected_extension,
	):
		self.instance = instance
		self.style_name = style_name
		self.style_key = style_key
		self.kind = kind
		self.output_folder = output_folder
		self.outline_format = outline_format
		self.container = container
		self.expected_extension = expected_extension.lower()

	@property
	def label(self):
		return "%s — %s %s" % (
			self.style_name,
			self.kind,
			self.expected_extension.lstrip(".").upper(),
		)


class ApproximateTypePackageBuilder:
	"""Reusable export and packaging engine."""

	def __init__(self, font, options, logger=print):
		self.font = font
		self.options = options
		self.log = logger

	def build(self):
		if not self.font:
			raise ExportPackageError("No font is open.")

		family = self._family_key(self.font.familyName)
		destination = self._normalized_destination(self.options.destination)
		report = ExportReport(destination)

		instances = self._eligible_instances()
		styles = self._validated_styles(instances)
		self._validate(destination)
		os.makedirs(destination, exist_ok=True)

		staging_name = ".approximate-type-package-%s" % uuid.uuid4().hex
		staging_path = os.path.join(destination, staging_name)
		os.mkdir(staging_path)
		raw_path = os.path.join(staging_path, ".exports")
		os.mkdir(raw_path)

		self.log(TITLE)
		self.log("Family: %s" % self.font.familyName)
		self.log("Delivery folder: %s" % destination)

		try:
			tasks = self._make_tasks(instances, styles, raw_path)
			if not tasks:
				report.add_error(
					"No eligible static instances were found. Enable at least one "
					"static instance in Font Info → Exports."
				)

			for task in tasks:
				self._run_task(task, family, staging_path, report)

			if not report.produced_files and not report.errors:
				report.add_error("No font files were produced.")

			if report.errors:
				raise ExportFailedError(report)

			shutil.rmtree(raw_path)
			self._zip_delivery_folders(staging_path, report)
			staged_files = list(report.produced_files)
			self._commit(staging_path, destination, report)
			report.produced_files = [
				os.path.join(
					destination,
					os.path.relpath(file_path, staging_path),
				)
				for file_path in staged_files
			]
			self.log("Completed: %i file(s)" % len(report.produced_files))
			return report
		except Exception:
			if os.path.isdir(staging_path):
				try:
					shutil.rmtree(staging_path)
				except Exception as cleanup_error:
					self.log(
						"Warning: could not remove failed staging folder: %s"
						% self._error_text(cleanup_error)
					)
			raise

	def _validate(self, destination):
		if not destination:
			raise ExportPackageError("Choose a destination folder.")
		if os.path.exists(destination) and not os.path.isdir(destination):
			raise ExportPackageError("The destination is not a folder.")

		existing_folders = []
		for folder_name in ("web", "desktop"):
			folder_path = os.path.join(destination, folder_name)
			if os.path.lexists(folder_path) and not os.path.isdir(folder_path):
				raise ExportPackageError(
					"A non-folder item already uses the required name:\n%s"
					% folder_path
				)
			if os.path.isdir(folder_path):
				existing_folders.append(folder_name)

		if existing_folders and not self.options.replace_existing:
			raise ExportPackageError(
				"The delivery already contains %s. Enable ‘Replace existing "
				"folders’ or choose another destination."
				% " and ".join(existing_folders)
			)

	def _eligible_instances(self):
		instances = [
			instance
			for instance in self.font.instances
			if instance.type == INSTANCETYPESINGLE
		]
		if self.options.active_only:
			instances = [
				instance for instance in instances if self._include_instance(instance)
			]
		return instances

	def _validated_styles(self, instances):
		styles = []
		for instance in instances:
			style_name = instance.name or ""
			style = self._style_key(style_name)
			if not style:
				raise ExportPackageError(
					"Every exported instance needs a style name containing at least "
					"one Latin letter or number."
				)
			if style == "complete":
				raise ExportPackageError(
					"An exported instance cannot be named Complete because the "
					"‘complete’ folder is reserved for the full family."
				)
			styles.append(style)

		return styles

	def _make_tasks(self, instances, styles, raw_path):
		tasks = []
		for index, (instance, style) in enumerate(zip(instances, styles)):
			style_name = instance.name or style
			instance_path = os.path.join(raw_path, "%03i" % index)
			for kind, outline_format, container, extension in (
				("desktop", OTF, PLAIN, ".otf"),
				("web", TTF, WOFF2, ".woff2"),
			):
				output_folder = os.path.join(instance_path, kind)
				os.makedirs(output_folder)
				tasks.append(
					ExportTask(
						instance,
						style_name,
						style,
						kind,
						output_folder,
						outline_format,
						container,
						extension,
					)
				)
		return tasks

	def _run_task(self, task, family, staging_path, report):
		self.log("Exporting %s…" % task.label)
		before = self._folder_snapshot(task.output_folder)

		try:
			result = task.instance.generate(
				format=task.outline_format,
				fontPath=task.output_folder,
				containers=[task.container],
			)
			result_errors = self._result_errors(result)
		except Exception as error:
			result_errors = [self._error_text(error)]

		after = self._folder_snapshot(task.output_folder)
		changed_files = self._changed_files(
			before,
			after,
			task.expected_extension,
		)

		if result_errors:
			message = "%s failed: %s" % (
				task.label,
				"; ".join(result_errors),
			)
			report.add_error(message)
			self.log("Error: %s" % message)
			return

		if len(changed_files) != 1:
			message = (
				"%s: Glyphs reported success but produced %i changed %s files; "
				"exactly one was expected."
				% (task.label, len(changed_files), task.expected_extension)
			)
			report.add_error(message)
			self.log("Error: %s" % message)
			return

		source_path = changed_files[0]
		filename = os.path.basename(source_path)
		complete_folder = os.path.join(
			staging_path,
			task.kind,
			"%s-complete" % family,
		)
		style_folder = os.path.join(
			staging_path,
			task.kind,
			"%s-%s" % (family, task.style_key),
		)

		for destination_folder in (complete_folder, style_folder):
			os.makedirs(destination_folder, exist_ok=True)
			destination_path = os.path.join(destination_folder, filename)
			shutil.copy2(source_path, destination_path)
			if destination_path not in report.produced_files:
				report.produced_files.append(destination_path)

		self.log("  %s" % filename)

	def _zip_delivery_folders(self, staging_path, report):
		for kind in ("web", "desktop"):
			kind_path = os.path.join(staging_path, kind)
			folder_names = sorted(
				name
				for name in os.listdir(kind_path)
				if os.path.isdir(os.path.join(kind_path, name))
			)
			for folder_name in folder_names:
				folder_path = os.path.join(kind_path, folder_name)
				archive_path = folder_path + ".zip"
				self.log("Creating %s/%s.zip…" % (kind, folder_name))
				with zipfile.ZipFile(
					archive_path,
					"w",
					compression=zipfile.ZIP_DEFLATED,
				) as archive:
					for root, directory_names, file_names in os.walk(folder_path):
						directory_names.sort()
						for file_name in sorted(file_names):
							file_path = os.path.join(root, file_name)
							archive.write(
								file_path,
								os.path.relpath(file_path, kind_path),
							)
				report.produced_files.append(archive_path)

	def _commit(self, staging_path, destination, report):
		folder_names = ("web", "desktop")
		backup_path = os.path.join(
			destination,
			".approximate-type-package-backup-%s" % uuid.uuid4().hex,
		)
		backed_up = []
		installed = []

		try:
			for folder_name in folder_names:
				target_path = os.path.join(destination, folder_name)
				if os.path.isdir(target_path):
					if not os.path.isdir(backup_path):
						os.mkdir(backup_path)
					os.replace(
						target_path,
						os.path.join(backup_path, folder_name),
					)
					backed_up.append(folder_name)

			for folder_name in folder_names:
				os.replace(
					os.path.join(staging_path, folder_name),
					os.path.join(destination, folder_name),
				)
				installed.append(folder_name)
		except Exception:
			for folder_name in installed:
				installed_path = os.path.join(destination, folder_name)
				if os.path.isdir(installed_path):
					shutil.rmtree(installed_path)
			for folder_name in backed_up:
				backup_folder = os.path.join(backup_path, folder_name)
				if os.path.isdir(backup_folder):
					os.replace(
						backup_folder,
						os.path.join(destination, folder_name),
					)
			raise
		finally:
			if os.path.isdir(staging_path):
				shutil.rmtree(staging_path)

		if os.path.isdir(backup_path):
			try:
				shutil.rmtree(backup_path)
			except Exception as error:
				report.add_warning(
					"The new delivery was built, but its hidden backup could not "
					"be removed: %s" % self._error_text(error)
				)

	def _include_instance(self, instance):
		active = getattr(instance, "active", None)
		if active is None:
			active = getattr(instance, "exports", True)
		return bool(active)

	@classmethod
	def _family_key(cls, family_name):
		if not family_name or not str(family_name).strip():
			raise ExportPackageError(
				"The current font needs a family name before it can be packaged."
			)
		name = cls._ascii_text(family_name).strip()
		if name == "AT":
			name = ""
		elif re.match(r"^AT[\s._-]+", name):
			name = re.sub(r"^AT[\s._-]+", "", name, count=1)
		elif (
			len(name) > 2
			and name.startswith("AT")
			and (name[2].isupper() or name[2].isdigit())
		):
			name = name[2:]

		key = re.sub(r"[^a-z0-9]+", "", name.lower())
		if not key:
			raise ExportPackageError(
				"The family name must contain a name after the AT prefix."
			)
		return key

	@classmethod
	def _style_key(cls, style_name):
		key = re.sub(
			r"[^a-z0-9]+",
			"-",
			cls._ascii_text(style_name).lower(),
		)
		return key.strip("-")

	@staticmethod
	def _ascii_text(value):
		value = unicodedata.normalize("NFKD", str(value or ""))
		return value.encode("ascii", "ignore").decode("ascii")

	@staticmethod
	def _normalized_destination(destination):
		if not destination:
			return ""
		return os.path.abspath(os.path.expanduser(destination.strip()))

	@staticmethod
	def _folder_snapshot(folder_path):
		snapshot = {}
		for root, _directories, file_names in os.walk(folder_path):
			for file_name in file_names:
				file_path = os.path.join(root, file_name)
				try:
					stat = os.stat(file_path)
					snapshot[file_path] = (stat.st_mtime_ns, stat.st_size)
				except OSError:
					pass
		return snapshot

	@staticmethod
	def _changed_files(before, after, extension):
		return sorted(
			file_path
			for file_path, signature in after.items()
			if file_path.lower().endswith(extension)
			and before.get(file_path) != signature
		)

	@classmethod
	def _result_errors(cls, result):
		if result is None or result is True or result == 1:
			return []
		if isinstance(result, (list, tuple)):
			errors = []
			for item in result:
				errors.extend(cls._result_errors(item))
			return errors
		return [cls._error_text(result)]

	@staticmethod
	def _error_text(error):
		text = str(error).strip()
		return text or error.__class__.__name__


class ApproximateTypePackageBuilderWindowController:
	"""Vanilla UI matching the workflow of Export Package Builder."""

	def __init__(self):
		self.font = Glyphs.font
		if not self.font:
			raise ExportPackageError(
				"Open a font in Glyphs, then run %s again." % TITLE
			)

		self.w = vanilla.FloatingWindow(
			(550, 258),
			TITLE,
			autosaveName=PREF_DOMAIN + ".window",
		)

		margin = 18
		label_width = 94
		field_left = margin + label_width

		self.w.destinationLabel = vanilla.TextBox(
			(margin, 16, label_width - 8, 20),
			"Destination:",
		)
		self.w.destination = vanilla.EditText(
			(field_left, 12, -112, 24),
			self._pref(
				"destination",
				os.path.join(
					os.path.expanduser("~/Desktop"),
					ApproximateTypePackageBuilder._family_key(self.font.familyName),
				),
			),
		)
		self.w.chooseButton = vanilla.Button(
			(-102, 12, -margin, 24),
			"Choose…",
			callback=self.choose_destination,
		)

		self.w.topLine = vanilla.HorizontalLine((margin, 50, -margin, 1))
		self.w.deliveryTitle = vanilla.TextBox(
			(margin, 68, label_width - 8, 20),
			"Delivery:",
		)
		self.w.deliverySummary = vanilla.TextBox(
			(field_left, 68, -margin, 42),
			"web: WOFF2   •   desktop: OTF\ncomplete + per-style folders, each with a matching ZIP archive",
		)

		self.w.optionsLine = vanilla.HorizontalLine((margin, 118, -margin, 1))
		self.w.activeOnly = vanilla.CheckBox(
			(margin, 134, 230, 20),
			"Export active instances only",
			value=self._pref("activeOnly", True),
		)
		self.w.replaceExisting = vanilla.CheckBox(
			(276, 134, -margin, 20),
			"Replace existing folders",
			value=self._pref("replaceExisting", True),
		)
		self.w.revealResult = vanilla.CheckBox(
			(margin, 162, 230, 20),
			"Reveal result in Finder",
			value=self._pref("revealResult", True),
		)

		self.w.progress = vanilla.ProgressBar(
			(margin, 192, -margin, 12),
			isIndeterminate=True,
			sizeStyle="small",
		)
		self.w.progress.show(False)
		self.w.status = vanilla.TextBox(
			(margin, 211, -172, 20),
			"Ready to build %s." % self.font.familyName,
		)
		self.w.buildButton = vanilla.Button(
			(-158, -38, -margin, 24),
			"Build Package",
			callback=self.build_package,
		)

		for headline in (
			self.w.destinationLabel,
			self.w.deliveryTitle,
		):
			self._make_bold(headline)
		self.w.setDefaultButton(self.w.buildButton)
		self.w.open()
		self.w.makeKey()

	def choose_destination(self, _sender):
		current_path = self.w.destination.get().strip()
		chosen_path = GetFolder(
			message="Choose the folder that should contain web and desktop",
			path=os.path.expanduser(current_path) if current_path else None,
		)
		if chosen_path:
			self.w.destination.set(chosen_path)

	def build_package(self, _sender):
		current_font = Glyphs.font
		if not current_font:
			self._show_error("No Font Open", "Open a font and try again.")
			return

		try:
			options = self._options_from_ui()
			self._save_preferences(options)
			self._set_busy(True, "Building %s…" % current_font.familyName)
			Glyphs.clearLog()

			report = ApproximateTypePackageBuilder(current_font, options).build()
			self._set_busy(
				False,
				"Built %i file(s) in %s."
				% (
					len(report.produced_files),
					os.path.basename(report.package_path),
				),
			)

			if options.reveal_result:
				try:
					self._reveal(report.package_path)
				except Exception as error:
					report.add_warning(
						"The package was built, but Finder could not reveal it: %s"
						% error
					)
			if report.warnings:
				self._print_report(report)
				self._show_warning_report(report)
			Glyphs.showNotification(
				TITLE,
				"Built %s with %i file(s)."
				% (current_font.familyName, len(report.produced_files)),
			)
		except ExportFailedError as error:
			self._set_busy(False, "The folders were not replaced; see the errors.")
			self._print_report(error.report)
			Glyphs.showMacroWindow()
			self._show_error(
				"Export Package Failed",
				self._compact_messages(error.report.errors),
			)
		except ExportPackageError as error:
			self._set_busy(False, str(error))
			self._show_error(TITLE, str(error))
		except Exception as error:
			self._set_busy(False, "Unexpected error; see the Macro window.")
			print(traceback.format_exc())
			Glyphs.showMacroWindow()
			self._show_error(
				"Unexpected Export Error",
				"%s\n\nDetails were printed in the Macro window." % error,
			)

	def _options_from_ui(self):
		return ExportOptions(
			destination=self.w.destination.get(),
			active_only=self.w.activeOnly.get(),
			replace_existing=self.w.replaceExisting.get(),
			reveal_result=self.w.revealResult.get(),
		)

	def _save_preferences(self, options):
		values = {
			"destination": options.destination,
			"activeOnly": options.active_only,
			"replaceExisting": options.replace_existing,
			"revealResult": options.reveal_result,
		}
		for key, value in values.items():
			Glyphs.defaults[self._pref_key(key)] = value

	def _pref(self, key, fallback):
		value = Glyphs.defaults[self._pref_key(key)]
		return fallback if value is None else value

	@staticmethod
	def _pref_key(key):
		return "%s.%s" % (PREF_DOMAIN, key)

	def _set_busy(self, busy, status):
		controls = (
			self.w.destination,
			self.w.chooseButton,
			self.w.activeOnly,
			self.w.replaceExisting,
			self.w.revealResult,
			self.w.buildButton,
		)
		for control in controls:
			control.enable(not busy)
		self.w.status.set(status)
		self.w.progress.show(busy)
		if busy:
			self.w.progress.start()
		else:
			self.w.progress.stop()

	@staticmethod
	def _make_bold(text_box):
		text_box.getNSTextField().setFont_(
			NSFont.boldSystemFontOfSize_(NSFont.systemFontSize())
		)

	@staticmethod
	def _print_report(report):
		if report.warnings:
			print("\nWarnings:")
			for warning in report.warnings:
				print("- %s" % warning)
		if report.errors:
			print("\nErrors:")
			for error in report.errors:
				print("- %s" % error)

	def _show_warning_report(self, report):
		Message(
			title="Package Built with Warnings",
			message=self._compact_messages(report.warnings),
			OKButton=None,
		)

	@staticmethod
	def _show_error(title, message):
		Message(title=title, message=message, OKButton=None)

	@staticmethod
	def _compact_messages(messages, limit=5):
		visible = list(messages[:limit])
		text = "\n\n".join("• %s" % item for item in visible)
		remaining = len(messages) - len(visible)
		if remaining > 0:
			text += "\n\n…and %i more. See the Macro window." % remaining
		return text

	@staticmethod
	def _reveal(path):
		url = NSURL.fileURLWithPath_(path)
		NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_([url])


def main():
	if Glyphs.versionNumber < 3:
		Message(
			title="Glyphs 3 Required",
			message="%s requires Glyphs 3." % TITLE,
			OKButton=None,
		)
		return
	if vanilla is None:
		Message(
			title="Vanilla Module Required",
			message=(
				"Install the Vanilla module in Window → Plugin Manager → "
				"Modules, restart Glyphs, and run the script again."
			),
			OKButton=None,
		)
		return
	try:
		ApproximateTypePackageBuilderWindowController()
	except ExportPackageError as error:
		Message(title=TITLE, message=str(error), OKButton=None)
	except Exception as error:
		print(traceback.format_exc())
		Glyphs.showMacroWindow()
		Message(
			title="%s Error" % TITLE,
			message=(
				"%s\n\nDetails were printed in the Macro window." % error
			),
			OKButton=None,
		)


main()
