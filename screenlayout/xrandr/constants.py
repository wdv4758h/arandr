from ..auxiliary import Flag
from math import pi

class Rotation(Flag):
    values = ["normal", "left", "inverted", "right"]

    is_odd = property(lambda self: self in ('left', 'right'))
    _angles = {'left':pi/2,'inverted':pi,'right':3*pi/2,'normal':0}
    angle = property(lambda self: Rotation._angles[self])

class Reflection(Flag):
    values = ['xaxis', 'yaxis', 'xyaxis', 'noaxis']

    aliases = {
            # used by parser
            'X axis': 'xaxis',
            'Y axis': 'yaxis',
            'X and Y axis': 'xyaxis',
            'none': 'noaxis',
            None: 'noaxis',
            # used on command line
            'normal': 'noaxis',
            'x': 'xaxis',
            'y':'yaxis',
            'xy': 'xyaxis',
            }

    # slicing own label because there's an 'x' in axis
    x = property(lambda self: 'x' in self[:2])
    y = property(lambda self: 'y' in self[:2])

    def __repr__(self):
        return '<Reflection x=%d y=%d>'%(self.x, self.y)

class ModeFlag(Flag):
    values = ['+HSync', '-HSync', '+VSync', '-VSync', 'Interlace', 'DoubleScan', '+CSync', '-CSync', 'CSync']

class SubpixelOrder(Flag):
    values = ['unknown', 'horizontal rgb', 'horizontal bgr', 'vertical rgb', 'vertical bgr', 'no subpixels']
