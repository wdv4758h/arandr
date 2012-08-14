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

"""Wrapper around command line xrandr"""

import re
import warnings

from collections import namedtuple

from .. import executions
from ..executions.context import local as local_context

from ..auxiliary import BetterList, Size, Position, Geometry, FileLoadError, FileSyntaxError, InadequateConfiguration, XRandRParseError

from .constants import Rotation, Reflection, ModeFlag, SubpixelOrder

import gettext
gettext.install('arandr')

SHELLSHEBANG='#!/bin/sh'

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

    def __repr__(self):
        return '<%s %s>'%(type(self).__name__, tuple.__repr__(self))

class Server(object):
    def __init__(self, context=local_context, force_version=False):
        """Create proxy object and check for xrandr at the given
        executions.context. Fail with untested versions unless `force_version`
        is True."""

        self.context = context

        self.version = self.Version(self._output_help(), self._output('--version'))

        if not force_version and not self.version.program_version.startswith(('1.2', '1.3', )):
            raise Exception("XRandR 1.2/1.3 required.")

        self.load(self._output('--query', '--verbose'))

        def __repr__(self):
            return "<Version server %r, program %r>"%(self.server_version, self.program_version)

    #################### calling xrandr ####################

    def _output(self, *args):
        # FIXME: the exception thrown should be beautiful enough to be presentable
        try:
            return executions.ManagedExecution(("xrandr",) + args, context=self.context).read()
        except executions.CalledProcessError as e:
            raise Exception("XRandR returned error code %d: %s"%(e.returncode, e.output))

    def _output_help(self):
        out, err, code = executions.ManagedExecution(("xrandr", "--help"), context=self.context).read_with_error()

        return out + err

    #################### loading ####################

    def load(self, verbose_output):
        lines = verbose_output.split('\n')

        screenline = lines.pop(0)

        self._load_parse_screenline(screenline)

        output_blocks = []

        if lines.pop(-1) != "":
            raise XRandRParseError("Output doesn't end with a newline.")

        self.outputs = {}
        self.modes = {}

        while lines:
            line = lines.pop(0)
            if line.startswith((' ', '\t')):
                raise XRandRParseError("Expected new output section, got whitespace.")

            headline = line
            details = []
            modes = []

            while lines and lines[0].startswith('\t'):
                details.append(lines.pop(0)[1:])

            while lines and lines[0].startswith(' '):
                modes.append(lines.pop(0)[2:])

            # headline, details and modes filled; interpret the data before
            # going through this again

            output = self.Output(headline, details)
            self.outputs[output.name] = output

            self._load_modes(modes, output)

    def _load_parse_screenline(self, screenline):
        ssplit = screenline.split(" ")

        ssplit_expect = ["Screen",None,"minimum",None,"x",None,"current",None,"x",None,"maximum",None,"x",None]

        if not all(a==b for (a,b) in zip(ssplit,ssplit_expect) if b is not None):
            raise XRandRParseError("Unexpected screen line: %r"%screenline)

        # the screen number ssplit[1] is discarded

        self.virtual = self.Virtual(
                min=Size((int(ssplit[3]),int(ssplit[5][:-1]))),
                current=Size((int(ssplit[7]),int(ssplit[9][:-1]))),
                max=Size((int(ssplit[11]),int(ssplit[13])))
                )

    def _load_modes(self, data, assign_to_output=None):
        if len(data) % 3 != 0:
            raise XRandRParseError("Unknown mode line format (not a multiple of 3)")

        for lines in zip(data[0::3], data[1::3], data[2::3]):
            mode = self.ServerAssignedMode.parse_xrandr(lines)

            if mode.id in self.modes:
                if mode != self.modes[mode.id]:
                    raise XRandRParseError("Mode shows up twice with different data: %s"%mode.id)
                else:
                    mode = self.modes[mode.id]
            else:
                self.modes[mode.id] = mode

            if assign_to_output is not None:
                assign_to_output.assigned_modes.append(mode)

    #################### sub objects ####################

    class Version(object):
        """Parser and representation of xrandr versions, handling both program
        and server version."""

        server_version = None
        program_version = None

        def __init__(self, help_string, version_string):
            SERVERVERSION_PREFIX = 'Server reports RandR version'
            PROGRAMVERSION_PREFIX = 'xrandr program version'

            lines = [l for l in version_string.split('\n') if l]

            for l in lines[:]:
                if l.startswith(SERVERVERSION_PREFIX):
                    self.server_version = l[len(SERVERVERSION_PREFIX):].strip()
                    lines.remove(l)
                if l.startswith(PROGRAMVERSION_PREFIX):
                    self.program_version = l[len(PROGRAMVERSION_PREFIX):].strip()
                    lines.remove(l)

            if lines:
                warnings.warn("XRandR version interpretation has leftover lines: %s"%lines)

            if self.server_version is None:
                raise XRandRParseError("XRandR did not report a server version.")

            if not self.program_version:
                # before 1.3.1, the program version was not reported. it can be
                # distinguished from older versions by the the presence of
                # --output flag in help.
                if '--output' in help_string:
                    if '--primary' in help_string:
                        self.program_version = '1.3.0' # or 1.2.99.x
                    else:
                        self.program_version = '1.2.x'
                else:
                    self.program_version = '< 1.2'

    Virtual = namedtuple("Virtual", ['min', 'current', 'max'])

    class ServerAssignedMode(Mode):
        XRANDR_EXPRESSIONS = [
                re.compile("^(?P<name>.+) +"
                    "\(0x(?P<mode_id>[0-9a-fA-F]+)\) +"
                    "(?P<pixelclock>[0-9]+\.[0-9]+)MHz"
                    "(?P<flags>( ([+-][HVC]Sync|Interlace|DoubleScan|CSync))*)"
                    ".*$"),
                re.compile("^      h:"
                    " +width +(?P<hwidth>[0-9]+)"
                    " +start +(?P<hstart>[0-9]+)"
                    " +end +(?P<hend>[0-9]+)"
                    " +total +(?P<htotal>[0-9]+)"
                    " +skew +(?P<hskew>[0-9]+)"
                    " +clock +(?P<hclock>[0-9]+\.[0-9]+)KHz"
                    "$"),
                re.compile("^      v:"
                    " +height +(?P<vheight>[0-9]+)"
                    " +start +(?P<vstart>[0-9]+)"
                    " +end +(?P<vend>[0-9]+)"
                    " +total +(?P<vtotal>[0-9]+)"
                    " +clock +(?P<vclock>[0-9]+\.[0-9]+)Hz"
                    "$"),
                ]

        @classmethod
        def parse_xrandr(cls, lines):
            matches = [r.match(l) for (r, l) in zip(cls.XRANDR_EXPRESSIONS, lines)]
            if any(m is None for m in matches):
                raise XRandRParseError("Can not parse mode line %r"%lines[matches.index(None)])
            matchdata = reduce(lambda a, b: dict(a, **b), (m.groupdict() for m in matches))

            ret = cls(
                    float(matchdata['pixelclock']),
                    int(matchdata['hwidth']),
                    int(matchdata['hstart']),
                    int(matchdata['hend']),
                    int(matchdata['htotal']),
                    int(matchdata['vheight']),
                    int(matchdata['vstart']),
                    int(matchdata['vend']),
                    int(matchdata['vtotal']),
                    [ModeFlag(x) for x in matchdata['flags'].split()],
                    )

            ret.name = matchdata['name']
            ret.id = int(matchdata['mode_id'], 16)

            # not comparing hclock and vclock values, as they can be rather
            # much off (>1%) due to rounded values being displayed by xrandr. 
            #
            # skew is dropped because i have no idea what it is or what it does
            # in the modeline.

            return ret

        def __repr__(self):
            return "<%s %r (%#x) %s>"%(type(self).__name__, self.name, self.id, tuple.__repr__(self))

    class Output(object):
        """Parser and representation of an output of a Server"""

        def __init__(self, headline, details):
            self.assigned_modes = [] # filled with modes by the server parser, as it keeps track of the modes
            self.properties = {}

            self._parse_headline(headline)
            self._parse_details(details)

        HEADLINE_EXPRESSION = re.compile(
                "^(?P<name>.*) (?P<connection>connected|disconnected|unknown connection) "
                "((?P<current_geometry>[0-9-+x]+) \(0x(?P<current_mode>[0-9a-fA-F]+)\) (?P<current_rotation>normal|left|inverted|right) ((?P<current_reflection>none|X axis|Y axis|X and Y axis) )?)?"
                "\("
                "(?P<supported_rotations>((normal|left|inverted|right) ?)*)"
                "(?P<supported_reflections>((x axis|y axis) ?)*)"
                "\)"
                "( (?P<physical_x>[0-9]+)mm x (?P<physical_y>[0-9]+)mm)?"
                "$")

        def _parse_headline(self, headline):
            headline_parsed = self.HEADLINE_EXPRESSION.match(headline)
            if headline_parsed is None:
                raise XRandRParseError("Unmatched headline: %r."%headline)
            headline_parsed = headline_parsed.groupdict()

            self.name = headline_parsed['name']
            self.active = headline_parsed['connection'] in ('connected', 'unknown connection')

            if headline_parsed['current_mode']:
                self.active = True
                self.mode_number = int(headline_parsed['current_mode'], 16)
                try:
                    self.geometry = Geometry(headline_parsed['current_geometry'])
                except ValueError:
                    raise XRandRParseError("Can not parse geometry %r"%headline_parsed['current_geometry'])

                # the values were already checked for in the regexp
                self.rotation = Rotation(headline_parsed['current_rotation'])
                # the values were already checked, and the values are aliases in the Reflection class
                self.reflection = Reflection(headline_parsed['current_reflection'])
            else:
                self.active = False
                self.mode_number = None
                self.rotation = None
                self.reflection = None

            self.supported_rotations = map(Rotation, headline_parsed['supported_rotations'].split())
            self.supported_reflections = [Reflection.noaxis]
            if 'x axis' in headline_parsed['supported_reflections']:
                self.supported_reflections.append(Reflection.xaxis)
            if 'y axis' in headline_parsed['supported_reflections']:
                self.supported_reflections.append(Reflection.yaxis)
            if 'x axis' in headline_parsed['supported_reflections'] and 'y axis' in headline_parsed['supported_reflections']:
                self.supported_reflections.append(Reflection.xyaxis)

            if headline_parsed['physical_x'] is not None:
                self.physical_x = int(headline_parsed['physical_x'])
                self.physical_y = int(headline_parsed['physical_y'])
            else:
                self.physical_x = self.physical_y = None

        def _parse_details(self, details):
            while details:
                current_detail = [details.pop(0)]
                while details and details[0].startswith((' ', '\t')):
                    current_detail.append(details.pop(0))
                self._parse_detail(current_detail)

        def _parse_detail(self, detail):
            if ':' not in detail[0]:
                raise XRandRParseError("Detail doesn't contain a recognizable label: %r."%detail[0])
            label = detail[0][:detail[0].index(':')]

            detail[0] = detail[0][len(label)+1:]

            if label.lower() in self.simple_details:
                mechanism = self.simple_details[label.lower()]
                try:
                    data, = detail
                    data = data.strip()
                    if isinstance(mechanism, tuple) and not mechanism[0](data):
                        raise ValueError()

                    setattr(self, label, mechanism[1](data) if isinstance(mechanism, tuple) else mechanism(data))
                except ValueError:
                    raise XRandRParseError("Can not evaluate detail %s."%label)

            elif label == 'Transform':
                pass # FIXME
            elif label == 'Panning':
                pass # FIXME
            elif label == 'Tracking':
                pass # FIXME
            elif label == 'Border':
                pass # FIXME

            else:
                self._parse_property_detail(label, detail)

        INTEGER_DETAIL_EXPRESSION = re.compile('^ +(?P<decimal>-?[0-9]+) +\(0x(?P<hex>[0-9a-fA-F]+)\)'
                '(\trange: +\((?P<min>-?[0-9]+),(?P<max>-?[0-9]+)\))?$')

        def _parse_property_detail(self, label, detail):
            print "trying to parse detail", label, repr(detail)

            if detail[0] == '':
                data = "".join([x.strip() for x in detail[1:]]).decode('hex')
                changable = None
            # counting \t against multi-value type=XA_ATOM format=32 data, not
            # implemented for lack of examples and ways of setting it (?)
            elif detail[0].startswith('\t') and detail[0].count('\t') == 1:
                data = detail[0][detail[0].index('\t'):].strip()
                changable = None

                if len(detail) > 1:
                    supported_string = '\tsupported:'
                    if detail[1].startswith(supported_string):
                        detail[1] = detail[1][len(supported_string):]
                        detail[2:] = [x.lstrip('\t') for x in detail[2:]]

                        alldetail = "".join(detail[1:])

                        if any(len(x) % 13 != 0 for x in detail[1:]) or alldetail[::13].strip(" ") != "":
                            warnings.warn("Can not read supported values for detail %r"%label)

                        else:
                            changable = [alldetail[i*13:(i+1)*13].strip() for i in range(len(alldetail)//13)]
                    else:
                        warnings.warn("Unhandled data in detail %r"%label)

            elif len(detail) == 1 and self.INTEGER_DETAIL_EXPRESSION.match(detail[0]) is not None:
                matched = self.INTEGER_DETAIL_EXPRESSION.match(detail[0]).groupdict()

                data = int(matched['decimal'])
                # ignoring hex value; it'd just be a hassle to make python give
                # me a machine-dependent version of the negative integer, and
                # really, why bother, what could possibly be wrong?
                if matched['min'] is not None and matched['max'] is not None:
                    changable = xrange(int(matched['min']), int(matched['max'])+1)
                else:
                    changable = None

            else:
                warnings.warn("Can not interpred detail %r"%label)
                return

            self.properties[label] = (data, changable)


        # simple patterns for _parse_detail
        #
        # this is matched against lowercased identifiers by _parse_detail for
        # bulk details that don't require more clever thinking. if the first
        # lambda doesn't return true or either of them throws a ValueError, an
        # XRandRParseError is raised. the second expression's return value is
        # assigned to the output object under the key's name. if just a single
        # lambda, it acts like the second one.
        simple_details = {
                'identifier': (lambda data: data[:2] == '0x', lambda data: int(data[2:], 16)),
                'timestamp': int,
                'subpixel': SubpixelOrder,
                'gamma': (lambda data: data.count(':') == 2, lambda data: [float(x) for x in data.split(':')]),
                'brightness': float,
                'clones': str, # FIXME, which values does that take?
                'crtc': int,
                'crtcs': lambda data: [int(x) for x in data.split()],
                }

class OldStuff(object):
    # old stuff that is lingering in the xrandr backend rewrite


    def load_from_string(self, data):
        data = data.replace("%","%%")
        lines = data.split("\n")
        if lines[-1] == '': lines.pop() # don't create empty last line

        if lines[0] != SHELLSHEBANG:
            raise FileLoadError('Not a shell script.')

        xrandrlines = [i for i,l in enumerate(lines) if l.strip().startswith('xrandr ')]
        if len(xrandrlines)==0:
            raise FileLoadError('No recognized xrandr command in this shell script.')
        if len(xrandrlines)>1:
            raise FileLoadError('More than one xrandr line in this shell script.')
        self._load_from_commandlineargs(lines[xrandrlines[0]].strip())
        lines[xrandrlines[0]] = '%(xrandr)s'

        return lines

    def _load_from_commandlineargs(self, commandline):
        self.load_from_x()

        args = BetterList(commandline.split(" "))
        if args.pop(0) != 'xrandr':
            raise FileSyntaxError()
        options = dict((a[0], a[1:]) for a in args.split('--output') if a) # first part is empty, exclude empty parts

        for on,oa in options.items():
            o = self.configuration.outputs[on]
            if oa == ['--off']:
                o.active = False
            else:
                if len(oa)%2 != 0:
                    raise FileSyntaxError()
                parts = [(oa[2*i],oa[2*i+1]) for i in range(len(oa)//2)]
                for p in parts:
                    if p[0] == '--mode':
                        o.mode = Size(p[1])
                    elif p[0] == '--pos':
                        o.position = Position(p[1])
                    elif p[0] == '--rotate':
                        if p[1] not in ROTATIONS:
                            raise FileSyntaxError()
                        o.rotation = Rotation(p[1])
                    else:
                        raise FileSyntaxError()
                o.active = True


    #################### saving ####################

    def save_to_shellscript_string(self, template=None, additional=None):
        """Return a shellscript that will set the current configuration. Output can be parsed by load_from_string.

        You may specify a template, which must contain a %(xrandr)s parameter and optionally others, which will be filled from the additional dictionary."""
        if not template:
            template = self.DEFAULTTEMPLATE
        template = '\n'.join(template)+'\n'

        d = {'xrandr': "xrandr "+" ".join(self.configuration.commandlineargs())}
        if additional:
            d.update(additional)

        return template%d

    def save_to_x(self):
        self.check_configuration()
        self._run(*self.configuration.commandlineargs())

    def check_configuration(self):
        vmax = self.state.virtual.max

        for on in self.outputs:
            oc = self.configuration.outputs[on]
            #os = self.state.outputs[on]

            if not oc.active:
                continue

            # we trust users to know what they are doing (e.g. widget: will accept current mode, but not offer to change it lacking knowledge of alternatives)
            #if oc.rotation not in os.rotations:
            #    raise InadequateConfiguration("Rotation not allowed.")
            #if oc.mode not in os.modes:
            #    raise InadequateConfiguration("Mode not allowed.")

            x = oc.position[0] + oc.size[0]
            y = oc.position[1] + oc.size[1]

            if x > vmax[0] or y > vmax[1]:
                raise InadequateConfiguration(_("A part of an output is outside the virtual screen."))

            if oc.position[0] < 0 or oc.position[1] < 0:
                raise InadequateConfiguration(_("An output is outside the virtual screen."))

    #################### sub objects ####################

    class State(object):
        """Represents everything that can not be set by xrandr."""
        def __init__(self):
            self.outputs = {}

        def __repr__(self):
            return '<%s for %d Outputs, %d connected>'%(type(self).__name__, len(self.outputs), len([x for x in self.outputs.values() if x.connected]))

        class Output(object):
            def __init__(self, name):
                self.name = name
                self.modes = []

            def __repr__(self):
                return '<%s %r (%d modes)>'%(type(self).__name__, self.name, len(self.modes))

    class Configuration(object):
        """Represents everything that can be set by xrand (and is therefore subject to saving and loading from files)"""
        def __init__(self):
            self.outputs = {}

        def __repr__(self):
            return '<%s for %d Outputs, %d active>'%(type(self).__name__, len(self.outputs), len([x for x in self.outputs.values() if x.active]))

        def commandlineargs(self):
            args = []
            for on,o in self.outputs.items():
                args.append("--output")
                args.append(on)
                if not o.active:
                    args.append("--off")
                else:
                    args.append("--mode")
                    args.append(str(o.mode))
                    args.append("--pos")
                    args.append(str(o.position))
                    args.append("--rotate")
                    args.append(o.rotation)
            return args

        class OutputConfiguration(object):
            def __init__(self, active, geometry, rotation):
                self.active = active
                if active:
                    self.position = geometry.position
                    self.rotation = rotation
                    if rotation.is_odd:
                        self.mode = Size(reversed(geometry.size))
                    else:
                        self.mode = geometry.size
            size = property(lambda self: Size(reversed(self.mode)) if self.rotation.is_odd else self.mode)

class Transition(object):
    DEFAULTTEMPLATE = [SHELLSHEBANG, '%(xrandr)s']

