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

from __future__ import division
import os
import stat
import pango
import pangocairo
import gobject, gtk
from ..xrandr.constants import ConnectionStatus
from ..xrandr.server import Server
from ..xrandr.transition import Transition
from ..snap import Snap
from .. import executions

import gettext
gettext.install('arandr')

class TransitionWidget(gtk.DrawingArea):
    __gsignals__ = {
            'expose-event':'override', # FIXME: still needed?
            'changed':(gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
            }

    def __init__(self, factor=8, context=executions.context.local, force_version=False):
        super(TransitionWidget, self).__init__()

        self.force_version = force_version
        self.context = context

        self._factor = factor

        self.set_size_request(1024//self.factor, 1024//self.factor) # best guess for now

        self.connect('button-press-event', self.click)
        self.set_events(gtk.gdk.BUTTON_PRESS_MASK)

        self.setup_draganddrop()

        self._transition = None

    #################### widget features ####################

    def _set_factor(self, f):
        self._factor = f
        self._update_size_request()
        self._force_repaint()

    factor = property(lambda self: self._factor, _set_factor)

    def abort_if_unsafe(self):
        if not len([x for x in self._transition.outputs.values() if not x.off]):
            d = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_YES_NO, _("Your configuration does not include an active monitor. Do you want to apply the configuration?"))
            result = d.run()
            d.destroy()
            if result == gtk.RESPONSE_YES:
                return False
            else:
                return True
        return False

    def error_message(self, message):
            d = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, message)
            d.run()
            d.destroy()

    def _update_size_request(self):
        max_gapless = sum(max(max(m.width, m.height) for m in o.assigned_modes) if o.assigned_modes else 0 for o in self._transition.server.outputs.values()) # this ignores that some outputs might not support rotation, but will always err at the side of caution.
        # have some buffer
        usable_size = int(max_gapless * 1.1)
        # don't request too large a window, but make sure very possible compination fits
        xdim = min(self._transition.server.virtual.max[0], usable_size)
        ydim = min(self._transition.server.virtual.max[1], usable_size)
        self.set_size_request(xdim//self.factor, ydim//self.factor)

    #################### loading ####################

    '''
    def load_from_file(self, file):
        data = open(file).read()
        template = self._xrandr.load_from_string(data)
        self._xrandr_was_reloaded()
        return template
    '''

    def load_from_x(self):
        server = Server(context=self.context, force_version=self.force_version)
        self._transition = Transition(server)
        self._make_transition_nonempty()
        self._xrandr_was_reloaded()

    def _make_transition_nonempty(self):
        """Set some configuration parameters in the transition that don't
        change the server in its default configuration, but help the user get
        an overview of the state in the transition.

        Only call this with an empty transition."""
        for output in self._transition.outputs.values():
            if output.server_output.active:
                output.set_any_mode()
                output.set_any_position()
            else:
                output.off = True

    def _xrandr_was_reloaded(self):
        self.sequence = sorted(self._transition.outputs.values())
        self._lastclick = (-1,-1)

        self._update_size_request()
        if self.window:
            self._force_repaint()
        self.emit('changed')

    def save_to_x(self):
        self._transition.server.apply(self._transition)
        # FIXME: it would be cleaner to keep the transition and re-bind it to a
        # new server. thus, changes that don't round-trip cleanly are
        # preserved. possibly don't rebind transition, but load from
        # serialization again
        self.load_from_x()

    def save_to_string(self):
        import sys
        if sys.version >= (3, 3):
            from shlex import quote as shell_quote
        else:
            from pipes import quote as shell_quote

        return " ".join(map(shell_quote, self._transition.serialize()))

    '''
    def save_to_file(self, file, template=None, additional=None):
        data = self._xrandr.save_to_shellscript_string(template, additional)
        open(file, 'w').write(data)
        os.chmod(file, stat.S_IRWXU)
        self.load_from_file(file)
    '''

    #################### doing changes ####################

    '''
    def _set_something(self, which, on, data):
        old = getattr(self._xrandr.configuration.outputs[on], which)
        setattr(self._xrandr.configuration.outputs[on], which, data)
        try:
            self._xrandr.check_configuration()
        except InadequateConfiguration:
            setattr(self._xrandr.configuration.outputs[on], which, old)
            raise

        self._force_repaint()
        self.emit('changed')
    '''

    def set_position(self, on, pos):
        self._set_something('position', on, pos)
    def set_rotation(self, on, rot):
        self._set_something('rotation', on, rot)
    def set_resolution(self, on, res):
        self._set_something('mode', on, res)

    def set_active(self, on, active):
        v = self._xrandr.state.virtual
        o = self._xrandr.configuration.outputs[on]

        if not active and o.active:
            o.active = False
            # don't delete: allow user to re-enable without state being lost
        if active and not o.active:
            if hasattr(o, 'position'):
                o.active = True # nothing can go wrong, position already set
            else:
                pos = Position((0,0))
                for m in self._xrandr.state.outputs[on].modes:
                    # determine first possible mode
                    if m[0]<=v.max[0] and m[1]<=v.max[1]:
                        mode = m
                        break
                else:
                    raise InadequateConfiguration("Smallest mode too large for virtual.")

                o.active = True
                o.position = pos
                o.mode = mode
                o.rotation = NORMAL

        self._force_repaint()
        self.emit('changed')

    #################### painting ####################

    def do_expose_event(self, event):
        cr = pangocairo.CairoContext(self.window.cairo_create())
        cr.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        cr.clip()

        # clear
        cr.set_source_rgb(0,0,0)
        cr.rectangle(0,0,*self.window.get_size())
        cr.fill()
        cr.save()

        cr.scale(1/self.factor, 1/self.factor)
        cr.set_line_width(self.factor*1.5)

        self._draw(self._transition, cr)

    def _draw(self, transition, cr):
        cr.set_source_rgb(0.25,0.25,0.25)
        cr.rectangle(0,0,*transition.server.virtual.max)
        cr.fill()

        cr.set_source_rgb(0.5,0.5,0.5)
        cr.rectangle(0,0,*transition.server.virtual.current) # FIXME: we should get an expected virtual
        cr.fill()

        # for most painting related stuff, it is easier to just access a
        # predicted server than to merge transition details with server data
        transition.predict_server()

        for output in self.sequence:
            predicted = output.predicted_server_output
            if not predicted.active:
                continue

            rect = predicted.geometry # FIXME: a bit of a long shot; i doubt .geometry() will hold for long
            center = rect[0]+rect[2]/2, rect[1]+rect[3]/2

            # paint rectangle
            cr.set_source_rgba(1,1,1,0.7)
            cr.rectangle(*rect)
            cr.fill()
            cr.set_source_rgb(0,0,0)
            cr.rectangle(*rect)
            cr.stroke()

            # set up for text -- FIXME: there gotta be a better way...
            cr.save()
            textwidth = rect[3 if predicted.rotation.is_odd else 2]
            widthperchar = textwidth/len(predicted.name)
            textheight = int(widthperchar * 0.8) # i think this looks nice and won't overflow even for wide fonts

            newdescr = pango.FontDescription("sans")
            newdescr.set_size(textheight * pango.SCALE)

            # create text
            layout = cr.create_layout()
            layout.set_font_description(newdescr)
            layout.set_text(predicted.name)

            # position text
            layoutsize = layout.get_pixel_size()
            layoutoffset = -layoutsize[0]/2, -layoutsize[1]/2
            cr.move_to(*center)
            cr.rotate(predicted.rotation.angle)
            cr.rel_move_to(*layoutoffset)

            # pain text
            cr.show_layout(layout)
            cr.restore()

    def _force_repaint(self):
        # using self.allocation as rect is offset by the menu bar.
        self.window.invalidate_rect(gtk.gdk.Rectangle(0,0,self._transition.server.virtual.max[0]//self.factor,self._transition.server.virtual.max[1]//self.factor), False)
        # this has the side effect of not painting out of the available region on drag and drop

    #################### click handling ####################

    def click(self, widget, event):
        undermouse = self._get_point_outputs(event.x, event.y)
        if undermouse:
            target = self._get_point_active_output(event.x, event.y)
        if event.button == 1 and undermouse:
            old_sequence = self.sequence[:]
            if self._lastclick == (event.x, event.y): # this was the second click to that stack
                # push the highest of the undermouse windows below the lowest
                newpos = min(self.sequence.index(a) for a in undermouse)
                self.sequence.remove(target)
                self.sequence.insert(newpos,target)
                # sequence changed
                target = self._get_point_active_output(event.x, event.y)
            # pull the clicked window to the absolute top
            self.sequence.remove(target)
            self.sequence.append(target)

            if old_sequence != self.sequence:
                self._force_repaint()
        if event.button == 3:
            m = self.contextmenu(undermouse)
            m.show_all()
            m.popup(None, None, None, event.button, event.time)

        self._lastclick = (event.x, event.y)

    def _get_point_outputs(self, x, y):
        x,y = x*self.factor, y*self.factor
        outputs = set()
        for output in self._transition.outputs.values():
            if not output.predicted_server_output.active:
                continue
            poly = output.predicted_server_output.polygon
            if poly.point_distance(x, y) < 2*self.factor: # 2 pixels margin of error
                outputs.add(output)
        return outputs

    def _get_point_active_output(self, x, y):
        undermouse = self._get_point_outputs(x, y)
        if not undermouse: raise IndexError("No output here.")
        active = [a for a in self.sequence if a in undermouse][-1]
        return active

    #################### context menu ####################

    def contextmenu(self, outputs=None):
        outputs = outputs or self._transition.outputs.values()

        if len(outputs) == 1:
            (output, ) = outputs
            return self._contextmenu(output)

        m = gtk.Menu()
        for output in outputs:
            i = gtk.MenuItem(output.name)
            i.props.submenu = self._contextmenu(output)
            m.add(i)

            if output.server_output.connection_status != ConnectionStatus.connected:
                i.props.sensitive = False
        return m

    def _contextmenu(self, output):
        m = gtk.Menu()
        details = gtk.MenuItem(_("Details..."))
        m.add(details)
        return m

        oc = self._xrandr.configuration.outputs[on]
        os = self._xrandr.state.outputs[on]

        enabled = gtk.CheckMenuItem(_("Active"))
        enabled.props.active = oc.active
        enabled.connect('activate', lambda menuitem: self.set_active(on, menuitem.props.active))

        m.add(enabled)

        if oc.active:
            res_m = gtk.Menu()
            for r in os.modes:
                i = gtk.CheckMenuItem(str(r))
                i.props.draw_as_radio = True
                i.props.active = (oc.mode.name == r.name)
                def _res_set(menuitem, on, r):
                    try:
                        self.set_resolution(on, r)
                    except InadequateConfiguration, e:
                        self.error_message(_("Setting this resolution is not possible here: %s")%e.message)
                i.connect('activate', _res_set, on, r)
                res_m.add(i)

            or_m = gtk.Menu()
            for r in ROTATIONS:
                i = gtk.CheckMenuItem("%s"%r)
                i.props.draw_as_radio = True
                i.props.active = (oc.rotation == r)
                def _rot_set(menuitem, on, r):
                    try:
                        self.set_rotation(on, r)
                    except InadequateConfiguration, e:
                        self.error_message(_("This orientation is not possible here: %s")%e.message)
                i.connect('activate', _rot_set, on, r)
                if r not in os.rotations:
                    i.props.sensitive = False
                or_m.add(i)

            res_i = gtk.MenuItem(_("Resolution"))
            res_i.props.submenu = res_m
            or_i = gtk.MenuItem(_("Orientation"))
            or_i.props.submenu = or_m

            m.add(res_i)
            m.add(or_i)

        m.show_all()
        return m

    #################### drag&drop ####################

    def setup_draganddrop(self):
        self.drag_source_set(gtk.gdk.BUTTON1_MASK, [('screenlayout-output', gtk.TARGET_SAME_WIDGET, 0)], 0)
        self.drag_dest_set(0, [('screenlayout-output', gtk.TARGET_SAME_WIDGET, 0)], 0)
        #self.drag_source_set(gtk.gdk.BUTTON1_MASK, [], 0)
        #self.drag_dest_set(0, [], 0)

        self._draggingfrom = None
        self._draggingoutput = None
        self.connect('drag-begin', self._dragbegin_cb)
        self.connect('drag-motion', self._dragmotion_cb)
        self.connect('drag-drop', self._dragdrop_cb)
        self.connect('drag-end', self._dragend_cb)

        self._lastclick = (0,0)

    def _dragbegin_cb(self, widget, context):
        try:
            output = self._get_point_active_output(*self._lastclick)
        except IndexError:
            # FIXME: abort?
            context.set_icon_stock(gtk.STOCK_CANCEL, 10,10)
            return None

        self._draggingoutput = output
        self._draggingfrom = self._lastclick
        context.set_icon_stock(gtk.STOCK_FULLSCREEN, 10,10)

        self._draggingsnap = Snap(
                self._xrandr.configuration.outputs[self._draggingoutput].size,
                self.factor*5,
                [(Position((0,0)),self._xrandr.state.virtual.max)]+[
                    (v.position, v.size) for (k,v) in self._xrandr.configuration.outputs.items() if k!=self._draggingoutput and v.active
                ]
            )

    def _dragmotion_cb(self, widget, context,  x, y, time):
        if not 'screenlayout-output' in context.targets: # from outside
            return False
        if not self._draggingoutput: # from void; should be already aborted
            return False

        context.drag_status(gtk.gdk.ACTION_MOVE, time)

        rel = x-self._draggingfrom[0], y-self._draggingfrom[1]

        oldpos = self._xrandr.configuration.outputs[self._draggingoutput].position
        newpos = Position((oldpos[0]+self.factor*rel[0], oldpos[1]+self.factor*rel[1]))
        self._xrandr.configuration.outputs[self._draggingoutput].tentative_position = self._draggingsnap.suggest(newpos)
        self._force_repaint()

        return True

    def _dragdrop_cb(self, widget, context, x, y, time):
        if not self._draggingoutput:
            return

        try:
            self.set_position(self._draggingoutput, self._xrandr.configuration.outputs[self._draggingoutput].tentative_position)
        except InadequateConfiguration:
            context.finish(False, False, time)
            #raise # snapping back to the original position should be enought feedback

        context.finish(True, False, time)

    def _dragend_cb(self, widget, context):
        try:
            del self._xrandr.configuration.outputs[self._draggingoutput].tentative_position
        except KeyError:
            pass # already reloaded
        self._draggingoutput = None
        self._draggingfrom = None
        self._force_repaint()
