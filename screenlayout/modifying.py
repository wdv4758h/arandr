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

def modifying(original_function, eval_from_self=False):
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

    It can also be used with classes, both for calling constructors...
    calling constructors...

    >>> class A(object):
    ...     def __init__(self, a, b, c="c"):
    ...         self.a = a
    >>> @modifying(A)
    ... def A_factory(super, c):
    ...     print "Creating a %r style A"%c
    ...     return super()
    >>> A_factory(1, 2)
    Creating a 'c' style A
    <__main__.A object at ...>

    ... and for decorating methods:

    >>> class A_Factory(object):
    ...     enforce_a = 42
    ...     @modifying(A)
    ...     def __call__(self, super):
    ...         return super(a=self.enforce_a)
    >>> factory = A_Factory()
    >>> a = factory(a=2, b=10)
    >>> a.a
    42

    In case the decision on what to decorate can only be made later, it can be
    deferred:

    >>> class Anything_Factory(object):
    ...     enforce_a = 42
    ...     @modifying(lambda self: self.baseclass, eval_from_self=True)
    ...     def __call__(self, super):
    ...         return super(a=self.enforce_a)
    >>> factory = Anything_Factory()
    >>> factory.baseclass = A
    >>> a = factory(a=2, b=10)
    >>> a.a
    42

    In a way, it is a generalization of functools.partial, as it can replicate
    its behavior.

    Caveat: The original function must not take * or ** arguments, or refuse to
    accept keyword arguments.  (It works only if `f(**inspect.getcallargs(f,
    ...))` is equivalent to `f(...)`."""

    def decorator(simple_function):

        args_for_simple_function = inspect.getargspec(simple_function).args

        simple_function_is_method = args_for_simple_function[0] == 'self' # if true, assume we're decorating an unbound method that will be called bound and strip an arg

        def wrapped(*args, **kwargs):
            if eval_from_self:
                _original_function = original_function(args[0])
            else:
                _original_function = original_function
            object_mode = isinstance(_original_function, type) # workaround because classes can't be introspected like functions

            if simple_function_is_method:
                self = args[0]
                args = args[1:]

            if object_mode:
                function_for_getcallargs = _original_function.__init__
                getcallargs_args = (None,) + args
            else:
                function_for_getcallargs = _original_function
                getcallargs_args = args

            argspec = inspect.getargspec(function_for_getcallargs)
            if argspec.varargs or argspec.keywords:
                raise ValueError("Original function must not have *args or **kwargs.")
            callargs = inspect.getcallargs(function_for_getcallargs, *getcallargs_args, **kwargs)

            if object_mode:
                del callargs['self']
            super = lambda **overrides: _original_function(**dict(callargs, **overrides))

            kwargs_for_simple = dict((k, callargs[k]) for k in args_for_simple_function if k in callargs)

            if simple_function_is_method:
                return simple_function(self, super, **kwargs_for_simple)
            else:
                return simple_function(super, **kwargs_for_simple)
        return wrapped
    return decorator

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
