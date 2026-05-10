import { state } from './state.js';
import { gallery, modal, zipFilenameInput, zipBtn, modalProgress, downloadBtn } from './dom.js';
import { archiveRequest, deleteFilesRequest, applyMoveRequest, fetchDirTree } from './api.js';
import { showModal, hideModal, showInfo } from './modal.js';
import { fetchAndPopulateTagFilter, initTagModal } from './tags.js';

// ─── Selection Helpers ─────────────────────────────────────

export function getSelectedImages() {
    return Array.from(document.querySelectorAll('.gallery .image-container.selected'))
        .map(container => {
            const img = container.querySelector('img');
            const video = container.querySelector('video');
            const audio = container.querySelector('audio');
            return img ? img.alt : video ? video.dataset.filename : audio ? audio.dataset.filename : null;
        })
        .filter(Boolean);
}

// ─── Static Frame Reload ───────────────────────────────────

export function reloadStaticFrames() {
    const timestamp = Date.now();
    document.querySelectorAll('.gallery img').forEach(img => {
        const currentSrc = img.src;
        if (currentSrc.includes('/static-frame/')) {
            img.src = `${currentSrc.split('?')[0]}?bust=${timestamp}`;
        } else if (img.dataset.static) {
            const baseUrl = img.dataset.static.split('?')[0];
            img.src = `${baseUrl}?bust=${timestamp}`;
            img.dataset.static = `${baseUrl}?bust=${timestamp}`;
        }
    });
}

// ─── Delete ────────────────────────────────────────────────

export async function deleteFiles(files) {
    const response = await deleteFilesRequest(files, state.currentDir);
    const result = await response.json();
    if (result.success) {
        result.deleted.forEach(filename => {
            const imgContainer = Array.from(gallery.children).find(container => {
                const img = container.querySelector('img');
                const video = container.querySelector('video');
                const audio = container.querySelector('audio');
                return (img && img.alt === filename) || (video && video.dataset.filename === filename) || (audio && audio.dataset.filename === filename);
            });
            if (imgContainer) gallery.removeChild(imgContainer);
        });
        showInfo('Deletion Complete', result.message);
    } else {
        showInfo('Deletion Error', `Error deleting files: ${result.message}`);
    }
}

// ─── Zip ───────────────────────────────────────────────────

export function initZipHandler() {
    zipBtn.addEventListener('click', async () => {
        const filename = zipFilenameInput.value.trim();
        if (!filename) { showInfo('Invalid Filename', 'Please enter a filename.'); return; }

        showModal('zipProgressStep');
        const selectedFiles = getSelectedImages();

        const response = await archiveRequest(filename, selectedFiles, state.currentDir);
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                showModal('zipDownloadStep');
                downloadBtn.onclick = () => {
                    window.location.href = `/download/${result.filename}`;
                    hideModal();
                };
            } else {
                modalProgress.innerText = `Error: ${result.message}`;
            }
        } else {
            const error = await response.json();
            modalProgress.innerText = `Error ${response.status}: ${error.message || 'An error occurred'}`;
        }
    });
}

// ─── Move ──────────────────────────────────────────────────

export async function openMoveModal(selectedFiles) {
    state.moveTargetDir = null;
    state.moveTargetSubpath = null;

    document.getElementById('move-info').innerText =
        `${selectedFiles.length} file${selectedFiles.length === 1 ? '' : 's'} selected`;
    document.getElementById('move-apply-btn').disabled = true;

    showModal('moveStep');

    const moveTree = document.getElementById('move-tree');
    moveTree.innerHTML = '<div class="move-tree-loading">Loading...</div>';

    let galleryTree, uploadsTree;
    try {
        [galleryTree, uploadsTree] = await Promise.all([
            fetchDirTree('gallery'),
            fetchDirTree('uploads'),
        ]);
    } catch (err) {
        moveTree.innerHTML = '<div class="move-tree-loading">Failed to load directories.</div>';
        return;
    }

    moveTree.innerHTML = '';
    renderMoveTreeSection(moveTree, 'Gallery', 'gallery', galleryTree);
    renderMoveTreeSection(moveTree, 'Uploads', 'uploads', uploadsTree);

    document.getElementById('move-apply-btn').onclick = () => applyMove(selectedFiles);
}

function renderMoveTreeSection(container, label, dir, tree) {
    const section = document.createElement('div');
    section.className = 'move-tree-section';

    const heading = document.createElement('div');
    heading.className = 'move-dir-section-header';
    heading.textContent = label;
    section.appendChild(heading);

    section.appendChild(createMoveRow('/', dir, '', 0));

    function appendChildren(parentEl, nodes, depth) {
        nodes.forEach(node => {
            parentEl.appendChild(createMoveRow(node.name + '/', dir, node.path, depth));
            if (node.children && node.children.length > 0) {
                appendChildren(parentEl, node.children, depth + 1);
            }
        });
    }
    appendChildren(section, tree, 1);

    container.appendChild(section);
}

