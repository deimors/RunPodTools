import { state } from './state.js';
import { lightbox, lightboxImg, lightboxVideo, lightboxAudio, lightboxInfo } from './dom.js';
import { createTagChipsElement, showLightboxTags } from './tags.js';
import { createRatingWidget, showLightboxRating } from './ratings.js';
import { closeMetadataPanel } from './metadata.js';
import { debounce } from './utils.js';

const observer = new IntersectionObserver(
    entries => {
        entries.forEach(entry => {
            const imgContainer = entry.target;
            if (imgContainer.dataset.mediaType !== 'image') return;
            const img = imgContainer.querySelector('img');
            if (entry.isIntersecting) {
                if (!img.dataset.src) return;
                img.src = img.dataset.static || img.dataset.src;
                state.loadedImages.set(imgContainer, true);
            } else {
                if (state.loadedImages.has(imgContainer)) {
                    img.removeAttribute('src');
                    state.loadedImages.delete(imgContainer);
                }
            }
        });
    },
    { rootMargin: '1000px 0px', threshold: 0.01 }
);

function handleMouseLeave(img, loadingIndicator) {
    img.dataset.hovering = 'false';
    loadingIndicator.style.display = 'none';
    img.src = img.dataset.static;
}

const debouncedMouseEnter = debounce((img, loadingIndicator) => {
    if (img.dataset.hovering === 'true') {
        loadingIndicator.style.display = 'block';
        img.src = img.dataset.animated;
    }
}, 500);

export function createVideoElement(fileName, sortValue = null, duration = null, rating = 0, tags = []) {
    const container = document.createElement('div');
    container.className = 'image-container';

    const imageWrapper = document.createElement('div');
    imageWrapper.className = 'image-wrapper';

    const video = document.createElement('video');
    video.muted = true;
    video.loop = true;
    video.preload = 'none';
    video.poster = `/video-thumbnail/${state.currentDir}/${fileName}`;
    video.src = `/${state.currentDir}/${fileName}`;
    video.dataset.filename = fileName;
    video.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:8px;';

    video.draggable = true;
    video.addEventListener('dragstart', e => {
        e.dataTransfer.setData(
            'DownloadURL',
            `${container.dataset.mimeType || 'video/mp4'}:${fileName}:${window.location.origin}/${state.currentDir}/${fileName}`
        );
    });

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'checkbox';

    checkbox.addEventListener('click', e => {
        if (e.shiftKey && state.lastSelectedIndex !== -1) {
            const checkboxes = Array.from(document.querySelectorAll('.gallery .checkbox'));
            const currentIndex = checkboxes.indexOf(checkbox);
            const [start, end] = [state.lastSelectedIndex, currentIndex].sort((a, b) => a - b);
            for (let i = start; i <= end; i++) {
                checkboxes[i].checked = checkbox.checked;
                checkboxes[i].closest('.image-container').classList.toggle('selected', checkbox.checked);
            }
        }
        state.lastSelectedIndex = Array.from(document.querySelectorAll('.gallery .checkbox')).indexOf(checkbox);
    });

    checkbox.addEventListener('change', () => {
        container.classList.toggle('selected', checkbox.checked);
    });

    if (sortValue || duration) {
        const infoBar = document.createElement('div');
        infoBar.className = 'media-info-bar';
        if (duration) {
            const durationElement = document.createElement('div');
            durationElement.className = 'duration';
            durationElement.textContent = `${duration.toFixed(2)}s`;
            infoBar.appendChild(durationElement);
        }
        if (sortValue) {
            const sortValueElement = document.createElement('div');
            sortValueElement.className = 'sort-value';
            sortValueElement.textContent = sortValue;
            infoBar.appendChild(sortValueElement);
        }
        imageWrapper.appendChild(infoBar);
    }

    container.addEventListener('mouseenter', () => video.play());
    container.addEventListener('mouseleave', () => {
        video.pause();
        video.currentTime = 0;
    });

    video.addEventListener('click', e => {
        if (e.target.className === 'checkbox') return;
        const cacheKey = `${state.currentDir}/${fileName}`;
        const fileMetadata = state.fileMetadataCache[cacheKey];

        lightboxImg.style.display = 'none';
        lightboxVideo.style.display = 'block';
        lightboxVideo.src = `/${state.currentDir}/${fileName}`;
        lightboxVideo.dataset.mimeType = container.dataset.mimeType || 'video/mp4';
        lightboxVideo.play();
        document.querySelectorAll('.animation-control').forEach(btn => btn.classList.add('hidden'));

        lightboxInfo.innerText = fileName;
        showLightboxRating(fileName, fileMetadata?.rating || 0);
        showLightboxTags(state.currentDir, fileName, JSON.parse(container.dataset.tags || '[]'));

        state.currentLightboxFile = fileName;
        state.currentLightboxDir = state.currentDir;
        closeMetadataPanel();
        lightbox.style.display = 'flex';
    });

    imageWrapper.appendChild(video);
    container.appendChild(imageWrapper);
    container.appendChild(checkbox);
    imageWrapper.appendChild(createRatingWidget(fileName, rating));

    container.dataset.filename = fileName;
    container.dataset.tags = JSON.stringify(tags);
    if (tags.length > 0) imageWrapper.appendChild(createTagChipsElement(tags));

    return container;
}

