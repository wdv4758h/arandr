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

"""Execution contexts

This module provides context objects, which define where and how to run a
program. Contexts can be as trivial as adding environment variables, but can
just as well redirect execution to another machine by means of SSH (Secure
Shell).

Context objects are subprocess.Popen factories, either by being a
subprocess.Popen subclass, or by behaving sufficiently similar (ie, they can be
called with Popen's args)."""

import logging
import string
import functools
import sys
import zipfile
import subprocess

if sys.version >= (3, 3):
    from shlex import quote as shell_quote
else:
    from pipes import quote as shell_quote

from ..modifying import modifying

local = subprocess.Popen

class WithEnvironment(object):
    """Enforces preset environment variables upon executions"""
    def __init__(self, preset_environment, underlying_context=local):
        self.preset_environment = preset_environment
        self.underlying_context = underlying_context

    @modifying(lambda self: self.underlying_context, eval_from_self=True)
    def __call__(self, super, env):
        if env is not None:
            env = dict(env, **self.preset_environment)
        else:
            env = self.preset_environment
        return super(env=env)

class SSHContext(object):
    ssh_executable = '/usr/bin/ssh'

    def __init__(self, host, ssh_args=(), underlying_context=local):
        self.host = host
        self.ssh_args = ssh_args
        self.underlying_context = underlying_context

    @modifying(lambda self: self.underlying_context, eval_from_self=True)
    def __call__(self, super, args, env, shell, cwd, executable):
        if executable:
            # i'm afraid this can't be implemented easily; there might be a way
            # to wrap the command in *another* shell execution and make that
            # shell do the trick
            raise NotImplementedException("The executable option is not usable with an SSHContext.")
        if cwd:
            # should be rather easy to implement
            raise NotImplementedException("The cwd option is not usable with an SSHContext.")
        if not shell:
            # with ssh, there is no way of passing individual arguments;
            # rather, arguments are always passed to be shell execued
            args = " ".join(shell_quote(a) for a in args)

        for (k, v) in env.iteritems() if env is not None else ():
            # definition as given in dash man page:
            #     Variables set by the user must have a name consisting solely
            #     of alphabetics, numerics, and underscores - the first of
            #     which must not be numeric.
            if k[0] in string.digits or any(_k not in string.ascii_letters + string.digits + '_' for _k in k):
                raise ValueError("The environment variable %r can not be set over SSH."%k)

            args = "%s=%s %s"%(shell_quote(k), shell_quote(v), args)

        return super(args=(self.ssh_executable,) + self.ssh_args + (self.host, '--', args), shell=False)

class SimpleLoggingContext(object):
    """Logs only command execution, no results"""
    def __init__(self, underlying_context=local, logmethod=logging.root.info):
        self.underlying_context = underlying_context
        self.logmethod = logmethod

    def __call__(self, *args, **kwargs):
        self.logmethod("Execution started: %s %s"%(args, kwargs))
        self.underlying_context.__call__(*args, **kwargs)

class ZipfileLoggingContext(object):
    """Logs all executed commands into a ZIP file state machine"""
    def __init__(self, zipfilename, underlying_context=local):
        self.underlying_context = underlying_context
        self.zipfile = zipfile.ZipFile(zipfilename, 'w')

class ZipfileContext(object):
    """Looks up cached command results from a ZIP file state machine."""
    def __init__(self, zipfilename):
        self.zipfile = zipfile.ZipFile(zipfilename)
