import { state } from './state.js';
import {
    galleryBtn, uploadsBtn, archivesBtn, modal, sortBy, sortDir,
    ratingFilter, extFilter, tagFilterBtn, tagFilterDropdown, dirPanel,
    zipFilenameInput,
} from './dom.js';
import { hideModal, showInfo } from './modal.js';
import { fetchAndPopulateTagFilter, fetchAndPopulateExtFilter, updateTagFilterLabel, initTagFilter } from './tags.js';
import {
    loadMore, reloadGallery, switchDirectory, navigateSubdir,
    showDirPanel, scheduleDirPanelHide, cancelDirPanelHide,
    initNavigation,
} from './navigation.js';
import { populateArchives, reloadArchives } from './archives.js';
import { initLightbox } from './lightbox.js';
import { initUploadListeners } from './upload.js';
import { initToolbar, initZipHandler } from './toolbar.js';

// ─── Directory buttons ─────────────────────────────────────

galleryBtn.addEventListener('click', () => switchDirectory('gallery'));
uploadsBtn.addEventListener('click', () => switchDirectory('uploads'));

archivesBtn.addEventListener('click', async () => {
    state.currentDir = 'archives';
    state.currentSubpath = '';
    document.getElementById('gallery').style.display = 'none';
    document.getElementById('drop-area').style.display = 'none';
    document.getElementById('archives-container').style.display = 'block';
    document.getElementById('loading').style.display = 'none';
    dirPanel.style.display = 'none';

    try {
        const response = await fetch(`/archives?sort_by=${sortBy.value}&sort_dir=${sortDir.value}`);
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        populateArchives(await response.json());
    } catch (err) {
        console.error('Failed to load archives:', err);
        document.getElementById('archives-container').innerHTML =
            `<p>Failed to load archives: ${err.message}</p>`;
    }

    galleryBtn.classList.remove('active');
    uploadsBtn.classList.remove('active');
    archivesBtn.classList.add('active');
    document.getElementById('main-heading-name').innerHTML = 'Archives';
    document.getElementById('current-path').style.display = 'none';
    document.getElementById('current-path').textContent = '';
});

// ─── Dir panel hover ───────────────────────────────────────

galleryBtn.addEventListener('mouseenter', e => { cancelDirPanelHide(); showDirPanel('gallery', e.currentTarget); });
galleryBtn.addEventListener('mouseleave', scheduleDirPanelHide);
uploadsBtn.addEventListener('mouseenter', e => { cancelDirPanelHide(); showDirPanel('uploads', e.currentTarget); });
uploadsBtn.addEventListener('mouseleave', scheduleDirPanelHide);
dirPanel.addEventListener('mouseenter', cancelDirPanelHide);
dirPanel.addEventListener('mouseleave', scheduleDirPanelHide);

// ─── Sort / filter controls ────────────────────────────────

sortBy.addEventListener('change', () => {
    if (state.currentDir === 'archives') reloadArchives(sortBy.value, sortDir.value);
    else reloadGallery();
});

sortDir.addEventListener('change', () => {
    if (state.currentDir === 'archives') reloadArchives(sortBy.value, sortDir.value);
    else reloadGallery();
});

ratingFilter.addEventListener('change', () => {
    if (state.currentDir !== 'archives') reloadGallery();
});

extFilter.addEventListener('change', () => {
    state.page = 0;
    state.done = false;
    state.loading = false;
    document.getElementById('gallery').innerHTML = '';
    loadMore();
    fetchAndPopulateTagFilter();
});

// ─── Tag filter dropdown ───────────────────────────────────

tagFilterBtn.addEventListener('click', e => {
    e.stopPropagation();
    tagFilterDropdown.classList.toggle('open');
});

document.addEventListener('click', e => {
    if (!e.target.closest('#tag-filter-wrapper')) {
        tagFilterDropdown.classList.remove('open');
    }
});

// ─── Modal keyboard / outside-click close ─────────────────

document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && document.getElementById('modal').style.display === 'block') {
        hideModal();
    }
});

modal.addEventListener('click', e => {
    if (e.target === modal) hideModal();
});

// ─── Infinite scroll ───────────────────────────────────────

window.addEventListener('scroll', () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
        loadMore();
    }
});

// ─── Init ──────────────────────────────────────────────────

initLightbox();
initUploadListeners();
initToolbar(zipFilenameInput);
initZipHandler();
initNavigation({ onAfterNavigate: () => { fetchAndPopulateTagFilter(); fetchAndPopulateExtFilter(); } });
initTagFilter({ onFilterChange: reloadGallery });

loadMore();
fetchAndPopulateTagFilter();
fetchAndPopulateExtFilter();
