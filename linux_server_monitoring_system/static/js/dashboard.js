/**
 * Linux Server Monitoring System - Dashboard Application
 * Production Observability Client Script
 */

document.addEventListener('DOMContentLoaded', () => {
  // Only run on the dashboard page; this script is loaded site-wide via
  // base.html, and its 403 redirect loop would otherwise hijack the login page.
  if (!document.getElementById('dashboard-app')) return;

  // Global Dashboard State
  const state = {
    servers: [],
    stats: null,
    alerts: [],
    currentServerFilter: 'ALL',
    searchQuery: '',
    currentAlertFilter: 'ACTIVE',
    selectedServerId: null,
    selectedRange: '24h',
    autoRefreshInterval: 30000,
    countdownSeconds: 30,
    countdownTimer: null,
    isFetching: false,
    theme: localStorage.getItem('dash_theme') || 'dark',
    charts: {
      cpu: null,
      memory: null,
      disk: null,
      network: null,
    },
  };

  // DOM Elements Cache
  const el = {
    app: document.getElementById('dashboard-app'),
    statTotal: document.getElementById('stat-total-servers'),
    statOnline: document.getElementById('stat-online-servers'),
    statOffline: document.getElementById('stat-offline-servers'),
    statAlerts: document.getElementById('stat-active-alerts'),
    statOnlineSub: document.getElementById('stat-online-subtext'),
    statOfflineSub: document.getElementById('stat-offline-subtext'),
    statAlertsSub: document.getElementById('stat-alerts-subtext'),
    statAvgCpu: document.getElementById('stat-avg-cpu'),
    statAvgCpuDelta: document.getElementById('stat-avg-cpu-delta'),
    statAvgMemory: document.getElementById('stat-avg-memory'),
    statAvgMemoryDelta: document.getElementById('stat-avg-memory-delta'),
    sidebarFleetStatus: document.getElementById('sidebar-fleet-status'),
    sidebarServerCount: document.getElementById('sidebar-server-count'),
    lastUpdatedTime: document.getElementById('last-updated-time'),
    countdownBadge: document.getElementById('refresh-countdown-badge'),
    countdownSec: document.getElementById('refresh-countdown-sec'),
    liveRefreshBar: document.getElementById('live-refresh-bar'),
    liveRefreshDot: document.getElementById('live-refresh-dot'),
    liveRefreshTime: document.getElementById('live-refresh-time'),
    liveRefreshMetrics: document.getElementById('live-refresh-metrics'),
    liveRefreshBadge: document.getElementById('live-refresh-status-badge'),
    refreshBtn: document.getElementById('btn-refresh-all'),
    refreshIcon: document.getElementById('refresh-icon'),
    autoRefreshLabel: document.getElementById('auto-refresh-label'),
    themeToggleBtn: document.getElementById('btn-theme-toggle'),
    themeToggleIcon: document.getElementById('theme-toggle-icon'),
    sidebarToggleBtn: document.getElementById('sidebar-toggle'),
    sidebar: document.getElementById('dash-sidebar'),
    serverSearchInput: document.getElementById('server-search-input'),
    serversTableBody: document.getElementById('servers-table-body'),
    serversEmptyState: document.getElementById('servers-empty-state'),
    btnClearSearch: document.getElementById('btn-clear-search'),
    chartServerSelect: document.getElementById('chart-server-select'),
    alertsListContainer: document.getElementById('alerts-list-container'),
    alertsEmptyState: document.getElementById('alerts-empty-state'),
    activityTableBody: document.getElementById('activity-table-body'),
    errorBanner: document.getElementById('dash-error-banner'),
    errorMessage: document.getElementById('dash-error-message'),
    btnErrorRetry: document.getElementById('btn-error-retry'),
    // Modal elements
    modalEl: document.getElementById('serverDetailModal'),
    modalName: document.getElementById('modal-server-name'),
    modalHostname: document.getElementById('modal-server-hostname'),
    modalStatus: document.getElementById('modal-server-status'),
    modalOs: document.getElementById('modal-server-os'),
    modalSsh: document.getElementById('modal-server-ssh'),
    modalLastCheck: document.getElementById('modal-server-lastcheck'),
    modalCpuPct: document.getElementById('modal-cpu-pct'),
    modalCpuBar: document.getElementById('modal-cpu-bar'),
    modalCpuLoad: document.getElementById('modal-cpu-load'),
    modalMemPct: document.getElementById('modal-mem-pct'),
    modalMemBar: document.getElementById('modal-mem-bar'),
    modalMemGb: document.getElementById('modal-mem-gb'),
    modalDiskPct: document.getElementById('modal-disk-pct'),
    modalDiskBar: document.getElementById('modal-disk-bar'),
    modalDiskGb: document.getElementById('modal-disk-gb'),
    modalNetIface: document.getElementById('modal-net-iface'),
    modalNetRx: document.getElementById('modal-net-rx'),
    modalNetTx: document.getElementById('modal-net-tx'),
    modalNetTotal: document.getElementById('modal-net-total'),
    modalErrorBox: document.getElementById('modal-error-box'),
    modalErrorText: document.getElementById('modal-error-text'),
    modalSshOutput: document.getElementById('modal-ssh-output'),
    btnModalTestSsh: document.getElementById('btn-modal-test-ssh'),
    btnModalCollect: document.getElementById('btn-modal-collect'),
    // Chart current value badges
    badgeCpu: document.getElementById('current-cpu-badge'),
    badgeMem: document.getElementById('current-mem-badge'),
    badgeDisk: document.getElementById('current-disk-badge'),
    badgeNet: document.getElementById('current-net-badge'),
    deltaCpuBadge: document.getElementById('delta-cpu-badge'),
    deltaMemBadge: document.getElementById('delta-mem-badge'),
    deltaDiskBadge: document.getElementById('delta-disk-badge'),
    deltaNetBadge: document.getElementById('delta-net-badge'),
  };

  // Helper: Get CSRF Token
  function getCsrfToken() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, 10) === 'csrftoken=') {
          cookieValue = decodeURIComponent(cookie.substring(10));
          break;
        }
      }
    }
    return cookieValue || '';
  }

  // Helper: Toast Notifications
  function showToast(message, type = 'info') {
    const container = document.getElementById('dashboard-toast-container');
    if (!container) return;

    const toastId = 'toast-' + Date.now();
    const bgClass =
      type === 'success' ? 'bg-success text-white' :
      type === 'danger' ? 'bg-danger text-white' :
      type === 'warning' ? 'bg-warning text-dark' :
      'bg-primary text-white';

    const icon =
      type === 'success' ? 'bi-check-circle-fill' :
      type === 'danger' ? 'bi-exclamation-triangle-fill' :
      type === 'warning' ? 'bi-exclamation-circle-fill' :
      'bi-info-circle-fill';

    const toastHtml = `
      <div id="${toastId}" class="toast align-items-center ${bgClass} border-0 show shadow-lg" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
          <div class="toast-body d-flex align-items-center gap-2">
            <i class="bi ${icon} fs-6"></i>
            <span>${message}</span>
          </div>
          <button type="button" class="btn-close ${type === 'warning' ? '' : 'btn-close-white'} me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>
    `;
    container.insertAdjacentHTML('beforeend', toastHtml);

    setTimeout(() => {
      const item = document.getElementById(toastId);
      if (item) {
        item.classList.remove('show');
        setTimeout(() => item.remove(), 400);
      }
    }, 4500);
  }

  // Format relative time
  function formatRelativeTime(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Never';

    const now = new Date();
    const diffSeconds = Math.floor((now - date) / 1000);

    if (diffSeconds < 10) return 'Just now';
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }

  function getOsBadge(os) {
    const osUpper = (os || '').toUpperCase();
    if (osUpper.includes('UBUNTU')) return '<i class="bi bi-ubuntu text-danger me-1"></i> Ubuntu';
    if (osUpper.includes('DEBIAN')) return '<i class="bi bi-box text-primary me-1"></i> Debian';
    if (osUpper.includes('CENTOS') || osUpper.includes('ROCKY')) return '<i class="bi bi-cpu text-secondary me-1"></i> CentOS/Rocky';
    return '<i class="bi bi-terminal text-info me-1"></i> Linux';
  }

  function getMeterColorClass(pct) {
    if (pct >= 90) return 'meter-fill-danger';
    if (pct >= 70) return 'meter-fill-warning';
    return 'meter-fill-normal';
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Helper: 30s Delta Variation Formatting
  function renderDeltaPill(delta, unit = '%', invertSemantic = false) {
    if (typeof delta !== 'number' || isNaN(delta)) {
      return `<span class="badge-delta badge-delta-neutral font-monospace">0.00${unit}</span>`;
    }
    const abs = Math.abs(delta).toFixed(2);
    if (delta > 0) {
      const cls = invertSemantic ? 'badge-delta-down' : 'badge-delta-up';
      return `<span class="badge-delta ${cls} font-monospace" title="30s variation: +${abs}${unit}"><i class="bi bi-arrow-up-short"></i>+${abs}${unit}</span>`;
    } else if (delta < 0) {
      const cls = invertSemantic ? 'badge-delta-up' : 'badge-delta-down';
      return `<span class="badge-delta ${cls} font-monospace" title="30s variation: -${abs}${unit}"><i class="bi bi-arrow-down-short"></i>-${abs}${unit}</span>`;
    } else {
      return `<span class="badge-delta badge-delta-neutral font-monospace" title="30s variation: 0.00${unit}"><i class="bi bi-dash"></i>0.00${unit}</span>`;
    }
  }

  function updateDeltaBadgeEl(badgeEl, delta, unit = '%', invertSemantic = false) {
    if (!badgeEl) return;
    if (typeof delta !== 'number' || isNaN(delta)) {
      badgeEl.className = 'badge-delta badge-delta-neutral font-monospace';
      badgeEl.innerHTML = `<i class="bi bi-dash"></i>0.00${unit}`;
      badgeEl.title = `30s variation: 0.00${unit}`;
      return;
    }
    const abs = Math.abs(delta).toFixed(2);
    if (delta > 0) {
      const cls = invertSemantic ? 'badge-delta-down' : 'badge-delta-up';
      badgeEl.className = `badge-delta ${cls} font-monospace`;
      badgeEl.innerHTML = `<i class="bi bi-arrow-up-short"></i>+${abs}${unit}`;
      badgeEl.title = `30s variation: +${abs}${unit}`;
    } else if (delta < 0) {
      const cls = invertSemantic ? 'badge-delta-up' : 'badge-delta-down';
      badgeEl.className = `badge-delta ${cls} font-monospace`;
      badgeEl.innerHTML = `<i class="bi bi-arrow-down-short"></i>-${abs}${unit}`;
      badgeEl.title = `30s variation: -${abs}${unit}`;
    } else {
      badgeEl.className = 'badge-delta badge-delta-neutral font-monospace';
      badgeEl.innerHTML = `<i class="bi bi-dash"></i>0.00${unit}`;
      badgeEl.title = `30s variation: 0.00${unit}`;
    }
  }

  // ================= API CALLS =================

  async function apiFetch(url, options = {}) {
    const res = await fetch(url, options);
    if (res.status === 401 || res.status === 403) {
      window.location.href = `/accounts/login/?next=${encodeURIComponent(window.location.pathname)}`;
      throw new Error('Authentication required');
    }
    return res;
  }

  async function fetchDashboardStats() {
    const res = await apiFetch('/api/dashboard/stats/', {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) throw new Error(`Stats HTTP ${res.status}`);
    return await res.json();
  }

  async function fetchServers() {
    const res = await apiFetch('/api/servers/', {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) throw new Error(`Servers HTTP ${res.status}`);
    return await res.json();
  }

  async function fetchAlerts() {
    const res = await apiFetch('/api/alerts/', {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) throw new Error(`Alerts HTTP ${res.status}`);
    return await res.json();
  }

  async function fetchServerMetrics(serverId, range = '24h') {
    const res = await apiFetch(`/api/servers/${serverId}/metrics/?range=${range}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) throw new Error(`Metrics HTTP ${res.status}`);
    return await res.json();
  }

  async function testServerSSH(serverId) {
    const res = await apiFetch(`/api/servers/${serverId}/test_connection/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
    });
    return await res.json();
  }

  async function collectServerMetricsNow(serverId) {
    const res = await apiFetch(`/api/servers/${serverId}/collect_metrics/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
    });
    return await res.json();
  }

  async function resolveAlert(alertId) {
    const res = await apiFetch(`/api/alerts/${alertId}/resolve/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
    });
    if (!res.ok) throw new Error(`Resolve HTTP ${res.status}`);
    return await res.json();
  }

  // ================= RENDER FUNCTIONS =================

  function renderStats(stats) {
    if (!stats) return;
    state.stats = stats;

    if (el.statTotal) el.statTotal.textContent = stats.total_servers;
    if (el.statOnline) el.statOnline.textContent = stats.online_servers;
    if (el.statOffline) el.statOffline.textContent = stats.offline_servers;
    if (el.statAlerts) el.statAlerts.textContent = stats.active_alerts;

    if (el.statOnlineSub) {
      el.statOnlineSub.innerHTML = `
        <span class="badge ${stats.offline_servers > 0 ? 'bg-warning text-dark' : 'bg-success'}">${stats.healthy_percent}%</span>
        <span>${stats.offline_servers > 0 ? 'Degraded fleet' : 'Operating normally'}</span>
      `;
    }

    if (el.statOfflineSub) {
      el.statOfflineSub.innerHTML = `
        <span class="badge ${stats.offline_servers > 0 ? 'bg-danger' : 'bg-secondary'}">${stats.offline_servers} Issues</span>
        <span>${stats.offline_servers > 0 ? 'Requires attention' : 'All responsive'}</span>
      `;
    }

    if (el.statAlertsSub) {
      el.statAlertsSub.innerHTML = `
        <span class="badge ${stats.critical_alerts > 0 ? 'bg-danger' : 'bg-secondary'}">${stats.critical_alerts} Critical</span>
        <span>${stats.active_alerts > 0 ? 'Active incidents' : 'All clear'}</span>
      `;
    }

    if (el.statAvgCpu) {
      el.statAvgCpu.textContent = `${Number(stats.avg_cpu || 0).toFixed(1)}%`;
    }
    if (el.statAvgCpuDelta) {
      updateDeltaBadgeEl(el.statAvgCpuDelta, stats.avg_cpu_delta || 0, '%');
    }

    if (el.statAvgMemory) {
      el.statAvgMemory.textContent = `${Number(stats.avg_memory || 0).toFixed(1)}%`;
    }
    if (el.statAvgMemoryDelta) {
      updateDeltaBadgeEl(el.statAvgMemoryDelta, stats.avg_memory_delta || 0, '%');
    }

    if (el.sidebarFleetStatus) {
      el.sidebarFleetStatus.textContent = stats.offline_servers > 0
        ? `${stats.offline_servers} Server Offline`
        : 'All Systems Healthy';
    }

    if (el.sidebarServerCount) {
      el.sidebarServerCount.textContent = `Monitoring ${stats.total_servers} ${stats.total_servers === 1 ? 'Server' : 'Servers'}`;
    }

    if (el.lastUpdatedTime) {
      const now = new Date();
      el.lastUpdatedTime.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
  }

  function renderLiveRefreshBanner(stats, servers) {
    if (!el.liveRefreshBar) return;

    if (el.liveRefreshTime) {
      const now = new Date();
      el.liveRefreshTime.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    if (el.liveRefreshMetrics) {
      if (servers && servers.length > 0) {
        const s = servers[0];
        const m = s.latest_metrics;
        const cpuPill = m && m.cpu ? renderDeltaPill(m.cpu.delta, '%') : '';
        const memPill = m && m.memory ? renderDeltaPill(m.memory.delta, '%') : '';
        const diskPill = m && m.disk ? renderDeltaPill(m.disk.delta, '%') : '';
        const rxPill = m && m.network ? renderDeltaPill(m.network.rx_delta_kbps, ' KB/s') : '';

        const cpuVal = m && m.cpu ? `${m.cpu.usage_percent}%` : '0.0%';
        const memVal = m && m.memory ? `${m.memory.usage_percent}%` : '0.0%';
        const diskVal = m && m.disk ? `${m.disk.usage_percent}%` : '0.0%';
        const rxVal = m && m.network ? `${m.network.receive_rate_kbps} KB/s` : '0.0 KB/s';

        el.liveRefreshMetrics.innerHTML = `
          <span class="badge badge-soft-info"><i class="bi bi-server me-1"></i>${escapeHtml(s.server_name)}</span>
          <span class="badge bg-dark border border-secondary text-light font-monospace">CPU: ${cpuVal} ${cpuPill}</span>
          <span class="badge bg-dark border border-secondary text-light font-monospace">RAM: ${memVal} ${memPill}</span>
          <span class="badge bg-dark border border-secondary text-light font-monospace">Disk: ${diskVal} ${diskPill}</span>
          <span class="badge bg-dark border border-secondary text-light font-monospace">Net RX: ${rxVal} ${rxPill}</span>
        `;
      } else {
        el.liveRefreshMetrics.innerHTML = '<span class="text-muted font-monospace">Waiting for active telemetry...</span>';
      }
    }

    // Trigger visual highlight animation
    el.liveRefreshBar.classList.remove('poll-flash');
    void el.liveRefreshBar.offsetWidth; // Trigger DOM reflow
    el.liveRefreshBar.classList.add('poll-flash');
  }

  function renderServersTable() {
    if (!el.serversTableBody) return;

    let filtered = state.servers;

    // Filter by status
    if (state.currentServerFilter !== 'ALL') {
      filtered = filtered.filter(s => s.status === state.currentServerFilter);
    }

    // Filter by search
    if (state.searchQuery.trim() !== '') {
      const q = state.searchQuery.toLowerCase();
      filtered = filtered.filter(s =>
        (s.server_name && s.server_name.toLowerCase().includes(q)) ||
        (s.hostname && s.hostname.toLowerCase().includes(q))
      );
    }

    if (filtered.length === 0) {
      el.serversTableBody.innerHTML = '';
      if (el.serversEmptyState) el.serversEmptyState.classList.remove('d-none');
      return;
    }

    if (el.serversEmptyState) el.serversEmptyState.classList.add('d-none');

    const rowsHtml = filtered.map(server => {
      const m = server.latest_metrics;
      const statusBadge =
        server.status === 'UP' ? '<span class="badge badge-soft-success"><span class="status-dot online me-1"></span> ONLINE</span>' :
        server.status === 'DOWN' ? '<span class="badge badge-soft-danger"><span class="status-dot offline me-1"></span> OFFLINE</span>' :
        '<span class="badge badge-soft-warning"><span class="status-dot unknown me-1"></span> UNKNOWN</span>';

      const cpuUsage = m && m.cpu ? m.cpu.usage_percent : 0;
      const cpuLoad = m && m.cpu ? `Load: ${m.cpu.load_1m}, ${m.cpu.load_5m}` : 'Load: N/A';
      const cpuDeltaPill = renderDeltaPill(m && m.cpu ? m.cpu.delta : 0, '%');

      const memUsage = m && m.memory ? m.memory.usage_percent : 0;
      const memText = m && m.memory ? `${m.memory.used_gb} / ${m.memory.total_gb} GB` : 'N/A';
      const memDeltaPill = renderDeltaPill(m && m.memory ? m.memory.delta : 0, '%');

      const diskUsage = m && m.disk ? m.disk.usage_percent : 0;
      const diskText = m && m.disk ? `${m.disk.used_gb} / ${m.disk.total_gb} GB` : 'N/A';
      const diskDeltaPill = renderDeltaPill(m && m.disk ? m.disk.delta : 0, '%');

      const netRx = m && m.network ? `${m.network.receive_rate_kbps} KB/s` : '0 KB/s';
      const netTx = m && m.network ? `${m.network.transmit_rate_kbps} KB/s` : '0 KB/s';
      const rxDeltaPill = renderDeltaPill(m && m.network ? m.network.rx_delta_kbps : 0, ' KB/s');
      const txDeltaPill = renderDeltaPill(m && m.network ? m.network.tx_delta_kbps : 0, ' KB/s');

      const relativeCheck = formatRelativeTime(server.last_check_at);

      const alertBadge = server.active_alerts_count > 0
        ? `<span class="badge bg-warning text-dark"><i class="bi bi-bell-fill me-1"></i>${server.active_alerts_count}</span>`
        : `<span class="badge badge-soft-success"><i class="bi bi-shield-check me-1"></i>Clean</span>`;

      return `
        <tr data-server-id="${server.id}">
          <td>
            <div class="server-title">
              <span>${escapeHtml(server.server_name)}</span>
            </div>
            <div class="hostname-sub">
              ${getOsBadge(server.operating_system)} • ${escapeHtml(server.hostname)}
            </div>
          </td>
          <td>${statusBadge}</td>
          <td>
            <div class="metric-meter" title="${cpuLoad}">
              <div class="metric-meter-label">
                <span>CPU</span>
                <div class="d-flex align-items-center gap-1">
                  <span>${cpuUsage}%</span>
                  ${cpuDeltaPill}
                </div>
              </div>
              <div class="meter-track">
                <div class="meter-fill ${getMeterColorClass(cpuUsage)}" style="width: ${Math.min(100, Math.max(0, cpuUsage))}%;"></div>
              </div>
            </div>
          </td>
          <td>
            <div class="metric-meter" title="${memText}">
              <div class="metric-meter-label">
                <span>RAM</span>
                <div class="d-flex align-items-center gap-1">
                  <span>${memUsage}%</span>
                  ${memDeltaPill}
                </div>
              </div>
              <div class="meter-track">
                <div class="meter-fill ${getMeterColorClass(memUsage)}" style="width: ${Math.min(100, Math.max(0, memUsage))}%;"></div>
              </div>
            </div>
          </td>
          <td>
            <div class="metric-meter" title="${diskText}">
              <div class="metric-meter-label">
                <span>Disk</span>
                <div class="d-flex align-items-center gap-1">
                  <span>${diskUsage}%</span>
                  ${diskDeltaPill}
                </div>
              </div>
              <div class="meter-track">
                <div class="meter-fill ${getMeterColorClass(diskUsage)}" style="width: ${Math.min(100, Math.max(0, diskUsage))}%;"></div>
              </div>
            </div>
          </td>
          <td>
            <div style="font-size: 0.78rem;">
              <div class="d-flex align-items-center gap-1">
                <span class="text-info"><i class="bi bi-arrow-down-short"></i>${netRx}</span>
                ${rxDeltaPill}
              </div>
              <div class="d-flex align-items-center gap-1 mt-1">
                <span class="text-primary"><i class="bi bi-arrow-up-short"></i>${netTx}</span>
                ${txDeltaPill}
              </div>
            </div>
          </td>
          <td>
            <span class="small font-monospace" title="${server.last_check_at || ''}">${relativeCheck}</span>
          </td>
          <td>${alertBadge}</td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-primary btn-server-details" data-id="${server.id}" title="View Telemetry">
                <i class="bi bi-eye-fill"></i>
              </button>
              <button class="btn btn-outline-secondary btn-server-test" data-id="${server.id}" title="Quick Test SSH">
                <i class="bi bi-plug-fill"></i>
              </button>
              <button class="btn btn-outline-success btn-server-collect" data-id="${server.id}" title="Collect Metrics Now">
                <i class="bi bi-arrow-repeat"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    el.serversTableBody.innerHTML = rowsHtml;

    // Attach row button events
    el.serversTableBody.querySelectorAll('.btn-server-details').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt(btn.getAttribute('data-id'), 10);
        openServerDetailModal(id);
      });
    });

    el.serversTableBody.querySelectorAll('.btn-server-test').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.getAttribute('data-id'), 10);
        const origHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';

        try {
          const res = await testServerSSH(id);
          if (res.success) {
            showToast(`SSH Test Success: Connected to ${res.hostname || 'server'}`, 'success');
          } else {
            showToast(`SSH Test Failed: ${res.message}`, 'danger');
          }
          await refreshAll(true);
        } catch (err) {
          showToast(`SSH error: ${err.message}`, 'danger');
        } finally {
          btn.disabled = false;
          btn.innerHTML = origHtml;
        }
      });
    });

    el.serversTableBody.querySelectorAll('.btn-server-collect').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.getAttribute('data-id'), 10);
        const origHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';

        try {
          const res = await collectServerMetricsNow(id);
          if (res.success) {
            showToast('Live metrics collected successfully!', 'success');
          } else {
            showToast(`Collection failed: ${res.message}`, 'danger');
          }
          await refreshAll(true);
        } catch (err) {
          showToast(`Collection error: ${err.message}`, 'danger');
        } finally {
          btn.disabled = false;
          btn.innerHTML = origHtml;
        }
      });
    });
  }

  function populateServerSelect() {
    if (!el.chartServerSelect) return;

    if (state.servers.length === 0) {
      el.chartServerSelect.innerHTML = '<option value="">No servers available</option>';
      return;
    }

    const currentVal = el.chartServerSelect.value;
    const optionsHtml = state.servers.map(s => `
      <option value="${s.id}" ${s.id === state.selectedServerId ? 'selected' : ''}>
        ${escapeHtml(s.server_name)} (${s.hostname})
      </option>
    `).join('');

    el.chartServerSelect.innerHTML = optionsHtml;

    if (!state.selectedServerId && state.servers.length > 0) {
      state.selectedServerId = state.servers[0].id;
      el.chartServerSelect.value = state.selectedServerId;
    } else if (currentVal) {
      el.chartServerSelect.value = currentVal;
    }
  }

  // ================= CHART CONTROLLER =================

  function getChartThemeColors() {
    const isDark = state.theme === 'dark';
    return {
      gridColor: isDark ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.06)',
      textColor: isDark ? '#94a3b8' : '#64748b',
      tooltipBg: isDark ? '#1e293b' : '#ffffff',
      tooltipText: isDark ? '#f8fafc' : '#0f172a',
      tooltipBorder: isDark ? '#334155' : '#e2e8f0',
    };
  }

  async function updateCharts() {
    if (!state.selectedServerId) return;

    try {
      const data = await fetchServerMetrics(state.selectedServerId, state.selectedRange);
      renderChartsData(data);
    } catch (err) {
      console.warn('Error updating charts:', err);
    }
  }

  function renderChartsData(data) {
    if (!window.Chart) return;
    const theme = getChartThemeColors();

    const formattedLabels = (data.labels || []).map(l => {
      const d = new Date(l);
      if (isNaN(d.getTime())) return l;
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    });

    // Update badges
    const latestCpu = data.cpu && data.cpu.length > 0 ? data.cpu[data.cpu.length - 1] : 0;
    const latestMem = data.memory && data.memory.length > 0 ? data.memory[data.memory.length - 1] : 0;
    const latestDisk = data.disk && data.disk.length > 0 ? data.disk[data.disk.length - 1] : 0;
    const latestNetRx = data.network_rx && data.network_rx.length > 0 ? data.network_rx[data.network_rx.length - 1] : 0;
    const latestNetTx = data.network_tx && data.network_tx.length > 0 ? data.network_tx[data.network_tx.length - 1] : 0;

    if (el.badgeCpu) el.badgeCpu.textContent = `${Number(latestCpu).toFixed(1)}%`;
    if (el.badgeMem) el.badgeMem.textContent = `${Number(latestMem).toFixed(1)}%`;
    if (el.badgeDisk) el.badgeDisk.textContent = `${Number(latestDisk).toFixed(1)}%`;
    if (el.badgeNet) el.badgeNet.textContent = `↓${Number(latestNetRx).toFixed(1)} ↑${Number(latestNetTx).toFixed(1)} KB/s`;

    if (data.deltas) {
      updateDeltaBadgeEl(el.deltaCpuBadge, data.deltas.cpu, '%');
      updateDeltaBadgeEl(el.deltaMemBadge, data.deltas.memory, '%');
      updateDeltaBadgeEl(el.deltaDiskBadge, data.deltas.disk, '%');
      updateDeltaBadgeEl(el.deltaNetBadge, data.deltas.network_rx, ' KB/s');
    }

    const pointRadius = (data.cpu || []).length > 60 ? 2 : 4;

    // 1. CPU Chart
    const cpuCtx = document.getElementById('chart-cpu')?.getContext('2d');
    if (cpuCtx) {
      if (state.charts.cpu) state.charts.cpu.destroy();
      state.charts.cpu = new Chart(cpuCtx, {
        type: 'line',
        data: {
          labels: formattedLabels,
          datasets: [
            {
              label: 'CPU Usage (%)',
              data: data.cpu || [],
              borderColor: '#6366f1',
              backgroundColor: 'rgba(99, 102, 241, 0.15)',
              borderWidth: 2,
              tension: 0.35,
              fill: true,
              pointRadius: pointRadius,
              pointHoverRadius: 6,
            },
            {
              label: '1m Load Average',
              data: data.load_1m || [],
              borderColor: '#f59e0b',
              borderDash: [4, 4],
              borderWidth: 1.5,
              tension: 0.35,
              fill: false,
              pointRadius: 0,
            },
          ],
        },
        options: createChartOptions(theme, '%', [0, 100]),
      });
    }

    // 2. Memory Chart
    const memCtx = document.getElementById('chart-memory')?.getContext('2d');
    if (memCtx) {
      if (state.charts.memory) state.charts.memory.destroy();
      state.charts.memory = new Chart(memCtx, {
        type: 'line',
        data: {
          labels: formattedLabels,
          datasets: [
            {
              label: 'Memory Usage (%)',
              data: data.memory || [],
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              borderWidth: 2,
              tension: 0.35,
              fill: true,
              pointRadius: pointRadius,
              pointHoverRadius: 6,
            },
          ],
        },
        options: createChartOptions(theme, '%', [0, 100]),
      });
    }

    // 3. Disk Chart
    const diskCtx = document.getElementById('chart-disk')?.getContext('2d');
    if (diskCtx) {
      if (state.charts.disk) state.charts.disk.destroy();
      state.charts.disk = new Chart(diskCtx, {
        type: 'line',
        data: {
          labels: formattedLabels,
          datasets: [
            {
              label: 'Disk Usage (%)',
              data: data.disk || [],
              borderColor: '#f59e0b',
              backgroundColor: 'rgba(245, 158, 11, 0.15)',
              borderWidth: 2,
              tension: 0.35,
              fill: true,
              pointRadius: pointRadius,
              pointHoverRadius: 6,
            },
          ],
        },
        options: createChartOptions(theme, '%', [0, 100]),
      });
    }

    // 4. Network Chart
    const netCtx = document.getElementById('chart-network')?.getContext('2d');
    if (netCtx) {
      if (state.charts.network) state.charts.network.destroy();
      state.charts.network = new Chart(netCtx, {
        type: 'line',
        data: {
          labels: formattedLabels,
          datasets: [
            {
              label: 'Receive Rate (KB/s)',
              data: data.network_rx || [],
              borderColor: '#0ea5e9',
              backgroundColor: 'rgba(14, 165, 233, 0.1)',
              borderWidth: 2,
              tension: 0.35,
              fill: true,
              pointRadius: pointRadius,
              pointHoverRadius: 6,
            },
            {
              label: 'Transmit Rate (KB/s)',
              data: data.network_tx || [],
              borderColor: '#a855f7',
              backgroundColor: 'rgba(168, 85, 247, 0.1)',
              borderWidth: 2,
              tension: 0.35,
              fill: true,
              pointRadius: pointRadius,
              pointHoverRadius: 6,
            },
          ],
        },
        options: createChartOptions(theme, ' KB/s'),
      });
    }
  }

  function createChartOptions(theme, unit = '', suggestedRange = null) {
    const scales = {
      x: {
        grid: { color: theme.gridColor },
        ticks: { color: theme.textColor, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
      },
      y: {
        grid: { color: theme.gridColor },
        ticks: {
          color: theme.textColor,
          callback: (value) => `${value}${unit}`,
        },
      },
    };

    if (suggestedRange) {
      scales.y.suggestedMin = suggestedRange[0];
      scales.y.suggestedMax = suggestedRange[1];
    }

    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'end',
          labels: {
            boxWidth: 12,
            color: theme.textColor,
            font: { size: 11 },
          },
        },
        tooltip: {
          backgroundColor: theme.tooltipBg,
          titleColor: theme.tooltipText,
          bodyColor: theme.tooltipText,
          borderColor: theme.tooltipBorder,
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}${unit}`,
          },
        },
      },
      scales,
    };
  }

  // ================= ALERTS RENDER =================

  function renderAlertsList() {
    if (!el.alertsListContainer) return;

    let filtered = state.alerts;

    if (state.currentAlertFilter === 'ACTIVE') {
      filtered = filtered.filter(a => a.status === 'ACTIVE');
    } else if (state.currentAlertFilter === 'RESOLVED') {
      filtered = filtered.filter(a => a.status === 'RESOLVED');
    } else if (state.currentAlertFilter === 'CRITICAL') {
      filtered = filtered.filter(a => a.severity === 'CRITICAL' && a.status === 'ACTIVE');
    } else if (state.currentAlertFilter === 'WARNING') {
      filtered = filtered.filter(a => a.severity === 'WARNING' && a.status === 'ACTIVE');
    }

    if (filtered.length === 0) {
      el.alertsListContainer.innerHTML = '';
      if (el.alertsEmptyState) el.alertsEmptyState.classList.remove('d-none');
      return;
    }

    if (el.alertsEmptyState) el.alertsEmptyState.classList.add('d-none');

    const alertsHtml = filtered.map(alert => {
      const severityClass = (alert.severity || '').toLowerCase();
      const severityBadge =
        alert.severity === 'CRITICAL' ? '<span class="badge bg-danger">CRITICAL</span>' :
        alert.severity === 'WARNING' ? '<span class="badge bg-warning text-dark">WARNING</span>' :
        '<span class="badge bg-info">INFO</span>';

      const statusBadge =
        alert.status === 'ACTIVE' ? '<span class="badge badge-soft-danger">ACTIVE</span>' :
        '<span class="badge badge-soft-success">RESOLVED</span>';

      const resolveBtn = alert.status === 'ACTIVE'
        ? `<button class="btn btn-sm btn-outline-success btn-resolve-alert" data-id="${alert.id}">
             <i class="bi bi-check-lg me-1"></i> Resolve
           </button>`
        : `<span class="text-muted small"><i class="bi bi-check2-all text-success me-1"></i>Resolved</span>`;

      return `
        <div class="alert-item-card ${severityClass}" id="alert-card-${alert.id}">
          <div class="d-flex align-items-start gap-3 flex-grow-1">
            <div class="mt-1">
              ${severityBadge}
            </div>
            <div>
              <div class="d-flex align-items-center gap-2 mb-1">
                <span class="fw-bold text-light">${escapeHtml(alert.title)}</span>
                <span class="badge badge-soft-info">${escapeHtml(alert.server_name)}</span>
                ${statusBadge}
              </div>
              <p class="text-muted small mb-1">${escapeHtml(alert.message || 'No additional details.')}</p>
              <div class="text-muted" style="font-size: 0.72rem;">
                <i class="bi bi-clock me-1"></i> Triggered ${formatRelativeTime(alert.created_at)}
              </div>
            </div>
          </div>
          <div class="align-self-center">
            ${resolveBtn}
          </div>
        </div>
      `;
    }).join('');

    el.alertsListContainer.innerHTML = alertsHtml;

    // Attach resolve button events
    el.alertsListContainer.querySelectorAll('.btn-resolve-alert').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.getAttribute('data-id'), 10);
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';

        try {
          await resolveAlert(id);
          showToast('Alert resolved successfully.', 'success');
          await refreshAll(true);
        } catch (err) {
          showToast(`Error resolving alert: ${err.message}`, 'danger');
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Resolve';
        }
      });
    });
  }

  // ================= SYSTEM ACTIVITY LOG =================

  function renderActivityLog(recentActivity = null, isLiveRefresh = false) {
    if (!el.activityTableBody) return;

    const activityList = (recentActivity && recentActivity.length > 0)
      ? recentActivity
      : (state.stats && state.stats.recent_activity && state.stats.recent_activity.length > 0)
        ? state.stats.recent_activity
        : null;

    if (!activityList || activityList.length === 0) {
      if (state.servers.length === 0) {
        el.activityTableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">No monitoring activity recorded yet.</td></tr>';
        return;
      }

      // Fallback to current server fleet state
      const rows = state.servers.map(s => {
        const isUp = s.status === 'UP';
        const resultBadge = isUp
          ? '<span class="badge badge-soft-success font-monospace"><i class="bi bi-check2 me-1"></i>200 OK</span>'
          : `<span class="badge badge-soft-danger font-monospace" title="${escapeHtml(s.last_error)}"><i class="bi bi-x me-1"></i>Failed</span>`;
        const m = s.latest_metrics;
        const cpuV = m && m.cpu ? m.cpu.usage_percent : 0;
        const memV = m && m.memory ? m.memory.usage_percent : 0;
        const diskV = m && m.disk ? m.disk.usage_percent : 0;
        const rxV = m && m.network ? m.network.receive_rate_kbps : 0;
        const cpuDeltaPill = renderDeltaPill(m && m.cpu ? m.cpu.delta : 0, '%');
        const memDeltaPill = renderDeltaPill(m && m.memory ? m.memory.delta : 0, '%');

        return `
          <tr>
            <td class="font-monospace small">${s.last_check_at ? new Date(s.last_check_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Just now'}</td>
            <td class="fw-bold">${escapeHtml(s.server_name)} <span class="text-muted small font-monospace">(${escapeHtml(s.hostname)})</span></td>
            <td>${isUp ? '<span class="status-dot online me-1"></span> ONLINE' : '<span class="status-dot offline me-1"></span> OFFLINE'}</td>
            <td class="font-monospace small">
              <span class="text-info">CPU: ${cpuV}%</span> | 
              <span class="text-success">RAM: ${memV}%</span> | 
              <span class="text-warning">Disk: ${diskV}%</span> | 
              <span class="text-primary">Net: ${rxV} KB/s</span>
            </td>
            <td>
              <div class="d-flex align-items-center gap-1">
                ${cpuDeltaPill} ${memDeltaPill}
              </div>
            </td>
            <td>${resultBadge}</td>
          </tr>
        `;
      }).join('');
      el.activityTableBody.innerHTML = rows;
      return;
    }

    const rows = activityList.map((item, idx) => {
      const isUp = item.status === 'UP';
      const resultBadge = isUp
        ? '<span class="badge badge-soft-success font-monospace"><i class="bi bi-check2-circle me-1"></i>200 OK</span>'
        : `<span class="badge badge-soft-danger font-monospace" title="${escapeHtml(item.result || 'Poll failed')}"><i class="bi bi-x-circle me-1"></i>Failed</span>`;

      const d = item.timestamp ? new Date(item.timestamp) : null;
      const timeStr = d && !isNaN(d.getTime())
        ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : 'Recently';
      const dateStr = d && !isNaN(d.getTime())
        ? d.toLocaleDateString()
        : '';

      const flashClass = (idx === 0 && isLiveRefresh) ? 'row-flash' : '';
      const cpuDeltaPill = renderDeltaPill(item.cpu_delta || 0, '%');
      const memDeltaPill = renderDeltaPill(item.mem_delta || 0, '%');

      return `
        <tr class="${flashClass}">
          <td class="font-monospace small">
            <strong>${timeStr}</strong> <span class="text-muted" style="font-size: 0.72rem;">(${dateStr})</span>
          </td>
          <td class="fw-bold">
            ${escapeHtml(item.server_name)} 
            <span class="text-muted small font-monospace">(${escapeHtml(item.hostname)})</span>
          </td>
          <td>${isUp ? '<span class="status-dot online me-1"></span> ONLINE' : '<span class="status-dot offline me-1"></span> OFFLINE'}</td>
          <td class="font-monospace small">
            <span class="text-info">CPU: ${item.cpu_usage}%</span> | 
            <span class="text-success">RAM: ${item.memory_usage}%</span> | 
            <span class="text-warning">Disk: ${item.disk_usage}%</span> | 
            <span class="text-primary">Net: ${item.network_rx_kbps} KB/s</span>
          </td>
          <td>
            <div class="d-flex align-items-center gap-1">
              ${cpuDeltaPill} ${memDeltaPill}
            </div>
          </td>
          <td>${resultBadge}</td>
        </tr>
      `;
    }).join('');

    el.activityTableBody.innerHTML = rows;
  }

  // ================= SERVER DRILL-DOWN MODAL =================

  function openServerDetailModal(serverId) {
    const server = state.servers.find(s => s.id === serverId);
    if (!server) return;

    state.selectedServerId = server.id;

    if (el.modalName) el.modalName.textContent = server.server_name;
    if (el.modalHostname) el.modalHostname.textContent = `${server.hostname}:${server.ssh_port}`;
    if (el.modalStatus) {
      el.modalStatus.innerHTML = server.status === 'UP'
        ? '<span class="text-success"><i class="bi bi-check-circle-fill me-1"></i> ONLINE</span>'
        : '<span class="text-danger"><i class="bi bi-x-circle-fill me-1"></i> OFFLINE</span>';
    }
    if (el.modalOs) el.modalOs.innerHTML = getOsBadge(server.operating_system);
    if (el.modalSsh) el.modalSsh.textContent = `Port ${server.ssh_port} (${server.username})`;
    if (el.modalLastCheck) el.modalLastCheck.textContent = formatRelativeTime(server.last_check_at);

    const m = server.latest_metrics;

    // CPU
    const cpuPct = m && m.cpu ? m.cpu.usage_percent : 0;
    if (el.modalCpuPct) el.modalCpuPct.textContent = `${cpuPct}%`;
    if (el.modalCpuBar) {
      el.modalCpuBar.style.width = `${Math.min(100, Math.max(0, cpuPct))}%`;
      el.modalCpuBar.className = `meter-fill ${getMeterColorClass(cpuPct)}`;
    }
    if (el.modalCpuLoad) {
      el.modalCpuLoad.textContent = m && m.cpu
        ? `Load: 1m: ${m.cpu.load_1m} | 5m: ${m.cpu.load_5m} | 15m: ${m.cpu.load_15m}`
        : 'Load: N/A';
    }

    // Memory
    const memPct = m && m.memory ? m.memory.usage_percent : 0;
    if (el.modalMemPct) el.modalMemPct.textContent = `${memPct}%`;
    if (el.modalMemBar) {
      el.modalMemBar.style.width = `${Math.min(100, Math.max(0, memPct))}%`;
      el.modalMemBar.className = `meter-fill ${getMeterColorClass(memPct)}`;
    }
    if (el.modalMemGb) {
      el.modalMemGb.textContent = m && m.memory
        ? `${m.memory.used_gb} GB used / ${m.memory.total_gb} GB total`
        : 'N/A';
    }

    // Disk
    const diskPct = m && m.disk ? m.disk.usage_percent : 0;
    if (el.modalDiskPct) el.modalDiskPct.textContent = `${diskPct}%`;
    if (el.modalDiskBar) {
      el.modalDiskBar.style.width = `${Math.min(100, Math.max(0, diskPct))}%`;
      el.modalDiskBar.className = `meter-fill ${getMeterColorClass(diskPct)}`;
    }
    if (el.modalDiskGb) {
      el.modalDiskGb.textContent = m && m.disk
        ? `${m.disk.used_gb} GB used (${m.disk.mount_point})`
        : 'N/A';
    }

    // Network
    if (el.modalNetIface) el.modalNetIface.textContent = m && m.network ? m.network.interface : 'eth0';
    if (el.modalNetRx) el.modalNetRx.textContent = m && m.network ? `${m.network.receive_rate_kbps} KB/s` : '0 KB/s';
    if (el.modalNetTx) el.modalNetTx.textContent = m && m.network ? `${m.network.transmit_rate_kbps} KB/s` : '0 KB/s';
    if (el.modalNetTotal) {
      const rxMb = m && m.network ? (m.network.received_bytes / (1024 * 1024)).toFixed(1) : 0;
      const txMb = m && m.network ? (m.network.transmitted_bytes / (1024 * 1024)).toFixed(1) : 0;
      el.modalNetTotal.textContent = `RX: ${rxMb} MB | TX: ${txMb} MB`;
    }

    // Error box
    if (server.last_error) {
      if (el.modalErrorBox) el.modalErrorBox.classList.remove('d-none');
      if (el.modalErrorText) el.modalErrorText.textContent = server.last_error;
    } else {
      if (el.modalErrorBox) el.modalErrorBox.classList.add('d-none');
    }

    if (el.modalSshOutput) {
      el.modalSshOutput.textContent = 'Click "Test SSH Connection" to run live paramiko diagnostic test.';
    }

    if (window.bootstrap && el.modalEl) {
      const modal = bootstrap.Modal.getOrCreateInstance(el.modalEl);
      modal.show();
    }
  }

  // ================= REFRESH ORCHESTRATION =================

  async function refreshAll(silent = false) {
    if (state.isFetching) return;
    state.isFetching = true;

    if (!silent && el.refreshIcon) {
      el.refreshIcon.classList.add('spin-icon');
    }
    if (el.refreshBtn) el.refreshBtn.disabled = true;

    try {
      const [stats, servers, alerts] = await Promise.all([
        fetchDashboardStats(),
        fetchServers(),
        fetchAlerts(),
      ]);

      if (el.errorBanner) el.errorBanner.classList.add('d-none');

      state.servers = servers;
      state.alerts = alerts;
      renderStats(stats);
      renderLiveRefreshBanner(stats, servers);
      renderServersTable();
      populateServerSelect();
      renderAlertsList();
      renderActivityLog(stats.recent_activity, silent);
      await updateCharts();

    } catch (err) {
      console.error('Failed to refresh dashboard:', err);
      if (el.errorBanner) {
        el.errorBanner.classList.remove('d-none');
        if (el.errorMessage) el.errorMessage.textContent = `Error loading dashboard metrics: ${err.message}`;
      }
    } finally {
      state.isFetching = false;
      if (el.refreshIcon) el.refreshIcon.classList.remove('spin-icon');
      if (el.refreshBtn) el.refreshBtn.disabled = false;
    }
  }

  function startCountdown() {
    stopCountdown();
    if (state.autoRefreshInterval <= 0) {
      if (el.countdownSec) el.countdownSec.textContent = 'Paused';
      return;
    }
    state.countdownSeconds = Math.round(state.autoRefreshInterval / 1000);
    if (el.countdownSec) el.countdownSec.textContent = state.countdownSeconds;

    state.countdownTimer = setInterval(() => {
      if (state.autoRefreshInterval <= 0) {
        if (el.countdownSec) el.countdownSec.textContent = 'Paused';
        return;
      }
      state.countdownSeconds -= 1;
      if (state.countdownSeconds <= 0) {
        state.countdownSeconds = Math.round(state.autoRefreshInterval / 1000);
        if (el.countdownSec) el.countdownSec.textContent = state.countdownSeconds;
        refreshAll(true);
      } else {
        if (el.countdownSec) el.countdownSec.textContent = state.countdownSeconds;
      }
    }, 1000);
  }

  function stopCountdown() {
    if (state.countdownTimer) {
      clearInterval(state.countdownTimer);
      state.countdownTimer = null;
    }
  }

  // ================= THEME CONTROLLER =================

  function applyTheme(theme) {
    state.theme = theme;
    localStorage.setItem('dash_theme', theme);

    if (el.app) el.app.setAttribute('data-bs-theme', theme);
    document.body.setAttribute('data-bs-theme', theme);

    if (el.themeToggleIcon) {
      el.themeToggleIcon.className = theme === 'dark' ? 'bi bi-moon-stars' : 'bi bi-sun';
    }

    updateCharts();
  }

  // ================= EVENT LISTENERS =================

  // Theme Toggle
  if (el.themeToggleBtn) {
    el.themeToggleBtn.addEventListener('click', () => {
      applyTheme(state.theme === 'dark' ? 'light' : 'dark');
    });
  }

  // Manual Refresh
  if (el.refreshBtn) {
    el.refreshBtn.addEventListener('click', () => {
      state.countdownSeconds = Math.round(state.autoRefreshInterval / 1000);
      if (el.countdownSec) el.countdownSec.textContent = state.countdownSeconds;
      refreshAll(false);
      showToast('Telemetry data refreshed.', 'info');
    });
  }

  // Auto Refresh Interval
  document.querySelectorAll('[data-interval]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const interval = parseInt(btn.getAttribute('data-interval'), 10);
      state.autoRefreshInterval = interval;

      document.querySelectorAll('[data-interval]').forEach(b => b.classList.remove('active-refresh'));
      btn.classList.add('active-refresh');

      if (interval === 0) {
        if (el.autoRefreshLabel) el.autoRefreshLabel.textContent = 'Paused';
        stopCountdown();
        if (el.countdownSec) el.countdownSec.textContent = 'Paused';
        showToast('Auto-refresh paused.', 'warning');
      } else {
        const sec = interval / 1000;
        if (el.autoRefreshLabel) el.autoRefreshLabel.textContent = `Refresh: ${sec}s`;
        startCountdown();
        showToast(`Auto-refresh set to ${sec}s.`, 'info');
      }
    });
  });

  // Server Filter Buttons
  document.querySelectorAll('[data-server-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-server-filter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentServerFilter = btn.getAttribute('data-server-filter');
      renderServersTable();
    });
  });

  // Server Search
  if (el.serverSearchInput) {
    let debounceTimer = null;
    el.serverSearchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        state.searchQuery = e.target.value;
        renderServersTable();
      }, 150);
    });
  }

  if (el.btnClearSearch) {
    el.btnClearSearch.addEventListener('click', () => {
      if (el.serverSearchInput) el.serverSearchInput.value = '';
      state.searchQuery = '';
      state.currentServerFilter = 'ALL';
      document.querySelectorAll('[data-server-filter]').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-server-filter') === 'ALL');
      });
      renderServersTable();
    });
  }

  // Time Range Buttons
  document.querySelectorAll('[data-range]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-range]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.selectedRange = btn.getAttribute('data-range');
      updateCharts();
    });
  });

  // Chart Server Select
  if (el.chartServerSelect) {
    el.chartServerSelect.addEventListener('change', (e) => {
      state.selectedServerId = parseInt(e.target.value, 10);
      updateCharts();
    });
  }

  // Alert Filter Buttons
  document.querySelectorAll('[data-alert-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-alert-filter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentAlertFilter = btn.getAttribute('data-alert-filter');
      renderAlertsList();
    });
  });

  // Mobile Sidebar Toggle
  if (el.sidebarToggleBtn && el.sidebar) {
    el.sidebarToggleBtn.addEventListener('click', () => {
      el.sidebar.classList.toggle('show');
    });

    document.addEventListener('click', (e) => {
      if (!el.sidebar.contains(e.target) && !el.sidebarToggleBtn.contains(e.target) && el.sidebar.classList.contains('show')) {
        el.sidebar.classList.remove('show');
      }
    });
  }

  // Modal SSH Test Button
  if (el.btnModalTestSsh) {
    el.btnModalTestSsh.addEventListener('click', async () => {
      if (!state.selectedServerId) return;
      const origText = el.btnModalTestSsh.innerHTML;
      el.btnModalTestSsh.disabled = true;
      el.btnModalTestSsh.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Testing SSH...';
      if (el.modalSshOutput) {
        el.modalSshOutput.textContent = 'Connecting via SSH (paramiko)... executing "hostname"...';
      }

      try {
        const res = await testServerSSH(state.selectedServerId);
        if (el.modalSshOutput) {
          el.modalSshOutput.innerHTML = `[${new Date().toLocaleTimeString()}] Result: ${res.success ? 'SUCCESS' : 'FAILED'}\nStatus: ${res.status}\nMessage: ${res.message}\nRemote Hostname: ${res.hostname || 'N/A'}\nLast Checked: ${res.last_check_at || 'Now'}`;
        }
        if (res.success) {
          showToast(`Connected successfully to ${res.hostname || 'server'}`, 'success');
        } else {
          showToast(`SSH failed: ${res.message}`, 'danger');
        }
        await refreshAll(true);
      } catch (err) {
        if (el.modalSshOutput) el.modalSshOutput.textContent = `Diagnostic Error: ${err.message}`;
        showToast(`SSH error: ${err.message}`, 'danger');
      } finally {
        el.btnModalTestSsh.disabled = false;
        el.btnModalTestSsh.innerHTML = origText;
      }
    });
  }

  // Modal Collect Metrics Button
  if (el.btnModalCollect) {
    el.btnModalCollect.addEventListener('click', async () => {
      if (!state.selectedServerId) return;
      const origText = el.btnModalCollect.innerHTML;
      el.btnModalCollect.disabled = true;
      el.btnModalCollect.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Collecting...';

      try {
        const res = await collectServerMetricsNow(state.selectedServerId);
        if (res.success) {
          showToast('Fresh metrics collected successfully!', 'success');
          await refreshAll(true);
          // Re-populate modal with updated data
          openServerDetailModal(state.selectedServerId);
        } else {
          showToast(`Collection failed: ${res.message}`, 'danger');
        }
      } catch (err) {
        showToast(`Error: ${err.message}`, 'danger');
      } finally {
        el.btnModalCollect.disabled = false;
        el.btnModalCollect.innerHTML = origText;
      }
    });
  }

  // Retry Button
  if (el.btnErrorRetry) {
    el.btnErrorRetry.addEventListener('click', () => {
      refreshAll(false);
    });
  }

  // Initialize
  applyTheme(state.theme);
  refreshAll(false);
  startCountdown();
});
