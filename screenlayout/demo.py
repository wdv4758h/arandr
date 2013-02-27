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

"""Demo application, primarily used to make sure the screenlayout library can be used independent of ARandR.

Run by calling the main() function."""

import gtk
from .widget import TransitionWidget, TransitionOutputWidget

def update_tabs(widget, tabs):
    for output_name in widget._transition.outputs.keys():
        tabs.insert_page(TransitionOutputWidget(widget, output_name), tab_label=gtk.Label(output_name))

def main():
    w = gtk.Window()
    w.connect('destroy',gtk.main_quit)

    r = TransitionWidget()
    r.load_from_x()

    output_properties = gtk.Notebook()
    r.connect('changed', update_tabs, output_properties)
    r.emit('changed')

    b = gtk.Button("Reload")
    b.connect('clicked', lambda *args: r.load_from_x())

    b2 = gtk.Button("Apply")
    b2.connect('clicked', lambda *args: r.save_to_x())

    v = gtk.VBox()
    w.add(v)
    v.add(r)
    v.add(output_properties)
    v.add(b)
    v.add(b2)
    w.set_title('Simple ARandR Widget Demo')
    w.show_all()
    gtk.main()

if __name__ == "__main__":
    main()
