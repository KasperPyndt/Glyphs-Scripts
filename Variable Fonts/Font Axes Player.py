# MenuTitle: Font Axes Player
# -*- coding: utf-8 -*-
# Compatibility: Glyphs 4 only, Python 3 (native Font Axes sidebar).
"""Play Glyphs 4's Font Axes sliders in the active Edit tab.

Choose axes, set the playback speed, then Play. Pause leaves
that preview in place. Restore returns to the preview captured on opening.
Closing the panel stops its timer. No masters, instances or outlines are edited.

Native sidebar integration verified with Glyphs 4.1.1 (4108). The sidebar's
AxisCellView interface is not part of the public Python SDK; discovery fails
closed if a later Glyphs build changes it. No mouse automation is used.
"""

import builtins
import math
import time
import traceback

import vanilla
from AppKit import NSApp, NSSlider, NSTableView
from Foundation import NSRunLoop, NSDefaultRunLoopMode, NSTimer
from GlyphsApp import Glyphs, Message

VERSION = "1.2.0"
SINGLETON = "_kp_font_axes_player"
FRAME_RATES = (30.0, 20.0, 12.0)
CONTEXT_CHECK_INTERVAL = 0.5
LABEL_INTERVAL = 0.25


def wave(phase, smooth=True):
    """Unit ping-pong wave; phase is measured in full cycles."""
    phase %= 1.0
    if smooth:
        return (1.0 - math.cos(2.0 * math.pi * phase)) * 0.5
    return 2.0 * phase if phase <= 0.5 else 2.0 * (1.0 - phase)


def phase_for_value(value, low, high, smooth=True, descending=False):
    unit = max(0.0, min(1.0, (value - low) / (high - low)))
    phase = math.acos(1.0 - 2.0 * unit) / (2.0 * math.pi) if smooth else unit * 0.5
    return (1.0 - phase) % 1.0 if descending else phase


def descendants(root):
    if root is None:
        return
    pending = [root]
    while pending:
        view = pending.pop()
        yield view
        pending.extend(reversed(list(view.subviews())))


def signature(font):
    return tuple((str(axis.axisId), str(axis.name)) for axis in font.axes)


def font_sliders(tab, axes):
    """Use the Font Axes section, never a similarly named glyph axis.

    Glyphs 4108's AxesSidebar table begins with a heading followed by the font
    axes in native order. Validate every row, name, slider and native action.
    Request offscreen row views too, for fonts with many axes.
    """
    tables = [view for view in descendants(tab.leftSidebarView())
              if isinstance(view, NSTableView)
              and str(view.delegate().className()) == "AxesSidebar.SidebarViewController"]
    if len(tables) != 1:
        raise RuntimeError("Show the Axes section in the left sidebar, then run the script again.")
    table = tables[0]
    if table.numberOfRows() < len(axes) + 1:
        raise RuntimeError("The Font Axes section is filtered. Clear its Filter field first.")
    heading = table.viewAtColumn_row_makeIfNecessary_(0, 0, True)
    if heading is None or not hasattr(heading, "stringValue"):
        raise RuntimeError("This Glyphs build has a different Font Axes table layout.")
    result = []
    for row, (_, name) in enumerate(axes, 1):
        cell = table.viewAtColumn_row_makeIfNecessary_(0, row, True)
        if cell is None or str(cell.className()) != "AxesSidebar.AxisCellView":
            raise RuntimeError("The Font Axes rows have changed. Clear the sidebar Filter field.")
        if not hasattr(cell, "nameLabel") or str(cell.nameLabel().stringValue()) != name:
            raise RuntimeError("Font axis order does not match the sidebar. Clear its Filter field.")
        sliders = [view for view in descendants(cell) if isinstance(view, NSSlider)]
        if len(sliders) != 1:
            raise RuntimeError("Could not identify the native slider for %s." % name)
        slider = sliders[0]
        if slider.target() != cell or str(slider.action()) != "sliderChanged:":
            raise RuntimeError("The native slider action changed in this Glyphs build.")
        if not all(math.isfinite(float(v)) for v in
                   (slider.minValue(), slider.maxValue(), slider.doubleValue())):
            raise RuntimeError("Invalid slider range for %s." % name)
        result.append(slider)
    return result


