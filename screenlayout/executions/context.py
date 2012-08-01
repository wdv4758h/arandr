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
import os.path
import StringIO

if sys.version >= (3, 3):
    from shlex import quote as shell_quote
else:
    from pipes import quote as shell_quote

from .. import executions
from ..modifying import modifying

local = subprocess.Popen

class StackingContext(object):
    """Base class for contexts that delegate execution to an
    `underlying_context`"""
    def __init__(self, underlying_context=local):
        self.underlying_context = underlying_context

    def __repr__(self):
        return '<%s at %x atop %r>'%(type(self).__name__, id(self), self.underlying_context)

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

class WithXEnvironment(WithEnvironment):
    """Context that, upon execution of the first command, tries to autodetect a
    running X session and sets environment variables on the commands in a way
    that X11 progams can be executed.

    This is particularly useful atop a SSH connection; in that context, it is
    not SSH X forwarding that is used, but the programs will be both executed
    and displayed remotely."""

    def __init__(self, underlying_context=local):
        self.preset_environment = None
        StackingContext.__init__(self, underlying_context)

    @modifying(lambda self: super(WithXEnvironment, self).__call__, eval_from_self=True)
    def __call__(self, super):
        if self.preset_environment is None:
            self.determine_environment()

        return super()

    def determine_environment(self):
        displays = executions.ManagedExecution('grep --no-filename --text --null-data "^DISPLAY=" /proc/*/environ 2>/dev/null |sort --zero-terminated --unique', shell=True, context=self.underlying_context).read().split("\0")

        displays = (line.split('=', 1)[1] for line in displays if line)

        # the DISPLAY variable is sometimes set with and sometimes without
        # screennumber. according to X(7), the screen number defaults to 0, so
        # stripping it off should provide sufficient normalization.
        displays = set(d[:-2] if d.endswith('.0') else d for d in displays)

        if not displays:
            raise self.NoEnvironmentFound()
        if len(displays) != 1:
            raise self.AmbiguousEnvironmentFound()

        (display, ) = displays

        self.preset_environment = {'DISPLAY': display}

    class NoEnvironmentFound(Exception): "No usable X11 display was found."

    class AmbiguousEnvironmentFound(Exception): "More than one X11 display found. (And hinting not yet implemented.)"

class InDirectory(StackingContext):
    """Enforce a working directory setting"""
    def __init__(self, cwd, underlying_context=local):
        self.cwd = cwd
        super(InDirectory, self).__init__(underlying_context)

    @modifying(lambda self: self.underlying_context, eval_from_self=True)
    def __call__(self, super):
        return super(cwd=self.cwd)

class SSHContext(StackingContext):
    """Context that executes the process on another machine.

    Caveats:
        * The SSH context relies on the remote system to have a POSIX like
          shell.
        * Environment variables can only be set or explicitly unset; passing
          them will not automatically unset all others (unlike with
          subprocess.Popen)
    """
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
            raise NotImplementedError("The executable option is not usable with an SSHContext.")
        if cwd:
            # should be rather easy to implement
            raise NotImplementedError("The cwd option is not usable with an SSHContext.")
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
        self.logmethod("Execution started: %r within environment %r on %r"%(args, env, self.underlying_context))
        return super()

