document.addEventListener('click', function (e) {
    var overlay = document.getElementById('plot-lightbox');
    if (!overlay) return;

    // Open: click on a plot image
    var img = e.target.closest('.plot-img');
    if (img) {
        document.getElementById('lightbox-img').src = img.src;
        overlay.style.display = 'flex';
        return;
    }

    // Close: click on overlay background or the × button
    if (e.target === overlay || e.target.id === 'lightbox-close') {
        overlay.style.display = 'none';
    }
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        var overlay = document.getElementById('plot-lightbox');
        if (overlay) overlay.style.display = 'none';
    }
});
