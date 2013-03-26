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
import copy

class PredictedServer(object):
    def __init__(self, original_server):
        for k,v in vars(original_server).items():
            if k == 'context':
                continue # a predicted server can't do anything, it's just for information
            setattr(self, k, v)

class BaseTransitionOutput(object):
    transition = property(lambda self: self._transition())
    server_output = property(lambda self: self.transition.server.outputs[self.name])
    predicted_server_output = property(lambda self: self.transition.predicted_server.outputs[self.name])

    available_modes = property(lambda self: self.server_output.assigned_modes) # when implementing new modes, and a transition includes new modes, include them here

    def __init__(self, name, transition):
        self.name = name
        self._transition = weakref.ref(transition)

        self._initialize_empty()

    def _initialize_empty(self):
        """Analogous to ``BaseTransition._initialize_empty``"""

    def serialize(self):
        """Analogous to ``BaseTransition.serialize``"""
        return []

    def shove_to_fit(self):
        """Analogous to ``BaseTransition.shove_to_fit``"""

    def validate(self):
        """Analogous to ``BaseTransition.validate``"""

    def unserialize(self, args):
        """Analogous to ``BaseTransition.unserialize``"""

        if vars(args):
            raise FileSyntaxError("Unserialized arguments remain: %r"%args)

    def predict_server(self):
        """Update .predicted_server_output as BaseTransition.predict_server
        does. Do not call this directly unless you know what you're doing
        (instead, call the complete transition's predict_server function)."""
class BaseTransition(object):
    """Transition instructions for one X server's state to a new one; basically
    an internal representation of an ``xrandr`` invocation. See
    ``README.development`` for details.

    Final ``Transition`` objects are assembled by diamond heritage, make sure
    to use super properly."""
    def __init__(self, server):
        self.server = server

        self._initialize_empty()

    def _initialize_empty(self):
        """Fill self's properties for a no-op transition."""

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

    def shove_to_fit(self):
        """Give a transition a chance to modify itself if it is in a state that
        would not pass validation, but can easily be bent gracefully.

        This is not intended for fixing things that can be easily set at
        programming time (like removing --auto when --off gets set), but to
        primarily for adapting to impossible user requests (like outputs placed
        outside the virtual, which is currently the only implemented
        functionality)."""
        for o in self.outputs.values():
            o.shove_to_fit()

    def validate(self):
        """Check if a transition is currently valid (can be applied to the
        server it is bound to). This usually won't check for *anything* that
        could go wrong (eg wrong types assigned to properties, so serialization
        would fail), but checks for everything a developer using Transitions
        can not be expected to check in advance (e.g. if a particular rotation
        is possible with that output at all, if the server's virtual is
        respected, etc.).

        Raises auxiliary.InadequateConfiguration exceptions on invalid
        configurations."""
        for o in self.outputs.values():
            o.validate()

    def serialize(self):
        """Convert a Transition to arguments to an ``xrandr`` call. When
        implementing, take care to create a joint list of your own arguments
        and what super() returned."""
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
        and finally call super.

        Raises an ``auxiliary.FileSyntaxError`` when the command line can not
        be read."""

        del args.output # technical remnant from argument parsing (--output_
        if 'output_grouped' in args:
            for output_name, output_args in args.output_grouped.items():
                if output_name not in self.outputs:
                    raise FileSyntaxError("XRandR command mentions unknown output %r"%output_name)
                self.outputs[output_name].unserialize(output_args)
            del args.output_grouped # them being empty gets checked by the individual output objects

        if vars(args):
            raise FileSyntaxError("Unhandled arguments remain: %r"%args)

    def predict_server(self):
        """Update .predicted_server to reflect what after applying the
        transition, the server is supposed to look like."""

        self.predicted_server = PredictedServer(self.server)

        for output in self.outputs.values():
            output.predict_server()

    def __repr__(self):
        return '<%s bound to %s: %s>'%(type(self).__name__, self.server, " ".join(self.serialize() or ["no changes"]))

    Output = BaseTransitionOutput
