let page = 0;
let loading = false;
let done = false;
let currentDir = "gallery"; // Default to gallery directory
let lastSelectedIndex = -1; // Track the last selected image index
let currentSubpath = ""; // Track the current subdirectory path
let fetchController = null;
const dirTreeCache = {};
let dirPanelHideTimer = null;
let activeDirBtn = null;
let panelDir = null;

const gallery = document.getElementById("gallery");
const archivesContainer = document.getElementById("archives-container");
const loadedImages = new Map();
const mainHeading = document.getElementById("main-heading");
const mainHeadingName = document.getElementById("main-heading-name");
const currentPathEl = document.getElementById("current-path");
const galleryBtn = document.getElementById("gallery-btn");
const uploadsBtn = document.getElementById("uploads-btn");
const archivesBtn = document.getElementById("archives-btn");
const dropArea = document.getElementById("drop-area");
const lightbox = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const lightboxVideo = document.getElementById("lightbox-video");
lightboxVideo.draggable = true;
lightboxVideo.addEventListener("dragstart", (e) => {
    const src = lightboxVideo.src;
    const fileName = src.split("/").pop();
    e.dataTransfer.setData(
        "DownloadURL",
        `video/mp4:${fileName}:${src}`
    );
});
const modal = document.getElementById("modal");
const modalTitle = document.getElementById("modal-title"); // Define modalTitle
const zipFilenameInput = document.getElementById("zip-filename"); // Define zipFilenameInput
const zipBtn = document.getElementById("zip-btn"); // Ensure consistent usage of "zip-btn"
const modalProgress = document.getElementById("modal-progress");
const downloadBtn = document.getElementById("download-btn");
const lightboxInfo = document.getElementById("lightbox-info");
const lightboxRating = document.getElementById("lightbox-rating");
const sortBy = document.getElementById("sort-by");
const sortDir = document.getElementById("sort-dir");
const loadingText = document.getElementById("loading"); // Extracted loading text element

const modalSteps = {
    deleteConfirmation: document.getElementById("delete-confirmation"),
    zipFilenameStep: document.getElementById("zip-filename-step"),
    zipProgressStep: document.getElementById("zip-progress-step"),  
    zipDownloadStep: document.getElementById("zip-download-step"),
    infoStep: document.getElementById("info-step")
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        const imgContainer = entry.target;
        const img = imgContainer.querySelector('img');
        if (entry.isIntersecting) {
            if (!img.dataset.src) return;
            img.src = img.dataset.static || img.dataset.src;
            loadedImages.set(imgContainer, true);
        } else {
            if (loadedImages.has(imgContainer)) {
                img.removeAttribute("src");  // Unload image
                loadedImages.delete(imgContainer);
            }
        }
    });
}, {
    rootMargin: "1000px 0px",  // Start loading before visible
    threshold: 0.01
});

function showInfo(title, details) {
    const infoTitle = document.getElementById("info-title");
    const infoDetails = document.getElementById("info-details");

    infoTitle.innerText = title;
    infoDetails.innerHTML = details;

    showModal("infoStep");
}

function showModal(step) {
    modal.style.display = "block";
    Object.values(modalSteps).forEach(s => s.style.display = "none");
    modalSteps[step].style.display = "block";
}

function hideModal() {
    modal.style.display = "none";
}

function debounce(func, delay) {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
    };
}

function handleMouseLeave(img, loadingIndicator) {
    img.dataset.hovering = "false"; // Mark as not hovering
    loadingIndicator.style.display = "none"; // Hide loading indicator
    img.src = img.dataset.static; // Return to static frame
}

const debouncedMouseEnter = debounce((img, loadingIndicator) => {
    if (img.dataset.hovering === "true") { // Only show animation if still hovering
        loadingIndicator.style.display = "block"; // Show loading indicator
        img.src = img.dataset.animated;
    }
}, 500);

// ─── Rating Functions ──────────────────────────────────────

async function setRating(filename, rating) {
    try {
        const response = await fetch('/rate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                dir: currentDir,
                filename: filename,
                rating: rating
            })
        });
        const data = await response.json();
        if (data.success) {
            // Update cache
            const cacheKey = `${currentDir}/${filename}`;
            if (fileMetadataCache[cacheKey]) {
                fileMetadataCache[cacheKey].rating = rating;
            }
            return true;
        } else {
            console.error('Failed to set rating:', data.message);
            return false;
        }
    } catch (err) {
        console.error('Error setting rating:', err);
        return false;
    }
}

function createRatingWidget(filename, currentRating = 0) {
    const ratingContainer = document.createElement('div');
    ratingContainer.className = 'rating-container';
    if (currentRating > 0) {
        ratingContainer.classList.add('rated');
    }

    for (let i = 1; i <= 3; i++) {
        const star = document.createElement('span');
        star.className = 'star';
        star.innerHTML = '★';
        star.dataset.starIndex = i;
        if (i <= currentRating) {
            star.classList.add('filled');
        }
        
        star.addEventListener('mouseenter', () => {
            // Highlight all stars up to and including this one
            const stars = ratingContainer.querySelectorAll('.star');
            stars.forEach((s, idx) => {
                if (idx < i) {
                    s.classList.add('hover');
                } else {
                    s.classList.remove('hover');
                }
            });
        });
        
        star.addEventListener('click', async (e) => {
            e.stopPropagation(); // Prevent image click/lightbox
            
            // Toggle rating: if clicking the current rating, set to 0 (unrated)
            const newRating = (currentRating === i) ? 0 : i;
            
            if (await setRating(filename, newRating)) {
                // Update UI
                updateRatingDisplay(ratingContainer, newRating);
                currentRating = newRating;
            }
        });
        
        ratingContainer.appendChild(star);
    }
    
    // Remove hover state when mouse leaves the container
    ratingContainer.addEventListener('mouseleave', () => {
        const stars = ratingContainer.querySelectorAll('.star');
        stars.forEach(s => s.classList.remove('hover'));
    });

    return ratingContainer;
}

