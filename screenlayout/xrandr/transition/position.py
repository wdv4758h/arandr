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

from . import base
from ...auxiliary import Geometry, Position

# FIXME: this needs validation over the complete size parameters, not sure how
# this plays together with scaling etc

class TransitionOutputForPosition(base.BaseTransitionOutput):
    def _initialize_empty(self):
        super(TransitionOutputForPosition, self)._initialize_empty()
        self.position = None

    def serialize(self):
        if self.position is not None:
            return ['--pos', str(self.position)] + super(TransitionOutputForPosition, self).serialize()
        else:
            return super(TransitionOutputForPosition, self).serialize()

    def unserialize(self, args):
        if 'pos' in args:
            self.position = args.pos
            del args.pos
        super(TransitionOutputForPosition, self).unserialize(args)

    def set_any_position(self):
        """Use this if you want to configure a position but don't care which
        one"""
        if self.server_output.active:
            self.position = self.server_output.geometry.position
        else:
            self.position = Position((0, 0))

    def predict_server(self):
        super(TransitionOutputForPosition, self).predict_server()
        if self.position is not None:
            self.predicted_server_output.geometry = Geometry(
                self.position.left,
                self.position.top,
                self.predicted_server_output.geometry.width,
                self.predicted_server_output.geometry.height,
                )

    def _shift(self, delta):
        self.position = Position((self.position.left + delta[0], self.position.top + delta[1]))

    def shove_to_fit(self):
        super(TransitionOutputForPosition, self).shove_to_fit()

        if self.position is None:
            return

        # not using prediction here because it is needlessly heavyweight
        assumed_mode = self.get_configured_mode() or self.server_output.mode

        if assumed_mode is None:
            return # the rare case when position (and not mode) is set and the output was last active on the server

        max_x = self.position.left + assumed_mode.width
        max_y = self.position.top + assumed_mode.height

        virtualsize = self.transition.server.virtual.max

        delta = (virtualsize.width - max_x if max_x > virtualsize.width else 0,
                virtualsize.height - max_y if max_y > virtualsize.height else 0)
        self._shift(delta)

class TransitionForPosition(base.BaseTransition):
    Output = TransitionOutputForPosition

    def shove_to_fit(self):
        super(TransitionForPosition, self).shove_to_fit()

        positioned_outputs = [o for o in self.outputs.values() if o.position is not None]
        if positioned_outputs:
            min_x = min(o.position.left for o in positioned_outputs)
            min_y = min(o.position.top for o in positioned_outputs)

            # don't shove to corner if the outputs are placed in the center of
            # the virtual; xrandr does that, but it makes it hard for the user
            # to move around outputs if they always snap back
            delta = (-min_x if min_x<0 else 0, -min_y if min_y < 0 else 0)

            if delta != (0, 0):
                for o in positioned_outputs:
                    o._shift(delta)
