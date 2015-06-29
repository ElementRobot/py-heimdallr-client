import os
import unittest
import json
from subprocess import Popen, PIPE
from threading import Event
from time import sleep

from heimdallr_client import Provider, Consumer


# Setup test server
DIR = os.path.dirname(os.path.realpath(__file__))
PORT = 3000
URL = 'http://localhost:%s' % PORT
UUID = 'c7528fa8-0a7b-4486-bbdc-460905ffa035'
server_filepath = os.path.join(DIR, 'server.js')
stdin = Popen('PORT=%s node %s' % (PORT, server_filepath), shell=True, stdin=PIPE).stdin


class HeimdallrClientTestCase(unittest.TestCase):
    def setUp(self):
        self.packet_received = Event()
        self.client_type = None
        self.client = None

    def tearDown(self):
        pass

    def set_packet_received(self, *args):
        self.packet_received.set()

    def wait_for_packet(self):
        if not self.packet_received.wait(3):
            self.fail('Timeout reached')

    def trigger(self, packet_type):
        stdin.write(json.dumps({'action': 'send-%s' % packet_type, 'client': self.client_type}))
        stdin.flush()


class ProviderTestCase(HeimdallrClientTestCase):
    def setUp(self):
        super(ProviderTestCase, self).setUp()
        self.client_type = 'provider'
        self.client = Provider('valid-token')
        self.client.connect()

    def tearDown(self):
        super(ProviderTestCase, self).tearDown()

    def test_receives_packets(self):
        def callback(data):
            self.assertDictEqual(data, {'ping': 'data'}, 'Ping data did not match')
            self.packet_received.set()

        self.client.on('ping', callback)
        self.trigger('ping')
        self.wait_for_packet()

    def test_raises_exceptions(self):
        self.trigger('error')

    def test_decorates_callbacks(self):
        @self.client.on('ping')
        def callback(data):
            self.assertDictEqual(data, {'ping': 'data'}, 'Ping data did not match')
            self.packet_received.set()

        self.trigger('ping')
        self.wait_for_packet()

    def test_send_event(self):
        self.client.on('heardEvent', self.set_packet_received)
        self.client.send_event('test', None)
        self.wait_for_packet()

    def test_send_sensor(self):
        self.client.on('heardSensor', self.set_packet_received)
        self.client.send_sensor('test', None)
        self.wait_for_packet()

    def test_waits_until_ready(self):
        self.heard_event = False
        provider = Provider('valid-token')

        @provider.on('heardEvent')
        def callback(data):
            self.assertTrue(self.client.ready, 'Provider was not ready')
            self.heard_event = True

        @provider.on('heardSensor')
        def callback(data):
            self.assertTrue(self.heard_event, 'Order was not preserved')
            self.packet_received.set()

        provider.send_event('test', None).send_sensor('test', None)
        sleep(2)
        provider.connect()
        self.wait_for_packet()

    def test_remove_listener(self):
        self.client.remove_listener('err')
        self.client.on('err', self.set_packet_received)
        self.trigger('err')
        self.wait_for_packet()

    def test_completes_control(self):
        self.client.on('completedControl', self.set_packet_received)
        self.client.completed('test')
        self.wait_for_packet()

    def test_snake_case_off(self):
        @self.client.on('snakeCasePacket')
        def callback(data):
            self.assertDictEqual(data, {'caseTest': {'receivedUnderscore': True}}, 'Case conversion failed')
            self.packet_received.set()

        self.client.send_event('snake_case')
        self.wait_for_packet()
        self.packet_received.clear()
        self.client.send_sensor('snake_case')
        self.wait_for_packet()

    def test_snake_case_on(self):
        self.client.snake_case = True
        @self.client.on('snake_case_packet')
        def callback(data):
            self.assertDictEqual(data, {'case_test': {'received_underscore': False}}, 'Case conversion failed')
            self.packet_received.set()

        self.client.send_event('snake_case')
        self.wait_for_packet()
        self.packet_received.clear()
        self.client.send_sensor('snake_case')
        self.wait_for_packet()


class ConsumerTestCase(HeimdallrClientTestCase):
    def setUp(self):
        super(ConsumerTestCase, self).setUp()
        self.client_type = 'consumer'
        self.client = Consumer('valid-token')
        self.client.connect()

    def tearDown(self):
        super(ConsumerTestCase, self).tearDown()

    def test_receives_packets(self):
        def callback(data):
            self.assertDictEqual(data, {'ping': 'data'}, 'Ping data did not match')
            self.packet_received.set()

        self.client.on('ping', callback)
        self.trigger('ping')
        self.wait_for_packet()

    def test_raises_exceptions(self):
        self.trigger('error')

    def test_decorates_callbacks(self):
        @self.client.on('ping')
        def callback(data):
            self.assertDictEqual(data, {'ping': 'data'}, 'Ping data did not match')
            self.packet_received.set()

        self.trigger('ping')
        self.wait_for_packet()

    def test_send_control(self):
        self.client.on('heardControl', self.set_packet_received)
        self.client.send_control('test', None)
        self.wait_for_packet()

    def test_waits_until_ready(self):
        self.heard_event = False
        consumer = Consumer('valid-token')

        @consumer.on('heardControl')
        def callback(data):
            self.assertTrue(self.client.ready, 'Provider was not ready')
            self.heard_event = True

        consumer.send_control(UUID, 'test', None).send_sensor('test', None)
        sleep(2)
        consumer.connect()
        self.wait_for_packet()

    def test_remove_listener(self):
        self.client.remove_listener('err')
        self.client.on('err', self.set_packet_received)
        self.trigger('err')
        self.wait_for_packet()

    def test_set_filter(self):
        self.client.on('checkedPacket', self.set_packet_received)
        self.client.set_filter(UUID, {'event': [], 'sensor': []})
        self.wait_for_packet()

    def test_get_state(self):
        self.client.on('checkedPacket', self.set_packet_received)
        self.client.get_state(UUID, [])
        self.wait_for_packet()

    def test_subscription_actions(self):
        subscription_actions = ['subscribe', 'unsubscribe', 'joinStream', 'leaveStream']
        self.count = 0

        @self.client.on('checkedPacket')
        def callback(data):
            self.count += 1
            if self.count == len(subscription_actions):
                self.packet_received.set()

        for action in subscription_actions:
            getattr(self.client, action)(UUID)

        self.wait_for_packet()