# Copilot Instructions — RunPodTools Gallery

## Project Overview

A Python/Flask server (`serve.py`) that serves a media gallery UI. The front-end is a vanilla JS ES-module application located in `static/gallery/`. The HTML shell is in `templates/gallery.html`.

---

## Front-End Module Map (`static/gallery/`)

The front-end was split from a single `static/gallery.js` monolith into 15 focused ES modules. **Always load the relevant module(s) rather than the old monolith when making changes.**

### State & Infrastructure

| File | What it owns | Load when... |
|---|---|---|
| `state.js` | Single shared mutable `state` object: `page`, `loading`, `done`, `currentDir`, `currentSubpath`, `lastGallerySubpath`, `lastUploadsSubpath`, `fetchController`, `dirTreeCache`, `fileMetadataCache`, `metadataCache`, `loadedImages`, `selectedTags`, `_cachedTagSuggestions`, lightbox tracking vars, move target vars | Touching any shared state |
| `dom.js` | All `getElementById` / `querySelector` DOM element references as named exports | Referencing any DOM element |
| `utils.js` | `debounce`, `formatFileSize`, `escapeHtml`, `getSortLabel`, `insertSorted` | Adding/changing utility functions |
| `api.js` | **All `fetch` calls** as isolated async functions: `addTagRequest`, `removeTagRequest`, `setRatingRequest`, `fetchMetadataRequest`, `fetchTagsRequest`, `fetchExtensionsRequest`, `uploadFilesRequest`, `deleteFilesRequest`, `applyMoveRequest`, `fetchDirTree`, `fetchArchivesRequest`, `archiveRequest`, `extractArchiveRequest`, `mkdirRequest`, `fetchImagesRequest` | Changing any server API call or URL |
| `modal.js` | `showModal(step)`, `hideModal()`, `showInfo(title, html)` | Changing modal display logic |

### Feature Modules

| File | What it owns | Load when... |
|---|---|---|
| `metadata.js` | `fetchMetadata`, `displayMetadata`, `toggleMetadataPanel`, `closeMetadataPanel` — renders the side panel in the lightbox | Changing metadata display or panel behaviour |
| `tags.js` | Tag filter bar (`fetchAndPopulateTagFilter`, `fetchAndPopulateExtFilter`, `updateTagFilterLabel`), tag suggestions (`fetchTagSuggestions`), thumbnail chips (`createTagChipsElement`, `updateThumbnailTags`), lightbox inline tag editor (`showLightboxTags`), bulk tag modal (`initTagModal`, `addPendingInputChip`, `createPendingFilledChip`) | Any tag-related change |
| `ratings.js` | `createRatingWidget` (thumbnail star widget), `updateRatingDisplay`, `showLightboxRating` | Any rating-related change |
| `gallery-items.js` | `createImageElement`, `createVideoElement`, `createAudioElement` — builds individual thumbnail DOM nodes including checkboxes, hover animation, drag-start, lightbox click | Changing how thumbnails look or behave |
| `archives.js` | `populateArchives`, `reloadArchives` — renders the archives list view | Changing archive display |

### Navigation & Layout

| File | What it owns | Load when... |
|---|---|---|
| `navigation.js` | `loadMore` (paginated image fetch + DOM append), `reloadGallery`, `switchDirectory`, `navigateSubdir`, `updateActiveFolderButton`; also owns the directory tree panel: `renderDirTree`, `showDirPanel`, `scheduleDirPanelHide`, `cancelDirPanelHide`, and the new-folder input controls | Changing directory switching, infinite scroll, folder tree, or subpath navigation |
| `lightbox.js` | Lightbox open/close, backdrop click, animation frame controls (play / first-frame / last-frame buttons), `lightboxImg` load handler, metadata panel toggle wiring | Changing lightbox behaviour or animation controls |
| `upload.js` | `uploadFiles`, drag-drop listeners, file-input listener (`initUploadListeners`) | Changing upload behaviour |
| `toolbar.js` | Toolbar click delegation (select-all, clear, reload, zip, tag, move, delete), `getSelectedImages`, `reloadStaticFrames`, `deleteFiles`, `initZipHandler`, `openMoveModal`, move tree rendering (`renderMoveTreeSection`, `createMoveRow`), `applyMove`, `initToolbar` | Any toolbar action |
| `main.js` | **Entry point only** — imports everything, attaches top-level event listeners (sort, filter, scroll, modal keyboard/outside-click, dir panel hover, archives button), calls `loadMore` / `fetchAndPopulateTagFilter` / `fetchAndPopulateExtFilter` on init | Adding new top-level event listeners; wiring new modules |

---

## Key Patterns

### Shared state
All modules import the `state` object from `state.js` and mutate its properties directly:
```js
import { state } from './state.js';
state.page = 0;
state.currentDir = 'uploads';
```
Never introduce new module-level `let` variables for data that needs to be shared across modules — put them in `state.js`.

### API layer
Every `fetch` call belongs in `api.js`. Feature modules call those functions; they do not call `fetch` directly. When the server adds a new endpoint, add a function to `api.js` first.

### Avoiding circular dependencies (Dependency Inversion)
Circular imports between modules must not be introduced. If module A needs to call a function owned by module B, and B already imports from A, the solution is **callback injection** via an `init` function rather than a cross-import.

`navigation.js` and `tags.js` would otherwise be circular (`navigation` calls `fetchAndPopulateTagFilter`; `tags` calls `reloadGallery`). This is broken by having each module expose an `init` function that accepts the dependency as a callback, which `main.js` supplies at startup:

