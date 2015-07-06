from threading import _Event
from urlparse import urlparse
from functools import partial
from socketIO_client import SocketIO, SocketIONamespace, EngineIONamespace

from exceptions import HeimdallrClientException
from utils import timestamp, for_own_methods, on_ready


__all__ = ['Client', 'Provider', 'Consumer']


def _init(self, io):
    self._io = io
    self._callback_by_event = {}
    self._log_name = Client.url
    self.initialize()


EngineIONamespace.__init__ = _init


class _SocketIO(SocketIO):
    def _should_stop_waiting(self, **kwargs):
        event = kwargs.pop('event', None)
        event_set = False
        if isinstance(event, _Event):
            event_set = event.is_set()
        return super(_SocketIO, self)._should_stop_waiting(**kwargs) or event_set


class Client(object):
    url = 'https://heimdallr.co'
    auth_source = 'heimdallr'
    namespace = '/'

    def __init__(self, token, **kwargs):
        self.ready = False
        self.ready_callbacks = []
        self.callbacks = {}
        self.token = token
        self.connection = SocketIONamespace(None, self.namespace)

        @self.on('err')
        def fn(err):
            if 'message' in err:
                raise HeimdallrClientException(err['message'])
            else:
                raise HeimdallrClientException(err)

        @self.on('auth-success')
        def fn(*args):
            self.ready = True
            while self.ready_callbacks:
                self.ready_callbacks.pop(0)()

        @self.on('connect')
        def fn(*args):
            self.connection.emit('authorize', {'token': self.token, 'authSource': self.auth_source})

    def wait(self, **kwargs):
        self.connection._io.wait(**kwargs)

        return self

    def connect(self):
        parsed = urlparse(self.url)
        self.connection._io = _SocketIO(parsed.hostname, parsed.port)
        self.connection._io._namespace = self.connection
        self.connection._io._namespace_by_path[self.namespace] = self.connection
        self.connection._io.connect(self.namespace)
        self.connection._io.wait(for_connect=True)

        return self

    def __wrap_callback(self, message_name, *args, **kwargs):
        callbacks = self.callbacks.get(message_name, [])
        for callback in callbacks:
            callback(*args, **kwargs)

    def __on(self, message_name, callback):
        self.callbacks.setdefault(message_name, [])
        self.callbacks[message_name].append(callback)

    def on(self, message_name, callback=None):
        # Decorator syntax
        if callback is None:
            def decorator(fn):
                self.__on(message_name, fn)
                self.connection.on(message_name, partial(self.__wrap_callback, message_name))
            return decorator

        # SocketIO-Client syntax
        self.__on(message_name, callback)
        self.connection.on(message_name, partial(self.__wrap_callback, message_name))

        return self

    def remove_listener(self, message_name, callback=None):
        if callback:
            while callback in self.callbacks.get(message_name, []):
                self.callbacks[message_name].remove(callback)
        else:
            self.callbacks.pop(message_name, None)

        return self


@for_own_methods(on_ready)
class Provider(Client):
    namespace = '/provider'

    def send_event(self, subtype, data=None):
        self.connection.emit('event', {'subtype': subtype, 'data': data, 't': timestamp()})

    def send_sensor(self, subtype, data=None):
        self.connection.emit('sensor', {'subtype': subtype, 'data': data, 't': timestamp()})

    def send_stream(self, data):
        self.connection.emit('stream', data)

    def completed(self, uuid):
        self.connection.emit('event', {'subtype': 'completed', 'data': uuid, 't': timestamp()})


@for_own_methods(on_ready)
class Consumer(Client):
    namespace = '/consumer'

    def send_control(self, uuid, subtype, data=None, persistent=False):
        self.connection.emit('control', {'provider': uuid, 'subtype': subtype, 'data': data, 'persistent': persistent})

    def subscribe(self, uuid):
        self.connection.emit('subscribe', {'provider': uuid})

    def unsubscribe(self, uuid):
        self.connection.emit('unsubscribe', {'provider': uuid})

    def set_filter(self, uuid, filter_):
        filter_['provider'] = uuid
        self.connection.emit('setFilter', filter_)

    def get_state(self, uuid, subtypes):
        self.connection.emit('getState', {'provider': uuid, 'subtypes': subtypes})

    def join_stream(self, uuid):
        self.connection.emit('joinStream', {'provider': uuid})

    def leave_stream(self, uuid):
        self.connection.emit('leaveStream', {'provider': uuid})