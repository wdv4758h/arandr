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

"""Provides the `modifying` decorator, which might go into the functools module."""

import inspect

from collections import OrderedDict

def _getargspec(func):
    """Wrapper around getargspec that also respects callables that use the
    __getargspec__ property to simulate complex argspec when they really only
    have *args, **kwargs.

    When a __getargspec__ is found as a bound function (as it would happen with
    objects of types that implement __call__), it gets passed self.
    """

    if hasattr(func, '__getargspec__'):
        return func.__getargspec__(func.im_self) if hasattr(func, 'im_self') else func.__getargspec__()
    else:
        return inspect.getargspec(func)

def evalargs(func, *positional, **named):
    """Determine what the positional and named arguments look like when applied
    to func.

    The function returns a 3-tuple (expected, args, kwargs) of expected keyword
    arguments (with their default values filled in), args and kwargs as they
    could be passed with * and **.

    Unless func is picky about arguments being passed as keywords (eg
    operator.lt), it will always hold that `f(...)` is equivalent to that::

        (expected, args, kwargs) = evalargs(f, ...)
        kwargs.update(expected)
        return evalargs(*args, **kwargs)

    As the expected arguments are stored in a sorted dictionary, the last line
    can also be put like this::

        return evalargs(*(expected.values() + args), **kwargs)

    When the positional and named args are not sufficient or adequate to be
    passed to func, the same exception is raised as if it was actually tried
    (although there might be inaccuracies).

    This is similar to inspect.getcallargs, but handles some things
    differently: It focuses on the outside view of the function (how arguments
    can be passed back in) instate of the inside view (what *args and **kwargs
    would actually be assigned to). In addition to that, it checks func for a
    __getargspec__() property that allows wrapped methods to mimick their
    original functions. (If func is a bound method, __getargspec__ will be
    passed its self).

    >>> def f(a, b=5, *args):
    ...     pass
    >>> evalargs(f, 10, 15, 20)
    (OrderedDict([('a', 10), ('b', 15)]), (20,), None)
    >>> evalargs(f, x=42)
    Traceback (most recent call last):
      ...
    TypeError: f() got an unexpected keyword argument 'x'
    >>> evalargs(f)
    Traceback (most recent call last):
      ...
    TypeError: f() takes at least 1 argument (0 given)
    >>> f(1, a=5)
    Traceback (most recent call last):
      ...
    TypeError: f() got multiple values for keyword argument 'a'

    Caveat: As an anticipation of PEP 3113, tuple unpacking is not supported.
    The author acknowledges that he now finally sees the reasons behind that
    PEP."""

    argspec = _getargspec(func)

    takes_varargs = argspec.varargs is not None
    takes_keywords = argspec.keywords is not None

    undefined = object() # sentinel for identifying unfilled arguments

    expected = OrderedDict((name, undefined) for name in argspec.args)

    for name, assigned in zip(argspec.args, positional):
        expected[name] = assigned

    # fill in positional arguments

    if len(positional) > len(argspec.args):
        if takes_varargs:
            varargs = positional[len(argspec.args):]
        else:
            # this is one of the inaccuracies mentioned in the docstring: see
            # inspect.getcallargs for situations in which it says "no arguments
            # (%d given)" instead.
            raise TypeError("%s() takes %s %s (%d given)"%(
                func.__name__,
                "at most" if argspec.defaults else "exactly",
                "1 argument" if len(argspec.args) == 1 else "%d arguments"%len(argspec.args),
                len(positional)
                ))
    else:
        if takes_varargs:
            varargs = ()
        else:
            varargs = None

    # fill in keyword arguments

    if takes_keywords:
        kwargs = {}
    else:
        kwargs = None

    for name, assigned in named.iteritems():
        if name in expected:
            if expected[name] is not undefined:
                raise TypeError("%s() got multiple values for keyword argument %r"%(
                    func.__name__,
                    name
                    ))
            else:
                expected[name] = assigned
        else:
            if takes_keywords:
                kwargs[name] = assigned
            else:
                raise TypeError("%s() got an unexpected keyword argument %r"%(
                    func.__name__,
                    name
                    ))

    # fill in defaults

    for name, default in zip(argspec.args[-len(argspec.defaults):], argspec.defaults):
        if expected[name] is undefined:
            expected[name] = default

    # check for undefined arguments

    if any(value is undefined for value in expected.values()):
        raise TypeError("%s() takes %s %s (%d given)"%(
            func.__name__,
            "at least" if argspec.defaults else "exactly",
            "1 argument" if (len(argspec.args) - len(argspec.defaults)) == 1 else "%d arguments"%(len(argspec.args) - len(argspec.defaults)),
            len(positional)
            ))

    return (expected, varargs, kwargs)

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
