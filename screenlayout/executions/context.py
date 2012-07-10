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

import string
import functools
import sys
if sys.version >= (3, 3):
    from shlex import quote
else:
    from pipes import quote

local = subprocess.Popen

class WithEnvironment(object):
    def __init__(self, preset_environment, underlying_context=local):
        self.preset_environment = preset_environment
        self.underlying_context = underlying_context

    def __call__(self, *args, **kwargs):
        kwargs['env'] = dict(kwargs.get('env', {}), **self.preset_environment)
        return self.underlying_context(*args, **kwargs)

class SSHContext(object):
    ssh_executable = '/usr/bin/ssh'

    def __init__(self, host, ssh_args=(), underlying_context=local):
        self.host = host
        self.ssh_args = ssh_args

    # FIXME: i'd raver have the argument list automatically extracted from subprocess.Popen
    def __call__(self, args, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None, universal_newlines=False, startupinfo=None, creationflags=0):
        if executable:
            raise NotImplementedException("The executable option is not usable with an SSHContext.")
        if not shell:
            # with ssh, there is no way of passing individual arguments;
            # rather, arguments are always passed to be shell execued
            args = " ".join(quote(a) for a in args)

        for (k, v) in env.iteritems():
            # definition as given in dash man page:
            #     Variables set by the user must have a name consisting solely
            #     of alphabetics, numerics, and underscores - the first of
            #     which must not be numeric.
            if k[0] in string.digits orany(_k not in string.ascii_letters + string.digits + '_' for _k in k):
                raise ValueError("The environment variable %r can not be set over SSH."%k)

            args = "%s=%s %s"%(quote(k), quote(v), args)

        self.underlying_context((self.ssh_executable,) + self.ssh_args + (self.host, '--', args), bufsize=bufsize, stdin=stdin, stdout=stdout, stderr=stderr, preexec_fn=preexec_fn, close_fds=close_fds, universal_newlines=universal_newlines, startupinfo=startupinfo, creationflags=creationflags)

