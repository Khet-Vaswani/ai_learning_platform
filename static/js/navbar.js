/* ===== Modern AI Learning Platform Navbar JavaScript ===== */

class NavbarManager {
    constructor() {
        // DOM Elements
        this.navbar = document.getElementById('mainNavbar');
        this.searchInput = document.getElementById('searchInput');
        this.mobileSearchInput = document.getElementById('mobileSearchInput');
        this.searchSuggestions = document.getElementById('searchSuggestions');
        this.suggestionsList = document.getElementById('suggestionsList');
        this.trendingList = document.getElementById('trendingList');
        this.mobileSuggestions = document.getElementById('mobileSuggestions');

        // Action Buttons
        this.mobileSearchTriggerBtn = document.getElementById('mobileSearchTriggerBtn');
        this.aiAssistantBtn = document.getElementById('aiAssistantBtn');
        this.notificationBtn = document.getElementById('notificationBtn');
        this.notificationPanel = document.getElementById('notificationPanel');
        this.notificationBadge = document.getElementById('notificationBadge');
        this.themeToggleBtn = document.getElementById('themeToggleBtn');
        this.profileBtn = document.getElementById('profileBtn');
        this.profilePanel = document.getElementById('profilePanel');
        this.hamburgerBtn = document.getElementById('hamburgerBtn');

        // Mobile Elements
        this.mobileSearchPanel = document.getElementById('mobileSearchPanel');
        this.mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
        this.mobileMenu = document.getElementById('mobileMenu');
        this.closeSearchBtn = document.getElementById('closeSearchBtn');
        this.closeMenuBtn = document.getElementById('closeMenuBtn');

        // Voice Search Buttons
        this.voiceSearchBtn = document.getElementById('voiceSearchBtn');
        this.mobileVoiceBtn = document.getElementById('mobileVoiceBtn');

        // Logout Button
        this.logoutBtn = document.getElementById('logoutBtn');

        // State
        this.isDarkMode = false;
        this.recentSearches = this.sanitizeRecentSearches(
            JSON.parse(localStorage.getItem('recentSearches')) || []
        );
        localStorage.setItem('recentSearches', JSON.stringify(this.recentSearches));
        this.isVoiceSearching = false;
        this.recognition = null;
        this.activeSuggestionIndex = -1;
        this.originalSearchQuery = '';
        this.searchTimeout = null;
        this.mobileSearchTimeout = null;

        // Strictly Educational Trending Topics
        this.trendingTopics = [
            'Python Programming',
            'Machine Learning Basics',
            'Data Structures & Algorithms',
            'Web Development (Full Stack)',
            'Database Systems & SQL',
            'Artificial Intelligence',
            'Linear Algebra & Calculus',
            'Cybersecurity Fundamentals'
        ];

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initDarkMode();
        this.loadNotifications();
        this.setupVoiceSearch();
        this.loadTrendingTopics();
        this.setupClickOutside();
        this.setupScrollEffects();
    }

    setupEventListeners() {
        // Search Input
        this.searchInput?.addEventListener('focus', () => this.showSearchSuggestions());
        this.searchInput?.addEventListener('input', (e) => this.handleSearchInput(e));
        this.searchInput?.addEventListener('keydown', (e) => this.handleSearchKeydown(e));

        // Mobile Search
        this.mobileSearchTriggerBtn?.addEventListener('click', () => this.handleMobileSearchOpen());
        this.mobileSearchInput?.addEventListener('input', (e) => this.handleMobileSearchInput(e));
        this.mobileSearchInput?.addEventListener('keydown', (e) => this.handleMobileSearchKeydown(e));

        // Voice Search
        this.voiceSearchBtn?.addEventListener('click', () => this.toggleVoiceSearch('desktop'));
        this.mobileVoiceBtn?.addEventListener('click', () => this.toggleVoiceSearch('mobile'));

        // Notification Button & Mark All Read
        this.notificationBtn?.addEventListener('click', (e) => this.togglePanel(e, this.notificationPanel));
        document.getElementById('markAllReadBtn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.markAllNotificationsRead();
        });

