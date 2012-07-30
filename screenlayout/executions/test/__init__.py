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

import subprocess
import unittest

from ... import executions
from ...modifying import modifying

class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        # the ssh tests need an automatic setup to localhost anyway. if the
        # setup requires a password, but uses ControlMaster, this will set the
        # control master up.
        subprocess.check_call(['ssh', 'localhost', 'true'])

    def test_chainedWithEnvironment(self):
        env1 = executions.context.WithEnvironment({'x': '42'})
        env2 = executions.context.WithEnvironment({'y': '23'}, underlying_context=env1)

        job = executions.ManagedExecution(['env'], context=env2)
        self.assertEqual(job.read(), "y=23\nx=42\n")

    def test_ssh_escapes(self):
        # when running this, make sure ssh to localhost works
        to_localhost = executions.context.SSHContext("localhost")

        both_contexts = [to_localhost, executions.context.local]

        self.assertEqualWorkingJobs(['uname', '-a'], context=both_contexts)

        self.assertEqualWorkingJobs(['echo', '"spam"', 'egg\\spam'], context=both_contexts)
        self.assertEqualWorkingJobs(['echo', ''.join(chr(x) for x in range(32, 256))], context=both_contexts)
        self.assertEqualWorkingJobs('''echo "hello world!\\nthis is" 'fun', really''', shell=True, context=both_contexts)

        complex_shell_expression = '''for x in a b `echo c`; do sh -c "(echo \\\\$x) && echo 1"; done; echo $x'''
        self.assertEqualWorkingJobs(complex_shell_expression, shell=True, context=both_contexts)
        self.assertEqualWorkingJobs(['sh', '-c', complex_shell_expression], context=both_contexts)

    def test_ssh_environment(self):
        base_context = executions.context.SimpleLoggingContext()

        just_set_env = executions.context.WithEnvironment({"x": "23"}, underlying_context=base_context)
        locally_set_env = executions.context.SSHContext("localhost", underlying_context=just_set_env)

        plain_localhost = executions.context.SSHContext("localhost", underlying_context=base_context)
        remotely_set_env = executions.context.WithEnvironment({"x": "23"}, underlying_context=plain_localhost)

        # variable will not be forwarded over the ssh connection
        self.assertEqualWorkingJobs('echo x = $x', context=[plain_localhost, locally_set_env], shell=True)
        self.assertEqualWorkingJobs('echo x = $x', context=[just_set_env, remotely_set_env], shell=True)

    def test_zipfiles(self):
        zip_context = executions.context.ZipfileContext("./test.zip")

        both_contexts = [zip_context, executions.context.local]

        self.assertEqualWorkingJobs(['echo', '42'], context=both_contexts)

    @modifying(executions.ManagedExecution)
    def assertEqualWorkingJobs(self, super, context):
        results = []
        for c in context:
            results.append(super(context=c).read())
        first = results[0]
        for c, r in zip(context, results):
            self.assertEqual(first, r, "Disparity between contexts %s and %s: %r != %r"%(context[0], c, first, r))
