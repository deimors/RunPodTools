import { state } from './state.js';
import { tagFilterBtn, tagFilterDropdown, extFilter } from './dom.js';
import { addTagRequest as apiAddTag, removeTagRequest, fetchTagsRequest, fetchExtensionsRequest } from './api.js';
import { hideModal } from './modal.js';

// Injected by main.js via initTagFilter — avoids a circular dependency with navigation.js
let _onFilterChange = () => {};

export function initTagFilter({ onFilterChange }) {
    _onFilterChange = onFilterChange;
}

export function updateTagFilterLabel() {
    tagFilterBtn.textContent = state.selectedTags.size === 0 ? 'Select...' : `Tags (${state.selectedTags.size})`;
}

export async function fetchAndPopulateTagFilter() {
    try {
        const data = await fetchTagsRequest(state.currentDir, state.currentSubpath, state.selectedTags);
        if (!data) return;
        const tags = data.tags || [];
        tagFilterDropdown.innerHTML = '';
        if (tags.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'tag-filter-no-tags';
            empty.textContent = 'No tags';
            tagFilterDropdown.appendChild(empty);
        } else {
            tags.forEach(({ name, count }) => {
                const label = document.createElement('label');
                label.className = 'tag-filter-item';
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = name;
                cb.checked = state.selectedTags.has(name);
                cb.addEventListener('change', () => {
                    if (cb.checked) state.selectedTags.add(name);
                    else state.selectedTags.delete(name);
                    updateTagFilterLabel();
                    _onFilterChange();
                    fetchAndPopulateTagFilter();
                });
                label.appendChild(cb);
                label.appendChild(document.createTextNode(` ${name} (${count})`));
                tagFilterDropdown.appendChild(label);
            });
        }
    } catch (err) {
        console.error('Error fetching tags:', err);
    }
}

export async function fetchAndPopulateExtFilter() {
    try {
        const data = await fetchExtensionsRequest(state.currentDir, state.currentSubpath);
        if (!data) return;
        const extensions = data.extensions || [];
        const currentVal = extFilter.value;
        extFilter.innerHTML = '<option value="">All</option>';
        extensions.forEach(({ ext, count }) => {
            const option = document.createElement('option');
            option.value = ext;
            option.textContent = `${ext} (${count})`;
            extFilter.appendChild(option);
        });
        if (currentVal && extensions.some(e => e.ext === currentVal)) extFilter.value = currentVal;
    } catch (err) {
        console.error('Error fetching extensions:', err);
    }
}

export async function fetchTagSuggestions() {
    try {
        const results = await Promise.all(
            ['gallery', 'uploads'].map(d =>
                fetch(`/tags?dir=${encodeURIComponent(d)}`).then(r => r.json()).catch(() => ({ tags: [] }))
            )
        );
        const tagSet = new Set();
        results.forEach(data => (data.tags || []).forEach(t => tagSet.add(t.name)));
        state._cachedTagSuggestions = Array.from(tagSet).sort();
    } catch {
        state._cachedTagSuggestions = [];
    }
}

export function createTagChipsElement(tags) {
    const container = document.createElement('div');
    container.className = 'tag-chips-container';
    const displayTags = tags.slice(0, 2);
    const overflowTags = tags.slice(2);
    displayTags.forEach(tag => {
        const chip = document.createElement('span');
        chip.className = 'tag-chip';
        chip.textContent = tag;
        container.appendChild(chip);
    });
    if (overflowTags.length > 0) {
        const ellipsis = document.createElement('span');
        ellipsis.className = 'tag-chip tag-ellipsis';
        ellipsis.textContent = `+${overflowTags.length}`;
        const tooltip = document.createElement('span');
        tooltip.className = 'tag-overflow-tooltip';
        tooltip.textContent = overflowTags.join(', ');
        ellipsis.appendChild(tooltip);
        container.appendChild(ellipsis);
    }
    return container;
}

export function updateThumbnailTags(filename, tags) {
    document.querySelectorAll('.gallery .image-container').forEach(container => {
        const containerFilename = container.dataset.filename;
        if (containerFilename === filename) {
            container.dataset.tags = JSON.stringify(tags);
            const existing = container.querySelector('.tag-chips-container');
            const newChips = createTagChipsElement(tags);
            if (existing) existing.replaceWith(newChips);
            else container.querySelector('.image-wrapper').appendChild(newChips);
        }
    });
}

