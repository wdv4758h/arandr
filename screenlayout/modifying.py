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

HIDE = object() # sentinel value

def _getargspec(func):
    """Wrapper around getargspec that is enhanced

    * to respects callables that use the
      __getargspec__ property (to simulate complex argspec when they really
      only have *args, **kwargs),

    * to instanciable types (getting whose argspec
      usually means inspecting its __init__ and chopping off the first argument
      because it behaves like a bound method but isn't one), and

    * to recognize objects that implement __call__ and give the bound method's
      argspec

    When a __getargspec__ is found as a bound function (as it would happen with
    objects of types that implement __call__), it gets passed self."""

    if hasattr(func, '__getargspec__'):
        return func.__getargspec__(func.__self__) if hasattr(func, '__self__') else func.__getargspec__()
    else:
        if isinstance(func, type):
            argspec = _getargspec(func.__init__)
            # defaults are only modified if someone uses a default value for
            # self. if someone can make meaningful use of the varargs argument,
            # he might be interested in whether the varargs will contain a self
            # when called, but that seems to be too special to break the rules
            # here -- besides, i fail to imagine how that could happen and what
            # would be a proper result at all.
            return inspect.ArgSpec(argspec.args[1:], argspec.varargs, argspec.keywords, argspec.defaults[1:] if len(argspec.args) == len(argspec.defaults) else argspec.defaults)
        elif inspect.isfunction(func) or inspect.ismethod(func): # only those can be inspected
            # FIXME: we should detect bound methods here and do first argument stripping too
            return inspect.getargspec(func)
        else:
            return _getargspec(func.__call__)

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

    if isinstance(func, inspect.ArgSpec):
        argspec = func
        funcname = repr(argspec)
    else:
        argspec = _getargspec(func)
        funcname = "%s()"%func.__name__

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
            raise TypeError("%s takes %s %s (%d given)"%(
                funcname,
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

    for name, assigned in named.items():
        if name in expected:
            if expected[name] is not undefined:
                raise TypeError("%s got multiple values for keyword argument %r"%(
                    funcname,
                    name
                    ))
            else:
                expected[name] = assigned
        else:
            if takes_keywords:
                kwargs[name] = assigned
            else:
                raise TypeError("%s got an unexpected keyword argument %r"%(
                    funcname,
                    name
                    ))

    # fill in defaults

    for name, default in zip(argspec.args[-len(argspec.defaults):], argspec.defaults):
        if expected[name] is undefined:
            expected[name] = default

    # check for undefined arguments

    if any(value is undefined for value in expected.values()):
        raise TypeError("%s takes %s %s (%d given)"%(
            funcname,
            "at least" if argspec.defaults else "exactly",
            "1 argument" if (len(argspec.args) - len(argspec.defaults)) == 1 else "%d arguments"%(len(argspec.args) - len(argspec.defaults)),
            len(positional)
            ))

    return (expected, varargs, kwargs)

def _argspec_get_defaultdict(argspec):
    """Return the arguments of an argspec that do have default values in a dict
    with their default values"""

    if argspec.defaults:
        return dict(zip(argspec.args[-len(argspec.defaults):], argspec.defaults))
    else:
        return {}

def _join_argspecs(orig_func, updating_func):
    """Create an argspec that resembles that of orig_func, but whose default
    values are updated to resemble those of updating_func if defined.

    Arguments of updating_func without default values or those that are not in
    orig_func will be ignored.

    It is an error if the resulting argspec can not be represented, i.e. if an
    argument gets a default assigned that is not the last positional argument.
    """

    orig = _getargspec(orig_func)
    updating = _getargspec(updating_func)

    defaults = _argspec_get_defaultdict(orig)
    for key, value in _argspec_get_defaultdict(updating).items():
        if key not in orig.args:
            continue
        defaults[key] = value

    sorted_defaults = []

    from_now_we_need_defaults = False
    for arg in orig.args:
        if arg in defaults:
            sorted_defaults.append(defaults[arg])
            from_now_we_need_defaults = True
        else:
            if from_now_we_need_defaults:
                raise ValueError("This set of default values can not be expressed in an argspec because there is no default value for %s."%arg)

    return inspect.ArgSpec(orig.args, orig.varargs, orig.keywords, tuple(sorted_defaults))

def modifying(original_function, eval_from_self=False, hide=()):
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
    ...     print c, d
    >>>
    >>> @modifying(f)
    ... def new_f(super, c, e):
    ...     if e != 'e':
    ...         return super(c=2*c)
    ...     else:
    ...         return super(c=3*c)
    >>> new_f(1, 2, 3, 4, 5)
    6 4
    >>> new_f(1, 2, c=3)
    9 d

    It can also be used with classes, both for calling constructors...

    >>> class A(object):
    ...     def __init__(self, a, b, c="c"):
    ...         self.a = a
    ...         self.b = b
    >>> @modifying(A)
    ... def A_factory(super, c):
    ...     print "Creating a %r style A"%c
    ...     return super()
    >>> A_factory(1, 2)
    Creating a 'c' style A
    <....A object at ...>

    ... and for decorating methods:

    >>> class A_Factory(object):
    ...     def __init__(self, enforce_a):
    ...         self.enforce_a = enforce_a
    ...     @modifying(A)
    ...     def __call__(self, super):
    ...         return super(a=self.enforce_a)
    >>> factory = A_Factory(enforce_a=42)
    >>> a = factory(a=2, b=10)
    >>> a.a
    42

    In case the decision on what to decorate can only be made later, it can be
    deferred, eg for chaining factories:

    >>> class Anything_Factory(object):
    ...     enforce_b = 23
    ...     @modifying(lambda self: self.baseclass, eval_from_self=True)
    ...     def __call__(self, super):
    ...         return super(b=self.enforce_b)
    >>> second_factory = Anything_Factory()
    >>> second_factory.baseclass = factory
    >>> a = second_factory(a=2, b=10)
    >>> a.a
    42
    >>> a.b
    23

    The simple function can use positional arguments to override defaults:

    >>> @modifying(f)
    ... def different_f(super, d="new_d"):
    ...     super()
    >>> different_f(1, 2, 3)
    3 new_d

    Arguments to the modified function that should *not* be passed to super can
    be explicitly supressed by passing the modifying.HIDE value; those
    arguments can only be passed in from outside as keyword arguments:

    >>> @modifying(f, hide=["new_param"])
    ... def better_f(super, c, new_param):
    ...     super(c=new_param*c)
    >>> better_f(1, 2, 3, new_param=3)
    9 d

    In a way, it is a generalization of functools.partial, as it can replicate
    its behavior.

    Caveat: The original function must not take * or ** arguments, or refuse to
    accept keyword arguments.  (It works only if `f(**inspect.getcallargs(f,
    ...))` is equivalent to `f(...)`."""

    def decorator(simple_function):

        args_for_simple_function = inspect.getargspec(simple_function).args

        # FIXME: it would be more reliable if this used descriptors
        simple_function_is_method = args_for_simple_function[0] == 'self' # if true, assume we're decorating an unbound method that will be called bound and strip an arg

        def wrapped(*args, **kwargs):
            if eval_from_self:
                # this will typically only be the case if
                # simple_function_is_method, but i don't see a reason to check
                # for it -- maybe someone's trying to be clever, let's let him
                _original_function = original_function(args[0])
            else:
                _original_function = original_function

            if simple_function_is_method:
                self = args[0]
                args = args[1:]

#            if not isinstance(function_for_getcallargs, type(lambda:None)): # for instances of classes that can be called
#                function_for_getcallargs = function_for_getcallargs.__call__

            argspec = _getargspec(_original_function)
            if argspec.varargs or argspec.keywords:
                raise ValueError("Original function must not have *args or **kwargs.")

            argspec_for_evalargs = _join_argspecs(_original_function, simple_function)
            joint_expected, joint_args, joint_kwargs = evalargs(argspec_for_evalargs, *args, **(dict((k,v) for (k,v) in kwargs.items() if k not in hide)))

            def super(**overrides):
                all_kwargs = dict(joint_expected)
                if joint_kwargs is not None:
                    all_kwargs.update(joint_kwargs)
                # the above two (expected vs kwargs) could just as well be the
                # other way round too -- evalargs alreay makes sure there are
                # no duplicates

                # if we wanted to cater for functions that don't take arguments
                # in keyword form, we'd have to sort the overrides into
                # expected if they fit and into kwargs otherwise, and pass
                # expected as a part of *args. this is unlikely to be necessary
                # as such functions (like operator.lt) can't be introspected
                # anyway.
                all_kwargs.update(overrides)

                return _original_function(*(joint_args if joint_args is not None else ()), **all_kwargs)

            kwargs_for_simple = {}
            for a in args_for_simple_function:
                if a in joint_expected:
                    kwargs_for_simple[a] = joint_expected[a]
                elif joint_kwargs is not None and a in joint_kwargs:
                    kwargs_for_simple[a] = joint_kwargs[a]
                else:
                    # hope it has a default
                    pass

            # feed hidden arguments back again
            for hidden_argument in hide:
                if hidden_argument in kwargs:
                    kwargs_for_simple[hidden_argument] = kwargs[hidden_argument]

            if simple_function_is_method:
                return simple_function(self, super, **kwargs_for_simple)
            else:
                return simple_function(super, **kwargs_for_simple)

        if simple_function_is_method:
            if eval_from_self:
                wrapped.__getargspec__ = lambda self: _join_argspecs(original_function(self), simple_function)
            else:
                wrapped.__getargspec__ = lambda self, result=_join_argspecs(original_function, simple_function): result
        else:
            wrapped.__getargspec__ = lambda result=_join_argspecs(original_function, simple_function): result

        wrapped.__name__ = simple_function.__name__
        wrapped.__doc__ = simple_function.__doc__

        return wrapped
    return decorator

def test(module=None):
    import doctest
    doctest.testmod(module, optionflags=doctest.ELLIPSIS)

if __name__ == "__main__":
    test()
