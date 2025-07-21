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
                
                // Insert after file info
                const fileInfo = document.getElementById('fileInfo');
                if (fileInfo && fileInfo.parentNode) {
                    fileInfo.parentNode.insertBefore(this.container, fileInfo.nextSibling);
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

    // --- NEW: Clear persistent messages like stage, stats, and progress ---
    clearPersistentMessages() {
        if (this.progressMessage) this.remove(this.progressMessage);
        if (this.stageMessage) this.remove(this.stageMessage);
        if (this.statsMessage) this.remove(this.statsMessage);
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
    
    // Show a progress status message with visual progress bar
    showProgress(message, current, total, type = 'progress') {
        const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
        const progressContent = `
            <div class="progress-container">
                <div class="progress-header">
                    <span class="progress-message">${message}</span>
                    <span class="progress-counter">${current}/${total} (${percentage}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;

        if (!this.progressMessage) {
            // Create new progress status
            this.progressMessage = this.show(progressContent, type);
        } else {
            // Update existing progress status
            this.update(this.progressMessage, progressContent);
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
    
    // --- UPDATED: Show processing statistics in a compact, single row ---
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
                <div class="stats-item"><strong>Time:</strong> ${formattedTime}</div>
                <div class="stats-item"><strong>Rate:</strong> ${itemsPerSecond} items/sec</div>
                <div class="stats-item"><strong>Cache:</strong> ${cacheHitRate}%</div>
                <div class="stats-item"><strong>Errors:</strong> ${errors}</div>
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
    
    // Show file information in a consistent way
    showFileInfo(fileName, fileSize) {
        const fileMessage = `<strong>File loaded:</strong> ${fileName} (${this.formatFileSize(fileSize)})`;
        return this.show(fileMessage, 'info');
    }
    
    // Show test status in a consistent way
    showTestInfo(testName, description) {
        const testMessage = `<strong>${testName}:</strong> ${description}`;
        return this.show(testMessage, 'info');
    }
    
    // --- UPDATED: Inject required CSS styles with progress bar styles ---
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
            /* --- UPDATED: Styles for single-row stats --- */
            .processing-stats {
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                align-items: center;
                width: 100%;
                font-size: 13px;
            }
            .stats-item {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .stats-item strong {
                font-weight: 600;
                color: var(--color-gray-600, #666);
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
            
            /* Progress bar styles */
            .progress-container {
                width: 100%;
            }
            .progress-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
                font-size: 14px;
            }
            .progress-message {
                font-weight: 500;
            }
            .progress-counter {
                font-family: var(--font-family-mono, monospace);
                font-size: 13px;
                color: var(--color-gray-600, #666);
            }
            .progress-bar {
                width: 100%;
                height: 8px;
                background-color: var(--color-gray-200, #e0e0e0);
                border-radius: 4px;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--color-primary, #3f51b5), var(--color-primary-dark, #303f9f));
                border-radius: 4px;
                transition: width 0.3s ease;
                min-width: 2px;
            }
            .progress-fill:empty {
                background: var(--color-primary, #3f51b5);
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

// Batch processing configuration - matches backend NLP_BATCH_SIZE
// To configure batch size: set window.ENV.NLP_BATCH_SIZE or backend env var NLP_BATCH_SIZE
function getBatchSize() {
    // Check for environment variable (in production this could be set via build-time env vars)
    if (typeof window !== 'undefined' && window.ENV && window.ENV.NLP_BATCH_SIZE) {
        return parseInt(window.ENV.NLP_BATCH_SIZE);
    }
    // Default batch size (same as backend default)
    return 25;
}

// --- UTILITY FUNCTIONS (globally accessible) ---
function preventDefaults(e) { 
    e.preventDefault(); 
    e.stopPropagation();
}

// --- GLOBAL VARIABLES ---
let currentModel = 'default'; // Initialize the current model
let availableModels = {}; // Store available models from API

// --- MODEL TOGGLE FUNCTIONS (globally accessible) ---
function switchModel(modelKey) {
    console.log(`🔄 switchModel called with modelKey: ${modelKey}`);
    
    if (!availableModels[modelKey] || availableModels[modelKey].status !== 'available') {
        console.warn(`Model ${modelKey} is not available. Status:`, availableModels[modelKey]?.status);
        return;
    }
    
    console.log(`✓ Switching to model: ${modelKey}`);
    currentModel = modelKey;
    
    document.querySelectorAll('.model-toggle').forEach(btn => btn.classList.remove('active'));
    const selectedButton = document.getElementById(`${modelKey}ModelBtn`);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }
    
    const displayName = formatModelName(modelKey);
    // USE THIS:
    statusManager.show(`Switched to ${displayName} model`, 'success', 3000);
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
    
    async function testApiConnectivity() {
        try {
            // CORRECTED: Use the full, pre-constructed URL.
            const response = await fetch(apiConfig.HEALTH_URL, { method: 'GET', timeout: 5000 });
            if (response.ok) console.log('✓ API connectivity test passed');
            else console.warn('⚠ API health check failed:', response.status);
        } catch (error) {
            console.error('✗ API connectivity test failed:', error);
        }
    }
    testApiConnectivity();
    
    // --- DYNAMIC MODEL INITIALIZATION ---
    async function loadAvailableModels() {
        try {
            console.log('🔍 Fetching available models from backend...');
            const response = await fetch(MODELS_URL, { method: 'GET', timeout: 5000 });
            if (response.ok) {
                const modelsData = await response.json();
                availableModels = modelsData.models || {};
                currentModel = modelsData.default_model || 'default';
                
                console.log('✓ Available models loaded:', Object.keys(availableModels));
                buildModelSelectionUI();
            } else {
                console.warn('⚠ Models API unavailable, using fallback models');
                useFallbackModels();
            }
        } catch (error) {
            console.error('✗ Failed to load models:', error);
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
                button.addEventListener('click', () => switchModel(modelKey));
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

    // --- DOM ELEMENTS ---
    const uploadSection = document.getElementById('uploadSection');
    const demosSection = document.getElementById('demosSection');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
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
    
    // View toggle event listener
    document.getElementById('viewToggleBtn').addEventListener('click', toggleView);
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
            <p><strong>What it does:</strong> This application transforms messy, inconsistent radiology exam names from different hospital systems into standardised, clinically meaningful names with structured components.</p>
            
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
                <h4>2. Standardisation</h4>
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
            <p>The Radiology Cleaner application is a web-based tool designed to standardise and process radiology exam names. It leverages a Flask backend for API services, a Python-based natural language processing (NLP) engine for semantic parsing, and a simple HTML/JavaScript frontend for user interaction. The system aims to provide clean, standardised exam names, SNOMED codes, and extracted clinical components (anatomy, laterality, contrast, etc.) for improved data quality and interoperability.</p>
            
            <h2>2. Architecture Overview</h2>
            <p>The system follows a modern web application architecture with the following key components:</p>
            <ul>
                <li><strong>Frontend</strong>: HTML/CSS/JavaScript interface for user interaction</li>
                <li><strong>Backend API</strong>: Flask application with REST endpoints</li>
                <li><strong>NLP Engine</strong>: Semantic parsing and text processing</li>
                <li><strong>NHS Lookup</strong>: Standardisation against NHS reference data</li>
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
                <li><strong>NHSLookupEngine</strong>: NHS reference data standardisation
                    <ul>
                        <li>Unified preprocessing pipeline</li>
                        <li>Dynamic cache invalidation</li>
                        <li>Dual lookup strategy (Clean Name + SNOMED FSN)</li>
                        <li>Interventional procedure weighting</li>
                    </ul>
                </li>
            </ul>
            
            <h2>4. Recent Improvements</h2>
            
            
            <h3>4.1. Multi-Model NLP Support</h3>
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
                <li><strong>NHS Standardisation</strong>: Match against NHS reference data</li>
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
        statusManager.clearAll();
        
        // Reset file input
        fileInput.value = '';
        
        // Clear global state
        allMappings = [];
        summaryData = null;
        
        // Clear any status messages
        statusManager.clearAll();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    

    // --- CORE PROCESSING FUNCTIONS ---
    // Process files individually (for small files)
    async function processIndividually(codes) {
    // Inform the user this is a slower fallback method
    statusManager.show('Batch processing failed. Using slower individual processing...', 'warning', 6000);
    
    // This function will now update a single progress message in real-time
    try {
        for (let i = 0; i < codes.length; i++) {
            const code = codes[i];
            
            // Update the progress bar before each API call for a responsive feel
            // The showProgress method is designed to be updated repeatedly
            statusManager.showProgress('Processing record', i + 1, codes.length);
            
            try {
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ exam_name: code.EXAM_NAME, modality_code: code.MODALITY_CODE, model: currentModel })
                });
                if (!response.ok) throw new Error(`API returned status ${response.status}`);
                
                const parsed = await response.json();
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
                allMappings.push({ ...code, clean_name: 'ERROR - PARSING FAILED', components: {} });
            }
        }
        
        statusManager.show(`Individual processing complete! ${allMappings.length} records processed.`, 'success', 8000);

    } finally {
        // Use the dedicated method to clean up the progress, stage, and stats messages
        statusManager.clearPersistentMessages();
    }
}
    
    // Process files in batches (for large files)
    async function processBatch(codes) {
        console.log(`Using batch processing for ${codes.length} records...`);
        
        // Update status message
        statusManager.show(`Preparing ${codes.length} exam records for processing...`, 'info', 4000);
        
        try {
            // Transform codes to the expected format for batch API
            const exams = codes.map(code => ({
                exam_name: code.EXAM_NAME,
                modality_code: code.MODALITY_CODE,
                data_source: code.DATA_SOURCE,
                exam_code: code.EXAM_CODE
            }));
            
            statusManager.show(`Sending ${codes.length} exam records to AI processing engine...`, 'progress', 6000);
            
            const response = await fetch(BATCH_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    exams: exams,
                    chunk_size: getBatchSize(), // Use configured batch size
                    model: currentModel
                })
            });
            
            if (!response.ok) throw new Error(`Batch API returned status ${response.status}`);
            
            statusManager.show(`🧠 AI engine processing exam names using biomedical BERT model...`, 'progress', 7000);
            
            const batchResult = await response.json();
            
            // Process batch results - updated format from HEAD
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
            }
            
            // Handle any errors from batch processing - updated format from HEAD
            if (batchResult.errors && batchResult.errors.length > 0) {
                console.error('Errors returned from batch processing:', batchResult.errors);
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
            }
            
            // Log batch processing stats and update user
            if (batchResult.processing_stats) {
                const stats = batchResult.processing_stats;
                const formattedTime = formatProcessingTime(stats.processing_time_ms);
                
                // Handle optional cache statistics
                if (stats.cache_hits !== undefined && stats.cache_hit_ratio !== undefined) {
                    const hitRate = (stats.cache_hit_ratio * 100).toFixed(1);
                    statusManager.show(`Processing complete! ${stats.successful} successful, ${stats.cache_hits} from cache (${hitRate}% hit rate), ${formattedTime} total`, 'success', 8000);
                    console.log(`Batch processing completed: ${stats.successful} successful, ${stats.errors} errors, ${stats.cache_hits} cache hits (${hitRate}% hit rate), ${formattedTime} total`);
                } else {
                    statusManager.show(`Processing complete! ${stats.successful} successful, ${formattedTime} total`, 'success', 8000);
                    console.log(`Batch processing completed: ${stats.successful} successful, ${stats.errors} errors, ${formattedTime} total`);
                }
            } else {
                statusManager.show(`Processing complete! ${allMappings.length} exam records processed successfully.`, 'success', 8000);
            }
            
        } catch (error) {
            console.error('Batch processing failed:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                name: error.name
            });
            statusManager.show(`Batch processing failed: ${error.message}. Falling back to individual processing...`, 'warning', 6000);
            // Fall back to individual processing if batch fails
            console.log('Falling back to individual processing...');
            await processIndividually(codes);
        }
        
    }

    // --- CORE LOGIC ---
    async function processFile(file) {
        if (!file.name.endsWith('.json')) {
            alert('Please upload a valid JSON file.');
            return;
        }

        // Hide upload interface during processing
        hideUploadInterface();
        
        statusManager.clearAll();
        statusManager.showFileInfo(file.name, file.size);
        resultsSection.style.display = 'none';
        allMappings = [];
        summaryData = null;
        

        const reader = new FileReader();
        reader.onload = async function(e) {
            try {
                const codes = JSON.parse(e.target.result);
                if (!Array.isArray(codes) || codes.length === 0) {
                    alert('JSON file is empty or not in the correct array format.');
                    showUploadInterface();
                    return;
                }

                console.log(`Processing ${codes.length} exam records...`);
                statusManager.show(`📁 Loaded ${codes.length} exam records from ${file.name}. Starting processing...`, 'info', 5000);
        
                
                await processBatch(codes);
        
                runAnalysis(allMappings);

             } catch (error) {
                alert('Error processing file: ' + error.message);
                showUploadInterface();
             }
};
        
        reader.readAsText(file);
    }



    async function runSanityTest() {
    console.log('🧪 Sanity test button clicked - starting test...');
    const button = document.getElementById('sanityTestBtn');
    let statusId = null; // To hold the ID of the "in-progress" message

    try {
        // UI updates for processing
        hideUploadInterface();
        button.disabled = true;
        button.innerHTML = 'Processing Test Cases...';
        statusManager.clearAll();
        statusManager.showTestInfo('Sanity Test', 'Verifying engine performance...');

        // Show a "progress" message that we can remove later
        statusId = statusManager.show(`Running 100-exam test suite with model: '${currentModel}'...`, 'progress');

        // Call the correct backend endpoint
        const response = await fetch(apiConfig.SANITY_TEST_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: currentModel })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API returned status ${response.status}: ${errorText}`);
        }

        allMappings = await response.json();
        console.log(`Completed processing. Generated ${allMappings.length} results.`);
        
        // On success, explicitly remove the progress message and show a success one
        statusManager.remove(statusId);
        statusId = null; // Clear the ID so the 'finally' block doesn't try to remove it again
        statusManager.show(`Sanity test complete! Processed ${allMappings.length} records.`, 'success', 5000);
        
        // Run analysis on the results
        runAnalysis(allMappings);

    } catch (error) {
        console.error('Sanity test failed:', error);
        statusManager.show(`❌ Sanity Test Failed: ${error.message}`, 'error');
        
        // Show a persistent error message so the user can read it
        statusManager.show(`<strong>Sanity Test Failed:</strong> ${error.message}`, 'error', 0);
        showUploadInterface(); // Let the user try again or upload a file
        
    } finally {
        // This 'finally' block ensures the UI is always restored correctly
        
        // If an error occurred before the success message, the progress status might still be visible.
        // This ensures it's always removed.
        if (statusId) {
            statusManager.remove(statusId);
        }
        
        // Restore button state
        button.disabled = false;
        button.innerHTML = '100 Exam Test Suite';
    }
}

    function runAnalysis(mappings) {
        summaryData = generateAnalyticsSummary(mappings);
        updateStatsUI(summaryData);
        updateResultsTitle();
        displayResults(mappings);
        generateConsolidatedResults(mappings);
        generateSourceLegend(mappings);
        resultsSection.style.display = 'block';
        // NOTE: Upload interface stays hidden - only restored via "New Upload" button
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
            'NL': 'Northland',
            'TMT': 'Te Manawa Taki',  // Placeholder code
            'AM': 'Auckland Metro',   // Placeholder code
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
        'K': '#9467bd',            // Purple - Southern (changed from red to avoid error implication)
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

    function closeModal() { document.getElementById('consolidationModal').style.display = 'none'; }
    
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
                confidence: mapping.components.confidence || 0,
                snomedId: mapping.snomed_id || '',
                source: mapping.source || 'UNKNOWN',
                components: mapping.components || {}
            });
            
            consolidatedGroups[cleanName].totalCount++;
            consolidatedGroups[cleanName].dataSources.add(mapping.data_source);
            consolidatedGroups[cleanName].modalities.add(mapping.modality_code);
        });
        
        // Calculate average confidence and collect additional metadata for each group
        Object.values(consolidatedGroups).forEach(group => {
            const totalConfidence = group.sourceCodes.reduce((sum, code) => sum + code.confidence, 0);
            group.avgConfidence = totalConfidence / group.sourceCodes.length;
            
            // Extract SNOMED ID from the first available source code that has one
            group.snomedId = group.sourceCodes.find(code => code.snomedId)?.snomedId || '';
            
            // Set the components to the first available component set (they should be similar within a group)
            group.components = group.sourceCodes.find(code => code.components)?.components || {};
        });
        
        consolidatedData = Object.values(consolidatedGroups);
        filteredConsolidatedData = [...consolidatedData];
        sortConsolidatedResults();
    }
    
    
    
    // Track current view state
    let isFullView = true;
    
    function toggleView() {
        const toggleBtn = document.getElementById('viewToggleBtn');
        const fullView = document.getElementById('fullView');
        const consolidatedView = document.getElementById('consolidatedView');
        
        if (isFullView) {
            // Switch to consolidated view
            fullView.style.display = 'none';
            consolidatedView.style.display = 'block';
            toggleBtn.textContent = 'Switch to Full View';
            toggleBtn.classList.remove('active');
            toggleBtn.classList.add('secondary');
            displayConsolidatedResults();
            isFullView = false;
        } else {
            // Switch to full view
            fullView.style.display = 'block';
            consolidatedView.style.display = 'none';
            toggleBtn.textContent = 'Switch to Consolidated View';
            toggleBtn.classList.remove('secondary');
            toggleBtn.classList.add('active');
            isFullView = true;
        }
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
            
            // Group source codes by data source for better organization
            const sourceGroups = groupSourceCodesByDataSource(group.sourceCodes);
            const matchingMethodology = getGroupMatchingMethodology(group.sourceCodes);
            
            groupElement.innerHTML = `
                <div class="consolidated-header">
                    <div class="consolidated-title-section">
                        <div class="consolidated-title">${group.cleanName}</div>
                        <div class="consolidated-snomed">
                            ${group.snomedId ? `<span class="snomed-badge">SNOMED: ${group.snomedId}</span>` : ''}
                        </div>
                    </div>
                    <div class="consolidated-count">${group.totalCount} codes</div>
                </div>
                <div class="consolidated-body">
                    <div class="consolidated-meta">
                        <div class="meta-item">
                            <strong>Data Sources</strong>
                            <div class="source-indicators">
                                ${Array.from(group.dataSources).map(source => 
                                    `<div class="source-item" title="${getSourceDisplayName(source)}">${getSourceDisplayName(source)}</div>`
                                ).join('')}
                            </div>
                        </div>
                        <div class="meta-item">
                            <strong>Modalities</strong>
                            <div class="modality-list">${Array.from(group.modalities).join(', ')}</div>
                        </div>
                        <div class="meta-item">
                            <strong>Matching Engine</strong>
                            <div class="methodology-badge">${matchingMethodology}</div>
                        </div>
                        <div class="meta-item">
                            <strong>Avg Confidence</strong>
                            <div class="confidence-display">
                                <div class="confidence-bar">
                                    <div class="confidence-fill ${confidenceClass}" style="width: ${confidencePercent}%"></div>
                                </div>
                                <div class="confidence-text">${confidencePercent}%</div>
                            </div>
                        </div>
                        <div class="meta-item">
                            <strong>Parsed Components</strong>
                            <div class="component-tags">${generateComponentTags(group.components)}</div>
                        </div>
                        <div class="meta-item">
                            <strong>SNOMED Info</strong>
                            <div class="snomed-info">
                                ${group.snomedId ? `<div class="snomed-id">${group.snomedId}</div>` : '<div class="no-snomed">No SNOMED</div>'}
                            </div>
                        </div>
                    </div>
                    <div class="source-codes">
                        <div class="source-codes-label"><strong>Source Exam Codes:</strong></div>
                        ${generateGroupedSourceCodes(sourceGroups)}
                    </div>
                </div>
            `;
            
            container.appendChild(groupElement);
        });
    }
    
    function generateComponentTags(components) {
        let tags = '';
        
        // Anatomy tags
        if (components.anatomy && components.anatomy.length > 0) {
            components.anatomy.forEach(a => tags += `<span class="tag anatomy" title="Anatomy">${a}</span>`);
        }
        
        // Modality tag (from the main component)
        if (components.modality) {
            tags += `<span class="tag modality" title="Modality">${components.modality}</span>`;
        }
        
        // Laterality tags
        if (components.laterality && components.laterality.length > 0) {
            const lateralityValue = Array.isArray(components.laterality) 
                ? components.laterality.join(', ') 
                : components.laterality;
            tags += `<span class="tag laterality" title="Laterality">${lateralityValue}</span>`;
        }
        
        // Contrast tags
        if (components.contrast && components.contrast.length > 0) {
            const contrastValue = Array.isArray(components.contrast) 
                ? components.contrast.join(', ') 
                : components.contrast;
            tags += `<span class="tag contrast" title="Contrast">${contrastValue}</span>`;
        }
        
        // Technique tags
        if (components.technique && components.technique.length > 0) {
            components.technique.forEach(t => tags += `<span class="tag technique" title="Technique">${t}</span>`);
        }
        
        // Gender context
        if (components.gender_context) {
            tags += `<span class="tag gender" title="Gender Context">${components.gender_context}</span>`;
        }
        
        // Clinical context
        if (components.clinical_context && components.clinical_context.length > 0) {
            components.clinical_context.forEach(c => tags += `<span class="tag clinical" title="Clinical Context">${c}</span>`);
        }
        
        return tags || '<span class="no-components">No parsed components</span>';
    }
    
    // Group source codes by data source for better organization
    function groupSourceCodesByDataSource(sourceCodes) {
        const groups = {};
        sourceCodes.forEach(code => {
            if (!groups[code.dataSource]) {
                groups[code.dataSource] = [];
            }
            groups[code.dataSource].push(code);
        });
        return groups;
    }
    
    // Get the matching methodology for a group of source codes
    function getGroupMatchingMethodology(sourceCodes) {
        const sources = new Set(sourceCodes.map(code => code.source));
        if (sources.size === 1) {
            const source = Array.from(sources)[0];
            if (source && source.includes('UNIFIED_MATCH')) {
                return 'NLP Semantic Matching';
            } else if (source && source.includes('EXACT_MATCH')) {
                return 'Exact Match';
            } else if (source && source.includes('FUZZY_MATCH')) {
                return 'Fuzzy String Matching';
            } else if (source && source.includes('NO_MATCH')) {
                return 'No Match';
            }
        }
        
        // Check if we have any valid sources at all
        const validSources = Array.from(sources).filter(s => s && s.trim() !== '');
        if (validSources.length === 0) {
            return 'NLP Semantic Matching'; // Default for new backend results
        }
        
        return sources.size > 1 ? 'Mixed Methods' : 'NLP Semantic Matching';
    }
    
    // Get display name for data source
    function getSourceDisplayName(source) {
        const sourceNames = {
            'C': 'Central',
            'CO': 'SIRS (Canterbury)', 
            'K': 'Southern',
            'NL': 'Northland',
            'TMT': 'Te Manawa Taki',  // Placeholder code
            'AM': 'Auckland Metro',   // Placeholder code
            'TestData': 'Test Data',
            'SanityTest': 'Sanity Test',
            'Demo': 'Demo',
            'Upload': 'User Upload'
        };
        return sourceNames[source] || source;
    }
    
    // Generate grouped source codes display
    function generateGroupedSourceCodes(sourceGroups) {
        let html = '';
        
        Object.entries(sourceGroups).forEach(([dataSource, codes]) => {
            const sourceColor = getSourceColor(dataSource);
            const sourceDisplayName = getSourceDisplayName(dataSource);
            
            html += `
                <div class="source-group">
                    <div class="source-group-header">
                        <span class="source-indicator" style="background-color: ${sourceColor}"></span>
                        <span class="source-name">${sourceDisplayName} (${codes.length})</span>
                    </div>
                    <div class="source-group-codes">
                        ${codes.map(code => `
                            <div class="source-code">
                                <div class="source-code-header">
                                    <span class="exam-code">${code.examCode}</span>
                                    <span class="confidence-mini">${Math.round(code.confidence * 100)}%</span>
                                </div>
                                <div class="source-code-name">${code.examName}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });
        
        return html;
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
    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
    // formatFileSize function removed - using StatusManager.formatFileSize instead
    
    function formatProcessingTime(milliseconds) {
        if (milliseconds < 1000) {
            return `${milliseconds}ms`;
        } else if (milliseconds < 60000) {
            const seconds = (milliseconds / 1000).toFixed(1);
            return `${seconds}s`;
        } else {
            const minutes = Math.floor(milliseconds / 60000);
            const seconds = Math.floor((milliseconds % 60000) / 1000);
            if (seconds === 0) {
                return `${minutes}m`;
            } else {
                return `${minutes}m ${seconds}s`;
            }
        }
    }
    
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
    
});