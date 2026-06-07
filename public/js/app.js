/**
 * app.js — Main Application Logic
 * Coordinates WebSocket, charts, and alerts
 */

class NetWatchApp {
  constructor() {
    this.maxConnections = 50;
    this.connections    = [];
    this.stats          = null;
    this.deviceNames    = {};     // ip → device name (local devices)
    this._resolveCache  = {};     // ip → DNS/org data (external IPs)
    this.localIP = null;
    this.detectLocalIP();
    this.init();
  }

  /**
   * Initialize application
   */
  init() {
    console.log('🚀 NetWatch Dashboard Initializing...');

    wsManager.on('stats',        (stats)  => this.handleStatsUpdate(stats));
    wsManager.on('alerts',       (alerts) => this.handleAlerts(alerts));
    wsManager.on('connected',    ()       => this.handleConnected());
    wsManager.on('disconnected', ()       => this.handleDisconnected());
    wsManager.on('error',        ()       => this.handleError());

    this.setupUI();
    this.loadDeviceNames();
  }

  /**
   * Setup UI event listeners
   */
  setupUI() {
    const tableWrap = document.querySelector('.table-wrap');
    if (tableWrap) {
      tableWrap.addEventListener('scroll', (e) => {
        const target = e.target;
        const isAtBottom = Math.abs(
          target.scrollHeight - target.scrollTop - target.clientHeight
        ) < 5;
      });
    }
  }

  /**
   * Load device names from /api/devices and refresh every 5 minutes
   */
  async loadDeviceNames() {
    try {
      const res  = await fetch('/api/devices');
      const data = await res.json();
      (data.devices || []).forEach(d => {
        if (d.ip && d.name) this.deviceNames[d.ip] = d.name;
      });
    } catch (_) {}

    setTimeout(() => this.loadDeviceNames(), 5 * 60 * 1000);
  }

  /**
   * Handle statistics update
   */
  handleStatsUpdate(stats) {
    this.stats = stats;

    this.updateHeaderStats(stats);
    chartManager.updateBandwidth(stats);
    chartManager.updateProtocols(stats);
    this.updateTopIPs(stats);
    this.updateConnections(stats);
  }

  /**
   * Update header statistics display
   */
  updateHeaderStats(stats) {
    const packetsEl = document.getElementById('h-packets');
    if (packetsEl) packetsEl.textContent = this.formatNumber(stats.total_packets);

    const bpsEl = document.getElementById('h-bps');
    if (bpsEl) bpsEl.textContent = this.formatBytes(stats.bps) + '/s';

    const ipsEl = document.getElementById('h-ips');
    if (ipsEl) ipsEl.textContent = this.formatNumber(stats.unique_ips);

    const ppsEl = document.getElementById('h-pps');
    if (ppsEl) ppsEl.textContent = this.formatNumber(stats.pps);
  }

