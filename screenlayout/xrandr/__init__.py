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

"""Wrapper around command line xrandr"""

import gettext
gettext.install('arandr')

SHELLSHEBANG='#!/bin/sh'

from .server import Server
from .transition import Transition

__all__ = ['Server', 'Transition']


















class OldStuff(object):
    # old stuff that is lingering in the xrandr backend rewrite


    def load_from_commandlineargs(self, commandline):
        args = BetterList(shlex.split(commandline))
        if args.pop(0) != 'xrandr':
            raise FileSyntaxError()
        options = dict((a[0], a[1:]) for a in args.split('--output') if a) # first part is empty, exclude empty parts

        for on,oa in options.items():
            o = self.configuration.outputs[on]
            if oa == ['--off']:
                o.active = False
            else:
                if len(oa)%2 != 0:
                    raise FileSyntaxError()
                parts = [(oa[2*i],oa[2*i+1]) for i in range(len(oa)//2)]
                for p in parts:
                    if p[0] == '--mode':
                        o.mode = Size(p[1])
                    elif p[0] == '--pos':
                        o.position = Position(p[1])
                    elif p[0] == '--rotate':
                        if p[1] not in ROTATIONS:
                            raise FileSyntaxError()
                        o.rotation = Rotation(p[1])
                    else:
                        raise FileSyntaxError()
                o.active = True

    def load_from_string(self, data):
        data = data.replace("%","%%")
        lines = data.split("\n")
        if lines[-1] == '': lines.pop() # don't create empty last line

        if lines[0] != SHELLSHEBANG:
            raise FileLoadError('Not a shell script.')

        xrandrlines = [i for i,l in enumerate(lines) if l.strip().startswith('xrandr ')]
        if len(xrandrlines)==0:
            raise FileLoadError('No recognized xrandr command in this shell script.')
        if len(xrandrlines)>1:
            raise FileLoadError('More than one xrandr line in this shell script.')
        self._load_from_commandlineargs(lines[xrandrlines[0]].strip())
        lines[xrandrlines[0]] = '%(xrandr)s'

        return lines


    #################### saving ####################

    def save_to_shellscript_string(self, template=None, additional=None):
        """Return a shellscript that will set the current configuration. Output can be parsed by load_from_string.

        You may specify a template, which must contain a %(xrandr)s parameter and optionally others, which will be filled from the additional dictionary."""
        if not template:
            template = self.DEFAULTTEMPLATE
        template = '\n'.join(template)+'\n'

        d = {'xrandr': "xrandr "+" ".join(self.configuration.commandlineargs())}
        if additional:
            d.update(additional)

        return template%d

    def save_to_x(self):
        self.check_configuration()
        self._run(*self.configuration.commandlineargs())

    def check_configuration(self):
        vmax = self.state.virtual.max

        for on in self.outputs:
            oc = self.configuration.outputs[on]
            #os = self.state.outputs[on]

            if not oc.active:
                continue

            # we trust users to know what they are doing (e.g. widget: will accept current mode, but not offer to change it lacking knowledge of alternatives)
            #if oc.rotation not in os.rotations:
            #    raise InadequateConfiguration("Rotation not allowed.")
            #if oc.mode not in os.modes:
            #    raise InadequateConfiguration("Mode not allowed.")

            x = oc.position[0] + oc.size[0]
            y = oc.position[1] + oc.size[1]

            if x > vmax[0] or y > vmax[1]:
                raise InadequateConfiguration(_("A part of an output is outside the virtual screen."))

            if oc.position[0] < 0 or oc.position[1] < 0:
                raise InadequateConfiguration(_("An output is outside the virtual screen."))

    #################### sub objects ####################

    class State(object):
        """Represents everything that can not be set by xrandr."""
        def __init__(self):
            self.outputs = {}

        def __repr__(self):
            return '<%s for %d Outputs, %d connected>'%(type(self).__name__, len(self.outputs), len([x for x in self.outputs.values() if x.connected]))

        class Output(object):
            def __init__(self, name):
                self.name = name
                self.modes = []

            def __repr__(self):
                return '<%s %r (%d modes)>'%(type(self).__name__, self.name, len(self.modes))

    class Configuration(object):
        """Represents everything that can be set by xrand (and is therefore subject to saving and loading from files)"""
        def __init__(self):
            self.outputs = {}

        def __repr__(self):
            return '<%s for %d Outputs, %d active>'%(type(self).__name__, len(self.outputs), len([x for x in self.outputs.values() if x.active]))

        def commandlineargs(self):
            args = []
            for on,o in self.outputs.items():
                args.append("--output")
                args.append(on)
                if not o.active:
                    args.append("--off")
                else:
                    args.append("--mode")
                    args.append(str(o.mode))
                    args.append("--pos")
                    args.append(str(o.position))
                    args.append("--rotate")
                    args.append(o.rotation)
            return args

        class OutputConfiguration(object):
            def __init__(self, active, geometry, rotation):
                self.active = active
                if active:
                    self.position = geometry.position
                    self.rotation = rotation
                    if rotation.is_odd:
                        self.mode = Size(reversed(geometry.size))
                    else:
                        self.mode = geometry.size
            size = property(lambda self: Size(reversed(self.mode)) if self.rotation.is_odd else self.mode)
