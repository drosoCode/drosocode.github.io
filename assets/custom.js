document.querySelectorAll('.lightgallery_custom').forEach(el => {
    lightGallery(el, {
        selector: 'a',
        plugins: [lgThumbnail],
        thumbnail: true,
        download: false,
    });
});