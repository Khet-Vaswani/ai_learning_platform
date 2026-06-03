// ============================================================
// AI Learn Dashboard - Modern JavaScript
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeNotifications();
    initializeSearch();
    initializeVideoCards();
});

/**
 * Initialize Notifications
 */
function initializeNotifications() {
    const notifBtn = document.getElementById('notifBtn');
    const notifDropdown = document.getElementById('notificationDropdown');

    if (notifBtn && notifDropdown) {
        notifBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            notifDropdown.classList.toggle('active');
        });

        document.addEventListener('click', function(e) {
            if (!notifBtn.contains(e.target) && !notifDropdown.contains(e.target)) {
                notifDropdown.classList.remove('active');
            }
        });
    }
}

/**
 * Initialize Search
 */
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function(e) {
            const query = e.target.value;
            if (query.length > 2) {
                performSearch(query);
            }
        }, 300));
    }
}

function performSearch(query) {
    console.log('Searching for:', query);
    // Implement search functionality
    fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
    })
    .then(r => r.json())
    .then(data => {
        console.log('Search results:', data);
        // Display search results
    })
    .catch(err => console.error('Search error:', err));
}

/**
 * Initialize Video Cards Click Handlers
 */
function initializeVideoCards() {
    // Continue watching videos
    document.querySelectorAll('#continueCarousel .video-card').forEach(card => {
        card.addEventListener('click', function() {
            // Navigate to video player
            console.log('Playing video');
        });
    });

    // Recommendation cards
    document.querySelectorAll('.recommendation-card').forEach(card => {
        card.addEventListener('click', function() {
            console.log('Opening recommendation');
        });

        const addBtn = card.querySelector('.btn-add-to-queue');
        if (addBtn) {
            addBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                addToQueue();
            });
        }
    });

    // History items
    document.querySelectorAll('.history-item').forEach(item => {
        const playBtn = item.querySelector('.btn-icon:first-child');
        const noteBtn = item.querySelector('.btn-icon:nth-child(2)');
        const quizBtn = item.querySelector('.btn-icon:nth-child(3)');

        if (playBtn) playBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Continue video');
        });
        if (noteBtn) noteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('View notes');
        });
        if (quizBtn) quizBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Take quiz');
        });
    });
}

/**
 * Utility Functions
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function addToQueue() {
    alert('Added to your learning queue!');
}

/**
 * Load recommendations dynamically
 */
async function loadRecommendations() {
    try {
        const response = await fetch('/api/recommendations');
        const data = await response.json();
        updateRecommendationsUI(data.recommendations);
    } catch (error) {
        console.error('Error loading recommendations:', error);
    }
}

function updateRecommendationsUI(recommendations) {
    const grid = document.querySelector('.recommendations-grid');
    if (!grid) return;

    grid.innerHTML = recommendations.map(rec => `
        <div class="recommendation-card">
            <div class="rec-thumbnail">
                <img src="${rec.thumbnail}" alt="${rec.title}">
                <span class="rec-badge">${rec.reason}</span>
                <button class="btn-add-to-queue" title="Add to queue">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
            <div class="rec-content">
                <h3>${rec.title}</h3>
                <p class="rec-channel">${rec.channel}</p>
                <div class="rec-stats">
                    <span class="difficulty ${rec.difficulty.toLowerCase()}">${rec.difficulty}</span>
                    <span class="topic-tag">${rec.topic}</span>
                </div>
            </div>
        </div>
    `).join('');

    initializeVideoCards();
}

/**
 * Load weak topics dynamically
 */
async function loadWeakTopics() {
    try {
        const response = await fetch('/api/weak-topics');
        const data = await response.json();
        updateWeakTopicsUI(data.topics);
    } catch (error) {
        console.error('Error loading weak topics:', error);
    }
}

function updateWeakTopicsUI(topics) {
    const grid = document.querySelector('.weak-topics-grid');
    if (!grid) return;

    grid.innerHTML = topics.map(topic => `
        <div class="weak-topic-card">
            <div class="topic-header">
                <h3>${topic.name}</h3>
                <span class="fail-count">${topic.fail_count}× incorrect</span>
            </div>
            <p class="topic-desc">${topic.description}</p>
            <div class="topic-actions">
                <button class="btn-small btn-primary" onclick="watchTutorial(${topic.id})">
                    <i class="fas fa-video"></i> Watch Tutorial
                </button>
                <button class="btn-small btn-secondary" onclick="readNotes(${topic.id})">
                    <i class="fas fa-book"></i> Read Notes
                </button>
            </div>
        </div>
    `).join('');
}

function watchTutorial(topicId) {
    console.log('Watching tutorial for topic:', topicId);
    fetch(`/weak-topic/${topicId}/video`)
        .then(r => r.json())
        .then(data => {
            if (data.video_url) {
                window.location.href = `/video-player?video_id=${data.video_id}`;
            }
        });
}

function readNotes(topicId) {
    console.log('Reading notes for topic:', topicId);
    window.location.href = `/notes?topic_id=${topicId}`;
}

/**
 * Refresh dashboard data
 */
async function refreshDashboard() {
    await loadRecommendations();
    await loadWeakTopics();
    console.log('Dashboard refreshed');
}

/**
 * Export functions for global use
 */
window.watchTutorial = watchTutorial;
window.readNotes = readNotes;
window.refreshDashboard = refreshDashboard;
