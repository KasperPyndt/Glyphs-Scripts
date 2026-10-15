# MenuTitle: Export Package Builder
# -*- coding: utf-8 -*-
"""
Build a Desktop/Web/Variable export package for the frontmost Glyphs 3 font.

The export engine and the Vanilla window controller are intentionally separate.
That keeps the engine reusable when this script is promoted to a .glyphsPlugin.
"""

import os
import shutil
import traceback
import uuid

from AppKit import NSFont, NSWorkspace
from Foundation import NSURL
from GlyphsApp import (
    Glyphs,
    GetFolder,
    INSTANCETYPESINGLE,
    INSTANCETYPEVARIABLE,
    Message,
    OTF,
    PLAIN,
    TTF,
    VARIABLE,
    WOFF,
    WOFF2,
)

try:
    import vanilla
except ImportError:
    vanilla = None


PREF_DOMAIN = "com.atype.exportPackageBuilder"


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
        package_name=None,
        desktop_folder_name="Desktop",
        web_folder_name="Web",
        variable_folder_name="Variable",
        desktop_otf=True,
        desktop_ttf=False,
        web_woff2=True,
        web_woff=False,
        variable_ttf=True,
        variable_woff2=True,
        active_only=True,
        replace_existing=True,
        reveal_result=True,
    ):
        self.destination = destination
        self.package_name = package_name
        self.desktop_folder_name = desktop_folder_name
        self.web_folder_name = web_folder_name
        self.variable_folder_name = variable_folder_name
        self.desktop_otf = bool(desktop_otf)
        self.desktop_ttf = bool(desktop_ttf)
        self.web_woff2 = bool(web_woff2)
        self.web_woff = bool(web_woff)
        self.variable_ttf = bool(variable_ttf)
        self.variable_woff2 = bool(variable_woff2)
        self.active_only = bool(active_only)
        self.replace_existing = bool(replace_existing)
        self.reveal_result = bool(reveal_result)

    def has_selected_format(self):
        return any(
            (
                self.desktop_otf,
                self.desktop_ttf,
                self.web_woff2,
                self.web_woff,
                self.variable_ttf,
                self.variable_woff2,
            )
        )


class ExportReport:
    """Collects output paths, recoverable warnings, and fatal export errors."""

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
        label,
        output_folder,
        outline_format,
        container,
        expected_extension,
        optional=False,
    ):
        self.instance = instance
        self.label = label
        self.output_folder = output_folder
        self.outline_format = outline_format
        self.container = container
        self.expected_extension = expected_extension.lower()
        self.optional = optional


