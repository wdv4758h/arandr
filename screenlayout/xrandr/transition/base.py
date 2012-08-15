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

class BaseTransitionOutput(object):
    transition = property(lambda self: self._transition())
    server_output = property(lambda self: self.transition.server.outputs[self.name])
    available_modes = property(lambda self: self.server_output.assigned_modes) # when implementing new modes, and a transition includes new modes, include them here

    def __init__(self, name, transition):
        self.name = name
        self._transition = weakref.ref(transition)

        self._initialize_empty()

    def _initialize_empty(self):
        pass

    def serialize(self):
        return []

    def validate(self):
        pass

    def unserialize(self, args):
        if vars(args):
            raise FileSyntaxError("Unserialized arguments remain: %r"%args)
class BaseTransition(object):
    def __init__(self, server):
        self.server = server

        self._initialize_empty()

    def _initialize_empty(self):
        bases = []
        for transition_class in type(self).mro():
            if not hasattr(transition_class, "Output"):
                continue
            output_class = transition_class.Output
            if output_class in bases:
                continue
            bases.append(output_class)
        my_output_class = type("%sOutput"%type(self).__name__, tuple(bases), {})

        self.outputs = dict((name, my_output_class(name, self)) for name in self.server.outputs)

    def validate(self):
        for o in self.outputs.values():
            o.validate()

    def serialize(self):
        self.validate()

        ret = []
        for output_name, output in self.outputs.items():
            serialized_from_output = output.serialize()
            if serialized_from_output:
                ret.extend(['--output', output_name] + serialized_from_output)
        return ret

    def unserialize(self, args):
        """Load the args object created by a
        screenlayout.xrandr.commandline_parser argparser into a Transition.
        This raises an exception if any arguments remain unparsed. Thus, mixin
        objects have to consume and remove their arguments from the args object
        and finally call super."""

        del args.output # technical remnant
        if 'output_grouped' in args:
            for output_name, output_args in args.output_grouped.items():
                if output_name not in self.outputs:
                    raise FileSyntaxError("XRandR command mentions unknown output %r"%output_name)
                self.outputs[output_name].unserialize(output_args)
            del args.output_grouped # them being empty gets checked by the individual output objects

        if vars(args):
            raise FileSyntaxError("Unhandled arguments remain: %r"%args)

    def __repr__(self):
        return '<%s bound to %s: %s>'%(type(self).__name__, self.server, " ".join(self.serialize() or ["no changes"]))

    Output = BaseTransitionOutput
