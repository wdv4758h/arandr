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

import warnings
from collections import namedtuple
import re

from .constants import Rotation, Reflection, ModeFlag, SubpixelOrder, ConnectionStatus
from .. import executions
from ..executions.context import local as local_context
from ..auxiliary import Size, Geometry, XRandRParseError
from ..polygon import ConvexPolygon

from .helpers import Mode
from functools import reduce

class Server(object):
    def __init__(self, context=local_context, force_version=False):
        """Create proxy object and check for xrandr at the given
        executions.context. Fail with untested versions unless `force_version`
        is True."""

        self.context = context

        self.version = self.Version(self._output_help(), self._output('--version'))

        if not force_version and not self.version.program_version.startswith(('1.2', '1.3', '1.4', )):
            raise Exception("XRandR 1.2 to 1.4 required.")

        self.load(self._output('--query', '--verbose'))

    #################### calling xrandr ####################

    def _output(self, *args):
        # FIXME: the exception thrown should already be beautiful enough to be presentable
        try:
            return executions.ManagedExecution(("xrandr",) + args, context=self.context).read()
        except executions.CalledProcessError as e:
            raise Exception("XRandR returned error code %d: %s"%(e.returncode, e.output))

    def _output_help(self):
        out, err, code = executions.ManagedExecution(("xrandr", "--help"), context=self.context).read_with_error()

        return out + err

    def apply(self, transition):
        """Execute the transition on the connected server. The server
        object is probably not recent after this and should be recreated."""

        self._output(*transition.serialize())

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

        self.primary = None

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

            primary = [] # hack to get the information about an output being primary out and set it later
            def setpri(): primary.append(True)
            output = self.Output(headline, details, setpri)
            if primary:
                self.primary = output
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
            mode = self.ServerMode.parse_xrandr(lines)

            if mode.id in self.modes:
                if mode != self.modes[mode.id]:
                    raise XRandRParseError("Mode shows up twice with different data: %s"%mode.id)
                else:
                    mode = self.modes[mode.id]
            else:
                self.modes[mode.id] = mode

            if assign_to_output is not None:
                assign_to_output.assigned_modes.append(mode)

            if assign_to_output is not None and assign_to_output.active == True and assign_to_output.mode_number == None:
                # old xrandr version (< 1.2.2) workaround
                if mode.width == assign_to_output.geometry.width and mode.height == assign_to_output.geometry.height:
                    assign_to_output.mode_number = mode.id

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

        def at_least_program_version(self, major, minor):
            if major < 1:
                return True

            if major > 1:
                return False

            if minor < 3:
                raise ValueError("Can't check for that early version numbers for lack of implementation")

            if '<' in self.program_version or 'x' in self.program_version:
                return False

            parsed_version = tuple(map(int, self.program_version.split(".")))

            return (major, minor, 0) <= parsed_version

        def __repr__(self):
            return "<Version server %r, program %r>"%(self.server_version, self.program_version)

    Virtual = namedtuple("Virtual", ['min', 'current', 'max'])

    class ServerMode(Mode):
        XRANDR_EXPRESSIONS = [
                re.compile("^(?P<name>.+) +"
                    "\(0x(?P<mode_id>[0-9a-fA-F]+)\) +"
                    "(?P<pixelclock>[0-9]+\.[0-9]+)MHz"
                    "(?P<flags>( ([+-][HVC]Sync|Interlace|DoubleScan|CSync))*)"
                    "(?P<serverflags>( (\\*current|\\+preferred))*)"
                    "(?P<garbage>.*)$"),
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

            if matchdata['garbage']:
                warnings.warn("Unparsed part of line: %r"%matchdata['garbage'])

            ret.is_preferred = '+preferred' in matchdata['serverflags']
            ret.is_current = '*current' in matchdata['serverflags']

            ret.name = matchdata['name']
            ret.id = int(matchdata['mode_id'], 16)

            # not comparing hclock and vclock values, as they can be rather
            # much off (>1%) due to rounded values being displayed by xrandr. 
            #
            # skew is dropped because i have no idea what it is or what it does
            # in the modeline.

            return ret

        def __repr__(self):
            return "<%s %r (%#x) %s%s%s>"%(type(self).__name__, self.name, self.id, tuple.__repr__(self), " preferred" if self.is_preferred else "", " current" if self.is_current else "")

    class Output(object):
        """Parser and representation of an output of a Server"""

        def __init__(self, headline, details, primary_callback):
            self.assigned_modes = [] # filled with modes by the server parser, as it keeps track of the modes
            self.properties = {}

            self._parse_headline(headline, primary_callback)
            self._parse_details(details)

        HEADLINE_EXPRESSION = re.compile(
                "^(?P<name>.*) (?P<connection>connected|disconnected|unknown connection) "
                "(?P<primary>primary )?"
                "((?P<current_geometry>[0-9-+x]+)( \(0x(?P<current_mode>[0-9a-fA-F]+)\))? (?P<current_rotation>normal|left|inverted|right) ((?P<current_reflection>none|X axis|Y axis|X and Y axis) )?)?"
                "\("
                "(?P<supported_rotations>((normal|left|inverted|right) ?)*)"
                "(?P<supported_reflections>((x axis|y axis) ?)*)"
                "\)"
                "( (?P<physical_x>[0-9]+)mm x (?P<physical_y>[0-9]+)mm)?"
                "$")

        @property
        def mode(self):
            if self.mode_number is False:
                return False
            for m in self.assigned_modes:
                if m.id == self.mode_number:
                    return m
            raise ValueError("Output in an inconsistent state: active mode is not assigned")

        def _parse_headline(self, headline, primary_callback):
            headline_parsed = self.HEADLINE_EXPRESSION.match(headline)
            if headline_parsed is None:
                raise XRandRParseError("Unmatched headline: %r."%headline)
            headline_parsed = headline_parsed.groupdict()

            self.name = headline_parsed['name']
            # the values were already checked in the regexp
            self.connection_status = ConnectionStatus(headline_parsed['connection'])

            if headline_parsed['primary']:
                primary_callback()

            if headline_parsed['current_geometry']:
                self.active = True
                if headline_parsed['current_mode']:
                    self.mode_number = int(headline_parsed['current_mode'], 16)
                else:
                    # current_mode is only shown since xrandr 1.2.2; for everything before that, we have to guess because there was no '*current' either
                    warnings.warn("Old xrandr version (< 1.2.2), guessing current mode")
                    self.mode_number = None
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

            self.supported_rotations = list(map(Rotation, headline_parsed['supported_rotations'].split()))
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
                    changable = range(int(matched['min']), int(matched['max'])+1)
                else:
                    changable = None

            else:
                warnings.warn("Can not interpret detail %r"%label)
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

        @property
        def polygon(self):
            """Return the output area's outlining polygon."""

            # winding clock-wise, as we're in "pc coordinates" (right, down
            # instead of right, up), so clock-wise is the new positive
            # direction
            return ConvexPolygon([
                    self.geometry.position,
                    (self.geometry.position[0] + self.geometry.size[0], self.geometry.position[1]),
                    tuple(p+s for (p, s) in zip(self.geometry.position, self.geometry.size)),
                    (self.geometry.position[0], self.geometry.position[0] + self.geometry.size[1]),
                    ])
