# ARandR -- Another XRandR GUI
# Copyright (C) 2008 -- 2012 chrysn <chrysn@fsfe.org>
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

"""Command-line interface to execution contexts.

The main purpose of this software is to allow creation of execution persistence
ZIP files."""

import sys
import logging
import argparse

from .. import executions
from . import contextbuilder

def main():
    p = argparse.ArgumentParser(description=__doc__)

    p.add_argument('command', nargs=argparse.REMAINDER, help="Command to execute")
    p.add_argument('--shell', action='store_true', help='Execute several commands. If enabled, the command has to be shell-escaped, but more than one command can be specified.')
    p.add_argument('--ignore-errors', action='store_true', help='Ignore errors from subprocesses')
    contextbuilder.populate_parser(p)

    args = p.parse_args()

    if not args.command:
        raise p.error("No command specified")

    # always show all messages -- when verbose is off, nothing will log anyway
    logging.debug("Starting up")
    logging.root.setLevel(logging.DEBUG)

    c = contextbuilder.build_from_arguments(args)

    if args.shell:
        for cmd in args.command:
            stdout, stderr, returncode = executions.ManagedExecution(cmd, shell=True, context=c).read_with_error()
            sys.stderr.buffer.write(stderr)
            sys.stdout.buffer.write(stdout)

            if returncode and not args.ignore_errors:
                sys.exit(returncode)
    else:
        stdout, stderr, returncode = executions.ManagedExecution(args.command, context=c).read_with_error()
        sys.stderr.buffer.write(stderr)
        sys.stdout.buffer.write(stdout)
        if not args.ignore_errors:
            sys.exit(returncode)

if __name__ == "__main__":
    main()
