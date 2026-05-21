
const FILTERS = ['year','paperNum','variantNum','subtopic','difficulty','objective','marks','bloom','command','layout'];
// Initial state per filter is read from the .tab-btn.active rendered by the
// Python builder. Filters with no active button (server didn't pick a default)
// fall back to 'all'. This lets each topic page choose its own defaults
// without baking them into JS.
function initialDefaultFor(f) {
    const btn = document.querySelector('.tab-group[data-filter="' + f + '"] .tab-btn.active');
    return btn ? btn.dataset.value : 'all';
}
const FILTER_DEFAULTS = Object.fromEntries(FILTERS.map(f => [f, initialDefaultFor(f)]));
const filterDefault = (f) => FILTER_DEFAULTS[f];
const state = Object.fromEntries(FILTERS.map(f => [f, filterDefault(f)]));

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
    updateFilterSummary();
}

function bindFilterCollapse() {
    document.querySelectorAll('.filter-bar').forEach(bar => {
        const toggle = bar.querySelector('.filter-toggle');
        if (!toggle) return;
        toggle.addEventListener('click', () => {
            const collapsed = bar.classList.toggle('collapsed');
            toggle.setAttribute('aria-expanded', String(!collapsed));
        });
    });
}

function updateFilterSummary() {
    const el = document.querySelector('.filter-summary');
    if (!el) return;
    const activeCount = Object.entries(state)
        .filter(([k, v]) => v !== filterDefault(k))
        .length;
    const shown = document.getElementById('counter-shown')?.textContent;
    const total = document.getElementById('counter-total')?.textContent;
    const parts = [];
    if (activeCount > 0) parts.push(`${activeCount} active`);
    if (shown && total) parts.push(`${shown} of ${total} questions`);
    el.textContent = parts.length ? '· ' + parts.join(' · ') : '';
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
        FILTERS.forEach(f => state[f] = filterDefault(f));
        document.querySelectorAll('.tab-group[data-filter]').forEach(group => {
            const filter = group.dataset.filter;
            const def = filterDefault(filter);
            group.querySelectorAll('.tab-btn').forEach(b =>
                b.classList.toggle('active', b.dataset.value === def)
            );
        });
        applyFilters();
    });
}

bindFilterTabs();
bindActions();
bindFilterCollapse();
applyFilters();
