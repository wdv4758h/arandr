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

import sys
import logging
import unittest

from .. import test

def main(verbose=False):
    """Run the test suite of the executions package"""
    if verbose:
        logging.root.setLevel(logging.DEBUG)
    logging.info("Starting test suite")
    unittest.main(test)
    doctest.testmod(test)

if __name__ == "__main__":
    main(verbose='--verbose' in sys.argv)
