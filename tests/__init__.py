import os
import unittest
import json
from subprocess import Popen, PIPE
from threading import Event
from functools import partial
from requests.packages import urllib3

from heimdallr_client import Client, Provider, Consumer, HeimdallrClientException

# Turn off SubjectAltNameWarning
urllib3.disable_warnings(urllib3.exceptions.SubjectAltNameWarning)

# Setup test server
DIR = os.path.dirname(os.path.realpath(__file__))
PORT = 3000
UUID = 'c7528fa8-0a7b-4486-bbdc-460905ffa035'
CONNECT_KWARGS = {'verify': os.path.join(DIR, 'certs/localhost-cert.pem')}

Client._url = 'https://localhost:%s' % PORT
Client._safe = False
shared = {}


def setUpModule():
    server_filepath = os.path.join(DIR, 'server.js')
    shared['pipe'] = Popen(
        'PORT=%s node %s' % (PORT, server_filepath),
        shell=True,
        stdin=PIPE,
        stdout=PIPE
    )
    shared['stdin'] = shared['pipe'].stdin
    print shared['pipe'].stdout.readline()


def tearDownModule():
    shared['stdin'].write('%s\n' % json.dumps('close'))
    shared['stdin'].flush()
    stdout, stderr = shared['pipe'].communicate()
    print '\n\nSERVER OUTPUT: %s\n' % stdout
    print 'SERVER ERROR: %s\n' % stderr


class HeimdallrClientTestCase(unittest.TestCase):
    def setUp(self):
        self.packet_received = Event()
        self.client_type = None
        self.client = None

    def tearDown(self):
        pass

    def set_packet_received(self, *args):
        self.packet_received.set()

    def wait_for_packet(self, client=None):
        client = client or self.client
        client.run(seconds=3, event=self.packet_received)
        if not self.packet_received.is_set():
            self.fail('Timeout reached')

    def trigger(self, kind):
        shared['stdin'].write(
            '%s\n' % json.dumps(
                {'action': 'send-%s' % kind, 'client': self.client_type}
            )
        )
        shared['stdin'].flush()


class ProviderTestCase(HeimdallrClientTestCase):
    def setUp(self):
        super(ProviderTestCase, self).setUp()
        self.client_type = 'provider'
        self.provider = Provider('valid-token')
        self.provider.connect(**CONNECT_KWARGS)
        self.client = self.provider

    def tearDown(self):
        super(ProviderTestCase, self).tearDown()

    def test_receives_packets(self):
        def fn(data):
            self.assertDictEqual(
                data,
                {'ping': 'data'},
                'Ping data did not match'
            )
            self.packet_received.set()

        self.provider.on('ping', fn)
        self.trigger('ping')
        self.wait_for_packet()

    def test_raises_exceptions(self):
        self.trigger('JSON-error')
        self.assertRaises(
            HeimdallrClientException,
            partial(self.wait_for_packet, self.provider)
        )
        self.trigger('js-error')
        self.assertRaises(
            HeimdallrClientException,
            partial(self.wait_for_packet, self.provider)
        )

    def test_decorates_callbacks(self):
        @self.provider.on('ping')
        def fn(data):
            self.assertDictEqual(
                data,
                {'ping': 'data'},
                'Ping data did not match'
            )
            self.packet_received.set()

        self.trigger('ping')
        self.wait_for_packet()

    def test_send_event(self):
        self.provider.on('heardEvent', self.set_packet_received)
        self.provider.send_event('test')
        self.wait_for_packet()

    def test_send_sensor(self):
        self.provider.on('heardSensor', self.set_packet_received)
        self.provider.send_sensor('test')
        self.wait_for_packet()

    def test_send_stream(self):
        self.provider.on('heardStream', self.set_packet_received)
        self.provider.send_stream('\x21')
        self.wait_for_packet()

    def test_on_ready(self):
        self.heard_event = False
        provider = Provider('valid-token')

        @provider.on('heardEvent')
        def fn(*args):
            self.assertTrue(provider.ready, 'Provider was not ready')
            self.heard_event = True

        @provider.on('heardSensor')
        def fn(*args):
            self.assertTrue(self.heard_event, 'Order was not preserved')
            provider.send_event('ping')

        @provider.on('pong')
        def fn(*args):
            self.packet_received.set()

        provider.send_event('test').send_sensor('test')
        provider.connect(**CONNECT_KWARGS)
        self.wait_for_packet(provider)

    def test_multiple_listeners(self):
        self.called_first = False

        @self.provider.on('ping')
        def fn(*args):
            self.called_first = True

        @self.provider.on('ping')
        def fn(*args):
            self.assertTrue(self.called_first, 'Order was not preserved')
            self.set_packet_received()

        self.trigger('ping')
        self.wait_for_packet()

    def test_remove_listener(self):
        def callback(*args):
            self.fail('Called removed listener')

        @self.provider.on('ping')
        def fn(*args):
            callback()

        @self.provider.on('ping')
        def fn(*args):
            callback()

        self.provider.remove_listener('ping')

        self.provider.on('ping', callback)

        @self.provider.on('ping')
        def fn(*args):
            self.set_packet_received()

        self.provider.remove_listener('ping', callback)
        self.trigger('ping')
        self.wait_for_packet()

    def test_completes_control(self):
        self.provider.on('completedControl', self.set_packet_received)
        self.provider.completed('test')
        self.wait_for_packet()


