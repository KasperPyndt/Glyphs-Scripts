# MenuTitle: Variable Axis Player
# -*- coding: utf-8 -*-
# Compatibility: Glyphs 4 only, Python 3 (native Font Axes sidebar).
"""Play Glyphs 4's Font Axes sliders in the active Edit tab.

Choose axes, set the playback speed, then Play. Pause leaves
that preview in place. Restore returns to the preview captured on opening.
Pause modes hold for one second at extremes or matching active instances.
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
from GlyphsApp import Glyphs, Message, INSTANCETYPESINGLE

VERSION = "1.3.2"
SINGLETON = "_kp_font_axes_player"
FRAME_RATES = (30.0, 20.0, 12.0)
CONTEXT_CHECK_INTERVAL = 0.5
HOLD_SECONDS = 1.0


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


class DwellPath:
    """Travel between exact axis locations and hold at each stop, without sleep."""
    def __init__(self, stops, current, ranges, descending=False):
        if len(stops) < 2:
            raise ValueError("At least two distinct stops are needed.")
        self.stops = [tuple(stop) for stop in stops]
        self.values = tuple(current)
        self.ranges = tuple(ranges)
        self.direction = -1 if descending else 1
        self.hold = 0.0
        self.arrived = False
        # Enter the route from the current preview, avoiding an initial jump.
        candidates = [i for i, stop in enumerate(self.stops)
                      if (stop[0] - current[0]) * self.direction > 1e-9]
        self.target = (candidates[-1] if descending else candidates[0]) if candidates else (0 if descending else len(stops)-1)
        matches = [i for i, stop in enumerate(self.stops)
                   if all(abs(a-b) <= max(1.0, hi-lo)*1e-9
                          for a, b, (lo, hi) in zip(stop, current, ranges))]
        if matches:
            self.target = matches[0]
            self.hold = HOLD_SECONDS
            self.arrived = True

    def next_stop(self):
        if self.target == len(self.stops)-1:
            self.direction = -1
        elif self.target == 0:
            self.direction = 1
        self.target += self.direction
        self.arrived = False

    def advance(self, elapsed, cycle_seconds):
        while elapsed > 1e-12:
            if self.arrived:
                consumed = min(elapsed, self.hold)
                self.hold -= consumed
                elapsed -= consumed
                if self.hold > 1e-12:
                    break
                self.next_stop()
                if elapsed <= 1e-12:
                    break
            destination = self.stops[self.target]
            distance = max(abs(b-a)/(hi-lo) for a, b, (lo, hi) in
                           zip(self.values, destination, self.ranges))
            travel_seconds = distance * cycle_seconds * 0.5
            if travel_seconds <= elapsed + 1e-12:
                self.values = destination
                elapsed = max(0.0, elapsed-travel_seconds)
                self.hold = HOLD_SECONDS
                self.arrived = True
            else:
                amount = elapsed/travel_seconds
                self.values = tuple(a+(b-a)*amount for a, b in zip(self.values, destination))
                elapsed = 0.0
        return self.values


def instance_stops(font, moving, ranges, fixed_values):
    """Exact static instance locations; unchecked axes stay at their current value."""
    stops = []
    for instance in font.instances:
        if instance.type != INSTANCETYPESINGLE or not instance.active or instance.manualInterpolation:
            continue
        values = tuple(float(v) for v in instance.axes)
        if len(values) != len(ranges) or not all(math.isfinite(v) for v in values):
            continue
        if any(abs(values[i]-fixed_values[i]) > max(1.0, hi-lo)*1e-7
               for i, (lo, hi) in enumerate(ranges) if i not in moving):
            continue
        if any(values[i] < ranges[i][0]-1e-9 or values[i] > ranges[i][1]+1e-9 for i in moving):
            continue
        stop = tuple(values[i] for i in moving)
        if stop not in stops:
            stops.append(stop)
    # Along the first checked axis, then the remaining checked axes.
    stops.sort()
    if len(stops) < 2:
        raise RuntimeError("Pause at instances needs two distinct active static instances matching the unchecked axes. Enable more axes or check Font Info → Exports.")
    return stops


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
        self.last_context_time = 0.0
        self.animated_indices = []
        self.cycle_duration = 6.0
        self.smooth = True
        self.dwell_path = None
        self.checks = []
        self.available = [hi > lo for lo, hi in self.ranges]
        if not any(self.available):
            raise RuntimeError("This font has no Font Axes slider with a nonzero range.")

        axis_rows = len(self.axes)
        controls_y = 36 + 24*axis_rows
        height = controls_y + 120
        self.w = vanilla.FloatingWindow((280, height), "Variable Axis Player",
                                       autosaveName="kp.VariableAxisPlayer.narrow")
        self.w.fontName = vanilla.TextBox((12, 9, -12, 17), str(font.familyName), sizeStyle="small")
        first = self.available.index(True)
        for i, (_, name) in enumerate(self.axes):
            low, high = self.ranges[i]
            title = "%s (%g–%g)" % (name, low, high)
            check = vanilla.CheckBox((12, 31 + 24*i, 148, 20),
                                    name, value=i == first, sizeStyle="small",
                                    callback=self.selection_changed)
            check.enable(self.available[i])
            check.getNSButton().setToolTip_(title)
            setattr(self.w, "axis%d" % i, check)
            self.checks.append(check)
            range_label = vanilla.TextBox((-112, 34 + 24*i, 100, 17),
                                           "(%g–%g)" % (low, high),
                                           alignment="right", sizeStyle="small")
            setattr(self.w, "range%d" % i, range_label)
        self.w.speedLabel = vanilla.TextBox((12, controls_y+3, 64, 17), "Speed", sizeStyle="small")
        self.w.speed = vanilla.Slider((86, controls_y, 132, 21), minValue=-2.0, maxValue=2.0,
                                     value=0.0, callback=self.speed_changed, sizeStyle="small")
        self.w.speedValue = vanilla.TextBox((224, controls_y+3, 44, 17), "1×",
                                            alignment="right", sizeStyle="small")
        self.w.motionLabel = vanilla.TextBox((12, controls_y+29, 64, 17), "Motion", sizeStyle="small")
        self.w.motion = vanilla.PopUpButton((86, controls_y+25, -12, 22),
                                            ["Smooth", "Pause at extremes", "Pause at instances"],
                                            callback=self.motion_changed, sizeStyle="small")
        self.w.performanceLabel = vanilla.TextBox((12, controls_y+55, 64, 17), "Playback", sizeStyle="small")
        self.w.performance = vanilla.PopUpButton((86, controls_y+51, -12, 22),
                                                 ["Smooth · 30 fps", "Balanced · 20 fps", "Light · 12 fps"],
                                                 callback=self.performance_changed, sizeStyle="small")
        self.w.restore = vanilla.Button((12, -34, 92, 22), "Restore", callback=self.restore, sizeStyle="small")
        self.w.play = vanilla.Button((-104, -34, 92, 22), "Play", callback=self.toggle, sizeStyle="small")
        self.w.motion.getNSPopUpButton().setToolTip_("Pause modes hold for one second. Instances follow active static exports matching unchecked axes.")
        self.w.speed.getNSSlider().setToolTip_("Move right for faster playback, left for slower.")
        self.w.restore.getNSButton().setToolTip_("Stop and restore the preview captured when this panel opened.")
        self.w.bind("close", self.window_closed)
        self.w.open()
        self.w.makeKey()

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
            mode = self.w.motion.get()
            self.smooth = mode == 0
            self.dwell_path = None
            if mode >= 1:
                moving = self.animated_indices
                fixed = [float(slider.doubleValue()) for slider in self.sliders]
                ranges = [self.ranges[i] for i in moving]
                if mode == 1:
                    stops = [tuple(low for low, high in ranges), tuple(high for low, high in ranges)]
                else:
                    stops = instance_stops(self.font, moving, self.ranges, fixed)
                self.dwell_path = DwellPath(stops, [fixed[i] for i in moving], ranges,
                                           self.phases[moving[0]] > 0.5)
            self.arm_timer()
            self.w.play.setTitle("Pause")
        except Exception as error:
            self.pause(str(error))
            Message("Variable Axis Player", str(error))

    def pause(self, message="Play resumes from this position."):
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None
        if not self.closed:
            self.w.play.setTitle("Play")
            self.w.play.getNSButton().setToolTip_(message)

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
            stop_values = self.dwell_path.advance(elapsed, self.cycle_duration) if self.dwell_path else None
            for position, i in enumerate(self.animated_indices):
                slider = self.sliders[i]
                # Test animated control ownership before every native action.
                if slider.window() is None:
                    self.acquire_sliders()
                    slider = self.sliders[i]
                low, high = self.ranges[i]
                if stop_values is None:
                    self.phases[i] = (self.phases[i] + advance) % 1.0
                    value = low + (high - low) * wave(self.phases[i], self.smooth)
                else:
                    value = stop_values[position]
                # Smaller than 1/4 of one slider point: indistinguishable thumb
                # motion need not trigger another expensive native interpolation.
                span = max(1.0, float(slider.bounds().size.width))
                threshold = (high - low) * 0.25 / span
                difference = abs(value - float(slider.doubleValue()))
                exact_stop = self.dwell_path is not None and self.dwell_path.arrived
                if difference > 1e-10 and (exact_stop or difference >= threshold):
                    move_slider(slider, value)
        except Exception as error:
            self.pause(str(error))
            print("Variable Axis Player:", error)
            traceback.print_exc()

    def performance_changed(self, sender):
        if self.timer is not None:
            self.arm_timer()

    def selection_changed(self, sender):
        if self.timer is not None:
            self.pause("Axes changed. Press Play to resume.")

    def cycle_seconds(self):
        return 6.0 / (2.0 ** self.w.speed.get())

    def speed_changed(self, sender):
        self.w.speedValue.set("%.2g×" % (2.0 ** sender.get()))
        self.cycle_duration = self.cycle_seconds()

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
            self.phases = [0.0] * len(self.axes)
            self.dwell_path = None
        except Exception as error:
            Message("Variable Axis Player", str(error))
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
        Message("Variable Axis Player", "This tool requires Glyphs 4's native Font Axes sidebar.")
        return
    previous = getattr(builtins, SINGLETON, None)
    if previous is not None:
        previous.close()
    font = Glyphs.font
    if font is None or font.currentTab is None:
        Message("Variable Axis Player", "Open a font and an Edit tab, then show Axes in the left sidebar.")
        return
    if not font.axes:
        Message("Variable Axis Player", "This font has no font axes.")
        return
    try:
        player = FontAxesPlayer(font, font.currentTab)
        setattr(builtins, SINGLETON, player)
    except Exception as error:
        traceback.print_exc()
        Message("Variable Axis Player", str(error))


if __name__ == "__main__":
    main()
