import { state } from './state.js';
import {
    gallery, archivesContainer, mainHeadingName, currentPathEl,
    galleryBtn, uploadsBtn, archivesBtn, dropArea, loadingText,
    sortBy, sortDir, ratingFilter, extFilter, dirPanel, dirList, dirBreadcrumb,
} from './dom.js';
import { fetchImagesRequest, fetchDirTree, mkdirRequest } from './api.js';
import { getSortLabel } from './utils.js';
import { createImageElement, createVideoElement, createAudioElement } from './gallery-items.js';

// Injected by main.js via initNavigation — avoids a circular dependency with tags.js
let onAfterNavigate = () => {};

export function initNavigation({ onAfterNavigate: fn }) {
    onAfterNavigate = fn;
}

// ─── Gallery Loading ───────────────────────────────────────

export async function loadMore() {
    if (state.loading || state.done) return;
    state.loading = true;
    loadingText.style.display = 'block';

    if (state.fetchController) state.fetchController.abort();
    state.fetchController = new AbortController();

    try {
        const response = await fetchImagesRequest({
            dir: state.currentDir,
            page: state.page,
            sortBy: sortBy.value,
            sortDir: sortDir.value,
            subpath: state.currentSubpath,
            ratingFilter: ratingFilter.value,
            tagFilter: state.selectedTags,
            extFilter: extFilter.value,
        });
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();

        if (data.files.length === 0) {
            loadingText.innerText = 'No more files.';
            state.done = true;
            return;
        }

        data.files.forEach(file => {
            const fileName = file.name;
            const fileExt = fileName.split('.').pop().toLowerCase();
            const isMp4 = fileExt === 'mp4';
            const isWebP = fileExt === 'webp';
            const isMp3 = fileExt === 'mp3';
            const filePath = isWebP
                ? `/static-frame/${state.currentDir}/${fileName}`
                : `/${state.currentDir}/${fileName}`;
            const animatedPath = isWebP ? `/${state.currentDir}/${fileName}` : null;
            const fileDuration = (isWebP || isMp4 || isMp3) ? file.duration_seconds : null;

            state.fileMetadataCache[`${state.currentDir}/${fileName}`] = file;

            const sortValue = getSortLabel(sortBy.value, file);
            const rating = file.rating || 0;
            const tags = file.tags || [];

            const container = isMp4
                ? createVideoElement(fileName, sortValue, fileDuration, rating, tags)
                : isMp3
                    ? createAudioElement(fileName, sortValue, fileDuration, rating, tags)
                    : createImageElement(fileName, filePath, isWebP, animatedPath, sortValue, fileDuration, rating, tags);

            container.dataset.sortDate = new Date(file.last_modified).toISOString();
            container.dataset.sortFilename = fileName.toLowerCase();
            container.dataset.sortSize = file.size_bytes || 0;
            gallery.appendChild(container);
        });

        state.page++;
        loadingText.style.display = 'none';

        if (document.body.scrollHeight <= window.innerHeight && !state.done) {
            loadMore();
        }
    } catch (err) {
        if (err.name !== 'AbortError') {
            loadingText.innerText = 'Failed to load files.';
            console.error('loadMore error:', err);
        }
    } finally {
        state.loading = false;
    }
}

export function reloadGallery() {
    state.page = 0;
    state.done = false;
    gallery.innerHTML = '';
    loadMore();
}

export function updateActiveFolderButton(dir) {
    galleryBtn.classList.toggle('active', dir === 'gallery');
    uploadsBtn.classList.toggle('active', dir === 'uploads');
    archivesBtn.classList.toggle('active', dir === 'archives');
}

export function switchDirectory(dir) {
    if (state.fetchController) state.fetchController.abort();
    state.currentDir = dir;
    state.currentSubpath = dir === 'gallery' ? state.lastGallerySubpath : state.lastUploadsSubpath;
    state.page = 0;
    state.done = false;
    state.loading = false;
    gallery.innerHTML = '';
    archivesContainer.style.display = 'none';
    gallery.style.display = 'grid';
    dropArea.style.display = dir === 'uploads' ? 'block' : 'none';
    ratingFilter.value = 'all';
    state.selectedTags.clear();
    extFilter.value = '';

    loadMore();
    onAfterNavigate();

    mainHeadingName.innerHTML = dir === 'gallery' ? 'Gallery' : 'Uploads';
    if (state.currentSubpath) {
        currentPathEl.textContent = state.currentSubpath;
        currentPathEl.style.display = 'block';
    } else {
        currentPathEl.style.display = 'none';
        currentPathEl.textContent = '';
    }

    updateActiveFolderButton(dir);
}

