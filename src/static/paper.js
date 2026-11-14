
document.querySelectorAll('.q-header').forEach(h => {
    h.addEventListener('click', () => h.closest('.card').classList.toggle('open'));
});
