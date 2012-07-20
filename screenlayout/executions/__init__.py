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

"""Executions module

The execution module provides the infrastructure for running external programs
that don't need data from stdin.

In extension of the subprocess module, this contains helper routines for
capturing stdout, watching stderr, nonblocking execution (FIXME: not yet) and
execution contexts (see executions.context)."""

import subprocess
from . import context

class ManagedExecution(object):
    def __init__(self, argv, context=context.local, shell=False):
        # i don't recommend using shell=True, but it's useful for testing the ssh wrapper
        self.process = context(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=shell)

    def read(self):
        # currently, this does hardly more than subprocess.check_output.
        stdout, stderr = self.process.communicate()

        if self.process.returncode != 0 or stderr:
            raise subproces.CalledProcessError(self.process.returncode, self, stderr)

        return stdout