class ZipfileLoggingContext(StackingContext):
    """Logs all executed commands into a ZIP file state machine. For a
    description of the ZIP file format, see the ZipfileContext
    documentation.

    If store_states is False, commands will be assumed not to modify any state
    at all (resulting in a flat ZIP file). Otherwise, states will be
    continuously numbered, and the ZIP file can only be replayed in the same
    sequence. More fine-grained control is possible by passing a next_state
    argument to the process generation.

    The context has to be closed using its close() method.

    Caveat: This context must be used inside a ManagedExecution (or anything
    else that calls the process's _finished_execution(stdout_data, stderr_data,
    retcode) after the execution). The reason for this hack is that it's hard
    to emulate a 'tee' in the stdout/stderr pair: As long as stdout/stderr are
    just accessed with .read(), it could be emulated by creating a file-like
    object that catches the read function, but when the process's
    .communicate() is used, it reads the files by means of os.read(fileno), and
    emulating that would mean either overriding the complete .communicate()
    method or creating a os-level file like object.
    """

    def __init__(self, zipfilename, store_states=True, underlying_context=local):
        self.zipfile = zipfile.ZipFile(zipfilename, 'w')
        self.store_states = True
        self.current_state = ""
        self._incrementing_state_number = 0
        super(ZipfileLoggingContext, self).__init__(underlying_context)

    @modifying(lambda self: self.underlying_context, eval_from_self=True, hide=['next_state'])
    def __call__(self, super, args, shell, next_state=None):
        base_state = self.current_state
        if next_state is None:
            if self.store_states:
                self._incrementing_state_number += 1
                next_state = "%d/"%self._incrementing_state_number
            else:
                next_state = self.current_state
        self.current_state = next_state

        real_process = super()

        condensed_args = args if shell else " ".join(map(shell_quote, args))

        real_process._finished_execution = lambda stdout, stderr, retcode: self.store(condensed_args, stdout, stderr, retcode, base_state, next_state)

        return real_process

    def store(self, args, stdout, stderr, returncode, base_state, next_state):
        name = base_state + args

        self.zipfile.writestr(name + ".out", stdout)
        if stderr:
            self.zipfile.writestr(name + ".err", stderr)
        if returncode:
            self.zipfile.writestr(name + ".exit", str(returncode))
        if next_state != base_state:
            self.zipfile.writestr(name + ".state", next_state)

    def close(self):
        self.zipfile.close()

    def __del__(self):
        self.close()

class ZipfileContext(object):
    """Looks up cached command results from a ZIP file state machine.

    File format description
    =======================

    ZIP files for ZipfileContexts represent machine states and the results of
    stored commands that take no standard input.

    Command results (stdout, stderr, exit code, state machine transition) are
    stored as the contents of individual files in the ZIP file, discerned by
    their suffixes (.out, .err, .exit, .state). The command line is stored in
    the first part of the file name, shell-escaped. (As shell escaping is not a
    normalization, it might happen that even though a command was stored in the
    ZIP file, it can not be looked up if it is escaped differently).

    It is required for a .out file to exist, even if it is empty, as it
    indicates that a result of the command was stored. All other files can be
    absent and default to empty, 0, and no state change, respectively.

    If a state is set in a ZipfileContext, all successive commands are prefixed
    with that state, typically in a directory-structure-like fashion (i.e.
    states end with slashes).

    Caveats:

    * No environment variables can be set.
    * It is up to the user to make sure the commands of
      different machine states don't clash, e.g. if you use an executable in a
      relative path, `bin/ls`, and want to use the systems's `ls` in a machine
      state you call `bin/`, you might be in trouble.
    * When the ZIP file is opened with a utility that interprets file names
      hierarchically, commands containing slashes (eg because they contain file
      references) may appear spit at those slashes.
    """

    def __init__(self, zipfilename):
        self.state_prefix = ""
        self.zipfile = zipfile.ZipFile(zipfilename)

    # not using @modifying here on purpose: whenever someone uses a strange
    # argument, i want to know it and fail. close_fds can be ignored safely.
    def __call__(self, args, shell=False, stdout=None, stderr=None, close_fds=False):
        if stdout is not subprocess.PIPE or stderr is not subprocess.PIPE:
            # a straightforward implementation would just write the whole
            # contents there, but that might block while writing, and it would
            # block the very process that is supposed to read in order to get
            # the blocking away.
            raise NotImplementedError("Using any other stdout/stderr options than subprocess.PIPE is not supported yet.")

        if shell is False:
            args = " ".join(map(shell_quote, args))

        filename = self.state_prefix + args

        stdout = self.zipfile.open(filename + ".out")
        try:
            stderr = self.zipfile.open(filename + ".err")
        except KeyError:
            stderr = StringIO.StringIO("")
        try:
            returncode = int(self.zipfile.open(filename + ".exit").read())
        except KeyError:
            returncode = 0
        try:
            self.state_prefix = self.zipfile.open(filename + ".state").read()
        except KeyError:
            # as specified, no change happened
            pass

        return self.VirtualProcess(stdout, stderr, returncode)

    class VirtualProcess(object):
        def __init__(self, stdout, stderr, returncode):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

        def wait(self):
            return self.returncode

        def communicate(self):
            return self.stdout.read(), self.stderr.read()