// ─── Directory Tree ────────────────────────────────────────

function renderTreeNode(node, depth, navDir) {
    const item = document.createElement('div');

    const row = document.createElement('div');
    row.className =
        'dir-item' + (node.path === state.currentSubpath && navDir === state.currentDir ? ' active' : '');
    row.style.paddingLeft = `${0.4 + depth * 1.2}em`;

    if (node.children && node.children.length > 0) {
        const toggle = document.createElement('i');
        toggle.className = 'fas fa-chevron-down tree-toggle';
        toggle.addEventListener('click', e => {
            e.stopPropagation();
            const childrenEl = item.querySelector(':scope > .tree-children');
            const collapsed = childrenEl.style.display === 'none';
            childrenEl.style.display = collapsed ? '' : 'none';
            toggle.className = (collapsed ? 'fas fa-chevron-down' : 'fas fa-chevron-right') + ' tree-toggle';
        });
        row.appendChild(toggle);
    } else {
        const spacer = document.createElement('span');
        spacer.className = 'tree-toggle-spacer';
        row.appendChild(spacer);
    }

    const icon = document.createElement('i');
    icon.className =
        node.path === state.currentSubpath && navDir === state.currentDir
            ? 'fas fa-folder-open'
            : 'fas fa-folder';
    icon.style.marginRight = '0.4em';
    row.appendChild(icon);

    const label = document.createElement('span');
    label.textContent = node.name + '/';
    row.appendChild(label);

    row.addEventListener('click', () => navigateSubdir(node.path, navDir));
    item.appendChild(row);

    if (node.children && node.children.length > 0) {
        const childrenEl = document.createElement('div');
        childrenEl.className = 'tree-children';
        node.children.forEach(child => childrenEl.appendChild(renderTreeNode(child, depth + 1, navDir)));
        item.appendChild(childrenEl);
    }

    return item;
}

// ─── New Folder Controls ───────────────────────────────────

const newDirBtn = document.createElement('button');
newDirBtn.id = 'new-dir-btn';
newDirBtn.innerHTML = `<i class="fas fa-folder-plus"></i>`;

const newDirLabel = document.createElement('span');
newDirLabel.id = 'new-dir-label';
newDirLabel.textContent = 'New Folder';

const newDirInput = document.createElement('input');
newDirInput.type = 'text';
newDirInput.id = 'new-dir-input';
newDirInput.placeholder = 'Folder name';

newDirBtn.addEventListener('click', e => {
    e.stopPropagation();
    newDirInput.classList.remove('error');
    newDirInput.value = '';
    newDirLabel.style.display = 'none';
    newDirInput.style.display = 'block';
    newDirInput.focus();
});

async function submitNewDir() {
    const name = newDirInput.value.trim();
    if (!name) {
        newDirInput.style.display = 'none';
        newDirLabel.style.display = '';
        newDirInput.classList.remove('error');
        return;
    }
    const parentSubdir = state.panelDir === state.currentDir ? state.currentSubpath : '';
    try {
        const response = await mkdirRequest(state.panelDir, parentSubdir, name);
        if (response.ok) {
            newDirInput.style.display = 'none';
            newDirLabel.style.display = '';
            newDirInput.classList.remove('error');
            delete state.dirTreeCache[state.panelDir];
            const res = await fetchDirTree(state.panelDir);
            state.dirTreeCache[state.panelDir] = res;
            renderDirTree(state.panelDir);
        } else {
            newDirInput.classList.add('error');
            newDirInput.focus();
        }
    } catch (err) {
        console.error('Failed to create directory:', err);
        newDirInput.classList.add('error');
        newDirInput.focus();
    }
}

newDirInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); submitNewDir(); }
    if (e.key === 'Escape') {
        newDirInput.style.display = 'none';
        newDirLabel.style.display = '';
        newDirInput.classList.remove('error');
    }
});
newDirInput.addEventListener('blur', submitNewDir);

// ─── Tree Rendering ────────────────────────────────────────

