import inspect
from functools import wraps, partial
from datetime import datetime


def timestamp():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def on_ready(fn):
    @wraps(fn)
    def decorate(self, *args, **kwargs):
        if self.ready:
            fn(self, *args, **kwargs)
        else:
            self.ready_callbacks.append(partial(fn, self, *args, **kwargs))
        return self

    return decorate


# From http://stackoverflow.com/a/30764825/4059062
def for_own_methods(decorator):
    @wraps(decorator)
    def decorate(cls):
        def predicate(member):
            return inspect.ismethod(member) and member.__name__ in cls.__dict__

        for name, method in inspect.getmembers(cls, predicate):
            setattr(cls, name, decorator(method))
        return cls

    return decorate


def map_keys(dictionary, fn):
    if not isinstance(dictionary, dict):
        return dictionary

    new = {}

    for key, value in dictionary.iteritems():
        key = fn(key)
        if isinstance(value, dict):
            value = map_keys(value, fn)
        new[key] = value

    return new


def preserve_case(string):
    return string