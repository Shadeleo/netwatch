/**
 * charts.js — Chart Managers
 * Initializes and updates Chart.js visualizations
 */

class ChartManager {
  constructor() {
    this.bwChart = null;
    this.protoChart = null;
    this.bwData = {
      labels: [],
      bps: [],
      pps: []
    };
    this.maxDataPoints = 30;
    this.init();
  }

  /**
   * Initialize all charts
   */
  init() {
    this.initBandwidthChart();
    this.initProtocolChart();
  }

  /**
   * Initialize bandwidth/PPS line chart
   */
  initBandwidthChart() {
    const ctx = document.getElementById('chart-bw');
    if (!ctx) return;

    this.bwChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: this.bwData.labels,
        datasets: [
          {
            label: 'Bytes/s',
            data: this.bwData.bps,
            borderColor: '#00e5ff',
            backgroundColor: 'rgba(0, 229, 255, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 6,
            yAxisID: 'y'
          },
          {
            label: 'Packets/s',
            data: this.bwData.pps,
            borderColor: '#39ff14',
            backgroundColor: 'rgba(57, 255, 20, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 6,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          x: {
            display: false,
            grid: {
              display: false
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            grid: {
              color: 'rgba(14, 36, 72, 0.3)',
              drawBorder: false
            },
            ticks: {
              color: '#5a8abf',
              font: { size: 10 },
              callback: (value) => this.formatBytes(value) + '/s'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            grid: {
              display: false,
              drawBorder: false
            },
            ticks: {
              color: '#5a8abf',
              font: { size: 10 }
            }
          }
        }
      }
    });
  }

  /**
   * Initialize protocol distribution donut chart
   */
  initProtocolChart() {
    const ctx = document.getElementById('chart-proto');
    if (!ctx) return;

    this.protoChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: [],
        datasets: [
          {
            data: [],
            backgroundColor: [
              '#00e5ff',
              '#39ff14',
              '#ffd600',
              '#ff6d00',
              '#d500f9',
              '#ff1744'
            ],
            borderColor: '#071428',
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            titleFont: { family: "'IBM Plex Mono', monospace", size: 11 },
            bodyFont: { family: "'IBM Plex Mono', monospace", size: 10 },
            backgroundColor: 'rgba(7, 20, 40, 0.95)',
            titleColor: '#c4dff7',
            bodyColor: '#5a8abf',
            borderColor: '#0e2448',
            borderWidth: 1,
            callbacks: {
              label: (context) => `${context.label}: ${context.parsed} paquets`
            }
          }
        }
      }
    });
  }

  /**
   * Update bandwidth chart with new data
   */
  updateBandwidth(stats) {
    if (!this.bwChart) return;

    const timestamp = new Date().toLocaleTimeString('fr-FR');
    const bps = stats.bps || 0;
    const pps = stats.pps || 0;

    this.bwData.labels.push(timestamp);
    this.bwData.bps.push(bps);
    this.bwData.pps.push(pps);

    // Keep only last N datapoints
    if (this.bwData.labels.length > this.maxDataPoints) {
      this.bwData.labels.shift();
      this.bwData.bps.shift();
      this.bwData.pps.shift();
    }

    this.bwChart.data.labels = this.bwData.labels;
    this.bwChart.data.datasets[0].data = this.bwData.bps;
    this.bwChart.data.datasets[1].data = this.bwData.pps;
    this.bwChart.update('none'); // No animation for smooth updates
  }

  /**
   * Update protocol chart with protocol distribution
   */
  updateProtocols(stats) {
    if (!this.protoChart) return;

    const protocols = stats.protocols || {};
    
    // Sort by count
    const sorted = Object.entries(protocols)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6); // Top 6 protocols

    const labels = sorted.map(([name]) => name);
    const data = sorted.map(([_, count]) => count);

    this.protoChart.data.labels = labels;
    this.protoChart.data.datasets[0].data = data;
    this.protoChart.update('none');

    // Update legend
    this.updateProtocolLegend(labels, data);
  }

  /**
   * Update protocol legend HTML
   */
  updateProtocolLegend(labels, data) {
    const legend = document.getElementById('proto-legend');
    if (!legend) return;

    const colors = [
      '#00e5ff', '#39ff14', '#ffd600',
      '#ff6d00', '#d500f9', '#ff1744'
    ];

    legend.innerHTML = labels
      .map((label, i) => `
        <div class="proto-row">
          <div class="proto-row-dot" style="background: ${colors[i]}"></div>
          <span class="proto-row-name">${label}</span>
          <span class="proto-row-count">${data[i]}</span>
        </div>
      `)
      .join('');
  }

  /**
   * Format bytes for display
   */
  formatBytes(bytes, decimals = 1) {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = Math.abs(bytes);
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return size.toFixed(decimals) + units[unitIndex];
  }
}

// Create global instance
const chartManager = new ChartManager();