export function showLightboxTags(dir, filename, tags) {
    const container = document.getElementById('lightbox-tags');
    container.innerHTML = '';

    tags.forEach(tag => {
        const chip = document.createElement('span');
        chip.className = 'tag-chip tag-chip-deletable';
        chip.textContent = tag;

        const del = document.createElement('span');
        del.className = 'tag-chip-delete';
        del.textContent = '×';
        del.addEventListener('click', async e => {
            e.stopPropagation();
            const newTags = await removeTagRequest(dir, filename, tag);
            if (newTags !== null) {
                showLightboxTags(dir, filename, newTags);
                updateThumbnailTags(filename, newTags);
                fetchAndPopulateTagFilter();
            }
        });
        chip.appendChild(del);
        container.appendChild(chip);
    });

    const addChip = document.createElement('span');
    addChip.className = 'tag-add-chip';
    addChip.textContent = '+';

    addChip.addEventListener('click', e => {
        e.stopPropagation();

        const wrapper = document.createElement('div');
        wrapper.className = 'tag-input-popup-wrapper';

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'tag-input-popup';
        input.placeholder = 'tag name';

        const dropdown = document.createElement('div');
        dropdown.className = 'tag-input-popup-dropdown';

        let highlightIndex = -1;

        function updateDropdown() {
            const query = input.value.toLowerCase();
            dropdown.innerHTML = '';
            highlightIndex = -1;
            if (!query) { dropdown.style.display = 'none'; return; }
            const currentTags = new Set(
                Array.from(container.querySelectorAll('.tag-chip')).map(c => c.childNodes[0].textContent.trim())
            );
            const matches = state._cachedTagSuggestions
                .filter(t => t.includes(query) && !currentTags.has(t))
                .slice(0, 8);
            if (!matches.length) { dropdown.style.display = 'none'; return; }
            matches.forEach(t => {
                const item = document.createElement('div');
                item.className = 'tag-pending-dropdown-item';
                item.textContent = t;
                item.addEventListener('mousedown', ev => { ev.preventDefault(); commitTag(t); });
                dropdown.appendChild(item);
            });
            dropdown.style.display = 'block';
        }

        function highlightItem(idx) {
            const items = dropdown.querySelectorAll('.tag-pending-dropdown-item');
            items.forEach((el, i) => el.classList.toggle('highlighted', i === idx));
            highlightIndex = idx;
        }

        async function commitTag(tag) {
            dropdown.style.display = 'none';
            if (tag) {
                const newTags = await apiAddTag(dir, filename, tag);
                if (newTags !== null) {
                    showLightboxTags(dir, filename, newTags);
                    updateThumbnailTags(filename, newTags);
                    fetchAndPopulateTagFilter();
                    return;
                }
            }
            if (wrapper.parentNode === container) container.replaceChild(addChip, wrapper);
        }

        input.addEventListener('input', () => {
            const coerced = input.value.toLowerCase().replace(/[^a-z0-9_-]/g, '');
            if (input.value !== coerced) input.value = coerced;
            updateDropdown();
        });

        input.addEventListener('keydown', async ke => {
            const items = dropdown.querySelectorAll('.tag-pending-dropdown-item');
            if (ke.key === 'ArrowDown') {
                ke.preventDefault();
                highlightItem(Math.min(highlightIndex + 1, items.length - 1));
            } else if (ke.key === 'ArrowUp') {
                ke.preventDefault();
                highlightItem(Math.max(highlightIndex - 1, 0));
            } else if (ke.key === 'Enter') {
                ke.preventDefault();
                await commitTag(
                    highlightIndex >= 0 && items[highlightIndex]
                        ? items[highlightIndex].textContent
                        : input.value.trim()
                );
            } else if (ke.key === 'Escape') {
                if (dropdown.style.display === 'block') {
                    ke.stopPropagation();
                    dropdown.style.display = 'none';
                } else if (wrapper.parentNode === container) {
                    container.replaceChild(addChip, wrapper);
                }
            }
        });

        input.addEventListener('blur', () => {
            setTimeout(() => {
                dropdown.style.display = 'none';
                if (wrapper.parentNode === container) container.replaceChild(addChip, wrapper);
            }, 150);
        });

        wrapper.appendChild(input);
        wrapper.appendChild(dropdown);
        container.replaceChild(wrapper, addChip);
        input.focus();
        fetchTagSuggestions();
    });

    container.appendChild(addChip);
}

