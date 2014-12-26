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

from collections import namedtuple

class Mode(namedtuple("BaseMode", [
        "pclk",
        "hdisp", "hsyncstart", "hsyncend", "htotal",
        "vdisp", "vsyncstart", "vsyncend", "vtotal",
        "flags"
        ])):
    """Representation of an X mode line"""

    hsync = property(lambda self: self.pclk * 1000 / self.htotal)
    vsync = property(lambda self: self.hsync * 1000 / self.vtotal)
    refreshrate = vsync # just an alias, so it's available both on the technical term and the common one

    width = property(lambda self: self.hdisp) # shortcut
    height = property(lambda self: self.vdisp) # shortcut
    size = property(lambda self: Size(self.width, self.height))

    def __repr__(self):
        return '<%s %s>'%(type(self).__name__, tuple.__repr__(self))

class Transformation(namedtuple('_Transformation', tuple('abcdefghi'))):
    """9-tuple describing a transformation matrix"""

    @classmethod
    def from_comma_separated(cls, string):
        return cls(*list(map(float, string.split(","))))

    def __repr__(self):
        return "<%s %s>"%(type(self).__name__, ",".join(map(str, self)))
