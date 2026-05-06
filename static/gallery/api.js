import { state } from './state.js';

export async function addTagRequest(dir, filename, tag) {
    try {
        const response = await fetch('/tag', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dir, filename, tag }),
        });
        const data = await response.json();
        if (data.success) {
            const cacheKey = `${dir}/${filename}`;
            if (state.fileMetadataCache[cacheKey]) {
                state.fileMetadataCache[cacheKey].tags = data.tags;
            }
            return data.tags;
        }
        return null;
    } catch (err) {
        console.error('Error adding tag:', err);
        return null;
    }
}

export async function removeTagRequest(dir, filename, tag) {
    try {
        const response = await fetch('/untag', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dir, filename, tag }),
        });
        const data = await response.json();
        if (data.success) {
            const cacheKey = `${dir}/${filename}`;
            if (state.fileMetadataCache[cacheKey]) {
                state.fileMetadataCache[cacheKey].tags = data.tags;
            }
            return data.tags;
        }
        return null;
    } catch (err) {
        console.error('Error removing tag:', err);
        return null;
    }
}

export async function setRatingRequest(dir, filename, rating) {
    try {
        const response = await fetch('/rate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dir, filename, rating }),
        });
        const data = await response.json();
        if (data.success) {
            const cacheKey = `${dir}/${filename}`;
            if (state.fileMetadataCache[cacheKey]) {
                state.fileMetadataCache[cacheKey].rating = rating;
            }
            return true;
        }
        console.error('Failed to set rating:', data.message);
        return false;
    } catch (err) {
        console.error('Error setting rating:', err);
        return false;
    }
}

export async function fetchMetadataRequest(filename, dir) {
    try {
        const response = await fetch(`/metadata/${dir}/${filename}`);
        const data = await response.json();
        if (data.success) {
            state.metadataCache[`${dir}/${filename}`] = data.metadata;
            return data.metadata;
        }
        console.error('Metadata fetch failed:', data.message);
        return null;
    } catch (err) {
        console.error('Error fetching metadata:', err);
        return null;
    }
}

export async function fetchTagsRequest(dir, subpath, tagFilter = new Set()) {
    const tagParam = tagFilter.size > 0 ? `&tag_filter=${[...tagFilter].join(',')}` : '';
    const response = await fetch(`/tags?dir=${dir}&subpath=${encodeURIComponent(subpath)}${tagParam}`);
    if (!response.ok) return null;
    return response.json();
}

export async function fetchExtensionsRequest(dir, subpath) {
    const response = await fetch(`/extensions?dir=${dir}&subpath=${encodeURIComponent(subpath)}`);
    if (!response.ok) return null;
    return response.json();
}

export async function uploadFilesRequest(formData) {
    return fetch('/upload', { method: 'POST', body: formData });
}

export async function deleteFilesRequest(files, directory) {
    return fetch('/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files, directory }),
    });
}

export async function applyMoveRequest(files, sourceDir, targetDir, targetSubpath) {
    return fetch('/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            files,
            source_dir: sourceDir,
            target_dir: targetDir,
            target_subpath: targetSubpath || '',
        }),
    });
}

export async function fetchDirTree(dir) {
    if (state.dirTreeCache[dir]) return state.dirTreeCache[dir];
    const res = await fetch(`/dirs?dir=${dir}`);
    if (!res.ok) throw new Error(`Failed to fetch ${dir} tree`);
    const data = await res.json();
    state.dirTreeCache[dir] = data.tree;
    return data.tree;
}

export async function fetchArchivesRequest(sortByVal, sortDirVal) {
    return fetch(`/archives?sort_by=${sortByVal}&sort_dir=${sortDirVal}`);
}

export async function archiveRequest(filename, files, directory) {
    return fetch('/archive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, files, directory }),
    });
}

export async function extractArchiveRequest(filename) {
    return fetch('/archive/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
    });
}

export async function mkdirRequest(dir, subdir, name) {
    return fetch('/mkdir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dir, subdir, name }),
    });
}

export async function fetchImagesRequest(params) {
    const { dir, page, sortBy, sortDir, subpath, ratingFilter, tagFilter, extFilter } = params;
    const tagParam = tagFilter.size > 0 ? `&tag_filter=${[...tagFilter].join(',')}` : '';
    const extParam = extFilter ? `&ext_filter=${encodeURIComponent(extFilter)}` : '';
    return fetch(
        `/images?dir=${dir}&page=${page}&sort_by=${sortBy}&sort_dir=${sortDir}&subpath=${encodeURIComponent(subpath)}&rating_filter=${ratingFilter}${tagParam}${extParam}`,
        { signal: state.fetchController?.signal }
    );
}
