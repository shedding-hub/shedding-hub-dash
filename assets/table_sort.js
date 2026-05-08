document.addEventListener('click', function (e) {
    var th = e.target.closest('.sortable-th');
    if (!th) return;

    var table = th.closest('table');
    if (!table) return;

    var colIdx = Array.from(th.parentNode.children).indexOf(th);
    var asc = th.getAttribute('data-sort') !== 'asc';

    // Reset all headers in this table
    table.querySelectorAll('.sortable-th').forEach(function (h) {
        h.removeAttribute('data-sort');
    });
    th.setAttribute('data-sort', asc ? 'asc' : 'desc');

    var tbody = table.querySelector('tbody');
    if (!tbody) return;

    var rows = Array.from(tbody.querySelectorAll('tr'));

    rows.sort(function (a, b) {
        var aText = (a.cells[colIdx] ? a.cells[colIdx].textContent.trim() : '');
        var bText = (b.cells[colIdx] ? b.cells[colIdx].textContent.trim() : '');

        var aNum = parseFloat(aText);
        var bNum = parseFloat(bText);
        var numeric = !isNaN(aNum) && !isNaN(bNum);

        var cmp = numeric ? (aNum - bNum) : aText.localeCompare(bText);
        return asc ? cmp : -cmp;
    });

    rows.forEach(function (row) { tbody.appendChild(row); });
});
