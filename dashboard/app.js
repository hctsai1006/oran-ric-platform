/**
 * O-RAN RIC Platform Dashboard - Application Logic
 * Version: 1.0.0
 */

const CONFIG = {
    API_BASE_URL: '/api',
    GRAFANA_URL: 'http://192.168.10.65:30030',
    BEAM_UI_URL: 'http://192.168.10.65:30888',
    REFRESH_INTERVAL: 30000, // 30 seconds
};

let refreshTimer = null;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    loadOverview();
    setupAutoRefresh();
});

// Navigation
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabId = this.getAttribute('data-tab');
            switchTab(tabId);

            // Update active state
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function switchTab(tabId) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show selected tab
    const activeTab = document.getElementById(tabId);
    if (activeTab) {
        activeTab.classList.add('active');
    }

    // Update page title and breadcrumb
    const titles = {
        'overview': 'Platform Overview',
        'monitoring': 'Monitoring Dashboard',
        'beam-kpi': 'Beam KPI Query',
        'xapps': 'xApps Management',
        'logs': 'Logs Viewer',
        'platform': 'Platform Resources'
    };

    document.getElementById('page-title').textContent = titles[tabId] || 'Dashboard';
    document.getElementById('breadcrumb-current').textContent = titles[tabId] || 'Dashboard';

    // Load tab-specific content
    if (tabId === 'overview') {
        loadOverview();
    } else if (tabId === 'monitoring') {
        loadGrafana();
    } else if (tabId === 'xapps') {
        refreshXapps();
    } else if (tabId === 'logs') {
        loadPodsList();
    } else if (tabId === 'platform') {
        loadPlatformInfo();
    }
}

// Overview Tab
async function loadOverview() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/platform/status`);
        const data = await response.json();

        // Update stats
        document.getElementById('stat-platform-pods').textContent = data.platformPods || 0;
        document.getElementById('stat-xapps').textContent = data.xappPods || 0;
        document.getElementById('stat-services').textContent = data.services || 0;
        document.getElementById('stat-uptime').textContent = data.uptime || '--';

        // Update components list
        displayComponents(data.components || []);
    } catch (error) {
        console.error('Error loading overview:', error);
        displayMockData();
    }
}

function displayComponents(components) {
    const container = document.getElementById('components-list');

    if (!components.length) {
        container.innerHTML = '<p class="text-muted text-center">No components data available</p>';
        return;
    }

    const html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Component</th>
                    <th>Namespace</th>
                    <th>Status</th>
                    <th>Restarts</th>
                    <th>Age</th>
                </tr>
            </thead>
            <tbody>
                ${components.map(comp => `
                    <tr>
                        <td><strong>${comp.name}</strong></td>
                        <td>${comp.namespace}</td>
                        <td><span class="status-badge status-${comp.status.toLowerCase()}">${comp.status}</span></td>
                        <td>${comp.restarts || 0}</td>
                        <td>${comp.age || '--'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

function displayMockData() {
    // Display mock data for demo
    const mockComponents = [
        { name: 'DBaaS', namespace: 'ricplt', status: 'Running', restarts: 0, age: '25m' },
        { name: 'E2Term', namespace: 'ricplt', status: 'Running', restarts: 0, age: '23m' },
        { name: 'SubMgr', namespace: 'ricplt', status: 'Running', restarts: 0, age: '23m' },
        { name: 'RTMgr', namespace: 'ricplt', status: 'Running', restarts: 5, age: '23m' },
        { name: 'KPIMON', namespace: 'ricxapp', status: 'Running', restarts: 0, age: '25m' },
        { name: 'E2 Simulator', namespace: 'ricxapp', status: 'Running', restarts: 0, age: '15m' },
        { name: 'Beam Query UI', namespace: 'ricxapp', status: 'Running', restarts: 0, age: '14m' },
    ];

    document.getElementById('stat-platform-pods').textContent = '15';
    document.getElementById('stat-xapps').textContent = '3';
    document.getElementById('stat-services').textContent = '24';
    document.getElementById('stat-uptime').textContent = '25m';

    displayComponents(mockComponents);
}

function refreshOverview() {
    document.getElementById('components-list').innerHTML = '<div class="spinner-container"><div class="spinner-border text-primary" role="status"></div></div>';
    loadOverview();
}

// Monitoring Tab
function loadGrafana() {
    const iframe = document.getElementById('grafana-frame');
    if (iframe.src === 'about:blank') {
        iframe.src = CONFIG.GRAFANA_URL;
    }
}

// xApps Tab
async function refreshXapps() {
    const container = document.getElementById('xapps-list');
    container.innerHTML = '<div class="spinner-container"><div class="spinner-border text-primary" role="status"></div></div>';

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/xapps`);
        const xapps = await response.json();

        displayXapps(xapps);
    } catch (error) {
        console.error('Error loading xApps:', error);
        displayMockXapps();
    }
}

function displayXapps(xapps) {
    const container = document.getElementById('xapps-list');

    const html = `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>xApp Name</th>
                    <th>Status</th>
                    <th>Image</th>
                    <th>Restarts</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${xapps.map(xapp => `
                    <tr>
                        <td><strong>${xapp.name}</strong></td>
                        <td><span class="status-badge status-${xapp.status.toLowerCase()}">${xapp.status}</span></td>
                        <td><small>${xapp.image}</small></td>
                        <td>${xapp.restarts}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" onclick="restartXapp('${xapp.name}')">
                                <span class="material-icons" style="font-size: 14px;">refresh</span>
                                Restart
                            </button>
                            <button class="btn btn-sm btn-outline-info" onclick="viewXappLogs('${xapp.name}')">
                                <span class="material-icons" style="font-size: 14px;">description</span>
                                Logs
                            </button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

function displayMockXapps() {
    const mockXapps = [
        { name: 'kpimon', status: 'Running', image: 'localhost:5000/xapp-kpimon:1.0.1', restarts: 0 },
        { name: 'e2-simulator', status: 'Running', image: 'localhost:5000/e2-simulator:1.0.0', restarts: 0 },
        { name: 'beam-query-ui', status: 'Running', image: 'localhost:5000/beam-query-ui:1.0.0', restarts: 0 },
    ];

    displayXapps(mockXapps);
}

async function restartXapp(name) {
    if (!confirm(`Are you sure you want to restart ${name}?`)) {
        return;
    }

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/xapps/${name}/restart`, {
            method: 'POST'
        });

        if (response.ok) {
            alert(`${name} restart initiated`);
            refreshXapps();
        } else {
            alert(`Failed to restart ${name}`);
        }
    } catch (error) {
        console.error('Error restarting xApp:', error);
        alert('Error: ' + error.message);
    }
}

function viewXappLogs(name) {
    switchTab('logs');
    document.getElementById('log-namespace').value = 'ricxapp';
    loadPodsList();
    setTimeout(() => {
        const podSelect = document.getElementById('log-pod');
        for (let option of podSelect.options) {
            if (option.text.includes(name)) {
                option.selected = true;
                viewLogs();
                break;
            }
        }
    }, 1000);
}

// Logs Tab
async function loadPodsList() {
    const namespace = document.getElementById('log-namespace').value;
    const podSelect = document.getElementById('log-pod');

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/pods?namespace=${namespace}`);
        const pods = await response.json();

        podSelect.innerHTML = '<option value="">Select Pod...</option>';
        pods.forEach(pod => {
            const option = document.createElement('option');
            option.value = pod.name;
            option.textContent = pod.name;
            podSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading pods:', error);
        // Mock data
        podSelect.innerHTML = `
            <option value="">Select Pod...</option>
            <option value="kpimon-54486974b6-rxq2x">kpimon-54486974b6-rxq2x</option>
            <option value="e2-simulator-54f6cfd7b4-cl8kq">e2-simulator-54f6cfd7b4-cl8kq</option>
            <option value="beam-query-ui-646b9d55c5-nvgdj">beam-query-ui-646b9d55c5-nvgdj</option>
        `;
    }
}

async function viewLogs() {
    const namespace = document.getElementById('log-namespace').value;
    const pod = document.getElementById('log-pod').value;
    const logsContent = document.getElementById('logs-content');

    if (!pod) {
        logsContent.textContent = 'Please select a pod';
        return;
    }

    logsContent.textContent = 'Loading logs...';

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/logs?namespace=${namespace}&pod=${pod}`);
        const logs = await response.text();

        logsContent.textContent = logs || 'No logs available';
    } catch (error) {
        console.error('Error loading logs:', error);
        logsContent.textContent = `Error loading logs: ${error.message}\n\nMock logs:\n[2025-11-21 01:10:00] INFO: Application started\n[2025-11-21 01:10:05] INFO: Connected to database\n[2025-11-21 01:10:10] INFO: Service ready`;
    }
}