export function initTagModal(selectedFiles) {
    const list = document.getElementById('tag-pending-list');
    list.innerHTML = '';
    fetchTagSuggestions().then(() => addPendingInputChip(list));

    document.getElementById('tag-apply-btn').onclick = async () => {
        const tags = Array.from(list.querySelectorAll('.tag-pending-chip'))
            .map(el => el.dataset.tag)
            .filter(Boolean);
        const activeInput = list.querySelector('.tag-pending-input');
        if (activeInput) {
            const val = activeInput.value.trim();
            if (val) tags.push(val);
        }
        if (tags.length === 0) return;

        hideModal();

        const requests = [];
        const lastTagsByFile = {};
        for (const filename of selectedFiles) {
            for (const tag of tags) {
                requests.push(
                    apiAddTag(state.currentDir, filename, tag).then(newTags => {
                        if (newTags !== null) lastTagsByFile[filename] = newTags;
                    })
                );
            }
        }
        await Promise.all(requests);
        for (const [filename, newTags] of Object.entries(lastTagsByFile)) {
            updateThumbnailTags(filename, newTags);
        }
        fetchAndPopulateTagFilter();
    };
}

export function addPendingInputChip(list) {
    const wrapper = document.createElement('div');
    wrapper.className = 'tag-pending-input-wrapper';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'tag-pending-input';
    input.placeholder = 'tag name\u2026';

    const dropdown = document.createElement('div');
    dropdown.className = 'tag-pending-dropdown';

    let highlightIndex = -1;

    function updateDropdown() {
        const query = input.value.toLowerCase();
        dropdown.innerHTML = '';
        highlightIndex = -1;
        if (!query) { dropdown.style.display = 'none'; return; }
        const alreadyAdded = new Set(
            Array.from(list.querySelectorAll('.tag-pending-chip')).map(c => c.dataset.tag)
        );
        const matches = state._cachedTagSuggestions
            .filter(t => t.includes(query) && !alreadyAdded.has(t))
            .slice(0, 8);
        if (!matches.length) { dropdown.style.display = 'none'; return; }
        matches.forEach(t => {
            const item = document.createElement('div');
            item.className = 'tag-pending-dropdown-item';
            item.textContent = t;
            item.addEventListener('mousedown', e => { e.preventDefault(); commitTag(t); });
            dropdown.appendChild(item);
        });
        dropdown.style.display = 'block';
    }

    function highlightItem(idx) {
        const items = dropdown.querySelectorAll('.tag-pending-dropdown-item');
        items.forEach((el, i) => el.classList.toggle('highlighted', i === idx));
        highlightIndex = idx;
    }

    function commitTag(tag) {
        dropdown.style.display = 'none';
        list.insertBefore(createPendingFilledChip(tag), wrapper);
        input.value = '';
        input.style.width = '80px';
        updateDropdown();
        input.focus();
    }

    input.addEventListener('input', () => {
        const coerced = input.value.toLowerCase().replace(/[^a-z0-9_-]/g, '');
        if (input.value !== coerced) input.value = coerced;
        input.style.width = Math.max(80, input.value.length * 7.5 + 24) + 'px';
        updateDropdown();
    });

    input.addEventListener('keydown', e => {
        const items = dropdown.querySelectorAll('.tag-pending-dropdown-item');
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            highlightItem(Math.min(highlightIndex + 1, items.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            highlightItem(Math.max(highlightIndex - 1, 0));
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (highlightIndex >= 0 && items[highlightIndex]) commitTag(items[highlightIndex].textContent);
            else { const tag = input.value.trim(); if (tag) commitTag(tag); }
        } else if (e.key === 'Escape') {
            if (dropdown.style.display === 'block') { e.stopPropagation(); dropdown.style.display = 'none'; }
        }
    });

    input.addEventListener('blur', () => {
        setTimeout(() => { dropdown.style.display = 'none'; }, 150);
    });

    wrapper.appendChild(input);
    wrapper.appendChild(dropdown);
    list.appendChild(wrapper);
    setTimeout(() => input.focus(), 50);
    return wrapper;
}

export function createPendingFilledChip(tag) {
    const chip = document.createElement('span');
    chip.className = 'tag-pending-chip';
    chip.dataset.tag = tag;

    const text = document.createElement('span');
    text.textContent = tag;
    chip.appendChild(text);

    const del = document.createElement('span');
    del.className = 'tag-pending-chip-delete';
    del.textContent = '×';
    del.addEventListener('click', () => chip.remove());
    chip.appendChild(del);

    return chip;
}
