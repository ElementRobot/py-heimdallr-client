"use strict";

var PORT = process.env.PORT,
    io = require('socket.io').listen(PORT),
    _ = require('lodash'),
    readline = require('readline'),
    validator = require('heimdallr-validator');

var sockets = {},
    input;

io.of('/provider').on('connect', function (socket) {
    sockets.provider = socket;

    socket.on('authorize', function (packet) {
        if (!packet.token) {
            socket.emit('err', 'No token provided');
            return;
        }
        socket.emit('auth-success');
    }).on('event', function (packet) {
        validator.validatePacket('event', packet, function (err) {
            if (err) {
                socket.emit('err', err);
                return;
            }
            socket.emit('heardEvent', packet);
            if (packet.subtype === 'ping') {
                socket.emit('pong');
            } else if (packet.subtype === 'completed') {
                socket.emit('completedControl');
            }
        });
    }).on('sensor', function (packet) {
        validator.validatePacket('sensor', packet, function (err) {
            if (err) {
                socket.emit('err', err);
                return;
            }
            socket.emit('heardSensor', packet);
        });
    }).on('stream', function (data) {
        if (data.constructor === Buffer.prototype.constructor) {
            socket.emit('heardStream');
        }
    });
});

io.of('/consumer').on('connect', function (socket) {
    sockets.consumer = socket;

    function checkConsumerPacket(packet) {
        if (!packet) {
            socket.emit('err', 'No packet provided');
            return;
        }

        if (!packet.provider) {
            socket.emit('err', 'No provider specified');
            return;
        }
        socket.emit('checkedPacket', 'consumer');
    }

    socket.on('authorize', function (packet) {
        if (!packet.token) {
            socket.emit('err', 'No token provided');
            return;
        }
        socket.emit('auth-success');
    }).on('control', function (packet) {
        validator.validatePacket('control', packet, function (err) {
            if (err) {
                socket.emit('err', err);
                return;
            }
            socket.emit('heardControl', packet);
            if (packet.subtype === 'ping') {
                socket.emit('pong');
            }
        });
    }).on('setFilter', function (packet) {
        checkConsumerPacket(packet);
        if (!(packet.event instanceof Array) && !(packet.sensor instanceof Array)) {
            socket.emit('err', 'Invalid `filter`');
            return;
        }
        socket.emit('checkedPacket', 'setFilter');
    }).on('getState', function (packet) {
        checkConsumerPacket(packet);
        if (!packet.subtypes) {
            socket.emit('err', 'No subtypes provided');
            return;
        }
        socket.emit('checkedPacket', 'getState');
    });

    // Subsctiption actions
    socket.on('subscribe', checkConsumerPacket)
        .on('unsubscribe', checkConsumerPacket)
        .on('joinStream', checkConsumerPacket)
        .on('leaveStream', checkConsumerPacket);
});

input = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

input.on('line', function (line) {
    var message = JSON.parse(line),
        client = sockets[message.client];

    if (message.action === 'send-ping') {
        client.emit('ping', {ping: 'data'});
    } else if (message.action === 'send-JSON-error') {
        client.emit('err', {message: 'error'});
    } else if (message.action === 'send-js-error') {
        client.emit('err', new Error('error'));
    } else if (message === 'close') {
        input.close();
        process.exit();
    }
});

console.log('SERVER READY');