export function renderDirTree(dir) {
    dirBreadcrumb.textContent = '';
    dirBreadcrumb.style.display = 'none';
    dirList.innerHTML = '';

    const rootRow = document.createElement('div');
    rootRow.className = 'dir-item' + (dir !== state.currentDir || state.currentSubpath === '' ? ' active' : '');
    rootRow.style.paddingLeft = '0.4em';

    const rootSpacer = document.createElement('span');
    rootSpacer.className = 'tree-toggle-spacer';
    rootRow.appendChild(rootSpacer);

    const rootIcon = document.createElement('i');
    rootIcon.className =
        state.currentSubpath === '' && dir === state.currentDir ? 'fas fa-folder-open' : 'fas fa-folder';
    rootIcon.style.marginRight = '0.4em';
    rootRow.appendChild(rootIcon);

    const rootLabel = document.createElement('span');
    rootLabel.textContent = '/';
    rootRow.appendChild(rootLabel);

    rootRow.addEventListener('click', () => navigateSubdir('', dir));
    dirList.appendChild(rootRow);

    const tree = state.dirTreeCache[dir];
    if (tree && tree.length > 0) {
        tree.forEach(node => dirList.appendChild(renderTreeNode(node, 1, dir)));
    } else if (tree) {
        const empty = document.createElement('div');
        empty.className = 'dir-empty';
        empty.textContent = 'No subdirectories';
        dirList.appendChild(empty);
    }

    const effectiveSubpath = dir === state.currentDir ? state.currentSubpath : '';
    const depth = effectiveSubpath ? effectiveSubpath.split('/').length : 0;
    const addRow = document.createElement('div');
    addRow.className = 'new-dir-row';
    addRow.style.paddingLeft = `${0.4 + (depth + 1) * 1.2}em`;

    const addSpacer = document.createElement('span');
    addSpacer.className = 'tree-toggle-spacer';
    addRow.appendChild(addSpacer);
    addRow.appendChild(newDirBtn);
    addRow.appendChild(newDirLabel);
    addRow.appendChild(newDirInput);

    const activeItem = dirList.querySelector('.dir-item.active');
    if (!activeItem || effectiveSubpath === '') {
        dirList.appendChild(addRow);
    } else {
        const itemWrapper = activeItem.parentElement;
        let childrenEl = itemWrapper.querySelector(':scope > .tree-children');
        if (!childrenEl) {
            childrenEl = document.createElement('div');
            childrenEl.className = 'tree-children';
            itemWrapper.appendChild(childrenEl);
        }
        childrenEl.appendChild(addRow);
    }
}

// ─── Directory Panel ───────────────────────────────────────

export async function showDirPanel(dir, triggerBtn) {
    if (dir === 'archives') return;
    state.panelDir = dir;
    if (!state.dirTreeCache[dir]) {
        try {
            state.dirTreeCache[dir] = await fetchDirTree(dir);
        } catch (err) {
            console.error('Failed to load directory tree:', err);
            return;
        }
    }
    renderDirTree(dir);
    const rect = triggerBtn.getBoundingClientRect();
    dirPanel.style.left = rect.right + 8 + 'px';
    dirPanel.style.top = rect.bottom + 4 + 'px';
    dirPanel.style.display = 'block';
    if (state.activeDirBtn && state.activeDirBtn !== triggerBtn) {
        state.activeDirBtn.classList.remove('tooltip-active');
    }
    state.activeDirBtn = triggerBtn;
    triggerBtn.classList.add('tooltip-active');
}

export function scheduleDirPanelHide() {
    state.dirPanelHideTimer = setTimeout(() => {
        dirPanel.style.display = 'none';
        if (state.activeDirBtn) {
            state.activeDirBtn.classList.remove('tooltip-active');
            state.activeDirBtn = null;
        }
    }, 200);
}

export function cancelDirPanelHide() {
    if (state.dirPanelHideTimer) {
        clearTimeout(state.dirPanelHideTimer);
        state.dirPanelHideTimer = null;
    }
}

// ─── Subdirectory Navigation ───────────────────────────────

export function navigateSubdir(subpath, navDir = state.currentDir) {
    if (navDir !== state.currentDir) {
        if (state.fetchController) state.fetchController.abort();
        state.currentDir = navDir;
        archivesContainer.style.display = 'none';
        gallery.style.display = 'grid';
        dropArea.style.display = navDir === 'uploads' ? 'block' : 'none';
        updateActiveFolderButton(navDir);
        ratingFilter.value = 'all';
        state.selectedTags.clear();
        extFilter.value = '';
    }

    state.currentSubpath = subpath;
    if (navDir === 'gallery') state.lastGallerySubpath = subpath;
    else if (navDir === 'uploads') state.lastUploadsSubpath = subpath;

    state.page = 0;
    state.done = false;
    state.loading = false;
    gallery.innerHTML = '';

    mainHeadingName.innerHTML = navDir === 'gallery' ? 'Gallery' : 'Uploads';
    if (subpath) {
        currentPathEl.textContent = subpath;
        currentPathEl.style.display = 'block';
    } else {
        currentPathEl.textContent = '';
        currentPathEl.style.display = 'none';
    }

    renderDirTree(navDir);
    loadMore();
    onAfterNavigate();
}
