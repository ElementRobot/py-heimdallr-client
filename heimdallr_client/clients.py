from threading import _Event
from urlparse import urlparse
from functools import partial
from socketIO_client import SocketIO, SocketIONamespace, EngineIONamespace

from exceptions import HeimdallrClientException
from utils import timestamp, for_own_methods, on_ready
from settings import AUTH_SOURCE, URL


__all__ = ['Client', 'Provider', 'Consumer']


def _init(self, io):
    self._io = io
    self._callback_by_event = {}
    self._log_name = Client._url
    self.initialize()


EngineIONamespace.__init__ = _init


class _SocketIO(SocketIO):
    def _should_stop_waiting(self, **kwargs):
        event = kwargs.pop('event', None)
        event_set = False
        if isinstance(event, _Event):
            event_set = event.is_set()
        return super(_SocketIO, self)._should_stop_waiting(**kwargs) or \
            event_set


class Client():
    """
    The ``Client`` class provides most of the behavior for
    Heimdallr clients. However, it is not intended to be
    used directly. The ``Client`` constructor creates the
    basic connection which in this case is a
    ``SocketIONamespace``. It sets up callbacks for
    connection and authentication as well as a default
    callback for errors. The default error handler can be
    removed by ``client.remove_listener('err')``.

    Args:
        token (str): Authentication token
    """

    _url = URL
    _auth_source = AUTH_SOURCE
    _namespace = '/'
    _safe = True

    def __init__(self, token):
        self.ready = False
        self.ready_callbacks = []
        self.callbacks = {}
        self.token = token
        self.connection = SocketIONamespace(None, self._namespace)

        emit = self.connection.emit

        def safe_emit(*args, **kwargs):
            try:
                emit(*args, **kwargs)
            except Exception as e:
                print (
                    'HeimdallrClient failed to send. Original exception: %s'
                    % e.message
                )

        if self._safe:
            self.connection.emit = safe_emit

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

        def on_connect(*args):
            self.connection.emit(
                'authorize',
                {'token': self.token, 'authSource': self._auth_source}
            )

        self.on('connect', on_connect)
        self.on('reconnect', on_connect)

    def connect(self, **kwargs):
        """ Connect to the Heimdallr server.

        The ``connect`` method blocks until the the socket connection
        to the server has been established.

        Args:
            **kwargs: Passed to underlying SocketIO constructor

        :returns: :class:`Client <Client>`
        """

        try:
            parsed = urlparse(self._url)
            if self.connection._io and self.connection._io.connected:
                self.connection.disconnect()
            self.connection._io = _SocketIO(
                '%s://%s' % (parsed.scheme, parsed.hostname),
                parsed.port,
                **kwargs
            )
            io = self.connection._io
            io._namespace = self.connection
            io._namespace_by_path[self._namespace] = self.connection
            io.connect(self._namespace)
            io.wait(for_connect=True)
        except Exception as e:
            if not self._safe:
                raise e

            print 'HeimdallrClient failed to connect: %s' % e.message

        return self

    def run(self, seconds=None, **kwargs):
        """ Main loop for a client.

        The ``run`` method is the main loop for a client and is where
        all communication between the Heimdallr server and client
        takes place. The ``run`` method is just a proxy for the
        ``SocketIO.wait`` method so you can call it with the
        same arguments. However, an additional ``event`` option has
        been added. If a :py:class:`threading.Event` object is passed in for
        ``event``, the wait loop will terminate once the flag is set.

        Args:
            seconds (float): Number of seconds to loop for
            event (:py:class:`threading.Event`): Triggers the exit of the run
                loop when the flag is set
            for_connect (bool): Run until the SocketIO connect event
            for_callback (bool): Run until the server has acknowledged all
                emits

        :returns: :class:`Client <Client>`

        **Usage:**

        .. code-block:: python

            client.run(1)  # Loops for 1 second
            from threading import Event
            event = Event()
            client.run(event=event)  # Loops until event.is_set() is True
            client.run()  # Loops forever
        """

        kwargs['seconds'] = seconds
        self.connection._io.wait(**kwargs)

        return self

    def __trigger_callbacks(self, message_name, *args):
        """ Call all of the callbacks for a socket.io message.

        A version of this method curried with ``message_name``
        is given to the underlying ``SocketIONamespace``. When the
        ``SocketIONamespace`` calls it each of the callbacks that
        have been attached to ``message_name`` will be called.

        Args:
            message_name (str): Name of the socket.io message to listen for
            args: Data sent with message
        """

        callbacks = self.callbacks.get(message_name, [])
        for callback in callbacks:
            callback(*args)

    def __on(self, message_name, callback):
        """ Store ``callback`` and register a placeholder callback.

        Appends ``callback`` to the list of callbacks for the
        given ``message_name``. Also assigns a placeholder
        callback to the underlying ``SocketIONamespace`` so that
        the placeholder can call all of the callbacks in
        the list.

        Args:
            message_name (str): Name of the socket.io message to listen for
            callback (function): Callback to be run when the socket.io message
                is heard
        """

        self.callbacks.setdefault(message_name, [])
        self.callbacks[message_name].append(callback)
        self.connection.on(
            message_name,
            partial(self.__trigger_callbacks, message_name)
        )

    def on(self, message_name, callback=None):
        """ Add a socket.io message listener.

        The ``on`` method will add a callback for socket.io messages
        of the specified message name. Multiple callbacks can be
        added for the same message name. They will be triggered
        in the order in which they were added. This method can be
        called outright or it can be used as a decorator.

        Args:
            message_name (str): Name of the socket.io message to listen for
            callback (function): Callback to run when the socket.io
                message is heard
                
        :returns: :class:`Client <Client>`

        **Usage:**

        .. code-block:: python

            def first(*args):
                print 'FIRST'

            client.on('myMessage', first)

            @client.on('myMessage')
            def second(*args):
                print 'SECOND'
        """

        # Decorator syntax
        if callback is None:
            def decorator(fn):
                self.__on(message_name, fn)
            return decorator

        # SocketIO-Client syntax
        self.__on(message_name, callback)

        return self

    def remove_listener(self, message_name, callback=None):
        """ Remove listener for socket.io message.

        If ``callback`` is specified, only the callbacks registered
        for ``message_name`` that match ``callback`` will be removed.
        If only ``message_name`` is specified, all of the callbacks
        will be removed.

        Args:
            message_name (str): Name of the socket.io message to remove
            callback (function): Specific callback to remove

        :returns: :class:`Client <Client>`
        """

        if callback:
            while callback in self.callbacks.get(message_name, []):
                self.callbacks[message_name].remove(callback)
        else:
            self.callbacks.pop(message_name, None)
            self.connection._callback_by_event.pop(message_name, None)

        return self


