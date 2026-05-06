import { archivesContainer } from './dom.js';
import { fetchArchivesRequest, extractArchiveRequest } from './api.js';
import { formatFileSize } from './utils.js';
import { showInfo } from './modal.js';

export function populateArchives(data) {
    archivesContainer.innerHTML = '';

    data.files.forEach(archive => {
        const archiveBox = document.createElement('div');
        archiveBox.className = 'archive-box';

        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'details';

        const archiveName = document.createElement('span');
        archiveName.textContent = archive.name;

        const archiveDetails = document.createElement('span');
        archiveDetails.textContent = `${formatFileSize(archive.size_bytes)} | ${new Date(archive.last_modified).toLocaleString()}`;

        const downloadButton = document.createElement('button');
        downloadButton.title = 'Download';
        downloadButton.innerHTML = `<i class="fas fa-download"></i>`;
        downloadButton.addEventListener('click', () => {
            window.location.href = `/download/${archive.name}`;
        });

        const extractButton = document.createElement('button');
        extractButton.title = 'Extract';
        extractButton.innerHTML = `<i class="fas fa-file-zipper"></i>`;
        extractButton.addEventListener('click', async () => {
            const response = await extractArchiveRequest(archive.name);
            const result = await response.json();
            if (response.ok) {
                showInfo('Extraction Complete', result.message);
            } else {
                showInfo('Extraction Error', `Error: ${result.message}`);
            }
        });

        const showContentsButton = document.createElement('button');
        showContentsButton.title = 'Contents';
        showContentsButton.innerHTML = `<i class="fas fa-folder-open"></i>`;
        showContentsButton.addEventListener('click', e => {
            e.preventDefault();
            const contentsDiv = archiveBox.querySelector('.contents');
            contentsDiv.style.display = contentsDiv.style.display !== 'block' ? 'block' : 'none';
        });

        const contentsDiv = document.createElement('div');
        contentsDiv.className = 'contents';
        archive.contents.forEach(content => {
            const contentLine = document.createElement('div');
            const contentName = document.createElement('span');
            contentName.textContent = content.path;
            const contentSize = document.createElement('span');
            contentSize.textContent = formatFileSize(content.size_bytes);
            contentLine.appendChild(contentName);
            contentLine.appendChild(contentSize);
            contentsDiv.appendChild(contentLine);
        });

        detailsDiv.appendChild(archiveName);
        detailsDiv.appendChild(archiveDetails);
        detailsDiv.appendChild(downloadButton);
        detailsDiv.appendChild(extractButton);
        detailsDiv.appendChild(showContentsButton);

        archiveBox.appendChild(detailsDiv);
        archiveBox.appendChild(contentsDiv);
        archivesContainer.appendChild(archiveBox);
    });
}

export async function reloadArchives(sortByVal, sortDirVal) {
    try {
        const response = await fetchArchivesRequest(sortByVal, sortDirVal);
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();
        populateArchives(data);
    } catch (err) {
        console.error('Failed to reload archives:', err);
    }
}