class ExportPackageBuilder:
    """Glyphs-independent orchestration around the small Glyphs export surface."""

    def __init__(self, font, options, logger=print):
        self.font = font
        self.options = options
        self.log = logger

    def build(self):
        if not self.font:
            raise ExportPackageError("No font is open.")
        if self.options.package_name is None:
            package_name = self._package_name(self.font.familyName)
        else:
            package_name = self._safe_folder_name(
                self.options.package_name,
                "package",
            )
        folder_names = self._resolved_folder_names()
        destination = self._normalized_destination(self.options.destination)
        package_path = os.path.join(destination, package_name)
        report = ExportReport(package_path)

        self._validate(destination, package_path, folder_names)
        os.makedirs(destination, exist_ok=True)

        staging_name = ".%s.export-package-%s" % (
            package_name,
            uuid.uuid4().hex,
        )
        staging_path = os.path.join(destination, staging_name)
        os.mkdir(staging_path)

        folders = {}
        for folder_key, folder_name in folder_names.items():
            folders[folder_key] = os.path.join(staging_path, folder_name)
            os.mkdir(folders[folder_key])

        self.log("Export Package Builder")
        self.log("Family: %s" % self.font.familyName)
        self.log("Destination: %s" % package_path)

        try:
            tasks = self._make_tasks(folders, report)
            if not tasks:
                report.add_error(
                    "No eligible instances were found for the selected formats."
                )

            for task in tasks:
                self._run_task(task, report)

            if not report.produced_files and not report.errors:
                report.add_error("No font files were produced.")

            if report.errors:
                raise ExportFailedError(report)

            staged_files = list(report.produced_files)
            self._commit(staging_path, package_path, report)
            report.produced_files = [
                os.path.join(
                    package_path,
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

    def _validate(self, destination, package_path, folder_names):
        if not self.font:
            raise ExportPackageError("No font is open.")
        if not self.options.has_selected_format():
            raise ExportPackageError("Select at least one export format.")
        if not destination:
            raise ExportPackageError("Choose a destination folder.")
        if os.path.exists(destination) and not os.path.isdir(destination):
            raise ExportPackageError("The destination is not a folder.")
        if os.path.isfile(package_path) or os.path.islink(package_path):
            raise ExportPackageError(
                "A non-folder item already uses the package name:\n%s" % package_path
            )
        if os.path.isdir(package_path) and not self.options.replace_existing:
            raise ExportPackageError(
                "The package already exists. Enable ‘Replace existing package’ "
                "or choose another destination."
            )
        comparable_names = [name.casefold() for name in folder_names.values()]
        if len(comparable_names) != len(set(comparable_names)):
            raise ExportPackageError(
                "Desktop, Web, and Variable must use different folder names."
            )

    def _make_tasks(self, folders, report):
        instances = list(self.font.instances)
        all_static_instances = [
            instance
            for instance in instances
            if instance.type == INSTANCETYPESINGLE
        ]
        all_variable_instances = [
            instance
            for instance in instances
            if instance.type == INSTANCETYPEVARIABLE
        ]
        static_instances = [
            instance
            for instance in all_static_instances
            if self._include_instance(instance)
        ]
        variable_instances = [
            instance
            for instance in all_variable_instances
            if self._include_instance(instance)
        ]

        static_requested = any(
            (
                self.options.desktop_otf,
                self.options.desktop_ttf,
                self.options.web_woff2,
                self.options.web_woff,
            )
        )
        variable_requested = any(
            (self.options.variable_ttf, self.options.variable_woff2)
        )

        if static_requested and not static_instances:
            report.add_warning(
                self._no_instances_message("static", all_static_instances)
            )
        if variable_requested and not variable_instances:
            report.add_warning(
                self._no_instances_message("variable", all_variable_instances)
                + " Add a Variable Font Setting in Font Info → Exports."
            )

        tasks = []
        for instance in static_instances:
            style_name = instance.name or "Unnamed static instance"
            if self.options.desktop_otf:
                tasks.append(
                    ExportTask(
                        instance,
                        "%s — desktop OTF" % style_name,
                        folders["desktop"],
                        OTF,
                        PLAIN,
                        ".otf",
                    )
                )
            if self.options.desktop_ttf:
                tasks.append(
                    ExportTask(
                        instance,
                        "%s — desktop TTF" % style_name,
                        folders["desktop"],
                        TTF,
                        PLAIN,
                        ".ttf",
                    )
                )
            if self.options.web_woff2:
                tasks.append(
                    ExportTask(
                        instance,
                        "%s — web WOFF2" % style_name,
                        folders["web"],
                        TTF,
                        WOFF2,
                        ".woff2",
                    )
                )
            if self.options.web_woff:
                tasks.append(
                    ExportTask(
                        instance,
                        "%s — web WOFF" % style_name,
                        folders["web"],
                        TTF,
                        WOFF,
                        ".woff",
                    )
                )

        for instance in variable_instances:
            setting_name = instance.name or "Variable font"
            if self.options.variable_ttf:
                tasks.append(
                    ExportTask(
                        instance,
                        "%s — variable TTF" % setting_name,
                        folders["variable"],
                        VARIABLE,
                        PLAIN,
                        ".ttf",
                    )
                )
            if self.options.variable_woff2:
                tasks.append(
                    ExportTask(
                        instance,
                        "%s — variable WOFF2" % setting_name,
                        folders["variable"],
                        VARIABLE,
                        WOFF2,
                        ".woff2",
                        optional=True,
                    )
                )
        return tasks

    def _run_task(self, task, report):
        self.log("Exporting %s…" % task.label)
        before = self._folder_snapshot(task.output_folder)
        export_folder_parameters = self._remove_export_folder_parameters(
            task.instance
        )

        try:
            try:
                result = task.instance.generate(
                    format=task.outline_format,
                    fontPath=task.output_folder,
                    containers=[task.container],
                )
                result_errors = self._result_errors(result)
            except Exception as error:
                result_errors = [self._error_text(error)]
        finally:
            self._restore_custom_parameters(
                task.instance,
                export_folder_parameters,
            )

        after = self._folder_snapshot(task.output_folder)
        changed_files = self._changed_files(
            before,
            after,
            task.expected_extension,
        )
        for file_path in changed_files:
            if file_path not in report.produced_files:
                report.produced_files.append(file_path)

        if result_errors:
            message = "%s failed: %s" % (
                task.label,
                "; ".join(result_errors),
            )
            if task.optional:
                report.add_warning(message)
                self.log("Warning: %s" % message)
            else:
                report.add_error(message)
                self.log("Error: %s" % message)
            return

        if not changed_files:
            message = (
                "%s: Glyphs reported success but no %s file was produced."
                % (task.label, task.expected_extension)
            )
            if task.optional:
                report.add_warning(message)
                self.log("Warning: %s" % message)
            else:
                report.add_error(message)
                self.log("Error: %s" % message)
            return

        for file_path in changed_files:
            self.log("  %s" % os.path.basename(file_path))

    @staticmethod
    def _remove_export_folder_parameters(instance):
        """Temporarily stop Glyphs from adding instance export subfolders."""
        parameters = instance.customParameters
        removed = []
        for index in range(len(parameters) - 1, -1, -1):
            parameter = parameters[index]
            if parameter.name == "Export Folder":
                removed.append((index, parameter))
                del parameters[index]
        return removed

    @staticmethod
    def _restore_custom_parameters(instance, removed_parameters):
        parameters = instance.customParameters
        for index, parameter in sorted(removed_parameters):
            parameters.insert(index, parameter)

    def _commit(self, staging_path, package_path, report):
        backup_path = None
        if os.path.isdir(package_path):
            backup_path = os.path.join(
                os.path.dirname(package_path),
                ".%s.export-package-backup-%s"
                % (os.path.basename(package_path), uuid.uuid4().hex),
            )
            os.replace(package_path, backup_path)

        try:
            os.replace(staging_path, package_path)
        except Exception:
            if backup_path and os.path.isdir(backup_path):
                os.replace(backup_path, package_path)
            raise

        if backup_path and os.path.isdir(backup_path):
            try:
                shutil.rmtree(backup_path)
            except Exception as error:
                report.add_warning(
                    "The new package was built, but its hidden backup could not "
                    "be removed: %s" % self._error_text(error)
                )

    def _include_instance(self, instance):
        if not self.options.active_only:
            return True
        active = getattr(instance, "active", None)
        if active is None:
            active = getattr(instance, "exports", True)
        return bool(active)

    def _no_instances_message(self, kind, all_instances):
        qualifier = "active " if self.options.active_only else ""
        if all_instances and self.options.active_only:
            return "No %s%s instances are available." % (qualifier, kind)
        return "No %s instances are configured." % kind

    def _resolved_folder_names(self):
        return {
            "desktop": self._safe_folder_name(
                self.options.desktop_folder_name,
                "Desktop",
            ),
            "web": self._safe_folder_name(
                self.options.web_folder_name,
                "Web",
            ),
            "variable": self._safe_folder_name(
                self.options.variable_folder_name,
                "Variable",
            ),
        }

    @staticmethod
    def _normalized_destination(destination):
        if not destination:
            return ""
        return os.path.abspath(os.path.expanduser(destination.strip()))

    @staticmethod
    def _package_name(family_name):
        if not family_name or not family_name.strip():
            raise ExportPackageError(
                "The current font needs a family name before it can be packaged."
            )
        name = family_name.strip().replace("\x00", "")
        name = name.replace("/", "-").replace(":", "-")
        if os.altsep:
            name = name.replace(os.altsep, "-")
        if name in (".", "..") or not name:
            raise ExportPackageError("The family name is not a safe folder name.")
        return name

    @staticmethod
    def _safe_folder_name(value, label):
        name = str(value).strip() if value is not None else ""
        if not name:
            raise ExportPackageError("Enter a name for the %s folder." % label)
        forbidden = [character for character in ("/", ":", "\x00") if character in name]
        if os.altsep and os.altsep in name:
            forbidden.append(os.altsep)
        if name in (".", "..") or forbidden:
            raise ExportPackageError(
                "The %s folder name is not valid. Do not use /, :, or null characters."
                % label
            )
        return name

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


class ExportPackageBuilderWindowController:
    """Small Vanilla UI. A future plugin can instantiate this controller unchanged."""

    def __init__(self):
        self.font = Glyphs.font
        if not self.font:
            raise ExportPackageError(
                "Open a font in Glyphs, then run Export Package Builder again."
            )

        self.w = vanilla.FloatingWindow(
            (550, 342),
            "Export Package Builder",
            autosaveName=PREF_DOMAIN + ".window",
        )

        margin = 18
        label_width = 94
        field_left = margin + label_width
        folder_field_width = 190
        format_left = field_left + folder_field_width + 20
        second_format_left = format_left + 88

        self.w.packageLabel = vanilla.TextBox(
            (margin, 16, label_width - 8, 20),
            "Package:",
        )
        self.w.packageName = vanilla.EditText(
            (field_left, 12, -margin, 24),
            ExportPackageBuilder._package_name(self.font.familyName),
        )
        self.w.destinationLabel = vanilla.TextBox(
            (margin, 48, label_width - 8, 20),
            "Destination:",
        )
        self.w.destination = vanilla.EditText(
            (field_left, 44, -112, 24),
            self._pref("destination", os.path.expanduser("~/Desktop")),
        )
        self.w.chooseButton = vanilla.Button(
            (-102, 44, -margin, 24),
            "Choose…",
            callback=self.choose_destination,
        )
        self.w.topLine = vanilla.HorizontalLine((margin, 82, -margin, 1))

        self.w.desktopTitle = vanilla.TextBox(
            (margin, 102, label_width - 8, 20),
            "Desktop:",
        )
        self.w.desktopFolderName = vanilla.EditText(
            (field_left, 98, folder_field_width, 24),
            "Desktop",
        )
        self.w.desktopOTF = vanilla.CheckBox(
            (format_left, 100, 78, 20),
            "OTF",
            value=self._pref("desktopOTF", True),
        )
        self.w.desktopTTF = vanilla.CheckBox(
            (second_format_left, 100, 78, 20),
            "TTF",
            value=self._pref("desktopTTF", False),
        )

        self.w.webTitle = vanilla.TextBox(
            (margin, 134, label_width - 8, 20),
            "Web:",
        )
        self.w.webFolderName = vanilla.EditText(
            (field_left, 130, folder_field_width, 24),
            "Web",
        )
        self.w.webWOFF2 = vanilla.CheckBox(
            (format_left, 132, 78, 20),
            "WOFF2",
            value=self._pref("webWOFF2", True),
        )
        self.w.webWOFF = vanilla.CheckBox(
            (second_format_left, 132, 78, 20),
            "WOFF",
            value=self._pref("webWOFF", False),
        )

        self.w.variableTitle = vanilla.TextBox(
            (margin, 166, label_width - 8, 20),
            "Variable:",
        )
        self.w.variableFolderName = vanilla.EditText(
            (field_left, 162, folder_field_width, 24),
            "Variable",
        )
        self.w.variableTTF = vanilla.CheckBox(
            (format_left, 164, 78, 20),
            "TTF",
            value=self._pref("variableTTF", True),
        )
        self.w.variableWOFF2 = vanilla.CheckBox(
            (second_format_left, 164, 92, 20),
            "WOFF2",
            value=self._pref("variableWOFF2", True),
        )

        self.w.optionsLine = vanilla.HorizontalLine((margin, 202, -margin, 1))
        self.w.activeOnly = vanilla.CheckBox(
            (margin, 218, 230, 20),
            "Export active instances only",
            value=self._pref("activeOnly", True),
        )
        self.w.replaceExisting = vanilla.CheckBox(
            (276, 218, -margin, 20),
            "Replace existing package",
            value=self._pref("replaceExisting", True),
        )
        self.w.revealResult = vanilla.CheckBox(
            (margin, 246, 230, 20),
            "Reveal result in Finder",
            value=self._pref("revealResult", True),
        )

        self.w.progress = vanilla.ProgressBar(
            (margin, 278, -margin, 12),
            isIndeterminate=True,
            sizeStyle="small",
        )
        self.w.progress.show(False)
        self.w.status = vanilla.TextBox(
            (margin, 297, -172, 20),
            "Ready to build %s." % self.font.familyName,
        )
        self.w.buildButton = vanilla.Button(
            (-158, -38, -margin, 24),
            "Build Package",
            callback=self.build_package,
        )
        for headline in (
            self.w.packageLabel,
            self.w.destinationLabel,
            self.w.desktopTitle,
            self.w.webTitle,
            self.w.variableTitle,
        ):
            self._make_bold(headline)
        self.w.setDefaultButton(self.w.buildButton)
        self.w.open()
        self.w.makeKey()

    def choose_destination(self, _sender):
        current_path = self.w.destination.get().strip()
        chosen_path = GetFolder(
            message="Choose where the family package should be created",
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

            report = ExportPackageBuilder(current_font, options).build()
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
                "Export Package Builder",
                "Built %s with %i file(s)."
                % (current_font.familyName, len(report.produced_files)),
            )
        except ExportFailedError as error:
            self._set_busy(False, "The package was not replaced; see the errors.")
            self._print_report(error.report)
            Glyphs.showMacroWindow()
            self._show_error(
                "Export Package Failed",
                self._compact_messages(error.report.errors),
            )
        except ExportPackageError as error:
            self._set_busy(False, str(error))
            self._show_error("Export Package Builder", str(error))
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
            package_name=self.w.packageName.get(),
            desktop_folder_name=self.w.desktopFolderName.get(),
            web_folder_name=self.w.webFolderName.get(),
            variable_folder_name=self.w.variableFolderName.get(),
            desktop_otf=self.w.desktopOTF.get(),
            desktop_ttf=self.w.desktopTTF.get(),
            web_woff2=self.w.webWOFF2.get(),
            web_woff=self.w.webWOFF.get(),
            variable_ttf=self.w.variableTTF.get(),
            variable_woff2=self.w.variableWOFF2.get(),
            active_only=self.w.activeOnly.get(),
            replace_existing=self.w.replaceExisting.get(),
            reveal_result=self.w.revealResult.get(),
        )

    def _save_preferences(self, options):
        values = {
            "destination": options.destination,
            "desktopOTF": options.desktop_otf,
            "desktopTTF": options.desktop_ttf,
            "webWOFF2": options.web_woff2,
            "webWOFF": options.web_woff,
            "variableTTF": options.variable_ttf,
            "variableWOFF2": options.variable_woff2,
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
            self.w.packageName,
            self.w.destination,
            self.w.chooseButton,
            self.w.desktopFolderName,
            self.w.desktopOTF,
            self.w.desktopTTF,
            self.w.webFolderName,
            self.w.webWOFF2,
            self.w.webWOFF,
            self.w.variableFolderName,
            self.w.variableTTF,
            self.w.variableWOFF2,
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
            message="Export Package Builder requires Glyphs 3.",
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
        ExportPackageBuilderWindowController()
    except ExportPackageError as error:
        Message(
            title="Export Package Builder",
            message=str(error),
            OKButton=None,
        )
    except Exception as error:
        print(traceback.format_exc())
        Glyphs.showMacroWindow()
        Message(
            title="Export Package Builder Error",
            message=(
                "%s\n\nDetails were printed in the Macro window." % error
            ),
            OKButton=None,
        )


main()