export function createImageElement(
    fileName,
    filePath,
    isWebP = false,
    animatedPath = null,
    sortValue = null,
    duration = null,
    rating = 0,
    tags = []
) {
    const container = document.createElement('div');
    container.className = 'image-container';

    const imageWrapper = document.createElement('div');
    imageWrapper.className = 'image-wrapper';

    const img = document.createElement('img');
    img.alt = fileName;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'checkbox';

    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'loading-indicator';

    checkbox.addEventListener('click', e => {
        if (e.shiftKey && state.lastSelectedIndex !== -1) {
            const checkboxes = Array.from(document.querySelectorAll('.gallery .checkbox'));
            const currentIndex = checkboxes.indexOf(checkbox);
            const [start, end] = [state.lastSelectedIndex, currentIndex].sort((a, b) => a - b);
            for (let i = start; i <= end; i++) {
                checkboxes[i].checked = checkbox.checked;
                checkboxes[i].closest('.image-container').classList.toggle('selected', checkbox.checked);
            }
        }
        state.lastSelectedIndex = Array.from(document.querySelectorAll('.gallery .checkbox')).indexOf(checkbox);
    });

    checkbox.addEventListener('change', () => {
        container.classList.toggle('selected', checkbox.checked);
    });

    if (sortValue || duration) {
        const infoBar = document.createElement('div');
        infoBar.className = 'media-info-bar';
        if (duration) {
            const durationElement = document.createElement('div');
            durationElement.className = 'duration';
            durationElement.textContent = `${duration.toFixed(2)}s`;
            infoBar.appendChild(durationElement);
        }
        if (sortValue) {
            const sortValueElement = document.createElement('div');
            sortValueElement.className = 'sort-value';
            sortValueElement.textContent = sortValue;
            infoBar.appendChild(sortValueElement);
        }
        imageWrapper.appendChild(infoBar);
    }

    img.src = filePath;

    if (isWebP && animatedPath) {
        img.dataset.static = filePath;
        img.dataset.animated = animatedPath;

        container.addEventListener('mouseenter', () => {
            img.dataset.hovering = 'true';
            debouncedMouseEnter(img, loadingIndicator);
        });
        container.addEventListener('mouseleave', () => handleMouseLeave(img, loadingIndicator));
    }

    img.addEventListener('load', () => {
        loadingIndicator.style.display = 'none';
    });

    img.addEventListener('click', e => {
        if (e.target.className === 'checkbox') return;
        lightboxImg.dataset.filename = fileName;
        lightboxImg.src = container.dataset.isAnimated === 'true' ? img.dataset.animated : img.src;

        const cacheKey = `${state.currentDir}/${fileName}`;
        const fileMetadata = state.fileMetadataCache[cacheKey];
        showLightboxRating(fileName, fileMetadata?.rating || 0);
        showLightboxTags(state.currentDir, fileName, JSON.parse(container.dataset.tags || '[]'));

        const animationControls = document.querySelectorAll('.animation-control');
        if (container.dataset.isAnimated === 'true') {
            animationControls.forEach(btn => btn.classList.remove('hidden'));
        } else {
            animationControls.forEach(btn => btn.classList.add('hidden'));
        }

        state.currentLightboxFile = fileName;
        state.currentLightboxDir = state.currentDir;
        closeMetadataPanel();
        lightbox.style.display = 'flex';
    });

    imageWrapper.appendChild(img);
    imageWrapper.appendChild(loadingIndicator);
    container.appendChild(imageWrapper);
    container.appendChild(checkbox);
    imageWrapper.appendChild(createRatingWidget(fileName, rating));

    container.dataset.filename = fileName;
    container.dataset.tags = JSON.stringify(tags);
    if (tags.length > 0) imageWrapper.appendChild(createTagChipsElement(tags));

    return container;
}

