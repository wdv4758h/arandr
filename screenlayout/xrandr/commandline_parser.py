from ..auxiliary import Position, Size
from .helpers import Transformation

import argparse
from pprint import pprint

class GroupingMixin(object):
    group_to = property(lambda self: self.group_by + '_grouped')

    def __call__(self, parser, namespace, values, option_string=None):
        if not hasattr(namespace, self.group_to):
            setattr(namespace, self.group_to, {})
        current_group = getattr(namespace, self.group_by)
        if current_group is None:
            raise parser.error("Option %r must be preceded by an option %r."%(self.dest, self.group_by))
        current_namespace = getattr(namespace, self.group_to).setdefault(current_group, argparse.Namespace())
        #print "calling grouping", self, parser, namespace, values, option_string
        return super(GroupingMixin, self).__call__(parser, current_namespace, values, option_string)

    @classmethod
    def boost_object(cls, o):
        o.__class__ = type("%s+%s"%(cls.__name__, type(o).__name__), (cls, type(o)), {})

class GroupingByOptionMixin(GroupingMixin):
    group_by = 'output'

def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--noprimary", action='store_true')

    parser.add_argument("--output")

    per_output = parser.add_argument_group("per output commands")

    [(GroupingByOptionMixin.boost_object(x), setattr(x, 'default', argparse.SUPPRESS)) for x in (
        per_output.add_argument("--auto", action='store_true'),
        per_output.add_argument("--mode"),
        per_output.add_argument("--pos", type=Position),
        per_output.add_argument("--rate", type=float),
        per_output.add_argument("--reflect", choices=['normal', 'x', 'y', 'xy']),
        per_output.add_argument("--rotate", choices=['normal', 'left', 'right', 'inverted']),
        per_output.add_argument("--set", nargs=2),
        per_output.add_argument("--scale", type=Size),
        per_output.add_argument("--transform", type=Transformation.from_comma_separated),
        per_output.add_argument("--off", action='store_true'),
        per_output.add_argument("--panning"),
        per_output.add_argument("--primary", action='store_true'),
    )]

    return parser

if __name__ == "__main__":
    print get_parser().parse_args()
