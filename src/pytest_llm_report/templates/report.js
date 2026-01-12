// pytest-llm-report interactive features

// Global state for filters
const activeStatuses = new Set(['passed', 'failed', 'skipped', 'xfailed', 'xpassed', 'error']);

// Filter tests based on search input and outcome filters
function filterTests() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    document.querySelectorAll('.test-row').forEach(row => {
        const nodeid = row.querySelector('.test-name').textContent.toLowerCase();
        const statusMatch = Array.from(activeStatuses).some(status => row.classList.contains(status));
        const matchesSearch = nodeid.includes(query);
        row.classList.toggle('hidden', !matchesSearch || !statusMatch);
    });
}

// Toggle visibility of status filters
function toggleStatus(checkbox) {
    const status = checkbox.dataset.status;
    if (checkbox.checked) {
        activeStatuses.add(status);
    } else {
        activeStatuses.delete(status);
    }
    filterTests();
}

// Initialize interactive features after DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // Filter by outcome (for button-based filtering if present)
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const filter = btn.dataset.filter;

            // Update active state
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Filter tests by outcome class
            document.querySelectorAll('.test-row').forEach(test => {
                if (filter === 'all') {
                    test.classList.remove('hidden');
                } else {
                    const matchesFilter = test.classList.contains(filter);
                    test.classList.toggle('hidden', !matchesFilter);
                }
            });
        });
    });

    // Toggle dark mode on preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.dataset.theme = 'dark';
    }
});
