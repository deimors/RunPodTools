import { gallery, sortBy, sortDir } from './dom.js';

export function debounce(func, delay) {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
    };
}

export function formatFileSize(size) {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
    if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(2)} MB`;
    return `${(size / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export function getSortLabel(sortKey, file) {
    if (sortKey === 'date') {
        const ts = file.last_modified || (file.lastModified ? new Date(file.lastModified).toISOString() : null);
        return ts ? new Date(ts).toLocaleString() : new Date().toLocaleString();
    }
    if (sortKey === 'filename') return file.name;
    if (sortKey === 'size') return formatFileSize(file.size_bytes || file.size || 0);
    return null;
}

export function insertSorted(container) {
    const sortKey = sortBy.value;
    const dir = sortDir.value;

    function getSortValue(c) {
        if (sortKey === 'date') return c.dataset.sortDate || '';
        if (sortKey === 'filename') return c.dataset.sortFilename || '';
        return Number(c.dataset.sortSize) || 0;
    }

    const newVal = getSortValue(container);
    const containers = Array.from(gallery.children);

    let insertBefore = null;
    for (const existing of containers) {
        const existingVal = getSortValue(existing);
        const insertBeforeThis = dir === 'asc' ? newVal < existingVal : newVal > existingVal;
        if (insertBeforeThis) {
            insertBefore = existing;
            break;
        }
    }

    if (insertBefore) {
        gallery.insertBefore(container, insertBefore);
    } else {
        gallery.appendChild(container);
    }
}
