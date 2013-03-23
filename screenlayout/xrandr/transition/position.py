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
            self.position = Position(0, 0)

class TransitionForPosition(base.BaseTransition):
    Output = TransitionOutputForPosition
