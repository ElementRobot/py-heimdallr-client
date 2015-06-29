from socketIO_client import SocketIO, SocketIONamespace, TRANSPORTS, parse_host, prepare_http_session


class _SocketIO(SocketIO):
    def __init__(
            self,
            host,
            port=None,
            Namespace=SocketIONamespace,
            wait_for_connection=True,
            transports=TRANSPORTS,
            resource='socket.io',
            hurry_interval_in_seconds=1,
            **kwargs):
        self._namespace_by_path = {}
        self._callback_by_ack_id = {}
        self._ack_id = 0
        self._is_secure, self._url = parse_host(host, port, resource)
        self._wait_for_connection = wait_for_connection
        self._client_transports = transports
        self._hurry_interval_in_seconds = hurry_interval_in_seconds
        self._http_session = prepare_http_session(kwargs)

        self._log_name = self._url
        self._wants_to_close = False
        self._opened = False

        if Namespace:
            self.define(Namespace)


class Client(object):
    url = 'https://heimdallr.co'
    auth_source = 'heimdallr'
    namespace = '/'

    def __init__(self, token, **kwargs):
        self.ready = False
        self.ready_callbacks = []
        self.token = token

    def connect(self):
        pass

    def on(self, packet_type, callback=None):
        pass


class Provider(Client):
    namespace = '/provider'


class Consumer(Client):
    namespace = '/consumer'