function createMoveRow(label, dir, subpath, depth) {
    const row = document.createElement('div');
    row.className = 'move-dir-item';
    row.style.paddingLeft = `${0.5 + depth * 1.2}em`;

    const icon = document.createElement('i');
    icon.className = 'fas fa-folder';
    icon.style.marginRight = '0.4em';
    row.appendChild(icon);

    const text = document.createElement('span');
    text.textContent = label;
    row.appendChild(text);

    row.addEventListener('click', () => {
        document.querySelectorAll('.move-dir-item.move-selected').forEach(el => {
            el.classList.remove('move-selected');
            el.querySelector('i').className = 'fas fa-folder';
        });
        row.classList.add('move-selected');
        icon.className = 'fas fa-folder-open';
        state.moveTargetDir = dir;
        state.moveTargetSubpath = subpath;
        document.getElementById('move-apply-btn').disabled = false;
    });

    return row;
}

async function applyMove(selectedFiles) {
    if (!state.moveTargetDir) return;
    document.getElementById('move-apply-btn').disabled = true;

    const response = await applyMoveRequest(
        selectedFiles,
        state.currentDir,
        state.moveTargetDir,
        state.moveTargetSubpath
    );
    const result = await response.json();

    if (result.moved && result.moved.length > 0) {
        result.moved.forEach(filename => {
            const imgContainer = Array.from(gallery.children).find(container => {
                const img = container.querySelector('img');
                const video = container.querySelector('video');
                const audio = container.querySelector('audio');
                return (img && img.alt === filename) || (video && video.dataset.filename === filename) || (audio && audio.dataset.filename === filename);
            });
            if (imgContainer) gallery.removeChild(imgContainer);

            const cacheKey = `${state.currentDir}/${filename}`;
            delete state.metadataCache[cacheKey];
            delete state.fileMetadataCache[cacheKey];
        });

        delete state.dirTreeCache[state.currentDir];
        delete state.dirTreeCache[state.moveTargetDir];
    }

    hideModal();

    if (result.errors && result.errors.length > 0) {
        const movedMsg = result.moved.length > 0 ? `Moved ${result.moved.length} file(s).<br>` : '';
        showInfo('Move Errors', movedMsg + result.errors.map(e => `<div>${e}</div>`).join(''));
    }
}

// ─── Toolbar Listener ──────────────────────────────────────

export function initToolbar(zipFilenameInputEl) {
    document.getElementById('toolbar').addEventListener('click', e => {
        if (e.target.closest('#reload-btn')) {
            reloadStaticFrames();
        } else if (e.target.closest('#select-all-btn')) {
            document.querySelectorAll('.gallery .image-container').forEach(container => {
                const checkbox = container.querySelector('.checkbox');
                checkbox.checked = true;
                container.classList.add('selected');
            });
        } else if (e.target.closest('#clear-selection-btn')) {
            document.querySelectorAll('.gallery .image-container').forEach(container => {
                const checkbox = container.querySelector('.checkbox');
                checkbox.checked = false;
                container.classList.remove('selected');
            });
        } else if (e.target.closest('#tag-selected-btn')) {
            const selectedFiles = getSelectedImages();
            if (selectedFiles.length === 0) { showInfo("Can't Tag Selected", 'No files selected.'); return; }
            document.getElementById('tag-info').innerText =
                `${selectedFiles.length} file${selectedFiles.length === 1 ? '' : 's'} selected`;
            showModal('tagStep');
            initTagModal(selectedFiles);
        } else if (e.target.closest('#move-selected-btn')) {
            const selectedFiles = getSelectedImages();
            if (selectedFiles.length === 0) { showInfo("Can't Move Selected", 'No files selected.'); return; }
            openMoveModal(selectedFiles);
        } else if (e.target.closest('#zip-selected-btn')) {
            const selectedFiles = getSelectedImages();
            if (selectedFiles.length === 0) { showInfo("Can't Zip Selected", 'No files selected.'); return; }
            document.getElementById('zip-info').innerText = `${selectedFiles.length} files selected`;
            zipFilenameInputEl.value = `Gallery_${new Date().toISOString().split('T')[0]}.zip`;
            showModal('zipFilenameStep');
        } else if (e.target.closest('#delete-selected-btn')) {
            const selectedFiles = getSelectedImages();
            if (selectedFiles.length === 0) { showInfo("Can't Delete Selected", 'No files selected.'); return; }
            document.getElementById('delete-info').innerText = `${selectedFiles.length} files selected`;
            showModal('deleteConfirmation');
            document.getElementById('delete-btn').onclick = async () => {
                hideModal();
                await deleteFiles(selectedFiles);
            };
        }
    });
}