// Platform Tab
async function loadPlatformInfo() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/platform/info`);
        const data = await response.json();

        displayNamespaces(data.namespaces || []);
        displayHelmReleases(data.releases || []);
    } catch (error) {
        console.error('Error loading platform info:', error);
        displayMockPlatformInfo();
    }
}

function displayNamespaces(namespaces) {
    const html = `
        <ul class="list-group">
            ${namespaces.map(ns => `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    ${ns.name}
                    <span class="badge bg-primary rounded-pill">${ns.podCount} pods</span>
                </li>
            `).join('')}
        </ul>
    `;
    document.getElementById('namespaces-list').innerHTML = html;
}

function displayHelmReleases(releases) {
    const html = `
        <ul class="list-group">
            ${releases.map(rel => `
                <li class="list-group-item">
                    <strong>${rel.name}</strong><br>
                    <small class="text-muted">Chart: ${rel.chart} | Status: ${rel.status}</small>
                </li>
            `).join('')}
        </ul>
    `;
    document.getElementById('helm-releases').innerHTML = html;
}

function displayMockPlatformInfo() {
    const mockNamespaces = [
        { name: 'ricplt', podCount: 15 },
        { name: 'ricxapp', podCount: 3 },
        { name: 'kube-system', podCount: 8 },
    ];

    const mockReleases = [
        { name: 'r4-dbaas', chart: 'dbaas-2.0.0', status: 'deployed' },
        { name: 'r4-e2term', chart: 'e2term-3.0.0', status: 'deployed' },
        { name: 'r4-submgr', chart: 'submgr-3.0.0', status: 'deployed' },
        { name: 'r4-rtmgr', chart: 'rtmgr-3.0.0', status: 'deployed' },
        { name: 'oran-grafana', chart: 'grafana-10.1.5', status: 'deployed' },
    ];

    displayNamespaces(mockNamespaces);
    displayHelmReleases(mockReleases);
}

// Auto-refresh
function setupAutoRefresh() {
    document.getElementById('log-namespace').addEventListener('change', loadPodsList);

    refreshTimer = setInterval(() => {
        const activeTab = document.querySelector('.tab-content.active');
        if (activeTab && activeTab.id === 'overview') {
            loadOverview();
        }
    }, CONFIG.REFRESH_INTERVAL);
}

// Cleanup
window.addEventListener('beforeunload', () => {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
});
