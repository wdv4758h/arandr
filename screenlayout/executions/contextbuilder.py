# ARandR -- Another XRandR GUI
# Copyright (C) 2008 -- 2014 chrysn <chrysn@fsfe.org>
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

"""Context builder for executions

This module provides tools for applications to use execution contexts without
assembling them themselves. This encompasses the
build_default_context function (whose result can be used as a drop-in
replacement for subprocess.Popen, but allows a user to override the subprocess
execution using environment variables) and the populate_parser /
build_from_arguments pair that is both used internally in build_default_context
and can be used to add context creating arguments to an argparse.ArgumentParser
instance."""

import os
import shlex
import argparse

from . import context

def populate_parser(p):
    """Given an argparse.ArgumentParser or subparser, add arguments for
    building an execution context.

    The particular arguments are expected to change until further notice."""

    p.add_argument('--zip-in', metavar='FILE', help="Use FILE to look up command results there instead of executing them locally")
    p.add_argument('--zip-out', metavar='FILE', help="Store all commands and their results in the FILE")
    p.add_argument('--zip-out-stateless', action='store_true', help="When creating a zip file, assume no command executed has any side effects")
    p.add_argument('--ssh', metavar='HOST', help="Execute the commands remotely on HOST")
    p.add_argument('--auto-x', action='store_true', help="Automatically find a running X session and redirect graphical output there")
    p.add_argument('--verbose', action='store_true', help="Log all executed commands")

def build_from_arguments(args):
    """Given the result of a populate_parser() treated argparse.ArgumentParser,
    create an execution context."""

    if args.ssh and args.zip_in:
        raise p.error("--ssh and --zip-in can not be used together.")

    if args.zip_out_stateless and not args.zip_out:
        raise p.error("--zip-out-stateless requires --zip-out.")

    if args.zip_in:
        c = context.ZipfileContext(args.zip_in)
    else:
        c = context.local

        if args.ssh:
            if args.verbose:
                c = context.SimpleLoggingContext(underlying_context=c)

            c = context.SSHContext(args.ssh, underlying_context=c)

    if args.auto_x:
            if args.verbose:
                c = context.SimpleLoggingContext(underlying_context=c)

            c = context.WithXEnvironment(underlying_context=c)

    if args.zip_out:
        c = context.ZipfileLoggingContext(args.zip_out, underlying_context=c, store_states=not args.zip_out_stateless)

    if args.verbose:
        c = context.SimpleLoggingContext(underlying_context=c)

    return c

def build_default_context():
    """Create an execution context as described in executions.context

    Usually, this just returns subprocess.Popen (the trivial execution
    context). If the environment variable EXECUTION_CONTEXT is present, it is
    evaluated like the arguments to `python3 -m screenlayout.executions.run`
    (see its help function). For example, with EXECUTION_CONTEXT="--ssh
    my_remote_host", all commands spawned from the resulting context will be
    executed on my_remote_host via ssh.
    """

    if "EXECUTION_CONTEXT" in os.environ:
        p = argparse.ArgumentParser(prog="EXECUTION_CONTEXT=", description="Default subprocess creator arguments")
        populate_parser(p)
        args = p.parse_args(shlex.split(os.environ['EXECUTION_CONTEXT']))
        return build_from_arguments(args)

    return context.local
