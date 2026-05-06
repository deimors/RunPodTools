import { modal } from './dom.js';

const modalSteps = {
    deleteConfirmation: document.getElementById('delete-confirmation'),
    zipFilenameStep: document.getElementById('zip-filename-step'),
    zipProgressStep: document.getElementById('zip-progress-step'),
    zipDownloadStep: document.getElementById('zip-download-step'),
    infoStep: document.getElementById('info-step'),
    tagStep: document.getElementById('tag-step'),
    moveStep: document.getElementById('move-step'),
};

export function showModal(step) {
    modal.style.display = 'block';
    Object.values(modalSteps).forEach(s => (s.style.display = 'none'));
    modalSteps[step].style.display = 'block';
}

export function hideModal() {
    modal.style.display = 'none';
}

export function showInfo(title, details) {
    document.getElementById('info-title').innerText = title;
    document.getElementById('info-details').innerHTML = details;
    showModal('infoStep');
}
