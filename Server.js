/**
 * NetWatch — Frontend Node.js server
 *
 * Serves static dashboard from ./public/
 * Proxies /api/* and /ws to the Python backend (default localhost:8000)
 *
 * Usage:
 *   BACKEND_URL=http://localhost:8000 node server.js
 */

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const PORT        = parseInt(process.env.PORT || '3000', 10);
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const app = express();

// ── Static assets ────────────────────────────────────────────────────────────
app.use(express.static(path.join(__dirname, 'public')));

// ── REST API proxy ───────────────────────────────────────────────────────────
app.use(
  '/api',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    on: {
      error: (err, req, res) => {
        console.error('[proxy] API error:', err.message);
        res.status(502).json({ error: 'Backend unreachable', detail: err.message });
      },
    },
  })
);

// ── WebSocket proxy ──────────────────────────────────────────────────────────
const wsProxy = createProxyMiddleware({
  target: BACKEND_URL.replace(/^http/, 'ws'),
  changeOrigin: true,
  ws: true,
  on: {
    error: (err) => console.error('[proxy] WS error:', err.message),
  },
});
app.use('/ws', wsProxy);

// ── SPA fallback ─────────────────────────────────────────────────────────────
app.get('*', (_req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// ── Start ────────────────────────────────────────────────────────────────────
const server = app.listen(PORT, () => {
  console.log(`╔════════════════════════════════════╗`);
  console.log(`║  NetWatch Frontend                 ║`);
  console.log(`║  http://localhost:${PORT}             ║`);
  console.log(`║  Backend → ${BACKEND_URL}    ║`);
  console.log(`╚════════════════════════════════════╝`);
});

// ── Upgrade WS connections ──────────────────────────────────────────────────
server.on('upgrade', wsProxy.upgrade);