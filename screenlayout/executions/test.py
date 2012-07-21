import subprocess
import unittest

from .. import executions
from ..modifying import modifying

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

        self.assertEqualWorkingJobs(['uname', '-a'], context=[to_localhost, executions.context.local])

        self.assertEqualWorkingJobs(['echo', '"spam"', 'egg\\spam'], context=[to_localhost, executions.context.local])
        self.assertEqualWorkingJobs(['echo', ''.join(chr(x) for x in range(32, 256))], context=[to_localhost, executions.context.local])
        self.assertEqualWorkingJobs('''echo "hello world!\\nthis is" 'fun', really''', context=[to_localhost, executions.context.local], shell=True)

    def test_ssh_environment(self):
        base_context = executions.context.SimpleLoggingContext()

        just_set_env = executions.context.WithEnvironment({"x": "23"}, underlying_context=base_context)
        locally_set_env = executions.context.SSHContext("localhost", underlying_context=just_set_env)

        plain_localhost = executions.context.SSHContext("localhost", underlying_context=base_context)
        remotely_set_env = executions.context.WithEnvironment({"x": "23"}, underlying_context=plain_localhost)

        # variable will not be forwarded over the ssh connection
        self.assertEqualWorkingJobs('echo x = $x', context=[plain_localhost, locally_set_env], shell=True)
        self.assertEqualWorkingJobs('echo x = $x', context=[just_set_env, remotely_set_env], shell=True)

    @modifying(executions.ManagedExecution)
    def assertEqualWorkingJobs(self, super, context):
        results = []
        for c in context:
            results.append(super(context=c).read())
        first = results[0]
        for c, r in zip(context, results):
            self.assertEqual(first, r, "Disparity between contexts %s and %s: %r != %r"%(context[0], c, first, r))

if __name__ == "__main__":
    import logging
#    logging.root.setLevel(logging.DEBUG)
    logging.info("Starting test suite")
    unittest.main()
