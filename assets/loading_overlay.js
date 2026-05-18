(function () {
    var pendingRequests = 0;

    function setOverlay(visible) {
        var overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = visible ? 'block' : 'none';
        }
    }

    var originalFetch = window.fetch;
    window.fetch = function (url) {
        var isDashUpdate = typeof url === 'string' && url.indexOf('_dash-update-component') !== -1;
        if (!isDashUpdate) {
            return originalFetch.apply(this, arguments);
        }

        pendingRequests++;
        setOverlay(true);

        return originalFetch.apply(this, arguments).then(function (response) {
            pendingRequests--;
            if (pendingRequests <= 0) { pendingRequests = 0; setOverlay(false); }
            return response;
        }, function (err) {
            pendingRequests--;
            if (pendingRequests <= 0) { pendingRequests = 0; setOverlay(false); }
            throw err;
        });
    };
}());
