/**
 * Linux Server Monitoring System - Dashboard Application
 * Infrastructure Command Center Observability Client Script
 */

document.addEventListener('DOMContentLoaded', () => {
  // Global Dashboard State
  const state = {
    servers: [],
    stats: null,
    alerts: [],
    currentServerFilter: 'ALL', // 'ALL' | 'HEALTHY' | 'WARNING' | 'DOWN'
    searchQuery: '',
    currentAlertFilter: 'ACTIVE',
    selectedServerId: null,
    selectedRange: '24h',
    autoRefreshInterval: 10000, // Exactly 10 seconds
    countdownSeconds: 10,
    countdownTimer: null,
    isFetching: false,
    theme: localStorage.getItem('dash_theme') || 'dark',
    chartModel: localStorage.getItem('dash_chart_model') || 'zigzag', // 'zigzag' | 'smooth' | 'stepped'
    chartScaleMode: localStorage.getItem('dash_chart_scale') || 'dynamic', // 'dynamic' | 'fixed'
    charts: {
      cpu: null,
      memory: null,
      disk: null,
      network: null,
    },
    sparklines: {
      cpu: null,
      memory: null,
      disk: null,
      network: null,
    },
  };

  // DOM Elements Cache
  const el = {
    app: document.getElementById('dashboard-app'),
    // System Command Bar (Level 1)
    systemStatusPill: document.getElementById('system-status-pill'),
    systemStatusDot: document.getElementById('system-status-dot'),
    systemStatusText: document.getElementById('system-status-text'),
    statTotalChip: document.getElementById('stat-total-chip'),
    statOnlineChip: document.getElementById('stat-online-chip'),
    statWarningChip: document.getElementById('stat-warning-chip'),
    statOfflineChip: document.getElementById('stat-offline-chip'),
    statAlertsChip: document.getElementById('stat-alerts-chip'),
    lastUpdatedTime: document.getElementById('last-updated-time'),
    footerLastUpdated: document.getElementById('footer-last-updated'),
    refreshStatusBadge: document.getElementById('refresh-status-badge'),
    countdownSec: document.getElementById('refresh-countdown-sec'),
    refreshBtn: document.getElementById('btn-refresh-all'),
    refreshIcon: document.getElementById('refresh-icon'),
    themeToggleBtn: document.getElementById('btn-theme-toggle'),
    themeToggleIcon: document.getElementById('theme-toggle-icon'),
    sidebarToggleBtn: document.getElementById('sidebar-toggle'),
    sidebar: document.getElementById('dash-sidebar'),
    sidebarFleetStatus: document.getElementById('sidebar-fleet-status'),
    sidebarServerCount: document.getElementById('sidebar-server-count'),
    sidebarStatusDot: document.getElementById('sidebar-status-dot'),
    errorBanner: document.getElementById('dash-error-banner'),
    errorMessage: document.getElementById('dash-error-message'),
    btnErrorRetry: document.getElementById('btn-error-retry'),

    // KPI Cards (Level 2)
    statTotal: document.getElementById('stat-total-servers'),
    statOnline: document.getElementById('stat-online-servers'),
    statOnlineSub: document.getElementById('stat-online-subtext'),
    statWarning: document.getElementById('stat-warning-servers'),
    statWarningSub: document.getElementById('stat-warning-subtext'),
    statOffline: document.getElementById('stat-offline-servers'),
    statOfflineSub: document.getElementById('stat-offline-subtext'),
    statAlerts: document.getElementById('stat-active-alerts'),
    statAlertsSub: document.getElementById('stat-alerts-subtext'),
    statSuccessRate: document.getElementById('stat-success-rate'),
    statSuccessSub: document.getElementById('stat-success-subtext'),

    // Server Health Matrix (Level 3)
    serverSearchInput: document.getElementById('server-search-input'),
    serversTableBody: document.getElementById('servers-table-body'),
    serversEmptyState: document.getElementById('servers-empty-state'),
    btnClearSearch: document.getElementById('btn-clear-search'),

    // Resource Overview (Level 4A)
    overviewCpuVal: document.getElementById('overview-cpu-val'),
    overviewCpuStatus: document.getElementById('overview-cpu-status'),
    overviewCpuDelta: document.getElementById('overview-cpu-delta'),
    overviewMemVal: document.getElementById('overview-mem-val'),
    overviewMemStatus: document.getElementById('overview-mem-status'),
    overviewMemDelta: document.getElementById('overview-mem-delta'),
    overviewDiskVal: document.getElementById('overview-disk-val'),
    overviewDiskStatus: document.getElementById('overview-disk-status'),
    overviewDiskDelta: document.getElementById('overview-disk-delta'),
    overviewNetVal: document.getElementById('overview-net-val'),
    overviewNetStatus: document.getElementById('overview-net-status'),
    overviewNetDelta: document.getElementById('overview-net-delta'),

    // Resource Heatmap (Level 4B)
    heatmapTableBody: document.getElementById('heatmap-table-body'),

    // Alerts & Action Tasks (Level 5)
    alertsListContainer: document.getElementById('alerts-list-container'),
    alertsEmptyState: document.getElementById('alerts-empty-state'),
    actionTasksContainer: document.getElementById('action-tasks-container'),

    // Monitoring Engine (Level 6)
    engineServiceStatus: document.getElementById('engine-service-status'),
    engineSchedulerStatus: document.getElementById('engine-scheduler-status'),
    engineRunnerStatus: document.getElementById('engine-runner-status'),
    engineLastSuccess: document.getElementById('engine-last-success'),
    engineLastFail: document.getElementById('engine-last-fail'),
    engineLastCheck: document.getElementById('engine-last-check'),
    engineNextRefresh: document.getElementById('engine-next-refresh'),
    engineOverallBadge: document.getElementById('engine-overall-badge'),

    // Historical Analytics (Level 7)
    chartServerSelect: document.getElementById('chart-server-select'),
    chartModelGroup: document.getElementById('chart-model-group'),
    btnChartScaleToggle: document.getElementById('btn-chart-scale-toggle'),
    chartScaleLabel: document.getElementById('chart-scale-label'),
    chartScaleIcon: document.getElementById('chart-scale-icon'),
    btnChartCollectSample: document.getElementById('btn-chart-collect-sample'),
    statCpuCurrent: document.getElementById('stat-cpu-current'),
    statCpuAvg: document.getElementById('stat-cpu-avg'),
    statCpuPeak: document.getElementById('stat-cpu-peak'),
    statMemCurrent: document.getElementById('stat-mem-current'),
    statMemAvg: document.getElementById('stat-mem-avg'),
    statMemPeak: document.getElementById('stat-mem-peak'),
    statDiskCurrent: document.getElementById('stat-disk-current'),
    statDiskAvg: document.getElementById('stat-disk-avg'),
    statDiskPeak: document.getElementById('stat-disk-peak'),
    statNetCurrent: document.getElementById('stat-net-current'),
    statNetAvg: document.getElementById('stat-net-avg'),
    statNetPeak: document.getElementById('stat-net-peak'),

    // Activity Stream (Level 8)
    activityTableBody: document.getElementById('activity-table-body'),

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
    }, 4000);
  }

  // Format relative time (e.g. "8 sec ago")
  function formatRelativeTime(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Never';

    const now = new Date();
    const diffSeconds = Math.floor((now - date) / 1000);

    if (diffSeconds < 5) return 'Just now';
    if (diffSeconds < 60) return `${diffSeconds} sec ago`;
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }

  function formatTimeOnly(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Never';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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

  // Helper: Delta Variation Formatting
  function renderDeltaPill(delta, unit = '%', invertSemantic = false) {
    if (typeof delta !== 'number' || isNaN(delta)) {
      return `<span class="badge-delta badge-delta-neutral font-monospace">0.00${unit}</span>`;
    }
    const abs = Math.abs(delta).toFixed(2);
    if (delta > 0) {
      const cls = invertSemantic ? 'badge-delta-down' : 'badge-delta-up';
      return `<span class="badge-delta ${cls} font-monospace" title="10s variation: +${abs}${unit}"><i class="bi bi-arrow-up-short"></i>+${abs}${unit}</span>`;
    } else if (delta < 0) {
      const cls = invertSemantic ? 'badge-delta-up' : 'badge-delta-down';
      return `<span class="badge-delta ${cls} font-monospace" title="10s variation: -${abs}${unit}"><i class="bi bi-arrow-down-short"></i>-${abs}${unit}</span>`;
    } else {
      return `<span class="badge-delta badge-delta-neutral font-monospace" title="10s variation: 0.00${unit}"><i class="bi bi-dash"></i>0.00${unit}</span>`;
    }
  }

  function updateDeltaBadgeEl(badgeEl, delta, unit = '%', invertSemantic = false) {
    if (!badgeEl) return;
    if (typeof delta !== 'number' || isNaN(delta)) {
      badgeEl.className = 'badge-delta badge-delta-neutral font-monospace';
      badgeEl.innerHTML = `<i class="bi bi-dash"></i>0.00${unit}`;
      badgeEl.title = `10s variation: 0.00${unit}`;
      return;
    }
    const abs = Math.abs(delta).toFixed(2);
    if (delta > 0) {
      const cls = invertSemantic ? 'badge-delta-down' : 'badge-delta-up';
      badgeEl.className = `badge-delta ${cls} font-monospace`;
      badgeEl.innerHTML = `<i class="bi bi-arrow-up-short"></i>+${abs}${unit}`;
      badgeEl.title = `10s variation: +${abs}${unit}`;
    } else if (delta < 0) {
      const cls = invertSemantic ? 'badge-delta-up' : 'badge-delta-down';
      badgeEl.className = `badge-delta ${cls} font-monospace`;
      badgeEl.innerHTML = `<i class="bi bi-arrow-down-short"></i>-${abs}${unit}`;
      badgeEl.title = `10s variation: -${abs}${unit}`;
    } else {
      badgeEl.className = 'badge-delta badge-delta-neutral font-monospace';
      badgeEl.innerHTML = `<i class="bi bi-dash"></i>0.00${unit}`;
      badgeEl.title = `10s variation: 0.00${unit}`;
    }
  }

  // ================= API LAYER =================

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

  // ================= RENDER LEVEL 1: TOP SYSTEM HEALTH BAR =================

  function renderSystemHealthBar(stats) {
    if (!stats) return;

    const sysStatus = (stats.system_status || 'HEALTHY').toUpperCase();
    if (el.systemStatusPill) {
      el.systemStatusPill.className = `system-status-pill ${sysStatus.toLowerCase()}`;
    }
    if (el.systemStatusText) {
      el.systemStatusText.textContent = sysStatus;
    }
    if (el.systemStatusDot) {
      el.systemStatusDot.className = `status-dot ${sysStatus === 'HEALTHY' ? 'online' : sysStatus === 'WARNING' ? 'warning' : 'offline'}`;
    }

    // Counters
    if (el.statTotalChip) el.statTotalChip.textContent = stats.total_servers ?? 0;
    if (el.statOnlineChip) el.statOnlineChip.textContent = stats.online_servers ?? 0;
    if (el.statWarningChip) el.statWarningChip.textContent = stats.warning_servers ?? 0;
    if (el.statOfflineChip) el.statOfflineChip.textContent = stats.offline_servers ?? 0;
    if (el.statAlertsChip) el.statAlertsChip.textContent = stats.active_alerts ?? 0;

    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    if (el.lastUpdatedTime) el.lastUpdatedTime.textContent = nowStr;
    if (el.footerLastUpdated) el.footerLastUpdated.textContent = nowStr;

    if (el.sidebarFleetStatus) {
      el.sidebarFleetStatus.textContent = sysStatus === 'CRITICAL'
        ? `${stats.offline_servers || 1} Offline Issue`
        : sysStatus === 'WARNING'
        ? 'Fleet Warnings Pending'
        : 'All Systems Healthy';
    }
    if (el.sidebarStatusDot) {
      el.sidebarStatusDot.className = `status-dot ${sysStatus === 'HEALTHY' ? 'online' : sysStatus === 'WARNING' ? 'warning' : 'offline'}`;
    }
    if (el.sidebarServerCount) {
      const count = stats.total_servers ?? 0;
      el.sidebarServerCount.textContent = `Monitoring ${count} ${count === 1 ? 'Server' : 'Servers'}`;
    }
  }

  // ================= RENDER LEVEL 2: KPI CARDS =================

  function renderKpis(stats) {
    if (!stats) return;

    if (el.statTotal) el.statTotal.textContent = stats.total_servers ?? 0;
    if (el.statOnline) el.statOnline.textContent = stats.online_servers ?? 0;
    if (el.statWarning) el.statWarning.textContent = stats.warning_servers ?? 0;
    if (el.statOffline) el.statOffline.textContent = stats.offline_servers ?? 0;
    if (el.statAlerts) el.statAlerts.textContent = stats.active_alerts ?? 0;

    const successPct = stats.monitoring_success_rate ?? stats.healthy_percent ?? 100.0;
    if (el.statSuccessRate) el.statSuccessRate.textContent = `${Number(successPct).toFixed(1)}%`;

    if (el.statOnlineSub) {
      el.statOnlineSub.innerHTML = `
        <span class="badge ${stats.offline_servers > 0 ? 'bg-warning text-dark' : 'bg-success'}">${stats.healthy_percent}%</span>
        <span>${stats.offline_servers > 0 ? 'Degraded fleet' : 'Responsive'}</span>
      `;
    }

    if (el.statWarningSub) {
      el.statWarningSub.innerHTML = `
        <span class="badge ${stats.warning_servers > 0 ? 'bg-warning text-dark' : 'bg-secondary'}">${stats.warning_servers} Elevated</span>
        <span>${stats.warning_servers > 0 ? 'Investigate' : 'Normal'}</span>
      `;
    }

    if (el.statOfflineSub) {
      el.statOfflineSub.innerHTML = `
        <span class="badge ${stats.offline_servers > 0 ? 'bg-danger' : 'bg-secondary'}">${stats.offline_servers} Issues</span>
        <span>${stats.offline_servers > 0 ? 'Requires attention' : 'All connected'}</span>
      `;
    }

    if (el.statAlertsSub) {
      el.statAlertsSub.innerHTML = `
        <span class="badge ${stats.critical_alerts > 0 ? 'bg-danger' : 'bg-secondary'}">${stats.critical_alerts} Critical</span>
        <span>${stats.active_alerts > 0 ? 'Active alerts' : 'Fleet normal'}</span>
      `;
    }

    if (el.statSuccessSub) {
      el.statSuccessSub.innerHTML = `
        <span class="badge ${successPct < 90 ? 'bg-danger' : 'bg-success'}">${successPct >= 99 ? 'Optimal' : 'Active'}</span>
        <span>Scheduled runs</span>
      `;
    }
  }

  // ================= RENDER LEVEL 3: SERVER HEALTH MATRIX (PHASE 5-8) =================

  function renderServerHealthMatrix() {
    if (!el.serversTableBody) return;

    let list = [...state.servers];

    // Attention-First Sorting Priority:
    // 1. Offline (DOWN)
    // 2. Critical Health / Critical Alert
    // 3. Warning
    // 4. Healthy (UP)
    list.sort((a, b) => {
      const getRank = (s) => {
        if (s.status === 'DOWN') return 0;
        if (s.health_status === 'CRITICAL') return 1;
        if (s.health_status === 'WARNING' || s.active_alerts_count > 0) return 2;
        if (s.status === 'UP') return 3;
        return 4;
      };
      return getRank(a) - getRank(b);
    });

    // Filter by Status
    if (state.currentServerFilter !== 'ALL') {
      if (state.currentServerFilter === 'HEALTHY') {
        list = list.filter(s => s.status === 'UP' && (s.health_status === 'HEALTHY' || !s.health_status));
      } else if (state.currentServerFilter === 'WARNING') {
        list = list.filter(s => s.health_status === 'WARNING' || (s.status === 'UP' && s.active_alerts_count > 0));
      } else if (state.currentServerFilter === 'DOWN') {
        list = list.filter(s => s.status === 'DOWN');
      }
    }

    // Filter by Search Query
    if (state.searchQuery.trim() !== '') {
      const q = state.searchQuery.toLowerCase();
      list = list.filter(s =>
        (s.server_name && s.server_name.toLowerCase().includes(q)) ||
        (s.hostname && s.hostname.toLowerCase().includes(q))
      );
    }

    if (list.length === 0) {
      el.serversTableBody.innerHTML = '';
      if (el.serversEmptyState) el.serversEmptyState.classList.remove('d-none');
      return;
    }

    if (el.serversEmptyState) el.serversEmptyState.classList.add('d-none');

    const rowsHtml = list.map(server => {
      const isDown = server.status === 'DOWN';
      const isWarn = server.health_status === 'WARNING' || server.active_alerts_count > 0;
      const rowAttentionClass = isDown ? 'matrix-row-attention-critical' : isWarn ? 'matrix-row-attention-warning' : '';

      // Status Badge (Phase 7: Explicit semantics)
      let statusBadge;
      if (isDown) {
        statusBadge = '<span class="badge badge-soft-danger"><span class="status-dot offline me-1"></span> Offline</span>';
      } else if (isWarn) {
        statusBadge = '<span class="badge badge-soft-warning"><i class="bi bi-exclamation-triangle-fill me-1"></i> Warning</span>';
      } else if (server.status === 'UP') {
        statusBadge = '<span class="badge badge-soft-success"><span class="status-dot online me-1"></span> Online</span>';
      } else {
        statusBadge = '<span class="badge badge-soft-secondary"><i class="bi bi-question-circle me-1"></i> Unknown</span>';
      }

      const m = server.latest_metrics;

      // CPU cell (Phase 6: compact indicator with progress bar & %)
      let cpuCell;
      if (m && m.cpu && !isDown) {
        const cpuPct = m.cpu.usage_percent;
        const cpuDeltaPill = renderDeltaPill(m.cpu.delta, '%');
        const cpuLoad = `Load: ${m.cpu.load_1m}, ${m.cpu.load_5m}`;
        cpuCell = `
          <div class="metric-meter-compact" title="${cpuLoad}">
            <div class="meter-top">
              <span class="meter-pct">${cpuPct}%</span>
              ${cpuDeltaPill}
            </div>
            <div class="meter-track-sm">
              <div class="meter-fill-sm ${getMeterColorClass(cpuPct)}" style="width: ${Math.min(100, Math.max(0, cpuPct))}%;"></div>
            </div>
          </div>
        `;
      } else {
        cpuCell = '<span class="text-muted font-monospace">--</span>';
      }

      // Memory cell
      let memCell;
      if (m && m.memory && !isDown) {
        const memPct = m.memory.usage_percent;
        const memDeltaPill = renderDeltaPill(m.memory.delta, '%');
        const memText = `${m.memory.used_gb} / ${m.memory.total_gb} GB`;
        memCell = `
          <div class="metric-meter-compact" title="${memText}">
            <div class="meter-top">
              <span class="meter-pct">${memPct}%</span>
              ${memDeltaPill}
            </div>
            <div class="meter-track-sm">
              <div class="meter-fill-sm ${getMeterColorClass(memPct)}" style="width: ${Math.min(100, Math.max(0, memPct))}%;"></div>
            </div>
          </div>
        `;
      } else {
        memCell = '<span class="text-muted font-monospace">--</span>';
      }

      // Disk cell
      let diskCell;
      if (m && m.disk && !isDown) {
        const diskPct = m.disk.usage_percent;
        const diskDeltaPill = renderDeltaPill(m.disk.delta, '%');
        const diskText = `${m.disk.used_gb} / ${m.disk.total_gb} GB (${m.disk.mount_point})`;
        diskCell = `
          <div class="metric-meter-compact" title="${diskText}">
            <div class="meter-top">
              <span class="meter-pct">${diskPct}%</span>
              ${diskDeltaPill}
            </div>
            <div class="meter-track-sm">
              <div class="meter-fill-sm ${getMeterColorClass(diskPct)}" style="width: ${Math.min(100, Math.max(0, diskPct))}%;"></div>
            </div>
          </div>
        `;
      } else {
        diskCell = '<span class="text-muted font-monospace">--</span>';
      }

      // Network cell
      let netCell;
      if (m && m.network && !isDown) {
        const rx = `${m.network.receive_rate_kbps} KB/s`;
        const tx = `${m.network.transmit_rate_kbps} KB/s`;
        netCell = `
          <div style="font-size: 0.76rem; font-family: ui-monospace, monospace;">
            <div class="text-info"><i class="bi bi-arrow-down-short"></i>${rx}</div>
            <div class="text-secondary"><i class="bi bi-arrow-up-short"></i>${tx}</div>
          </div>
        `;
      } else {
        netCell = '<span class="text-muted font-monospace">--</span>';
      }

      // Last Check
      const relativeCheck = formatRelativeTime(server.last_check_at);

      // Alert cell
      let alertCell;
      if (isDown) {
        alertCell = '<span class="badge bg-danger" title="SSH connection failed"><i class="bi bi-exclamation-octagon me-1"></i>Offline</span>';
      } else if (server.active_alerts_count > 0) {
        alertCell = `<span class="badge bg-warning text-dark"><i class="bi bi-bell-fill me-1"></i>${server.active_alerts_count} Active</span>`;
      } else {
        alertCell = '<span class="badge badge-soft-success"><i class="bi bi-shield-check me-1"></i>None</span>';
      }

      return `
        <tr class="${rowAttentionClass}" data-server-id="${server.id}">
          <td>
            <div class="fw-bold text-light">${escapeHtml(server.server_name)}</div>
            <div class="text-muted" style="font-size: 0.72rem;">
              ${getOsBadge(server.operating_system)} &bull; <span class="font-monospace">${escapeHtml(server.hostname)}</span>
            </div>
          </td>
          <td>${statusBadge}</td>
          <td>${cpuCell}</td>
          <td>${memCell}</td>
          <td>${diskCell}</td>
          <td>${netCell}</td>
          <td><span class="small font-monospace" title="${server.last_check_at || ''}">${relativeCheck}</span></td>
          <td>${alertCell}</td>
          <td class="text-end">
            <div class="btn-group btn-group-sm" role="group">
              <button class="btn btn-outline-primary btn-server-details" data-id="${server.id}" title="Inspect Server Telemetry">
                <i class="bi bi-eye-fill"></i>
              </button>
              <button class="btn btn-outline-secondary btn-server-test" data-id="${server.id}" title="Test SSH Connection">
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

    // Row Buttons Event Binding
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
            showToast(`Connected to ${res.hostname || 'server'} successfully.`, 'success');
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
            showToast('Metrics collected successfully!', 'success');
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

  // ================= RENDER LEVEL 4A: RESOURCE OVERVIEW WITH SPARKLINE CHARTS =================

  function renderResourceOverview(stats) {
    if (!stats) return;

    // CPU
    if (el.overviewCpuVal) el.overviewCpuVal.textContent = `${Number(stats.avg_cpu || 0).toFixed(1)}%`;
    if (el.overviewCpuStatus) {
      const cpu = stats.avg_cpu || 0;
      el.overviewCpuStatus.textContent = cpu >= 90 ? 'Critical' : cpu >= 70 ? 'Warning' : 'Healthy';
      el.overviewCpuStatus.className = `badge ${cpu >= 90 ? 'badge-soft-danger' : cpu >= 70 ? 'badge-soft-warning' : 'badge-soft-success'}`;
    }
    if (el.overviewCpuDelta) {
      updateDeltaBadgeEl(el.overviewCpuDelta, stats.avg_cpu_delta || 0, '%');
    }

    // Memory
    if (el.overviewMemVal) el.overviewMemVal.textContent = `${Number(stats.avg_memory || 0).toFixed(1)}%`;
    if (el.overviewMemStatus) {
      const mem = stats.avg_memory || 0;
      el.overviewMemStatus.textContent = mem >= 90 ? 'Critical' : mem >= 70 ? 'Warning' : 'Healthy';
      el.overviewMemStatus.className = `badge ${mem >= 90 ? 'badge-soft-danger' : mem >= 70 ? 'badge-soft-warning' : 'badge-soft-success'}`;
    }
    if (el.overviewMemDelta) {
      updateDeltaBadgeEl(el.overviewMemDelta, stats.avg_memory_delta || 0, '%');
    }

    // Disk
    if (el.overviewDiskVal) el.overviewDiskVal.textContent = `${Number(stats.avg_disk || 0).toFixed(1)}%`;
    if (el.overviewDiskStatus) {
      const disk = stats.avg_disk || 0;
      el.overviewDiskStatus.textContent = disk >= 90 ? 'Critical' : disk >= 80 ? 'Warning' : 'Healthy';
      el.overviewDiskStatus.className = `badge ${disk >= 90 ? 'badge-soft-danger' : disk >= 80 ? 'badge-soft-warning' : 'badge-soft-success'}`;
    }

    // Network
    if (el.overviewNetVal) {
      let rxRate = 0;
      let txRate = 0;
      if (state.servers.length > 0) {
        state.servers.forEach(s => {
          if (s.latest_metrics && s.latest_metrics.network) {
            rxRate += s.latest_metrics.network.receive_rate_kbps || 0;
            txRate += s.latest_metrics.network.transmit_rate_kbps || 0;
          }
        });
      }
      el.overviewNetVal.innerHTML = `
        <div class="font-monospace">↓ ${Number(rxRate).toFixed(1)} KB/s</div>
        <div class="font-monospace text-muted fs-6">↑ ${Number(txRate).toFixed(1)} KB/s</div>
      `;
    }

    // Render Sparklines
    renderSparklines(stats.resource_sparklines);
  }

  function renderSparklines(sparklinesData) {
    if (!window.Chart || !sparklinesData) return;

    const createMiniSparkline = (canvasId, key, dataArray, color) => {
      const canvas = document.getElementById(canvasId);
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const sparkTension = (state.chartModel === 'smooth') ? 0.35 : 0;
      const sparkStepped = (state.chartModel === 'stepped') ? 'middle' : false;

      if (state.sparklines[key]) {
        state.sparklines[key].data.labels = dataArray.map((_, i) => i);
        state.sparklines[key].data.datasets[0].data = dataArray;
        state.sparklines[key].data.datasets[0].tension = sparkTension;
        state.sparklines[key].data.datasets[0].stepped = sparkStepped;
        state.sparklines[key].update('none');
        return;
      }

      state.sparklines[key] = new Chart(ctx, {
        type: 'line',
        data: {
          labels: dataArray.map((_, i) => i),
          datasets: [{
            data: dataArray,
            borderColor: color,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 0,
            fill: true,
            backgroundColor: `${color}20`,
            tension: sparkTension,
            stepped: sparkStepped,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: {
            x: { display: false },
            y: { display: false, min: 0 },
          },
        },
      });
    };

    if (sparklinesData.cpu && sparklinesData.cpu.length > 0) {
      createMiniSparkline('sparkline-cpu', 'cpu', sparklinesData.cpu, '#6366f1');
    }
    if (sparklinesData.memory && sparklinesData.memory.length > 0) {
      createMiniSparkline('sparkline-memory', 'memory', sparklinesData.memory, '#10b981');
    }
    if (sparklinesData.disk && sparklinesData.disk.length > 0) {
      createMiniSparkline('sparkline-disk', 'disk', sparklinesData.disk, '#f59e0b');
    }
    if (sparklinesData.network && sparklinesData.network.length > 0) {
      createMiniSparkline('sparkline-network', 'network', sparklinesData.network, '#0ea5e9');
    }
  }

  // ================= RENDER LEVEL 4B: RESOURCE HEALTH HEATMAP (PHASE 10) =================

  function renderResourceHeatmap() {
    if (!el.heatmapTableBody) return;

    if (state.servers.length === 0) {
      el.heatmapTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No servers registered.</td></tr>';
      return;
    }

    const rowsHtml = state.servers.map(server => {
      const isDown = server.status === 'DOWN';
      const m = server.latest_metrics;

      const getChip = (pct, warnThreshold = 70, critThreshold = 90) => {
        if (isDown || typeof pct !== 'number') return '<span class="badge-heatmap-offline">--</span>';
        if (pct >= critThreshold) return `<span class="badge-heatmap-high">${pct}% High</span>`;
        if (pct >= warnThreshold) return `<span class="badge-heatmap-warn">${pct}% Warn</span>`;
        return `<span class="badge-heatmap-good">${pct}% Good</span>`;
      };

      const cpuChip = m && m.cpu ? getChip(m.cpu.usage_percent, 70, 90) : (isDown ? '<span class="badge-heatmap-offline">--</span>' : '<span class="badge-heatmap-offline">--</span>');
      const memChip = m && m.memory ? getChip(m.memory.usage_percent, 75, 90) : (isDown ? '<span class="badge-heatmap-offline">--</span>' : '<span class="badge-heatmap-offline">--</span>');
      const diskChip = m && m.disk ? getChip(m.disk.usage_percent, 80, 90) : (isDown ? '<span class="badge-heatmap-offline">--</span>' : '<span class="badge-heatmap-offline">--</span>');
      const netChip = isDown
        ? '<span class="badge-heatmap-offline">Offline</span>'
        : server.status === 'UP'
        ? '<span class="badge-heatmap-good">Good</span>'
        : '<span class="badge-heatmap-warn">Degraded</span>';

      return `
        <tr>
          <td>
            <span class="fw-bold">${escapeHtml(server.server_name)}</span>
            <span class="text-muted small font-monospace ms-1">(${escapeHtml(server.hostname)})</span>
          </td>
          <td class="text-center">${cpuChip}</td>
          <td class="text-center">${memChip}</td>
          <td class="text-center">${diskChip}</td>
          <td class="text-center">${netChip}</td>
        </tr>
      `;
    }).join('');

    el.heatmapTableBody.innerHTML = rowsHtml;
  }

  // ================= RENDER LEVEL 5: ALERT CENTER & ACTION CENTER =================

  function renderAlertCenter() {
    if (!el.alertsListContainer) return;

    let filtered = [...state.alerts];

    if (state.currentAlertFilter === 'ACTIVE') {
      filtered = filtered.filter(a => a.status === 'ACTIVE');
    } else if (state.currentAlertFilter === 'CRITICAL') {
      filtered = filtered.filter(a => a.severity === 'CRITICAL' && a.status === 'ACTIVE');
    } else if (state.currentAlertFilter === 'WARNING') {
      filtered = filtered.filter(a => a.severity === 'WARNING' && a.status === 'ACTIVE');
    } else if (state.currentAlertFilter === 'RESOLVED') {
      filtered = filtered.filter(a => a.status === 'RESOLVED');
    }

    if (filtered.length === 0) {
      el.alertsListContainer.innerHTML = '';
      if (el.alertsEmptyState) el.alertsEmptyState.classList.remove('d-none');
      return;
    }

    if (el.alertsEmptyState) el.alertsEmptyState.classList.add('d-none');

    const html = filtered.map(alert => {
      const isCritical = alert.severity === 'CRITICAL';
      const isWarning = alert.severity === 'WARNING';
      const severityClass = isCritical ? 'critical' : isWarning ? 'warning' : 'info';
      const severityBadge = isCritical
        ? '<span class="badge bg-danger">CRITICAL</span>'
        : isWarning
        ? '<span class="badge bg-warning text-dark">WARNING</span>'
        : '<span class="badge bg-info">INFO</span>';

      const resolveBtn = alert.status === 'ACTIVE'
        ? `<button class="btn btn-sm btn-outline-success btn-resolve-alert" data-id="${alert.id}">
             <i class="bi bi-check-lg me-1"></i> Resolve
           </button>`
        : `<span class="text-muted small"><i class="bi bi-check2-all text-success me-1"></i>Resolved</span>`;

      return `
        <div class="alert-item-card ${severityClass}" id="alert-card-${alert.id}">
          <div class="d-flex align-items-start gap-2 flex-grow-1">
            <div class="mt-1">${severityBadge}</div>
            <div>
              <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                <span class="fw-bold text-light">${escapeHtml(alert.title)}</span>
                <span class="badge badge-soft-info">${escapeHtml(alert.server_name)}</span>
              </div>
              <p class="text-muted small mb-1">${escapeHtml(alert.message || 'No additional diagnostic details.')}</p>
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

    el.alertsListContainer.innerHTML = html;

    el.alertsListContainer.querySelectorAll('.btn-resolve-alert').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.getAttribute('data-id'), 10);
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';

        try {
          await resolveAlert(id);
          showToast('Alert resolved.', 'success');
          await refreshAll(true);
        } catch (err) {
          showToast(`Error resolving: ${err.message}`, 'danger');
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Resolve';
        }
      });
    });
  }

  function renderActionCenter(tasks) {
    if (!el.actionTasksContainer) return;

    if (!tasks || tasks.length === 0) {
      el.actionTasksContainer.innerHTML = `
        <div class="p-3 text-center text-muted">
          <i class="bi bi-check-circle text-success fs-3 mb-1 d-block"></i>
          <span>No operational tasks pending. All infrastructure checks healthy.</span>
        </div>
      `;
      return;
    }

    const html = tasks.map(task => {
      const p = (task.priority || 'INFO').toUpperCase();
      const priorityClass = p === 'URGENT' ? 'priority-urgent' : p === 'HIGH' ? 'priority-high' : p === 'MEDIUM' ? 'priority-medium' : 'priority-info';
      const badgeClass = p === 'URGENT' ? 'bg-danger' : p === 'HIGH' ? 'bg-warning text-dark' : p === 'MEDIUM' ? 'bg-info' : 'bg-success';

      let actionBtn = '';
      if (task.action_type === 'test_ssh' && task.server_id) {
        actionBtn = `<button class="btn btn-sm btn-danger btn-task-action" data-action="test_ssh" data-server-id="${task.server_id}">
          <i class="bi bi-plug-fill me-1"></i> ${escapeHtml(task.action_label || 'Test SSH')}
        </button>`;
      } else if (task.action_type === 'view_details' && task.server_id) {
        actionBtn = `<button class="btn btn-sm btn-outline-warning btn-task-action" data-action="view_details" data-server-id="${task.server_id}">
          <i class="bi bi-eye-fill me-1"></i> ${escapeHtml(task.action_label || 'Inspect')}
        </button>`;
      } else if (task.action_type === 'collect_metrics' && task.server_id) {
        actionBtn = `<button class="btn btn-sm btn-outline-primary btn-task-action" data-action="collect_metrics" data-server-id="${task.server_id}">
          <i class="bi bi-arrow-repeat me-1"></i> ${escapeHtml(task.action_label || 'Collect')}
        </button>`;
      } else {
        actionBtn = `<span class="badge badge-soft-success font-monospace">${escapeHtml(task.action_label || 'Clear')}</span>`;
      }

      return `
        <div class="task-item-card ${priorityClass}">
          <div class="d-flex align-items-start gap-2 flex-grow-1">
            <span class="badge ${badgeClass} mt-1">${p}</span>
            <div>
              <div class="fw-bold text-light">${escapeHtml(task.title)}</div>
              <div class="text-muted small font-monospace">
                ${escapeHtml(task.server_name)} &bull; ${escapeHtml(task.hostname)}
              </div>
            </div>
          </div>
          <div class="ms-2">
            ${actionBtn}
          </div>
        </div>
      `;
    }).join('');

    el.actionTasksContainer.innerHTML = html;

    // Attach task action events
    el.actionTasksContainer.querySelectorAll('.btn-task-action').forEach(btn => {
      btn.addEventListener('click', async () => {
        const action = btn.getAttribute('data-action');
        const serverId = parseInt(btn.getAttribute('data-server-id'), 10);
        if (!serverId) return;

        if (action === 'view_details') {
          openServerDetailModal(serverId);
        } else if (action === 'test_ssh') {
          openServerDetailModal(serverId);
          if (el.btnModalTestSsh) el.btnModalTestSsh.click();
        } else if (action === 'collect_metrics') {
          btn.disabled = true;
          try {
            await collectServerMetricsNow(serverId);
            showToast('Metrics collected successfully.', 'success');
            await refreshAll(true);
          } catch (err) {
            showToast(`Collection failed: ${err.message}`, 'danger');
          } finally {
            btn.disabled = false;
          }
        }
      });
    });
  }

  // ================= RENDER LEVEL 6: MONITORING ENGINE STATUS =================

  function renderMonitoringEngine(engine) {
    if (!engine) return;

    if (el.engineServiceStatus) {
      el.engineServiceStatus.innerHTML = `<span class="status-dot online"></span> ${escapeHtml(engine.service_status || 'Running')}`;
    }
    if (el.engineSchedulerStatus) {
      el.engineSchedulerStatus.innerHTML = `<span class="status-dot online"></span> ${escapeHtml(engine.scheduler_status || 'Active')}`;
    }
    if (el.engineRunnerStatus) {
      const isHealthy = (engine.runner_status || '').toLowerCase() === 'healthy';
      el.engineRunnerStatus.innerHTML = `<span class="status-dot ${isHealthy ? 'online' : 'warning'}"></span> ${escapeHtml(engine.runner_status || 'Healthy')}`;
    }
    if (el.engineLastSuccess) {
      el.engineLastSuccess.textContent = engine.last_successful_run ? formatTimeOnly(engine.last_successful_run) : 'Never';
    }
    if (el.engineLastFail) {
      el.engineLastFail.textContent = engine.last_failed_run ? formatTimeOnly(engine.last_failed_run) : 'None';
      el.engineLastFail.className = engine.last_failed_run ? 'engine-value font-monospace small text-danger' : 'engine-value font-monospace small text-muted';
    }
    if (el.engineLastCheck) {
      el.engineLastCheck.textContent = engine.last_check ? formatTimeOnly(engine.last_check) : '--:--:--';
    }
    if (el.engineNextRefresh) {
      el.engineNextRefresh.textContent = `${state.countdownSeconds}s`;
    }
  }

  // ================= RENDER LEVEL 7: HISTORICAL METRICS =================

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

  function createChartOptions(theme, unit = '%', bounds = null) {
    let yMin = 0;
    let yMax = undefined;
    let decimals = 0;

    if (bounds) {
      yMin = (bounds.min !== undefined) ? bounds.min : 0;
      yMax = bounds.max;
      decimals = bounds.decimals || 0;
    }

    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 250 },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { color: theme.textColor, boxWidth: 12, font: { size: 11 } },
        },
        tooltip: {
          backgroundColor: theme.tooltipBg,
          titleColor: theme.tooltipText,
          bodyColor: theme.tooltipText,
          borderColor: theme.tooltipBorder,
          borderWidth: 1,
          padding: 8,
          callbacks: {
            label: function(ctx) {
              const val = ctx.parsed.y;
              return ` ${ctx.dataset.label}: ${Number(val).toFixed(decimals > 0 ? decimals : 2)}${unit}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: theme.gridColor },
          ticks: { color: theme.textColor, maxRotation: 0, autoSkip: true, maxTicksLimit: 6, font: { size: 10 } },
        },
        y: {
          min: yMin,
          max: yMax,
          grid: { color: theme.gridColor },
          ticks: {
            color: theme.textColor,
            font: { size: 10 },
            callback: (v) => `${Number(v).toFixed(decimals)}${unit}`,
          },
        },
      },
    };
  }

  async function updateHistoricalCharts() {
    if (!state.selectedServerId) return;

    try {
      const data = await fetchServerMetrics(state.selectedServerId, state.selectedRange);
      renderChartsData(data);
    } catch (err) {
      console.warn('Error updating historical charts:', err);
    }
  }

  function renderChartsData(data) {
    if (!window.Chart || !data) return;
    const theme = getChartThemeColors();

    const formattedLabels = (data.labels || []).map(l => {
      const d = new Date(l);
      if (isNaN(d.getTime())) return l;
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    });

    const s = data.summary || {};

    // Update Badges
    if (s.cpu) {
      if (el.statCpuCurrent) el.statCpuCurrent.innerHTML = `Cur: <strong>${s.cpu.current}%</strong>`;
      if (el.statCpuAvg) el.statCpuAvg.innerHTML = `Avg: <strong>${s.cpu.avg}%</strong>`;
      if (el.statCpuPeak) el.statCpuPeak.innerHTML = `Peak: <strong>${s.cpu.peak}%</strong>`;
    }
    if (s.memory) {
      if (el.statMemCurrent) el.statMemCurrent.innerHTML = `Cur: <strong>${s.memory.current}%</strong>`;
      if (el.statMemAvg) el.statMemAvg.innerHTML = `Avg: <strong>${s.memory.avg}%</strong>`;
      if (el.statMemPeak) el.statMemPeak.innerHTML = `Peak: <strong>${s.memory.peak}%</strong>`;
    }
    if (s.disk) {
      if (el.statDiskCurrent) el.statDiskCurrent.innerHTML = `Cur: <strong>${s.disk.current}%</strong>`;
      if (el.statDiskAvg) el.statDiskAvg.innerHTML = `Avg: <strong>${s.disk.avg}%</strong>`;
      if (el.statDiskPeak) el.statDiskPeak.innerHTML = `Peak: <strong>${s.disk.peak}%</strong>`;
    }
    if (s.network_rx) {
      if (el.statNetCurrent) el.statNetCurrent.innerHTML = `Cur: <strong>${s.network_rx.current} KB/s</strong>`;
      if (el.statNetAvg) el.statNetAvg.innerHTML = `Avg: <strong>${s.network_rx.avg} KB/s</strong>`;
      if (el.statNetPeak) el.statNetPeak.innerHTML = `Peak: <strong>${s.network_rx.peak} KB/s</strong>`;
    }

    // Chart Model Configuration: Zigzag (sharp point-to-point) / Smooth / Stepped
    const chartModel = state.chartModel || 'zigzag';
    const isZigzag = (chartModel === 'zigzag');
    const isStepped = (chartModel === 'stepped');

    const tension = isZigzag ? 0 : (isStepped ? 0 : 0.35);
    const stepped = isStepped ? 'middle' : false;
    const pointRadius = isZigzag
      ? ((data.cpu || []).length > 60 ? 2.5 : 4)
      : (isStepped ? 0 : ((data.cpu || []).length > 60 ? 2 : 3));
    const pointHoverRadius = isZigzag ? 6 : 5;

    // Calculate adaptive bounds if state.chartScaleMode === 'dynamic'
    const isDynamic = (state.chartScaleMode === 'dynamic');

    // CPU Bounds
    let cpuBounds = { min: 0, max: 100, decimals: 0 };
    if (isDynamic) {
      const cpuVals = [...(data.cpu || []), ...(data.load_1m || [])].filter(v => typeof v === 'number' && !isNaN(v));
      const peakCpu = cpuVals.length > 0 ? Math.max(...cpuVals) : 0;
      if (peakCpu <= 1.0) {
        cpuBounds = { min: 0, max: 1.0, decimals: 1 };
      } else if (peakCpu <= 5.0) {
        cpuBounds = { min: 0, max: Math.max(1, Math.ceil(peakCpu * 1.3 * 10) / 10), decimals: 1 };
      } else if (peakCpu <= 25.0) {
        cpuBounds = { min: 0, max: Math.min(100, Math.ceil(peakCpu * 1.25 / 5) * 5), decimals: 0 };
      } else {
        cpuBounds = { min: 0, max: Math.min(100, Math.ceil(peakCpu * 1.15 / 10) * 10), decimals: 0 };
      }
    }

    // Memory Bounds
    let memBounds = { min: 0, max: 100, decimals: 0 };
    if (isDynamic) {
      const memVals = (data.memory || []).filter(v => typeof v === 'number' && !isNaN(v));
      if (memVals.length > 0) {
        const minMem = Math.min(...memVals);
        const maxMem = Math.max(...memVals);
        const delta = maxMem - minMem;
        if (delta < 5) {
          const yMin = Math.max(0, Math.floor(minMem - 2));
          const yMax = Math.min(100, Math.ceil(maxMem + 2));
          memBounds = { min: yMin, max: yMax, decimals: 1 };
        } else if (maxMem <= 40) {
          memBounds = { min: 0, max: Math.min(100, Math.ceil(maxMem * 1.25 / 5) * 5), decimals: 0 };
        } else {
          memBounds = { min: 0, max: Math.min(100, Math.ceil(maxMem * 1.15 / 10) * 10), decimals: 0 };
        }
      }
    }

    // Disk Bounds
    let diskBounds = { min: 0, max: 100, decimals: 0 };
    if (isDynamic) {
      const diskVals = (data.disk || []).filter(v => typeof v === 'number' && !isNaN(v));
      if (diskVals.length > 0) {
        const maxDisk = Math.max(...diskVals);
        if (maxDisk <= 5) {
          diskBounds = { min: 0, max: 10, decimals: 0 };
        } else if (maxDisk <= 50) {
          diskBounds = { min: 0, max: Math.ceil(maxDisk * 1.25 / 5) * 5, decimals: 0 };
        }
      }
    }

    // Network Bounds
    const netVals = [...(data.network_rx || []), ...(data.network_tx || [])].filter(v => typeof v === 'number' && !isNaN(v));
    const maxNet = netVals.length > 0 ? Math.max(...netVals) : 0;
    const netBounds = {
      min: 0,
      max: maxNet > 0 ? Math.ceil(maxNet * 1.25 * 10) / 10 : 2,
      decimals: 1,
    };

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
              tension: tension,
              stepped: stepped,
              fill: true,
              pointRadius: pointRadius,
              pointHoverRadius: pointHoverRadius,
            },
            {
              label: '1m Load Average',
              data: data.load_1m || [],
              borderColor: '#f59e0b',
              borderDash: [4, 4],
              borderWidth: 1.5,
              tension: tension,
              stepped: stepped,
              fill: false,
              pointRadius: isZigzag ? 2.5 : 0,
              pointHoverRadius: isZigzag ? 4 : 0,
            },
          ],
        },
        options: createChartOptions(theme, '%', cpuBounds),
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
          datasets: [{
            label: 'Memory Usage (%)',
            data: data.memory || [],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            borderWidth: 2,
            tension: tension,
            stepped: stepped,
            fill: true,
            pointRadius: pointRadius,
            pointHoverRadius: pointHoverRadius,
          }],
        },
        options: createChartOptions(theme, '%', memBounds),
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
          datasets: [{
            label: 'Disk Usage (%)',
            data: data.disk || [],
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.15)',
            borderWidth: 2,
            tension: tension,
            stepped: stepped,
            fill: true,
            pointRadius: pointRadius,
            pointHoverRadius: pointHoverRadius,
          }],
        },
        options: createChartOptions(theme, '%', diskBounds),
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
              label: 'RX (KB/s)',
              data: data.network_rx || [],
              borderColor: '#0ea5e9',
              backgroundColor: 'rgba(14, 165, 233, 0.15)',
              borderWidth: 2,
              tension: tension,
              stepped: stepped,
              fill: true,
              pointRadius: pointRadius,
              pointHoverRadius: pointHoverRadius,
            },
            {
              label: 'TX (KB/s)',
              data: data.network_tx || [],
              borderColor: '#8b5cf6',
              borderWidth: 1.5,
              borderDash: [3, 3],
              tension: tension,
              stepped: stepped,
              fill: false,
              pointRadius: isZigzag ? 2.5 : 0,
              pointHoverRadius: isZigzag ? 4 : 0,
            },
          ],
        },
        options: createChartOptions(theme, ' KB/s', netBounds),
      });
    }
  }

  // ================= RENDER LEVEL 8: RECENT ACTIVITY =================

  function renderRecentActivity(recentActivity = null) {
    if (!el.activityTableBody) return;

    const activityList = (recentActivity && recentActivity.length > 0)
      ? recentActivity
      : (state.stats && state.stats.recent_activity && state.stats.recent_activity.length > 0)
        ? state.stats.recent_activity
        : null;

    if (!activityList || activityList.length === 0) {
      el.activityTableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">No monitoring activity recorded yet.</td></tr>';
      return;
    }

    const rows = activityList.map(item => {
      const isUp = item.status === 'UP';
      const resultBadge = isUp
        ? '<span class="badge badge-soft-success font-monospace"><i class="bi bi-check2-circle me-1"></i>200 OK</span>'
        : `<span class="badge badge-soft-danger font-monospace" title="${escapeHtml(item.result || 'Failed')}"><i class="bi bi-x-circle me-1"></i>Failed</span>`;

      const d = item.timestamp ? new Date(item.timestamp) : null;
      const timeStr = d && !isNaN(d.getTime())
        ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : 'Recently';

      const cpuDeltaPill = renderDeltaPill(item.cpu_delta || 0, '%');
      const memDeltaPill = renderDeltaPill(item.mem_delta || 0, '%');

      return `
        <tr>
          <td class="font-monospace small"><strong>${timeStr}</strong></td>
          <td class="fw-bold">
            ${escapeHtml(item.server_name)}
            <span class="text-muted small font-monospace">(${escapeHtml(item.hostname)})</span>
          </td>
          <td>${isUp ? '<span class="status-dot online me-1"></span> Online' : '<span class="status-dot offline me-1"></span> Offline'}</td>
          <td class="font-monospace small">
            <span class="text-info">CPU: ${item.cpu_usage}%</span> | 
            <span class="text-success">RAM: ${item.memory_usage}%</span> | 
            <span class="text-warning">Disk: ${item.disk_usage}%</span>
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
      el.modalSshOutput.textContent = 'Click "Test SSH Connection" to verify server connectivity via paramiko.';
    }

    if (window.bootstrap && el.modalEl) {
      const modal = bootstrap.Modal.getOrCreateInstance(el.modalEl);
      modal.show();
    }
  }

  // ================= REFRESH ORCHESTRATION (EXACT 10 SECONDS - PHASE 17 & 18) =================

  async function refreshAll(silent = false) {
    if (state.isFetching) return;
    state.isFetching = true;

    if (!silent && el.refreshIcon) {
      el.refreshIcon.classList.add('spin-icon');
    }
    if (el.refreshStatusBadge) {
      el.refreshStatusBadge.className = 'badge badge-soft-warning font-monospace';
      el.refreshStatusBadge.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Updating...';
    }

    try {
      const [stats, servers, alerts] = await Promise.all([
        fetchDashboardStats(),
        fetchServers(),
        fetchAlerts(),
      ]);

      if (el.errorBanner) el.errorBanner.classList.add('d-none');

      state.stats = stats;
      state.servers = servers;
      state.alerts = alerts;

      renderSystemHealthBar(stats);
      renderKpis(stats);
      renderServerHealthMatrix();
      renderResourceOverview(stats);
      renderResourceHeatmap();
      renderAlertCenter();
      renderActionCenter(stats.tasks);
      renderMonitoringEngine(stats.monitoring_engine);
      populateServerSelect();
      renderRecentActivity(stats.recent_activity);
      await updateHistoricalCharts();

      if (el.refreshStatusBadge) {
        el.refreshStatusBadge.className = 'badge badge-soft-success font-monospace';
        el.refreshStatusBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Live';
      }

    } catch (err) {
      console.error('Failed to refresh dashboard:', err);
      if (el.errorBanner) {
        el.errorBanner.classList.remove('d-none');
        if (el.errorMessage) {
          el.errorMessage.textContent = `Update failed (${err.message}). Using last known telemetry.`;
        }
      }
      if (el.refreshStatusBadge) {
        el.refreshStatusBadge.className = 'badge badge-soft-danger font-monospace';
        el.refreshStatusBadge.innerHTML = '<i class="bi bi-exclamation-triangle-fill me-1"></i> Offline';
      }
    } finally {
      state.isFetching = false;
      if (el.refreshIcon) el.refreshIcon.classList.remove('spin-icon');
      if (el.refreshBtn) el.refreshBtn.disabled = false;
    }
  }

  function startCountdown() {
    stopCountdown();
    state.countdownSeconds = Math.round(state.autoRefreshInterval / 1000);
    if (el.countdownSec) el.countdownSec.textContent = state.countdownSeconds;

    state.countdownTimer = setInterval(() => {
      state.countdownSeconds -= 1;

      if (state.countdownSeconds <= 0) {
        state.countdownSeconds = Math.round(state.autoRefreshInterval / 1000);
        if (el.countdownSec) el.countdownSec.textContent = state.countdownSeconds;
        refreshAll(true);
      } else {
        if (el.countdownSec) el.countdownSec.textContent = state.countdownSeconds;
      }

      if (el.engineNextRefresh) {
        el.engineNextRefresh.textContent = `${state.countdownSeconds}s`;
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

    updateHistoricalCharts();
  }

  // ================= EVENT LISTENERS =================

  if (el.themeToggleBtn) {
    el.themeToggleBtn.addEventListener('click', () => {
      applyTheme(state.theme === 'dark' ? 'light' : 'dark');
    });
  }

  // Manual Refresh Button
  if (el.refreshBtn) {
    el.refreshBtn.addEventListener('click', () => {
      state.countdownSeconds = Math.round(state.autoRefreshInterval / 1000);
      if (el.countdownSec) el.countdownSec.textContent = state.countdownSeconds;
      refreshAll(false);
      showToast('Refreshing telemetry...', 'info');
    });
  }

  // Server Filters
  document.querySelectorAll('[data-server-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-server-filter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentServerFilter = btn.getAttribute('data-server-filter');
      renderServerHealthMatrix();
    });
  });

  // Server Search
  if (el.serverSearchInput) {
    let debounceTimer = null;
    el.serverSearchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        state.searchQuery = e.target.value;
        renderServerHealthMatrix();
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
      renderServerHealthMatrix();
    });
  }

  // Chart Server Select
  if (el.chartServerSelect) {
    el.chartServerSelect.addEventListener('change', (e) => {
      state.selectedServerId = parseInt(e.target.value, 10);
      updateHistoricalCharts();
    });
  }

  // Time Range Buttons
  document.querySelectorAll('[data-range]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-range]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.selectedRange = btn.getAttribute('data-range');
      updateHistoricalCharts();
    });
  });

  // Chart Model Buttons (Zigzag / Smooth / Stepped)
  const modelBtns = document.querySelectorAll('#chart-model-group [data-chart-model]');
  modelBtns.forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-chart-model') === state.chartModel);
    btn.addEventListener('click', () => {
      const model = btn.getAttribute('data-chart-model');
      state.chartModel = model;
      localStorage.setItem('dash_chart_model', model);
      modelBtns.forEach(b => b.classList.toggle('active', b.getAttribute('data-chart-model') === model));
      updateHistoricalCharts();
      if (state.stats && state.stats.resource_sparklines) {
        renderSparklines(state.stats.resource_sparklines);
      }
    });
  });

  // Chart Scale Toggle (Dynamic vs Fixed 0-100%)
  function updateScaleToggleButton() {
    if (!el.btnChartScaleToggle) return;
    const isDyn = (state.chartScaleMode === 'dynamic');
    if (el.chartScaleLabel) {
      el.chartScaleLabel.textContent = isDyn ? 'Dynamic Scale' : '0-100% Scale';
    }
    if (el.chartScaleIcon) {
      el.chartScaleIcon.className = isDyn ? 'bi bi-arrows-expand text-info' : 'bi bi-arrows-collapse text-muted';
    }
    el.btnChartScaleToggle.classList.toggle('active-dynamic', isDyn);
  }

  if (el.btnChartScaleToggle) {
    updateScaleToggleButton();
    el.btnChartScaleToggle.addEventListener('click', () => {
      state.chartScaleMode = (state.chartScaleMode === 'dynamic') ? 'fixed' : 'dynamic';
      localStorage.setItem('dash_chart_scale', state.chartScaleMode);
      updateScaleToggleButton();
      updateHistoricalCharts();
    });
  }

  // Quick Collect Sample Button in Historical Header
  if (el.btnChartCollectSample) {
    el.btnChartCollectSample.addEventListener('click', async () => {
      if (!state.selectedServerId) {
        showToast('Please select a server first.', 'warning');
        return;
      }
      const origHtml = el.btnChartCollectSample.innerHTML;
      el.btnChartCollectSample.disabled = true;
      el.btnChartCollectSample.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Sampling...';

      try {
        const res = await collectServerMetricsNow(state.selectedServerId);
        if (res.success) {
          showToast('Sample collected! Telemetry updated.', 'success');
          await updateHistoricalCharts();
          await refreshAll(true);
        } else {
          showToast(`Sampling failed: ${res.message}`, 'danger');
        }
      } catch (err) {
        showToast(`Sampling error: ${err.message}`, 'danger');
      } finally {
        el.btnChartCollectSample.disabled = false;
        el.btnChartCollectSample.innerHTML = origHtml;
      }
    });
  }

  // Alert Filters
  document.querySelectorAll('[data-alert-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-alert-filter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentAlertFilter = btn.getAttribute('data-alert-filter');
      renderAlertCenter();
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

  // Clean up on page unload
  window.addEventListener('beforeunload', () => {
    stopCountdown();
  });

  // Initialize Dashboard Application
  applyTheme(state.theme);
  refreshAll(false);
  startCountdown();
});
