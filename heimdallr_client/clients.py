from threading import _Event
from urlparse import urlparse
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
    def _should_stop_waiting(self, for_connect=False, for_callbacks=False, event=None):
        if for_connect:
            for namespace in self._namespace_by_path.values():
                is_namespace_connected = getattr(
                    namespace, '_connected', False)
                if not is_namespace_connected:
                    return False
            return True
        if for_callbacks and not self._has_ack_callback:
            return True
        event_set = False
        if isinstance(event, _Event):
            event_set = event.is_set()
        return super(SocketIO, self)._should_stop_waiting() or event_set


class Client(object):
    url = 'https://heimdallr.co'
    auth_source = 'heimdallr'
    namespace = '/'

    def __init__(self, token, **kwargs):
        self.ready = False
        self.ready_callbacks = []
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

    def connect(self):
        parsed = urlparse(self.url)
        self.connection._io = _SocketIO(parsed.hostname, parsed.port)
        self.connection._io._namespace = self.connection
        self.connection._io._namespace_by_path[self.namespace] = self.connection
        self.connection._io.connect(self.namespace)
        self.connection._io.wait(for_connect=True)

        return self

    def on(self, message_name, callback=None):
        if callback is None:
            # Decorator syntax
            def decorator(fn):
                self.connection.on(message_name, fn)
            return decorator

        # SocketIO-Client syntax
        self.connection.on(message_name, callback)
        return self

    def remove_listener(self, message_name):
        self.connection._callback_by_event.pop(message_name, None)


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