function updateRatingDisplay(ratingContainer, rating) {
    const stars = ratingContainer.querySelectorAll('.star');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.add('filled');
        } else {
            star.classList.remove('filled');
        }
    });
    
    // Update visibility class
    if (rating > 0) {
        ratingContainer.classList.add('rated');
    } else {
        ratingContainer.classList.remove('rated');
    }
}

function showLightboxRating(filename, currentRating = 0) {
    lightboxRating.innerHTML = ''; // Clear previous rating
    
    for (let i = 1; i <= 3; i++) {
        const star = document.createElement('span');
        star.className = 'star';
        star.innerHTML = '★';
        star.dataset.starIndex = i;
        if (i <= currentRating) {
            star.classList.add('filled');
        }
        
        star.addEventListener('mouseenter', () => {
            // Highlight all stars up to and including this one
            const stars = lightboxRating.querySelectorAll('.star');
            stars.forEach((s, idx) => {
                if (idx < i) {
                    s.classList.add('hover');
                } else {
                    s.classList.remove('hover');
                }
            });
        });
        
        star.addEventListener('click', async (e) => {
            e.stopPropagation();
            
            // Toggle rating: if clicking the current rating, set to 0 (unrated)
            const newRating = (currentRating === i) ? 0 : i;
            
            if (await setRating(filename, newRating)) {
                // Update lightbox display
                showLightboxRating(filename, newRating);
                currentRating = newRating;
                
                // Update gallery thumbnail rating if visible
                const containers = document.querySelectorAll('.gallery .image-container');
                containers.forEach(container => {
                    const ratingWidget = container.querySelector('.rating-container');
                    const video = container.querySelector('video');
                    const img = container.querySelector('img');
                    const containerFilename = video?.dataset.filename || img?.alt;
                    
                    if (containerFilename === filename && ratingWidget) {
                        updateRatingDisplay(ratingWidget, newRating);
                    }
                });
            }
        });
        
        lightboxRating.appendChild(star);
    }
    
    // Remove hover state when mouse leaves the lightbox rating container
    lightboxRating.addEventListener('mouseleave', () => {
        const stars = lightboxRating.querySelectorAll('.star');
        stars.forEach(s => s.classList.remove('hover'));
    });
}

function createVideoElement(fileName, sortValue = null, duration = null, rating = 0) {
    const container = document.createElement("div");
    container.className = "image-container";

    const imageWrapper = document.createElement("div");
    imageWrapper.className = "image-wrapper";

    const video = document.createElement("video");
    video.muted = true;
    video.loop = true;
    video.preload = "none";
    video.poster = `/video-thumbnail/${currentDir}/${fileName}`;
    video.src = `/${currentDir}/${fileName}`;
    video.dataset.filename = fileName;
    video.style.width = "100%";
    video.style.height = "100%";
    video.style.objectFit = "cover";
    video.style.borderRadius = "8px";

    video.draggable = true;
    video.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData(
            "DownloadURL",
            `video/mp4:${fileName}:${window.location.origin}/${currentDir}/${fileName}`
        );
    });

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "checkbox";

    checkbox.addEventListener("click", (e) => {
        if (e.shiftKey && lastSelectedIndex !== -1) {
            const checkboxes = Array.from(document.querySelectorAll(".gallery .checkbox"));
            const currentIndex = checkboxes.indexOf(checkbox);
            const [start, end] = [lastSelectedIndex, currentIndex].sort((a, b) => a - b);
            for (let i = start; i <= end; i++) {
                checkboxes[i].checked = checkbox.checked;
                checkboxes[i].closest(".image-container").classList.toggle("selected", checkbox.checked);
            }
        }
        lastSelectedIndex = Array.from(document.querySelectorAll(".gallery .checkbox")).indexOf(checkbox);
    });

    checkbox.addEventListener("change", () => {
        container.classList.toggle("selected", checkbox.checked);
    });

    if (sortValue) {
        const sortValueElement = document.createElement("div");
        sortValueElement.className = "sort-value";
        sortValueElement.textContent = sortValue;
        imageWrapper.appendChild(sortValueElement);
    }

    if (duration) {
        const durationElement = document.createElement("div");
        durationElement.className = "duration";
        durationElement.textContent = `${duration.toFixed(2)}s`;
        imageWrapper.appendChild(durationElement);
    }

    container.addEventListener("mouseenter", () => video.play());
    container.addEventListener("mouseleave", () => {
        video.pause();
        video.currentTime = 0;
    });

    video.addEventListener("click", (e) => {
        if (e.target.className === "checkbox") return;
        const cacheKey = `${currentDir}/${fileName}`;
        const fileMetadata = fileMetadataCache[cacheKey];

        lightboxImg.style.display = "none";
        lightboxVideo.style.display = "block";
        lightboxVideo.src = `/${currentDir}/${fileName}`;
        lightboxVideo.play();
        document.getElementById("lightbox-controls").style.display = "none";

        if (fileMetadata) {
            const resolution = fileMetadata.resolution ? fileMetadata.resolution : "";
            const duration = fileMetadata.duration_seconds ? `${fileMetadata.duration_seconds.toFixed(2)}s` : "";
            const frameRate = fileMetadata.frame_rate ? `${fileMetadata.frame_rate.toFixed(2)} fps` : "";
            const fileSize = fileMetadata.size_bytes ? formatFileSize(fileMetadata.size_bytes) : "";
            const lastModified = fileMetadata.last_modified ? new Date(fileMetadata.last_modified).toLocaleString() : "";
            lightboxInfo.innerText = [fileName, resolution, duration, frameRate, fileSize, lastModified]
                .filter(Boolean).join(" | ");
            showLightboxRating(fileName, fileMetadata.rating || 0);
        } else {
            lightboxInfo.innerText = fileName;
            showLightboxRating(fileName, 0);
        }

        lightbox.style.display = "flex";
    });

    imageWrapper.appendChild(video);
    container.appendChild(imageWrapper);
    container.appendChild(checkbox);
    
    // Add rating widget
    const ratingWidget = createRatingWidget(fileName, rating);
    imageWrapper.appendChild(ratingWidget);
    
    return container;
}

