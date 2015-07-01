import inspect
from functools import wraps, partial
from datetime import datetime


def timestamp():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


@wraps
def on_ready(fn):
    def decorate(self, *args, **kwargs):
        if self.ready:
            fn(*args, **kwargs)
        else:
            self.ready_callbacks.append(partial(fn, *args, **kwargs))

    return decorate


# From http://stackoverflow.com/a/30764825/4059062
@wraps
def for_all_methods(decorator):
    def decorate(cls):
        for name, method in inspect.getmembers(cls, inspect.ismethod):
            setattr(cls, name, decorator(method))
        return cls

    return decorate