export function createAudioElement(fileName, sortValue = null, duration = null, rating = 0, tags = []) {
    const container = document.createElement('div');
    container.className = 'image-container';

    const imageWrapper = document.createElement('div');
    imageWrapper.className = 'image-wrapper audio-wrapper';

    const audio = document.createElement('audio');
    audio.controls = true;
    audio.loop = true;
    audio.preload = 'metadata';
    audio.src = `/${state.currentDir}/${fileName}`;
    audio.dataset.filename = fileName;
    audio.style.cssText = 'width:100%;';

    audio.draggable = true;
    audio.addEventListener('dragstart', e => {
        e.dataTransfer.setData(
            'DownloadURL',
            `${container.dataset.mimeType || 'audio/mpeg'}:${fileName}:${window.location.origin}/${state.currentDir}/${fileName}`
        );
    });

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'checkbox';

    checkbox.addEventListener('click', e => {
        if (e.shiftKey && state.lastSelectedIndex !== -1) {
            const checkboxes = Array.from(document.querySelectorAll('.gallery .checkbox'));
            const currentIndex = checkboxes.indexOf(checkbox);
            const [start, end] = [state.lastSelectedIndex, currentIndex].sort((a, b) => a - b);
            for (let i = start; i <= end; i++) {
                checkboxes[i].checked = checkbox.checked;
                checkboxes[i].closest('.image-container').classList.toggle('selected', checkbox.checked);
            }
        }
        state.lastSelectedIndex = Array.from(document.querySelectorAll('.gallery .checkbox')).indexOf(checkbox);
    });

    checkbox.addEventListener('change', () => {
        container.classList.toggle('selected', checkbox.checked);
    });

    if (sortValue || duration) {
        const infoBar = document.createElement('div');
        infoBar.className = 'media-info-bar';
        if (duration) {
            const durationElement = document.createElement('div');
            durationElement.className = 'duration';
            durationElement.textContent = `${duration.toFixed(2)}s`;
            infoBar.appendChild(durationElement);
        }
        if (sortValue) {
            const sortValueElement = document.createElement('div');
            sortValueElement.className = 'sort-value';
            sortValueElement.textContent = sortValue;
            infoBar.appendChild(sortValueElement);
        }
        imageWrapper.appendChild(infoBar);
    }

    // Open lightbox when clicking the wrapper (but not on the audio controls themselves)
    imageWrapper.addEventListener('click', e => {
        if (e.target === audio || audio.contains(e.target)) return;
        if (e.target.className === 'checkbox') return;
        const cacheKey = `${state.currentDir}/${fileName}`;
        const fileMetadata = state.fileMetadataCache[cacheKey];

        lightboxImg.style.display = 'none';
        lightboxVideo.style.display = 'none';
        lightboxAudio.style.display = 'block';
        lightboxAudio.src = `/${state.currentDir}/${fileName}`;
        lightboxAudio.play();
        document.querySelectorAll('.animation-control').forEach(btn => btn.classList.add('hidden'));

        lightboxInfo.innerText = fileName;
        showLightboxRating(fileName, fileMetadata?.rating || 0);
        showLightboxTags(state.currentDir, fileName, JSON.parse(container.dataset.tags || '[]'));

        state.currentLightboxFile = fileName;
        state.currentLightboxDir = state.currentDir;
        closeMetadataPanel();
        lightbox.style.display = 'flex';
    });

    imageWrapper.appendChild(audio);
    container.appendChild(imageWrapper);
    container.appendChild(checkbox);
    imageWrapper.appendChild(createRatingWidget(fileName, rating));

    container.dataset.filename = fileName;
    container.dataset.tags = JSON.stringify(tags);
    if (tags.length > 0) imageWrapper.appendChild(createTagChipsElement(tags));

    return container;
}