function createImageElement(fileName, filePath, isWebP = false, animatedPath = null, sortValue = null, duration = null, rating = 0) {
    const container = document.createElement("div");
    container.className = "image-container";

    const imageWrapper = document.createElement("div");
    imageWrapper.className = "image-wrapper";

    const img = document.createElement("img");
    img.alt = fileName;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "checkbox";

    const loadingIndicator = document.createElement("div");
    loadingIndicator.className = "loading-indicator";

    // Handle shift-click for range selection
    checkbox.addEventListener("click", (e) => {
        if (e.shiftKey && lastSelectedIndex !== -1) {
            const checkboxes = Array.from(document.querySelectorAll(".gallery .checkbox"));
            const currentIndex = checkboxes.indexOf(checkbox);
            const [start, end] = [lastSelectedIndex, currentIndex].sort((a, b) => a - b);

            for (let i = start; i <= end; i++) {
                checkboxes[i].checked = checkbox.checked;
                checkboxes[i].closest(".image-container").classList.toggle("selected", checkbox.checked);
            }
        }
        lastSelectedIndex = Array.from(document.querySelectorAll(".gallery .checkbox")).indexOf(checkbox);
    });

    // Ensure the container toggles the selected class when the checkbox is changed
    checkbox.addEventListener("change", () => {
        container.classList.toggle("selected", checkbox.checked);
    });

    if (sortValue) {
        const sortValueElement = document.createElement("div");
        sortValueElement.className = "sort-value";
        sortValueElement.textContent = sortValue;
        imageWrapper.appendChild(sortValueElement);
    }

    if (isWebP && duration) {
        const durationElement = document.createElement("div");
        durationElement.className = "duration";
        durationElement.textContent = `${duration.toFixed(2)}s`;
        imageWrapper.appendChild(durationElement);
    }

    img.src = filePath;

    if (isWebP && animatedPath) {
        img.dataset.static = filePath;
        img.dataset.animated = animatedPath;

        container.addEventListener("mouseenter", () => {
            img.dataset.hovering = "true"; // Mark as hovering
            debouncedMouseEnter(img, loadingIndicator);
        });
        container.addEventListener("mouseleave", () => handleMouseLeave(img, loadingIndicator));
    }

    img.addEventListener("load", () => {
        loadingIndicator.style.display = "none"; // Hide loading indicator once loaded
    });

    img.addEventListener("click", (e) => {
        if (e.target.className === "checkbox") return;
        lightboxImg.dataset.filename = fileName;
        lightboxImg.src = isWebP && animatedPath ? img.dataset.animated : img.src;
        
        // Get rating from cache
        const cacheKey = `${currentDir}/${fileName}`;
        const fileMetadata = fileMetadataCache[cacheKey];
        const currentRating = fileMetadata?.rating || 0;
        showLightboxRating(fileName, currentRating);
        
        lightbox.style.display = "flex";
    });

    imageWrapper.appendChild(img);
    imageWrapper.appendChild(loadingIndicator);
    container.appendChild(imageWrapper);
    container.appendChild(checkbox);
    
    // Add rating widget
    const ratingWidget = createRatingWidget(fileName, rating);
    imageWrapper.appendChild(ratingWidget);
    
    return container;
}

const fileMetadataCache = {}; // Object to store metadata indexed by directory and filename

function getSortLabel(sortKey, file) {
    if (sortKey === "date") {
        const ts = file.last_modified || (file.lastModified ? new Date(file.lastModified).toISOString() : null);
        return ts ? new Date(ts).toLocaleString() : new Date().toLocaleString();
    }
    if (sortKey === "filename") return file.name;
    if (sortKey === "size") return formatFileSize(file.size_bytes || file.size || 0);
    return null;
}

