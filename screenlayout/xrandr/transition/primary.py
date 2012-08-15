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

class TransitionOutputForPrimary(base.BaseTransitionOutput):
    def serialize(self):
        if self.transition.primary is self:
            return ['--primary'] + super(TransitionOutputForPrimary, self).serialize()
        else:
            return super(TransitionOutputForPrimary, self).serialize()

    def unserialize(self, args):
        if 'primary' in args:
            if args.primary:
                self.transition.primary = self
            del args.primary

        super(TransitionOutputForPrimary, self).unserialize(args)
class TransitionForPrimary(base.BaseTransition):
    def _initialize_empty(self):
        super(TransitionForPrimary, self)._initialize_empty()
        self.primary = None

    NO_PRIMARY = object()

    def serialize(self):
        if self.primary is self.NO_PRIMARY:
            return ['--noprimary'] + super(TransitionForPrimary, self).serialize()
        else:
            # if a primary output is explicitly set, it will be handled by the output serialization
            return super(TransitionForPrimary, self).serialize()

    def unserialize(self, args):
        if args.noprimary:
            self.primary = self.NO_PRIMARY
        del args.noprimary

        super(TransitionForPrimary, self).unserialize(args)

    Output = TransitionOutputForPrimary
