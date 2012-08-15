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

"""Exceptions and generic classes"""

from math import pi
from collections import namedtuple

class FileLoadError(Exception): pass
class FileSyntaxError(FileLoadError):
    """A file's syntax could not be parsed."""

class XRandRParseError(Exception):
    """The output of XRandR didn't fulfill the program's expectations"""

class InadequateConfiguration(Exception):
    """A configuration is incompatible with the current state of X."""


class BetterList(list):
    """List that can be split like a string"""
    def indices(self, item):
        i = -1
        while True:
            try:
                i = self.index(item, i+1)
            except ValueError:
                break
            yield i

    def split(self, item):
        indices = list(self.indices(item))
        yield self[:indices[0]]
        for x in (self[a+1:b] for (a,b) in zip(indices[:-1], indices[1:])):
            yield x
        yield self[indices[-1]+1:]


class Size(tuple):
    """2-tuple of width and height that can be created from a '<width>x<height>' string"""
    def __new__(cls, arg):
        if isinstance(arg, basestring):
            arg = [int(x) for x in arg.split("x")]
        arg = tuple(arg)
        if len(arg) != 2:
            raise ValueError("Sizes use XxY format")
        return super(Size, cls).__new__(cls, arg)

    width = property(lambda self:self[0])
    height = property(lambda self:self[1])
    def __str__(self):
        return "%dx%d"%self

class Position(tuple):
    """2-tuple of left and top that can be created from a '<left>x<top>' string"""
    def __new__(cls, arg):
        if isinstance(arg, basestring):
            arg = [int(x) for x in arg.split("x")]
        arg = tuple(arg)
        if len(arg) != 2:
            raise ValueError("Positions use XxY format")
        return super(Position, cls).__new__(cls, arg)

    left = property(lambda self:self[0])
    top = property(lambda self:self[1])
    def __str__(self):
        return "%dx%d"%self

class Geometry(tuple):
    """4-tuple of width, height, left and top that can be created from an XParseGeometry style string"""
    # FIXME: use XParseGeometry instead of an own incomplete implementation
    def __new__(cls, width, height=None, left=None, top=None):
        if isinstance(width, basestring):
            width,rest = width.split("x")
            height,left,top = rest.split("+")
        return super(Geometry, cls).__new__(cls, (int(width), int(height), int(left), int(top)))

    def __str__(self):
        return "%dx%d+%d+%d"%self

    width = property(lambda self:self[0])
    height = property(lambda self:self[1])
    left = property(lambda self:self[2])
    top = property(lambda self:self[3])

    position = property(lambda self:Position(self[2:4]))
    size = property(lambda self:Size(self[0:2]))

class FlagClass(type):
    def __init__(self, name, bases, dict):
        super(FlagClass, self).__init__(name, bases, dict)

        if 'values' in dict: # guard agains error on Flag class
            self.values = [super(FlagClass, self).__call__(x) for x in dict['values']]

            for v in self.values:
                setattr(self, str.__str__(v), v)

    def __call__(self, label):
        if label in self.values:
            return self.values[self.values.index(label)]

        if hasattr(self, 'aliases') and label in self.aliases:
            return self(self.aliases[label])

        raise ValueError("No such %s flag: %r"%(self.__name__, label))

class Flag(str):
    __metaclass__ = FlagClass

    def __repr__(self):
        return '<%s "%s">'%(type(self).__name__, self)