def move_slider(slider, value):
    slider.setDoubleValue_(float(value))
    if not slider.sendAction_to_(slider.action(), slider.target()):
        raise RuntimeError("Glyphs could not deliver the axis slider action.")


class FontAxesPlayer:
    def __init__(self, font, tab):
        self.font = font
        self.tab = tab
        self.axes = signature(font)
        self.sliders = font_sliders(tab, self.axes)
        self.ranges = [(float(s.minValue()), float(s.maxValue())) for s in self.sliders]
        self.original_values = [float(s.doubleValue()) for s in self.sliders]
        self.original_location = dict(tab.graphicView().interpolationLocation() or {})
        self.original_master = int(font.parent.windowController().masterIndex())
        self.timer = None
        self.closed = False
        self.phases = [0.0] * len(self.axes)
        self.last_time = None
        self.last_label_time = 0.0
        self.last_context_time = 0.0
        self.animated_indices = []
        self.cycle_duration = 6.0
        self.smooth = True
        self.label_strings = [None] * len(self.axes)
        self.checks = []
        self.labels = []
        self.available = [hi > lo for lo, hi in self.ranges]
        if not any(self.available):
            raise RuntimeError("This font has no Font Axes slider with a nonzero range.")

        height = 261 + 32 * len(self.axes)
        self.w = vanilla.FloatingWindow((390, height), "Font Axes Player",
                                       autosaveName="kp.FontAxesPlayer.window")
        self.w.fontName = vanilla.TextBox((16, 12, -16, 20), str(font.familyName))
        self.w.hint = vanilla.TextBox((16, 36, -16, 18), "Animate these axes:", sizeStyle="small")
        first = self.available.index(True)
        for i, ((_, name), (low, high), value) in enumerate(zip(self.axes, self.ranges, self.original_values)):
            y = 61 + 32 * i
            check = vanilla.CheckBox((16, y, 215, 22), name, value=i == first,
                                     callback=self.selection_changed)
            check.enable(self.available[i])
            label = vanilla.TextBox((235, y + 2, -16, 18), self.label(i, value),
                                   alignment="right", sizeStyle="small")
            setattr(self.w, "axis%d" % i, check)
            setattr(self.w, "value%d" % i, label)
            self.checks.append(check)
            self.labels.append(label)
        y = 65 + 32 * len(self.axes)
        self.w.divider = vanilla.HorizontalLine((16, y, -16, 1))
        self.w.speedLabel = vanilla.TextBox((16, y + 14, 100, 18), "Speed", sizeStyle="small")
        # Logarithmic: equal distances double/halve speed; the centre is 1×.
        self.w.speed = vanilla.Slider((116, y + 10, 183, 24), minValue=-2.0, maxValue=2.0,
                                     value=0.0, callback=self.speed_changed)
        self.w.speedValue = vanilla.TextBox((305, y + 14, 68, 18), "1×", sizeStyle="small")
        self.w.motionLabel = vanilla.TextBox((16, y + 48, 100, 18), "Motion", sizeStyle="small")
        self.w.motion = vanilla.PopUpButton((116, y + 44, -16, 24),
                                            ["Smooth turnarounds", "Constant speed"],
                                            callback=self.motion_changed)
        self.w.performanceLabel = vanilla.TextBox((16, y + 82, 100, 18), "Playback", sizeStyle="small")
        self.w.performance = vanilla.PopUpButton((116, y + 78, -16, 24),
                                                 ["Smooth · 30 fps", "Balanced · 20 fps", "Light · 12 fps"],
                                                 callback=self.performance_changed)
        self.w.status = vanilla.TextBox((16, y + 116, -16, 34), "6.0 seconds out and back. Move Speed right for faster.",
                                       sizeStyle="small")
        self.w.restore = vanilla.Button((16, -40, 120, 24), "Restore", callback=self.restore)
        self.w.play = vanilla.Button((-126, -40, 110, 24), "Play", callback=self.toggle)
        self.w.bind("close", self.window_closed)
        self.w.open()
        self.w.makeKey()

    def label(self, i, value):
        low, high = self.ranges[i]
        return "%g  (%g–%g)" % (value, low, high)

    def valid_context(self, full=True):
        if full and not any(f == self.font for f in Glyphs.fonts):
            raise RuntimeError("Paused: the font was closed.")
        if Glyphs.font != self.font or self.font.currentTab != self.tab:
            raise RuntimeError("Paused: return to the original font and Edit tab.")
        if full and signature(self.font) != self.axes:
            raise RuntimeError("Font axes changed. Close this panel and run the script again.")
        if NSApp.modalWindow() is not None:
            raise RuntimeError("Paused while a dialog is open.")

    def acquire_sliders(self):
        self.valid_context()
        sliders = font_sliders(self.tab, self.axes)
        ranges = [(float(s.minValue()), float(s.maxValue())) for s in sliders]
        if ranges != self.ranges:
            raise RuntimeError("Axis ranges changed. Close this panel and run the script again.")
        self.sliders = sliders

    def sync_phases(self):
        smooth = self.w.motion.get() == 0
        for i, slider in enumerate(self.sliders):
            low, high = self.ranges[i]
            if high > low:
                self.phases[i] = phase_for_value(float(slider.doubleValue()), low, high,
                                                 smooth, self.phases[i] > 0.5)
        self.last_time = time.monotonic()

    def start(self):
        try:
            self.acquire_sliders()
            if not any(check.get() and available for check, available in zip(self.checks, self.available)):
                raise RuntimeError("Choose at least one axis to play.")
            self.sync_phases()
            self.animated_indices = [i for i, c in enumerate(self.checks) if c.get() and self.available[i]]
            self.cycle_duration = self.cycle_seconds()
            self.smooth = self.w.motion.get() == 0
            self.arm_timer()
            self.w.play.setTitle("Pause")
            self.playing_status()
        except Exception as error:
            self.pause(str(error))

    def pause(self, message="Paused. Play resumes from this position."):
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None
        if not self.closed:
            self.w.play.setTitle("Play")
            self.w.status.set(message)

    def toggle(self, sender=None):
        if self.timer is None:
            self.start()
        else:
            self.pause()

    def arm_timer(self):
        if self.timer is not None:
            self.timer.invalidate()
        fps = FRAME_RATES[self.w.performance.get()]
        self.timer = NSTimer.timerWithTimeInterval_repeats_block_(1.0 / fps, True, self.tick)
        # Default mode yields to menu/scroll/drag tracking. Never chase missed
        # frames: UI interaction gets priority over the animation.
        self.timer.setTolerance_(0.002)
        NSRunLoop.mainRunLoop().addTimer_forMode_(self.timer, NSDefaultRunLoopMode)

    def playing_status(self):
        self.w.status.set("Playing · %.1f s out and back · %g fps" %
                          (self.cycle_duration, FRAME_RATES[self.w.performance.get()]))

    def tick(self, timer):
        try:
            now = time.monotonic()
            # Floating panels may be hidden when the app deactivates. Do not
            # mistake that for Close, or interpolate a hidden font in background.
            if not NSApp.isActive():
                self.last_time = now
                return
            window = self.w.getNSWindow()
            if self.closed or window is None or not window.isVisible():
                self.window_closed(None)
                return
            full_check = now - self.last_context_time >= CONTEXT_CHECK_INTERVAL
            self.valid_context(full=full_check)
            if full_check:
                self.last_context_time = now
                if any(s.window() is None for s in self.sliders):
                    self.acquire_sliders()
            elapsed = now - self.last_time
            self.last_time = now
            if elapsed > 0.5:
                return
            advance = elapsed / self.cycle_duration
            # Compute from elapsed time, so dropping a late frame never creates
            # a backlog or changes the selected playback speed.
            for i in self.animated_indices:
                slider = self.sliders[i]
                # Test animated control ownership before every native action.
                if slider.window() is None:
                    self.acquire_sliders()
                    slider = self.sliders[i]
                low, high = self.ranges[i]
                self.phases[i] = (self.phases[i] + advance) % 1.0
                value = low + (high - low) * wave(self.phases[i], self.smooth)
                # Smaller than 1/4 of one slider point: indistinguishable thumb
                # motion need not trigger another expensive native interpolation.
                span = max(1.0, float(slider.bounds().size.width))
                threshold = (high - low) * 0.25 / span
                if abs(value - float(slider.doubleValue())) >= threshold:
                    move_slider(slider, value)
            if now - self.last_label_time >= LABEL_INTERVAL:
                self.update_labels()
                self.last_label_time = now
        except Exception as error:
            self.pause(str(error))
            print("Font Axes Player:", error)
            traceback.print_exc()

    def update_labels(self):
        for i, slider in enumerate(self.sliders):
            text = self.label(i, float(slider.doubleValue()))
            if text != self.label_strings[i]:
                self.labels[i].set(text)
                self.label_strings[i] = text

    def performance_changed(self, sender):
        if self.timer is not None:
            self.arm_timer()
            self.playing_status()
        else:
            self.w.status.set("%g fps selected. Speed controls the cycle time." %
                              FRAME_RATES[sender.get()])

    def selection_changed(self, sender):
        if self.timer is not None:
            self.pause("Axes changed. Press Play to resume.")

    def cycle_seconds(self):
        return 6.0 / (2.0 ** self.w.speed.get())

    def speed_changed(self, sender):
        self.w.speedValue.set("%.2g×" % (2.0 ** sender.get()))
        self.cycle_duration = self.cycle_seconds()
        if self.timer is not None:
            self.playing_status()
            return
        prefix = "Playing · " if self.timer is not None else "Speed set · "
        self.w.status.set(prefix + "%.1f seconds out and back" % self.cycle_seconds())

    def motion_changed(self, sender):
        if self.timer is not None:
            self.pause("Motion changed. Press Play to resume.")

    def restore(self, sender=None):
        self.pause()
        try:
            self.acquire_sliders()
            self.font.parent.windowController().setMasterIndex_(self.original_master)
            # Changing the master can rebuild the sidebar.
            self.acquire_sliders()
            for slider, value in zip(self.sliders, self.original_values):
                move_slider(slider, value)
            self.tab.graphicView().showInterpolationAtLocation_(self.original_location)
            self.tab.graphicView().reflow()
            self.update_labels()
            self.phases = [0.0] * len(self.axes)
            self.w.status.set("Restored the preview from when this panel opened.")
        except Exception as error:
            self.w.status.set(str(error))
            traceback.print_exc()

    def window_closed(self, sender):
        if self.closed:
            return
        self.closed = True
        self.pause()
        if getattr(builtins, SINGLETON, None) is self:
            delattr(builtins, SINGLETON)

    def close(self):
        if self.closed:
            return
        # NSPanel close notifications can be deferred on the host. Do the
        # timer/singleton cleanup immediately, before asking AppKit to close.
        self.window_closed(None)
        self.w.getNSWindow().performClose_(None)


def main():
    if float(Glyphs.versionNumber) < 4.0:
        Message("Font Axes Player", "This tool requires Glyphs 4's native Font Axes sidebar.")
        return
    previous = getattr(builtins, SINGLETON, None)
    if previous is not None:
        previous.close()
    font = Glyphs.font
    if font is None or font.currentTab is None:
        Message("Font Axes Player", "Open a font and an Edit tab, then show Axes in the left sidebar.")
        return
    if not font.axes:
        Message("Font Axes Player", "This font has no font axes.")
        return
    try:
        player = FontAxesPlayer(font, font.currentTab)
        setattr(builtins, SINGLETON, player)
    except Exception as error:
        traceback.print_exc()
        Message("Font Axes Player", str(error))


if __name__ == "__main__":
    main()
