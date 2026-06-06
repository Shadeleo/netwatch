/**
 * ws.js — WebSocket Connection Manager
 * Manages real-time connection to NetWatch API
 */

class WebSocketManager {
  constructor(url = null) {
    // Use current domain for WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.host;
    this.url = url || `${protocol}://${host}/ws`;
    
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000;
    this.handlers = {};
    this.isConnected = false;
  }

  /**
   * Subscribe to a message type
   */
  on(type, callback) {
    if (!this.handlers[type]) {
      this.handlers[type] = [];
    }
    this.handlers[type].push(callback);
  }

  /**
   * Emit event to all subscribers
   */
  emit(type, data) {
    if (this.handlers[type]) {
      this.handlers[type].forEach(callback => callback(data));
    }
  }

  /**
   * Connect to WebSocket server
   */
  connect() {
    try {
      console.log(`🔌 Connecting to WebSocket: ${this.url}`);
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => this.handleOpen();
      this.ws.onmessage = (event) => this.handleMessage(event);
      this.ws.onerror = (error) => this.handleError(error);
      this.ws.onclose = () => this.handleClose();
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Handle WebSocket open
   */
  handleOpen() {
    console.log('✅ WebSocket connected');
    this.isConnected = true;
    this.reconnectAttempts = 0;
    this.emit('connected', { timestamp: new Date() });
    this.updateStatus('CONNECTED');
  }

  /**
   * Handle incoming message
   */
  handleMessage(event) {
    try {
      const message = JSON.parse(event.data);
      
      // Handle different message types
      if (message.type === 'stats_update') {
        this.emit('stats', message.data);
        if (message.alerts) {
          this.emit('alerts', message.alerts);
        }
      } else if (message.type === 'connected') {
        this.emit('connected', message);
      } else if (message.type === 'ping') {
        // Just a keep-alive ping
      } else {
        this.emit(message.type, message);
      }
    } catch (error) {
      console.error('Error parsing message:', error);
    }
  }

  /**
   * Handle WebSocket error
   */
  handleError(error) {
    console.error('❌ WebSocket error:', error);
    this.updateStatus('ERROR');
    this.emit('error', error);
  }

  /**
   * Handle WebSocket close
   */
  handleClose() {
    console.log('🔌 WebSocket disconnected');
    this.isConnected = false;
    this.updateStatus('DISCONNECTED');
    this.emit('disconnected', {});
    this.scheduleReconnect();
  }

  /**
   * Schedule reconnection attempt
   */
  scheduleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * this.reconnectAttempts;
      console.log(`⏳ Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('❌ Max reconnection attempts reached');
      this.updateStatus('ERROR');
    }
  }

  /**
   * Update connection status badge
   */
  updateStatus(status) {
    const badge = document.getElementById('status-badge');
    const label = document.getElementById('status-label');
    
    if (!badge || !label) return;
    
    badge.className = 'status-badge';
    
    switch (status) {
      case 'CONNECTED':
        badge.classList.add('live');
        label.textContent = 'LIVE';
        break;
      case 'CONNECTING':
        label.textContent = 'CONNECTING…';
        break;
      case 'DISCONNECTED':
        label.textContent = 'DISCONNECTED';
        badge.classList.add('error');
        break;
      case 'ERROR':
        label.textContent = 'ERROR';
        badge.classList.add('error');
        break;
    }
  }

  /**
   * Send message to server
   */
  send(data) {
    if (this.isConnected && this.ws) {
      this.ws.send(JSON.stringify(data));
    }
  }

  /**
   * Close connection
   */
  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Create global instance
const wsManager = new WebSocketManager();

// Auto-connect on page load
document.addEventListener('DOMContentLoaded', () => {
  wsManager.connect();
});
