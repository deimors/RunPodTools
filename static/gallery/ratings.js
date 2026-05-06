import { state } from './state.js';
import { lightboxRating, ratingFilter } from './dom.js';
import { setRatingRequest } from './api.js';

export async function setRating(filename, rating) {
    return setRatingRequest(state.currentDir, filename, rating);
}

export function createRatingWidget(filename, currentRating = 0) {
    const ratingContainer = document.createElement('div');
    ratingContainer.className = 'rating-container';
    if (currentRating > 0) ratingContainer.classList.add('rated');

    for (let i = 1; i <= 3; i++) {
        const star = document.createElement('span');
        star.className = 'star';
        star.innerHTML = '★';
        star.dataset.starIndex = i;
        if (i <= currentRating) star.classList.add('filled');

        star.addEventListener('mouseenter', () => {
            ratingContainer.querySelectorAll('.star').forEach((s, idx) => {
                s.classList.toggle('hover', idx < i);
            });
        });

        star.addEventListener('click', async e => {
            e.stopPropagation();
            const newRating = currentRating === i ? 0 : i;
            if (await setRating(filename, newRating)) {
                updateRatingDisplay(ratingContainer, newRating);
                currentRating = newRating;
                const filterValue = ratingFilter.value;
                if (filterValue !== 'all' && newRating !== parseInt(filterValue)) {
                    ratingContainer.closest('.image-container')?.remove();
                }
            }
        });

        ratingContainer.appendChild(star);
    }

    ratingContainer.addEventListener('mouseleave', () => {
        ratingContainer.querySelectorAll('.star').forEach(s => s.classList.remove('hover'));
    });

    return ratingContainer;
}

export function updateRatingDisplay(ratingContainer, rating) {
    ratingContainer.querySelectorAll('.star').forEach((star, index) => {
        star.classList.toggle('filled', index < rating);
    });
    ratingContainer.classList.toggle('rated', rating > 0);
}

export function showLightboxRating(filename, currentRating = 0) {
    lightboxRating.innerHTML = '';

    for (let i = 1; i <= 3; i++) {
        const star = document.createElement('span');
        star.className = 'star';
        star.innerHTML = '★';
        star.dataset.starIndex = i;
        if (i <= currentRating) star.classList.add('filled');

        star.addEventListener('mouseenter', () => {
            lightboxRating.querySelectorAll('.star').forEach((s, idx) => {
                s.classList.toggle('hover', idx < i);
            });
        });

        star.addEventListener('click', async e => {
            e.stopPropagation();
            const newRating = currentRating === i ? 0 : i;
            if (await setRating(filename, newRating)) {
                showLightboxRating(filename, newRating);
                currentRating = newRating;
                const filterValue = ratingFilter.value;
                const containers = document.querySelectorAll('.gallery .image-container');
                if (filterValue !== 'all' && newRating !== parseInt(filterValue)) {
                    containers.forEach(container => {
                        const video = container.querySelector('video');
                        const img = container.querySelector('img');
                        if ((video?.dataset.filename || img?.alt) === filename) container.remove();
                    });
                } else {
                    containers.forEach(container => {
                        const ratingWidget = container.querySelector('.rating-container');
                        const video = container.querySelector('video');
                        const img = container.querySelector('img');
                        if ((video?.dataset.filename || img?.alt) === filename && ratingWidget) {
                            updateRatingDisplay(ratingWidget, newRating);
                        }
                    });
                }
            }
        });

        lightboxRating.appendChild(star);
    }

    lightboxRating.addEventListener('mouseleave', () => {
        lightboxRating.querySelectorAll('.star').forEach(s => s.classList.remove('hover'));
    });
}
