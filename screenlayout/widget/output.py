# This Python file uses the following encoding: utf-8

# ARandR -- Another XRandR GUI
# Copyright (C) 2008 -- 2011 chrysn <chrysn@fsfe.org>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import weakref
from collections import OrderedDict
from math import sqrt

import gobject, gtk
import pango

from ..gtktools import CategoryDefinitionWidget
from ..xrandr.constants import ConnectionStatus, SubpixelOrder

from ..auxiliary import Position

import gettext
gettext.install('arandr')

class Tab(object):
    def _set_outputwidget(self, new_value):
        self._outputwidget = weakref.ref(new_value)
    outputwidget = property(lambda self: self._outputwidget(), _set_outputwidget)

class TransitionOutputWidget(gtk.Notebook):
    """A detail widget for a single output of a transition. Bound to (and
    constructed from) a TransitionWidget. This coupling is necessary as long as
    the transition widget wraps general server/transition handling like server
    re-creation after updates; additionally, some of the interface requires
    knowledge of the complete transition / complete server (eg. virtual
    bounds); only those should access main_widget.

    The transition output widget is not bound to a transition output object,
    but only to an output name. This is done so that when the server is
    re-created after a transition is applied, the transition output widget can
    easily update itself from its main widget's new server.
    """

    __gsignals__ = {
            'changed':(gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
            }

    def __init__(self, main_widget, output_name):
        super(TransitionOutputWidget, self).__init__()

        self._main_widget = weakref.ref(main_widget)
        self.output_name = output_name

        self._create_tabs()

        self.update()

    def _create_tabs(self):
        self.tabs = OrderedDict([
            ('base', self.BaseTab()),
            ('position', self.PositionTab()),
            ('edid', self.EDIDTab()),
            ('automation', self.AutomationTab()),
            ])

        for t in self.tabs.values():
            self.insert_page(t, t.get_label())
            t.outputwidget = self

    def update(self):
        for t in self.tabs.values():
            t.update()

    main_widget = property(lambda self: self._main_widget())
    transition_output = property(lambda self: self.main_widget._transition.outputs[self.output_name])
    server_output = property(lambda self: self.transition_output.server_output)

    class BaseTab(CategoryDefinitionWidget, Tab):
        def __init__(self):
            super(TransitionOutputWidget.BaseTab, self).__init__()

            OUTPUT = _("Output information")
            CONNECTED = _("Connected monitor")
            CONFIG = _("Base configuration")

            self.output_name = gtk.Label()
            self.connection_status = gtk.Label()

            self.physical_dimension = gtk.Label()
            self.physical_diagonal = gtk.Label()
            self.subpixels = gtk.Label()

            self.active = gtk.CheckButton()
            self.active.connect('clicked', self.set_active)
            self.resolution = self._construct_resolution_box()
            self.resolution.connect('changed', self.set_resolution)
            self.refreshrate = gtk.ComboBox()
            self.primary = gtk.CheckButton()
            self.primary.connect('clicked', self.set_primary)

            items = [
                    (OUTPUT, _("Output name:"), self.output_name),
                    (OUTPUT, _("Connection status:"), self.connection_status),
                    (CONNECTED, _("Physical dimension:"), self.physical_dimension),
                    (CONNECTED, _("Screen diagonal:"), self.physical_diagonal),
                    (CONNECTED, _("Subpixel order:"), self.subpixels),
                    (CONFIG, _("Output active:"), self.active),
                    (CONFIG, _("Resolution:"), self.resolution),
                    (CONFIG, _("Refresh rate:"), self.refreshrate),
                    (CONFIG, _("Primary output:"), self.primary),
                    ]

            self.set_items(items)

        @staticmethod
        def _construct_resolution_box():
            b = gtk.ComboBox()
            crt = gtk.CellRendererText()
            b.pack_end(crt, expand=False)
            def labelfun(celllayout, cell, model, iter):
                cell.props.text = u"\N{BLACK STAR}" if model.get_value(iter, 0).is_preferred else "" # u"\N{MIDDLE DOT}"
            b.set_cell_data_func(crt, labelfun)

            crt = gtk.CellRendererText()
            b.pack_start(crt, expand=True)
            def labelfun(celllayout, cell, model, iter):
                cell.props.text = model.get_value(iter, 0).name
            b.set_cell_data_func(crt, labelfun)

            return b

        @staticmethod
        def get_label():
            return gtk.Label(_("Basic"))

        def update(self):
            self.output_name.props.label = self.outputwidget.output_name

            self.connection_status.props.label = {
                    ConnectionStatus('connected'): _("connected"),
                    ConnectionStatus('disconnected'): _("disconnected"),
                    ConnectionStatus('unknown connection'): _("unknown"),
                    }[self.outputwidget.server_output.connection_status]

            dimensions = (self.outputwidget.server_output.physical_x, self.outputwidget.server_output.physical_y)
            if any(x is None for x in dimensions):
                self.physical_dimension.props.label = _("–")
                self.physical_diagonal.props.label = _("–")
            else:
                diag = sqrt(sum(x**2 for x in dimensions))
                self.physical_dimension.props.label = _("%smm × %smm")%dimensions
                self.physical_diagonal.props.label = _('%.0fmm / %.1f"')%(diag, diag/25.4)
            self.subpixels.props.label = {
                    SubpixelOrder('unknown'): _('–'),
                    SubpixelOrder('horizontal rgb'): _('horizontal (RGB)'),
                    SubpixelOrder('horizontal bgr'): _('horizontal (BGR)'),
                    SubpixelOrder('vertical rgb'): _('vertical (RGB)'),
                    SubpixelOrder('vertical bgr'): _('vertical (BGR)'),
                    SubpixelOrder('no subpixels'): _('no subpixels'),
                    }[self.outputwidget.server_output.Subpixel]


            if self.outputwidget.transition_output.off:
                self.active.props.inconsistent = False
                self.active.props.active = False
            elif self.outputwidget.transition_output.named_mode or self.outputwidget.transition_output.precise_mode:
                self.active.props.inconsistent = False
                self.active.props.active = True
            else:
                self.active.props.inconsistent = True
                self.active.props.active = False
            self.active.props.sensitive = self.outputwidget.server_output.connection_status != ConnectionStatus('disconnected') # FIXME: check what happens when we have a unknown status with no modes


            self.resolution.props.sensitive = bool(self.outputwidget.transition_output.named_mode)

            model_by_name = gtk.ListStore(gobject.TYPE_PYOBJECT)
            modenames = set(m.name for m in self.outputwidget.server_output.assigned_modes)
            modecollections = [self.ModeCollectionByName(n, [m for m in self.outputwidget.server_output.assigned_modes if m.name == n]) for n in modenames]
            modecollections.sort(key=lambda a: (a.is_preferred, a.modes[0].width * a.modes[0].height), reverse=True)
            select_iter = None
            for mc in modecollections:
                mc_iter = model_by_name.append((mc,))
                if mc.name == self.outputwidget.transition_output.named_mode:
                    select_iter = mc_iter
            self.resolution.props.model = model_by_name
            if select_iter is not None:
                self.resolution.set_active_iter(select_iter)

            # FIXME CONTINUE HERE: procede like that with rates

            self.primary.props.active = self.outputwidget.transition_output is self.outputwidget.transition_output.transition.primary

        def set_active(self, widget):
            old_state = bool(self.outputwidget.transition_output.named_mode or self.outputwidget.transition_output.precise_mode)
            if widget.props.active == old_state:
                return

            if widget.props.active:
                self.outputwidget.transition_output.set_any_mode()
                self.outputwidget.transition_output.set_any_position()
            else:
                self.outputwidget.transition_output.named_mode = None
                self.outputwidget.transition_output.rate = None
                self.outputwidget.transition_output.precise_mode = None
                self.outputwidget.transition_output.auto = False
                self.outputwidget.transition_output.off = True
                self.outputwidget.transition_output.position = None
            self.outputwidget.emit('changed')

        def set_resolution(self, widget):
            active_iter = widget.get_active_iter()
            if active_iter is None:
                warnings.warn("set_resolution callback triggered without configured mode. If this happens inside an update() function, a widget emitted an event even though it should not have.")
                return
            selected_collection = widget.props.model.get_value(active_iter, 0)
            if self.outputwidget.transition_output.named_mode != selected_collection.name:
                self.outputwidget.transition_output.named_mode = selected_collection.name
                self.outputwidget.emit('changed')

        class ModeCollectionByName(object):
            def __init__(self, name, modes):
                self.name = name
                self.modes = modes

                assert all(m.name == self.name for m in self.modes)

            is_preferred = property(lambda self: any(x.is_preferred for x in self.modes))
            is_current = property(lambda self: any(x.is_current for x in self.modes))

        def set_primary(self, widget):
            old_state = self.outputwidget.transition_output.transition.primary is self.outputwidget.transition_output
            if old_state == widget.props.active:
                return

            if widget.props.active:
                self.outputwidget.transition_output.transition.primary = self.outputwidget.transition_output
            else:
                self.outputwidget.transition_output.transition.primary = self.outputwidget.transition_output.transition.NO_PRIMARY

            self.outputwidget.emit('changed')

    class PositionTab(CategoryDefinitionWidget, Tab):
        def __init__(self):
            super(TransitionOutputWidget.PositionTab, self).__init__()

            PRECISE_COORDINATES = _("Precise coordinates")

            self.x = gtk.SpinButton()
            self.x.connect('changed', self.set_position)
            self.y = gtk.SpinButton()
            self.y.connect('changed', self.set_position)

            self.x.props.adjustment.props.lower = 0
            self.y.props.adjustment.props.lower = 0
            self.x.props.adjustment.props.step_increment = 1
            self.y.props.adjustment.props.step_increment = 1

            items = [
                    (PRECISE_COORDINATES, _("Pixels from left:"), self.x),
                    (PRECISE_COORDINATES, _("Pixels from top:"), self.y),
                    ]

            self.set_items(items)

        @staticmethod
        def get_label():
            return gtk.Label(_("Position"))

        def _configure_limits(self, widget):
            self.x.props.adjustment.lower = 0
            self.x.props.adjustment.upper = widget.main_widget._transition.server.virtual.max[0]
            self.y.props.adjustment.lower = 0
            self.y.props.adjustment.upper = widget.main_widget._transition.server.virtual.max[1]

        def update(self):
            self._configure_limits(self.outputwidget)
            usable = self.outputwidget.transition_output.position is not None
            self.x.props.sensitive = usable
            self.y.props.sensitive = usable
            if usable:
                self.x.props.value = self.outputwidget.transition_output.position.left
                self.y.props.value = self.outputwidget.transition_output.position.top
            elif self.outputwidget.server_output.active:
                self.x.props.value = self.outputwidget.server_output.geometry.left
                self.y.props.value = self.outputwidget.server_output.geometry.top
            else:
                self.x.props.value = 0
                self.y.props.value = 0

            pso = self.outputwidget.transition_output.predicted_server_output
            if pso.active:
                self.x.props.adjustment.props.upper = self.outputwidget.transition_output.transition.server.virtual.max.width - pso.geometry.width
                self.y.props.adjustment.props.upper = self.outputwidget.transition_output.transition.server.virtual.max.height - pso.geometry.height
            else:
                self.x.props.adjustment.props.upper = 0
                self.y.props.adjustment.props.upper = 0

        def set_position(self, widget):
            old_position = self.outputwidget.transition_output.position
            if self.x.props.sensitive:
                new_position = Position((int(self.x.props.value), int(self.y.props.value)))
            else:
                new_position = None

            if old_position != new_position:
                self.outputwidget.transition_output.position = new_position
                self.outputwidget.emit('changed')

    class EDIDTab(gtk.Label, Tab):
        def __init__(self):
            super(TransitionOutputWidget.EDIDTab, self).__init__()
            self.props.wrap = True
            self.props.wrap_mode = pango.WRAP_CHAR

        def update(self):
            if 'EDID' in self.outputwidget.server_output.properties:
                self.props.label = self.outputwidget.server_output.properties['EDID'][0].encode('hex')
            else:
                self.props.label = _("No EDID data available.")

        @staticmethod
        def get_label():
            return gtk.Label(_("EDID information"))

    class AutomationTab(CategoryDefinitionWidget, Tab):
        def __init__(self):
            super(TransitionOutputWidget.AutomationTab, self).__init__()

            MODE_AND_POSITION = _("Mode and position")
            GLOBAL = _("Global options")
            RESET = _("Reset")

            self.auto = gtk.CheckButton()
            self.auto.connect('clicked', self.set_auto)
            self.explicit_mode = gtk.CheckButton()
            self.explicit_mode.connect('clicked', self.set_explicit_mode)
            self.explicit_position = gtk.CheckButton()
            self.explicit_position.connect('clicked', self.set_explicit_position)

            self.explicit_primary = gtk.CheckButton()
            self.explicit_primary.connect('clicked', self.set_explicit_primary)

            self.no_advanced_button = gtk.Button(_("Don't use advanced automation"))
            im = gtk.Image()
            im.props.icon_name = 'undo'
            self.no_advanced_button.props.image = im
            self.no_advanced_button.connect('clicked', self.reset_advanced)

            auto_label = gtk.Label(_("Let <tt>xrandr</tt> decide position and mode:"))
            auto_label.props.use_markup = True

            items = [
                    (MODE_AND_POSITION, auto_label, self.auto),
                    (MODE_AND_POSITION, _("Set explicit mode:"), self.explicit_mode),
                    (MODE_AND_POSITION, _("Set explicit position:"), self.explicit_position),
                    (GLOBAL, _("Set explicit primary screen:"), self.explicit_primary),
                    (RESET, self.no_advanced_button, None),
                    ]

            self.set_items(items)

        def reset_advanced(self, widget):
            self.auto.props.active = False
            self.explicit_mode.props.active = True
            self.explicit_position.props.active = True

        def set_auto(self, widget):
            old_state = self.outputwidget.transition_output.auto
            if old_state == widget.props.active:
                return

            if widget.props.active:
                self.outputwidget.transition_output.named_mode = None
                self.outputwidget.transition_output.rate = None
                self.outputwidget.transition_output.precise_mode = None
                self.outputwidget.transition_output.off = False
                self.outputwidget.transition_output.position = None
            self.outputwidget.transition_output.auto = widget.props.active
            self.outputwidget.emit('changed')

        def set_explicit_mode(self, widget):
            old_state = bool(self.outputwidget.transition_output.named_mode or self.outputwidget.transition_output.precise_mode)
            if old_state == widget.props.active:
                return

            if widget.props.active:
                self.outputwidget.transition_output.set_any_mode()
            else:
                self.outputwidget.transition_output.named_mode = None
                self.outputwidget.transition_output.rate = None
                self.outputwidget.transition_output.precise_mode = None
            self.outputwidget.emit('changed')

        def set_explicit_position(self, widget):
            old_state = bool(self.outputwidget.transition_output.position)
            if old_state == widget.props.active:
                return

            if widget.props.active:
                self.outputwidget.transition_output.set_any_position()
            else:
                self.outputwidget.transition_output.position = None
            self.outputwidget.emit('changed')

        def set_explicit_primary(self, widget):
            old_state = self.outputwidget.transition_output.transition.primary is not None
            if old_state == widget.props.active:
                return

            if widget.props.active:
                self.outputwidget.transition_output.transition.primary = self.outputwidget.transition_output.transition.NO_PRIMARY
            else:
                self.outputwidget.transition_output.transition.primary = None
            self.outputwidget.emit('changed')

        @staticmethod
        def get_label():
            return gtk.Label(_("Advanced automation"))

        def update(self):
            to = self.outputwidget.transition_output
            self.auto.props.active = to.auto
            self.explicit_mode.props.active = bool(to.named_mode or to.precise_mode)
            self.explicit_position.props.active = bool(to.position)
            self.explicit_primary.props.active = to.transition.primary is not None

            # FIXME: disable stuff when output can't be enabled, compare basic tab's .active
