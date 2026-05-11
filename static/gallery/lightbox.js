import { state } from './state.js';
import {
    lightbox, lightboxImg, lightboxVideo, lightboxAudio, lightboxInfo, lightboxRating,
    toggleMetadataBtn, closeMetadataBtn,
} from './dom.js';
import { toggleMetadataPanel, closeMetadataPanel } from './metadata.js';
import { showLightboxTags } from './tags.js';
import { showLightboxRating } from './ratings.js';

export function initLightbox() {
    // Setup video drag
    lightboxVideo.draggable = true;
    lightboxVideo.addEventListener('dragstart', e => {
        const src = lightboxVideo.src;
        const fileName = src.split('/').pop();
        e.dataTransfer.setData('DownloadURL', `${lightboxVideo.dataset.mimeType || 'video/mp4'}:${fileName}:${src}`);
    });

    // Close lightbox on backdrop click
    lightbox.addEventListener('click', e => {
        if (e.target.closest('#lightbox-metadata-panel')) return;
        if (e.target.closest('#toggle-metadata-btn')) return;
        if (e.target.closest('#lightbox-info-bar')) return;

        lightbox.style.display = 'none';
        lightboxImg.src = '';
        lightboxImg.style.display = 'block';
        lightboxVideo.pause();
        lightboxVideo.src = '';
        lightboxVideo.style.display = 'none';
        lightboxAudio.pause();
        lightboxAudio.src = '';
        lightboxAudio.style.display = 'none';
        lightboxInfo.innerText = '';
        lightboxRating.innerHTML = '';
        document.getElementById('lightbox-tags').innerHTML = '';
        closeMetadataPanel();
        state.currentLightboxFile = null;
        state.currentLightboxDir = null;
    });

    // Metadata panel toggle
    toggleMetadataBtn.addEventListener('click', e => {
        e.stopPropagation();
        toggleMetadataPanel();
    });

    closeMetadataBtn.addEventListener('click', e => {
        e.stopPropagation();
        closeMetadataPanel();
    });

    // lightboxImg load handler — syncs info bar after src changes
    lightboxImg.addEventListener('load', () => {
        const storedFilename = lightboxImg.dataset.filename;
        const filename = storedFilename || lightboxImg.src.split('/').pop().split('?')[0];
        const cacheKey = `${state.currentDir}/${filename}`;
        const fileMetadata = state.fileMetadataCache[cacheKey];
        const animationControls = document.querySelectorAll('.animation-control');

        if (fileMetadata) {
            lightboxImg.dataset.static = `/static-frame/${state.currentDir}/${filename}?frame=first`;
            lightboxImg.dataset.animated = `/${state.currentDir}/${filename}`;
            lightboxInfo.innerText = filename;
            showLightboxRating(filename, fileMetadata.rating || 0);
            showLightboxTags(state.currentDir, filename, fileMetadata.tags || []);
            if (fileMetadata.frames && fileMetadata.frames > 0) {
                animationControls.forEach(btn => btn.classList.remove('hidden'));
            } else {
                animationControls.forEach(btn => btn.classList.add('hidden'));
            }
        } else {
            lightboxInfo.innerText = filename;
            showLightboxRating(filename, 0);
            showLightboxTags(state.currentDir, filename, []);
            animationControls.forEach(btn => btn.classList.add('hidden'));
        }
    });

    // Animation controls
    const playAnimationBtn = document.getElementById('play-animation-btn');
    const showFirstFrameBtn = document.getElementById('show-first-frame-btn');
    const showLastFrameBtn = document.getElementById('show-last-frame-btn');

    playAnimationBtn.addEventListener('click', e => {
        e.stopPropagation();
        playAnimationBtn.classList.add('active');
        showFirstFrameBtn.classList.remove('active');
        showLastFrameBtn.classList.remove('active');
        lightboxImg.src = lightboxImg.dataset.animated || lightboxImg.src;
    });

    showFirstFrameBtn.addEventListener('click', e => {
        e.stopPropagation();
        playAnimationBtn.classList.remove('active');
        showFirstFrameBtn.classList.add('active');
        showLastFrameBtn.classList.remove('active');
        lightboxImg.src = (lightboxImg.dataset.static || lightboxImg.src).replace('.webp', '.png');
    });

    showLastFrameBtn.addEventListener('click', e => {
        e.stopPropagation();
        playAnimationBtn.classList.remove('active');
        showFirstFrameBtn.classList.remove('active');
        showLastFrameBtn.classList.add('active');
        const stored = lightboxImg.dataset.filename || lightboxImg.src.split('/').pop().split('?')[0];
        const webpFilename = stored.endsWith('.webp') ? stored : stored.replace('.png', '.webp');
        lightboxImg.src = `/static-frame/${state.currentDir}/${webpFilename.replace('.webp', '.png')}?frame=last`;
    });
}
