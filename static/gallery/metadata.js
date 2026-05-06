import { state } from './state.js';
import { lightbox, lightboxMetadataPanel, lightboxMetadataContent, toggleMetadataBtn } from './dom.js';
import { fetchMetadataRequest } from './api.js';
import { escapeHtml } from './utils.js';

export async function fetchMetadata(filename, dir) {
    const cacheKey = `${dir}/${filename}`;
    if (state.metadataCache[cacheKey]) return state.metadataCache[cacheKey];
    return fetchMetadataRequest(filename, dir);
}

export function toggleMetadataPanel() {
    const isVisible = lightboxMetadataPanel.style.display !== 'none';
    if (isVisible) {
        closeMetadataPanel();
    } else {
        lightboxMetadataPanel.style.display = 'flex';
        lightbox.classList.add('with-metadata');
        toggleMetadataBtn.title = 'Hide Metadata';
        if (state.currentLightboxFile && state.currentLightboxDir) {
            lightboxMetadataContent.innerHTML = '<div class="metadata-loading">Loading metadata...</div>';
            fetchMetadata(state.currentLightboxFile, state.currentLightboxDir).then(displayMetadata);
        }
    }
}

export function closeMetadataPanel() {
    lightboxMetadataPanel.style.display = 'none';
    lightbox.classList.remove('with-metadata');
    toggleMetadataBtn.title = 'Show Metadata';
}

export function displayMetadata(metadata) {
    if (!metadata) {
        lightboxMetadataContent.innerHTML = '<div class="metadata-error">Failed to load metadata</div>';
        return;
    }

    let html = '';
    const workflowSections = [];
    const otherSections = [];

    for (const [k, v] of Object.entries(metadata)) {
        if (k.startsWith('🔧') || k.startsWith('⚙️')) workflowSections.push([k, v]);
        else otherSections.push([k, v]);
    }

    for (const [k, v] of workflowSections) {
        html += `<div class="metadata-section collapsible collapsed">`;
        html += `<div class="metadata-section-title collapsible-header" onclick="this.parentElement.classList.toggle('collapsed')">${k} <span class="collapse-icon">▼</span></div>`;
        html += `<div class="collapsible-content">`;
        html +=
            typeof v === 'object' && v !== null && !Array.isArray(v)
                ? `<div class="metadata-json">${formatJsonValue(v)}</div>`
                : `<div class="metadata-value">${formatMetadataValue(v)}</div>`;
        html += `</div></div>`;
    }

    for (const [k, v] of otherSections) {
        const cleanKey = k.replace(/^_/, '');
        const displayKey = cleanKey.charAt(0).toUpperCase() + cleanKey.slice(1);
        if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
            html += `<div class="metadata-section collapsible collapsed">`;
            html += `<div class="metadata-section-title collapsible-header" onclick="this.parentElement.classList.toggle('collapsed')">${displayKey} <span class="collapse-icon">▼</span></div>`;
            html += `<div class="collapsible-content"><div class="metadata-table">`;
            for (const [key, value] of Object.entries(v)) {
                html += `<div class="metadata-row"><div class="metadata-key">${escapeHtml(key)}</div><div class="metadata-value">${formatMetadataValue(value)}</div></div>`;
            }
            html += `</div></div></div>`;
        }
    }

    lightboxMetadataContent.innerHTML = html || '<div class="metadata-error">No metadata found</div>';
}

function formatJsonValue(obj) {
    try {
        return `<pre class="json-display">${escapeHtml(JSON.stringify(obj, null, 2))}</pre>`;
    } catch {
        return `<pre>${escapeHtml(String(obj))}</pre>`;
    }
}

function formatMetadataValue(value) {
    if (typeof value === 'object' && value !== null) return formatJsonValue(value);
    const str = String(value);
    return str.length > 100 ? `<pre>${escapeHtml(str)}</pre>` : escapeHtml(str);
}