async function loadMore() {
    if (loading || done) return;
    loading = true;
    loadingText.style.display = "block";

    if (fetchController) fetchController.abort();
    fetchController = new AbortController();

    try {
        const response = await fetch(
            `/images?dir=${currentDir}&page=${page}&sort_by=${sortBy.value}&sort_dir=${sortDir.value}&subpath=${encodeURIComponent(currentSubpath)}`,
            { signal: fetchController.signal }
        );
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();

        if (data.files.length === 0) {
            loadingText.innerText = "No more files.";
            done = true;
            return;
        }

        data.files.forEach(file => {
            const fileName = file.name;
            const fileExt = fileName.split('.').pop().toLowerCase();
            const isMp4 = fileExt === 'mp4';
            const isWebP = fileExt === 'webp';
            const filePath = isWebP ? `/static-frame/${currentDir}/${fileName}` : `/${currentDir}/${fileName}`;
            const animatedPath = isWebP ? `/${currentDir}/${fileName}` : null;
            const fileDuration = (isWebP || isMp4) ? file.duration_seconds : null;

            const cacheKey = `${currentDir}/${fileName}`;
            fileMetadataCache[cacheKey] = file;

            const sortValue = getSortLabel(sortBy.value, file);
            const rating = file.rating || 0;

            const container = isMp4
                ? createVideoElement(fileName, sortValue, fileDuration, rating)
                : createImageElement(fileName, filePath, isWebP, animatedPath, sortValue, fileDuration, rating);
            container.dataset.sortDate = new Date(file.last_modified).toISOString();
            container.dataset.sortFilename = fileName.toLowerCase();
            container.dataset.sortSize = file.size_bytes || 0;
            gallery.appendChild(container);
        });

        page++;
        loadingText.style.display = "none";

        // Check if enough images are loaded to create a scrollbar
        const viewportHeight = window.innerHeight;
        const contentHeight = document.body.scrollHeight;
        if (contentHeight <= viewportHeight && !done) {
            loadMore();
        }
    } catch (err) {
        if (err.name !== "AbortError") {
            loadingText.innerText = "Failed to load files.";
            console.error("loadMore error:", err);
        }
    } finally {
        loading = false;
    }
}

function updateActiveFolderButton(dir) {
    galleryBtn.classList.toggle("active", dir === "gallery");
    uploadsBtn.classList.toggle("active", dir === "uploads");
    archivesBtn.classList.toggle("active", dir === "archives");
}

function switchDirectory(dir) {
    if (fetchController) fetchController.abort();
    currentDir = dir;
    currentSubpath = "";
    page = 0;
    done = false;
    loading = false;
    gallery.innerHTML = ""; // Clear current gallery
    archivesContainer.style.display = "none"; // Show archives only for "Archives"
    gallery.style.display = "grid"; // Show gallery for "Gallery" and "Uploads"
    dropArea.style.display = dir === "uploads" ? "block" : "none"; // Show drop area only for "Uploads"

    loadMore(); // Load new directory contents

    // Update heading text
    mainHeadingName.innerHTML = dir === "gallery" ? "Gallery" : "Uploads";
    currentPathEl.style.display = "none";
    currentPathEl.textContent = "";

    updateActiveFolderButton(dir); // Update active folder button
}

