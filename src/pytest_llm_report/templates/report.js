// pytest-llm-report interactive features
(function () {
    'use strict';

    // Filter by outcome
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const filter = btn.dataset.filter;

            // Update active state
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Filter tests
            document.querySelectorAll('.test').forEach(test => {
                if (filter === 'all') {
                    test.classList.remove('hidden');
                } else {
                    const outcome = test.dataset.outcome;
                    test.classList.toggle('hidden', outcome !== filter);
                }
            });
        });
    });

    // Search
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const query = searchInput.value.toLowerCase();

            document.querySelectorAll('.test').forEach(test => {
                const nodeid = test.querySelector('.nodeid').textContent.toLowerCase();
                test.classList.toggle('hidden', !nodeid.includes(query));
            });

            // Reset filter buttons
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('.filter-btn[data-filter="all"]').classList.add('active');
        });
    }

    // Toggle dark mode on preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.dataset.theme = 'dark';
    }
})();