  /**
   * Update top senders list
   */
  updateTopIPs(stats) {
    const listEl = document.getElementById('topips-list');
    if (!listEl) return;

    const topIPs = stats.top_src_ips || [];
    if (topIPs.length === 0) {
      listEl.innerHTML = '<div class="empty-state">Aucune donnée</div>';
      return;
    }

    const maxBytes = topIPs[0]?.[1]?.bytes || 1;

    listEl.innerHTML = topIPs
      .slice(0, 10)
      .map(([ip, data]) => {
        const bytes      = data.bytes || 0;
        const percentage = (bytes / maxBytes) * 100;
        const formatted  = this.formatBytes(bytes);
        
        let label = '';
        if (ip === this.localIP) {
          label = ' · Ordinateur actuel';
        } else if (this.deviceNames[ip]) {
          label = ` · ${this.deviceNames[ip]}`;
        }

        return `
          <div class="ip-row">
            <div class="ip-row-top">
              <span class="ip-addr">${ip}<span class="ip-device">${label}</span></span>
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
    const tbody   = document.getElementById('conn-tbody');
    const countEl = document.getElementById('conn-count');
    if (!tbody) return;

    const recentConns = stats.recent_connections || [];

    if (recentConns.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty-state">Aucune connexion</td></tr>';
      if (countEl) countEl.textContent = '0';
      return;
    }

    if (countEl) countEl.textContent = recentConns.length;

    tbody.innerHTML = recentConns
      .slice(-this.maxConnections)
      .reverse()
      .map((conn, idx) => this.createConnectionRow(conn, idx === 0))
      .join('');

    // Injecte le cache immédiatement après le rendu
    this._injectCachedResolutions();

    // Fetch les IPs manquantes
    this.resolveVisibleIPs();
  }

  // Ajoute cette méthode dans la classe


  /**
   * Create table row for connection
   */
  createConnectionRow(conn, isNew = false) {
    const time     = this.formatTime(conn.timestamp);
    const proto    = conn.protocol || 'OTHER';
    const size     = this.formatBytes(conn.size);
    const flags    = conn.flags || '—';
    const srcPort  = conn.src_port || '—';
    const dstPort  = conn.dst_port || '—';
    const service  = conn.service  || '';

    const rowClass   = isNew ? 'row-new' : '';
    const protoClass = `proto-${proto.toUpperCase()}`;

    const dstPortHtml = service
      ? `<span class="port-known" title="${service}">${dstPort}</span>`
      : dstPort;

    const serviceHtml = service
      ? `<span class="service-badge">${service}</span>`
      : '—';

    const isPrivate  = (ip) => /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(ip);
    const deviceName = (ip) => this.deviceNames[ip] || null;

    const srcHtml = `
      <span class="ip-cell">
        <span class="ip-addr">${conn.src}</span>
        ${deviceName(conn.src)
          ? `<span class="ip-device">· ${deviceName(conn.src)}</span>`
          : (!isPrivate(conn.src) ? `<span class="ip-hostname" data-ip="${conn.src}">…</span>` : '')
        }
      </span>`;

    const dstHtml = `
      <span class="ip-cell">
        <span class="ip-addr">${conn.dst}</span>
        ${deviceName(conn.dst)
          ? `<span class="ip-device">· ${deviceName(conn.dst)}</span>`
          : (!isPrivate(conn.dst)
              ? `<span class="ip-hostname" data-ip="${conn.dst}">…</span>
                 <span class="ip-org" data-ip="${conn.dst}"></span>`
              : '')
        }
      </span>`;

    return `
      <tr class="${rowClass}">
        <td class="td-time">${time}</td>
        <td class="td-src">${srcHtml}</td>
        <td class="td-port">${srcPort}</td>
        <td class="td-dst">${dstHtml}</td>
        <td class="td-port">${dstPortHtml}</td>
        <td>${serviceHtml}</td>
        <td><span class="td-proto ${protoClass}">${proto}</span></td>
        <td class="td-flags">${this.formatFlags(flags)}</td>
        <td class="td-size">${size}</td>
      </tr>`;
  }

  /**
   * Inject cached DNS/device data immediately after table redraw
   */
  _injectCachedResolutions() {
    // Noms de devices locaux
    Object.entries(this.deviceNames).forEach(([ip, name]) => {
      document.querySelectorAll('.ip-addr').forEach(el => {
        if (el.textContent.trim() === ip) {
          const cell = el.closest('.ip-cell');
          if (cell && !cell.querySelector('.ip-device')) {
            const span       = document.createElement('span');
            span.className   = 'ip-device';
            span.textContent = `· ${name}`;
            cell.appendChild(span);
          }
        }
      });
    });

    // DNS/org cache pour IPs externes
    Object.entries(this._resolveCache).forEach(([ip, data]) => {
      this._applyResolveData(ip, data);
    });
  }

  /**
   * Resolve external IPs asynchronously
   */
  async resolveVisibleIPs() {
    const pending = document.querySelectorAll('[data-ip]');
    const toFetch = new Set();

    pending.forEach(el => {
      const ip = el.dataset.ip;
      if (this._resolveCache[ip]) {
        this._applyResolveData(ip, this._resolveCache[ip]);
      } else {
        toFetch.add(ip);
      }
    });

    for (const ip of toFetch) {
      try {
        const res  = await fetch(`/api/resolve?ip=${ip}`);
        const data = await res.json();
        this._resolveCache[ip] = data;
        this._applyResolveData(ip, data);
      } catch (_) {}
    }
  }

  async detectLocalIP() {
    try {
      const res  = await fetch('/api/local-ip');
      const data = await res.json();
      this.localIP = data.ip;
    } catch (_) {}
  }

  /**
   * Apply resolved DNS/org data to DOM spans
   */
  _applyResolveData(ip, data) {
    document.querySelectorAll(`.ip-hostname[data-ip="${ip}"]`).forEach(el => {
      el.textContent = data.hostname || '';
    });

    document.querySelectorAll(`.ip-org[data-ip="${ip}"]`).forEach(el => {
      const country = data.country_code || '';
      const org     = data.org ? data.org.replace(/^AS\d+\s*/, '') : '';
      el.innerHTML  = country || org
        ? `<span class="ip-country">${country}</span>${org ? `<span class="ip-orgname">${org}</span>` : ''}`
        : '';
    });
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

  handleAlerts(alerts) {
    if (Array.isArray(alerts)) alertManager.processAlerts(alerts);
  }

  handleConnected() {
    console.log('✅ Connected to backend');
    wsManager.updateStatus('CONNECTED');
  }

  handleDisconnected() {
    console.log('⚠️  Disconnected from backend');
    wsManager.updateStatus('DISCONNECTED');
  }

  handleError() {
    console.log('❌ Connection error');
    wsManager.updateStatus('ERROR');
  }

  formatBytes(bytes, decimals = 1) {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size      = Math.abs(bytes || 0);
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return size.toFixed(decimals) + units[unitIndex];
  }

  formatNumber(num) {
    if (typeof num !== 'number') return '0';
    return num.toLocaleString('fr-FR');
  }

  formatTime(isoString) {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('fr-FR', {
        hour:   '2-digit',
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

  window.netwatch = { app, wsManager, chartManager, alertManager };
});