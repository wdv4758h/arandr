import unittest
from .. import executions
from ..modifying import modifying

class EnvironmentTests(unittest.TestCase):
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

    @modifying(executions.ManagedExecution)
    def assertEqualWorkingJobs(self, super, context):
        results = []
        for c in context:
            results.append(super(context=c).read())
        first = results[0]
        for r in results:
            self.assertEqual(first, r)

if __name__ == "__main__":
    unittest.main()