function formatFileSize(size) {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
    if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(2)} MB`;
    return `${(size / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

galleryBtn.addEventListener("click", () => switchDirectory("gallery"));
uploadsBtn.addEventListener("click", () => switchDirectory("uploads"));
archivesBtn.addEventListener("click", async () => {
    currentDir = "archives"; // Switch to archives directory
    currentSubpath = "";
    gallery.style.display = "none"; // Hide gallery
    dropArea.style.display = "none"; // Hide upload control
    archivesContainer.style.display = "block"; // Show archives container
    loadingText.style.display = "none"; // Ensure loading text is hidden

    document.getElementById("dir-panel").style.display = "none";

    try {
        const response = await fetch(`/archives?sort_by=${sortBy.value}&sort_dir=${sortDir.value}`);
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();
        populateArchives(data);
    } catch (err) {
        console.error("Failed to load archives:", err);
        archivesContainer.innerHTML = `<p>Failed to load archives: ${err.message}</p>`;
    }

    updateActiveFolderButton("archives");
    mainHeadingName.innerHTML = "Archives"; // Update heading name
    currentPathEl.style.display = "none";
    currentPathEl.textContent = "";
});

function populateArchives(data) {
    archivesContainer.innerHTML = ""; // Clear previous content

    data.files.forEach(archive => {
        const archiveBox = document.createElement("div");
        archiveBox.className = "archive-box";

        const detailsDiv = document.createElement("div");
        detailsDiv.className = "details";

        const archiveName = document.createElement("span");
        archiveName.textContent = archive.name;

        const archiveDetails = document.createElement("span");
        archiveDetails.textContent = `${formatFileSize(archive.size_bytes)} | ${new Date(archive.last_modified).toLocaleString()}`;

        const downloadButton = document.createElement("button");
        downloadButton.title = "Download";
        downloadButton.innerHTML = `<i class="fas fa-download"></i>`;
        downloadButton.addEventListener("click", () => {
            window.location.href = `/download/${archive.name}`;
        });

        const extractButton = document.createElement("button");
        extractButton.title = "Extract";
        extractButton.innerHTML = `<i class="fas fa-file-zipper"></i>`;
        extractButton.addEventListener("click", async () => {
            const response = await fetch("/archive/extract", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename: archive.name })
            });
            const result = await response.json();
            if (response.ok) {
                showInfo("Extraction Complete", result.message);
            } else {
                showInfo("Extraction Error", `Error: ${result.message}`);
            }
        });

        const showContentsButton = document.createElement("button");
        showContentsButton.title = "Contents";
        showContentsButton.innerHTML = `<i class="fas fa-folder-open"></i>`;
        showContentsButton.addEventListener("click", (e) => {
            e.preventDefault(); // Prevent default behavior
            const contentsDiv = archiveBox.querySelector(".contents");
            contentsDiv.style.display = contentsDiv.style.display !== "block" ? "block" : "none";
        });

        const contentsDiv = document.createElement("div");
        contentsDiv.className = "contents";
        archive.contents.forEach(content => {
            const contentLine = document.createElement("div");

            const contentName = document.createElement("span");
            contentName.textContent = content.path;

            const contentSize = document.createElement("span");
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

function insertSorted(container) {
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

async function reloadGallery() {
    page = 0;
    done = false;
    gallery.innerHTML = "";
    loadMore();
}

async function reloadArchives() {
    try {
        const response = await fetch(`/archives?sort_by=${sortBy.value}&sort_dir=${sortDir.value}`);
        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();
        populateArchives(data);
    } catch (err) {
        console.error("Failed to reload archives:", err);
    }
}

sortBy.addEventListener("change", () => {
    if (currentDir === "archives") {
        reloadArchives(); // Reload archives with updated sort parameters
    } else {
        reloadGallery(); // Reload gallery with updated sort parameters
    }
});

sortDir.addEventListener("change", () => {
    if (currentDir === "archives") {
        reloadArchives(); // Reload archives with updated sort parameters
    } else {
        reloadGallery(); // Reload gallery with updated sort parameters
    }
});

function renderTreeNode(node, depth, navDir) {
    const item = document.createElement("div");

    const row = document.createElement("div");
    row.className = "dir-item" + (node.path === currentSubpath && navDir === currentDir ? " active" : "");
    row.style.paddingLeft = `${0.4 + depth * 1.2}em`;

    if (node.children && node.children.length > 0) {
        const toggle = document.createElement("i");
        toggle.className = "fas fa-chevron-down tree-toggle";
        toggle.addEventListener("click", (e) => {
            e.stopPropagation();
            const childrenEl = item.querySelector(":scope > .tree-children");
            const collapsed = childrenEl.style.display === "none";
            childrenEl.style.display = collapsed ? "" : "none";
            toggle.className = (collapsed ? "fas fa-chevron-down" : "fas fa-chevron-right") + " tree-toggle";
        });
        row.appendChild(toggle);
    } else {
        const spacer = document.createElement("span");
        spacer.className = "tree-toggle-spacer";
        row.appendChild(spacer);
    }

    const icon = document.createElement("i");
    icon.className = (node.path === currentSubpath && navDir === currentDir) ? "fas fa-folder-open" : "fas fa-folder";
    icon.style.marginRight = "0.4em";
    row.appendChild(icon);

    const label = document.createElement("span");
    label.textContent = node.name + "/";
    row.appendChild(label);

    row.addEventListener("click", () => navigateSubdir(node.path, navDir));
    item.appendChild(row);

    if (node.children && node.children.length > 0) {
        const childrenEl = document.createElement("div");
        childrenEl.className = "tree-children";
        node.children.forEach(child => childrenEl.appendChild(renderTreeNode(child, depth + 1, navDir)));
        item.appendChild(childrenEl);
    }

    return item;
}

function renderDirTree(dir) {
    document.getElementById("dir-breadcrumb").textContent = "";
    document.getElementById("dir-breadcrumb").style.display = "none";

    const dirList = document.getElementById("dir-list");
    dirList.innerHTML = "";

    // Root node
    const rootRow = document.createElement("div");
    rootRow.className = "dir-item" + (dir !== currentDir || currentSubpath === "" ? " active" : "");
    rootRow.style.paddingLeft = "0.4em";

    const rootSpacer = document.createElement("span");
    rootSpacer.className = "tree-toggle-spacer";
    rootRow.appendChild(rootSpacer);

    const rootIcon = document.createElement("i");
    rootIcon.className = (currentSubpath === "" && dir === currentDir) ? "fas fa-folder-open" : "fas fa-folder";
    rootIcon.style.marginRight = "0.4em";
    rootRow.appendChild(rootIcon);

    const rootLabel = document.createElement("span");
    rootLabel.textContent = "/";
    rootRow.appendChild(rootLabel);

    rootRow.addEventListener("click", () => navigateSubdir("", dir));
    dirList.appendChild(rootRow);

    const tree = dirTreeCache[dir];
    if (tree && tree.length > 0) {
        tree.forEach(node => dirList.appendChild(renderTreeNode(node, 1, dir)));
    } else if (tree) {
        const empty = document.createElement("div");
        empty.className = "dir-empty";
        empty.textContent = "No subdirectories";
        dirList.appendChild(empty);
    }

    // Align new-folder button with the depth where the folder would be created
    const effectiveSubpath = (dir === currentDir) ? currentSubpath : "";
    const depth = effectiveSubpath ? effectiveSubpath.split('/').length : 0;
    const addRow = document.createElement("div");
    addRow.className = "new-dir-row";
    addRow.style.paddingLeft = `${0.4 + (depth + 1) * 1.2}em`;
    const addSpacer = document.createElement("span");
    addSpacer.className = "tree-toggle-spacer";
    addRow.appendChild(addSpacer);
    addRow.appendChild(newDirBtn);
    addRow.appendChild(newDirLabel);
    addRow.appendChild(newDirInput);

    // Insert addRow as a child of the active directory node, not always at the bottom
    const activeItem = dirList.querySelector(".dir-item.active");
    if (!activeItem || effectiveSubpath === "") {
        dirList.appendChild(addRow);
    } else {
        const itemWrapper = activeItem.parentElement;
        let childrenEl = itemWrapper.querySelector(":scope > .tree-children");
        if (!childrenEl) {
            childrenEl = document.createElement("div");
            childrenEl.className = "tree-children";
            itemWrapper.appendChild(childrenEl);
        }
        childrenEl.appendChild(addRow);
    }
}

async function showDirPanel(dir, triggerBtn) {
    if (dir === "archives") return;
    panelDir = dir;
    if (!dirTreeCache[dir]) {
        try {
            const response = await fetch(`/dirs?dir=${dir}`);
            if (!response.ok) throw new Error("Failed to fetch tree");
            const data = await response.json();
            dirTreeCache[dir] = data.tree;
        } catch (err) {
            console.error("Failed to load directory tree:", err);
            return;
        }
    }
    renderDirTree(dir);
    const panel = document.getElementById("dir-panel");
    const rect = triggerBtn.getBoundingClientRect();
    panel.style.left = (rect.right + 8) + "px";
    panel.style.top = (rect.bottom + 4) + "px";
    panel.style.display = "block";
    if (activeDirBtn && activeDirBtn !== triggerBtn) {
        activeDirBtn.classList.remove("tooltip-active");
    }
    activeDirBtn = triggerBtn;
    triggerBtn.classList.add("tooltip-active");
}

function scheduleDirPanelHide() {
    dirPanelHideTimer = setTimeout(() => {
        document.getElementById("dir-panel").style.display = "none";
        if (activeDirBtn) {
            activeDirBtn.classList.remove("tooltip-active");
            activeDirBtn = null;
        }
    }, 200);
}

function cancelDirPanelHide() {
    if (dirPanelHideTimer) {
        clearTimeout(dirPanelHideTimer);
        dirPanelHideTimer = null;
    }
}

galleryBtn.addEventListener("mouseenter", (e) => { cancelDirPanelHide(); showDirPanel("gallery", e.currentTarget); });
galleryBtn.addEventListener("mouseleave", scheduleDirPanelHide);
uploadsBtn.addEventListener("mouseenter", (e) => { cancelDirPanelHide(); showDirPanel("uploads", e.currentTarget); });
uploadsBtn.addEventListener("mouseleave", scheduleDirPanelHide);
document.getElementById("dir-panel").addEventListener("mouseenter", cancelDirPanelHide);
document.getElementById("dir-panel").addEventListener("mouseleave", scheduleDirPanelHide);

const newDirBtn = document.createElement("button");
newDirBtn.id = "new-dir-btn";
newDirBtn.innerHTML = `<i class="fas fa-folder-plus"></i>`;

const newDirLabel = document.createElement("span");
newDirLabel.id = "new-dir-label";
newDirLabel.textContent = "New Folder";

const newDirInput = document.createElement("input");
newDirInput.type = "text";
newDirInput.id = "new-dir-input";
newDirInput.placeholder = "Folder name";

newDirBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    newDirInput.classList.remove("error");
    newDirInput.value = "";
    newDirLabel.style.display = "none";
    newDirInput.style.display = "block";
    newDirInput.focus();
});

async function submitNewDir() {
    const name = newDirInput.value.trim();
    if (!name) {
        newDirInput.style.display = "none";
        newDirLabel.style.display = "";
        newDirInput.classList.remove("error");
        return;
    }
    const parentSubdir = panelDir === currentDir ? currentSubpath : "";
    try {
        const response = await fetch("/mkdir", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ dir: panelDir, subdir: parentSubdir, name })
        });
        if (response.ok) {
            newDirInput.style.display = "none";
            newDirLabel.style.display = "";
            newDirInput.classList.remove("error");
            delete dirTreeCache[panelDir];
            const res = await fetch(`/dirs?dir=${panelDir}`);
            const data = await res.json();
            dirTreeCache[panelDir] = data.tree;
            renderDirTree(panelDir);
        } else {
            newDirInput.classList.add("error");
            newDirInput.focus();
        }
    } catch (err) {
        console.error("Failed to create directory:", err);
        newDirInput.classList.add("error");
        newDirInput.focus();
    }
}

newDirInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); submitNewDir(); }
    if (e.key === "Escape") { newDirInput.style.display = "none"; newDirLabel.style.display = ""; newDirInput.classList.remove("error"); }
});
newDirInput.addEventListener("blur", submitNewDir);

function navigateSubdir(subpath, navDir = currentDir) {
    if (navDir !== currentDir) {
        if (fetchController) fetchController.abort();
        currentDir = navDir;
        archivesContainer.style.display = "none";
        gallery.style.display = "grid";
        dropArea.style.display = navDir === "uploads" ? "block" : "none";
        updateActiveFolderButton(navDir);
    }
    currentSubpath = subpath;
    page = 0;
    done = false;
    loading = false;
    gallery.innerHTML = "";

    const label = navDir === "gallery" ? "Gallery" : "Uploads";
    mainHeadingName.innerHTML = label;
    if (subpath) {
        currentPathEl.textContent = subpath;
        currentPathEl.style.display = "block";
    } else {
        currentPathEl.textContent = "";
        currentPathEl.style.display = "none";
    }

    renderDirTree(navDir);
    loadMore();
}

// Close lightbox on click
lightbox.addEventListener("click", () => {
    lightbox.style.display = "none";
    lightboxImg.src = "";
    lightboxImg.style.display = "block";
    lightboxVideo.pause();
    lightboxVideo.src = "";
    lightboxVideo.style.display = "none";
    lightboxInfo.innerText = ""; // Clear info text
    lightboxRating.innerHTML = ""; // Clear rating
});

