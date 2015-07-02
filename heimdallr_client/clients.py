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

    def connect(self):
        parsed = urlparse(self.url)
        self.connection._io = SocketIO(parsed.hostname, parsed.port)
        self.connection._io._namespace = self.connection

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
        attr_name = 'on_' + message_name.replace(' ', '_')
        if hasattr(self.connection, attr_name):
            delattr(self.connection, attr_name)


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
        if not isinstance(filter_, dict):
            raise TypeError('filter_ must be a dict not a %s' % type(filter_).__name__)

        if not isinstance(filter_.get('event'), list) and not isinstance(filter_.get('sensor'), list):
            raise TypeError('Either `event` or `sensor` must be a list')

        filter_['provider'] = uuid
        self.connection.emit('setFilter', filter_)

    def get_state(self, uuid, subtypes):
        if not isinstance(subtypes, list):
            raise TypeError('`subtypes` must be a list')

        self.connection.emit('getState', {'provider': uuid, 'subtypes': subtypes})

    def join_stream(self, uuid):
        self.connection.emit('joinStream', {'provider': uuid})

    def leave_stream(self, uuid):
        self.connection.emit('leaveStream', {'provider': uuid})