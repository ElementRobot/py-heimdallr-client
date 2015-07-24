import inspect
import requests
import json
from functools import partial
from datetime import datetime
from wrapt import decorator

from settings import AUTH_SOURCE, URL

__all__ = ['timestamp', 'on_ready', 'for_own_methods']


def timestamp():
    """ Generates an ISO 8601 timestamp for the current UTC time.

    Returns:
        str: ISO 8601 timestamp
    """

    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


@decorator
def on_ready(method, self, args, kwargs):
    """ on_ready(method)

    Decorator that ensures methods are only called once the client
    is ready. If the client is ready when the method is first
    called, the method will be evaluated immediately. If the
    client is not ready, the method will be postponed until the
    client is ready. Once the client is ready, the postponed
    methods will be called in the same order that they were
    originally called in.

    Args:
        method (function): Class method to decorate

    Returns:
        function: The decorated function
    """

    if self.ready:
        method(*args, **kwargs)
    else:
        self.ready_callbacks.append(partial(method, *args, **kwargs))
    return self


# From http://stackoverflow.com/a/30764825/4059062
def for_own_methods(method_decorator):
    """ Decorates all the methods in a class.

    This function takes a function decorator and returns a class
    decorator that applies the function decorator to all of the
    methods in a class. The function decorator will only be applied
    to methods that are explicitly defined on the class. Any inherited
    methods that aren't overridden or altered will not be decorated.

    Args:
        method_decorator (function): Method decorator to be applied to
            each method of the class

    Returns:
        function: A class decorator
    """

    def decorate(cls):
        def predicate(member):
            return inspect.ismethod(member) and member.__name__ in cls.__dict__

        for name, method in inspect.getmembers(cls, predicate):
            setattr(cls, name, method_decorator(method))
        return cls

    return decorate


def post_schemas(token, uuids, packet_schemas):
    results = {}
    for uuid in uuids:
        for packet_type, schemas in packet_schemas.iteritems():
            results[uuid] = requests.post(
                '%sprovider/%s/subtype-schemas' % (URL, uuid),
                data=json.dumps(
                    {'packetType': packet_type, 'subtypeSchemas': schemas}
                ),
                headers={
                    'content-type': 'application/json',
                    'authorization': 'Token %s' % token
                }
            )
    return results