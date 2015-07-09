import inspect
from functools import wraps, partial
from datetime import datetime


__all__ = ['timestamp', 'on_ready', 'for_own_methods']


def timestamp():
    """ Generates an ISO 8601 timestamp for the current UTC time.

    :return: str ISO 8601 timestamp
    """

    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def on_ready(method):
    """ Decorator that ensures methods are only called once the client is ready.

    This decorator will prevent a method from being called before
    the client is ready. If the client is ready when the decorator
    is called, the method will be evaluated immediately. If the
    client is not ready, the method will be postponed until the
    client is ready. Once the client is ready, the postponed
    methods will be called in the same order that they were
    originally called in.

    :type method: __builtin__.instancemethod Method to decorate
    :return: __builtin__.function Decorated function
    """

    @wraps(method)
    def decorate(self, *args, **kwargs):
        if self.ready:
            method(self, *args, **kwargs)
        else:
            self.ready_callbacks.append(partial(method, self, *args, **kwargs))
        return self

    return decorate


# From http://stackoverflow.com/a/30764825/4059062
def for_own_methods(decorator):
    """ Decorates all the methods in a class.

    This function takes a function decorator and returns a class
    decorator that applies the function decorator to all of the
    methods in a class. The function decorator will only be applied
    to methods that are explicitly defined on the class. Any inherited
    methods that aren't overridden or altered will not be decorated.

    :type decorator: __builtin__.function Function decorator to be applied to
        each method of the class
    :return: __builtin__.function Class decorator
    """

    @wraps(decorator)
    def decorate(cls):
        def predicate(member):
            return inspect.ismethod(member) and member.__name__ in cls.__dict__

        for name, method in inspect.getmembers(cls, predicate):
            setattr(cls, name, decorator(method))
        return cls

    return decorate