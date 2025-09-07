/**
 * Zavion - Frontend Application
 * Modern JavaScript application for video analysis and user behavior insights
 */

class ZavionApp {
    constructor() {
        // Use configuration from injected global variable or fallback to default
        this.apiBaseUrl = window.ZAVION_CONFIG?.apiBaseUrl || 'http://localhost:8000';
        console.log('Zavion Frontend initialized with API base URL:', this.apiBaseUrl);
        
        this.connectionStatus = 'connecting';
        this.uploadProgress = 0;
        this.currentStep = 1;
        this.selectedFile = null;
        this.toastTimeout = null;
        this.rateLimitInfo = {}; // Add rate limit tracking
        this.rateLimitTimers = {}; // Track countdown timers
        
        // Propositions pagination
        this.currentPropositionsPage = 1;
        this.currentMemoryPage = 1;
        
        // Tab management
        this.activeTab = 'home';
        // Theme management - handle migration from old theme key
        let theme = localStorage.getItem('gum-theme');
        if (!theme) {
            // Default to light theme
            theme = 'light';
            localStorage.setItem('gum-theme', theme);
        }
        this.theme = theme;
        
        // Text shimmer management
        this.textShimmerInstances = new Map();
        
        this.init();
    }

    async apiCall(url, options = {}) {
        try {
            const response = await fetch(url, options);
            
            if (response.status === 429) {
                const retryAfter = response.headers.get('Retry-After');
                const rateLimitLimit = response.headers.get('X-RateLimit-Limit');
                const rateLimitRemaining = response.headers.get('X-RateLimit-Remaining');
                const rateLimitReset = response.headers.get('X-RateLimit-Reset');
                
                const errorData = await response.json();
                
                this.handleRateLimit(url, retryAfter, errorData.detail, {
                    limit: rateLimitLimit,
                    remaining: rateLimitRemaining,
                    reset: rateLimitReset
                });
                throw new Error('Rate limited');
            }
            
            // Clear any rate limit info on success
            delete this.rateLimitInfo[url];
            this.updateRateLimitUI();
            
            return response;
        } catch (error) {
            if (error.message !== 'Rate limited') {
                this.showToast('❌ Connection error. Make sure Zavion is running.', 'error');
            }
            throw error;
        }
    }

    handleRateLimit(endpoint, retryAfter, message, headers = {}) {
        const waitTime = parseInt(retryAfter) || 60;
        const resetTime = Date.now() + (waitTime * 1000);
        
        this.rateLimitInfo[endpoint] = {
            resetTime: resetTime,
            message: message,
            limit: headers.limit,
            remaining: headers.remaining,
            reset: headers.reset
        };
        
        this.showToast(`⏳ ${message}`, 'warning', waitTime * 1000);
        this.updateRateLimitUI();
        
        // Start countdown timer
        this.startRateLimitCountdown(endpoint, resetTime);
        
        // Auto-clear after wait time
        setTimeout(() => {
            delete this.rateLimitInfo[endpoint];
            this.updateRateLimitUI();
        }, waitTime * 1000);
    }

    startRateLimitCountdown(endpoint, resetTime) {
        // Clear existing timer for this endpoint
        if (this.rateLimitTimers[endpoint]) {
            clearInterval(this.rateLimitTimers[endpoint]);
        }
        
        // Start new countdown timer
        this.rateLimitTimers[endpoint] = setInterval(() => {
            const remainingTime = Math.ceil((resetTime - Date.now()) / 1000);
            
            if (remainingTime <= 0) {
                // Time's up, clear timer and re-enable
                clearInterval(this.rateLimitTimers[endpoint]);
                delete this.rateLimitTimers[endpoint];
                delete this.rateLimitInfo[endpoint];
                this.updateRateLimitUI();
                this.showToast('✅ Rate limit reset - you can try again!', 'success');
            } else {
                // Update UI with remaining time
                this.updateRateLimitUI();
            }
        }, 1000);
    }

    updateRateLimitUI() {
        // Update video upload button
        this.updateEndpointRateLimitUI('/observations/video', 'uploadBtn', 'Upload Video');
        
        // Update text submission button
        this.updateEndpointRateLimitUI('/observations/text', 'submitTextBtn', 'Submit Text');
        
        // Update query button
        this.updateEndpointRateLimitUI('/query', 'querySearchBtn', 'Search');
        
        // Update propositions load button
        this.updateEndpointRateLimitUI('/propositions', 'loadPropositions', 'Load Insights');
    }

    updateEndpointRateLimitUI(endpoint, buttonId, defaultText) {
        const fullEndpoint = `${this.apiBaseUrl}${endpoint}`;
        const rateLimitInfo = this.rateLimitInfo[fullEndpoint];
        const button = document.getElementById(buttonId);
        
        if (rateLimitInfo && button) {
            const remainingTime = Math.ceil((rateLimitInfo.resetTime - Date.now()) / 1000);
            
            if (remainingTime > 0) {
                button.disabled = true;
                button.textContent = `Wait ${remainingTime}s`;
                button.classList.add('rate-limited');
                
                // Add visual indicator
                this.addRateLimitIndicator(button, remainingTime, rateLimitInfo.limit, rateLimitInfo.remaining);
            } else {
                button.disabled = false;
                button.textContent = defaultText;
                button.classList.remove('rate-limited');
                this.removeRateLimitIndicator(button);
            }
        } else if (button) {
            button.disabled = false;
            button.textContent = defaultText;
            button.classList.remove('rate-limited');
            this.removeRateLimitIndicator(button);
        }
    }

    addRateLimitIndicator(button, remainingTime, limit, remaining) {
        // Remove existing indicator
        this.removeRateLimitIndicator(button);
        
        // Create indicator element
        const indicator = document.createElement('div');
        indicator.className = 'rate-limit-indicator';
        indicator.innerHTML = `
            <div class="rate-limit-progress">
                <div class="rate-limit-bar" style="width: ${((remaining || 0) / (limit || 1)) * 100}%"></div>
            </div>
            <div class="rate-limit-text">
                ${remaining || 0}/${limit || '∞'} remaining • ${remainingTime}s
            </div>
        `;
        
        // Insert after button
        button.parentNode.insertBefore(indicator, button.nextSibling);
    }

    removeRateLimitIndicator(button) {
        const indicator = button.parentNode.querySelector('.rate-limit-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    getRateLimitStatus(endpoint) {
        const fullEndpoint = `${this.apiBaseUrl}${endpoint}`;
        return this.rateLimitInfo[fullEndpoint] || null;
    }

    isRateLimited(endpoint) {
        const status = this.getRateLimitStatus(endpoint);
        return status && status.resetTime > Date.now();
    }

    /**
     * Initialize the application
     */
    async init() {
        this.applyTheme();
        this.setupEventListeners();
        this.setupTabNavigation();
        this.setupPropositionsListeners();
        this.setupMemoryListeners();
        this.setupTimelineListeners();
        this.setupNarrativeTimelineListeners();
        this.setupSuggestionsListeners();
        await this.checkConnection();
        this.updateConnectionStatus();
        
        // Initialize date inputs with today's date
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('timelineDate').value = today;
        document.getElementById('narrativeTimelineDate').value = today;
    }

    /**
     * Apply theme to the application
     */
    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.theme);
        const themeIcon = document.querySelector('#themeToggle i');
        if (themeIcon) {
            themeIcon.className = this.theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }

