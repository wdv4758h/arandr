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
from . import context

def main():
    p = argparse.ArgumentParser(description=__doc__)

    p.add_argument('command', nargs=argparse.REMAINDER, help="Command to execute")
    p.add_argument('--shell', action='store_true', help='Execute several commands. If enabled, the command has to be shell-escaped, but more than one command can be specified.')
    p.add_argument('--zip-in', metavar='FILE', help="Use FILE to look up command results there instead of executing them locally")
    p.add_argument('--zip-out', metavar='FILE', help="Store all commands and their results in the FILE")
    p.add_argument('--ssh', metavar='HOST', help="Execute the commands remotely on HOST")
    p.add_argument('--verbose', action='store_true', help="Log all executed commands")

    args = p.parse_args()

    if args.ssh and args.zip_in:
        raise p.error("--ssh and --zip-in can not be used together.")

    if not args.command:
        raise p.error("No command specified")

    # always show all messages -- when verbose is off, nothing will log anyway
    logging.debug("Starting up")
    logging.root.setLevel(logging.DEBUG)

    if args.zip_in:
        c = context.ZipfileContext(args.zip_in)
    else:
        c = context.local

        if args.ssh:
            if args.verbose:
                c = context.SimpleLoggingContext(underlying_context=c)

            c = context.SSHContext(args.ssh, underlying_context=c)

    if args.zip_out:
        c = context.ZipfileLoggingContext(args.zip_out, underlying_context=c)

    if args.verbose:
        c = context.SimpleLoggingContext(underlying_context=c)

    if args.shell:
        for cmd in args.command:
            stdout, stderr, returncode = executions.ManagedExecution(cmd, shell=True, context=c).read_with_error()
            sys.stderr.write(stderr)
            sys.stdout.write(stdout)

            if returncode:
                sys.exit(returncode)
    else:
        stdout, stderr, returncode = executions.ManagedExecution(args.command, context=c).read_with_error()
        sys.stderr.write(stderr)
        sys.stdout.write(stdout)
        sys.exit(returncode)

if __name__ == "__main__":
    main()