// Initial load
loadMore();

// Infinite scroll
window.addEventListener("scroll", () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
        loadMore();
    }
});

const fileElem = document.getElementById('fileElem');
const uploadStatus = document.getElementById('upload-status');

dropArea.addEventListener('click', () => fileElem.click());

dropArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropArea.classList.add('dragover');
});
dropArea.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropArea.classList.remove('dragover');
});
dropArea.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropArea.classList.remove('dragover');
    const files = e.dataTransfer.files;
    await uploadFiles(files);
});
fileElem.addEventListener('change', async (e) => {
    const files = e.target.files;
    await uploadFiles(files);
});

async function uploadFiles(files) {
    const formData = new FormData();
    for (const file of files) {
        formData.append('file', file);
    }
    const uploadSubpath = (currentDir === 'uploads' && currentSubpath) ? currentSubpath : '';
    if (uploadSubpath) {
        formData.append('subdir', uploadSubpath);
    }
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        uploadStatus.innerText = result.message;

        if (response.ok) {
            for (const file of files) {
                const fileExt = file.name.split('.').pop().toLowerCase();
                const isMp4 = fileExt === 'mp4';
                const isWebP = fileExt === 'webp';
                const rawPath = `/uploads/${uploadSubpath ? uploadSubpath + '/' : ''}${file.name}`;
                const filePath = isWebP ? `/static-frame/uploads/${uploadSubpath ? uploadSubpath + '/' : ''}${file.name}` : rawPath;
                const animatedPath = isWebP ? rawPath : null;

                const uploadDate = new Date();
                const sortValue = getSortLabel(sortBy.value, { ...file, last_modified: uploadDate.toISOString() });

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
        console.error("Upload failed:", err);
        uploadStatus.innerText = "Upload failed. Please try again.";
    }
}

function getSelectedImages() {
    return Array.from(document.querySelectorAll(".gallery .image-container.selected"))
        .map(container => {
            const img = container.querySelector("img");
            const video = container.querySelector("video");
            return img ? img.alt : video ? video.dataset.filename : null;
        })
        .filter(Boolean);
}

document.getElementById("toolbar").addEventListener("click", (e) => {
    if (e.target.closest("#reload-btn")) {
        // Reload static frames by clearing cache and reloading images
        reloadStaticFrames();
    } else if (e.target.closest("#select-all-btn")) {
        // Select all images
        document.querySelectorAll(".gallery .image-container").forEach(container => {
            const checkbox = container.querySelector(".checkbox");
            checkbox.checked = true;
            container.classList.add("selected");
        });
    } else if (e.target.closest("#clear-selection-btn")) {
        // Clear selection
        document.querySelectorAll(".gallery .image-container").forEach(container => {
            const checkbox = container.querySelector(".checkbox");
            checkbox.checked = false;
            container.classList.remove("selected");
        });
    } else if (e.target.closest("#zip-selected-btn")) {
        const selectedFiles = getSelectedImages();
        if (selectedFiles.length === 0) {
            showInfo("Can't Zip Selected", "No files selected.");
            return;
        }

        // Update zip info div with file count
        const zipInfo = document.getElementById("zip-info");
        zipInfo.innerText = `${selectedFiles.length} files selected`;

        // Set default filename to current date
        const currentDate = new Date().toISOString().split("T")[0]; // Format as YYYY-MM-DD
        zipFilenameInput.value = `Gallery_${currentDate}.zip`;

        showModal("zipFilenameStep"); // Show zip filename input step
    } else if (e.target.closest("#delete-selected-btn")) {
        const selectedFiles = getSelectedImages();
        if (selectedFiles.length === 0) {
            showInfo("Can't Delete Selected", "No files selected.");
            return;
        }

        // Update delete info div with file count
        const deleteInfo = document.getElementById("delete-info");
        deleteInfo.innerText = `${selectedFiles.length} files selected`;

        showModal("deleteConfirmation");

        const deleteBtn = document.getElementById("delete-btn");
        deleteBtn.onclick = async () => {
            hideModal();
            await deleteFiles(selectedFiles);
        };
    }
});

function reloadStaticFrames() {
    // Get all currently visible images in the gallery
    const images = document.querySelectorAll(".gallery img");
    
    images.forEach(img => {
        // Force cache bust by adding timestamp parameter
        const timestamp = Date.now();
        const currentSrc = img.src;
        
        // If it's a static frame URL, reload with cache busting
        if (currentSrc.includes('/static-frame/')) {
            const baseUrl = currentSrc.split('?')[0]; // Remove existing query params
            img.src = `${baseUrl}?bust=${timestamp}`;
        } else if (img.dataset.static) {
            // If it has a static frame dataset, use that with cache busting
            const baseUrl = img.dataset.static.split('?')[0];
            img.src = `${baseUrl}?bust=${timestamp}`;
            // Update the dataset to include cache busting for future use
            img.dataset.static = `${baseUrl}?bust=${timestamp}`;
        }
    });
}

zipBtn.addEventListener("click", async () => {
    const filename = zipFilenameInput.value.trim();
    if (!filename) {
        showInfo("Invalid Filename", "Please enter a filename.");
        return;
    }

    // Start zipping process
    showModal("zipProgressStep");

    const selectedFiles = getSelectedImages();

    const response = await fetch("/archive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, files: selectedFiles, directory: currentDir }) // Include directory in request
    });

    if (response.ok) {
        const result = await response.json();
        if (result.success) {
            showModal("zipDownloadStep");

            downloadBtn.onclick = () => {
                window.location.href = `/download/${result.filename}`;
                hideModal();
            };
        } else {
            modalProgress.innerText = `Error: ${result.message}`;
        }
    } else {
        const error = await response.json();
        modalProgress.innerText = `Error ${response.status}: ${error.message || "An error occurred"}`;
    }
});