```js
// main.js (composition root)
initNavigation({ onAfterNavigate: () => {
    fetchAndPopulateTagFilter();
    fetchAndPopulateExtFilter();
}});
initTagFilter({ onFilterChange: reloadGallery });
```

Neither module imports the other. `main.js`, as the composition root, is the only place that knows about both.

Apply the same pattern for any future case where two modules would otherwise need to import each other.

### HTML entry point
`templates/gallery.html` loads the app via:
```html
<script type="module" src="/static/gallery/main.js"></script>
```
All DOM element IDs are defined in `gallery.html`; `dom.js` is the single place that queries them.

### Media type data attributes (DOM as self-indexing registry)
Every gallery card container (`.image-container`) carries three data attributes stamped by `navigation.js` and `upload.js` immediately after the factory call:

| Attribute | Values | Purpose |
|---|---|---|
| `data-media-type` | `'image'` \| `'video'` \| `'audio'` | Identifies the media kind without querying children |
| `data-is-animated` | `'true'` \| `'false'` | True only for WebP animations |
| `data-mime-type` | `'video/mp4'` \| `'audio/mpeg'` \| `'image/webp'` \| `'image/png'` \| `'image/jpeg'` | Used in drag-and-drop `DownloadURL` and lightbox drag |

**Rules:**
- Never query `container.querySelector('video')`, `querySelector('img')`, or `querySelector('audio')` to determine media type or filename. Use `container.dataset.mediaType` and `container.dataset.filename` instead.
- Never hardcode MIME strings (`'video/mp4'`, `'audio/mpeg'`). Read `container.dataset.mimeType` (or `lightboxVideo.dataset.mimeType` in the lightbox drag handler).
- When adding a new media type, add a factory function in `gallery-items.js`, a dispatch branch in both `navigation.js` and `upload.js`, and stamp the three attributes there.
- Use CSS attribute selectors when you only need a subset of containers: e.g. `'.image-container[data-is-animated="true"]'` to find all WebP cards without scanning children.

---

## Maintaining These Instructions

After any significant refactor, update this file to reflect the new patterns before closing the task. A refactor is significant if it:
- Establishes a new convention that future changes should follow (e.g. a new data attribute contract, a new abstraction layer, a new module)
- Eliminates a pattern that was previously correct but is now wrong
- Changes the rules for how a named module, attribute, or function should be used

### What to document

For each significant refactor, add or update:
1. **The pattern itself** — what the new rule is and where it lives
2. **The motivation** — one sentence on why the old approach was replaced
3. **The rules** — specific do/don't statements a future agent can act on unambiguously
4. **A change guide row** — what files to touch when extending the pattern

### Example — Media type data attributes (May 2026)

**Old pattern (eliminated):** Code throughout `toolbar.js`, `ratings.js`, `tags.js`, and `gallery-items.js` queried `container.querySelector('video')`, `querySelector('img')`, and `querySelector('audio')` to determine the media type and filename of a card, and hardcoded MIME strings like `'video/mp4'` in drag handlers.

**Problem:** Every new media type required finding and updating all these scattered query sites. The `upload.js` dispatch was a copy of `navigation.js` and went out of sync when MP3 support was added, silently routing audio uploads to `createImageElement`.

**New pattern:** Three data attributes are stamped on every `.image-container` immediately after the factory call in `navigation.js` and `upload.js`:
- `dataset.filename` — the bare filename, used for all card-to-filename lookups
- `dataset.mediaType` — `'image'` | `'video'` | `'audio'`
- `dataset.isAnimated` — `'true'` | `'false'`
- `dataset.mimeType` — e.g. `'video/mp4'`, `'audio/mpeg'`, `'image/webp'`

All downstream code reads these attributes. No module outside `gallery-items.js` queries child elements to determine type or filename.

See the "Media type data attributes" section under Key Patterns for the full rules.

---

## Back-End Files

| File | Purpose |
|---|---|
| `serve.py` | Flask app, all API routes (`/images`, `/tag`, `/untag`, `/rate`, `/metadata`, `/upload`, `/delete`, `/move`, `/archive`, `/dirs`, `/mkdir`, etc.) |
| `images.py` | Image listing, filtering, sorting logic |
| `tags.py` | Tag read/write helpers |
| `ratings.py` | Rating read/write helpers |
| `gallery.py` / `gallery_source.py` | Gallery source configuration |
| `mp4.py` | MP4 thumbnail/duration helpers |
| `webp.py` | WebP frame extraction helpers |
| `mp3.py` | MP3 duration extraction via `mutagen` |
| `push.py` / `receive.py` | Asset sync utilities |

---

## Common Change Guide

| Task | Files to load |
|---|---|
| Add a new media type | `gallery-items.js` (new `createXElement`), `navigation.js` + `upload.js` (dispatch + stamp 3 data attributes), `gallery_source.py` + `gallery.py` (extension whitelists), `gallery.html` (accept attr + lightbox element), `dom.js` (lightbox element export), `lightbox.js` (close handler reset) |
| Change how images/videos are fetched from server | `api.js` → `fetchImagesRequest`, `navigation.js` → `loadMore` |
| Add a new tag action | `api.js` + `tags.js` |
| Change lightbox appearance or controls | `lightbox.js`, `gallery-items.js` (click handler) |
| Add a toolbar button | `toolbar.js` → `initToolbar`, `templates/gallery.html` |
| Change directory tree behaviour | `navigation.js` → `renderDirTree` / `renderTreeNode` |
| Add a new server endpoint | `serve.py` + `api.js` |
| Change rating widget | `ratings.js` |
| Change thumbnail DOM structure | `gallery-items.js` |
| Change modal steps | `modal.js` + `templates/gallery.html` |
