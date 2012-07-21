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

class StackingContext(object):
    """Base class for contexts that delegate execution to an
    `underlying_context`"""
    def __init__(self, underlying_context=local):
        self.underlying_context = underlying_context

    def __repr__(self):
        return '<%s context at %x atop %r>'%(type(self).__name__, id(self), self.underlying_context)

class WithEnvironment(StackingContext):
    """Enforces preset environment variables upon executions"""
    def __init__(self, preset_environment, underlying_context=local):
        self.preset_environment = preset_environment
        super(WithEnvironment, self).__init__(underlying_context)

    @modifying(lambda self: self.underlying_context, eval_from_self=True)
    def __call__(self, super, env):
        if env is not None:
            env = dict(env, **self.preset_environment)
        else:
            env = self.preset_environment
        return super(env=env)

class SSHContext(StackingContext):
    ssh_executable = '/usr/bin/ssh'

    def __init__(self, host, ssh_args=(), underlying_context=local):
        self.host = host
        self.ssh_args = ssh_args
        super(SSHContext, self).__init__(underlying_context)

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

        if env:
            prefix_args = []
            for (k, v) in env.iteritems() if env is not None else ():
                # definition as given in dash man page:
                #     Variables set by the user must have a name consisting solely
                #     of alphabetics, numerics, and underscores - the first of
                #     which must not be numeric.
                if k[0] in string.digits or any(_k not in string.ascii_letters + string.digits + '_' for _k in k):
                    raise ValueError("The environment variable %r can not be set over SSH."%k)

                prefix_args += "%s=%s "%(shell_quote(k), shell_quote(v))
            if shell == True:
                # sending it through *another* shell because when shell=True,
                # the user can expect the environment variables to already be
                # set when the expression is evaluated.
                args = "".join(prefix_args) + "exec sh -c " + shell_quote(args)
            else:
                args = "".join(prefix_args) + args

        return super(args=(self.ssh_executable,) + self.ssh_args + (self.host, '--', args), shell=False, env=None)

class SimpleLoggingContext(StackingContext):
    """Logs only command execution, no results"""
    def __init__(self, underlying_context=local, logmethod=logging.root.info):
        self.logmethod = logmethod
        super(SimpleLoggingContext, self).__init__(underlying_context)

    @modifying(lambda self: self.underlying_context, eval_from_self=True)
    def __call__(self, super, args, env):
        self.logmethod("Execution started: %r within %r"%(args, env))
        return super()

class ZipfileLoggingContext(StackingContext):
    """Logs all executed commands into a ZIP file state machine"""
    def __init__(self, zipfilename, underlying_context=local):
        self.zipfile = zipfile.ZipFile(zipfilename, 'w')
        super(ZipfileLoggingContext, self).__init__(underlying_context)

class ZipfileContext(object):
    """Looks up cached command results from a ZIP file state machine."""
    def __init__(self, zipfilename):
        self.zipfile = zipfile.ZipFile(zipfilename)