async function deleteFiles(files) {
    const response = await fetch("/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files, directory: currentDir })
    });
    const result = await response.json();
    if (result.success) {
        // Remove deleted files from gallery
        result.deleted.forEach(filename => {
            const imgContainer = Array.from(gallery.children).find(container => {
                const img = container.querySelector("img");
                const video = container.querySelector("video");
                return (img && img.alt === filename) || (video && video.dataset.filename === filename);
            });
            if (imgContainer) {
                gallery.removeChild(imgContainer);
            }
        });
        showInfo("Deletion Complete", result.message);
    } else {
        showInfo("Deletion Error", `Error deleting files: ${result.message}`);
    }
}

// Close modal when clicking outside
modal.addEventListener("click", (e) => {
    if (e.target === modal) {
        hideModal();
    }
});

const playAnimationBtn = document.getElementById("play-animation-btn");
const showFirstFrameBtn = document.getElementById("show-first-frame-btn");
const showLastFrameBtn = document.getElementById("show-last-frame-btn");

playAnimationBtn.addEventListener("click", (e) => {
    e.stopPropagation(); // Prevent lightbox from closing
    playAnimationBtn.classList.add("active");
    showFirstFrameBtn.classList.remove("active");
    showLastFrameBtn.classList.remove("active");
    lightboxImg.src = lightboxImg.dataset.animated || lightboxImg.src; // Play animation
});

showFirstFrameBtn.addEventListener("click", (e) => {
    e.stopPropagation(); // Prevent lightbox from closing
    playAnimationBtn.classList.remove("active");
    showFirstFrameBtn.classList.add("active");
    showLastFrameBtn.classList.remove("active");
    lightboxImg.src = lightboxImg.dataset.static.replace('.webp', '.png') || lightboxImg.src; // Show first frame as PNG
});

showLastFrameBtn.addEventListener("click", (e) => {
    e.stopPropagation(); // Prevent lightbox from closing
    playAnimationBtn.classList.remove("active");
    showFirstFrameBtn.classList.remove("active");
    showLastFrameBtn.classList.add("active");

    const stored = lightboxImg.dataset.filename || lightboxImg.src.split('/').pop().split('?')[0];
    const webpFilename = stored.endsWith('.webp') ? stored : stored.replace('.png', '.webp');
    lightboxImg.src = `/static-frame/${currentDir}/${webpFilename.replace('.webp', '.png')}?frame=last`; // Show last frame as PNG
});

lightboxImg.addEventListener("load", () => {
    const storedFilename = lightboxImg.dataset.filename;
    const filename = storedFilename || lightboxImg.src.split("/").pop().split('?')[0]; // Remove query parameters
    const originalFilename = filename.endsWith('.png') ? filename.replace('.png', '.webp') : filename;
    const cacheKey = `${currentDir}/${originalFilename}`;
    const fileMetadata = fileMetadataCache[cacheKey];

    if (fileMetadata) {
        // Set the dataset values for the lightbox image
        lightboxImg.dataset.static = `/static-frame/${currentDir}/${originalFilename}?frame=first`;
        lightboxImg.dataset.animated = `/${currentDir}/${originalFilename}`;
        
        const resolution = fileMetadata.resolution ? `${fileMetadata.resolution}` : "";
        const frames = fileMetadata.frames ? `${fileMetadata.frames} frames` : "";
        const duration = fileMetadata.duration_seconds ? `${fileMetadata.duration_seconds.toFixed(2)}s` : "";
        const frameRate = fileMetadata.frame_rate ? `${fileMetadata.frame_rate.toFixed(2)} fps` : "";
        const fileSize = fileMetadata.size_bytes ? formatFileSize(fileMetadata.size_bytes) : "";
        const lastModified = fileMetadata.last_modified ? new Date(fileMetadata.last_modified).toLocaleString() : "";

        lightboxInfo.innerText = [originalFilename, resolution, frames, duration, frameRate, fileSize, lastModified]
            .filter(Boolean) // Remove empty strings
            .join(" | ");

        // Show rating
        showLightboxRating(originalFilename, fileMetadata.rating || 0);

        // Show controls only if the file is a WebP animation with frames
        const lightboxControls = document.getElementById("lightbox-controls");
        if (fileMetadata.frames && fileMetadata.frames > 0) {
            lightboxControls.style.display = "flex";
        } else {
            lightboxControls.style.display = "none";
        }
    } else {
        lightboxInfo.innerText = filename;
        showLightboxRating(filename, 0);
        document.getElementById("lightbox-controls").style.display = "none"; // Hide controls
    }
});
