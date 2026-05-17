
const FILTERS = ['subtopic','difficulty','objective','bloom','command','marks','year'];
const state = Object.fromEntries(FILTERS.map(f => [f, 'all']));

function matchesMarks(card) {
    if (state.marks === 'all') return true;
    const m = parseInt(card.dataset.marks, 10);
    if (Number.isNaN(m)) return false;
    if (state.marks === '5+') return m >= 5;
    return m === parseInt(state.marks, 10);
}

function cardMatches(card) {
    for (const f of FILTERS) {
        if (f === 'marks') { if (!matchesMarks(card)) return false; continue; }
        if (state[f] !== 'all' && card.dataset[f] !== state[f]) return false;
    }
    return true;
}

function applyFilters() {
    const cards = document.querySelectorAll('.card');
    let shown = 0;
    cards.forEach(card => {
        const match = cardMatches(card);
        card.style.display = match ? '' : 'none';
        if (match) shown++;
    });
    document.getElementById('counter-shown').textContent = shown;
    document.getElementById('counter-total').textContent = cards.length;
    const empty = document.getElementById('empty-state');
    if (empty) empty.style.display = shown === 0 ? '' : 'none';
}

function bindFilterTabs() {
    document.querySelectorAll('.tab-group[data-filter]').forEach(group => {
        const filter = group.dataset.filter;
        group.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.disabled) return;
                state[filter] = btn.dataset.value;
                group.querySelectorAll('.tab-btn').forEach(b =>
                    b.classList.toggle('active', b.dataset.value === state[filter])
                );
                applyFilters();
            });
        });
    });
}

function bindActions() {
    const expandAll = document.getElementById('btn-expand-all');
    const collapseAll = document.getElementById('btn-collapse-all');
    const reset = document.getElementById('btn-reset');

    if (expandAll) expandAll.addEventListener('click', () => {
        document.querySelectorAll('.card').forEach(c => {
            if (c.style.display !== 'none') c.classList.add('open');
        });
    });
    if (collapseAll) collapseAll.addEventListener('click', () => {
        document.querySelectorAll('.card').forEach(c => c.classList.remove('open'));
    });
    if (reset) reset.addEventListener('click', () => {
        FILTERS.forEach(f => state[f] = 'all');
        document.querySelectorAll('.tab-group[data-filter]').forEach(group => {
            group.querySelectorAll('.tab-btn').forEach(b =>
                b.classList.toggle('active', b.dataset.value === 'all')
            );
        });
        applyFilters();
    });
}

bindFilterTabs();
bindActions();
applyFilters();
