/**
 * app.js — Main Application Logic
 * Coordinates WebSocket, charts, and alerts
 */

class NetWatchApp {
  constructor() {
    this.maxConnections = 50;
    this.connections = [];
    this.stats = null;
    this.init();
  }

  /**
   * Initialize application
   */
  init() {
    console.log('🚀 NetWatch Dashboard Initializing...');
    
    // Subscribe to WebSocket events
    wsManager.on('stats', (stats) => this.handleStatsUpdate(stats));
    wsManager.on('alerts', (alerts) => this.handleAlerts(alerts));
    wsManager.on('connected', () => this.handleConnected());
    wsManager.on('disconnected', () => this.handleDisconnected());
    wsManager.on('error', () => this.handleError());

    // Initialize UI
    this.setupUI();
  }

  /**
   * Setup UI event listeners
   */
  setupUI() {
    // Responsive table scroll indicator
    const tableWrap = document.querySelector('.table-wrap');
    if (tableWrap) {
      tableWrap.addEventListener('scroll', (e) => {
        const target = e.target;
        const isAtBottom = Math.abs(
          target.scrollHeight - target.scrollTop - target.clientHeight
        ) < 5;
        // Could add "more data" indicator here
      });
    }
  }

  /**
   * Handle statistics update
   */
  handleStatsUpdate(stats) {
    this.stats = stats;

    // Update header stats
    this.updateHeaderStats(stats);

    // Update charts
    chartManager.updateBandwidth(stats);
    chartManager.updateProtocols(stats);

    // Update top IPs
    this.updateTopIPs(stats);

    // Update connections table
    this.updateConnections(stats);
  }

  /**
   * Update header statistics display
   */
  updateHeaderStats(stats) {
    // Total packets
    const packetsEl = document.getElementById('h-packets');
    if (packetsEl) {
      packetsEl.textContent = this.formatNumber(stats.total_packets);
    }

    // Bandwidth (Bytes/s to human readable)
    const bpsEl = document.getElementById('h-bps');
    if (bpsEl) {
      bpsEl.textContent = this.formatBytes(stats.bps) + '/s';
    }

    // Unique IPs
    const ipsEl = document.getElementById('h-ips');
    if (ipsEl) {
      ipsEl.textContent = this.formatNumber(stats.unique_ips);
    }

    // Packets per second
    const ppsEl = document.getElementById('h-pps');
    if (ppsEl) {
      ppsEl.textContent = this.formatNumber(stats.pps);
    }
  }

  /**
   * Update top senders list
   */
  updateTopIPs(stats) {
    const listEl = document.getElementById('topips-list');
    if (!listEl) return;

    const topIPs = stats.top_src_ips || [];
    const totalBytes = stats.total_bytes || 1;

    if (topIPs.length === 0) {
      listEl.innerHTML = '<div class="empty-state">Aucune donnée</div>';
      return;
    }

    const maxBytes = topIPs[0]?.[1]?.bytes || 1;

    listEl.innerHTML = topIPs
      .slice(0, 10)
      .map(([ip, data]) => {
        const bytes = data.bytes || 0;
        const percentage = (bytes / maxBytes) * 100;
        const formatted = this.formatBytes(bytes);

        return `
          <div class="ip-row">
            <div class="ip-row-top">
              <span class="ip-addr">${ip}</span>
              <span class="ip-bytes">${formatted}</span>
            </div>
            <div class="ip-bar-track">
              <div class="ip-bar-fill" style="width: ${percentage}%"></div>
            </div>
          </div>
        `;
      })
      .join('');
  }

  /**
   * Update live connections table
   */
  updateConnections(stats) {
    const tbody = document.getElementById('conn-tbody');
    const countEl = document.getElementById('conn-count');
    
    if (!tbody) return;

    const recentConns = stats.recent_connections || [];

    if (recentConns.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Aucune connexion</td></tr>';
      if (countEl) countEl.textContent = '0';
      return;
    }

    if (countEl) countEl.textContent = recentConns.length;

    tbody.innerHTML = recentConns
      .slice(-this.maxConnections)
      .reverse()
      .map((conn, idx) => this.createConnectionRow(conn, idx === 0))
      .join('');
  }

  /**
   * Create table row for connection
   */
  createConnectionRow(conn, isNew = false) {
    const time = this.formatTime(conn.timestamp);
    const proto = conn.protocol || 'OTHER';
    const size = this.formatBytes(conn.size);
    const flags = conn.flags || '—';

    const rowClass = isNew ? 'row-new' : '';
    const protoClass = `proto-${proto.toUpperCase()}`;

    return `
      <tr class="${rowClass}">
        <td class="td-time">${time}</td>
        <td class="td-src">${conn.src}</td>
        <td class="td-dst">${conn.dst}</td>
        <td class="td-proto">
          <span class="td-proto ${protoClass}">${proto}</span>
        </td>
        <td class="td-size">${size}</td>
        <td class="td-flags">${this.formatFlags(flags)}</td>
      </tr>
    `;
  }

  /**
   * Format TCP flags
   */
  formatFlags(flags) {
    if (!flags || flags === '—' || flags === '') return '—';

    return flags
      .split(',')
      .map(flag => flag.trim())
      .filter(flag => flag.length > 0)
      .map(flag => `<span class="flag-${flag}">${flag}</span>`)
      .join(' ');
  }

  /**
   * Handle incoming alerts
   */
  handleAlerts(alerts) {
    if (Array.isArray(alerts)) {
      alertManager.processAlerts(alerts);
    }
  }

  /**
   * Handle WebSocket connection established
   */
  handleConnected() {
    console.log('✅ Connected to backend');
    wsManager.updateStatus('CONNECTED');
  }

  /**
   * Handle WebSocket disconnection
   */
  handleDisconnected() {
    console.log('⚠️  Disconnected from backend');
    wsManager.updateStatus('DISCONNECTED');
  }

  /**
   * Handle WebSocket error
   */
  handleError() {
    console.log('❌ Connection error');
    wsManager.updateStatus('ERROR');
  }

  /**
   * Format bytes for display
   */
  formatBytes(bytes, decimals = 1) {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = Math.abs(bytes || 0);
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return size.toFixed(decimals) + units[unitIndex];
  }

  /**
   * Format large numbers with thousands separators
   */
  formatNumber(num) {
    if (typeof num !== 'number') return '0';
    return num.toLocaleString('fr-FR');
  }

  /**
   * Format time for display
   */
  formatTime(isoString) {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return '—';
    }
  }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new NetWatchApp();
  console.log('✅ NetWatch Dashboard Ready');
  
  // Make available globally for debugging
  window.netwatch = {
    app,
    wsManager,
    chartManager,
    alertManager
  };
});
