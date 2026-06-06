/**
 * alerts.js — Alert Management
 * Handles alert display, history, panel, and filters
 */

class AlertManager {
  constructor() {
    this.alerts = [];
    this.maxAlerts = 100;
    this.seenAlertIds = new Set();
    this.activeFilter = 'ALL';
    this.panelOpen = false;
    this.init();
  }

  /**
   * Initialize alert manager
   */
  init() {
    // Clear button in the small sidebar feed
    const clearBtn = document.getElementById('clear-alerts');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => this.clearAlerts());
    }

    // Clear button inside the panel
    const clearPanelBtn = document.getElementById('clear-alerts-panel');
    if (clearPanelBtn) {
      clearPanelBtn.addEventListener('click', () => this.clearAlerts());
    }

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeFilter = btn.dataset.sev;
        this.renderPanel();
      });
    });

    // Close panel on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.panelOpen) this.closePanel();
    });
  }

  /**
   * Process incoming alerts
   */
  processAlerts(alerts) {
    if (!Array.isArray(alerts)) return;

    alerts.forEach(alert => {
      const alertId = `${alert.type}-${alert.source}-${alert.timestamp}`;

      if (!this.seenAlertIds.has(alertId)) {
        this.seenAlertIds.add(alertId);
        this.addAlert(alert);
      }
    });

    this.updateAlertCount();
  }

  /**
   * Add a new alert to the feed
   */
  addAlert(alert) {
    this.alerts.unshift(alert);

    if (this.alerts.length > this.maxAlerts) {
      this.alerts = this.alerts.slice(0, this.maxAlerts);
    }

    this.renderAlerts();

    // Also refresh panel if open
    if (this.panelOpen) this.renderPanel();
  }

  /**
   * Render alerts in the small sidebar feed (shows last 20)
   */
  renderAlerts() {
    const feed = document.getElementById('alerts-feed');
    if (!feed) return;

    if (this.alerts.length === 0) {
      feed.innerHTML = '<div class="empty-state">Aucune alerte</div>';
      return;
    }

    feed.innerHTML = this.alerts
      .slice(0, 20)
      .map(alert => this.createAlertElement(alert))
      .join('');
  }

  /**
   * Render alerts in the slide-over panel (with active filter applied)
   */
  renderPanel() {
    const feed = document.getElementById('alert-panel-feed');
    if (!feed) return;

    const filtered = this.activeFilter === 'ALL'
      ? this.alerts
      : this.alerts.filter(a => (a.severity || '').toUpperCase() === this.activeFilter);

    if (filtered.length === 0) {
      feed.innerHTML = '<div class="empty-state">Aucune alerte</div>';
      return;
    }

    feed.innerHTML = filtered
      .map(alert => this.createAlertElement(alert))
      .join('');
  }

  /**
   * Create HTML for a single alert card
   */
  createAlertElement(alert) {
    const severity = alert.severity || 'LOW';
    const severityClass = `sev-${severity.toLowerCase()}`;
    const timestamp = this.formatTime(alert.timestamp);

    return `
      <div class="alert-card ${severityClass}">
        <div class="alert-type">${alert.type}</div>
        <div class="alert-desc">${alert.description}</div>
        <div class="alert-meta">
          ${alert.source ? `<strong>${alert.source}</strong> — ` : ''}
          ${alert.details} · ${timestamp}
        </div>
      </div>
    `;
  }

  /**
   * Update alert count badge in header
   */
  updateAlertCount() {
    const counter = document.getElementById('h-alerts');
    const alertBadge = document.getElementById('alert-counter');

    if (!counter || !alertBadge) return;

    const count = this.alerts.length;
    counter.textContent = count > 99 ? '99+' : count;

    if (count > 0) {
      alertBadge.classList.add('has-alerts');
    } else {
      alertBadge.classList.remove('has-alerts');
    }
  }

  /**
   * Clear all alerts
   */
  clearAlerts() {
    this.alerts = [];
    this.seenAlertIds.clear();
    this.renderAlerts();
    this.renderPanel();
    this.updateAlertCount();
  }

  /**
   * Toggle the slide-over panel
   */
  togglePanel() {
    this.panelOpen ? this.closePanel() : this.openPanel();
  }

  /**
   * Open the slide-over panel
   */
  openPanel() {
    this.panelOpen = true;
    document.getElementById('alert-panel')?.classList.add('open');
    document.getElementById('alert-panel-overlay')?.classList.add('open');
    this.renderPanel();
  }

  /**
   * Close the slide-over panel
   */
  closePanel() {
    this.panelOpen = false;
    document.getElementById('alert-panel')?.classList.remove('open');
    document.getElementById('alert-panel-overlay')?.classList.remove('open');
  }

  /**
   * Format timestamp for display
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
      return 'N/A';
    }
  }
}

// Create global instance
const alertManager = new AlertManager();