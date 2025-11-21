/**
 * O-RAN RIC Beam KPI Query Dashboard
 * Author: 蔡秀吉 (thc1006)
 * Date: 2025-11-19
 */

// Configuration
const CONFIG = {
    API_BASE_URL: '',  // Empty = same origin (proxy handles routing)
    AUTO_REFRESH_INTERVAL: 0, // Set to 0 to disable auto-refresh, or 5000 for 5 seconds
    DEFAULT_BEAM_ID: 5
};

// State
let currentBeamID = CONFIG.DEFAULT_BEAM_ID;
let autoRefreshTimer = null;

// DOM Elements
const queryForm = document.getElementById('queryForm');
const beamSelect = document.getElementById('beamSelect');
const kpiTypeSelect = document.getElementById('kpiTypeSelect');
const timeRange = document.getElementById('timeRange');
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
const resultsContainer = document.getElementById('resultsContainer');
const kpiTableBody = document.getElementById('kpiTableBody');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Beam KPI Query Dashboard initialized');

    // Set default beam
    beamSelect.value = CONFIG.DEFAULT_BEAM_ID;

    // Event listeners
    queryForm.addEventListener('submit', handleQuery);

    // Auto-query on load
    queryBeamKPI(CONFIG.DEFAULT_BEAM_ID, 'all');
});

/**
 * Handle form submission
 */
function handleQuery(event) {
    event.preventDefault();

    const beamID = parseInt(beamSelect.value);
    const kpiType = kpiTypeSelect.value;

    queryBeamKPI(beamID, kpiType);
}

/**
 * Query Beam KPI from API
 */
async function queryBeamKPI(beamID, kpiType = 'all') {
    currentBeamID = beamID;

    // Show loading
    showLoading();

    try {
        const url = `${CONFIG.API_BASE_URL}/api/beam/${beamID}/kpi?kpi_type=${kpiType}`;
        console.log(`📡 Querying: ${url}`);

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            displayResults(data);
        } else {
            showError(`Query failed: ${data.message || 'Unknown error'}`);
        }

    } catch (error) {
        console.error('❌ Query error:', error);
        showError(`Failed to query Beam ${beamID}: ${error.message}`);
    }
}

/**
 * Display query results
 */
function displayResults(data) {
    hideLoading();
    hideError();

    // Show results container
    resultsContainer.style.display = 'block';

    // Update quick stats
    updateQuickStats(data.data);

    // Update table
    updateKPITable(data.data);

    // Update metadata
    updateMetadata(data);

    console.log('✅ Results displayed successfully');
}

/**
 * Update quick stats cards
 */
function updateQuickStats(kpiData) {
    const signalQuality = kpiData.signal_quality || {};
    const throughput = kpiData.throughput || {};

    // RSRP
    if (signalQuality.rsrp) {
        document.getElementById('statRSRP').textContent = signalQuality.rsrp.value.toFixed(1);
        document.getElementById('badgeRSRP').textContent = signalQuality.rsrp.quality || 'N/A';
        document.getElementById('badgeRSRP').className = `badge ${getQualityBadgeClass(signalQuality.rsrp.quality)}`;
    }

    // SINR
    if (signalQuality.sinr) {
        document.getElementById('statSINR').textContent = signalQuality.sinr.value.toFixed(1);
        document.getElementById('badgeSINR').textContent = signalQuality.sinr.quality || 'N/A';
        document.getElementById('badgeSINR').className = `badge ${getQualityBadgeClass(signalQuality.sinr.quality)}`;
    }

    // Downlink Throughput
    if (throughput.downlink) {
        document.getElementById('statDL').textContent = throughput.downlink.value.toFixed(1);
    }

    // Uplink Throughput
    if (throughput.uplink) {
        document.getElementById('statUL').textContent = throughput.uplink.value.toFixed(1);
    }
}

/**
 * Update KPI table
 */
function updateKPITable(kpiData) {
    kpiTableBody.innerHTML = '';

    const categories = {
        'signal_quality': 'Signal Quality',
        'throughput': 'Throughput',
        'packet_loss': 'Packet Loss',
        'resource_utilization': 'Resource Utilization'
    };

    for (const [category, categoryLabel] of Object.entries(categories)) {
        if (kpiData[category]) {
            const metrics = kpiData[category];

            for (const [metricName, metricData] of Object.entries(metrics)) {
                const row = document.createElement('tr');

                row.innerHTML = `
                    <td>${categoryLabel}</td>
                    <td>${formatMetricName(metricName)}</td>
                    <td><strong>${metricData.value?.toFixed(2) || 'N/A'}</strong></td>
                    <td>${metricData.unit || ''}</td>
                    <td>${metricData.quality ? `<span class="badge ${getQualityBadgeClass(metricData.quality)}">${metricData.quality}</span>` : 'N/A'}</td>
                    <td><small>${metricData.timestamp ? formatTimestamp(metricData.timestamp) : 'N/A'}</small></td>
                `;

                kpiTableBody.appendChild(row);
            }
        }
    }
}

/**
 * Update metadata section
 */
function updateMetadata(data) {
    const metadata = data.data.metadata || {};

    document.getElementById('metaBeamID').textContent = metadata.beam_id !== undefined ? metadata.beam_id : data.beam_id;
    document.getElementById('metaCellID').textContent = metadata.cell_id || 'N/A';
    document.getElementById('metaUECount').textContent = metadata.ue_count || '0';
    document.getElementById('metaQueryTime').textContent = data.timestamp ? formatTimestamp(data.timestamp) : new Date().toLocaleString();
}

/**
 * Format metric name for display
 */
function formatMetricName(name) {
    const nameMap = {
        'rsrp': 'RSRP',
        'rsrq': 'RSRQ',
        'sinr': 'SINR',
        'downlink': 'Downlink',
        'uplink': 'Uplink',
        'prb_usage_dl': 'PRB Usage (DL)',
        'prb_usage_ul': 'PRB Usage (UL)'
    };

    return nameMap[name] || name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Format timestamp
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

/**
 * Get badge class for quality
 */
function getQualityBadgeClass(quality) {
    if (!quality) return 'badge-secondary';

    const qualityLower = quality.toLowerCase();

    if (qualityLower === 'excellent' || qualityLower === 'good') {
        return 'badge-success';
    } else if (qualityLower === 'fair') {
        return 'badge-warning';
    } else if (qualityLower === 'poor') {
        return 'badge-error';
    } else {
        return 'badge-info';
    }
}

/**
 * Show loading state
 */
function showLoading() {
    loadingState.style.display = 'flex';
    resultsContainer.style.display = 'none';
    errorState.style.display = 'none';
}

/**
 * Hide loading state
 */
function hideLoading() {
    loadingState.style.display = 'none';
}

/**
 * Show error
 */
function showError(message) {
    hideLoading();
    resultsContainer.style.display = 'none';
    errorState.style.display = 'block';
    errorMessage.textContent = message;
}

/**
 * Hide error
 */
function hideError() {
    errorState.style.display = 'none';
}

/**
 * Auto refresh (if enabled)
 */
if (CONFIG.AUTO_REFRESH_INTERVAL > 0) {
    autoRefreshTimer = setInterval(() => {
        const beamID = parseInt(beamSelect.value);
        const kpiType = kpiTypeSelect.value;
        console.log(`🔄 Auto-refreshing Beam ${beamID}...`);
        queryBeamKPI(beamID, kpiType);
    }, CONFIG.AUTO_REFRESH_INTERVAL);
}

// Cleanup on unload
window.addEventListener('beforeunload', () => {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
    }
});
