const sourceFilter = document.querySelector('#source-filter');
const toneFilter = document.querySelector('#tone-filter');
const statusFilter = document.querySelector('#status-filter');
const rows = Array.from(document.querySelectorAll('.appeals-table tbody tr'));

function applyFilters() {
  const source = sourceFilter?.value || '';
  const tone = toneFilter?.value || '';
  const status = statusFilter?.value || '';
  rows.forEach(row => {
    const visible = (!source || row.dataset.source === source)
      && (!tone || row.dataset.tone === tone)
      && (!status || row.dataset.status === status);
    row.style.display = visible ? '' : 'none';
  });
}
[sourceFilter, toneFilter, statusFilter].forEach(item => item?.addEventListener('change', applyFilters));