    /**
     * Toggle between light and dark themes
     */    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('gum-theme', this.theme);
        this.applyTheme();
        this.showToast(`Switched to ${this.theme} mode`, 'info');
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Theme toggle
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }



        // Action buttons
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportResults());
        }

        const newAnalysisBtn = document.getElementById('newAnalysisBtn');
        if (newAnalysisBtn) {
            newAnalysisBtn.addEventListener('click', () => this.startNewAnalysis());
        }





        // Database cleanup button
        const cleanupDatabase = document.getElementById('cleanupDatabase');
        if (cleanupDatabase) {
            cleanupDatabase.addEventListener('click', () => this.handleDatabaseCleanup());
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'n':
                        e.preventDefault();
                        this.startNewAnalysis();
                        break;
                }
            }
        });


    }

















    /**
     * Simulate processing progress for better UX
     */
    async simulateProcessingProgress() {
        // Step 2: Processing
        for (let i = 0; i <= 100; i += 10) {
            this.updateProgressStep(2, i);
            await this.delay(200);
        }

        // Step 3: Analyzing
        for (let i = 0; i <= 100; i += 5) {
            this.updateProgressStep(3, i);
            await this.delay(150);
        }
    }

    /**
     * Poll job status for video processing
     */
    async pollJobStatus(jobId) {
        // Removed timeout limit - will poll indefinitely until completion or genuine error
        while (true) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/observations/video/status/${jobId}`);
                
                if (response.ok) {
                    const status = await response.json();
                    
                    // Update progress based on status
                    if (status.status === 'processing' || status.status === 'processing_frames') {
                        this.updateProgressStep(2, status.progress || 0);
                    } else if (status.status === 'analyzing') {
                        this.updateProgressStep(3, status.progress || 0);
                    }
                      if (status.status === 'completed') {
                        // Processing complete - now fetch insights
                        this.updateProgressStep(3, 100);
                        try {
                            const insightsResponse = await fetch(`${this.apiBaseUrl}/observations/video/${jobId}/insights`);
                            let insights = [];
                            let patterns = [];
                            let summary = '';
                            
                            if (insightsResponse.ok) {
                                const insightsData = await insightsResponse.json();
                                insights = insightsData.key_insights || [];
                                patterns = insightsData.behavior_patterns || [];
                                summary = insightsData.summary || '';
                            }
                            
                            return {
                                success: true,
                                frames_analyzed: status.total_frames || 0,
                                processing_time_ms: status.processing_time_ms || 0,
                                insights: insights,
                                patterns: patterns,
                                summary: summary,
                                analyses: status.frame_analyses || []
                            };
                        } catch (insightsError) {
                            console.warn('Failed to fetch insights:', insightsError);
                            // Return basic results without insights
                            return {
                                success: true,
                                frames_analyzed: status.total_frames || 0,
                                processing_time_ms: status.processing_time_ms || 0,
                                insights: ['Analysis completed successfully'],
                                patterns: ['Basic processing pattern identified'],
                                summary: 'Video analysis completed',
                                analyses: status.frame_analyses || []
                            };
                        }
                    } else if (status.status === 'error') {
                        throw new Error(status.error || 'Processing failed');
                    }
                } else {
                    throw new Error(`Status check failed: ${response.status}`);
                }
                
                // Wait before next poll
                await this.delay(2000);
                
            } catch (error) {
                throw new Error(`Status polling failed: ${error.message}`);
            }
        }
    }

    /**
     * Display analysis results
     */
    displayResults(results) {
        const resultsSection = document.getElementById('resultsSection');
        const resultsContent = document.getElementById('resultsContent');
        
        if (!resultsSection || !resultsContent) return;

        // Show results section
        resultsSection.style.display = 'block';
        
        // Create results HTML
        const resultsHtml = this.generateResultsHTML(results);
        resultsContent.innerHTML = resultsHtml;
        
        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });
        
        // Store results for export
        this.currentResults = results;
    }

    /**
     * Generate results HTML
     */    generateResultsHTML(results) {
        return `
            <div class="results-grid">
                <div class="result-card">
                    <div class="result-header">
                        <h3><i class="fas fa-info-circle"></i> Analysis Summary</h3>
                    </div>
                    <div class="result-content">
                        <div class="summary-stats">
                            <div class="stat">
                                <span class="stat-label">Processing Time</span>
                                <span class="stat-value">${results.processing_time_ms?.toFixed(1) || 'N/A'}ms</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Frames Analyzed</span>
                                <span class="stat-value">${results.frames_analyzed || 'N/A'}</span>
                            </div>
                            <div class="stat">
                                <span class="stat-label">Status</span>
                                <span class="stat-value success">Completed</span>
                            </div>
                        </div>
                        ${results.summary ? `<div class="summary-text"><p>${results.summary}</p></div>` : ''}
                    </div>
                </div>
                
                <div class="result-card">
                    <div class="result-header">
                        <h3><i class="fas fa-eye"></i> Key Insights</h3>
                    </div>
                    <div class="result-content">
                        <div class="insights-list">
                            ${this.generateInsightsList(results.insights || [])}
                        </div>
                    </div>
                </div>
                
                <div class="result-card">
                    <div class="result-header">
                        <h3><i class="fas fa-chart-line"></i> Behavior Patterns</h3>
                    </div>
                    <div class="result-content">
                        <div class="patterns-list">
                            ${this.generatePatternsList(results.patterns || [])}
                        </div>
                    </div>
                </div>
                
                <div class="result-card full-width">
                    <div class="result-header">
                        <h3><i class="fas fa-list"></i> Detailed Analysis</h3>
                    </div>
                    <div class="result-content">
                        <pre class="analysis-details">${JSON.stringify(results, null, 2)}</pre>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Generate insights list HTML
     */
    generateInsightsList(insights) {
        if (!insights.length) {
            return '<p class="no-data">No insights available</p>';
        }
        
        return insights.map(insight => `
            <div class="insight-item">
                <div class="insight-icon">
                    <i class="fas fa-lightbulb"></i>
                </div>
                <div class="insight-text">${insight}</div>
            </div>
        `).join('');
    }    /**
     * Generate patterns list HTML
     */
    generatePatternsList(patterns) {
        if (!patterns.length) {
            return '<p class="no-data">No patterns identified</p>';
        }
        
        return patterns.map(pattern => {
            // Handle both string patterns and object patterns
            if (typeof pattern === 'string') {
                return `
                    <div class="pattern-item">
                        <div class="pattern-name">${pattern}</div>
                    </div>
                `;
            } else {
                return `
                    <div class="pattern-item">
                        <div class="pattern-name">${pattern.name || 'Unknown Pattern'}</div>
                        <div class="pattern-confidence">
                            Confidence: ${((pattern.confidence || 0) * 100).toFixed(1)}%
                        </div>
                    </div>
                `;
            }
        }).join('');
    }

    /**
     * Export results
     */
    exportResults() {
        this.showToast('Export functionality is not available without upload feature', 'warning');
    }

    /**
     * Start new analysis
     */
    startNewAnalysis() {
        this.showToast('Upload feature has been removed from this interface', 'info');
    }

    /**
     * Handle database cleanup with confirmation
     */
    async handleDatabaseCleanup() {
        // Show confirmation dialog
        const confirmed = confirm(
            'Are you sure you want to clean the entire database?\n\n' +
            'This will permanently delete:\n' +
            '• All observations\n' +
            '• All propositions\n' +
            '• All insights\n' +
            '• All analysis data\n\n' +
            'This action cannot be undone!'
        );

        if (!confirmed) {
            return;
        }

        // Find the cleanup button (could be in settings or memory tab)
        const cleanupBtn = document.getElementById('cleanupDatabase') || document.getElementById('cleanupMemoryDatabase');
        if (cleanupBtn) {
            cleanupBtn.disabled = true;
            cleanupBtn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Cleaning...';
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/database/cleanup`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to clean database');
            }

            const result = await response.json();
            
            // Show success message with deletion counts
            const message = `Database cleaned successfully!\n\n` +
                `Deleted:\n` +
                `• ${result.observations_deleted} observations\n` +
                `• ${result.propositions_deleted} propositions\n` +
                `• ${result.junction_records_deleted} junction records\n` +
                `• FTS indexes cleared`;

            this.showToast('Database cleaned successfully!', 'success');
            
            // Optional: Show detailed results in an alert
            alert(message);
            
            // Refresh any displayed data
            this.loadRecentHistory();
            
            // Reset any current results
            this.currentResults = null;
            const resultsSection = document.getElementById('resultsSection');
            if (resultsSection) {
                resultsSection.style.display = 'none';
            }
            
        } catch (error) {
            console.error('Database cleanup failed:', error);
            this.showToast(`Database cleanup failed: ${error.message}`, 'error');
        } finally {
            // Restore button state
            if (cleanupBtn) {
                cleanupBtn.disabled = false;
                cleanupBtn.innerHTML = '<i class="fas fa-trash" aria-hidden="true"></i> Clean Database';
            }
        }
    }

    /**
     * Hide progress section
     */
    hideProgressSection() {
        const progressSection = document.getElementById('progressSection');
        if (progressSection) {
            progressSection.style.display = 'none';
        }
    }

    /**
     * Disable form during upload
     */
    disableForm() {
        const form = document.getElementById('videoForm');
        if (form) {
            const inputs = form.querySelectorAll('input, button, select');
            inputs.forEach(input => input.disabled = true);
        }
    }

    /**
     * Enable form after upload
     */
    enableForm() {
        const form = document.getElementById('videoForm');
        if (form) {
            const inputs = form.querySelectorAll('input, button, select');
            inputs.forEach(input => input.disabled = false);
        }
        
        // Keep upload button disabled if no file selected
        if (!this.selectedFile) {
            this.disableUploadButton();
        }
    }



    /**
     * Check API connection
     */
    async checkConnection() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`, {
                timeout: 5000
            });
            
            if (response.ok) {
                const health = await response.json();
                this.connectionStatus = health.gum_connected ? 'connected' : 'disconnected';
            } else {
                this.connectionStatus = 'disconnected';
            }
        } catch (error) {
            this.connectionStatus = 'disconnected';
        }
    }

    /**
     * Update connection status display
     */
    updateConnectionStatus() {
        const statusElement = document.getElementById('connectionStatus');
        if (!statusElement) return;

        const statusText = {
            'connected': 'Connected',
            'disconnected': 'Disconnected', 
            'connecting': 'Connecting...'
        };

        // Hide the connection status when connected, only show when there are issues
        if (this.connectionStatus === 'connected') {
            statusElement.style.display = 'none';
        } else {
            statusElement.style.display = 'flex';
            statusElement.className = `connection-status ${this.connectionStatus}`;
            const span = statusElement.querySelector('span');
            if (span) {
                span.textContent = statusText[this.connectionStatus];
            }
        }

        // Show warning if disconnected
        if (this.connectionStatus === 'disconnected') {
            this.showToast('Cannot connect to analysis service. Please check if the controller is running.', 'error');
        }
    }

    /**
     * Update scroll progress
     */
    /**
     * Enhanced toast notification system with multiple toasts support
     */
    showToast(message, type = 'info', position = 'top-right', duration = 5000) {
        // Create toast container if it doesn't exist
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        // Create individual toast element
        const toast = document.createElement('div');
        const toastId = Date.now() + Math.random();
        toast.id = `toast-${toastId}`;
        toast.className = `toast ${type}`;

        // Get icon for toast type
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        // Set toast content with icon
        toast.innerHTML = `
            <i class="${icons[type] || icons.info}" aria-hidden="true"></i>
            <span>${message}</span>
            <button class="toast-close" onclick="window.zavionApp.closeToast('${toastId}')">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Add to container
        container.appendChild(toast);

        // Trigger animation
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        // Auto hide after specified duration
        const timeout = setTimeout(() => {
            this.closeToast(toastId);
        }, duration);

        // Store timeout reference for manual cleanup
        toast.dataset.timeout = timeout;
    }

    /**
     * Close specific toast
     */
    closeToast(toastId) {
        const toast = document.getElementById(`toast-${toastId}`);
        if (!toast) return;

        // Clear timeout if exists
        if (toast.dataset.timeout) {
            clearTimeout(toast.dataset.timeout);
        }

        // Animate out and remove
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    /**
     * Utility: Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Utility: Format duration
     */
    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }

    /**
     * Utility: Delay function
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ========================================
    // TEXT SHIMMER LOADING ANIMATION
    // ========================================

    /**
     * Create a text shimmer element
     * @param {string} text - The text to display
     * @param {Object} options - Configuration options
     * @param {string} options.element - HTML element type (default: 'span')
     * @param {string} options.className - Additional CSS classes
     * @param {number} options.duration - Animation duration in seconds (default: 2)
     * @param {number} options.spread - Spread of the shimmer effect (default: 2)
     * @param {string} options.color - Color variant ('blue', 'cyan', or default)
     * @param {string} options.size - Size variant ('sm', 'lg', 'xl', or default)
     * @param {boolean} options.mono - Use monospace font
     * @param {boolean} options.fast - Use fast animation
     * @param {boolean} options.slow - Use slow animation
     * @returns {HTMLElement} The shimmer element
     */
    createTextShimmer(text, options = {}) {
        const {
            element = 'span',
            className = '',
            duration = 2,
            spread = 2,
            color = '',
            size = '',
            mono = false,
            fast = false,
            slow = false
        } = options;

        // Create the element
        const shimmerElement = document.createElement(element);
        shimmerElement.textContent = text;
        shimmerElement.className = 'text-shimmer';

        // Add color variant
        if (color === 'blue') {
            shimmerElement.classList.add('text-shimmer-blue');
        } else if (color === 'cyan') {
            shimmerElement.classList.add('text-shimmer-cyan');
        }

        // Add size variant
        if (size === 'sm') {
            shimmerElement.classList.add('text-shimmer-sm');
        } else if (size === 'lg') {
            shimmerElement.classList.add('text-shimmer-lg');
        } else if (size === 'xl') {
            shimmerElement.classList.add('text-shimmer-xl');
        }

        // Add font variant
        if (mono) {
            shimmerElement.classList.add('text-shimmer-mono');
        }

        // Add duration variant
        if (fast) {
            shimmerElement.classList.add('text-shimmer-fast');
        } else if (slow) {
            shimmerElement.classList.add('text-shimmer-slow');
        }

        // Add custom classes
        if (className) {
            shimmerElement.classList.add(...className.split(' '));
        }

        // Set custom duration if provided
        if (duration !== 2) {
            shimmerElement.style.animationDuration = `${duration}s`;
        }

        // Set custom spread if provided
        if (spread !== 2) {
            const dynamicSpread = text.length * spread;
            shimmerElement.style.setProperty('--spread', `${dynamicSpread}px`);
        }

        return shimmerElement;
    }

    /**
     * Show loading state with text shimmer
     * @param {string|HTMLElement} target - Target element or selector
     * @param {string} loadingText - Text to show while loading
     * @param {Object} options - Shimmer options
     * @returns {string} Original content for restoration
     */
    showLoadingShimmer(target, loadingText = 'Loading...', options = {}) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return null;

        // Store original content
        const originalContent = element.innerHTML;
        const originalText = element.textContent;

        // Create shimmer element
        const shimmerElement = this.createTextShimmer(loadingText, options);
        
        // Clear and add shimmer
        element.innerHTML = '';
        element.appendChild(shimmerElement);

        // Store for restoration
        const instanceId = `shimmer_${Date.now()}_${Math.random()}`;
        this.textShimmerInstances.set(instanceId, {
            element: element,
            originalContent: originalContent,
            originalText: originalText,
            shimmerElement: shimmerElement
        });

        return instanceId;
    }

    /**
     * Hide loading shimmer and restore original content
     * @param {string} instanceId - Instance ID returned from showLoadingShimmer
     */
    hideLoadingShimmer(instanceId) {
        const instance = this.textShimmerInstances.get(instanceId);
        if (!instance) return;

        const { element, originalContent } = instance;
        
        // Restore original content
        element.innerHTML = originalContent;
        
        // Clean up
        this.textShimmerInstances.delete(instanceId);
    }

    /**
     * Show loading state for a button
     * @param {string|HTMLElement} button - Button element or selector
     * @param {string} loadingText - Text to show while loading
     * @param {Object} options - Shimmer options
     * @returns {string} Instance ID for restoration
     */
    showButtonLoading(button, loadingText = 'Loading...', options = {}) {
        const buttonElement = typeof button === 'string' ? document.querySelector(button) : button;
        if (!buttonElement) return null;

        // Store original state
        const originalText = buttonElement.textContent;
        const originalDisabled = buttonElement.disabled;

        // Disable button
        buttonElement.disabled = true;
        buttonElement.classList.add('loading');

        // Create shimmer with button-specific options
        const shimmerOptions = {
            ...options,
            className: 'btn-shimmer'
        };
        
        const shimmerElement = this.createTextShimmer(loadingText, shimmerOptions);
        
        // Clear and add shimmer
        buttonElement.innerHTML = '';
        buttonElement.appendChild(shimmerElement);

        // Store for restoration
        const instanceId = `button_shimmer_${Date.now()}_${Math.random()}`;
        this.textShimmerInstances.set(instanceId, {
            element: buttonElement,
            originalText: originalText,
            originalDisabled: originalDisabled,
            shimmerElement: shimmerElement,
            type: 'button'
        });

        return instanceId;
    }

    /**
     * Hide button loading state
     * @param {string} instanceId - Instance ID returned from showButtonLoading
     */
    hideButtonLoading(instanceId) {
        const instance = this.textShimmerInstances.get(instanceId);
        if (!instance || instance.type !== 'button') return;

        const { element, originalText, originalDisabled } = instance;
        
        // Restore original state
        element.textContent = originalText;
        element.disabled = originalDisabled;
        element.classList.remove('loading');
        
        // Clean up
        this.textShimmerInstances.delete(instanceId);
    }

    /**
     * Show loading state for a card or container
     * @param {string|HTMLElement} target - Target element or selector
     * @param {string} loadingText - Text to show while loading
     * @param {Object} options - Shimmer options
     * @returns {string} Instance ID for restoration
     */
    showCardLoading(target, loadingText = 'Loading data...', options = {}) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return null;

        // Store original content
        const originalContent = element.innerHTML;
        
        // Add loading class
        element.classList.add('card-loading');

        // Create loading container
        const loadingContainer = document.createElement('div');
        loadingContainer.className = 'loading-container';
        loadingContainer.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: var(--spacing-xxl);
            text-align: center;
        `;

        // Add spinner
        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        loadingContainer.appendChild(spinner);

        // Add shimmer text
        const shimmerElement = this.createTextShimmer(loadingText, {
            ...options,
            className: 'mt-3'
        });
        loadingContainer.appendChild(shimmerElement);

        // Replace content
        element.innerHTML = '';
        element.appendChild(loadingContainer);

        // Store for restoration
        const instanceId = `card_shimmer_${Date.now()}_${Math.random()}`;
        this.textShimmerInstances.set(instanceId, {
            element: element,
            originalContent: originalContent,
            shimmerElement: shimmerElement,
            type: 'card'
        });

        return instanceId;
    }

    /**
     * Hide card loading state
     * @param {string} instanceId - Instance ID returned from showCardLoading
     */
    hideCardLoading(instanceId) {
        const instance = this.textShimmerInstances.get(instanceId);
        if (!instance || instance.type !== 'card') return;

        const { element, originalContent } = instance;
        
        // Restore original content
        element.innerHTML = originalContent;
        element.classList.remove('card-loading');
        
        // Clean up
        this.textShimmerInstances.delete(instanceId);
    }

    // ===== PROPOSITIONS FUNCTIONALITY =====

    /**
     * Setup propositions event listeners
     */
    setupPropositionsListeners() {
        const loadPropositionsBtn = document.getElementById('loadPropositions');
        const confidenceFilter = document.getElementById('confidenceFilter');
        const sortBySelect = document.getElementById('sortBy');
        const prevBtn = document.getElementById('prevPropositions');
        const nextBtn = document.getElementById('nextPropositions');

        if (loadPropositionsBtn) {
            loadPropositionsBtn.addEventListener('click', () => {
                this.currentPropositionsPage = 1;
                this.loadPropositions();
            });
        }

        if (confidenceFilter) {
            confidenceFilter.addEventListener('change', () => {
                this.currentPropositionsPage = 1;
                this.loadPropositions();
            });
        }

        if (sortBySelect) {
            sortBySelect.addEventListener('change', () => {
                this.currentPropositionsPage = 1;
                this.loadPropositions();
            });
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.currentPropositionsPage > 1) {
                    this.currentPropositionsPage--;
                    this.loadPropositions();
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                this.currentPropositionsPage++;
                this.loadPropositions();
            });
        }
    }

    /**
     * Setup event listeners for memory tab
     */
    setupMemoryListeners() {
        const loadMemoryPropositionsBtn = document.getElementById('loadMemoryPropositions');
        const memoryConfidenceFilter = document.getElementById('memoryConfidenceFilter');
        const memorySortBySelect = document.getElementById('memorySortBy');
        const prevMemoryBtn = document.getElementById('prevMemoryPropositions');
        const nextMemoryBtn = document.getElementById('nextMemoryPropositions');

        if (loadMemoryPropositionsBtn) {
            loadMemoryPropositionsBtn.addEventListener('click', () => {
                this.currentMemoryPage = 1;
                this.loadMemoryPropositions();
            });
        }

        if (memoryConfidenceFilter) {
            memoryConfidenceFilter.addEventListener('change', () => {
                this.currentMemoryPage = 1;
                this.loadMemoryPropositions();
            });
        }

        if (memorySortBySelect) {
            memorySortBySelect.addEventListener('change', () => {
                this.currentMemoryPage = 1;
                this.loadMemoryPropositions();
            });
        }

        if (prevMemoryBtn) {
            prevMemoryBtn.addEventListener('click', () => {
                if (this.currentMemoryPage > 1) {
                    this.currentMemoryPage--;
                    this.loadMemoryPropositions();
                }
            });
        }

        if (nextMemoryBtn) {
            nextMemoryBtn.addEventListener('click', () => {
                this.currentMemoryPage++;
                this.loadMemoryPropositions();
            });
        }

        // Memory tab database cleanup button
        const cleanupMemoryDatabase = document.getElementById('cleanupMemoryDatabase');
        if (cleanupMemoryDatabase) {
            cleanupMemoryDatabase.addEventListener('click', () => this.handleDatabaseCleanup());
        }
    }

    /**
     * Load propositions from the API
     */
    async loadPropositions() {
        const loadBtn = document.getElementById('loadPropositions');
        const contentContainer = document.getElementById('propositionsContent');
        const statsContainer = document.getElementById('propositionsStats');
        const paginationContainer = document.getElementById('propositionsPagination');

        if (!contentContainer) return;

        try {
            // Show loading state with text shimmer
            let buttonLoadingInstanceId = null;
            if (loadBtn) {
                buttonLoadingInstanceId = this.showButtonLoading(loadBtn, 'Loading insights...', {
                    color: 'cyan',
                    fast: true
                });
            }

            // Show card loading state
            const cardLoadingInstanceId = this.showCardLoading(contentContainer, 'Loading insights...', {
                color: 'cyan',
                size: 'lg'
            });

            // Get filter values
            const confidenceMin = document.getElementById('confidenceFilter')?.value || null;
            const sortBy = document.getElementById('sortBy')?.value || 'created_at';
            const limit = 20;
            const offset = (this.currentPropositionsPage - 1) * limit;

            // Build query parameters
            const params = new URLSearchParams({
                limit: limit.toString(),
                offset: offset.toString(),
                sort_by: sortBy
            });

            if (confidenceMin) {
                params.append('confidence_min', confidenceMin);
            }

            // Fetch propositions
            const response = await fetch(`${this.apiBaseUrl}/propositions?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const propositions = await response.json();

            // Fetch count for stats
            const countParams = new URLSearchParams();
            if (confidenceMin) {
                countParams.append('confidence_min', confidenceMin);
            }

            const countResponse = await fetch(`${this.apiBaseUrl}/propositions/count?${countParams}`);
            const countData = await countResponse.json();

            // Hide loading states
            if (buttonLoadingInstanceId) {
                this.hideButtonLoading(buttonLoadingInstanceId);
            }
            this.hideCardLoading(cardLoadingInstanceId);

            // Display results
            this.displayPropositions(propositions, countData);
            this.updatePropositionsPagination(propositions.length, limit);

            this.showToast(`Loaded ${propositions.length} insights`, 'success');

        } catch (error) {
            console.error('Error loading propositions:', error);
            this.showToast(`Failed to load insights: ${error.message}`, 'error');
            this.displayEmptyPropositions();
        }
    }

    /**
     * Display propositions in the UI
     */
    displayPropositions(propositions, countData) {
        const contentContainer = document.getElementById('propositionsContent');
        const statsContainer = document.getElementById('propositionsStats');

        if (!contentContainer) return;

        // Show stats
        if (statsContainer && countData) {
            statsContainer.style.display = 'flex';
            statsContainer.innerHTML = `
                <div class="stat-item">
                    <i class="fas fa-lightbulb"></i>
                    <span>Total: ${countData.total_propositions} insights</span>
                </div>
                <div class="stat-item">
                    <i class="fas fa-filter"></i>
                    <span>Showing: ${propositions.length} results</span>
                </div>
                ${countData.confidence_filter ? `
                    <div class="stat-item">
                        <i class="fas fa-star"></i>
                        <span>Min confidence: ${countData.confidence_filter}</span>
                    </div>
                ` : ''}
            `;
        }

        // Display propositions
        if (propositions.length === 0) {
            this.displayEmptyPropositions();
            return;
        }

        contentContainer.innerHTML = propositions.map((prop, index) => 
            this.createPropositionCard(prop, index)
        ).join('');
    }

    /**
     * Create a proposition card HTML
     */
    createPropositionCard(proposition, index) {
        const confidence = proposition.confidence;
        const confidenceClass = this.getConfidenceClass(confidence);
        const confidenceLabel = this.getConfidenceLabel(confidence);
        
        const createdDate = new Date(proposition.created_at);
        const formattedDate = createdDate.toLocaleDateString() + ' ' + 
                            this.formatLocalTime(proposition.created_at);

        return `
            <div class="proposition-card" style="animation-delay: ${index * 0.1}s">
                <div class="proposition-header">
                    <div class="proposition-meta">
                        <span class="proposition-id">#${proposition.id}</span>
                        <span class="confidence-badge ${confidenceClass}">
                            <i class="fas fa-star"></i>
                            ${confidenceLabel}
                        </span>
                    </div>
                </div>
                
                <div class="proposition-text">
                    ${this.escapeHtml(proposition.text)}
                </div>
                
                ${proposition.reasoning ? `
                    <div class="proposition-reasoning">
                        <strong>Reasoning:</strong> ${this.escapeHtml(proposition.reasoning)}
                    </div>
                ` : ''}
                
                <div class="proposition-footer">
                    <div class="proposition-date">
                        <i class="fas fa-clock"></i>
                        <span>${formattedDate}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get confidence CSS class
     */
    getConfidenceClass(confidence) {
        if (!confidence) return 'confidence-none';
        if (confidence >= 8) return 'confidence-high';
        if (confidence >= 6) return 'confidence-medium';
        return 'confidence-low';
    }

    /**
     * Get confidence label
     */
    getConfidenceLabel(confidence) {
        if (!confidence) return 'No confidence';
        return `${confidence}/10`;
    }

    /**
     * Display empty state for propositions
     */
    displayEmptyPropositions() {
        const contentContainer = document.getElementById('propositionsContent');
        const statsContainer = document.getElementById('propositionsStats');
        
        if (statsContainer) {
            statsContainer.style.display = 'none';
        }

        if (contentContainer) {
            contentContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-lightbulb"></i>
                    <h3>No insights found</h3>
                    <p>No propositions match your current filters. Try adjusting the confidence level or submit more observations.</p>
                </div>
            `;
        }
    }

    /**
     * Update pagination controls
     */
    updatePropositionsPagination(resultCount, limit) {
        const paginationContainer = document.getElementById('propositionsPagination');
        const prevBtn = document.getElementById('prevPropositions');
        const nextBtn = document.getElementById('nextPropositions');
        const pageInfo = document.getElementById('propositionsPageInfo');

        if (!paginationContainer) return;

        // Show pagination if we have results
        if (resultCount > 0) {
            paginationContainer.style.display = 'flex';
            
            // Update page info
            if (pageInfo) {
                pageInfo.textContent = `Page ${this.currentPropositionsPage}`;
            }

            // Update button states
            if (prevBtn) {
                prevBtn.disabled = this.currentPropositionsPage <= 1;
            }

            if (nextBtn) {
                nextBtn.disabled = resultCount < limit;
            }
        } else {
            paginationContainer.style.display = 'none';
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Load memory propositions from the API (same as insights but for memory tab)
     */
    async loadMemoryPropositions() {
        const loadBtn = document.getElementById('loadMemoryPropositions');
        const contentContainer = document.getElementById('memoryPropositionsContent');
        const statsContainer = document.getElementById('memoryPropositionsStats');
        const paginationContainer = document.getElementById('memoryPropositionsPagination');

        if (!contentContainer) return;

        try {
            // Show loading state with text shimmer
            let buttonLoadingInstanceId = null;
            if (loadBtn) {
                buttonLoadingInstanceId = this.showButtonLoading(loadBtn, 'Loading insights...', {
                    color: 'cyan',
                    fast: true
                });
            }

            // Show card loading state
            const cardLoadingInstanceId = this.showCardLoading(contentContainer, 'Loading insights...', {
                color: 'cyan',
                size: 'lg'
            });

            // Get filter values
            const confidenceMin = document.getElementById('memoryConfidenceFilter')?.value || null;
            const sortBy = document.getElementById('memorySortBy')?.value || 'created_at';
            const limit = 20;
            const offset = (this.currentMemoryPage - 1) * limit;

            // Build query parameters
            const params = new URLSearchParams({
                limit: limit.toString(),
                offset: offset.toString(),
                sort_by: sortBy
            });

            if (confidenceMin) {
                params.append('confidence_min', confidenceMin);
            }

            // Fetch propositions
            const response = await fetch(`${this.apiBaseUrl}/propositions?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const propositions = await response.json();

            // Fetch count for stats
            const countParams = new URLSearchParams();
            if (confidenceMin) {
                countParams.append('confidence_min', confidenceMin);
            }

            const countResponse = await fetch(`${this.apiBaseUrl}/propositions/count?${countParams}`);
            const countData = await countResponse.json();

            // Hide loading states
            if (buttonLoadingInstanceId) {
                this.hideButtonLoading(buttonLoadingInstanceId);
            }
            this.hideCardLoading(cardLoadingInstanceId);

            // Display results
            this.displayMemoryPropositions(propositions, countData);
            this.updateMemoryPagination(propositions.length, limit);

            this.showToast(`Loaded ${propositions.length} insights`, 'success');

        } catch (error) {
            console.error('Error loading memory propositions:', error);
            this.showToast(`Failed to load insights: ${error.message}`, 'error');
            this.displayEmptyMemoryPropositions();
        }
    }

    /**
     * Display memory propositions in the UI
     */
    displayMemoryPropositions(propositions, countData) {
        const contentContainer = document.getElementById('memoryPropositionsContent');
        const statsContainer = document.getElementById('memoryPropositionsStats');

        if (!contentContainer) return;

        // Show stats
        if (statsContainer && countData) {
            statsContainer.style.display = 'flex';
            statsContainer.innerHTML = `
                <div class="stat-item">
                    <i class="fas fa-lightbulb"></i>
                    <span>Total: ${countData.total_propositions} insights</span>
                </div>
                <div class="stat-item">
                    <i class="fas fa-filter"></i>
                    <span>Showing: ${propositions.length} results</span>
                </div>
                ${countData.confidence_filter ? `
                    <div class="stat-item">
                        <i class="fas fa-chart-line"></i>
                        <span>Min Confidence: ${countData.confidence_filter}</span>
                    </div>
                ` : ''}
            `;
        }

        // Display propositions
        if (propositions.length === 0) {
            this.displayEmptyMemoryPropositions();
            return;
        }

        contentContainer.innerHTML = propositions.map((prop, index) => 
            this.createPropositionCard(prop, index)
        ).join('');
    }

    /**
     * Display empty state for memory propositions
     */
    displayEmptyMemoryPropositions() {
        const contentContainer = document.getElementById('memoryPropositionsContent');
        const statsContainer = document.getElementById('memoryPropositionsStats');
        
        if (statsContainer) {
            statsContainer.style.display = 'none';
        }

        if (contentContainer) {
            contentContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-lightbulb"></i>
                    <h3>No insights found</h3>
                    <p>No propositions match your current filters. Try adjusting the confidence level or submit more observations.</p>
                </div>
            `;
        }
    }

    /**
     * Update memory pagination controls
     */
    updateMemoryPagination(resultCount, limit) {
        const paginationContainer = document.getElementById('memoryPropositionsPagination');
        const prevBtn = document.getElementById('prevMemoryPropositions');
        const nextBtn = document.getElementById('nextMemoryPropositions');
        const pageInfo = document.getElementById('memoryPropositionsPageInfo');

        if (!paginationContainer) return;

        // Show pagination if we have results
        if (resultCount > 0) {
            paginationContainer.style.display = 'flex';
            
            // Update page info
            if (pageInfo) {
                pageInfo.textContent = `Page ${this.currentMemoryPage}`;
            }

            // Update button states
            if (prevBtn) {
                prevBtn.disabled = this.currentMemoryPage <= 1;
            }

            if (nextBtn) {
                nextBtn.disabled = resultCount < limit;
            }
        } else {
            paginationContainer.style.display = 'none';
        }
    }

    // ===== TAB NAVIGATION FUNCTIONALITY =====

    /**
     * Setup tab navigation event listeners
     */
    setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-button');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tabId = button.getAttribute('data-tab');
                this.switchTab(tabId);
            });
        });

        // Setup home page styles
        this.setupHomePageStyles();
        
        // Setup dynamic home page content
        this.setupHomePage();

        // Initially hide sidebar since home tab is active by default
        const sidebar = document.querySelector('.tabs-navigation');
        if (sidebar) {
            sidebar.style.display = 'none';
        }

        // Ensure top-nav layout is disabled on initial Home
        const main = document.querySelector('.main-content');
        if (main) {
            main.classList.remove('has-top-nav');
        }
    }

    /**
     * Switch to a specific tab
     */
    switchTab(tabName) {
        // Hide all tab panels
        const tabPanels = document.querySelectorAll('.tab-panel');
        tabPanels.forEach(panel => {
            panel.classList.remove('active');
        });

        // Remove active class from all tab buttons
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.classList.remove('active');
        });

        // Show the selected tab panel
        const selectedPanel = document.getElementById(`${tabName}-panel`);
        if (selectedPanel) {
            selectedPanel.classList.add('active');
        }

        // Add active class to the selected tab button
        const selectedButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (selectedButton) {
            selectedButton.classList.add('active');
        }

        // Handle sidebar visibility
        const sidebar = document.querySelector('.tabs-navigation');
        if (sidebar) {
            if (tabName === 'home' || tabName === 'memory') {
                sidebar.style.display = 'none';
            } else {
                sidebar.style.display = 'block';
            }
        }

        // Toggle top-nav layout only where sidebar used to show (non-Home tabs)
        const main = document.querySelector('.main-content');
        if (main) {
            if (tabName === 'home' || tabName === 'memory') {
                main.classList.remove('has-top-nav');
            } else {
                main.classList.add('has-top-nav');
            }
        }

        // Handle memory view body class
        if (tabName === 'memory') {
            document.body.classList.add('memory-view');
        } else {
            document.body.classList.remove('memory-view');
        }

        // Load content based on tab
        switch (tabName) {
            case 'timeline':
                this.loadTimeline();
                break;
            case 'narrative':
                this.loadNarrativeTimeline();
                break;
            case 'suggestions':
                // Initialize real-time suggestion stream
                this.initializeSuggestionStream();
                break;
            case 'memory':
                // Load memory propositions
                this.currentMemoryPage = 1;
                this.loadMemoryPropositions();
                break;
            // 'dashboard' tab removed; Home CTA routes to 'timeline'
        }
    }



    // ===== TIMELINE FUNCTIONALITY =====

    /**
     * Setup timeline event listeners
     */
    setupTimelineListeners() {
        const loadTimelineBtn = document.getElementById('loadTimeline');
        const timelineDateInput = document.getElementById('timelineDate');
        const timelineConfidenceFilter = document.getElementById('timelineConfidenceFilter');

        if (loadTimelineBtn) {
            loadTimelineBtn.addEventListener('click', () => this.loadTimeline());
        }

        if (timelineDateInput) {
            // Set default date to today
            const today = new Date().toISOString().split('T')[0];
            timelineDateInput.value = today;
        }

        if (timelineConfidenceFilter) {
            timelineConfidenceFilter.addEventListener('change', () => {
                // Auto-reload timeline when filter changes
                if (document.getElementById('timeline-panel').classList.contains('active')) {
                    this.loadTimeline();
                }
            });
        }
    }

    /**
     * Load timeline data for the selected date
     */
    async loadTimeline() {
        const loadBtn = document.getElementById('loadTimeline');
        const contentContainer = document.getElementById('timelineContent');
        const dateInput = document.getElementById('timelineDate');
        const confidenceFilter = document.getElementById('timelineConfidenceFilter');

        if (!contentContainer || !dateInput) return;

        try {
            // Show loading state with text shimmer
            let buttonLoadingInstanceId = null;
            if (loadBtn) {
                buttonLoadingInstanceId = this.showButtonLoading(loadBtn, 'Loading timeline...', {
                    color: 'cyan',
                    fast: true
                });
            }

            // Show card loading state
            const cardLoadingInstanceId = this.showCardLoading(contentContainer, 'Loading timeline...', {
                color: 'cyan',
                size: 'lg'
            });

            // Get filter values
            const date = dateInput.value;
            const confidenceMin = confidenceFilter?.value || null;

            // Build query parameters
            const params = new URLSearchParams({
                date: date
            });

            if (confidenceMin) {
                params.append('confidence_min', confidenceMin);
            }

            // Fetch timeline data
            const response = await fetch(`${this.apiBaseUrl}/propositions/by-hour?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const timelineData = await response.json();

            // Hide loading states
            if (buttonLoadingInstanceId) {
                this.hideButtonLoading(buttonLoadingInstanceId);
            }
            this.hideCardLoading(cardLoadingInstanceId);

            // Display results
            this.displayTimeline(timelineData);

            this.showToast(`Loaded timeline for ${date}`, 'success');

        } catch (error) {
            console.error('Error loading timeline:', error);
            this.showToast(`Failed to load timeline: ${error.message}`, 'error');
            this.displayEmptyTimeline();
        }
    }

    /**
     * Display timeline data in the UI
     */
    displayTimeline(timelineData) {
        const contentContainer = document.getElementById('timelineContent');

        if (!contentContainer) return;

        if (!timelineData.hourly_groups || timelineData.hourly_groups.length === 0) {
            this.displayEmptyTimeline();
            return;
        }

        // Format date for display - ensure proper timezone handling
        let displayDate;
        try {
            // timelineData.date is in format "2025-08-08" (date only)
            // We need to create a proper date object for the user's local timezone
            const [year, month, day] = timelineData.date.split('-').map(Number);
            // Create date using UTC to avoid timezone conversion issues
            const localDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0)); // month is 0-indexed, noon UTC
            
            displayDate = localDate.toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (error) {
            console.error('Error formatting date:', error);
            displayDate = 'Invalid Date';
        }

        contentContainer.innerHTML = `
            <div class="timeline-date-header">
                <h3 class="timeline-date-title">
                    <i class="fas fa-calendar"></i>
                    ${displayDate}
                </h3>
                <div class="timeline-stats">
                    <div class="timeline-stat">
                        <i class="fas fa-clock"></i>
                        <span>${timelineData.total_hours} ${timelineData.total_hours === 1 ? 'hour' : 'hours'}</span>
                    </div>
                    <div class="timeline-stat">
                        <i class="fas fa-lightbulb"></i>
                        <span>${timelineData.total_propositions} ${timelineData.total_propositions === 1 ? 'insight' : 'insights'}</span>
                    </div>
                </div>
            </div>
            <div class="timeline-hours">
                ${this.createConsolidatedTimelineCard(timelineData.hourly_groups)}
            </div>
        `;

        // Setup click handlers for hour items
        this.setupTimelineHourHandlers();
        this.setupTimelinePropositionHandlers();
    }

    /**
     * Create a single consolidated timeline card with all hours
     */
    createConsolidatedTimelineCard(hourGroups) {
        if (!hourGroups || hourGroups.length === 0) {
            return '<div class="empty-state">No hours found</div>';
        }

        const hourEntries = hourGroups.map((hourGroup, index) => {
            const hour = hourGroup.hour;
            const hourDisplay = hourGroup.hour_display;
            const count = hourGroup.proposition_count;
            
            return `
                <div class="timeline-hour-item" data-hour="${hour}" style="animation-delay: ${index * 0.1}s">
                    <div class="timeline-hour-header" onclick="window.zavionApp?.toggleTimelineHourDetails(${hour})">
                        <div class="timeline-hour-info">
                            <h4 class="timeline-hour-title">
                                <i class="fas fa-clock"></i>
                                ${hourDisplay}
                            </h4>
                            <span class="timeline-hour-count">${count} insights</span>
                        </div>
                        <div class="timeline-hour-toggle">
                            <i class="fas fa-chevron-down"></i>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Create details sections for each hour
        const detailsSections = hourGroups.map(hourGroup => {
            const hour = hourGroup.hour;
            const propositions = Array.isArray(hourGroup.propositions) ? [...hourGroup.propositions] : [];

            // Sort propositions by created_at ascending (unknowns last)
            propositions.sort((a, b) => {
                const aTime = a?.created_at ? new Date(a.created_at).getTime() : Infinity;
                const bTime = b?.created_at ? new Date(b.created_at).getTime() : Infinity;
                return aTime - bTime;
            });

            return `
                <div class="timeline-hour-details" id="timeline-hour-${hour}">
                    <div class="timeline-propositions">
                        <strong>Individual Insights:</strong>
                        ${propositions.map(prop => {
                            const timeLabel = prop?.created_at ? this.formatLocalTime(prop.created_at) : 'Unknown time';
                            const shortText = this.escapeHtml(prop.text);
                            const confidence = prop.confidence || 0;
                            const confidenceClass = confidence >= 80 ? 'confidence-high' : confidence >= 60 ? 'confidence-medium' : confidence >= 40 ? 'confidence-low' : 'confidence-none';
                            return `
                                <div class="timeline-proposition-card" onclick="event.stopPropagation(); window.zavionApp?.togglePropositionDetails(${prop.id})">
                                    <div class="timeline-proposition-header">
                                        <span class="timeline-proposition-time">${timeLabel}</span>
                                        <span class="confidence-badge ${confidenceClass}">
                                            <i class="fas fa-chart-line"></i>
                                            ${prop.confidence || 'N/A'}% confidence
                                        </span>
                                    </div>
                                    <div class="timeline-proposition-content" id="prop-${prop.id}">
                                        <div class="proposition-id">#${prop.id}</div>
                                        <div class="proposition-text">${shortText}</div>
                                        <span class="click-hint">Click for reasoning</span>
                                        <div class="proposition-full" style="display: none;">
                                            <div class="proposition-reasoning">
                                                <strong>Reasoning:</strong> ${this.escapeHtml(prop.reasoning || 'No reasoning provided')}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }).join('');

        return `
            ${hourEntries}
            ${detailsSections}
        `;
    }

    /**
     * Create a consolidated timeline card with all hours (legacy function for compatibility)
     */
    createTimelineHourItem(hourGroups, index) {
        // If hourGroups is a single hour group, wrap it in an array
        const groups = Array.isArray(hourGroups) ? hourGroups : [hourGroups];
        
        const hourEntries = groups.map((hourGroup, groupIndex) => {
            const hour = hourGroup.hour;
            const hourDisplay = hourGroup.hour_display;
            const count = hourGroup.proposition_count;
            
            return `
                <div class="timeline-hour-entry" data-hour="${hour}" style="animation-delay: ${(index * 0.1) + (groupIndex * 0.05)}s">
                    <div class="timeline-hour-left">
                        <div class="timeline-hour-bullet"></div>
                        <div class="timeline-hour-time">${hourDisplay}</div>
                        <div class="timeline-hour-count">${count} insights</div>
                    </div>
                    <div class="timeline-hour-action">
                        <span>See Insights</span>
                        <i class="fas fa-chevron-right"></i>
                    </div>
                </div>
            `;
        }).join('');

        // Create details sections for each hour
        const detailsSections = groups.map(hourGroup => {
            const hour = hourGroup.hour;
            const propositions = Array.isArray(hourGroup.propositions) ? [...hourGroup.propositions] : [];

            // Sort propositions by created_at ascending (unknowns last)
            propositions.sort((a, b) => {
                const aTime = a?.created_at ? new Date(a.created_at).getTime() : Infinity;
                const bTime = b?.created_at ? new Date(b.created_at).getTime() : Infinity;
                return aTime - bTime;
            });

            return `
                <div class="timeline-hour-details" id="timeline-hour-${hour}">
                    <div class="timeline-propositions">
                        <strong>Individual Insights:</strong>
                        ${propositions.map(prop => {
                            const timeLabel = prop?.created_at ? this.formatLocalTime(prop.created_at) : 'Unknown time';
                            const shortText = this.escapeHtml(prop.text);
                            const confidence = prop.confidence || 0;
                            const confidenceClass = confidence >= 80 ? 'confidence-high' : confidence >= 60 ? 'confidence-medium' : confidence >= 40 ? 'confidence-low' : 'confidence-none';
                            return `
                                <div class="timeline-proposition-card" onclick="event.stopPropagation(); window.zavionApp?.togglePropositionDetails(${prop.id})">
                                    <div class="timeline-proposition-header">
                                        <span class="timeline-proposition-time">${timeLabel}</span>
                                        <span class="confidence-badge ${confidenceClass}">
                                            <i class="fas fa-chart-line"></i>
                                            ${prop.confidence || 'N/A'}% confidence
                                        </span>
                                    </div>
                                    <div class="timeline-proposition-content" id="prop-${prop.id}">
                                        <div class="proposition-id">#${prop.id}</div>
                                        <div class="proposition-text">${shortText}</div>
                                        <span class="click-hint">Click for reasoning</span>
                                        <div class="proposition-full" style="display: none;">
                                            <div class="proposition-reasoning">
                                                <strong>Reasoning:</strong> ${this.escapeHtml(prop.reasoning || 'No reasoning provided')}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>

                </div>
            `;
        }).join('');

        return `
            <div class="timeline-hour-item" style="animation-delay: ${index * 0.1}s">
                <div class="timeline-hour-entries">
                    ${hourEntries}
                </div>
                ${detailsSections}
            </div>
        `;
    }

    /**
     * Setup click handlers for timeline hour items
     */
    setupTimelineHourHandlers() {
        const hourItems = document.querySelectorAll('.timeline-hour-item');
        
        hourItems.forEach(item => {
            const hour = item.dataset.hour;
            const details = document.getElementById(`timeline-hour-${hour}`);
            const toggle = item.querySelector('.timeline-hour-toggle i');
            
            if (details && toggle) {
                // Initially hide details
                details.style.display = 'none';
                toggle.classList.remove('fa-chevron-up');
                toggle.classList.add('fa-chevron-down');
            }
        });
    }

    /**
     * Toggle timeline hour details visibility
     */
    toggleTimelineHourDetails(hour) {
        const details = document.getElementById(`timeline-hour-${hour}`);
        const toggle = document.querySelector(`[data-hour="${hour}"] .timeline-hour-toggle i`);
        
        if (details && toggle) {
            const isVisible = details.style.display !== 'none';
            
            if (isVisible) {
                details.style.display = 'none';
                toggle.classList.remove('fa-chevron-up');
                toggle.classList.add('fa-chevron-down');
            } else {
                details.style.display = 'block';
                toggle.classList.remove('fa-chevron-down');
                toggle.classList.add('fa-chevron-up');
            }
        }
    }

    /**
     * Display empty timeline state
     */
    displayEmptyTimeline() {
        const contentContainer = document.getElementById('timelineContent');
        
        if (!contentContainer) return;

        contentContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-calendar-times" aria-hidden="true"></i>
                <h3>No insights found</h3>
                <p>No timeline data available for the selected date. Try selecting a different date or adjusting your filters.</p>
            </div>
        `;
    }

    /**
     * Setup narrative timeline event listeners
     */
    setupNarrativeTimelineListeners() {
        const loadNarrativeTimelineBtn = document.getElementById('loadNarrativeTimeline');
        const narrativeTimelineDateInput = document.getElementById('narrativeTimelineDate');

        if (loadNarrativeTimelineBtn) {
            loadNarrativeTimelineBtn.addEventListener('click', () => this.loadNarrativeTimeline());
        }

        if (narrativeTimelineDateInput) {
            // Set default date to today
            const today = new Date().toISOString().split('T')[0];
            narrativeTimelineDateInput.value = today;
        }
    }

    setupSuggestionsListeners() {
        // Production-grade polling system - automatically fetches suggestions
        // The system intelligently polls for new suggestions based on user activity
        
        // Set up cleanup for polling on page unload
        window.addEventListener('beforeunload', () => {
            if (this.suggestionPolling) {
                this.cleanupSuggestionPolling();
                console.log('Suggestion polling cleaned up on page unload');
            }
        });
    }

    /**
     * Load narrative timeline data
     */
    async loadNarrativeTimeline() {
        const loadBtn = document.getElementById('loadNarrativeTimeline');
        const contentContainer = document.getElementById('narrativeTimelineContent');
        const dateInput = document.getElementById('narrativeTimelineDate');

        if (!contentContainer || !dateInput) return;

        try {
            // Show loading state with text shimmer
            let buttonLoadingInstanceId = null;
            if (loadBtn) {
                buttonLoadingInstanceId = this.showButtonLoading(loadBtn, 'Loading timeline...', {
                    color: 'cyan',
                    fast: true
                });
            }

            // Show card loading state
            const cardLoadingInstanceId = this.showCardLoading(contentContainer, 'Loading narrative timeline...', {
                color: 'cyan',
                size: 'lg'
            });

            // Get date value
            const date = dateInput.value;

            // Fetch narrative timeline data
            const response = await fetch(`${this.apiBaseUrl}/observations/by-hour?date=${date}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const timelineData = await response.json();

            // Hide loading states
            if (buttonLoadingInstanceId) {
                this.hideButtonLoading(buttonLoadingInstanceId);
            }
            this.hideCardLoading(cardLoadingInstanceId);

            // Display results
            this.displayNarrativeTimeline(timelineData);

            this.showToast(`Loaded narrative timeline for ${date}`, 'success');

        } catch (error) {
            console.error('Error loading narrative timeline:', error);
            this.showToast(`Failed to load narrative timeline: ${error.message}`, 'error');
            this.displayEmptyNarrativeTimeline();
        }
    }

    /**
     * Display narrative timeline data in the UI
     */
    displayNarrativeTimeline(timelineData) {
        const contentContainer = document.getElementById('narrativeTimelineContent');

        if (!contentContainer) return;

        if (!timelineData.hourly_groups || timelineData.hourly_groups.length === 0) {
            this.displayEmptyNarrativeTimeline();
            return;
        }

        // Format date for display - ensure proper timezone handling
        let displayDate;
        try {
            // timelineData.date is in format "2025-08-08" (date only)
            // We need to create a proper date object for the user's local timezone
            const [year, month, day] = timelineData.date.split('-').map(Number);
            // Create date using UTC to avoid timezone conversion issues
            const localDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0)); // month is 0-indexed, noon UTC
            
            displayDate = localDate.toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (error) {
            console.error('Error formatting narrative timeline date:', error);
            displayDate = 'Invalid Date';
        }

        contentContainer.innerHTML = `
            <div class="narrative-timeline-date-header">
                <h3 class="narrative-timeline-date-title">
                    <i class="fas fa-calendar"></i>
                    ${displayDate}
                </h3>
                <div class="narrative-timeline-stats">
                    <div class="narrative-timeline-stat">
                        <i class="fas fa-clock"></i>
                        <span>${timelineData.total_hours} ${timelineData.total_hours === 1 ? 'hour' : 'hours'}</span>
                    </div>
                    <div class="narrative-timeline-stat">
                        <i class="fas fa-list-alt"></i>
                        <span>${timelineData.total_observations} ${timelineData.total_observations === 1 ? 'activity' : 'activities'}</span>
                    </div>
                    <div class="narrative-timeline-stat">
                        <i class="fas fa-globe"></i>
                        <span>${this.getCurrentTimezone()}</span>
                    </div>
                </div>
            </div>
            <div class="narrative-timeline-hours">
                ${timelineData.hourly_groups.map((hourGroup, index) => 
                    this.createNarrativeTimelineHourItem(hourGroup, index)
                ).join('')}
            </div>
        `;

        // Setup click handlers for expandable hours
        this.setupNarrativeTimelineHourHandlers();
    }

    /**
     * Clean up raw transcription data for better readability
     */
    cleanTranscriptionData(content) {
        if (!content) return '';

        let cleaned = content;

        // Remove technical headers and metadata
        cleaned = cleaned.replace(/```plaintext\s*/g, '');
        cleaned = cleaned.replace(/```\s*$/g, '');
        cleaned = cleaned.replace(/Application:\s*/g, '');
        cleaned = cleaned.replace(/Window Title:\s*/g, '');
        cleaned = cleaned.replace(/File Path:\s*/g, '');
        cleaned = cleaned.replace(/URL:\s*/g, '');
        cleaned = cleaned.replace(/Timestamp:\s*/g, '');
        cleaned = cleaned.replace(/Date:\s*/g, '');

        // Remove file listings and technical details
        cleaned = cleaned.replace(/File Explorer:\s*[-•]\s*[^\n]+\n/g, '');
        cleaned = cleaned.replace(/[-•]\s*[^\n]+\.(py|md|txt|json|yaml|yml|toml|lock|gitignore|license|readme)/gi, '');
        cleaned = cleaned.replace(/[-•]\s*__pycache__\//g, '');
        cleaned = cleaned.replace(/[-•]\s*\.git\//g, '');
        cleaned = cleaned.replace(/[-•]\s*\.vscode\//g, '');

        // Remove terminal output and logs
        cleaned = cleaned.replace(/Terminal Output:\s*/g, '');
        cleaned = cleaned.replace(/PS C:[^>]*>/g, '');
        cleaned = cleaned.replace(/\d{2}:\d{2}:\d{2}\s*\[Screen\]\s*[^\n]*/g, '');
        cleaned = cleaned.replace(/INFO:[^:]*:\s*[^\n]*/g, '');
        cleaned = cleaned.replace(/DEBUG:[^:]*:\s*[^\n]*/g, '');
        cleaned = cleaned.replace(/WARNING:[^:]*:\s*[^\n]*/g, '');
        cleaned = cleaned.replace(/ERROR:[^:]*:\s*[^\n]*/g, '');

        // Remove markdown formatting
        cleaned = cleaned.replace(/#{1,6}\s*/g, '');
        cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '$1');
        cleaned = cleaned.replace(/\*([^*]+)\*/g, '$1');
        cleaned = cleaned.replace(/`([^`]+)`/g, '$1');

        // Remove code blocks
        cleaned = cleaned.replace(/```bash\s*[^`]*```/g, '');
        cleaned = cleaned.replace(/```\s*[^`]*```/g, '');

        // Clean up application names
        cleaned = cleaned.replace(/Application:\s*([^\n]+)/g, 'Using $1');
        cleaned = cleaned.replace(/Title:\s*([^\n]+)/g, 'Viewing: $1');

        // Extract meaningful content
        const lines = cleaned.split('\n').filter(line => {
            const trimmed = line.trim();
            return trimmed.length > 0 && 
                   !trimmed.match(/^[-•\s]*$/) &&
                   !trimmed.match(/^[A-Z][a-z]+:\s*$/) &&
                   !trimmed.match(/^\d{2}:\d{2}:\d{2}/) &&
                   !trimmed.match(/^PS C:/) &&
                   !trimmed.match(/^INFO:/) &&
                   !trimmed.match(/^DEBUG:/) &&
                   !trimmed.match(/^WARNING:/) &&
                   !trimmed.match(/^ERROR:/);
        });

        // Join and clean up
        cleaned = lines.join('\n').trim();

        // If we have meaningful content, format it nicely
        if (cleaned.length > 0) {
            // Extract the most meaningful parts
            const meaningfulParts = [];
            
            // Look for application usage
            const appMatch = content.match(/Application:\s*([^\n]+)/);
            if (appMatch) {
                meaningfulParts.push(`Using ${appMatch[1].trim()}`);
            }

            // Look for window titles
            const titleMatch = content.match(/Window Title:\s*([^\n]+)/);
            if (titleMatch) {
                meaningfulParts.push(`Viewing: ${titleMatch[1].trim()}`);
            }

            // Look for URLs
            const urlMatch = content.match(/URL:\s*([^\n]+)/);
            if (urlMatch) {
                meaningfulParts.push(`Browsing: ${urlMatch[1].trim()}`);
            }

            // Look for visible text content
            const textMatch = content.match(/Visible Text Content and UI Elements:\s*([^]*?)(?=\n[A-Z]|$)/);
            if (textMatch) {
                const textContent = textMatch[1].trim();
                if (textContent.length > 0) {
                    meaningfulParts.push(`Content: ${textContent.substring(0, 100)}${textContent.length > 100 ? '...' : ''}`);
                }
            }

            // If we found meaningful parts, use them
            if (meaningfulParts.length > 0) {
                return meaningfulParts.join(' • ');
            }

            // Otherwise, return cleaned content (truncated if too long)
            return cleaned.length > 200 ? cleaned.substring(0, 200) + '...' : cleaned;
        }

        // Fallback: return a generic description
        return 'Screen activity recorded';
    }

    /**
     * Create HTML for a narrative timeline hour item
     */
    createNarrativeTimelineHourItem(hourGroup, index) {
        const hour = hourGroup.hour_display;
        const observationCount = hourGroup.observation_count;
        const observations = hourGroup.observations;

        return `
            <div class="narrative-timeline-hour-item" data-hour="${hourGroup.hour}">
                <div class="narrative-timeline-hour-header" onclick="window.zavionApp?.toggleNarrativeTimelineHourDetails(${hourGroup.hour})">
                    <div class="narrative-timeline-hour-info">
                        <h4 class="narrative-timeline-hour-title">
                            <i class="fas fa-clock"></i>
                            ${hour}
                        </h4>
                        <span class="narrative-timeline-hour-count">${observationCount} activities</span>
                    </div>
                    <div class="narrative-timeline-hour-toggle">
                        <i class="fas fa-chevron-down"></i>
                    </div>
                </div>
                <div class="narrative-timeline-hour-details" id="narrative-timeline-hour-${hourGroup.hour}">
                    <div class="narrative-timeline-observations">
                        ${observations.map((obs, obsIndex) => `
                            <div class="narrative-timeline-observation">
                                <div class="narrative-timeline-observation-content">
                                    <p>${this.escapeHtml(this.cleanTranscriptionData(obs.content))}</p>
                                </div>
                                <div class="narrative-timeline-observation-meta">
                                    <span class="narrative-timeline-observation-time">
                                        ${this.formatLocalTime(obs.created_at)}
                                    </span>
                                    <span class="narrative-timeline-observation-type">
                                        ${obs.content_type}
                                    </span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Setup click handlers for narrative timeline hour items
     */
    setupNarrativeTimelineHourHandlers() {
        const hourItems = document.querySelectorAll('.narrative-timeline-hour-item');
        
        hourItems.forEach(item => {
            const hour = item.dataset.hour;
            const details = document.getElementById(`narrative-timeline-hour-${hour}`);
            const toggle = item.querySelector('.narrative-timeline-hour-toggle i');
            
            if (details && toggle) {
                // Initially hide details
                details.style.display = 'none';
                toggle.classList.remove('fa-chevron-up');
                toggle.classList.add('fa-chevron-down');
            }
        });
    }

    /**
     * Toggle narrative timeline hour details visibility
     */
    toggleNarrativeTimelineHourDetails(hour) {
        const details = document.getElementById(`narrative-timeline-hour-${hour}`);
        const toggle = document.querySelector(`[data-hour="${hour}"] .narrative-timeline-hour-toggle i`);
        
        if (details && toggle) {
            const isVisible = details.style.display !== 'none';
            
            if (isVisible) {
                details.style.display = 'none';
                toggle.classList.remove('fa-chevron-up');
                toggle.classList.add('fa-chevron-down');
            } else {
                details.style.display = 'block';
                toggle.classList.remove('fa-chevron-down');
                toggle.classList.add('fa-chevron-up');
            }
        }
    }

    /**
     * Setup home page styles
     */
    setupHomePageStyles() {
        // Add CSS for home page if not already present
        if (!document.getElementById('home-page-styles')) {
            const style = document.createElement('style');
            style.id = 'home-page-styles';
            style.textContent = `
                .home-actions-container {
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    min-height: 70vh;
                    width: 100%;
                    padding: 2rem;
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                }
                .home-welcome-header {
                    text-align: center;
                    margin-bottom: 3rem;
                }
                .home-welcome-header h1 {
                    font-size: 2rem;
                    font-weight: 600;
                    color: var(--text-primary, #1f2937);
                    margin: 0;
                    line-height: 1.2;
                }
                .home-actions-grid {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 2rem;
                    flex-wrap: wrap;
                }
                .home-action-button {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 1rem;
                    padding: 2rem 1.5rem;
                    background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-size: 1.1rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
                    min-height: 140px;
                }
                .home-action-button:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4);
                    background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
                }
                .home-action-button i {
                    font-size: 2rem;
                    margin-bottom: 0.5rem;
                }
                .home-action-button .button-title {
                    font-size: 1.1rem;
                    font-weight: 600;
                    text-align: center;
                    margin-bottom: 0.25rem;
                }
                .home-action-button .button-subtitle {
                    font-size: 0.85rem;
                    font-weight: 400;
                    text-align: center;
                    opacity: 0.8;
                    line-height: 1.2;
                }
                #home-panel {
                    position: relative;
                    height: 100vh;
                }
                .recent-suggestions-preview {
                    margin: 1rem 0;
                    display: flex;
                    flex-direction: column;
                    gap: 0.4rem;
                    max-width: 500px;
                    width: 100%;
                }
                .recent-suggestion-card {
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(5px);
                    border: 1px solid rgba(139, 92, 246, 0.1);
                    border-radius: 6px;
                    padding: 0.5rem 0.75rem;
                    font-size: 0.75rem;
                    color: var(--text-muted, #6b7280);
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .recent-suggestion-card:hover {
                    background: rgba(255, 255, 255, 0.08);
                    border-color: rgba(139, 92, 246, 0.2);
                }
                .suggestion-text {
                    margin-bottom: 0.2rem;
                    line-height: 1.2;
                    font-weight: 400;
                }
                .suggestion-meta {
                    font-size: 0.65rem;
                    opacity: 0.6;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .loading-suggestions, .stats-loading {
                    text-align: center;
                    font-size: 0.75rem;
                    opacity: 0.5;
                    color: var(--text-muted, #6b7280);
                    font-style: italic;
                }
                .home-stats-bar {
                    position: absolute;
                    bottom: 2rem;
                    left: 50%;
                    transform: translateX(-50%);
                    font-size: 0.75rem;
                    color: var(--text-muted, #6b7280);
                    opacity: 0.8;
                    text-align: center;
                }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * Setup dynamic home page content
     */
    setupHomePage() {
        this.updateGreeting();
        this.loadRecentSuggestions();
        this.loadHomeStats();
    }

    /**
     * Update greeting based on time of day
     */
    updateGreeting() {
        const greetingElement = document.getElementById('dynamic-greeting');
        if (!greetingElement) return;

        const now = new Date();
        const hour = now.getHours();
        let timeOfDay;

        if (hour < 12) {
            timeOfDay = 'morning';
        } else if (hour < 17) {
            timeOfDay = 'afternoon';
        } else {
            timeOfDay = 'evening';
        }

        greetingElement.textContent = `Good ${timeOfDay}! Ready to learn about yourself?`;
    }

    /**
     * Load recent suggestions for homepage preview
     */
    async loadRecentSuggestions() {
        const previewContainer = document.getElementById('recent-suggestions-preview');
        if (!previewContainer) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/suggestions/history?limit=2`);
            if (response.ok) {
                const suggestions = await response.json();
                
                if (suggestions.length === 0) {
                    previewContainer.innerHTML = `
                        <div class="loading-suggestions">No recent suggestions yet. Enable suggestions to see them here!</div>
                    `;
                    return;
                }

                const suggestionsHTML = suggestions.map(suggestion => {
                    const timeAgo = this.getTimeAgo(new Date(suggestion.created_at));
                    const suggestionText = suggestion.title || suggestion.description || 'No suggestion text';
                    return `
                        <div class="recent-suggestion-card" onclick="window.zavionApp?.switchTab('suggestions')">
                            <div class="suggestion-text">${this.escapeHtml(suggestionText.substring(0, 60))}${suggestionText.length > 60 ? '...' : ''}</div>
                            <div class="suggestion-meta">
                                <span>${timeAgo}</span>
                                <span>${suggestion.category || 'General'}</span>
                            </div>
                        </div>
                    `;
                }).join('');

                previewContainer.innerHTML = suggestionsHTML;
            }
        } catch (error) {
            console.error('Error loading recent suggestions:', error);
            previewContainer.innerHTML = `<div class="loading-suggestions">Unable to load recent suggestions</div>`;
        }
    }

    /**
     * Load stats for homepage stats bar
     */
    async loadHomeStats() {
        const statsBar = document.getElementById('home-stats-bar');
        if (!statsBar) return;

        try {
            // Get total count
            const countResponse = await fetch(`${this.apiBaseUrl}/propositions/count`);
            let totalInsights = 0;
            if (countResponse.ok) {
                const countData = await countResponse.json();
                totalInsights = countData.total_propositions; // API returns total_propositions, not count
            }

            // Get recent insights to calculate "last active"
            const recentResponse = await fetch(`${this.apiBaseUrl}/propositions?limit=1&sort_by=created_at`);
            let lastActiveText = 'No activity yet';
            if (recentResponse.ok) {
                const recentData = await recentResponse.json(); // Direct array
                if (recentData && recentData.length > 0) {
                    const lastInsight = recentData[0];
                    const lastActiveTime = this.getTimeAgo(new Date(lastInsight.created_at));
                    lastActiveText = `Last active ${lastActiveTime}`;
                }
            }

            statsBar.innerHTML = `${totalInsights} insights total • ${lastActiveText}`;
        } catch (error) {
            console.error('Error loading home stats:', error);
            statsBar.innerHTML = 'Stats unavailable';
        }
    }

    /**
     * Setup click handlers for timeline propositions
     */
    setupTimelinePropositionHandlers() {
        // Add CSS for expanded state if not already present
        if (!document.getElementById('timeline-proposition-styles')) {
            const style = document.createElement('style');
            style.id = 'timeline-proposition-styles';
            style.textContent = `
                .timeline-proposition-card {
                    background: rgba(255, 255, 255, 0.7);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 8px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
                }
                .timeline-proposition-card:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    background: rgba(255, 255, 255, 0.8);
                }
                .timeline-proposition-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 6px;
                }
                .timeline-proposition-time {
                    font-size: 0.75em;
                    color: #666;
                    font-weight: 500;
                }
                .proposition-id {
                    background: #f3f4f6;
                    color: #6b7280;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 0.7em;
                    font-weight: 600;
                    font-family: monospace;
                    margin-bottom: 4px;
                    display: inline-block;
                }
                .proposition-text {
                    color: #374151;
                    font-size: 0.85em;
                    line-height: 1.4;
                    margin-bottom: 4px;
                    font-weight: 500;
                }
                .click-hint {
                    font-size: 0.7em;
                    color: #9ca3af;
                    font-style: italic;
                }
                .proposition-full {
                    margin-top: 8px;
                    padding: 8px;
                    background: rgba(0, 0, 0, 0.05);
                    border-radius: 6px;
                    border-left: 2px solid #8b5cf6;
                }
                .proposition-reasoning {
                    color: #4b5563;
                    line-height: 1.4;
                    font-size: 0.8em;
                }
                .timeline-hour-item {
                    display: block !important;
                }
                .timeline-hour-item .timeline-hour-left {
                    position: sticky;
                    top: 10px;
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    z-index: 100;
                    padding: 12px;
                    border-radius: 12px;
                    margin-bottom: 12px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                .timeline-hour-button {
                    margin: 0 0 16px 0;
                    width: 100%;
                    padding: 12px 24px;
                    background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 0.9em;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
                    text-align: center;
                    display: block;
                }
                .timeline-hour-button:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
                    background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
                }

                /* Timeline and Narrative Timeline empty state styling */
                .timeline-content .empty-state,
                .narrative-timeline-content .empty-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    padding: var(--spacing-xxl, 3rem);
                    color: var(--text-secondary, #6b7280);
                    min-height: 300px;
                }

                .timeline-content .empty-state i,
                .narrative-timeline-content .empty-state i {
                    font-size: 4rem;
                    color: var(--brand-cyan, #06b6d4);
                    margin-bottom: var(--spacing-lg, 1.5rem);
                    opacity: 0.7;
                }

                .timeline-content .empty-state h3,
                .narrative-timeline-content .empty-state h3 {
                    font-size: var(--font-size-xl, 1.25rem);
                    font-weight: 600;
                    color: var(--text-primary, #1f2937);
                    margin-bottom: var(--spacing-sm, 0.5rem);
                }

                .timeline-content .empty-state p,
                .narrative-timeline-content .empty-state p {
                    font-size: var(--font-size-base, 1rem);
                    line-height: 1.5;
                    max-width: 400px;
                    color: var(--text-muted, #9ca3af);
                }
                .timeline-hour-details {
                    margin-top: 0 !important;
                }
                .timeline-propositions {
                    padding: 0 !important;
                    background: transparent !important;
                    border: none !important;
                }
                .confidence-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 0.7em;
                    font-weight: 600;
                    white-space: nowrap;
                }
                .confidence-badge.confidence-high {
                    background: rgba(16, 185, 129, 0.1);
                    color: #059669;
                    border: 1px solid rgba(16, 185, 129, 0.2);
                }
                .confidence-badge.confidence-medium {
                    background: rgba(245, 158, 11, 0.1);
                    color: #d97706;
                    border: 1px solid rgba(245, 158, 11, 0.2);
                }
                .confidence-badge.confidence-low {
                    background: rgba(239, 68, 68, 0.1);
                    color: #dc2626;
                    border: 1px solid rgba(239, 68, 68, 0.2);
                }
                .confidence-badge.confidence-none {
                    background: rgba(156, 163, 175, 0.1);
                    color: #6b7280;
                    border: 1px solid rgba(156, 163, 175, 0.2);
                }

            `;
            document.head.appendChild(style);
        }
    }

    /**
     * Toggle proposition details visibility
     */
    togglePropositionDetails(propId) {
        const propElement = document.getElementById(`prop-${propId}`);
        if (propElement) {
            const fullDetails = propElement.querySelector('.proposition-full');
            const clickHint = propElement.querySelector('.click-hint');
            
            if (fullDetails.style.display === 'none') {
                fullDetails.style.display = 'block';
                clickHint.textContent = 'Click to hide reasoning';
            } else {
                fullDetails.style.display = 'none';
                clickHint.textContent = 'Click for reasoning';
            }
        }
    }

    /**
     * Format datetime to local timezone
     */
    formatLocalTime(dateString) {
        try {
            console.log('🔥🔥🔥 formatLocalTime CALLED with input:', dateString);
            
            // Parse the UTC date string and convert to local time
            const date = new Date(dateString);
            
            console.log('Parsed date object:', date);
            console.log('Date.getTime():', date.getTime());
            console.log('Is valid:', !isNaN(date.getTime()));
            
            // Check if the date is valid
            if (isNaN(date.getTime())) {
                console.log('Invalid date, returning error');
                return 'Invalid time';
            }
            
            // If the dateString doesn't have timezone info, assume it's UTC
            // and create a proper UTC date object
            if (!dateString.includes('Z') && !dateString.includes('+')) {
                console.log('No timezone info, treating as UTC');
                // Treat as UTC and convert to local
                const utcDate = new Date(dateString + 'Z');
                if (!isNaN(utcDate.getTime())) {
                    const result = utcDate.toLocaleTimeString('en-US', {
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true,
                        timeZoneName: 'short'
                    });
                    console.log('UTC conversion result:', result);
                    return result;
                }
            }
            
            // Format in local timezone
            const result = date.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true,
                timeZoneName: 'short' // This will show the timezone
            });
            console.log('Direct conversion result:', result);
            return result;
        } catch (error) {
            console.error('Error formatting time:', error);
            return 'Time error';
        }
    }

    /**
     * Get current timezone name
     */
    getCurrentTimezone() {
        try {
            return Intl.DateTimeFormat().resolvedOptions().timeZone;
        } catch (error) {
            return 'Local Time';
        }
    }

    /**
     * Display empty narrative timeline state
     */
    displayEmptyNarrativeTimeline() {
        const contentContainer = document.getElementById('narrativeTimelineContent');
        
        if (!contentContainer) return;

        contentContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-list-alt" aria-hidden="true"></i>
                <h3>No observations found</h3>
                <p>No raw observations available for the selected date. Try selecting a different date or check if tracking was active.</p>
            </div>
        `;
    }

    // =============================================================================
    // GUMBO REAL-TIME SUGGESTION SYSTEM (SSE)
    // =============================================================================
        
    // Production-grade suggestion polling system
    initializeSuggestionStream() {
        const content = document.getElementById('suggestionsContent');
        if (!content) return;
        
        // Load all existing suggestions organized by time
        this.loadAllSuggestions();
        
        // Initialize polling for new suggestions
        this.initializeSuggestionPolling();
    }

    initializeSuggestionPolling() {
        // Initialize polling system
        this.suggestionPolling = {
            isActive: false,
            interval: null,
            lastFetch: null,
            retryCount: 0,
            maxRetries: 3,
            baseDelay: 30000, // 30 seconds
            maxDelay: 300000, // 5 minutes
            lastModified: null,
            suggestionsCache: new Map(),
            isUserActive: true,
            errorCount: 0,
            maxErrors: 5
        };

        // Start polling
        this.startSuggestionPolling();
        
        // Set up user activity detection
        this.setupUserActivityDetection();
        
        // Initial fetch
        this.fetchSuggestions();
    }

    startSuggestionPolling() {
        if (this.suggestionPolling.isActive) return;
        
        this.suggestionPolling.isActive = true;
        this.suggestionPolling.interval = setInterval(() => {
            this.fetchSuggestions();
        }, this.suggestionPolling.baseDelay);
        
        console.log('✅ Suggestion polling started');
        this.updateSuggestionUI('monitoring');
    }

    stopSuggestionPolling() {
        if (this.suggestionPolling.interval) {
            clearInterval(this.suggestionPolling.interval);
            this.suggestionPolling.interval = null;
        }
        this.suggestionPolling.isActive = false;
        console.log('⏹️ Suggestion polling stopped');
    }

    async fetchSuggestions() {
        try {
            // Check if user is active to adjust polling frequency
            if (!this.suggestionPolling.isUserActive) {
                console.log('👤 User inactive, skipping suggestion fetch');
                return;
            }

            // Prepare headers for conditional requests
            const headers = {};
            if (this.suggestionPolling.lastModified) {
                headers['If-Modified-Since'] = this.suggestionPolling.lastModified;
            }

            const response = await fetch(`${this.apiBaseUrl}/suggestions/history`, {
                method: 'GET',
                headers: headers,
                signal: AbortSignal.timeout(10000) // 10 second timeout
            });

            if (response.status === 304) {
                console.log('✅ No new suggestions (304 Not Modified)');
                this.suggestionPolling.errorCount = 0; // Reset error count on success
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Update last modified header
            const lastModified = response.headers.get('Last-Modified');
            if (lastModified) {
                this.suggestionPolling.lastModified = lastModified;
            }

            const suggestions = await response.json();
            console.log(`🎯 Fetched ${suggestions.length} suggestions`);
            
            // Process and display suggestions
            this.processSuggestions(suggestions);
            
            // Reset error tracking on success
            this.suggestionPolling.errorCount = 0;
            this.suggestionPolling.retryCount = 0;
            this.suggestionPolling.lastFetch = Date.now();
            
            // Adaptive polling: reduce frequency if no new suggestions
            if (suggestions.length === 0) {
                this.adjustPollingFrequency('reduce');
            } else {
                this.adjustPollingFrequency('normal');
            }

        } catch (error) {
            console.error('❌ Error fetching suggestions:', error);
            this.handleSuggestionFetchError(error);
        }
    }

    processSuggestions(suggestions) {
        // Check if suggestions have actually changed
        const suggestionsHash = this.hashSuggestions(suggestions);
        if (this.suggestionPolling.suggestionsCache.get('hash') === suggestionsHash) {
            console.log('🔄 Suggestions unchanged, skipping re-render');
            return;
        }

        // Update cache
        this.suggestionPolling.suggestionsCache.set('hash', suggestionsHash);
        this.suggestionPolling.suggestionsCache.set('data', suggestions);
        this.suggestionPolling.suggestionsCache.set('timestamp', Date.now());

        // Display suggestions
        this.displaySuggestions({ suggestions: suggestions });
    }

    hashSuggestions(suggestions) {
        // Simple hash for change detection
        return JSON.stringify(suggestions.map(s => ({ id: s.id, updated_at: s.updated_at || s.created_at })));
    }

    handleSuggestionFetchError(error) {
        this.suggestionPolling.errorCount++;
        
        if (this.suggestionPolling.errorCount >= this.suggestionPolling.maxErrors) {
            console.error('🚨 Max suggestion fetch errors reached, stopping polling');
            this.updateSuggestionUI('error', { message: 'Too many errors, polling stopped' });
            this.stopSuggestionPolling();
            return;
        }

        // Exponential backoff for retries
        const backoffDelay = Math.min(
            this.suggestionPolling.baseDelay * Math.pow(2, this.suggestionPolling.retryCount),
            this.suggestionPolling.maxDelay
        );

        console.log(`⏳ Retrying suggestion fetch in ${backoffDelay}ms (attempt ${this.suggestionPolling.retryCount + 1})`);
        
        setTimeout(() => {
            this.fetchSuggestions();
        }, backoffDelay);

        this.suggestionPolling.retryCount++;
        
        // Show user-friendly error message
        this.updateSuggestionUI('error', { 
            message: `Connection issue: ${error.message}. Retrying...` 
        });
    }

    adjustPollingFrequency(action) {
        if (action === 'reduce' && this.suggestionPolling.isActive) {
            // Reduce frequency for inactive periods
            const newInterval = Math.min(this.suggestionPolling.baseDelay * 2, this.suggestionPolling.maxDelay);
            if (this.suggestionPolling.interval) {
                clearInterval(this.suggestionPolling.interval);
                this.suggestionPolling.interval = setInterval(() => {
                    this.fetchSuggestions();
                }, newInterval);
            }
            console.log(`🐌 Reduced polling frequency to ${newInterval}ms`);
        } else if (action === 'normal' && this.suggestionPolling.isActive) {
            // Restore normal frequency
            if (this.suggestionPolling.interval) {
                clearInterval(this.suggestionPolling.interval);
                this.suggestionPolling.interval = setInterval(() => {
                    this.fetchSuggestions();
                }, this.suggestionPolling.baseDelay);
            }
            console.log(`🚀 Restored normal polling frequency (${this.suggestionPolling.baseDelay}ms)`);
        }
    }

    setupUserActivityDetection() {
        let activityTimeout;
        const resetActivity = () => {
            this.suggestionPolling.isUserActive = true;
            clearTimeout(activityTimeout);
            activityTimeout = setTimeout(() => {
                this.suggestionPolling.isUserActive = false;
                console.log('👤 User marked as inactive, reducing polling frequency');
            }, 300000); // 5 minutes of inactivity
        };

        // Reset activity on user interactions
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'].forEach(event => {
            document.addEventListener(event, resetActivity, { passive: true });
        });

        // Initial activity
        resetActivity();
    }

    // Cleanup method for component unmounting
    cleanupSuggestionPolling() {
        this.stopSuggestionPolling();
        this.suggestionPolling = null;
    }

    // Removed old SSE reconnection method - replaced with robust polling

    updateSuggestionUI(status, data = null) {
        const content = document.getElementById('suggestionsContent');
        if (!content) return;

        switch (status) {
            case 'connecting':
                content.innerHTML = `
                    <div class="stream-status connecting">
                        <div class="status-icon">🔄</div>
                        <div class="status-text">
                            <div class="main-text">Initializing suggestion system...</div>
                            <div class="sub-text">Setting up intelligent polling</div>
                        </div>
                    </div>
                `;
                break;
                
            case 'monitoring':
                content.innerHTML = `
                    <div class="stream-status monitoring">
                        <div class="status-icon">👁️</div>
                        <div class="status-text">
                            <div class="main-text">Monitoring for intelligent suggestions</div>
                            <div class="sub-text">Smart polling system active - checking every 30 seconds</div>
                        </div>
                        <div class="monitoring-details">
                            <div class="detail-item">
                                <span class="detail-label">Polling:</span>
                                <span class="detail-value">Active (${this.suggestionPolling?.baseDelay / 1000}s)</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Last Check:</span>
                                <span class="detail-value">${this.suggestionPolling?.lastFetch ? new Date(this.suggestionPolling.lastFetch).toLocaleTimeString() : 'Never'}</span>
                            </div>
                        </div>
                    </div>
                `;
                break;
                
            case 'error':
                content.innerHTML = `
                    <div class="stream-status error">
                        <div class="status-icon">❌</div>
                        <div class="status-text">
                            <div class="main-text">Connection Error</div>
                            <div class="sub-text">${data?.message || 'Failed to fetch suggestions'}</div>
                        </div>
                        <button class="retry-btn" onclick="window.zavionApp.fetchSuggestions()">🔄 Retry</button>
                        <button class="retry-btn" onclick="window.zavionApp.initializeSuggestionPolling()">🔄 Restart Polling</button>
                    </div>
                `;
                break;
                break;
                
            case 'error':
            case 'disconnected':
                content.innerHTML = `
                    <div class="error-state">
                        <div class="error-icon">⚠️</div>
                        <h3>Stream ${status === 'error' ? 'Error' : 'Disconnected'}</h3>
                        <p>${data?.message || 'Unable to connect to suggestion stream'}</p>
                        <button class="retry-btn" onclick="window.zavionApp.initializeSuggestionStream()">🔄 Reconnect</button>
                    </div>
                `;
                break;
        }
    }
    
    displaySuggestionBatch(batch) {
        // When new batch arrives, add to existing suggestions and refresh display
        if (batch && batch.suggestions && batch.suggestions.length > 0) {
            // Add timestamp to new suggestions if not present
            batch.suggestions.forEach(suggestion => {
                if (!suggestion.created_at) {
                    suggestion.created_at = batch.generated_at || new Date().toISOString();
                }
            });
            
            // Determine suggestion type for appropriate toast message
            const suggestionType = batch.type || 'gumbo';
            const typeLabel = suggestionType === 'proactive' ? 'Immediate' : 'Pattern-based';
            
            this.showToast(`${typeLabel} suggestions received!`, 'success');
        }
        
        // Always reload the full suggestions view organized by time
        this.loadAllSuggestions();
    }

    /**
     * Handle proactive suggestions from SSE stream
     */
    displayProactiveSuggestions(data) {
        if (data && data.suggestions && data.suggestions.length > 0) {
            // Add metadata to proactive suggestions
            data.suggestions.forEach(suggestion => {
                suggestion.type = 'proactive';
                suggestion.category = suggestion.category || 'proactive';
                if (!suggestion.created_at) {
                    suggestion.created_at = data.generated_at || new Date().toISOString();
                }
            });
            
            this.showToast(`${data.suggestions.length} immediate suggestions received!`, 'success');
            
            // Reload suggestions to show new proactive ones
            this.loadAllSuggestions();
        }
    }

    /**
     * Clear all caches and reset the app state
     */
    clearAllCaches() {
        // Clear suggestions cache
        if (this.suggestionPolling) {
            this.suggestionPolling.suggestionsCache.clear();
        }
        
        // Clear any other caches
        if (this.timelineCache) {
            this.timelineCache.clear();
        }
        
        // Clear localStorage theme cache (keep theme setting)
        const theme = localStorage.getItem('gum-theme');
        localStorage.clear();
        if (theme) {
            localStorage.setItem('gum-theme', theme);
        }
        
        console.log('🧹 All caches cleared');
        this.showToast('All caches cleared!', 'success');
    }

    /**
     * Clear all suggestions from the database
     */
    async clearAllSuggestions() {
        // Show confirmation dialog
        const confirmed = confirm('Are you sure you want to clear all suggestions? This action cannot be undone.');
        if (!confirmed) {
            return;
        }

        try {
            // Show loading state
            const clearBtn = document.getElementById('clearSuggestionsBtn');
            if (clearBtn) {
                clearBtn.disabled = true;
                clearBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Clearing...';
            }

            // Call the clear suggestions API
            const response = await fetch(`${this.apiBaseUrl}/suggestions/clear`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                // Clear the UI
                const content = document.getElementById('suggestionsContent');
                if (content) {
                    content.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-lightbulb"></i>
                            <h3>No suggestions available</h3>
                            <p>Suggestions will appear here automatically based on your recent activity</p>
                        </div>
                    `;
                }

                // Clear the cache
                if (this.suggestionPolling) {
                    this.suggestionPolling.suggestionsCache.clear();
                }

                // Show success message
                this.showToast('✅ All suggestions cleared successfully!', 'success');
            } else {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Failed to clear suggestions');
            }
        } catch (error) {
            console.error('Error clearing suggestions:', error);
            this.showToast(`❌ Error clearing suggestions: ${error.message}`, 'error');
        } finally {
            // Reset button state
            const clearBtn = document.getElementById('clearSuggestionsBtn');
            if (clearBtn) {
                clearBtn.disabled = false;
                clearBtn.innerHTML = '<i class="fas fa-trash"></i> Clear All Suggestions';
            }
        }
    }

    /**
     * Load and display all suggestions organized by time periods
     */
    async loadAllSuggestions() {
        const content = document.getElementById('suggestionsContent');
        if (!content) return;

        try {
            // Load all historical suggestions
            const response = await fetch(`${this.apiBaseUrl}/suggestions/history?limit=100`);
            if (!response.ok) {
                throw new Error(`Failed to load suggestions: ${response.status}`);
            }
            
            const allSuggestions = await response.json();
            
            if (!allSuggestions || allSuggestions.length === 0) {
                content.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-lightbulb"></i>
                        <h3>No suggestions available</h3>
                        <p>Suggestions will appear here automatically based on your recent activity</p>
                    </div>
                `;
                return;
            }

            // Group suggestions by time periods
            const timeGroups = this.groupSuggestionsByTime(allSuggestions);
            
            // Display organized suggestions
            content.innerHTML = this.renderTimeGroupedSuggestions(timeGroups);
            
            // Store current suggestions for copy functionality
            this.currentSuggestions = allSuggestions;
            
        } catch (error) {
            console.error('Error loading suggestions:', error);
            content.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Unable to load suggestions</h3>
                    <p>Please check your connection and try again</p>
                </div>
            `;
        }
    }

    /**
     * Group suggestions by time periods (Today, Yesterday, This Week, etc.)
     */
    groupSuggestionsByTime(suggestions) {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
        const thisWeekStart = new Date(today.getTime() - (today.getDay() * 24 * 60 * 60 * 1000));
        const lastWeekStart = new Date(thisWeekStart.getTime() - (7 * 24 * 60 * 60 * 1000));

        const groups = {
            today: [],
            yesterday: [],
            thisWeek: [],
            lastWeek: [],
            older: []
        };

        suggestions.forEach(suggestion => {
            const suggestionDate = new Date(suggestion.created_at);
            const suggestionDay = new Date(suggestionDate.getFullYear(), suggestionDate.getMonth(), suggestionDate.getDate());

            if (suggestionDay.getTime() === today.getTime()) {
                groups.today.push(suggestion);
            } else if (suggestionDay.getTime() === yesterday.getTime()) {
                groups.yesterday.push(suggestion);
            } else if (suggestionDate >= thisWeekStart) {
                groups.thisWeek.push(suggestion);
            } else if (suggestionDate >= lastWeekStart) {
                groups.lastWeek.push(suggestion);
            } else {
                groups.older.push(suggestion);
            }
        });

        // Sort suggestions within each group by time (newest first)
        Object.keys(groups).forEach(key => {
            groups[key].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        });

        return groups;
    }

    /**
     * Render time-grouped suggestions with clean section headers
     */
    renderTimeGroupedSuggestions(timeGroups) {
        const sections = [];

        const sectionConfigs = [
            { key: 'today', title: 'Today', icon: 'fas fa-sun' },
            { key: 'yesterday', title: 'Yesterday', icon: 'fas fa-moon' },
            { key: 'thisWeek', title: 'This Week', icon: 'fas fa-calendar-week' },
            { key: 'lastWeek', title: 'Last Week', icon: 'fas fa-calendar' },
            { key: 'older', title: 'Older', icon: 'fas fa-archive' }
        ];

        sectionConfigs.forEach(config => {
            const suggestions = timeGroups[config.key];
            if (suggestions && suggestions.length > 0) {
                // Group suggestions by type within each time period
                const proactiveSuggestions = suggestions.filter(s => s.type === 'proactive' || s.category === 'proactive');
                const gumboSuggestions = suggestions.filter(s => s.type !== 'proactive' && s.category !== 'proactive');
                
                let sectionContent = '';
                
                // Add proactive suggestions first (more immediate)
                if (proactiveSuggestions.length > 0) {
                    sectionContent += `
                        <div class="suggestion-type-group proactive-group">
                            <div class="suggestion-type-header">
                                <i class="fas fa-bolt"></i>
                                <span>Immediate Suggestions</span>
                                <span class="type-count">${proactiveSuggestions.length}</span>
                            </div>
                            ${proactiveSuggestions.map((suggestion, index) => this.renderSuggestionCard(suggestion, index, 'proactive')).join('')}
                        </div>
                    `;
                }
                
                // Add Gumbo suggestions second (behavioral patterns)
                if (gumboSuggestions.length > 0) {
                    sectionContent += `
                        <div class="suggestion-type-group gumbo-group">
                            <div class="suggestion-type-header">
                                <i class="fas fa-brain"></i>
                                <span>Pattern-Based Suggestions</span>
                                <span class="type-count">${gumboSuggestions.length}</span>
                            </div>
                            ${gumboSuggestions.map((suggestion, index) => this.renderSuggestionCard(suggestion, index, 'gumbo')).join('')}
                        </div>
                    `;
                }
                
                sections.push(`
                    <div class="suggestions-time-section">
                        <div class="suggestions-time-header">
                            <i class="${config.icon}"></i>
                            ${config.title}
                            <span class="suggestions-count">${suggestions.length}</span>
                        </div>
                        <div class="suggestions-list">
                            ${sectionContent}
                        </div>
                    </div>
                `);
            }
        });

        return sections.join('');
    }

    /**
     * Render individual suggestion card
     */
    renderSuggestionCard(suggestion, index, type = 'gumbo') {
        const isProactive = type === 'proactive' || suggestion.type === 'proactive' || suggestion.category === 'proactive';
        const cardClass = isProactive ? 'suggestion-card proactive-suggestion' : 'suggestion-card gumbo-suggestion';
        const typeIcon = isProactive ? 'fas fa-bolt' : 'fas fa-brain';
        const typeLabel = isProactive ? 'Immediate' : 'Pattern-Based';
        
        return `
            <div class="${cardClass}" data-suggestion-index="${index}" data-suggestion-type="${type}">
                <div class="suggestion-header">
                    <h4 class="suggestion-title">${this.escapeHtml(suggestion.title)}</h4>
                    <div class="suggestion-meta">
                        <span class="type-indicator ${isProactive ? 'proactive-indicator' : 'gumbo-indicator'}">
                            <i class="${typeIcon}"></i>
                            ${typeLabel}
                        </span>
                        <span class="category-badge" data-category="${suggestion.category}">
                            ${this.escapeHtml(suggestion.category || 'General')}
                        </span>
                        <span class="time-badge">
                            ${this.getTimeAgo(new Date(suggestion.created_at))}
                        </span>
                    </div>
                </div>
                <div class="suggestion-description">
                    ${this.escapeHtml(suggestion.description)}
                </div>
                ${suggestion.rationale ? `
                    <div class="suggestion-reasoning">
                        <details>
                            <summary>Click to see reasoning</summary>
                            <div class="reasoning-content">
                                ${this.escapeHtml(suggestion.rationale)}
                            </div>
                        </details>
                    </div>
                ` : ''}
                <div class="suggestion-actions">
                    <button class="action-btn" onclick="window.zavionApp.copySuggestion(${index})">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                    ${isProactive ? `
                        <span class="suggestion-timing">
                            <i class="fas fa-clock"></i>
                            Actionable now
                        </span>
                    ` : `
                        <span class="suggestion-timing">
                            <i class="fas fa-chart-line"></i>
                            Based on patterns
                        </span>
                    `}
                </div>
            </div>
        `;
    }

    // Helper methods for suggestion actions
    copySuggestion(index) {
        if (!this.currentSuggestions || !this.currentSuggestions[index]) return;
        
        const suggestion = this.currentSuggestions[index];
        const text = `${suggestion.title}\n\n${suggestion.description}\n\nRationale: ${suggestion.rationale}`;
        
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Suggestion copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy suggestion:', err);
            this.showToast('Failed to copy suggestion', 'error');
        });
    }



    displaySuggestions(suggestionsData) {
        const content = document.getElementById('suggestionsContent');
        
        if (!suggestionsData.suggestions || suggestionsData.suggestions.length === 0) {
            content.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-lightbulb"></i>
                    <h3>No suggestions available</h3>
                    <p>No actionable suggestions found based on your recent activity. Try increasing the time range or continue using the system to generate more data.</p>
                </div>
            `;
            return;
        }

        // Group suggestions by urgency/time
        const suggestionsByTime = {
            'now': [],
            'today': [],
            'this_week': []
        };

        suggestionsData.suggestions.forEach(suggestion => {
            const urgency = suggestion.urgency || 'today';
            if (suggestionsByTime[urgency]) {
                suggestionsByTime[urgency].push(suggestion);
            } else {
                suggestionsByTime['today'].push(suggestion);
            }
        });

        let suggestionsHtml = '';

        // Create sections for each time group
        if (suggestionsByTime.now.length > 0) {
            suggestionsHtml += this.createSuggestionsTimeSection('Now', suggestionsByTime.now);
        }
        
        if (suggestionsByTime.today.length > 0) {
            suggestionsHtml += this.createSuggestionsTimeSection('Today', suggestionsByTime.today);
        }
        
        if (suggestionsByTime.this_week.length > 0) {
            suggestionsHtml += this.createSuggestionsTimeSection('This Week', suggestionsByTime.this_week);
        }

        content.innerHTML = suggestionsHtml;
        

        
        this.showToast('Suggestions generated successfully!', 'success');
    }

    createSuggestionsTimeSection(timeLabel, suggestions) {
        let sectionHtml = `
            <div class="suggestions-time-section">
                <h3 class="suggestions-time-header">${timeLabel}</h3>
                <div class="suggestions-grid">
        `;

        suggestions.forEach((suggestion, index) => {
            // Clean the description for safe HTML insertion
            const cleanDescription = suggestion.description.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
            const suggestionJson = JSON.stringify(suggestion).replace(/"/g, '&quot;');
            
            sectionHtml += `
                <div class="suggestion-card" data-suggestion-id="${index}">
                    <h4 class="suggestion-title">${suggestion.title}</h4>
                    
                    <div class="suggestion-description">
                        ${suggestion.description}
                </div>
                    

            </div>
        `;
        });

        sectionHtml += `
                </div>
            </div>
        `;

        return sectionHtml;
    }






    

    

    

    

    

    

    

    

    


    getTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInSeconds = Math.floor((now - time) / 1000);
        
        if (diffInSeconds < 60) return 'Just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} min ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hr ago`;
        return `${Math.floor(diffInSeconds / 86400)} days ago`;
    }

    // Dashboard functionality
    startTracking() {
        // This will start the CLI tracking via Electron
        if (window.electronAPI && window.electronAPI.startCliTracking) {
            window.electronAPI.startCliTracking();
            this.updateTrackingStatus('Starting...');
        } else {
            console.log('Electron API not available');
        }
    }

    updateTrackingStatus(status) {
        const statusElement = document.getElementById('tracking-status');
        if (statusElement) {
            statusElement.textContent = status;
        }
    }

    updateDataStatus(status) {
        const dataElement = document.getElementById('data-status');
        if (dataElement) {
            dataElement.textContent = status;
        }
    }

    async loadDashboardData() {
        try {
            // Update insights count
            const countResponse = await fetch(`${this.apiBaseUrl}/propositions/count`);
            if (countResponse.ok) {
                const countData = await countResponse.json();
                this.updateDashboardInsightsCount(countData.count);
            }

            // Load recent insights preview
            const recentResponse = await fetch(`${this.apiBaseUrl}/propositions?limit=3&sort_by=created_at`);
            if (recentResponse.ok) {
                const recentData = await recentResponse.json();
                this.updateDashboardRecentInsights(recentData.propositions || []);
            }

            // Update last activity time
            if (recentData && recentData.propositions && recentData.propositions.length > 0) {
                const lastInsight = recentData.propositions[0];
                this.updateDashboardLastActivity(lastInsight.created_at);
            }

            // Check tracking status
            if (window.electronAPI && window.electronAPI.getCliStatus) {
                const status = await window.electronAPI.getCliStatus();
                this.updateTrackingStatus(status.isRunning ? 'Active' : 'Stopped');
            }

            // Check data status
            const response = await fetch(`${this.apiBaseUrl}/propositions/count`);
            if (response.ok) {
                const data = await response.json();
                this.updateDataStatus(`${data.count} insights generated`);
            } else {
                this.updateDataStatus('No data yet');
            }

            // Load recent activity
            this.loadRecentActivity();
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.updateTrackingStatus('Error');
            this.updateDataStatus('Error loading data');
            this.updateDashboardError();
        }
    }

    updateDashboardInsightsCount(count) {
        const countElement = document.getElementById('total-insights');
        if (countElement) {
            countElement.textContent = count;
        }
    }

    updateDashboardLastActivity(timestamp) {
        const activityElement = document.getElementById('last-activity');
        if (activityElement && timestamp) {
            const date = new Date(timestamp);
            const timeAgo = this.getTimeAgo(date);
            activityElement.textContent = timeAgo;
        }
    }

    updateDashboardRecentInsights(insights) {
        const previewContainer = document.getElementById('recent-insights-preview');
        if (!previewContainer) return;

        if (insights.length === 0) {
            previewContainer.innerHTML = `
                <div class="timeline-proposition-card">
                    <div class="proposition-text" style="text-align: center; color: var(--text-muted);">
                        No insights generated yet. Start using the app to see insights here!
                    </div>
                </div>
            `;
            return;
        }

        const insightsHTML = insights.slice(0, 3).map(insight => {
            const confidence = insight.confidence || 0;
            const confidenceClass = confidence >= 80 ? 'confidence-high' : confidence >= 60 ? 'confidence-medium' : confidence >= 40 ? 'confidence-low' : 'confidence-none';
            const timeLabel = insight.created_at ? this.formatLocalTime(insight.created_at) : 'Unknown time';
            
            return `
                <div class="timeline-proposition-card" onclick="window.zavionApp?.switchTab('memory')">
                    <div class="timeline-proposition-header">
                        <span class="timeline-proposition-time">${timeLabel}</span>
                        <span class="confidence-badge ${confidenceClass}">
                            <i class="fas fa-chart-line"></i>
                            ${confidence}% confidence
                        </span>
                    </div>
                    <div class="timeline-proposition-content">
                        <div class="proposition-id">#${insight.id}</div>
                        <div class="proposition-text">${this.escapeHtml(insight.text.substring(0, 120))}${insight.text.length > 120 ? '...' : ''}</div>
                        <span class="click-hint">Click to view all insights</span>
                    </div>
                </div>
            `;
        }).join('');

        previewContainer.innerHTML = insightsHTML;
    }

    updateDashboardError() {
        const countElement = document.getElementById('total-insights');
        const activityElement = document.getElementById('last-activity');
        const previewContainer = document.getElementById('recent-insights-preview');
        
        if (countElement) countElement.textContent = 'Error';
        if (activityElement) activityElement.textContent = 'Error';
        if (previewContainer) {
            previewContainer.innerHTML = `
                <div class="timeline-proposition-card">
                    <div class="proposition-text" style="text-align: center; color: var(--error-color);">
                        Error loading insights. Please check your connection.
                    </div>
                </div>
            `;
        }
    }

    getTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    }

    async loadRecentActivity() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/propositions?limit=3&sort_by=created_at`);
            if (response.ok) {
                const data = await response.json();
                this.displayRecentActivity(data.propositions || []);
            } else {
                this.displayRecentActivity([]);
            }
        } catch (error) {
            console.error('Error loading recent activity:', error);
            this.displayRecentActivity([]);
        }
    }

    displayRecentActivity(propositions) {
        const activityPreview = document.getElementById('activity-preview');
        if (!activityPreview) return;

        if (propositions.length === 0) {
            activityPreview.innerHTML = '<p class="loading-text">No insights generated yet. Start tracking to see your first insights!</p>';
            return;
        }

        const activityHTML = propositions.map(prop => `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas fa-lightbulb"></i>
                </div>
                <div class="activity-content">
                    <p class="activity-text">${prop.text.substring(0, 100)}${prop.text.length > 100 ? '...' : ''}</p>
                    <span class="activity-time">${new Date(prop.created_at).toLocaleDateString()}</span>
                </div>
            </div>
        `).join('');

        activityPreview.innerHTML = activityHTML;
    }

}



// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.zavionApp = new ZavionApp();
});

// Add CSS for results display dynamically
const additionalCSS = `
.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: var(--spacing-lg);
}

.result-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-lg);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
}

.result-card.full-width {
    grid-column: 1 / -1;
}

.result-header {
    background: linear-gradient(135deg, var(--primary-color), var(--primary-custom-tooltip-color));
    color: var(--text-white);
    padding: var(--spacing-lg);
}

.result-header h3 {
    margin: 0;
    font-size: var(--font-size-lg);
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.result-content {
    padding: var(--spacing-lg);
}

.summary-stats {
    display: grid;
    gap: var(--spacing-md);
}

.stat {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) 0;
    border-bottom: 1px solid var(--border-light);
}

.stat:last-child {
    border-bottom: none;
}

.stat-label {
    color: var(--text-secondary);
    font-weight: 500;
}

.stat-value {
    font-weight: 600;
    color: var(--text-primary);
}

.stat-value.success {
    color: var(--success-color);
}

.insights-list, .patterns-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
}

.insight-item, .pattern-item {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm);
    background: var(--bg-secondary);
    border-radius: var(--border-radius);
}

.insight-icon {
    color: var(--primary-color);
    font-size: var(--font-size-lg);
    flex-shrink: 0;
}

.insight-text {
    flex: 1;
    color: var(--text-primary);
}

.pattern-name {
    font-weight: 600;
    color: var(--text-primary);
}

.pattern-confidence {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
}

.analysis-details {
    background: var(--bg-secondary);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius);
    padding: var(--spacing-lg);
    font-family: var(--font-family-mono);
    font-size: var(--font-size-sm);
    color: var(--text-primary);
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
    max-height: 400px;
    overflow-y: auto;
}

.history-item {
    background: var(--bg-secondary);
    border: 1px solid var(--border-light);
    border-radius: var(--border-radius);
    padding: var(--spacing-lg);
    margin-bottom: var(--spacing-md);
}

.history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-sm);
}

.history-title {
    font-weight: 600;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.history-date {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
}

.history-details {
    display: flex;
    gap: var(--spacing-lg);
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin-bottom: var(--spacing-sm);
}

.history-content {
    font-size: var(--font-size-sm);
    color: var(--text-primary);
    line-height: 1.4;
}

.no-data {
    text-align: center;
    color: var(--text-muted);
    font-style: italic;
    padding: var(--spacing-xl);
}

@media (max-width: 768px) {
    .results-grid {
        grid-template-columns: 1fr;
    }
    
    .history-header {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-sm);
    }
    
    .history-details {
        flex-direction: column;
        gap: var(--spacing-sm);
    }
}
`;

// Inject additional CSS
const style = document.createElement('style');
style.textContent = additionalCSS;
document.head.appendChild(style);


