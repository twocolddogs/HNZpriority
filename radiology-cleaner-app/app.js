// --- STATUS MANAGER CLASS ---
class StatusManager {
    constructor() {
        this.container = null;
        this.activeMessages = new Map();
        this.progressMessage = null;
        this.stageMessage = null;
        this.statsMessage = null;
        this.messageCounter = 0;
        
        // Message type configuration
        this.typeConfig = {
            info: {
                background: 'var(--color-info-light, #e3f2fd)',
                border: '1px solid var(--color-info, #2196f3)',
                color: 'var(--color-info, #2196f3)',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
            },
            success: {
                background: 'var(--color-success-light, #e8f5e9)',
                border: '1px solid var(--color-success, #4caf50)',
                color: 'var(--color-success, #4caf50)',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
            },
            warning: {
                background: 'var(--color-warning-light, #fff8e1)',
                border: '1px solid var(--color-warning, #ff9800)',
                color: 'var(--color-warning, #ff9800)',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
            },
            error: {
                background: 'var(--color-danger-light, #ffebee)',
                border: '1px solid var(--color-danger, #f44336)',
                color: 'var(--color-danger, #f44336)',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'
            },
            network: {
                background: 'var(--color-primary-light, #e8eaf6)',
                border: '1px solid var(--color-primary, #3f51b5)',
                color: 'var(--color-primary, #3f51b5)',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>'
            },
            progress: {
                background: 'var(--color-primary-light, #e8eaf6)',
                border: '1px solid var(--color-primary, #3f51b5)',
                color: 'var(--color-primary, #3f51b5)',
                icon: '<div class="spinner"></div>'
            }
        };
        
        // Ensure CSS animations are added
        this.injectStyles();
    }
    
    // Initialize the container for status messages
    ensureContainer() {
        if (!this.container) {
            this.container = document.getElementById('statusMessageContainer');
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.id = 'statusMessageContainer';
                this.container.className = 'status-message-container';
                
                // Insert after progress bar
                const progressBar = document.getElementById('progressBar');
                if (progressBar && progressBar.parentNode) {
                    progressBar.parentNode.insertBefore(this.container, progressBar.nextSibling);
                } else {
                    // Fallback: insert at the top of the page
                    document.body.insertBefore(this.container, document.body.firstChild);
                }
            }
        }
        return this.container;
    }
    
    // Clear all status messages
    clearAll() {
        const container = this.ensureContainer();
        container.innerHTML = '';
        this.activeMessages.clear();
        this.progressMessage = null;
        this.stageMessage = null;
        this.statsMessage = null;
    }
    
    // Show a status message with type (info, success, warning, error, network, progress)
    show(message, type = 'info', autoHideDuration = 0, id = null) {
        const container = this.ensureContainer();
        const style = this.typeConfig[type] || this.typeConfig.info;
        const messageId = id || `status-${++this.messageCounter}`;
        
        // Create message element
        const messageElement = document.createElement('div');
        messageElement.id = messageId;
        messageElement.className = `status-message status-${type}`;
        messageElement.style.cssText = `
            padding: 12px 16px;
            background: ${style.background};
            border: ${style.border};
            border-radius: 6px;
            font-size: 14px;
            color: var(--color-gray-800, #333);
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 12px;
            animation: statusFadeIn 0.3s ease-out;
            position: relative;
        `;
        
        // Create icon element
        const iconElement = document.createElement('div');
        iconElement.className = 'status-icon';
        iconElement.innerHTML = style.icon;
        iconElement.style.cssText = `
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: ${style.color};
        `;
        
        // Create message text element
        const textElement = document.createElement('div');
        textElement.className = 'status-text';
        textElement.innerHTML = message;
        textElement.style.cssText = `
            flex-grow: 1;
        `;
        
        // Add close button for non-auto-hiding messages
        if (autoHideDuration === 0) {
            const closeButton = document.createElement('button');
            closeButton.className = 'status-close';
            closeButton.innerHTML = '&times;';
            closeButton.style.cssText = `
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                padding: 0;
                line-height: 1;
                color: var(--color-gray-600, #666);
                opacity: 0.7;
                transition: opacity 0.2s;
            `;
            closeButton.addEventListener('mouseenter', () => {
                closeButton.style.opacity = '1';
            });
            closeButton.addEventListener('mouseleave', () => {
                closeButton.style.opacity = '0.7';
            });
            closeButton.addEventListener('click', () => {
                this.remove(messageId);
            });
            messageElement.appendChild(closeButton);
        }
        
        // Assemble the message
        messageElement.appendChild(iconElement);
        messageElement.appendChild(textElement);
        
        // Add to container
        container.appendChild(messageElement);
        
        // Store reference to the message
        this.activeMessages.set(messageId, messageElement);
        
        // Auto-hide if duration is set
        if (autoHideDuration > 0) {
            setTimeout(() => {
                this.remove(messageId);
            }, autoHideDuration);
        }
        
        return messageId;
    }
    
    // Update an existing status message
    update(id, message) {
        const messageElement = this.activeMessages.get(id);
        if (!messageElement) {
            return this.show(message, 'info');
        }
        
        // Update the message text
        const textElement = messageElement.querySelector('.status-text');
        if (textElement) {
            textElement.innerHTML = message;
        }
        
        return id;
    }
    
    // Remove a status message with animation
    remove(id) {
        const messageElement = this.activeMessages.get(id);
        if (!messageElement) return;
        
        messageElement.style.animation = 'statusFadeOut 0.3s ease-out forwards';
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.parentNode.removeChild(messageElement);
            }
            this.activeMessages.delete(id);
        }, 300);
    }
    
    // Show a progress status message with details
    showProgress(message, current, total, type = 'progress') {
        // Calculate percentage
        const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
        
        // Create or update progress message
        if (!this.progressMessage) {
            // Create new progress status
            const id = this.show(
                `${message} <div class="status-progress-text">${current}/${total} (${percentage}%)</div>`, 
                type
            );
            
            const messageElement = this.activeMessages.get(id);
            
            // Add progress bar
            const progressElement = document.createElement('div');
            progressElement.className = 'status-progress-bar';
            progressElement.style.cssText = `
                width: 100%;
                height: 4px;
                background: var(--color-gray-200, #eee);
                border-radius: 2px;
                margin-top: 8px;
                overflow: hidden;
            `;
            
            const progressFill = document.createElement('div');
            progressFill.className = 'status-progress-fill';
            progressFill.style.cssText = `
                height: 100%;
                background: var(--color-${type === 'progress' ? 'primary' : type}, #3f51b5);
                width: ${percentage}%;
                transition: width 0.3s ease;
            `;
            
            progressElement.appendChild(progressFill);
            messageElement.querySelector('.status-text').appendChild(progressElement);
            
            this.progressMessage = id;
        } else {
            // Update existing progress status
            const messageElement = this.activeMessages.get(this.progressMessage);
            if (!messageElement) {
                // If message was removed, create a new one
                this.progressMessage = null;
                return this.showProgress(message, current, total, type);
            }
            
            // Update progress text
            const progressText = messageElement.querySelector('.status-progress-text');
            if (progressText) {
                progressText.textContent = `${current}/${total} (${percentage}%)`;
            }
            
            // Update progress bar fill
            const progressFill = messageElement.querySelector('.status-progress-fill');
            if (progressFill) {
                progressFill.style.width = `${percentage}%`;
            }
            
            // Update message text (keeping the progress text)
            const textElement = messageElement.querySelector('.status-text');
            if (textElement) {
                // Replace text content but keep the progress elements
                const progressElements = textElement.querySelectorAll('.status-progress-text, .status-progress-bar');
                textElement.innerHTML = message;
                progressElements.forEach(el => textElement.appendChild(el));
            }
        }
        
        return this.progressMessage;
    }
    
    // Show processing stage with animation
    showStage(stage, description) {
        const stageMessage = `
            <div class="processing-stage">
                <div class="stage-name">${stage}</div>
                <div class="stage-description">${description}</div>
            </div>
        `;
        
        if (!this.stageMessage) {
            this.stageMessage = this.show(stageMessage, 'progress');
        } else {
            this.update(this.stageMessage, stageMessage);
        }
        
        return this.stageMessage;
    }
    
    // Show processing statistics
    showStats(stats) {
        const {
            elapsedTime,
            processedItems,
            totalItems,
            cacheHits,
            errors,
            itemsPerSecond
        } = stats;
        
        const formattedTime = this.formatTime(elapsedTime);
        const cacheHitRate = totalItems > 0 ? 
            Math.round((cacheHits / totalItems) * 100) : 0;
        
        const statsMessage = `
            <div class="processing-stats">
                <div class="stats-row">
                    <div class="stats-label">Elapsed Time:</div>
                    <div class="stats-value">${formattedTime}</div>
                </div>
                <div class="stats-row">
                    <div class="stats-label">Processing Rate:</div>
                    <div class="stats-value">${itemsPerSecond} items/sec</div>
                </div>
                <div class="stats-row">
                    <div class="stats-label">Cache Hit Rate:</div>
                    <div class="stats-value">${cacheHitRate}%</div>
                </div>
                <div class="stats-row">
                    <div class="stats-label">Errors:</div>
                    <div class="stats-value">${errors}</div>
                </div>
            </div>
        `;
        
        if (!this.statsMessage) {
            this.statsMessage = this.show(statsMessage, 'info');
        } else {
            this.update(this.statsMessage, statsMessage);
        }
        
        return this.statsMessage;
    }
    
    // Format time in ms to a human-readable format
    formatTime(ms) {
        if (ms < 1000) return `${ms}ms`;
        
        const seconds = Math.floor(ms / 1000);
        if (seconds < 60) return `${seconds}s`;
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
        
        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;
        return `${hours}h ${remainingMinutes}m ${remainingSeconds}s`;
    }
    
    // Format file size in bytes to a human-readable format
    formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${Math.round(bytes / Math.pow(1024, i) * 100) / 100} ${sizes[i]}`;
    }
    
    // Format percentage with specified precision
    formatPercentage(value, total, precision = 1) {
        if (total === 0) return '0%';
        return `${(value / total * 100).toFixed(precision)}%`;
    }
    
    // Inject required CSS styles for animations
    injectStyles() {
        const styleId = 'status-manager-styles';
        if (document.getElementById(styleId)) return;
        
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .spinner {
                width: 16px;
                height: 16px;
                border: 2px solid var(--color-primary, #3f51b5);
                border-radius: 50%;
                border-top-color: transparent;
                animation: spin 1s linear infinite;
            }
            @keyframes statusFadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes statusFadeOut {
                from { opacity: 1; transform: translateY(0); }
                to { opacity: 0; transform: translateY(-10px); }
            }
            .status-message-container {
                display: flex;
                flex-direction: column;
                gap: 8px;
                margin: 16px 0;
            }
            .processing-stage {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .stage-name {
                font-weight: 600;
                font-size: 15px;
            }
            .stage-description {
                font-size: 13px;
                opacity: 0.9;
            }
            .processing-stats {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            .stats-row {
                display: flex;
                justify-content: space-between;
                font-size: 13px;
            }
            .stats-label {
                font-weight: 500;
                color: var(--color-gray-600, #666);
            }
            .stats-value {
                font-weight: 600;
                color: var(--color-gray-800, #333);
            }
            .current-exam {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .exam-label {
                font-size: 12px;
                color: var(--color-gray-600, #666);
                font-weight: 500;
            }
            .exam-value {
                font-weight: 600;
                font-family: var(--font-family-mono, monospace);
                font-size: 14px;
            }
            .exam-result {
                font-size: 13px;
                color: var(--color-success, #4caf50);
                font-weight: 500;
                margin-top: 2px;
            }
            .exam-error {
                font-size: 13px;
                color: var(--color-danger, #f44336);
                font-weight: 500;
                margin-top: 2px;
            }
            .current-exam.error .exam-value {
                color: var(--color-danger, #f44336);
            }
            .processing-complete {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .complete-icon {
                font-size: 20px;
                font-weight: bold;
                color: var(--color-success, #4caf50);
                background: var(--color-success-light, #e8f5e9);
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .complete-message {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .complete-title {
                font-weight: 600;
                font-size: 15px;
            }
            .complete-details {
                font-size: 13px;
                color: var(--color-gray-600, #666);
                display: flex;
                gap: 12px;
            }
        `;
        
        document.head.appendChild(style);
    }
}

