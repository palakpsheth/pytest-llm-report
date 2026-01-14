// pytest-llm-report interactive features

// Global state for filters
const activeStatuses = new Set(['passed', 'failed', 'skipped', 'xfailed', 'xpassed', 'error']);

// Filter tests based on search input and outcome filters
function filterTests() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    document.querySelectorAll('.test-row').forEach(row => {
        const nodeid = row.querySelector('.test-name').textContent.toLowerCase();
        const statusMatch = row.dataset.status ? activeStatuses.has(row.dataset.status) : false;
        const matchesSearch = nodeid.includes(query);
        row.classList.toggle('hidden', !matchesSearch || !statusMatch);
    });
}

// Show only failures and scroll to list
function showFailuresOnly() {
    document.querySelectorAll('.filter-chip input').forEach(cb => {
        const s = cb.dataset.status;
        if (s === 'failed' || s === 'error') {
            cb.checked = true;
            activeStatuses.add(s);
        } else {
            cb.checked = false;
            activeStatuses.delete(s);
        }
    });
    filterTests();
    const testList = document.getElementById('test-list');
    if (testList) {
        testList.scrollIntoView({ behavior: 'smooth' });
    }
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

    // Toggle dark mode on preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.dataset.theme = 'dark';
    }

    // Default: expand all details
    document.querySelectorAll('details').forEach(details => {
        details.setAttribute('open', '');
    });

    const params = new URLSearchParams(window.location.search);
    if (params.get('pdf') === '1') {
        document.body.classList.add('pdf-mode');
    }
});
