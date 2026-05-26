/**
 * SocketClient - WebSocket wrapper using Socket.IO
 */
class SocketClient {
    constructor(serverUrl = 'http://localhost:5000') {
        this.socket = io(serverUrl);
        this.callbacks = {};
        this.connected = false;
        this.setupListeners();
    }

    setupListeners() {
        this.socket.on('connect', () => {
            console.log('Connected to simulation server');
            this.connected = true;
            this.trigger('connected', {});
        });

        this.socket.on('state_update', (state) => {
            this.trigger('state_update', state);
        });

        this.socket.on('simulation_finished', (data) => {
            this.trigger('finished', data);
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.connected = false;
            this.trigger('disconnected', {});
        });

        this.socket.on('error', (error) => {
            console.error('Socket error:', error);
            this.trigger('error', error);
        });
    }

    on(event, callback) {
        if (!this.callbacks[event]) {
            this.callbacks[event] = [];
        }
        this.callbacks[event].push(callback);
    }

    trigger(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(cb => cb(data));
        }
    }

    requestState() {
        this.socket.emit('request_state');
    }

    disconnect() {
        this.socket.disconnect();
    }
}