        // Clear Recent Searches
        document.getElementById('clearRecentSearchesBtn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.clearRecentSearches();
        });

        // Theme Toggle (if exists)
        this.themeToggleBtn?.addEventListener('click', () => this.toggleDarkMode());

        // Profile Button
        this.profileBtn?.addEventListener('click', (e) => this.togglePanel(e, this.profilePanel));

        // Hamburger Menu
        this.hamburgerBtn?.addEventListener('click', () => this.toggleMobileMenu());

        // Close Mobile Menu
        this.closeMenuBtn?.addEventListener('click', () => this.closeMobileMenu());
        this.mobileMenuOverlay?.addEventListener('click', () => this.closeMobileMenu());

        // Close Mobile Search
        this.closeSearchBtn?.addEventListener('click', () => this.closeMobileSearch());

        // AI Assistant
        this.aiAssistantBtn?.addEventListener('click', () => this.openAIAssistant());

        // Logout
        this.logoutBtn?.addEventListener('click', () => this.logout());

        // Mobile Menu Items
        document.querySelectorAll('.mobile-menu-item').forEach(item => {
            item.addEventListener('click', () => this.closeMobileMenu());
        });

        // Close Panels on Panel Button Click
        document.querySelectorAll('.close-panel-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.dropdown-panel')?.style.setProperty('display', 'none');
            });
        });

        // Notification Dismiss Buttons
        document.querySelectorAll('.dismiss-notification-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const item = btn.closest('.notification-item');
                if (item) {
                    item.style.opacity = '0';
                    item.style.transform = 'translateX(20px)';
                    item.style.transition = 'all 0.3s ease';
                    setTimeout(() => {
                        item.remove();
                        this.clearNotification();
                        const remaining = this.notificationPanel.querySelectorAll('.notification-item');
                        if (remaining.length === 0) {
                            const body = this.notificationPanel.querySelector('.panel-body');
                            if (body) {
                                body.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-light); font-size: 13px;">No new notifications</div>';
                            }
                        }
                    }, 300);
                }
            });
        });
    }

    // ===== SEARCH FUNCTIONALITY =====
    showSearchSuggestions() {
        this.searchSuggestions.style.display = 'block';
        this.populateSuggestions();
    }

    hideSearchSuggestions() {
        this.searchSuggestions.style.display = 'none';
    }

    populateSuggestions() {
        // Recent Searches
        this.suggestionsList.innerHTML = '';
        if (this.recentSearches.length > 0) {
            this.recentSearches.slice(0, 5).forEach(search => {
                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.innerHTML = `<i class="fas fa-history"></i><span>${this.escapeHtml(search)}</span>`;
                item.addEventListener('click', () => this.selectSuggestion(search));
                this.suggestionsList.appendChild(item);
            });
        } else {
            const item = document.createElement('div');
            item.className = 'suggestion-item disabled';
            item.style.cursor = 'default';
            item.style.fontSize = '0.76rem';
            item.style.color = '#94a3b8';
            item.innerHTML = `<i class="fas fa-graduation-cap text-primary"></i><span>Search educational topics & courses</span>`;
            this.suggestionsList.appendChild(item);
        }

        // Trending Topics
        this.trendingList.innerHTML = '';
        this.trendingTopics.forEach(topic => {
            const item = document.createElement('div');
            item.className = 'trending-item';
            item.innerHTML = `<i class="fas fa-book-reader text-primary"></i><span>${this.escapeHtml(topic)}</span>`;
            item.addEventListener('click', () => this.selectSuggestion(topic));
            this.trendingList.appendChild(item);
        });
    }

    loadTrendingTopics() {
        // Already defined in constructor
    }

    handleSearchInput(e) {
        const query = e.target.value.trim();
        clearTimeout(this.searchTimeout);
        if (query.length > 0) {
            this.searchTimeout = setTimeout(() => {
                this.filterSuggestions(query);
            }, 150);
        } else {
            this.populateSuggestions();
        }
    }

    async filterSuggestions(query) {
        try {
            const response = await fetch(`/api/search-suggestions?q=${encodeURIComponent(query)}`);
            const suggestions = await response.json();

            // Hide headers & divider in suggestions dropdown
            const headers = this.searchSuggestions.querySelectorAll('.suggestions-header, .suggestions-divider');
            headers.forEach(h => h.style.display = 'none');

            this.trendingList.innerHTML = '';
            this.suggestionsList.innerHTML = '';
            this.activeSuggestionIndex = -1;

            if (suggestions.length === 0) {
                const item = document.createElement('div');
                item.className = 'suggestion-item disabled';
                item.style.cursor = 'default';
                item.style.justifyContent = 'center';
                item.style.color = 'var(--text-light)';
                item.innerHTML = '<span>No matching suggestions</span>';
                this.suggestionsList.appendChild(item);
                return;
            }

            suggestions.forEach(suggestion => {
                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.innerHTML = `
                    <i class="${suggestion.icon}"></i>
                    <span>${this.highlightMatch(suggestion.text, query)}</span>
                    <span class="suggestion-tag-badge">${suggestion.type}</span>
                `;
                item.addEventListener('click', () => this.selectSuggestion(suggestion.text));
                this.suggestionsList.appendChild(item);
            });
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    }

    highlightMatch(text, query) {
        // Suggestions include other students' video titles: escape them, and escape
        // the query for the regex (searches like "c++" used to throw an error)
        const safe = this.escapeHtml(text);
        const q = this.escapeHtml(query || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        if (!q) return safe;
        return safe.replace(new RegExp(`(${q})`, 'gi'), '<strong>$1</strong>');
    }

    selectSuggestion(suggestion) {
        this.searchInput.value = suggestion;
        this.hideSearchSuggestions();
        this.performSearch(suggestion);
    }

    isEducationalQuery(query) {
        if (!query || !query.trim()) return false;
        const q = query.trim().toLowerCase();
        
        // Entertainment / movie / song / gaming blacklists
        const nonEduKeywords = [
            'movie', 'movies', 'film', 'films', 'cinema', 'trailer', 'teaser',
            'song', 'songs', 'music video', 'mp3', 'remix', 'drama', 'dramas',
            'serial', 'serials', 'bollywood', 'hollywood', 'lollywood', 'tollywood',
            'kdrama', 'k-drama', 'bhojpuri', 'dubbed', 'bajrangi', 'bhaijaan',
            'airlift', 'dangal', 'pathaan', 'jawan', 'kgf', 'pushpa', 'bahubali',
            'prank', 'pranks', 'vlog', 'vlogs', 'comedy show', 'standup', 'roast',
            'reaction', 'tiktok', 'reels', 'shorts', 'pubg', 'free fire', 'fortnite',
            'gta', 'roblox', 'minecraft gaming'
        ];
        
        for (const kw of nonEduKeywords) {
            if (q.includes(kw)) {
                // If it has educational context like "film editing tutorial", permit it
                const eduExceptions = ['tutorial', 'course', 'lecture', 'lesson', 'education', 'analysis', 'programming', 'study', 'how to', 'science', 'math'];
                const hasException = eduExceptions.some(ex => q.includes(ex));
                if (!hasException) return false;
            }
        }
        
        // Exact checks for single-word non-educational queries like "baby"
        if (/^(\d+\.\s*)?baby$/i.test(q)) return false;

        return true;
    }

    sanitizeRecentSearches(list) {
        if (!Array.isArray(list)) return [];
        return list.filter(item => typeof item === 'string' && this.isEducationalQuery(item));
    }

    clearRecentSearches() {
        this.recentSearches = [];
        localStorage.removeItem('recentSearches');
        this.populateSuggestions();
    }

    addToRecentSearches(search) {
        if (!this.isEducationalQuery(search)) return;
        this.recentSearches = [search, ...this.recentSearches.filter(s => s !== search)].slice(0, 10);
        localStorage.setItem('recentSearches', JSON.stringify(this.recentSearches));
    }

    handleSearchKeydown(e) {
        const items = this.searchSuggestions.querySelectorAll('.suggestion-item, .trending-item');
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (this.searchSuggestions.style.display === 'none') {
                this.showSearchSuggestions();
                return;
            }
            if (items.length === 0) return;
            
            if (this.activeSuggestionIndex === -1) {
                this.originalSearchQuery = this.searchInput.value;
            }
            
            this.activeSuggestionIndex = (this.activeSuggestionIndex + 1) % items.length;
            this.highlightSuggestionItem(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (items.length === 0) return;
            
            if (this.activeSuggestionIndex > 0) {
                this.activeSuggestionIndex--;
                this.highlightSuggestionItem(items);
            } else if (this.activeSuggestionIndex === 0) {
                this.activeSuggestionIndex = -1;
                this.highlightSuggestionItem(items);
            } else {
                this.activeSuggestionIndex = items.length - 1;
                this.highlightSuggestionItem(items);
            }
        } else if (e.key === 'Enter') {
            if (this.activeSuggestionIndex > -1 && items[this.activeSuggestionIndex]) {
                e.preventDefault();
                const selectedText = items[this.activeSuggestionIndex].querySelector('span').textContent;
                this.selectSuggestion(selectedText);
            } else {
                const query = this.searchInput.value.trim();
                if (query) {
                    this.addToRecentSearches(query);
                    this.performSearch(query);
                    this.hideSearchSuggestions();
                }
            }
        } else if (e.key === 'Escape') {
            this.hideSearchSuggestions();
        }
    }

    highlightSuggestionItem(items) {
        items.forEach((item, index) => {
            if (index === this.activeSuggestionIndex) {
                item.classList.add('keyboard-active');
                item.style.backgroundColor = 'rgba(37, 99, 235, 0.1)';
                const text = item.querySelector('span').textContent;
                this.searchInput.value = text;
            } else {
                item.classList.remove('keyboard-active');
                item.style.backgroundColor = '';
            }
        });
        
        if (this.activeSuggestionIndex === -1 && this.originalSearchQuery !== undefined) {
            this.searchInput.value = this.originalSearchQuery;
        }
    }

    performSearch(query) {
        if (!this.isEducationalQuery(query)) {
            alert('🎓 LearnAI Platform Notice:\n\nThis platform is strictly dedicated to educational & academic content.\nSearching for movies, songs, dramas, or non-educational entertainment is not permitted.\n\nPlease search for learning subjects, tutorials, or courses (e.g. Python, Machine Learning, Data Science, Math).');
            return;
        }
        this.addToRecentSearches(query);
        console.log('Searching for:', query);
        window.location.href = `/dashboard?search=${encodeURIComponent(query)}`;
    }

    handleMobileSearchInput(e) {
        const query = e.target.value.trim();
        clearTimeout(this.mobileSearchTimeout);
        if (query.length > 0) {
            this.mobileSearchTimeout = setTimeout(() => {
                this.filterMobileSuggestions(query);
            }, 150);
        } else {
            this.mobileSuggestions.innerHTML = '';
        }
    }

    handleMobileSearchKeydown(e) {
        if (e.key === 'Enter') {
            const query = this.mobileSearchInput.value.trim();
            if (query) {
                this.addToRecentSearches(query);
                this.performSearch(query);
                this.closeMobileSearch();
            }
        } else if (e.key === 'Escape') {
            this.closeMobileSearch();
        }
    }

    async filterMobileSuggestions(query) {
        try {
            const response = await fetch(`/api/search-suggestions?q=${encodeURIComponent(query)}`);
            const suggestions = await response.json();

            this.mobileSuggestions.innerHTML = '';

            if (suggestions.length === 0) {
                const item = document.createElement('div');
                item.className = 'mobile-suggestion-item disabled';
                item.style.color = 'var(--text-light)';
                item.style.textAlign = 'center';
                item.style.padding = '12px 16px';
                item.textContent = 'No matching suggestions';
                this.mobileSuggestions.appendChild(item);
                return;
            }

            suggestions.forEach(suggestion => {
                const item = document.createElement('div');
                item.className = 'mobile-suggestion-item';
                item.style.display = 'flex';
                item.style.alignItems = 'center';
                item.style.justifyContent = 'space-between';
                item.style.padding = '12px 16px';
                item.style.borderBottom = '1px solid var(--border-light)';
                item.style.cursor = 'pointer';

                item.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <i class="${suggestion.icon}" style="font-size: 14px; opacity: 0.6;"></i>
                        <span>${this.escapeHtml(suggestion.text)}</span>
                    </div>
                    <span style="font-size: 10px; background: rgba(37,99,235,0.06); color: var(--primary-blue); padding: 2px 6px; border-radius: 10px; font-weight: 600; text-transform: uppercase;">${suggestion.type}</span>
                `;
                item.addEventListener('click', () => {
                    this.mobileSearchInput.value = suggestion.text;
                    this.addToRecentSearches(suggestion.text);
                    this.performSearch(suggestion.text);
                    this.closeMobileSearch();
                });
                this.mobileSuggestions.appendChild(item);
            });
        } catch (error) {
            console.error('Error fetching mobile suggestions:', error);
        }
    }

    // ===== VOICE SEARCH =====
    setupVoiceSearch() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';

            this.recognition.onstart = () => {
                this.isVoiceSearching = true;
                this.updateVoiceSearchUI();
            };

            this.recognition.onresult = (event) => {
                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }

                if (event.isFinal) {
                    this.searchInput.value = transcript;
                    this.mobileSearchInput.value = transcript;
                    this.performSearch(transcript);
                    this.isVoiceSearching = false;
                    this.updateVoiceSearchUI();
                }
            };

            this.recognition.onerror = (event) => {
                console.error('Voice search error:', event.error);
                this.isVoiceSearching = false;
                this.updateVoiceSearchUI();
                this.showNotification('Voice search failed. Please try again.', 'error');
            };

            this.recognition.onend = () => {
                this.isVoiceSearching = false;
                this.updateVoiceSearchUI();
            };
        }
    }

    toggleVoiceSearch(source) {
        if (!this.recognition) {
            this.showNotification('Voice search is not supported in your browser.', 'error');
            return;
        }

        if (this.isVoiceSearching) {
            this.recognition.abort();
        } else {
            this.recognition.start();
        }
    }

    updateVoiceSearchUI() {
        if (this.isVoiceSearching) {
            this.voiceSearchBtn?.classList.add('active');
            this.mobileVoiceBtn?.classList.add('active');
        } else {
            this.voiceSearchBtn?.classList.remove('active');
            this.mobileVoiceBtn?.classList.remove('active');
        }
    }

    // ===== DROPDOWN PANELS =====
    togglePanel(e, panel) {
        e.stopPropagation();
        
        // Close other panels
        document.querySelectorAll('.dropdown-panel').forEach(p => {
            if (p !== panel) p.style.display = 'none';
        });

        // Toggle current panel
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }

    // ===== DARK MODE =====
    initDarkMode() {
        // Reset dark mode to keep bright mode consistent and clear contrast bugs
        localStorage.removeItem('darkMode');
        document.body.classList.remove('dark-mode');
        this.isDarkMode = false;
    }

    toggleDarkMode() {
        this.isDarkMode = false;
        document.body.classList.remove('dark-mode');
        localStorage.removeItem('darkMode');
    }

    // ===== MOBILE MENU =====
    toggleMobileMenu() {
        if (typeof toggleSidebar === 'function') {
            toggleSidebar();
        } else {
            this.mobileMenuOverlay.style.display = 
                this.mobileMenuOverlay.style.display === 'none' ? 'flex' : 'none';
            this.hamburgerBtn.classList.toggle('active');
            document.body.classList.toggle('no-scroll');
        }
    }

    closeMobileMenu() {
        if (typeof closeSidebar === 'function') {
            closeSidebar();
        } else {
            this.mobileMenuOverlay.style.display = 'none';
            this.hamburgerBtn.classList.remove('active');
            document.body.classList.remove('no-scroll');
        }
    }

    openMobileSearch() {
        this.mobileSearchPanel.style.display = 'block';
        setTimeout(() => this.mobileSearchInput?.focus(), 100);
    }

    closeMobileSearch() {
        this.mobileSearchPanel.style.display = 'none';
        this.mobileSearchInput.value = '';
        this.mobileSuggestions.innerHTML = '';
    }

    handleMobileSearchOpen() {
        this.closeMobileMenu();
        this.openMobileSearch();
    }

    // ===== SCROLL EFFECTS =====
    setupScrollEffects() {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 0) {
                this.navbar.classList.add('scrolled');
            } else {
                this.navbar.classList.remove('scrolled');
            }
        });
    }

    // ===== CLICK OUTSIDE =====
    setupClickOutside() {
        document.addEventListener('click', (e) => {
            // Close search suggestions
            if (!e.target.closest('.search-wrapper')) {
                this.hideSearchSuggestions();
            }

            // Close dropdown panels
            if (!e.target.closest('.nav-action-item') && !e.target.closest('.dropdown-panel')) {
                document.querySelectorAll('.dropdown-panel').forEach(panel => {
                    panel.style.display = 'none';
                });
            }
        });
    }

    // ===== REAL STUDENT NOTIFICATIONS =====
    async loadNotifications() {
        const body = document.getElementById('notificationPanelBody');
        const badge = this.notificationBadge;
        try {
            const res = await fetch('/api/notifications');
            const data = await res.json();
            if (!data.success) return;

            const notifs = data.notifications || [];
            const unread = data.unread_count || 0;

            if (badge) {
                badge.textContent = unread;
                badge.style.display = unread > 0 ? 'flex' : 'none';
            }

            if (!body) return;

            if (notifs.length === 0) {
                body.innerHTML = '<div style="padding: 24px; text-align: center; color: #94a3b8; font-size: 0.8rem;">No notifications yet</div>';
                return;
            }

            const iconMap = {
                'quiz': 'fas fa-check-circle text-success',
                'weak_topic': 'fas fa-exclamation-triangle text-warning',
                'streak': 'fas fa-fire text-danger',
                'plan': 'fas fa-calendar-check text-primary',
                'welcome': 'fas fa-graduation-cap text-info',
                'info': 'fas fa-bell text-primary'
            };

            body.innerHTML = notifs.map(n => {
                const iconClass = iconMap[n.type] || ('fas ' + n.icon);
                const unreadClass = n.is_read ? '' : 'unread';
                return `
                    <div class="notification-item ${unreadClass}" data-id="${n.id}">
                        <div class="notification-icon">
                            <i class="${iconClass}"></i>
                        </div>
                        <div class="notification-content" style="flex: 1; min-width: 0;">
                            <p class="notification-title" style="margin: 0 0 2px; font-weight: 700; font-size: 0.82rem; color: #0f172a;">${this.escapeHtml(n.title)}</p>
                            <p class="notification-message" style="margin: 0 0 4px; font-size: 0.75rem; color: #64748b; line-height: 1.35;">${this.escapeHtml(n.message)}</p>
                            <span class="notification-time" style="font-size: 0.65rem; color: #94a3b8;">${n.time_ago}</span>
                        </div>
                        <button class="dismiss-notification-btn" title="Dismiss" onclick="window.navbarManager?.dismissNotificationItem(${n.id}, this)">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
            }).join('');

        } catch (e) {
            console.warn('Could not load notifications:', e);
            if (body) {
                body.innerHTML = '<div style="padding: 24px; text-align: center; color: #94a3b8; font-size: 0.8rem;">No notifications at this time</div>';
            }
        }
    }

    async markAllNotificationsRead() {
        try {
            await fetch('/api/notifications/mark-read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            if (this.notificationBadge) {
                this.notificationBadge.style.display = 'none';
                this.notificationBadge.textContent = '0';
            }
            document.querySelectorAll('#notificationPanelBody .notification-item').forEach(el => {
                el.classList.remove('unread');
            });
        } catch (e) {}
    }

    async dismissNotificationItem(id, btnEl) {
        try {
            const item = btnEl.closest('.notification-item');
            if (item) {
                item.style.opacity = '0';
                setTimeout(() => item.remove(), 200);
            }
            await fetch('/api/notifications/' + id + '/dismiss', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            this.clearNotification();
        } catch (e) {}
    }

    clearNotification() {
        const newCount = Math.max(0, parseInt(this.notificationBadge.textContent || 0) - 1);
        this.notificationBadge.textContent = newCount;
        
        if (newCount === 0) {
            this.notificationBadge.style.display = 'none';
        }
    }

    addNotification(title, message, type = 'info') {
        const count = parseInt(this.notificationBadge.textContent || 0) + 1;
        this.notificationBadge.textContent = count;
        this.notificationBadge.style.display = 'flex';
        this.loadNotifications();
    }

    // ===== UTILITIES =====
    showNotification(message, type = 'info') {
        console.log(`[${type.toUpperCase()}]`, message);
        // You can integrate with a toast notification library here
        // Example: using a custom toast system
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ===== USER ACTIONS =====
    openAIAssistant() {
        console.log('Opening AI Assistant...');
        // Navigate to chatbot or open modal
        window.location.href = '/chatbot' || new Event('openAIAssistant');
    }

    logout() {
        if (confirm('Are you sure you want to logout?')) {
            window.location.href = '/logout';
        }
    }
}

// ===== Initialize on DOM Ready =====
document.addEventListener('DOMContentLoaded', () => {
    const navbar = new NavbarManager();

    // Expose globally for external access
    window.navbarManager = navbar;

    // Handle responsive behavior
    const handleResize = () => {
        if (window.innerWidth > 768) {
            document.querySelector('.navbar-modern').style.display = 'flex';
            navbar.closeMobileMenu();
            navbar.closeMobileSearch();
        }
    };

    window.addEventListener('resize', handleResize);

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl+K or Cmd+K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            navbar.searchInput?.focus();
            navbar.showSearchSuggestions();
        }

        // Escape to close panels
        if (e.key === 'Escape') {
            navbar.hideSearchSuggestions();
            navbar.closeMobileMenu();
            navbar.closeMobileSearch();
            document.querySelectorAll('.dropdown-panel').forEach(panel => {
                panel.style.display = 'none';
            });
        }
    });

    // Mobile search trigger on mobile screens
    if (window.innerWidth <= 768) {
        const searchArea = document.querySelector('.navbar-center');
        if (searchArea) {
            searchArea.addEventListener('click', () => navbar.handleMobileSearchOpen());
        }
    }
});

// ===== API Integration Helpers =====
const NavbarAPI = {
    fetchNotifications: async () => {
        try {
            const response = await fetch('/api/notifications');
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
            return [];
        }
    },

    searchContent: async (query) => {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            return await response.json();
        } catch (error) {
            console.error('Failed to search:', error);
            return [];
        }
    },

    getUserProfile: async () => {
        try {
            const response = await fetch('/api/profile');
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch profile:', error);
            return null;
        }
    }
};

// Expose API globally
window.NavbarAPI = NavbarAPI;

// ===== Real-time Notification Updates (WebSocket) =====
class NotificationWebSocket {
    constructor() {
        this.ws = null;
        this.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/notifications`);

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (window.navbarManager) {
                window.navbarManager.addNotification(data.title, data.message, data.type);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connect(), 3000);
        };
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Initialize WebSocket only if needed
// const notificationWS = new NotificationWebSocket();

// ===== Export for Module Systems =====
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { NavbarManager, NavbarAPI };
}
