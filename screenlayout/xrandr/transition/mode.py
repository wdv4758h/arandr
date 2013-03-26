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
from ...auxiliary import InadequateConfiguration, Geometry

class TransitionOutputForMode(base.BaseTransitionOutput):
    def _initialize_empty(self):
        super(TransitionOutputForMode, self)._initialize_empty()
        self.named_mode = None
        self.precise_mode = None
        self.rate = None
        self.auto = False
        self.off = False

    def validate(self):
        super(TransitionOutputForMode, self).validate()

        if self.precise_mode is not None and (self.rate is not None or self.named_mode is not None):
            raise InadequateConfiguration("Named modes or refresh rates can not be used together with precise mode settings.")

        if self.auto and any(x is not None for x in (self.precise_mode, self.named_mode, self.rate)):
            raise InadequateConfiguration("Switching an output to auto is mutually exclusive with setting a mode.")

        if self.off and (any(x is not None for x in (self.precise_mode, self.named_mode, self.rate)) or self.auto):
            raise InadequateConfiguration("Switching an output off is mutually exclusive with setting a mode.")

    def serialize(self):
        args = super(TransitionOutputForMode, self).serialize()

        if self.precise_mode is not None:
            args += ['--mode', "%#x"%self.precise_mode]

        if self.named_mode is not None:
            args += ['--mode', self.named_mode]

        if self.rate is not None:
            args += ['--rate', str(self.rate)]

        if self.off:
            args += ['--off']

        if self.auto:
            args += ['--auto']

        return args

    def unserialize(self, args):
        if 'mode' in args:
            if args.mode.startswith('0x') and \
                    all(x in '0123456789abcdefABCDEF' for x in args.mode[2:]) and \
                    int(args.mode[2:], 16) in [x.id for x in self.available_modes]:
                self.precise_mode = int(args.mode[2:], 16)
            elif args.mode in [x.name for x in self.available_modes]:
                self.named_mode = args.mode
            else:
                raise FileSyntaxError("Unknown mode: %r"%args.mode)

            del args.mode

        if 'rate' in args:
            self.rate = args.rate
            del args.rate

        if 'auto' in args:
            self.auto = True
            del args.auto

        if 'off' in args:
            self.off = True
            del args.off

        super(TransitionOutputForMode, self).unserialize(args)

    def set_any_mode(self):
        """Use this if you want to configure a mode but don't care which one"""
        if self.named_mode or self.precise_mode:
            return

        self.auto = False
        self.off = False

        if self.server_output.active:
            best_mode = self.server_output.mode
        else:
            best_mode = max(self.server_output.assigned_modes, key=lambda m: (m.is_preferred, m.width * m.height))
        self.named_mode = best_mode.name

    def get_configured_mode(self):
        if self.precise_mode is None and self.named_mode is None:
            return None

        if self.precise_mode:
            return self.precise_mode

        # this will be random to a certain extent, but at least predictable as
        # to which resolution will be chosen. in most cases, all the matching
        # modes will all have the same resolution anyway
        return max((m for m in self.server_output.assigned_modes if m.name == self.named_mode), key=lambda m: (m.is_preferred, m.width * m.height))

    def predict_server(self):
        configuredmode = self.get_configured_mode()
        if self.off:
            self.predicted_server_output.active = False
        if self.auto or configuredmode is not None:
            self.predicted_server_output.active = True

        if configuredmode is not None:
            self.predicted_server_output.geometry = Geometry(
                self.predicted_server_output.geometry.left,
                self.predicted_server_output.geometry.top,
                configuredmode.width,
                configuredmode.height,
                )
class TransitionForMode(base.BaseTransition):
    Output = TransitionOutputForMode
