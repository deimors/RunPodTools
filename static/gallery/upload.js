import { state } from './state.js';
import { dropArea, fileElem, uploadStatus } from './dom.js';
import { uploadFilesRequest } from './api.js';
import { getSortLabel, insertSorted } from './utils.js';
import { createImageElement, createVideoElement } from './gallery-items.js';

export async function uploadFiles(files) {
    const formData = new FormData();
    for (const file of files) {
        formData.append('file', file);
    }
    const uploadSubpath = state.currentDir === 'uploads' && state.currentSubpath ? state.currentSubpath : '';
    if (uploadSubpath) formData.append('subdir', uploadSubpath);

    try {
        const response = await uploadFilesRequest(formData);
        const result = await response.json();
        uploadStatus.innerText = result.message;

        if (response.ok) {
            for (const file of files) {
                const fileExt = file.name.split('.').pop().toLowerCase();
                const isMp4 = fileExt === 'mp4';
                const isWebP = fileExt === 'webp';
                const rawPath = `/uploads/${uploadSubpath ? uploadSubpath + '/' : ''}${file.name}`;
                const filePath = isWebP
                    ? `/static-frame/uploads/${uploadSubpath ? uploadSubpath + '/' : ''}${file.name}`
                    : rawPath;
                const animatedPath = isWebP ? rawPath : null;

                const uploadDate = new Date();
                const sortValue = getSortLabel(state.currentDir === 'uploads' ? 'date' : 'date', {
                    ...file,
                    last_modified: uploadDate.toISOString(),
                });

                const container = isMp4
                    ? createVideoElement(file.name, sortValue)
                    : createImageElement(file.name, filePath, isWebP, animatedPath, sortValue);
                container.dataset.sortDate = uploadDate.toISOString();
                container.dataset.sortFilename = file.name.toLowerCase();
                container.dataset.sortSize = file.size || 0;
                insertSorted(container);
            }
        }
    } catch (err) {
        console.error('Upload failed:', err);
        uploadStatus.innerText = 'Upload failed. Please try again.';
    }
}

export function initUploadListeners() {
    dropArea.addEventListener('click', () => fileElem.click());

    dropArea.addEventListener('dragover', e => {
        e.preventDefault();
        dropArea.classList.add('dragover');
    });

    dropArea.addEventListener('dragleave', e => {
        e.preventDefault();
        dropArea.classList.remove('dragover');
    });

    dropArea.addEventListener('drop', async e => {
        e.preventDefault();
        dropArea.classList.remove('dragover');
        await uploadFiles(e.dataTransfer.files);
    });

    fileElem.addEventListener('change', async e => {
        await uploadFiles(e.target.files);
    });
}