// Initialize the status manager
const statusManager = new StatusManager();

// Utility functions for formatting
function formatProcessingTime(ms) {
    return statusManager.formatTime(ms);
}

function formatFileSize(bytes) {
    return statusManager.formatFileSize(bytes);
}

function formatPercentage(value, total, precision = 1) {
    return statusManager.formatPercentage(value, total, precision);
}

window.addEventListener('DOMContentLoaded', function() {
    // --- DYNAMIC API CONFIGURATION ---
    function detectApiUrls() {
        const hostname = window.location.hostname;
        const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
        const isProduction = hostname === 'hnzradtools.nz';
        const isStaging = hostname === 'develop.hnzradtools.nz';
        const isCloudflarePages = hostname.includes('pages.dev');
        
        const apiConfigs = {
            local: { base: 'http://localhost:10000', mode: 'LOCAL DEVELOPMENT' },
            staging: { base: '/api', mode: 'STAGING (Proxied)' },
            production: { base: '/api', mode: 'PRODUCTION (Proxied)' },
            fallback: { base: 'https://radiology-api-staging.onrender.com', mode: 'STAGING (Direct)' }
        };
        
        // Batch processing configuration - matches backend NLP_BATCH_SIZE
        // To configure batch size: set window.ENV.NLP_BATCH_SIZE or backend env var NLP_BATCH_SIZE
        const getBatchSize = () => {
            // Check for environment variable (in production this could be set via build-time env vars)
            if (typeof window !== 'undefined' && window.ENV && window.ENV.NLP_BATCH_SIZE) {
                return parseInt(window.ENV.NLP_BATCH_SIZE);
            }
            // Default batch size (same as backend default)
            return 1000;
        };

        // --- UTILITY FUNCTIONS (defined early to avoid hoisting issues) ---
        function preventDefaults(e) { 
            e.preventDefault(); 
            e.stopPropagation();
        }

        // --- MODEL TOGGLE FUNCTIONS ---
        function switchModel(modelKey) {
            console.log(`🔄 switchModel called with modelKey: ${modelKey}`);
            
            // Validate model exists and is available
            if (!availableModels[modelKey] || availableModels[modelKey].status !== 'available') {
                console.warn(`Model ${modelKey} is not available. Status:`, availableModels[modelKey]?.status);
                return;
            }
            
            console.log(`✓ Switching to model: ${modelKey}`);
            
            // Update global state
            currentModel = modelKey;
            
            // Update UI - toggle active states
            document.querySelectorAll('.model-toggle').forEach(btn => btn.classList.remove('active'));
            
            // Activate selected model button
            const selectedButton = document.getElementById(`${modelKey}ModelBtn`);
            if (selectedButton) {
                selectedButton.classList.add('active');
            }
            
            // Show feedback message
            const displayName = formatModelName(modelKey);
            statusManager.show(`Switched to ${displayName} model`, 'success', 3000);
        }
        
        let config;
        if (isLocalhost) config = apiConfigs.local;
        else if (isProduction) config = apiConfigs.production;
        else if (isStaging) config = apiConfigs.staging;
        else if (isCloudflarePages) config = apiConfigs.fallback; // Use direct API for Cloudflare Pages
        else config = apiConfigs.fallback;
        
        // CORRECTED: Construct the final URLs without adding an extra '/api'.
        // The base already contains '/api' when running on Render.
        return {
            API_URL: `${config.base}/parse_enhanced`,
            BATCH_API_URL: `${config.base}/parse_batch`,
            HEALTH_URL: `${config.base}/health`,
            SANITY_TEST_URL: `${config.base}/process_sanity_test`,
            mode: config.mode,
            baseUrl: config.base
        };
    }
    
    const apiConfig = detectApiUrls();
    const API_URL = apiConfig.API_URL;
    const BATCH_API_URL = apiConfig.BATCH_API_URL;
    const MODELS_URL = `${apiConfig.baseUrl}/models`;
    
    console.log(`Frontend running in ${apiConfig.mode} mode`);
    console.log(`API base URL: ${apiConfig.baseUrl}`);
    console.log(`Models URL: ${MODELS_URL}`);
    
    // ------------------------------------------------------------------
    //  UNIVERSAL FETCH WITH TIMEOUT & RETRY (💡 used for all network IO)
    // ------------------------------------------------------------------
    /**
     * Perform a fetch with automatic timeout and retry-on-failure.
     * @param {string} url – request URL
     * @param {object} options – fetch options (method, headers, body …)
     * @param {number} maxRetries – how many times to retry (default 3)
     * @param {number} timeoutMs – per-attempt timeout in ms (default 10000)
     */
    async function fetchWithRetry(url, options = {}, maxRetries = 3, timeoutMs = 10000) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            const controller = new AbortController();
            const id = setTimeout(() => controller.abort(), timeoutMs);
            try {
                // Show network activity in status system for long operations
                if (timeoutMs > 5000) {
                    statusManager.show(`Connecting to server (attempt ${attempt}/${maxRetries})...`, 'network');
                }
                
                const res = await fetch(url, { ...options, signal: controller.signal });
                clearTimeout(id);
                // Treat non-2xx as failure but still return the response
                if (!res.ok) {
                    if (attempt === maxRetries) {
                        if (timeoutMs > 5000) {
                            statusManager.show(`Server returned error: ${res.status} ${res.statusText}`, 'error');
                        }
                        return res; // let caller decide
                    }
                    console.warn(`Fetch ${url} failed (status ${res.status}), retrying ${attempt}/${maxRetries}…`);
                    statusManager.show(`Request failed (${res.status}), retrying...`, 'warning');
                } else {
                    if (timeoutMs > 5000) {
                        statusManager.show(`Connected to server successfully`, 'success', 1500);
                    }
                    return res;
                }
            } catch (err) {
                clearTimeout(id);
                if (attempt === maxRetries || err.name === 'AbortError') {
                    if (err.name === 'AbortError') {
                        statusManager.show(`Request timed out after ${timeoutMs/1000}s`, 'error');
                    } else {
                        statusManager.show(`Connection error: ${err.message}`, 'error');
                    }
                    throw err;
                }
                console.warn(`Fetch ${url} error '${err}', retrying ${attempt}/${maxRetries}…`);
                statusManager.show(`Connection error, retrying (${attempt}/${maxRetries})...`, 'warning');
            }
            // exponential backoff: 0.5s,1s,2s…
            await new Promise(r => setTimeout(r, 500 * Math.pow(2, attempt - 1)));
        }
    }

    async function testApiConnectivity() {
        try {
            statusManager.show('Testing API connectivity...', 'network');
            const response = await fetchWithRetry(apiConfig.HEALTH_URL, { method: 'GET' }, 2, 5000);
            if (response.ok) {
                console.log('✓ API connectivity test passed');
                statusManager.show('API connection successful', 'success', 2000);
            } else {
                console.warn('⚠ API health check failed:', response.status);
                statusManager.show(`API health check failed: ${response.status}`, 'warning');
            }
        } catch (error) {
            console.error('✗ API connectivity test failed:', error);
            statusManager.show('API connection failed - check your network', 'error');
        }
    }
    testApiConnectivity();
    
    // --- DYNAMIC MODEL INITIALIZATION ---
    async function loadAvailableModels() {
        try {
            console.log('🔍 Fetching available models from backend...');
            statusManager.show('Loading AI models...', 'network');
            const response = await fetchWithRetry(MODELS_URL, { method: 'GET' }, 2, 8000);
            if (response.ok) {
                const modelsData = await response.json();
                availableModels = modelsData.models || {};
                currentModel = modelsData.default_model || 'default';
                
                console.log('✓ Available models loaded:', Object.keys(availableModels));
                statusManager.show(`${Object.keys(availableModels).length} AI models loaded`, 'success', 2000);
                buildModelSelectionUI();
            } else {
                console.warn('⚠ Models API unavailable, using fallback models');
                statusManager.show('Could not load models from server, using fallbacks', 'warning');
                useFallbackModels();
            }
        } catch (error) {
            console.error('✗ Failed to load models:', error);
            statusManager.show('Failed to load AI models, using fallbacks', 'error');
            useFallbackModels();
        }
    }
    
    function useFallbackModels() {
        // Fallback models aligned with backend nlp_processor.py (without biolord)
        availableModels = {
            'default': {
                name: 'BioLORD (Default)',
                status: 'available',
                description: 'BioLORD - Advanced biomedical language model (default)'
            },
            'experimental': {
                name: 'MedCPT (Experimental)',
                status: 'available',
                description: 'NCBI Medical Clinical Practice Text encoder (experimental)'
            }
        };
        currentModel = 'default';
        buildModelSelectionUI();
    }
    
    function buildModelSelectionUI() {
        console.log('🔧 Building model selection UI...');
        console.log('Available models:', availableModels);
        
        const modelContainer = document.querySelector('.model-selection-container');
        if (!modelContainer) {
            console.error('❌ Model selection container not found in HTML');
            return;
        }
        
        console.log('✓ Found model container:', modelContainer);
        
        // Clear existing buttons
        modelContainer.innerHTML = '';
        
        // Create model selection buttons dynamically
        console.log(`🔄 Creating ${Object.keys(availableModels).length} model buttons...`);
        
        Object.entries(availableModels).forEach(([modelKey, modelInfo]) => {
            console.log(`Creating button for ${modelKey}:`, modelInfo);
            
            // Create a wrapper div for button + description layout
            const modelWrapper = document.createElement('div');
            modelWrapper.className = 'model-wrapper';
            modelWrapper.style.cssText = 'display: flex; align-items: center; gap: 15px; margin-bottom: 10px;';
            
            const button = document.createElement('button');
            button.className = `button secondary model-toggle ${modelKey === currentModel ? 'active' : ''}`;
            button.id = `${modelKey}ModelBtn`;
            button.dataset.model = modelKey;
            button.style.cssText = 'min-width: 150px; flex-shrink: 0;';
            
            // Remove emoji status icons, just use text
            const statusText = modelInfo.status === 'available' ? '' : ' (Unavailable)';
            const statusClass = modelInfo.status === 'available' ? 'available' : 'unavailable';
            
            button.innerHTML = `
                <span class="model-name">${formatModelName(modelKey)}${statusText}</span>
            `;
            
            // Create description element
            const description = document.createElement('span');
            description.className = 'model-description';
            description.style.cssText = 'font-size: 0.85em; color: #666; flex: 1;';
            description.textContent = modelInfo.description || '';
            
            // Set disabled state for unavailable models
            if (modelInfo.status !== 'available') {
                button.disabled = true;
                button.title = `${modelInfo.name} is currently unavailable`;
                description.style.color = '#999';
            } else {
                button.addEventListener('click', () => {
                    console.log(`🖱️ Model button clicked: ${modelKey}`);
                    switchModel(modelKey);
                });
            }
            
            modelWrapper.appendChild(button);
            modelWrapper.appendChild(description);
            modelContainer.appendChild(modelWrapper);
            console.log(`✓ Added ${modelKey} button with description to container`);
        });
        
        console.log(`✅ Model UI built with ${modelContainer.children.length} buttons`);
    }
    
    function formatModelName(modelKey) {
        // Use dynamic model names from the API if available
        if (availableModels && availableModels[modelKey] && availableModels[modelKey].name) {
            return availableModels[modelKey].name;
        }
        
        // Fallback to static mapping if API data not available
        const nameMap = {
            'default': 'BioLORD (Default)',
            'pubmed': 'PubMed',
            'biolord': 'BioLORD',
            'general': 'General',
            'experimental': 'Experimental'
        };
        return nameMap[modelKey] || modelKey.charAt(0).toUpperCase() + modelKey.slice(1);
    }
    
    
    // Initialize models on page load
    loadAvailableModels();

    // --- STATE ---
    let allMappings = [];
    let summaryData = null;
    let currentModel = 'default'; // Initialize the current model
    let availableModels = {}; // Store available models from API
    let processingState = {
        isProcessing: false,
        currentStage: '',
        totalItems: 0,
        processedItems: 0,
        startTime: 0,
        cacheHits: 0,
        errors: 0
    };

    // --- DOM ELEMENTS ---
    const uploadSection = document.getElementById('uploadSection');
    const demosSection = document.getElementById('demosSection');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');
    const resultsSection = document.getElementById('resultsSection');
    const resultsBody = document.getElementById('resultsBody');

    // --- EVENT LISTENERS ---
    uploadSection.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => e.target.files[0] && processFile(e.target.files[0]));
    ['dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadSection.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    ['dragenter', 'dragover'].forEach(eventName => uploadSection.addEventListener(eventName, () => uploadSection.classList.add('dragover'), false));
    ['dragleave', 'drop'].forEach(eventName => uploadSection.addEventListener(eventName, () => uploadSection.classList.remove('dragover'), false));
    uploadSection.addEventListener('drop', (e) => e.dataTransfer.files[0] && processFile(e.dataTransfer.files[0]), false);

    document.getElementById('newUploadBtn').addEventListener('click', startNewUpload);
    document.getElementById('exportMappingsBtn').addEventListener('click', exportResults);
    
    // Sanity test button with debug verification
    const sanityButton = document.getElementById('sanityTestBtn');
    if (sanityButton) {
        console.log('✓ Sanity test button found, attaching event listener');
        sanityButton.addEventListener('click', runSanityTest);
        sanityButton.addEventListener('click', () => console.log('Sanity test button clicked event fired'));
    } else {
        console.error('❌ Sanity test button not found!');
    }
    
    document.getElementById('closeModalBtn').addEventListener('click', closeModal);
    document.getElementById('consolidationModal').addEventListener('click', (e) => e.target.id === 'consolidationModal' && closeModal());
    
    // View toggle event listeners
    document.getElementById('fullViewBtn').addEventListener('click', showFullView);
    document.getElementById('consolidatedViewBtn').addEventListener('click', showConsolidatedView);
    document.getElementById('consolidatedSearch').addEventListener('input', filterConsolidatedResults);
    document.getElementById('consolidatedSort').addEventListener('change', sortConsolidatedResults);
    
    // Model toggle event listeners - now handled dynamically in buildModelSelectionUI()
    
    // Help button event listener
    document.getElementById('hamburgerToggle').addEventListener('click', () => {
        document.getElementById('hamburgerDropdown').classList.toggle('hidden');
    });

    // Close hamburger menu when clicking outside
    document.addEventListener('click', (event) => {
        const hamburgerMenu = document.getElementById('hamburgerDropdown');
        const hamburgerToggle = document.getElementById('hamburgerToggle');
        
        if (hamburgerMenu && hamburgerToggle) {
            // Check if the click was outside both the toggle button and the dropdown menu
            if (!hamburgerToggle.contains(event.target) && !hamburgerMenu.contains(event.target)) {
                hamburgerMenu.classList.add('hidden');
            }
        }
    });
    
    // Prevent hamburger dropdown from closing when clicking inside it
    const hamburgerDropdown = document.getElementById('hamburgerDropdown');
    if (hamburgerDropdown) {
        hamburgerDropdown.addEventListener('click', (event) => {
            event.stopPropagation();
        });
    }

    // Help and Architecture button event listeners with debug verification
    const helpButton = document.getElementById('helpButton');
    const architectureButton = document.getElementById('architectureButton');
    
    if (helpButton) {
        console.log('✓ Help button found, attaching event listener');
        helpButton.addEventListener('click', (e) => {
            e.stopPropagation();
            showHelpModal();
        });
    } else {
        console.error('❌ Help button not found!');
    }
    
    if (architectureButton) {
        console.log('✓ Architecture button found, attaching event listener');
        architectureButton.addEventListener('click', (e) => {
            e.stopPropagation();
            showArchitectureModal();
        });
    } else {
        console.error('❌ Architecture button not found!');
    }
    // Modal close button event listeners with error checking
    const closeHelpModal1 = document.getElementById('closeHelpModal');
    const closeHelpBtn = document.getElementById('closeHelpBtn');
    const closeArchitectureModal1 = document.getElementById('closeArchitectureModal');
    const closeArchitectureBtn = document.getElementById('closeArchitectureBtn');
    
    if (closeHelpModal1) closeHelpModal1.addEventListener('click', closeHelpModal);
    if (closeHelpBtn) closeHelpBtn.addEventListener('click', closeHelpModal);
    if (closeArchitectureModal1) closeArchitectureModal1.addEventListener('click', closeArchitectureModal);
    if (closeArchitectureBtn) closeArchitectureBtn.addEventListener('click', closeArchitectureModal);
    
    // Modal click-outside to close functionality with error checking
    const helpModal = document.getElementById('helpModal');
    const architectureModal = document.getElementById('architectureModal');
    
    if (helpModal) {
        helpModal.addEventListener('click', (e) => {
            if (e.target.id === 'helpModal') closeHelpModal();
        });
    }
    
    if (architectureModal) {
        architectureModal.addEventListener('click', (e) => {
            if (e.target.id === 'architectureModal') closeArchitectureModal();
        });
    }
    
    function showHelpModal() {
        
        // Populate modal with system architecture content
        const helpContent = document.getElementById('helpContent');
        helpContent.innerHTML = `
            <h2>Radiology Code Semantic Cleaner</h2>
            <p><strong>What it does:</strong> This application transforms messy, inconsistent radiology exam names from different hospital systems into standardized, clinically meaningful names with structured components.</p>
            
            <h3>How to Use This App</h3>
            
            <div style="background: var(--color-gray-50); padding: 1rem; border-radius: var(--radius-base); margin: 1rem 0;">
                <h4>Step 1: Prepare Your Data</h4>
                <p>Create a JSON file with your radiology exam data. Each exam record needs:</p>
                <ul>
                    <li><code>EXAM_NAME</code> - The exam description (e.g., "CT CHEST C+")</li>
                    <li><code>MODALITY_CODE</code> - Imaging type (CT, MR, XR, US, etc.)</li>
                    <li><code>DATA_SOURCE</code> - Hospital/system identifier</li>
                    <li><code>EXAM_CODE</code> - Internal exam code</li>
                </ul>
                <p><strong>Example:</strong> <code>{"EXAM_NAME": "CT CHEST C+", "MODALITY_CODE": "CT", "DATA_SOURCE": "HospitalA", "EXAM_CODE": "Q18"}</code></p>
            </div>

            <div style="background: var(--color-info-light); padding: 1rem; border-radius: var(--radius-base); margin: 1rem 0;">
                <h4>Step 2: Upload & Process</h4>
                <p>• <strong>Upload File:</strong> Click the upload area or drag your JSON file</p>
                <p>• <strong>Run Sanity Test:</strong> Use the test button to try with sample data</p>
                <p>• <strong>Automatic Processing:</strong> The app sends your data to AI processing engines</p>
            </div>

            <h3>What Happens During Processing</h3>
            
            <div style="background: var(--color-primary-light); padding: 1rem; border-radius: var(--radius-base); margin: 1rem 0;">
                <h4>1. Intelligent Parsing</h4>
                <p>The AI analyzes each exam name and extracts:</p>
                <ul>
                    <li><strong>Anatomy:</strong> Body parts (chest, abdomen, knee, etc.)</li>
                    <li><strong>Laterality:</strong> Left, right, or bilateral</li>
                    <li><strong>Contrast:</strong> With/without contrast agent</li>
                    <li><strong>Technique:</strong> Special imaging techniques</li>
                    <li><strong>Gender Context:</strong> Male, female, or pregnancy-related</li>
                    <li><strong>Clinical Context:</strong> Emergency, screening, follow-up, etc.</li>
                </ul>
            </div>

            <div style="background: var(--color-success-light); padding: 1rem; border-radius: var(--radius-base); margin: 1rem 0;">
                <h4>2. Standardization</h4>
                <p>• <strong>Clean Name Generation:</strong> Creates consistent exam names</p>
                <p>• <strong>SNOMED Mapping:</strong> Links to medical terminology standards</p>
                <p>• <strong>Confidence Scoring:</strong> Shows how certain the AI is about each result</p>
                <p>• <strong>Component Validation:</strong> Ensures all extracted parts make clinical sense</p>
            </div>

            <h3>Understanding Your Results</h3>
            
            <p><strong>Full View:</strong> See every individual exam with its clean name, components, and confidence score</p>
            <p><strong>Consolidated View:</strong> Groups identical clean names together to show consolidation patterns</p>
            
            <h4>📈 Key Metrics</h4>
            <ul>
                <li><strong>Consolidation Ratio:</strong> How many original names were simplified (e.g., 500 → 200 = 2.5:1)</li>
                <li><strong>Confidence:</strong> AI certainty level (Green: >80%, Yellow: 60-80%, Red: <60%)</li>
                <li><strong>Gender Context:</strong> Number of exams with gender-specific components</li>
                <li><strong>Processing Stats:</strong> Speed, cache hits, and success rates</li>
            </ul>

            <h3>Export Options</h3>
            <p>• <strong>Export Mappings:</strong> Download cleaned data as JSON for your systems</p>
            <p>• <strong>Full Results:</strong> Complete dataset with all components and confidence scores</p>
            <p>• <strong>Analytics:</strong> Summary reports showing consolidation patterns</p>

            <h3>🎯 Example Transformation</h3>
            <div style="background: var(--color-warning-light); padding: 1rem; border-radius: var(--radius-base); margin: 1rem 0; font-family: monospace;">
                <p><strong>Input:</strong> "CT CHEST C+", "CTCHEST", "Chest CT w/contrast"</p>
                <p><strong>↓ AI Processing ↓</strong></p>
                <p><strong>Output:</strong> "CT Chest with Contrast"</p>
                <p><strong>Components:</strong> Anatomy: [chest], Contrast: [with], Confidence: 95%</p>
            </div>

            <div style="margin-top: 2rem; padding: 1rem; background: var(--color-gray-100); border-radius: var(--radius-base); border-left: 4px solid var(--color-primary);">
                <p><strong>💡 Pro Tip:</strong> Start with the sanity test to see how the system works, then upload your own data. The AI learns from medical patterns and gets better results with more context.</p>
            </div>
        `;
        
        // Show modal
        document.getElementById('helpModal').classList.remove('hidden');
    }
    
    function closeHelpModal() {
        document.getElementById('helpModal').classList.add('hidden');
    }
    
    function showArchitectureModal() {
        // Close hamburger menu
        document.getElementById('hamburgerDropdown').classList.add('hidden');
        
        // Populate modal with system architecture content
        document.getElementById('architectureContent').innerHTML = getSystemArchitectureContent();
        
        // Show modal
        document.getElementById('architectureModal').classList.remove('hidden');
    }
    
    function closeArchitectureModal() {
        document.getElementById('architectureModal').classList.add('hidden');
    }
    
    function getSystemArchitectureContent() {
        return `
            <h1>Radiology Cleaner Application - System Architecture</h1>
            
            <h2>1. Overview</h2>
            <p>The Radiology Cleaner application is a web-based tool designed to standardize and process radiology exam names. It leverages a Flask backend for API services, a Python-based natural language processing (NLP) engine for semantic parsing, and a simple HTML/JavaScript frontend for user interaction. The system aims to provide clean, standardized exam names, SNOMED codes, and extracted clinical components (anatomy, laterality, contrast, etc.) for improved data quality and interoperability.</p>
            
            <h2>2. Architecture Overview</h2>
            <p>The system follows a modern web application architecture with the following key components:</p>
            <ul>
                <li><strong>Frontend</strong>: HTML/CSS/JavaScript interface for user interaction</li>
                <li><strong>Backend API</strong>: Flask application with REST endpoints</li>
                <li><strong>NLP Engine</strong>: Semantic parsing and text processing</li>
                <li><strong>NHS Lookup</strong>: Standardization against NHS reference data</li>
                <li><strong>Database</strong>: SQLite for performance metrics and feedback</li>
                <li><strong>Cache System</strong>: In-memory caching with dynamic versioning</li>
            </ul>
            
            <h2>3. Core Components</h2>
            
            <h3>3.1. Frontend</h3>
            <ul>
                <li><strong>index.html</strong>: Main entry point providing HTML structure</li>
                <li><strong>app.js</strong>: JavaScript logic for UI interaction and API communication</li>
                <li><strong>unified-styles.css</strong>: Professional healthcare-focused styling</li>
            </ul>
            
            <h3>3.2. Backend Services</h3>
            <ul>
                <li><strong>RadiologySemanticParser</strong>: Core rule-based semantic parsing
                    <ul>
                        <li>Modality detection (XR, CT, MRI, XA, Fluoroscopy, DEXA)</li>
                        <li>Technique classification (Angiography, Interventional, Barium Study)</li>
                        <li>Component extraction (anatomy, laterality, contrast)</li>
                    </ul>
                </li>
                <li><strong>NLPProcessor</strong>: Multi-model NLP support
                    <ul>
                        <li>PubMed embeddings (medical terminology optimized)</li>
                        <li>BioLORD-2023 (advanced biomedical language model)</li>
                        <li>General-purpose models for broad understanding</li>
                    </ul>
                </li>
                <li><strong>NHSLookupEngine</strong>: NHS reference data standardization
                    <ul>
                        <li>Unified preprocessing pipeline</li>
                        <li>Dynamic cache invalidation</li>
                        <li>Dual lookup strategy (Clean Name + SNOMED FSN)</li>
                        <li>Interventional procedure weighting</li>
                    </ul>
                </li>
            </ul>
            
            <h2>4. Recent Improvements (2024)</h2>
            
            <h3>4.1. Enhanced Medical Accuracy</h3>
            <ul>
                <li><strong>Mammography Reclassification</strong>: Correctly classified as XR modality (technique) rather than separate modality</li>
                <li><strong>Barium Studies</strong>: All barium procedures classified as Fluoroscopy modality</li>
                <li><strong>XA Modality Support</strong>: X-Ray Angiography for interventional procedures</li>
                <li><strong>DEXA Integration</strong>: Bone densitometry studies with dedicated patterns</li>
            </ul>
            
            <h3>4.2. NHS Interventional Procedure Accuracy</h3>
            <ul>
                <li>Redefined based on NHS credentialing requirements</li>
                <li>Specialist procedures in interventional labs (typically XA modality)</li>
                <li>Distinguishes from general interventions (PICC lines, biopsies)</li>
            </ul>
            
            <h3>4.3. Multi-Model NLP Support</h3>
            <ul>
                <li><strong>BioLORD Integration</strong>: FremyCompany/BioLORD-2023 for enhanced medical terminology</li>
                <li><strong>Model Selection API</strong>: Users can specify model via request parameters</li>
                <li><strong>Model Discovery</strong>: <code>/models</code> endpoint lists available models with status</li>
            </ul>
            
            <h2>5. API Endpoints</h2>
            <ul>
                <li><code>/health</code>: Basic health check</li>
                <li><code>/models</code>: Lists available NLP models with status and descriptions</li>
                <li><code>/parse_enhanced</code>: Enhanced parsing with model selection support</li>
                <li><code>/parse_batch</code>: Optimized batch processing</li>
                <li><code>/validate</code>: Quality validation and scoring</li>
                <li><code>/feedback</code>: User feedback submission</li>
            </ul>
            
            <h2>6. Data Flow</h2>
            <ol>
                <li><strong>Input Processing</strong>: User uploads exam data or uses sanity test</li>
                <li><strong>Preprocessing</strong>: Abbreviation expansion and normalization</li>
                <li><strong>Semantic Parsing</strong>: Component extraction using rule-based methods</li>
                <li><strong>NLP Enhancement</strong>: Semantic embeddings for similarity matching</li>
                <li><strong>NHS Standardization</strong>: Match against NHS reference data</li>
                <li><strong>SNOMED Mapping</strong>: Medical coding standards integration</li>
                <li><strong>Output Generation</strong>: Structured results with confidence scores</li>
            </ol>
            
            <h2>7. Key Technologies</h2>
            <ul>
                <li><strong>Frontend</strong>: HTML5, CSS3, ES6+ JavaScript</li>
                <li><strong>Backend</strong>: Python 3.9+, Flask, Flask-CORS</li>
                <li><strong>NLP</strong>: Hugging Face Inference API, NumPy</li>
                <li><strong>Data Storage</strong>: SQLite, JSON, CSV</li>
                <li><strong>Concurrency</strong>: ThreadPoolExecutor for batch processing</li>
                <li><strong>Caching</strong>: Dynamic versioning with automatic invalidation</li>
            </ul>
            
            <h2>8. Deployment Considerations</h2>
            <ul>
                <li><strong>Environment Variables</strong>: HUGGING_FACE_TOKEN required for NLP functionality</li>
                <li><strong>Scalability</strong>: Batch processing and API-based NLP for performance</li>
                <li><strong>Monitoring</strong>: Performance metrics recorded for optimization</li>
                <li><strong>Graceful Shutdown</strong>: Ensures data integrity during restarts</li>
            </ul>
            
            <div style="margin-top: 2rem; padding: 1rem; background: var(--color-primary-light); border-radius: var(--radius-base); border-left: 4px solid var(--color-primary);">
                <p><strong>🏥 Healthcare Focus:</strong> This system is specifically designed for healthcare data processing with medical accuracy as the top priority. All improvements are validated against NHS reference standards.</p>
            </div>
        `;
    }

    // --- UPLOAD INTERFACE CONTROL ---
    function hideUploadInterface() {
        uploadSection.style.display = 'none';
        demosSection.style.display = 'none';
        document.getElementById('modelSettingsSection').style.display = 'none';
    }
    
    function showUploadInterface() {
        uploadSection.style.display = 'block';
        demosSection.style.display = 'block';
        document.getElementById('modelSettingsSection').style.display = 'block';
    }
    
    function startNewUpload() {
        // Reset UI to initial state
        showUploadInterface();
        resultsSection.style.display = 'none';
        fileInfo.style.display = 'none';
        progressBar.style.display = 'none';
        
        // Reset file input
        fileInput.value = '';
        
        // Clear global state
        allMappings = [];
        summaryData = null;
        processingState = {
            isProcessing: false,
            currentStage: '',
            totalItems: 0,
            processedItems: 0,
            startTime: 0,
            cacheHits: 0,
            errors: 0
        };
        
        // Clear any status messages
        statusManager.clearAll();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // --- CORE PROCESSING FUNCTIONS ---
    // Process files individually (for small files)
    async function processIndividually(codes) {
        // Initialize processing state
        processingState = {
            isProcessing: true,
            currentStage: 'Individual Processing',
            totalItems: codes.length,
            processedItems: 0,
            startTime: Date.now(),
            cacheHits: 0,
            errors: 0
        };
        
        // Show initial progress status
        statusManager.showProgress(
            `Processing ${codes.length} exam records individually...`,
            0, codes.length
        );
        
        for (let i = 0; i < codes.length; i++) {
            const code = codes[i];
            
            // Update progress every item
            processingState.processedItems = i + 1;
            statusManager.showProgress(
                `Processing exam records individually...`,
                i + 1, codes.length
            );
            
            // Show detailed status only every 10th exam to reduce verbosity
            if (i % 10 === 0 || i === codes.length - 1) {
                statusManager.show(
                    `Processing exam ${i + 1}/${codes.length}: ${code.EXAM_NAME}`,
                    'processing', 1000 // Auto-clear after 1 second
                );
            }
            
            try {
                // Process exam without verbose API stages (progress bar shows overall progress)
                
                const response = await fetchWithRetry(API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ exam_name: code.EXAM_NAME, modality_code: code.MODALITY_CODE, model: currentModel })
                }, 3, 15000); // 3 retries, 15 second timeout for individual processing
                
                if (!response.ok) throw new Error(`API returned status ${response.status}`);
                
                const parsed = await response.json();
                
                // Check for cache hit
                if (parsed.metadata && parsed.metadata.cache_hit) {
                    processingState.cacheHits++;
                }
                
                // Update exam status to show results
                statusManager.update(
                    examStatusId,
                    `<div class="current-exam">
                        <div class="exam-label">Processed:</div>
                        <div class="exam-value">${code.EXAM_NAME}</div>
                        <div class="exam-result">→ ${parsed.clean_name}</div>
                    </div>`
                );
                
                allMappings.push({
                    data_source: code.DATA_SOURCE,
                    modality_code: code.MODALITY_CODE,
                    exam_code: code.EXAM_CODE,
                    exam_name: code.EXAM_NAME,
                    clean_name: parsed.clean_name,
                    snomed: parsed.snomed || {},
                    components: { 
                        anatomy: parsed.components.anatomy, 
                        laterality: parsed.components.laterality, 
                        contrast: parsed.components.contrast, 
                        technique: parsed.components.technique,
                        gender_context: parsed.components.gender_context,
                        age_context: parsed.components.age_context,
                        clinical_context: parsed.components.clinical_context,
                        confidence: parsed.components.confidence,
                        clinical_equivalents: parsed.clinical_equivalents
                    }
                });
            } catch (error) {
                console.error(`Failed to parse code: ${code.EXAM_NAME}`, error);
                
                // Update exam status to show error
                statusManager.update(
                    examStatusId,
                    `<div class="current-exam error">
                        <div class="exam-label">Error:</div>
                        <div class="exam-value">${code.EXAM_NAME}</div>
                        <div class="exam-error">${error.message}</div>
                    </div>`
                );
                
                processingState.errors++;
                allMappings.push({ ...code, clean_name: 'ERROR - PARSING FAILED', components: {} });
            }
            
            // Update progress bar
            progressFill.style.width = `${((i + 1) / codes.length) * 100}%`;
            
            // Show processing stats every 10 items or at the end
            if (i % 10 === 0 || i === codes.length - 1) {
                const elapsedTime = Date.now() - processingState.startTime;
                const itemsPerSecond = processingState.processedItems > 0 ? 
                    Math.round((processingState.processedItems / (elapsedTime / 1000)) * 10) / 10 : 0;
                
                statusManager.showStats({
                    elapsedTime,
                    processedItems: processingState.processedItems,
                    totalItems: processingState.totalItems,
                    cacheHits: processingState.cacheHits,
                    errors: processingState.errors,
                    itemsPerSecond
                });
            }
        }
        
        // Processing complete - completion message shown by main calling function
        const elapsedTime = Date.now() - processingState.startTime;
        console.log(`Individual processing completed: ${allMappings.length} records in ${formatProcessingTime(elapsedTime)}`);
        
        processingState.isProcessing = false;
    }
    
    // Process files in batches (for large files)
    async function processBatch(codes) {
        console.log(`Using batch processing for ${codes.length} records...`);
        
        // Initialize processing state
        processingState = {
            isProcessing: true,
            currentStage: 'Batch Processing',
            totalItems: codes.length,
            processedItems: 0,
            startTime: Date.now(),
            cacheHits: 0,
            errors: 0
        };
        
        // Show initial processing stage
        statusManager.showStage('Preparation', `Preparing ${codes.length} exam records for batch processing`);
        
        try {
            // Transform codes to the expected format for batch API
            const exams = codes.map(code => ({
                exam_name: code.EXAM_NAME,
                modality_code: code.MODALITY_CODE,
                data_source: code.DATA_SOURCE,
                exam_code: code.EXAM_CODE
            }));
            
            // Set progress to 25% while sending batch request
            progressFill.style.width = '25%';
            
            // Show API call stage with animated indicator
            statusManager.showStage(
                'API Request', 
                `Sending ${codes.length} exam records to AI processing engine`
            );
            
            // Show detailed request information
            statusManager.show(
                `<div class="request-details">
                    <div class="request-row">
                        <div class="request-label">Endpoint:</div>
                        <div class="request-value">${BATCH_API_URL}</div>
                    </div>
                    <div class="request-row">
                        <div class="request-label">Model:</div>
                        <div class="request-value">${formatModelName(currentModel)}</div>
                    </div>
                    <div class="request-row">
                        <div class="request-label">Batch Size:</div>
                        <div class="request-value">${getBatchSize()} records per chunk</div>
                    </div>
                </div>`,
                'network'
            );
            
            const response = await fetchWithRetry(BATCH_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    exams: exams,
                    chunk_size: getBatchSize(), // Configurable batch size (matches backend NLP_BATCH_SIZE)
                    model: currentModel
                })
            }, 2, 30000); // 2 retries, 30 second timeout for batch processing
            
            if (!response.ok) {
                throw new Error(`Batch API returned status ${response.status}`);
            }
            
            // Set progress to 75% while processing response
            progressFill.style.width = '75%';
            
            // Show processing stage
            statusManager.showStage(
                'AI Processing', 
                `Processing exam names with ${formatModelName(currentModel)} biomedical language model`
            );
            
            // Show detailed processing steps
            // Show simple processing message instead of verbose step animation
            statusManager.show('Processing exams with AI engine...', 'progress', 2000);
            
            // Parse response
            let batchResult;
            try {
                batchResult = await response.json();
            } catch (parseError) {
                throw new Error(`Failed to parse response JSON: ${parseError.message}`);
            }
            
            // Show results stage
            statusManager.showStage('Processing Results', 'Organizing and analyzing processed data');
            
            // Validate response structure
            if (!batchResult || typeof batchResult !== 'object') {
                throw new Error('Invalid response format from batch API');
            }
            
            // Process batch results
            if (batchResult.results) {
                allMappings = batchResult.results.map(item => ({
                    data_source: item.input.data_source,
                    modality_code: item.input.modality_code,
                    exam_code: item.input.exam_code,
                    exam_name: item.input.exam_name,
                    clean_name: item.output.clean_name,
                    snomed: item.output.snomed || {},
                    components: { 
                        ...item.output.components,
                        clinical_equivalents: item.output.clinical_equivalents || []
                    }
                }));
                
                // Update processing state
                processingState.processedItems = allMappings.length;
            }
            
            // Handle any errors from batch processing
            if (batchResult.errors && batchResult.errors.length > 0) {
                console.error('Errors returned from batch processing:', batchResult.errors);
                
                // Show error summary
                statusManager.show(
                    `<div class="error-summary">
                        <div class="error-title">Processing Errors</div>
                        <div class="error-count">${batchResult.errors.length} exams failed</div>
                        <div class="error-list">
                            ${batchResult.errors.slice(0, 3).map(err => 
                                `<div class="error-item">
                                    <span class="error-exam">${err.original_exam.exam_name}</span>
                                    <span class="error-message">${err.error}</span>
                                </div>`
                            ).join('')}
                            ${batchResult.errors.length > 3 ? 
                                `<div class="error-more">...and ${batchResult.errors.length - 3} more errors</div>` : ''}
                        </div>
                    </div>`,
                    'warning'
                );
                
                // Add error mappings
                batchResult.errors.forEach(err => {
                    allMappings.push({
                        data_source: err.original_exam.data_source,
                        modality_code: err.original_exam.modality_code,
                        exam_code: err.original_exam.exam_code,
                        exam_name: err.original_exam.exam_name,
                        clean_name: `ERROR: ${err.error}`,
                        components: {}
                    });
                });
                
                // Update processing state
                processingState.errors = batchResult.errors.length;
            }
            
            // Log batch processing stats and update user
            if (batchResult.processing_stats) {
                const stats = batchResult.processing_stats;
                processingState.cacheHits = stats.cache_hits || 0;
                
                const hitRate = (stats.cache_hit_ratio * 100).toFixed(1);
                const formattedTime = formatProcessingTime(stats.processing_time_ms);
                
                // Show processing stats
                statusManager.show(
                    `<div class="batch-stats">
                        <div class="stats-row">
                            <div class="stats-label">Successful:</div>
                            <div class="stats-value">${stats.successful} exams</div>
                        </div>
                        <div class="stats-row">
                            <div class="stats-label">Cache Hits:</div>
                            <div class="stats-value">${stats.cache_hits} exams (${hitRate}%)</div>
                        </div>
                        <div class="stats-row">
                            <div class="stats-label">Processing Time:</div>
                            <div class="stats-value">${formattedTime}</div>
                        </div>
                        <div class="stats-row">
                            <div class="stats-label">Model Used:</div>
                            <div class="stats-value">${formatModelName(stats.model_used)}</div>
                        </div>
                    </div>`,
                    'info'
                );
                
                console.log(`Batch processing completed: ${stats.successful} successful, ${stats.errors} errors, ${stats.cache_hits} cache hits (${hitRate}% hit rate), ${formattedTime} total`);
            } else {
                // Stats not available, will show completion message at end of function
                console.log(`Batch processing completed: ${allMappings.length} records processed`);
            }
            
        } catch (error) {
            console.error('Batch processing failed:', error);
            console.error('API URL:', BATCH_API_URL);
            console.error('Request payload size:', codes.length, 'records');
            statusManager.show(
                `<div class="error-alert">
                    <div class="error-title">Batch Processing Failed</div>
                    <div class="error-message">${error.message}</div>
                    <div class="error-recovery">Falling back to individual processing...</div>
                    <div class="error-debug">Debug: ${codes.length} records, Model: ${formatModelName(currentModel)}</div>
                </div>`,
                'error'
            );
            
            // Fall back to individual processing if batch fails
            console.log('Falling back to individual processing...');
            await processIndividually(codes);
        }
        
        // Set progress to 100%
        progressFill.style.width = '100%';
        
        // Show completion message
        const elapsedTime = Date.now() - processingState.startTime;
        const formattedTime = formatProcessingTime(elapsedTime);
        
        statusManager.show(
            `<div class="processing-complete">
                <div class="complete-icon">✓</div>
                <div class="complete-message">
                    <div class="complete-title">Processing Complete</div>
                    <div class="complete-details">
                        <span>${allMappings.length} records processed</span>
                        <span>${processingState.errors} errors</span>
                        <span>${formattedTime} total time</span>
                    </div>
                </div>
            </div>`,
            'success'
        );
        
        processingState.isProcessing = false;
    }

    // --- CORE LOGIC ---
    async function processFile(file) {
        const validJsonTypes = ['application/json', 'text/json'];
        if (!file.name.toLowerCase().endsWith('.json') || !validJsonTypes.includes(file.type)) {
            statusManager.show('Please upload a valid JSON file (.json).', 'error');
            return;
        }

        // Prevent users from re-uploading while current run in progress
        if (progressBar.style.display === 'block') {
            statusManager.show('A file is already being processed. Please wait until it finishes.', 'warning');
            return;
        }

        // Hide upload interface during processing
        hideUploadInterface();
        
        // Show file info with enhanced details
        fileInfo.innerHTML = `
            <div class="file-details">
                <div class="file-icon">📄</div>
                <div class="file-info-content">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">
                        <span class="file-size">${formatFileSize(file.size)}</span>
                        <span class="file-type">JSON</span>
                        <span class="file-date">${new Date().toLocaleDateString()}</span>
                    </div>
                </div>
            </div>
        `;
        fileInfo.style.display = 'block';
        progressBar.style.display = 'block';
        progressFill.style.width = '0%';
        resultsSection.style.display = 'none';
        allMappings = [];
        summaryData = null;
        
        // Clear any existing status messages
        statusManager.clearAll();
        
        // Show loading message
        statusManager.show('Reading file...', 'progress');

        const reader = new FileReader();
        reader.onload = async function(e) {
            try {
                // Show parsing stage
                statusManager.showStage('File Parsing', 'Reading and validating JSON data');
                
                const codes = JSON.parse(e.target.result);
                if (!Array.isArray(codes) || codes.length === 0) {
                    statusManager.show('JSON file is empty or not in the correct array format.', 'error');
                    progressBar.style.display = 'none';
                    showUploadInterface();
                    return;
                }

                console.log(`Processing ${codes.length} exam records...`);
                statusManager.show(`
                    <div class="file-loaded">
                        <div class="loaded-icon">✓</div>
                        <div class="loaded-message">
                            <div class="loaded-title">File Loaded Successfully</div>
                            <div class="loaded-details">${codes.length} exam records found in ${file.name}</div>
                        </div>
                    </div>
                `, 'success', 800);
                
                // Process the data
                await processBatch(codes);
                
                // Run analysis and show results
                statusManager.showStage('Analysis', 'Analyzing results and generating visualizations');
                runAnalysis(allMappings);

            } catch (error) {
                statusManager.show(`
                    <div class="file-error">
                        <div class="error-icon">❌</div>
                        <div class="error-message">
                            <div class="error-title">Error Processing File</div>
                            <div class="error-details">${error.message}</div>
                        </div>
                    </div>
                `, 'error');
                progressBar.style.display = 'none';
                showUploadInterface();
            }
        };
        
        reader.readAsText(file);
    }

    async function runSanityTest() {
        console.log('🧪 Sanity test button clicked - starting test...');
        const button = document.getElementById('sanityTestBtn');

        try {
            // UI updates for processing
            hideUploadInterface();
            button.disabled = true;
            button.innerHTML = 'Processing Test Cases...';
            
            // Show file info for sanity test
            fileInfo.innerHTML = `
                <div class="file-details test-details">
                    <div class="file-icon">🧪</div>
                    <div class="file-info-content">
                        <div class="file-name">Sanity Test Suite</div>
                        <div class="file-meta">
                            <span class="file-type">100 Standard Test Cases</span>
                            <span class="file-date">${new Date().toLocaleDateString()}</span>
                        </div>
                    </div>
                </div>
            `;
            fileInfo.style.display = 'block';
            progressBar.style.display = 'block';
            progressFill.style.width = '25%';
            
            // Clear any existing status messages
            statusManager.clearAll();
            
            // Initialize processing state
            processingState = {
                isProcessing: true,
                currentStage: 'Sanity Test',
                totalItems: 100, // Assuming 100 test cases
                processedItems: 0,
                startTime: Date.now(),
                cacheHits: 0,
                errors: 0
            };
            
            // Show progress and load sanity test data
            statusManager.showProgress(
                `Loading sanity test data...`,
                0, 100
            );
            
            statusManager.showStage('Loading Test Data', 'Loading 100 standard test cases');
            
            // Load sanity test data from backend
            const response = await fetchWithRetry('/backend/core/sanity_test.json', { method: 'GET' }, 2, 8000);
            if (!response.ok) {
                throw new Error(`Failed to load sanity test data: ${response.status}`);
            }
            
            const sanityTestCodes = await response.json();
            console.log(`✓ Loaded ${sanityTestCodes.length} sanity test cases`);
            
            statusManager.showStage(
                'AI Processing', 
                `Processing exam names with ${formatModelName(currentModel)} biomedical language model`
            );
            
            // Process each test case
            const allMappings = [];
            
            for (let i = 0; i < sanityTestCodes.length; i++) {
                const code = sanityTestCodes[i];
                
                // Update progress
                processingState.processedItems = i + 1;
                statusManager.showProgress(
                    `Processing sanity test cases...`,
                    i + 1, sanityTestCodes.length
                );
                
                // Show status only every 10th test case to reduce verbosity
                if (i % 10 === 0 || i === sanityTestCodes.length - 1) {
                    statusManager.show(
                        `Testing case ${i + 1}/${sanityTestCodes.length}: ${code.EXAM_NAME}`,
                        'processing', 1000 // Auto-clear after 1 second
                    );
                }
                
                try {
                    
                    const apiResponse = await fetchWithRetry(API_URL, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            exam_name: code.EXAM_NAME,
                            model: currentModel
                        })
                    }, 3, 15000); // 3 retries, 15 second timeout
                    
                    const parsed = await apiResponse.json();
                    
                    // Check for cache hit
                    if (parsed.metadata && parsed.metadata.cache_hit) {
                        processingState.cacheHits++;
                    }
                    
                    // Add the original data and processed result
                    allMappings.push({
                        ...code,
                        clean_name: parsed.clean_name || 'UNKNOWN',
                        components: parsed.components || {},
                        metadata: parsed.metadata || {}
                    });
                    
                } catch (error) {
                    console.error(`Error processing ${code.EXAM_NAME}:`, error);
                    statusManager.show(
                        `<div class="processing-error">
                            <div class="error-icon">⚠</div>
                            <div class="error-details">
                                <div class="error-exam">${code.EXAM_NAME}</div>
                                <div class="error-reason">${error.message}</div>
                            </div>
                        </div>`,
                        'error',
                        3000
                    );
                    
                    processingState.errors++;
                    allMappings.push({ ...code, clean_name: 'ERROR - PARSING FAILED', components: {} });
                }
                
                // Remove current exam status after processing
                statusManager.remove(examStatusId);
                
                // Show processing stats every 10 items or at the end
                if (i % 10 === 0 || i === sanityTestCodes.length - 1) {
                    const elapsedTime = Date.now() - processingState.startTime;
                    const itemsPerSecond = processingState.processedItems > 0 ? 
                        Math.round((processingState.processedItems / (elapsedTime / 1000)) * 10) / 10 : 0;
                    
                    statusManager.showStats({
                        elapsedTime,
                        processedItems: processingState.processedItems,
                        totalItems: processingState.totalItems,
                        cacheHits: processingState.cacheHits,
                        errors: processingState.errors,
                        itemsPerSecond
                    });
                }
            }
            
            // Processing complete
            const elapsedTime = Date.now() - processingState.startTime;
            const formattedTime = formatProcessingTime(elapsedTime);
            
            statusManager.show(
                `<div class="processing-complete">
                    <div class="complete-icon">✓</div>
                    <div class="complete-message">
                        <div class="complete-title">Sanity Test Complete</div>
                        <div class="complete-details">
                            <span>${allMappings.length} test cases processed</span>
                            <span>${processingState.errors} errors</span>
                            <span>${formattedTime} total time</span>
                        </div>
                    </div>
                </div>`,
                'success'
            );
            
            processingState.isProcessing = false;
            
            // Generate and display results
            console.log('🧪 Sanity test results:', allMappings);
            
            // Show analysis and visualizations for the test results
            statusManager.showStage('Analysis', 'Analyzing test results and generating report');
            runAnalysis(allMappings);
            
        } catch (error) {
            console.error('❌ Sanity test failed:', error);
            statusManager.show(
                `<div class="error-alert">
                    <div class="error-title">Sanity Test Failed</div>
                    <div class="error-message">${error.message}</div>
                    <div class="error-suggestion">Check the console for more details.</div>
                </div>`,
                'error'
            );
            
            processingState.isProcessing = false;
            
        } finally {
            // Reset UI
            button.disabled = false;
            button.innerHTML = 'Run Sanity Test';
            progressFill.style.width = '0%';
            showUploadInterface();
        }
    }

    // --- ANALYSIS AND DISPLAY FUNCTIONS ---
    function runAnalysis(mappings) {
        summaryData = generateAnalyticsSummary(mappings);
        updateStatsUI(summaryData);
        updateResultsTitle();
        displayResults(mappings);
        generateConsolidatedResults(mappings);
        generateSourceLegend(mappings);
        resultsSection.style.display = 'block';
    }

    function updateResultsTitle() {
        const titleElement = document.getElementById('resultsTitle');
        const modelDisplayName = formatModelName(currentModel);
        titleElement.textContent = `Cleaning Results with ${modelDisplayName}`;
    }

    function generateSourceLegend(mappings) {
        // Get unique sources from the data
        const uniqueSources = [...new Set(mappings.map(item => item.data_source))];
        
        // Source display names
        const sourceNames = {
            'C': 'Central',
            'CO': 'SIRS (Canterbury)',
            'K': 'Southern',
            'TestData': 'Test Data',
            'SanityTest': 'Sanity Test',
            'Demo': 'Demo',
            'Sample': 'Sample'
        };
        
        // Create legend container if it doesn't exist
        let legendContainer = document.getElementById('sourceLegend');
        if (!legendContainer) {
            legendContainer = document.createElement('div');
            legendContainer.id = 'sourceLegend';
            legendContainer.className = 'source-legend';
            
            // Insert after the view toggle buttons
            const viewToggle = document.querySelector('.view-toggle');
            if (viewToggle && viewToggle.parentNode) {
                viewToggle.parentNode.insertBefore(legendContainer, viewToggle.nextSibling);
            } else {
                // Fallback: insert at the end of results section if viewToggle not found
                const resultsSection = document.getElementById('resultsSection');
                if (resultsSection) {
                    resultsSection.appendChild(legendContainer);
                }
            }
        }
        
        // Generate legend content
        let legendHTML = '<h4>Data Sources</h4><div class="source-legend-grid">';
        uniqueSources.forEach(source => {
            const color = getSourceColor(source);
            const displayName = sourceNames[source] || source;
            legendHTML += `
                <div class="source-legend-item">
                    <div class="source-legend-color" style="background-color: ${color};"></div>
                    <span>${displayName}</span>
                </div>
            `;
        });
        legendHTML += '</div>';
        
        legendContainer.innerHTML = legendHTML;
    }

    // --- UI & DISPLAY FUNCTIONS ---
    function updateStatsUI(summary) {
        document.getElementById('originalCount').textContent = summary.totalOriginalCodes;
        document.getElementById('cleanCount').textContent = summary.uniqueCleanNames;
        document.getElementById('consolidationRatio').textContent = `${summary.consolidationRatio}:1`;
        document.getElementById('modalityCount').textContent = Object.keys(summary.modalityBreakdown).length;
        document.getElementById('avgConfidence').textContent = `${summary.avgConfidence}%`;
        document.getElementById('genderContext').textContent = summary.genderContextCount;
    }

    // Source color mapping
    const sourceColors = {
        'C': '#1f77b4',            // Blue - Central
        'CO': '#2ca02c',           // Green - SIRS (Canterbury)
        'K': '#d62728',            // Red - Southern
        'TestData': '#ff1493',     // Deep Pink
        'SanityTest': '#00ced1',   // Dark Turquoise
        'Demo': '#ffd700',         // Gold
        'Sample': '#ff6347',       // Tomato
        'Default': '#6c757d'       // Bootstrap secondary gray
    };

    function getSourceColor(source) {
        return sourceColors[source] || sourceColors['Default'];
    }

    function displayResults(results) {
        resultsBody.innerHTML = '';
        results.forEach(item => {
            const row = resultsBody.insertRow();
            
            // Add source indicator cell
            const sourceCell = row.insertCell();
            sourceCell.style.cssText = `
                width: 12px;
                padding: 0;
                background-color: ${getSourceColor(item.data_source)};
                border-right: none;
                position: relative;
            `;
            
            // Set tooltip with full source name
            const sourceNames = {
                'C': 'Central',
                'CO': 'SIRS (Canterbury)', 
                'K': 'Southern'
            };
            sourceCell.title = sourceNames[item.data_source] || item.data_source;
            row.insertCell().textContent = item.exam_code;
            row.insertCell().textContent = item.exam_name;
            const cleanNameCell = row.insertCell();
            if (item.clean_name && item.clean_name.startsWith('ERROR')) {
                cleanNameCell.innerHTML = `<span class="error-message">${item.clean_name}</span>`;
            } else {
                cleanNameCell.innerHTML = `<strong>${item.clean_name}</strong>`;
            }

            // Add SNOMED FSN cell with code underneath
            const snomedFsnCell = row.insertCell();
            if (item.snomed && item.snomed.fsn) {
                let snomedContent = `<div>${item.snomed.fsn}</div>`;
                if (item.snomed.id) {
                    snomedContent += `<div style="font-size: 0.8em; color: #666; margin-top: 2px;">${item.snomed.id}</div>`;
                }
                snomedFsnCell.innerHTML = snomedContent;
            } else {
                snomedFsnCell.innerHTML = '<span style="color: #999;">-</span>';
            }

            // Add combined Tags cell (components + context)
            const tagsCell = row.insertCell();
            const { anatomy, laterality, contrast, technique, gender_context, age_context, clinical_context, clinical_equivalents } = item.components;
            
            // Add component tags
            if(anatomy && anatomy.length > 0) anatomy.forEach(a => { if (a && a.trim()) tagsCell.innerHTML += `<span class="tag anatomy">${a}</span>`});
            if(laterality && Array.isArray(laterality)) laterality.forEach(l => { if (l && l.trim()) tagsCell.innerHTML += `<span class="tag laterality">${l}</span>`});
            else if(laterality && typeof laterality === 'string' && laterality.trim()) tagsCell.innerHTML += `<span class="tag laterality">${laterality}</span>`;
            if(contrast && Array.isArray(contrast)) contrast.forEach(c => { if (c && c.trim()) tagsCell.innerHTML += `<span class="tag contrast">${c}</span>`});
            else if(contrast && typeof contrast === 'string' && contrast.trim()) tagsCell.innerHTML += `<span class="tag contrast">${contrast}</span>`;
            if(technique && technique.length > 0) technique.forEach(t => { if (t && t.trim()) tagsCell.innerHTML += `<span class="tag technique">${t}</span>`});
            
            // Add context tags
            if(gender_context && gender_context.trim()) tagsCell.innerHTML += `<span class="tag gender">${gender_context}</span>`;
            if(age_context && age_context.trim()) tagsCell.innerHTML += `<span class="tag age">${age_context}</span>`;
            if(clinical_context && clinical_context.length > 0) clinical_context.forEach(c => { if (c && c.trim()) tagsCell.innerHTML += `<span class="tag clinical">${c}</span>`});
            if(clinical_equivalents && clinical_equivalents.length > 0) {
                clinical_equivalents.slice(0, 2).forEach(e => { if (e && e.trim()) tagsCell.innerHTML += `<span class="tag equivalent">${e}</span>`});
            }
            
            // Add confidence cell
            const confidenceCell = row.insertCell();
            const confidence = item.components.confidence || 0;
            const confidencePercent = Math.round(confidence * 100);
            const confidenceClass = confidence >= 0.8 ? 'confidence-high' : confidence >= 0.6 ? 'confidence-medium' : 'confidence-low';
            confidenceCell.innerHTML = `
                <div class="confidence-bar">
                    <div class="confidence-fill ${confidenceClass}" style="width: ${confidencePercent}%"></div>
                </div>
                <small>${confidencePercent}%</small>
            `;
        });
    }

    // --- UTILITY & EXPORT FUNCTIONS ---
    function generateAnalyticsSummary(mappings) {
        const summary = {
            totalOriginalCodes: mappings.length,
            uniqueCleanNames: new Set(mappings.map(m => m.clean_name).filter(n => n && !n.startsWith('ERROR'))).size,
            modalityBreakdown: {}, 
            contrastUsage: { with: 0, without: 0, 'with and without': 0, none: 0 },
            lateralityDistribution: { left: 0, right: 0, bilateral: 0, none: 0 },
            genderContextBreakdown: { male: 0, female: 0, pregnancy: 0, none: 0 },
            clinicalContextBreakdown: { emergency: 0, screening: 0, follow_up: 0, intervention: 0, none: 0 },
            avgConfidence: 0,
            genderContextCount: 0
        };
        summary.consolidationRatio = summary.uniqueCleanNames > 0 ? (summary.totalOriginalCodes / summary.uniqueCleanNames).toFixed(2) : "0.00";
        
        const cleanNameGroups = {};
        let totalConfidence = 0;
        let confidenceCount = 0;
        
        mappings.forEach(m => {
            if (!m.components || (m.clean_name && m.clean_name.startsWith('ERROR'))) return;
            const { modality_code, components } = m;
            const modality = m.components.modality || modality_code;
            if (modality) summary.modalityBreakdown[modality] = (summary.modalityBreakdown[modality] || 0) + 1;
            
            const contrastType = (Array.isArray(components.contrast) 
                ? (components.contrast.length > 0 ? components.contrast[0] : 'none')
                : String(components.contrast || 'none')).replace(' ', '_');
            if(summary.contrastUsage.hasOwnProperty(contrastType)) summary.contrastUsage[contrastType]++;
            
            const laterality = (Array.isArray(components.laterality) 
                ? (components.laterality.length > 0 ? components.laterality[0] : 'none')
                : (components.laterality || 'none')).toLowerCase();
            if(summary.lateralityDistribution.hasOwnProperty(laterality)) summary.lateralityDistribution[laterality]++;
            
            // Enhanced analytics
            const genderContext = components.gender_context || 'none';
            if(summary.genderContextBreakdown.hasOwnProperty(genderContext)) {
                summary.genderContextBreakdown[genderContext]++;
                if(genderContext !== 'none') summary.genderContextCount++;
            }
            
            const clinicalContexts = components.clinical_context || [];
            if(clinicalContexts.length > 0) {
                clinicalContexts.forEach(context => {
                    if(summary.clinicalContextBreakdown.hasOwnProperty(context)) {
                        summary.clinicalContextBreakdown[context]++;
                    }
                });
            } else {
                summary.clinicalContextBreakdown.none++;
            }
            
            if(components.confidence !== undefined) {
                totalConfidence += components.confidence;
                confidenceCount++;
            }

            if (!cleanNameGroups[m.clean_name]) cleanNameGroups[m.clean_name] = [];
            cleanNameGroups[m.clean_name].push(m);
        });
        
        summary.avgConfidence = confidenceCount > 0 ? Math.round((totalConfidence / confidenceCount) * 100) : 0;
        summary.topConsolidatedExams = Object.entries(cleanNameGroups)
            .filter(([, group]) => group.length > 1).sort((a, b) => b[1].length - a[1].length).slice(0, 10)
            .map(([cleanName, group]) => ({
                cleanName, originalCount: group.length,
                examples: group.slice(0, 3).map(m => ({ source: m.data_source, code: m.exam_code, name: m.exam_name }))
            }));
        return summary;
    }

    function exportResults() {
        if (!allMappings.length) return alert('No data to export.');
        downloadJSON(allMappings, 'radiology_codes_cleaned.json');
    }

    function exportSummary() {
        if (!summaryData) return alert('No summary to export.');
        let report = `ENHANCED RADIOLOGY CODE CLEANING SUMMARY\n========================================\n`;
        report += `Total Original Codes: ${summaryData.totalOriginalCodes}\n`;
        report += `Unique Clean Names: ${summaryData.uniqueCleanNames}\n`;
        report += `Consolidation Ratio: ${summaryData.consolidationRatio}:1\n`;
        report += `Average Confidence: ${summaryData.avgConfidence}%\n`;
        report += `Gender Context Detected: ${summaryData.genderContextCount} codes\n\n`;
        
        report += `GENDER CONTEXT BREAKDOWN\n-----------------------\n`;
        Object.entries(summaryData.genderContextBreakdown).forEach(([context, count]) => {
            if(count > 0) report += `${context}: ${count}\n`;
        });
        
        report += `\nCLINICAL CONTEXT BREAKDOWN\n-------------------------\n`;
        Object.entries(summaryData.clinicalContextBreakdown).forEach(([context, count]) => {
            if(count > 0) report += `${context}: ${count}\n`;
        });
        
        report += `\nTOP CONSOLIDATED EXAMS\n----------------------\n`;
        summaryData.topConsolidatedExams.forEach(exam => {
            report += `\n"${exam.cleanName}" (${exam.originalCount} codes)\n`;
            exam.examples.forEach(ex => report += `   - [${ex.source}] ${ex.code}: ${ex.name}\n`);
        });
        downloadText(report, 'enhanced_radiology_cleaning_summary.txt');
    }
    
    function showConsolidationExamples() {
        if (!summaryData || !summaryData.topConsolidatedExams.length) return alert('No consolidation data available.');
        const examplesDiv = document.getElementById('consolidationExamples');
        examplesDiv.innerHTML = '';
        summaryData.topConsolidatedExams.forEach(exam => {
            const card = document.createElement('div');
            card.className = 'example-card';
            card.innerHTML = `<h4>${exam.cleanName} (${exam.originalCount} original codes)</h4>
                              <div class="original-codes">
                                  ${exam.examples.map(ex => `• [${ex.source}] ${ex.code}: "${ex.name}"`).join('<br>')}
                                  ${exam.originalCount > 3 ? `<br>• ... and ${exam.originalCount - 3} more` : ''}
                              </div>`;
            examplesDiv.appendChild(card);
        });
        document.getElementById('consolidationModal').style.display = 'flex';
    }

    function closeModal() { 
        document.getElementById('consolidationModal').style.display = 'none'; 
    }
    
    // --- CONSOLIDATED VIEW FUNCTIONS ---
    let consolidatedData = [];
    let filteredConsolidatedData = [];
    
    function generateConsolidatedResults(mappings) {
        const consolidatedGroups = {};
        
        // Group mappings by clean name
        mappings.forEach(mapping => {
            if (!mapping.clean_name || mapping.clean_name.startsWith('ERROR')) return;
            
            const cleanName = mapping.clean_name;
            if (!consolidatedGroups[cleanName]) {
                consolidatedGroups[cleanName] = {
                    cleanName: cleanName,
                    sourceCodes: [],
                    totalCount: 0,
                    avgConfidence: 0,
                    components: mapping.components,
                    dataSources: new Set(),
                    modalities: new Set()
                };
            }
            
            consolidatedGroups[cleanName].sourceCodes.push({
                dataSource: mapping.data_source,
                examCode: mapping.exam_code,
                examName: mapping.exam_name,
                confidence: mapping.components.confidence || 0
            });
            
            consolidatedGroups[cleanName].totalCount++;
            consolidatedGroups[cleanName].dataSources.add(mapping.data_source);
            consolidatedGroups[cleanName].modalities.add(mapping.modality_code);
        });
        
        // Calculate average confidence for each group
        Object.values(consolidatedGroups).forEach(group => {
            const totalConfidence = group.sourceCodes.reduce((sum, code) => sum + code.confidence, 0);
            group.avgConfidence = totalConfidence / group.sourceCodes.length;
        });
        
        consolidatedData = Object.values(consolidatedGroups);
        filteredConsolidatedData = [...consolidatedData];
        sortConsolidatedResults();
    }
    
    // --- MODEL TOGGLE FUNCTIONS (moved to top of DOMContentLoaded) ---
    
    function showFullView() {
        document.getElementById('fullView').style.display = 'block';
        document.getElementById('consolidatedView').style.display = 'none';
        document.getElementById('fullViewBtn').classList.add('active');
        document.getElementById('consolidatedViewBtn').classList.remove('active');
    }
    
    function showConsolidatedView() {
        document.getElementById('fullView').style.display = 'none';
        document.getElementById('consolidatedView').style.display = 'block';
        document.getElementById('fullViewBtn').classList.remove('active');
        document.getElementById('consolidatedViewBtn').classList.add('active');
        displayConsolidatedResults();
    }
    
    function displayConsolidatedResults() {
        const container = document.getElementById('consolidatedResults');
        container.innerHTML = '';
        
        filteredConsolidatedData.forEach(group => {
            const groupElement = document.createElement('div');
            groupElement.className = 'consolidated-group';
            
            const confidencePercent = Math.round(group.avgConfidence * 100);
            const confidenceClass = group.avgConfidence >= 0.8 ? 'confidence-high' : 
                                   group.avgConfidence >= 0.6 ? 'confidence-medium' : 'confidence-low';
            
            groupElement.innerHTML = `
                <div class="consolidated-header">
                    <div class="consolidated-title">${group.cleanName}</div>
                    <div class="consolidated-count">${group.totalCount} codes</div>
                </div>
                <div class="consolidated-body">
                    <div class="consolidated-meta">
                        <div><strong>Sources:</strong> ${Array.from(group.dataSources).join(', ')}</div>
                        <div><strong>Modalities:</strong> ${Array.from(group.modalities).join(', ')}</div>
                        <div><strong>Avg Confidence:</strong> 
                            <span class="confidence-bar">
                                <span class="confidence-fill ${confidenceClass}" style="width: ${confidencePercent}%"></span>
                            </span>
                            ${confidencePercent}%
                        </div>
                    </div>
                    <div class="consolidated-components">
                        ${generateComponentTags(group.components)}
                    </div>
                    <div class="source-codes">
                        ${group.sourceCodes.map(code => `
                            <div class="source-code">
                                <div class="source-code-header">
                                    <span>[${code.dataSource}] ${code.examCode}</span>
                                </div>
                                <div class="source-code-name">${code.examName}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            
            container.appendChild(groupElement);
        });
    }
    
    function generateComponentTags(components) {
        let tags = '';
        
        if (components.anatomy) {
            components.anatomy.forEach(a => tags += `<span class="tag anatomy">${a}</span>`);
        }
        if (components.laterality && components.laterality.length > 0) {
            const lateralityValue = Array.isArray(components.laterality) 
                ? components.laterality.join(', ') 
                : components.laterality;
            tags += `<span class="tag laterality">${lateralityValue}</span>`;
        }
        if (components.contrast && components.contrast.length > 0) {
            const contrastValue = Array.isArray(components.contrast) 
                ? components.contrast.join(', ') 
                : components.contrast;
            tags += `<span class="tag contrast">${contrastValue}</span>`;
        }
        if (components.technique) {
            components.technique.forEach(t => tags += `<span class="tag technique">${t}</span>`);
        }
        if (components.gender_context) {
            tags += `<span class="tag gender">${components.gender_context}</span>`;
        }
        if (components.clinical_context) {
            components.clinical_context.forEach(c => tags += `<span class="tag clinical">${c}</span>`);
        }
        
        return tags;
    }
    
    function filterConsolidatedResults() {
        const searchTerm = document.getElementById('consolidatedSearch').value.toLowerCase();
        
        if (searchTerm === '') {
            filteredConsolidatedData = [...consolidatedData];
        } else {
            filteredConsolidatedData = consolidatedData.filter(group => 
                group.cleanName.toLowerCase().includes(searchTerm) ||
                group.sourceCodes.some(code => 
                    code.examName.toLowerCase().includes(searchTerm) ||
                    code.examCode.toLowerCase().includes(searchTerm)
                )
            );
        }
        
        sortConsolidatedResults();
    }
    
    function sortConsolidatedResults() {
        const sortBy = document.getElementById('consolidatedSort').value;
        
        filteredConsolidatedData.sort((a, b) => {
            switch (sortBy) {
                case 'count':
                    return b.totalCount - a.totalCount;
                case 'name':
                    return a.cleanName.localeCompare(b.cleanName);
                case 'confidence':
                    return b.avgConfidence - a.avgConfidence;
                default:
                    return b.totalCount - a.totalCount;
            }
        });
        
        displayConsolidatedResults();
    }

    // preventDefaults function moved to top of DOMContentLoaded

    function downloadJSON(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        triggerDownload(blob, filename);
    }

    function downloadText(text, filename) {
        const blob = new Blob([text], { type: 'text/plain' });
        triggerDownload(blob, filename);
    }

    function triggerDownload(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    // Event listener for file input change  
    function handleFileSelect(e) {
        if (e.target.files[0]) {
            processFile(e.target.files[0]);
        }
    }
    document.getElementById('fileInput').addEventListener('change', handleFileSelect);
});