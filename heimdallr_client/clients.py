from socketIO_client import SocketIO


class Client(object):
    url = 'https://heimdallr.co'
    auth_source = 'heimdallr'

    def __init__(self, token, options=None):
        pass

    def connect(self):
        pass

    def on(self, packet_type, callback=None):
        pass


class Provider(Client):
    pass


class Consumer(Client):
    pass