@for_own_methods(on_ready)
class Provider(Client):
    """
    This class should be used to create a Heimdallr provider.
    It inherits most of its functionality but it also
    automatically connects to the provider namespace and
    provides some convenience functions.
    """

    _namespace = '/provider'

    def send_event(self, subtype, data=None):
        """ Emit a Heimdallr event packet.

        This will send a Heimdallr event packet to the
        Heimdallr server where it will be rebroadcast.
        ``data`` must adhere to the provider's schema for
        the given ``subtype``.

        Args:
            subtype (str): The event packet subtype
            data: The event packet data

        :returns: :class:`Provider <Provider>`
        """

        self.connection.emit(
            'event',
            {'subtype': subtype, 'data': data, 't': timestamp()}
        )

    def send_sensor(self, subtype, data=None):
        """ Emit a Heimdallr sensor packet.

        This will send a Heimdallr sensor packet to the
        Heimdallr server where it will be rebroadcast.
        ``data`` must adhere to the provider's schema for
        the given ``subtype``.

        Args:
            subtype (str): The sensor packet subtype
            data: The sensor packet data

        :returns: :class:`Provider <Provider>`
        """

        self.connection.emit(
            'sensor',
            {'subtype': subtype, 'data': data, 't': timestamp()}
        )

    def send_stream(self, data):
        """ Send binary data to the Heimdallr server.

        This should only be used when the Heimdallr server
        has issued a ``{'stream': 'start'}`` control packet
        and should stop being used when the Heimdallr
        server issues a ``{'stream': 'start'}`` control
        packet.

        Args:
            data: The binary data to be sent.

        :returns: :class:`Provider <Provider>`
        """

        self.connection.emit(
            'stream',
            bytearray(data)
        )

    def completed(self, uuid):
        """ Signal the Heimdallr server that a control has been completed.

        This should be used when a control that has a persistent
        field set to ``uuid`` has been completed.

        Args:
            uuid (str): UUID of the persistent control packet that has been
                completed
                
        :returns: :class:`Provider <Provider>`
        """

        self.connection.emit(
            'event',
            {'subtype': 'completed', 'data': uuid, 't': timestamp()}
        )