class ConsumerTestCase(HeimdallrClientTestCase):
    def setUp(self):
        super(ConsumerTestCase, self).setUp()
        self.client_type = 'consumer'
        self.consumer = Consumer('valid-token')
        self.consumer.connect(**CONNECT_KWARGS)
        self.client = self.consumer

    def tearDown(self):
        super(ConsumerTestCase, self).tearDown()

    def test_receives_packets(self):
        def fn(data):
            self.assertDictEqual(
                data,
                {'ping': 'data'},
                'Ping data did not match'
            )
            self.packet_received.set()

        self.consumer.on('ping', fn)
        self.trigger('ping')
        self.wait_for_packet()

    def test_raises_exceptions(self):
        self.trigger('JSON-error')
        self.assertRaises(
            HeimdallrClientException,
            partial(self.wait_for_packet, self.consumer)
        )
        self.trigger('js-error')
        self.assertRaises(
            HeimdallrClientException,
            partial(self.wait_for_packet, self.consumer)
        )

    def test_decorates_callbacks(self):
        @self.consumer.on('ping')
        def fn(data):
            self.assertDictEqual(
                data,
                {'ping': 'data'},
                'Ping data did not match'
            )
            self.packet_received.set()

        self.trigger('ping')
        self.wait_for_packet()

    def test_send_control(self):
        self.consumer.on('heardControl', self.set_packet_received)
        self.consumer.send_control(UUID, 'test')
        self.wait_for_packet()

    def test_on_ready(self):
        self.heard_control = False
        consumer = Consumer('valid-token')

        @consumer.on('heardControl')
        def fn(*args):
            self.assertTrue(consumer.ready, 'Provider was not ready')
            self.heard_control = True

        @consumer.on('checkedPacket')
        def fn(*args):
            self.assertTrue(self.heard_control, 'Order was not preserved')

        @consumer.on('pong')
        def fn(*args):
            self.packet_received.set()

        consumer.send_control(UUID, 'test').subscribe(UUID)
        consumer.connect(**CONNECT_KWARGS)
        consumer.send_control(UUID, 'ping')
        self.wait_for_packet(consumer)

    def test_multiple_listeners(self):
        self.called_first = False

        @self.consumer.on('ping')
        def fn(*args):
            self.called_first = True

        @self.consumer.on('ping')
        def fn(*args):
            self.assertTrue(self.called_first, 'Order was not preserved')
            self.set_packet_received()

        self.trigger('ping')
        self.wait_for_packet()

    def test_remove_listener(self):
        def callback(*args):
            self.fail('Called removed listener')

        @self.consumer.on('ping')
        def fn(*args):
            callback()

        @self.consumer.on('ping')
        def fn(*args):
            callback()

        self.consumer.remove_listener('ping')

        self.consumer.on('ping', callback)

        @self.consumer.on('ping')
        def fn(*args):
            self.set_packet_received()

        self.consumer.remove_listener('ping', callback)
        self.trigger('ping')
        self.wait_for_packet()

    def test_set_filter(self):
        self.consumer.on('checkedPacket', self.set_packet_received)
        self.consumer.set_filter(UUID, {'event': [], 'sensor': []})
        self.wait_for_packet()

    def test_get_state(self):
        self.consumer.on('checkedPacket', self.set_packet_received)
        self.consumer.get_state(UUID, [])
        self.wait_for_packet()

    def test_subscription_actions(self):
        subscription_actions = [
            'subscribe',
            'unsubscribe',
            'join_stream',
            'leave_stream'
        ]
        self.count = 0

        @self.consumer.on('checkedPacket')
        def fn(*args):
            self.count += 1
            if self.count == len(subscription_actions):
                self.packet_received.set()

        for action in subscription_actions:
            getattr(self.consumer, action)(UUID)

        self.wait_for_packet()


if __name__ == '__main__':
    unittest.main()