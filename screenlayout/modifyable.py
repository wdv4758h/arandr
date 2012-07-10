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

"""Provides the modifyable decorator, which might go into the functools module."""

import inspect

def modifying(original_function):
    """Wraps a function in a way that it can be used as a drop-in replacement,
    signature-wise, for a function whose signature is overly complex. It also
    takes care of argument default values in the complex function, and passes
    them to the simple function as requested.

    In detail, when a simple function is decorated with @modifying(complex) and
    called, the arguments passed will be evaluated as they would be when passed
    to the complex function, and default values are filled in. Then, only those
    arguments that are mentioned in the simple function's signature are passed
    to the simple function.

    The simple function gets passed an additional first argument, super, which
    it can call to the same effect the complex function would have had when
    called with its original arguments. The simple function can add additional
    keyword arguments that override the original arguments.

    >>> def f(a, b, c, d="d", e="e"):
    ...     print c
    >>>
    >>> @modifying(f)
    ... def new_f(super, c, e):
    ...     if e != 'e':
    ...         return super(c=2*c)
    ...     else:
    ...         return super(c=3*c)
    >>> new_f(1, 2, 3, 4, 5)
    6
    >>> new_f(1, 2, c=3)
    9

    In a way, it is a generalization of functools.partial, as it can replicate
    its behavior.
    
    Caveat: The original function must not take * or ** arguments, or refuse to
    accept keyword arguments.  (It works only if `f(**inspect.getcallargs(f,
    ...))` is equivalent to `f(...)`."""

    def decorator(simple_function):
        args_for_simple_function = inspect.getargspec(simple_function).args

        def wrapped(*args, **kwargs):
            callargs = inspect.getcallargs(original_function, *args, **kwargs)
            super = lambda **overrides: original_function(**dict(callargs, **overrides))

            return simple_function(super, **dict((k, callargs[k]) for k in args_for_simple_function if k in callargs))
        return wrapped
    return decorator

if __name__ == "__main__":
    import doctest
    doctest.testmod()
