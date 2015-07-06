import os
import unittest
import json
from subprocess import Popen, PIPE
from threading import Event
from functools import partial
from time import sleep

from heimdallr_client import Client, Provider, Consumer, HeimdallrClientException


# Setup test server
DIR = os.path.dirname(os.path.realpath(__file__))
PORT = 3000
UUID = 'c7528fa8-0a7b-4486-bbdc-460905ffa035'

Client.url = 'http://localhost:%s' % PORT
shared = {}


def setUpModule():
    server_filepath = os.path.join(DIR, 'server.js')
    shared['pipe'] = Popen('PORT=%s node %s' % (PORT, server_filepath), shell=True, stdin=PIPE, stdout=PIPE)
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

    def tearDown(self):
        pass

    def set_packet_received(self, *args):
        self.packet_received.set()

    def wait_for_packet(self, client):
        client.wait(seconds=3, event=self.packet_received)
        if not self.packet_received.is_set():
            self.fail('Timeout reached')

    def trigger(self, kind):
        shared['stdin'].write('%s\n' % json.dumps({'action': 'send-%s' % kind, 'client': self.client_type}))
        shared['stdin'].flush()


class ProviderTestCase(HeimdallrClientTestCase):
    def setUp(self):
        super(ProviderTestCase, self).setUp()
        self.client_type = 'provider'
        self.provider = Provider('valid-token')
        self.provider.connect()

    def tearDown(self):
        super(ProviderTestCase, self).tearDown()

    def test_receives_packets(self):
        def fn(data):
            self.assertDictEqual(data, {'ping': 'data'}, 'Ping data did not match')
            self.packet_received.set()

        self.provider.on('ping', fn)
        self.trigger('ping')
        self.wait_for_packet(self.provider)

    def test_raises_exceptions(self):
        self.trigger('error')
        self.assertRaises(HeimdallrClientException, partial(self.wait_for_packet, self.provider))

    def test_decorates_callbacks(self):
        @self.provider.on('ping')
        def fn(data):
            self.assertDictEqual(data, {'ping': 'data'}, 'Ping data did not match')
            self.packet_received.set()

        self.trigger('ping')
        self.wait_for_packet(self.provider)

    def test_send_event(self):
        self.provider.on('heardEvent', self.set_packet_received)
        self.provider.send_event('test')
        self.wait_for_packet(self.provider)

    def test_send_sensor(self):
        self.provider.on('heardSensor', self.set_packet_received)
        self.provider.send_sensor('test')
        self.wait_for_packet(self.provider)

    def test_waits_until_ready(self):
        self.heard_event = False
        provider = Provider('valid-token')

        @provider.on('heardEvent')
        def fn(data):
            self.assertTrue(provider.ready, 'Provider was not ready')
            self.heard_event = True

        @provider.on('heardSensor')
        def fn(data):
            self.assertTrue(self.heard_event, 'Order was not preserved')
            self.packet_received.set()

        provider.send_event('test')
        provider.send_sensor('test')
        sleep(2)
        provider.connect()
        self.wait_for_packet(provider)

    def test_remove_listener(self):
        self.provider.remove_listener('err')
        self.provider.on('err', self.set_packet_received)
        self.trigger('error')
        self.wait_for_packet(self.provider)

    def test_completes_control(self):
        self.provider.on('completedControl', self.set_packet_received)
        self.provider.completed('test')
        self.wait_for_packet(self.provider)

    def test_snake_case_off(self):
        @self.provider.on('snakeCasePacket')
        def fn(data):
            self.assertDictEqual(data, {'caseTest': {'receivedUnderscore': True}}, 'Case conversion failed')
            self.packet_received.set()

        self.provider.send_event('snake_case')
        self.wait_for_packet(self.provider)
        self.packet_received.clear()
        self.provider.send_sensor('snake_case')
        self.wait_for_packet(self.provider)

    def test_snake_case_on(self):
        self.provider.snake_case = True
        @self.provider.on('snake_case_packet')
        def fn(data):
            self.assertDictEqual(data, {'case_test': {'received_underscore': False}}, 'Case conversion failed')
            self.packet_received.set()

        self.provider.send_event('snake_case')
        self.wait_for_packet(self.provider)
        self.packet_received.clear()
        self.provider.send_sensor('snake_case')
        self.wait_for_packet(self.provider)


