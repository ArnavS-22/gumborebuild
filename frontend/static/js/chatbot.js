/**
 * Enhanced Chatbot Manager - Beautiful AI Interface with GUM Integration
 * 
 * Features:
 * - Context-aware AI responses with GUM data
 * - Beautiful UI with animations and toggles
 * - File upload simulation
 * - Category-based suggestions
 * - Toggle options (Search, Deep Research, Reason)
 * - Smooth animations and transitions
 */

class ChatbotManager {
    constructor() {
        this.messages = [];
        this.isTyping = false;
        this.apiBaseUrl = window.ZAVION_CONFIG?.apiBaseUrl || 'http://localhost:8000';
        this.conversationId = this.generateConversationId();
        
        // DOM elements
        this.messagesContainer = null;
        this.welcomeBackground = null;
        this.chatInput = null;
        this.sendButton = null;
        this.suggestionsContainer = null;
        this.suggestionsList = null;
        this.suggestionsHeader = null;
        this.categories = null;
        this.chipsWrap = null;
        this.uploadBtn = null;
        this.uploadIcon = null;
        this.uploadText = null;
        
        // Toggle buttons
        this.btnSearch = null;
        this.btnDeep = null;
        this.btnReason = null;
        this.micBtn = null;
        
        // State
        this.isInitialized = false;
        this.suggestions = [];
        this.uploadedFiles = [];
        this.uploading = false;
        this.activeCategory = null;
        
        // Toggle states
        this.state = {
            search: false,
            deep: false,
            reason: false
        };
        
        // Category suggestions
        this.categorySuggestions = {
            learn: [
                "Explain the Big Bang theory",
                "How does photosynthesis work?",
                "What are black holes?",
                "Explain quantum computing",
                "How does the human brain work?"
            ],
            code: [
                "Create a React component for a todo list",
                "Write a Python function to sort a list",
                "How to implement authentication in Next.js",
                "Explain async/await in JavaScript",
                "Create a CSS animation for a button"
            ],
            write: [
                "Write a professional email to a client",
                "Create a product description for a smartphone",
                "Draft a blog post about AI",
                "Write a creative story about space exploration",
                "Create a social media post about sustainability"
            ]
        };
        
        this.init();
    }
    
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeElements());
        } else {
            this.initializeElements();
        }
    }
    
    initializeElements() {
        try {
            // Get DOM elements
            this.messagesContainer = document.getElementById('chatbot-messages');
            this.welcomeBackground = this.messagesContainer?.querySelector('.welcome-background');
            this.chatInput = document.getElementById('chatbot-input');
            this.sendButton = document.getElementById('chatbot-send');
            this.suggestionsContainer = document.getElementById('suggestionsContainer');
            this.suggestionsList = document.getElementById('suggestionsList');
            this.suggestionsHeader = document.getElementById('suggestionsHeader');
            this.categories = document.getElementById('categories');
            this.chipsWrap = document.getElementById('chips');
            this.uploadBtn = document.getElementById('uploadBtn');
            this.uploadIcon = document.getElementById('uploadIcon');
            this.uploadText = document.getElementById('uploadText');
            
            // Toggle buttons
            this.btnSearch = document.getElementById('btnSearch');
            this.btnDeep = document.getElementById('btnDeep');
            this.btnReason = document.getElementById('btnReason');
            this.micBtn = document.getElementById('micBtn');
            
            if (!this.messagesContainer || !this.chatInput || !this.sendButton) {
                console.warn('Chatbot elements not found, retrying in 1 second...');
                setTimeout(() => this.initializeElements(), 1000);
                return;
            }
            
            this.setupEventListeners();
            this.loadSuggestions();
            this.isInitialized = true;
            
            console.log('Enhanced chatbot manager initialized successfully');
            
        } catch (error) {
            console.error('Error initializing chatbot elements:', error);
        }
    }
    
    setupEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.handleSendMessage());
        
        // Enter key in input (with Shift+Enter for new line)
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });
        
        // Auto-resize textarea
        this.chatInput.addEventListener('input', () => this.updateSendButton());
        
        // Toggle buttons
        if (this.btnSearch) {
            this.btnSearch.addEventListener('click', () => this.toggleOption('search', this.btnSearch));
        }
        if (this.btnDeep) {
            this.btnDeep.addEventListener('click', () => this.toggleOption('deep', this.btnDeep));
        }
        if (this.btnReason) {
            this.btnReason.addEventListener('click', () => this.toggleOption('reason', this.btnReason));
        }
        
        // Upload button
        if (this.uploadBtn) {
            this.uploadBtn.addEventListener('click', () => this.handleUpload());
        }
        
        // Categories
        if (this.categories) {
            this.categories.addEventListener('click', (e) => {
                const btn = e.target.closest('.cat-btn');
                if (!btn) return;
                const cat = btn.dataset.cat;
                this.setActiveCategory(cat);
            });
        }
        
        // Click outside to close suggestions
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.categories') && !e.target.closest('#suggestionsContainer')) {
                this.collapseSuggestions();
            }
        });
    }
    
    async handleSendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isTyping) {
            return;
        }
        
        try {
            // Clear input and disable send button
            this.chatInput.value = '';
            this.updateSendButton();
            this.setSendButtonState(false);
            
            // Add user message to UI
            this.addMessage(message, true);
            
            // Show typing indicator
            this.showTypingIndicator();
            
            // Send message to API with toggle states
            const response = await this.sendMessageToAPI(message);
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            // Add AI response to UI
            if (response && response.message) {
                this.addMessage(response.message.content, false);
                
                // Update suggestions
                if (response.suggestions && response.suggestions.length > 0) {
                    this.updateSuggestions(response.suggestions);
                }
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.addMessage('Sorry, I encountered an error processing your message. Please try again.', false);
        } finally {
            this.setSendButtonState(true);
        }
    }
    
    async sendMessageToAPI(message) {
        const requestData = {
            message: message,
            user_name: "Arnav Sharma",
            conversation_id: this.conversationId,
            include_context: true,
            context_hours_back: 24,
            max_context_items: 10
        };
        
        // Add toggle states to request if needed
        if (this.state.deep) {
            requestData.deep_research = true;
        }
        if (this.state.reason) {
            requestData.reasoning_mode = true;
        }
        if (this.state.search) {
            requestData.search_mode = true;
        }
        
        const response = await fetch(`${this.apiBaseUrl}/chat/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    addMessage(content, isUser = false) {
        // Hide welcome background when first message is added
        if (this.welcomeBackground && this.messages.length === 0) {
            this.welcomeBackground.classList.add('hidden');
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user' : 'assistant'}`;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content-text';
        contentDiv.textContent = content;
        
        bubbleDiv.appendChild(contentDiv);
        messageDiv.appendChild(bubbleDiv);
        this.messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        this.scrollToBottom();
        
        // Store message
        this.messages.push({
            content,
            isUser,
            timestamp: new Date().toISOString()
        });
    }
    
    showTypingIndicator() {
        this.isTyping = true;
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message assistant';
        typingDiv.id = 'typing-indicator';
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        bubbleDiv.innerHTML = '<div class="message-content-text"><span class="shining-text">AI is thinking...</span></div>';
        
        typingDiv.appendChild(bubbleDiv);
        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.isTyping = false;
        const typingDiv = document.getElementById('typing-indicator');
        if (typingDiv) {
            typingDiv.remove();
        }
    }
    
    updateSendButton() {
        const nonEmpty = this.chatInput.value.trim().length > 0;
        if (nonEmpty) {
            this.sendButton.classList.remove('disabled');
            this.sendButton.classList.add('ready');
            this.sendButton.disabled = false;
        } else {
            this.sendButton.classList.add('disabled');
            this.sendButton.classList.remove('ready');
            this.sendButton.disabled = true;
        }
    }
    
    setSendButtonState(enabled) {
        if (this.sendButton) {
            this.sendButton.disabled = !enabled;
            if (enabled) {
                this.updateSendButton();
            } else {
                this.sendButton.classList.add('disabled');
                this.sendButton.classList.remove('ready');
            }
        }
    }
    
    scrollToBottom() {
        if (this.messagesContainer) {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }
    
    // Toggle functionality
    toggleOption(key, btnEl) {
        this.state[key] = !this.state[key];
        btnEl.classList.toggle('active', this.state[key]);
        console.log(`${key} toggled:`, this.state[key]);
    }
    
    // Upload functionality
    handleUpload() {
        if (this.uploading) return;
        this.uploading = true;
        this.renderUploadAnimation(true);
        
        // Simulate upload
        setTimeout(() => {
            const name = `Document-${this.uploadedFiles.length + 1}.pdf`;
            this.uploadedFiles.push(name);
            this.uploading = false;
            this.renderUploadAnimation(false);
            this.renderChips();
        }, 1400);
    }
    
    renderUploadAnimation(on) {
        if (on) {
            this.uploadIcon.innerHTML = '<span class="dots" aria-hidden="true"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span>';
            this.uploadText.textContent = 'Uploading...';
        } else {
            this.uploadIcon.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 3v12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M5 12l7-9 7 9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
            this.uploadText.textContent = 'Upload Files';
        }
    }
    
    renderChips() {
        if (this.uploadedFiles.length === 0) {
            this.chipsWrap.classList.add('hidden');
            this.chipsWrap.innerHTML = '';
            return;
        }
        this.chipsWrap.classList.remove('hidden');
        this.chipsWrap.innerHTML = '';
        this.uploadedFiles.forEach((f, i) => {
            const div = document.createElement('div');
            div.className = 'chip';
            div.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M14 2v6h6" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>${f}</span>
            `;
            const btn = document.createElement('button');
            btn.innerHTML = '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" aria-hidden="true"><path d="M6 6l12 12M6 18L18 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
            btn.addEventListener('click', () => {
                this.uploadedFiles.splice(i, 1);
                this.renderChips();
            });
            div.appendChild(btn);
            this.chipsWrap.appendChild(div);
        });
    }
    
    // Category suggestions
    setActiveCategory(cat) {
        if (this.activeCategory === cat) {
            // Close
            this.activeCategory = null;
            this.collapseSuggestions();
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            return;
        }
        this.activeCategory = cat;
        this.renderSuggestions(cat);
        this.expandSuggestions();
        // Mark category button active
        document.querySelectorAll('.cat-btn').forEach(b => b.classList.toggle('active', b.dataset.cat === cat));
    }
    
    renderSuggestions(cat) {
        this.suggestionsHeader.textContent = cat === 'learn' ? 'Learning suggestions' : 
                                           cat === 'code' ? 'Coding suggestions' : 'Writing suggestions';
        this.suggestionsList.innerHTML = '';
        this.categorySuggestions[cat].forEach((s, i) => {
            const li = document.createElement('li');
            li.setAttribute('role', 'button');
            li.innerHTML = `
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" aria-hidden="true">
                    <path d="${cat === 'learn' ? 'M4 19h16M4 5h16M8 7v10' : 
                              cat === 'code' ? 'M16 18l6-6-6-6M8 6L2 12l6 6' : 
                              'M16.5 3.5L21 8l-9 9H7v-4L16.5 3.5z'}" 
                          stroke="#2563eb" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span style="color:#111827">${s}</span>
            `;
            li.addEventListener('click', () => {
                this.chatInput.value = s;
                this.updateSendButton();
                this.setActiveCategory(null);
                this.collapseSuggestions();
                this.chatInput.focus();
            });
            this.suggestionsList.appendChild(li);
        });
    }
    
    expandSuggestions() {
        requestAnimationFrame(() => {
            this.suggestionsContainer.style.opacity = '1';
            this.suggestionsContainer.style.height = this.suggestionsContainer.scrollHeight + 'px';
        });
    }
    
    collapseSuggestions() {
        this.suggestionsContainer.style.height = this.suggestionsContainer.scrollHeight + 'px';
        requestAnimationFrame(() => {
            this.suggestionsContainer.style.height = '0px';
            this.suggestionsContainer.style.opacity = '0';
        });
        document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
        this.activeCategory = null;
    }
    
    async loadSuggestions() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/chat/suggestions?user_name=Arnav Sharma`);
            if (response.ok) {
                const suggestions = await response.json();
                this.updateSuggestions(suggestions.map(s => s.text));
            }
        } catch (error) {
            console.error('Error loading suggestions:', error);
        }
    }
    
    updateSuggestions(suggestions) {
        this.suggestions = suggestions;
    }
    
    generateConversationId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    // Public API methods
    sendMessage(message) {
        if (this.chatInput) {
            this.chatInput.value = message;
            this.updateSendButton();
            this.handleSendMessage();
        }
    }
    
    isReady() {
        return this.isInitialized;
    }
    
    getMessages() {
        return this.messages;
    }
}

// Initialize chatbot manager when DOM is ready
let chatbotManager = null;

function initializeChatbot() {
    if (!chatbotManager) {
        chatbotManager = new ChatbotManager();
        
        // Make it available globally for debugging
        window.chatbotManager = chatbotManager;
    }
    return chatbotManager;
}

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeChatbot);
} else {
    initializeChatbot();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChatbotManager;
}
