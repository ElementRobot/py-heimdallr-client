from threading import _Event
from urlparse import urlparse
from functools import partial
from pydash.strings import snake_case, camel_case
from socketIO_client import SocketIO, SocketIONamespace, EngineIONamespace

from exceptions import HeimdallrClientException
from utils import timestamp, for_own_methods, on_ready, map_keys, preserve_case


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
        self.__snake_case = False
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
            self.__emit('authorize', {'token': self.token, 'authSource': self.auth_source})

    @property
    def snake_case(self, value):
        self.__snake_case = bool(value)
        self.callbacks = map_keys(self.callbacks, self.__to_server)

    def __to_server(self, string):
        return camel_case(string) if self.__snake_case else string

    def __to_client(self, string):
        return snake_case(string) if self.__snake_case else string

    def connect(self):
        parsed = urlparse(self.url)
        self.connection._io = _SocketIO(parsed.hostname, parsed.port)
        self.connection._io._namespace = self.connection
        self.connection._io._namespace_by_path[self.namespace] = self.connection
        self.connection._io.connect(self.namespace)
        self.connection._io.wait(for_connect=True)

        return self

    def wait(self, **kwargs):
        self.connection._io.wait(**kwargs)

        return self

    def __emit(self, message_name, data):
        message_name = self.__to_server(message_name)
        data = map_keys(data, self.__to_server)

        self.connection.emit(message_name, data)

    def __wrap_callback(self, message_name, *args):
        message_name = self.__to_client(message_name)
        args = map(lambda item: map_keys(item, self.__to_client), args)

        callbacks = self.callbacks.get(message_name, [])
        for callback in callbacks:
            callback(*args)

    def __on(self, message_name, callback):
        self.callbacks.setdefault(message_name, [])
        self.callbacks[message_name].append(callback)

    def on(self, message_name, callback=None):
        message_name = self.__to_server(message_name)

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
        self.__emit('event', {'subtype': subtype, 'data': data, 't': timestamp()})

    def send_sensor(self, subtype, data=None):
        self.__emit('sensor', {'subtype': subtype, 'data': data, 't': timestamp()})

    def send_stream(self, data):
        self.__emit('stream', data)

    def completed(self, uuid):
        self.__emit('event', {'subtype': 'completed', 'data': uuid, 't': timestamp()})


@for_own_methods(on_ready)
class Consumer(Client):
    namespace = '/consumer'

    def send_control(self, uuid, subtype, data=None, persistent=False):
        self.__emit('control', {'provider': uuid, 'subtype': subtype, 'data': data, 'persistent': persistent})

    def subscribe(self, uuid):
        self.__emit('subscribe', {'provider': uuid})

    def unsubscribe(self, uuid):
        self.__emit('unsubscribe', {'provider': uuid})

    def set_filter(self, uuid, filter_):
        filter_['provider'] = uuid
        self.__emit('setFilter', filter_)

    def get_state(self, uuid, subtypes):
        self.__emit('getState', {'provider': uuid, 'subtypes': subtypes})

    def join_stream(self, uuid):
        self.__emit('joinStream', {'provider': uuid})

    def leave_stream(self, uuid):
        self.__emit('leaveStream', {'provider': uuid})