class ConsumerTestCase(HeimdallrClientTestCase):
    def setUp(self):
        super(ConsumerTestCase, self).setUp()
        self.client_type = 'consumer'
        self.consumer = Consumer('valid-token')
        self.consumer.connect()

    def tearDown(self):
        super(ConsumerTestCase, self).tearDown()

    def test_receives_packets(self):
        def fn(data):
            self.assertDictEqual(data, {'ping': 'data'}, 'Ping data did not match')
            self.packet_received.set()

        self.consumer.on('ping', fn)
        self.trigger('ping')
        self.wait_for_packet(self.consumer)

    def test_raises_exceptions(self):
        self.trigger('error')
        self.assertRaises(HeimdallrClientException, partial(self.wait_for_packet, self.consumer))

    def test_decorates_callbacks(self):
        @self.consumer.on('ping')
        def fn(data):
            self.assertDictEqual(data, {'ping': 'data'}, 'Ping data did not match')
            self.packet_received.set()

        self.trigger('ping')
        self.wait_for_packet(self.consumer)

    def test_send_control(self):
        self.consumer.on('heardControl', self.set_packet_received)
        self.consumer.send_control(UUID, 'test')
        self.wait_for_packet(self.consumer)

    def test_waits_until_ready(self):
        self.heard_control = False
        consumer = Consumer('valid-token')

        @consumer.on('heardControl')
        def fn(data):
            self.assertTrue(consumer.ready, 'Provider was not ready')
            self.heard_control = True

        @consumer.on('checkedPacket')
        def fn(data):
            self.assertTrue(self.heard_control, 'Order was not preserved')
            self.packet_received.set()

        consumer.send_control(UUID, 'test')
        consumer.subscribe(UUID)
        sleep(2)
        consumer.connect()
        self.wait_for_packet(consumer)

    def test_remove_listener(self):
        self.consumer.remove_listener('err')
        self.consumer.on('err', self.set_packet_received)
        self.trigger('error')
        self.wait_for_packet(self.consumer)

    def test_set_filter(self):
        self.consumer.on('checkedPacket', self.set_packet_received)
        self.consumer.set_filter(UUID, {'event': [], 'sensor': []})
        self.wait_for_packet(self.consumer)

    def test_get_state(self):
        self.consumer.on('checkedPacket', self.set_packet_received)
        self.consumer.get_state(UUID, [])
        self.wait_for_packet(self.consumer)

    def test_subscription_actions(self):
        subscription_actions = ['subscribe', 'unsubscribe', 'join_stream', 'leave_stream']
        self.count = 0

        @self.consumer.on('checkedPacket')
        def fn(data):
            self.count += 1
            if self.count == len(subscription_actions):
                self.packet_received.set()

        for action in subscription_actions:
            getattr(self.consumer, action)(UUID)

        self.wait_for_packet(self.consumer)

    def test_snake_case_off(self):
        @self.consumer.on('snakeCasePacket')
        def fn(data):
            self.assertDictEqual(data, {'caseTest': {'receivedUnderscore': True}}, 'Case conversion failed')
            self.packet_received.set()

        self.consumer.send_control(UUID, 'snake_case')
        self.wait_for_packet(self.consumer)

    def test_snake_case_on(self):
        self.consumer.snake_case = True
        @self.consumer.on('snake_case_packet')
        def fn(data):
            self.assertDictEqual(data, {'case_test': {'received_underscore': False}}, 'Case conversion failed')
            self.packet_received.set()

        self.consumer.send_control(UUID, 'snake_case')
        self.wait_for_packet(self.consumer)