@for_own_methods(on_ready)
class Consumer(Client):
    """
    This class should be used to create a Heimdallr consumer.
    It inherits most of its functionality but it also
    automatically connects to the consumer namespace and
    provides some convenience functions.
    """

    _namespace = '/consumer'

    def send_control(self, uuid, subtype, data=None, persistent=False):
        """ Emit a Heimdallr control packet.

        This will send a control to the provider specified by
        ``uuid``. ``data`` must adhere to the provider's schema
        for the given ``subtype``. If `persistent` is ``True``,
        the control packet will be sent immediately and then
        again every time the provider connects until the
        provider signals the Heimdallr server that it has
        completed the control.

        Args:
            uuid (str): UUID of the provider to send the control packet to
            subtype (str): The control packet subtype
            data: The control packet data
            persistent (bool): Whether or not the control should persist
            
        :returns: :class:`Consumer <Consumer>`
        """

        self.connection.emit(
            'control',
            {
                'provider': uuid,
                'subtype': subtype,
                'data': data,
                'persistent': persistent
            }
        )

    def subscribe(self, uuid):
        """ Subscribe to a provider.

        A consumer must subscribe to a provider before it
        receives event or sensor packets from the provider
        or can send control packets to the provider.

        Args:
            uuid (str): UUID of the provider to subscribe to
            
        :returns: :class:`Consumer <Consumer>`
        """

        self.connection.emit(
            'subscribe',
            {'provider': uuid}
        )

    def unsubscribe(self, uuid):
        """ Unsubscribe from a provider.

        The consumer will no longer receive packets from the
        provider or be able to send it controls. This will
        be done automatically by the Heimdallr server on
        disconnect.


        Args:
            uuid (str): UUID of the provider to subscribe to

        :returns: :class:`Consumer <Consumer>`
        """

        self.connection.emit(
            'unsubscribe',
            {'provider': uuid}
        )

    def set_filter(self, uuid, filter_):
        """ Control which event and sensor subtypes to hear from provider.

        Set which packet subtypes you want to hear from the provider.
        `filter` should be a dictionary with the keys `event` and/or
        `sensor`. The value of those fields should be an array of
        strings of the subtypes that you want to hear for the
        provider given by `uuid`.

        Args:
            uuid (str): UUID of the provider to filter packets from
            filter_ (dict): Dictionary containing event and/or sensor packet
                subtypes that you want to receive

        :returns: :class:`Consumer <Consumer>`
        """

        filter_['provider'] = uuid
        self.connection.emit(
            'setFilter',
            filter_
        )

    def get_state(self, uuid, subtypes):
        """ Get the current state of a provider.

        For each event packet subtype in `subtypes`, the most recent
        event packet of that subtype will be sent to the consumer by
        the Heimdallr server.

        Args:
            uuid (str): UUID of the provider to get the state of
            subtypes (list): Event subtypes to get the state of

        :returns: :class:`Consumer <Consumer>`
        """

        self.connection.emit(
            'getState',
            {'provider': uuid, 'subtypes': subtypes}
        )

    def join_stream(self, uuid):
        """ Join binary data stream from a provider.

        If this is the first consumer to join the stream of
        a provider, the Heimdallr server will send a
        ``{'stream': 'start'}`` control packet to the provider.

        Args:
            uuid (str): UUID of the provider to join the stream of

        :returns: :class:`Consumer <Consumer>`
        """

        self.connection.emit(
            'joinStream',
            {'provider': uuid}
        )

    def leave_stream(self, uuid):
        """ Leave binary data stream for a provider.

        If this is the last consumer to leave the stream for a
        provider the Heimdallr server will send a
        ``{'stream': 'stop'}`` control packet to the provider.
        This will be done automatically by the Heimdallr server
        on disconnect.

        Args:
            uuid (str): UUID of the provider to leave the stream of

        :returns: :class:`Consumer <Consumer>`
        """

        self.connection.emit(
            'leaveStream',
            {'provider': uuid}
        )