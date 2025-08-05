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
        
        this.injectStyles();
    }
    
    ensureContainer() {
        if (!this.container) {
            this.container = document.getElementById('statusMessageContainer');
            // The container already exists in HTML, so we don't need to create it
            if (!this.container) {
                console.warn('Status message container not found in HTML');
            }
        }
        return this.container;
    }
    
    clearAll() {
        const container = this.ensureContainer();
        container.innerHTML = '';
        this.activeMessages.clear();
        this.progressMessage = null;
        this.stageMessage = null;
        this.statsMessage = null;
    }

    clearPersistentMessages() {
        if (this.progressMessage) this.remove(this.progressMessage);
        if (this.stageMessage) this.remove(this.stageMessage);
        if (this.statsMessage) this.remove(this.statsMessage);
        this.progressMessage = null;
        this.stageMessage = null;
        this.statsMessage = null;
    }
    
    show(message, type = 'info', autoHideDuration = 0, id = null) {
        const container = this.ensureContainer();
        const style = this.typeConfig[type] || this.typeConfig.info;
        const messageId = id || `status-${++this.messageCounter}`;
        
        const messageElement = document.createElement('div');
        messageElement.id = messageId;
        messageElement.className = `status-message status-${type}`;
        messageElement.style.cssText = `
            padding: 12px 16px; background: ${style.background}; border: ${style.border}; border-radius: 6px;
            font-size: 14px; color: var(--color-gray-800, #333); font-weight: 500; display: flex;
            align-items: center; gap: 12px; animation: statusFadeIn 0.3s ease-out; position: relative;
        `;
        
        const iconElement = document.createElement('div');
        iconElement.className = 'status-icon';
        iconElement.innerHTML = style.icon;
        iconElement.style.cssText = `flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: ${style.color};`;
        
        const textElement = document.createElement('div');
        textElement.className = 'status-text';
        textElement.innerHTML = message;
        textElement.style.cssText = `flex-grow: 1;`;
        
        messageElement.appendChild(iconElement);
        messageElement.appendChild(textElement);
        
        if (autoHideDuration === 0) {
            const closeButton = document.createElement('button');
            closeButton.className = 'status-close';
            closeButton.innerHTML = '×';
            closeButton.style.cssText = `background: none; border: none; font-size: 18px; cursor: pointer; padding: 0; line-height: 1; color: var(--color-gray-600, #666); opacity: 0.7; transition: opacity 0.2s; position: absolute; right: 12px; top: 50%; transform: translateY(-50%);`;
            closeButton.addEventListener('click', () => this.remove(messageId));
            messageElement.appendChild(closeButton);
        }
        
        container.appendChild(messageElement);
        this.activeMessages.set(messageId, messageElement);
        
        if (autoHideDuration > 0) {
            setTimeout(() => this.remove(messageId), autoHideDuration);
        }
        
        return messageId;
    }
    
    update(id, message) {
        const messageElement = this.activeMessages.get(id);
        if (!messageElement) return this.show(message, 'info');
        
        const textElement = messageElement.querySelector('.status-text');
        if (textElement) textElement.innerHTML = message;
        
        return id;
    }
    
    remove(id) {
        const messageElement = this.activeMessages.get(id);
        if (!messageElement) return;
        
        messageElement.style.animation = 'statusFadeOut 0.3s ease-out forwards';
        setTimeout(() => {
            messageElement.parentNode?.removeChild(messageElement);
            this.activeMessages.delete(id);
        }, 300);
    }
    
    showProgress(message, current, total, type = 'progress') {
        const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
        const progressContent = `
            <div class="progress-container">
                <div class="progress-header">
                    <span class="progress-message">${message}</span>
                    <span class="progress-counter">${current}/${total} (${percentage}%)</span>
                </div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${percentage}%"></div></div>
            </div>`;

        // Return a unique ID so progress can be updated
        return this.show(progressContent, type, 0);
    }
    
    updateProgress(id, current, total, message = null) {
        const messageElement = document.getElementById(id);
        if (!messageElement) return false;
        
        const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
        const progressMessage = message || messageElement.querySelector('.progress-message')?.textContent || 'Processing';
        
        const progressContent = `
            <div class="progress-container">
                <div class="progress-header">
                    <span class="progress-message">${progressMessage}</span>
                    <span class="progress-counter">${current}/${total} (${percentage}%)</span>
                </div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${percentage}%"></div></div>
            </div>`;
        
        messageElement.innerHTML = progressContent;
        return true;
    }
    
    showStage(stage, description) {
        const stageMessage = `<div class="processing-stage"><div class="stage-name">${stage}</div><div class="stage-description">${description}</div></div>`;
        if (!this.stageMessage) this.stageMessage = this.show(stageMessage, 'progress');
        else this.update(this.stageMessage, stageMessage);
        return this.stageMessage;
    }
    
    showStats(stats) {
        const { elapsedTime, itemsPerSecond, cacheHits, totalItems, errors } = stats;
        const cacheHitRate = totalItems > 0 ? Math.round((cacheHits / totalItems) * 100) : 0;
        const statsMessage = `
            <div class="processing-stats">
                <div class="stats-item"><strong>Time:</strong> ${this.formatTime(elapsedTime)}</div>
                <div class="stats-item"><strong>Rate:</strong> ${itemsPerSecond} items/sec</div>
                <div class="stats-item"><strong>Cache:</strong> ${cacheHitRate}%</div>
                <div class="stats-item"><strong>Errors:</strong> ${errors}</div>
            </div>`;
        
        if (!this.statsMessage) this.statsMessage = this.show(statsMessage, 'info');
        else this.update(this.statsMessage, statsMessage);
        return this.statsMessage;
    }
    
    formatTime(ms) {
        if (ms < 1000) return `${ms}ms`;
        const seconds = Math.floor(ms / 1000);
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds}s`;
    }
    
    formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${Math.round(bytes / Math.pow(1024, i) * 100) / 100} ${sizes[i]}`;
    }
    
    formatPercentage(value, total, precision = 1) {
        if (total === 0) return '0%';
        return `${(value / total * 100).toFixed(precision)}%`;
    }
    
    showFileInfo(fileName, fileSize) {
        return this.show(`<strong>File loaded:</strong> ${fileName} (${this.formatFileSize(fileSize)})`, 'info');
    }
    
    showTestInfo(testName, description) {
        return this.show(`<strong>${testName}:</strong> ${description}`, 'info');
    }
    
    injectStyles() {
        const styleId = 'status-manager-styles';
        if (document.getElementById(styleId)) return;
        
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .spinner { width: 16px; height: 16px; border: 2px solid var(--color-primary, #3f51b5); border-radius: 50%; border-top-color: transparent; animation: spin 1s linear infinite; }
            @keyframes statusFadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
            @keyframes statusFadeOut { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(-10px); } }
            .status-message-container { display: flex; flex-direction: column; gap: 8px; margin: 0 auto 20px auto; position: static; width: 100%; max-width: 1200px; padding: 0 var(--space-8, 32px); box-sizing: border-box; }
            .processing-stage { display: flex; flex-direction: column; gap: 4px; }
            .stage-name { font-weight: 600; font-size: 15px; }
            .stage-description { font-size: 13px; opacity: 0.9; }
            .processing-stats { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; width: 100%; font-size: 13px; }
            .stats-item { display: flex; align-items: center; gap: 6px; }
            .stats-item strong { font-weight: 600; color: var(--color-gray-600, #666); }
            .current-exam { display: flex; flex-direction: column; gap: 4px; }
            .exam-label { font-size: 12px; color: var(--color-gray-600, #666); font-weight: 500; }
            .exam-value { font-weight: 600; font-family: var(--font-family-mono, monospace); font-size: 14px; }
            .exam-result { font-size: 13px; color: var(--color-success, #4caf50); font-weight: 500; margin-top: 2px; }
            .exam-error { font-size: 13px; color: var(--color-danger, #f44336); font-weight: 500; margin-top: 2px; }
            .progress-container { width: 100%; }
            .progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 14px; padding-right: 30px; }
            .progress-message { font-weight: 500; flex: 1; }
            .progress-counter { font-family: var(--font-family-mono, monospace); font-size: 13px; color: var(--color-gray-600, #666); flex-shrink: 0; }
            .progress-bar { width: 100%; height: 8px; background-color: var(--color-gray-200, #e0e0e0); border-radius: 4px; overflow: hidden; }
            .progress-fill { height: 100%; background: linear-gradient(90deg, var(--color-primary, #3f51b5), var(--color-primary-dark, #303f9f)); border-radius: 4px; transition: width 0.3s ease; min-width: 2px; }
            .progress-fill:empty { background: var(--color-primary, #3f51b5); }
            .current-exam.error .exam-value { color: var(--color-danger, #f44336); }
            .processing-complete { display: flex; align-items: center; gap: 12px; }
            .complete-icon { font-size: 20px; font-weight: bold; color: var(--color-success, #4caf50); background: var(--color-success-light, #e8f5e9); width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
            .complete-message { display: flex; flex-direction: column; gap: 4px; }
            .complete-title { font-weight: 600; font-size: 15px; }
            .complete-details { font-size: 13px; color: var(--color-gray-600, #666); display: flex; gap: 12px; }
        `;
        document.head.appendChild(style);
    }
}

const statusManager = new StatusManager();

// --- GLOBAL VARIABLES & STATE ---
let currentModel = localStorage.getItem('selectedModel') || 'retriever';
let availableModels = {};
let currentReranker = localStorage.getItem('selectedReranker') || 'medcpt';
let availableRerankers = {};
let allMappings = [];
let isUsingFallbackModels = false;
let summaryData = null;
let sortedMappings = [];
let currentPage = 1;
let pageSize = 100;
let sortBy = 'default';

// Track button state during model loading
let buttonsDisabledForLoading = true;

// --- BUTTON STATE MANAGEMENT ---
function disableActionButtons(reason = 'Models are loading...') {
    const buttons = [
        'runRandomDemoBtn', 
        'runFixedTestBtn', 
        'runProcessingBtn'
    ];
    
    buttons.forEach(buttonId => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = true;
            button.dataset.originalTitle = button.title || '';
            button.title = reason;
            button.classList.add('loading-disabled');
        }
    });
    
    // Also disable action cards
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.classList.add('loading-disabled');
        card.style.pointerEvents = 'none';
        card.dataset.originalTitle = card.title || '';
        card.title = reason;
    });
    
    buttonsDisabledForLoading = true;
}

function enableActionButtons() {
    const buttons = [
        'runRandomDemoBtn', 
        'runFixedTestBtn', 
        'runProcessingBtn'
    ];
    
    buttons.forEach(buttonId => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = false;
            button.title = button.dataset.originalTitle || '';
            button.classList.remove('loading-disabled');
        }
    });
    
    // Re-enable action cards
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.classList.remove('loading-disabled');
        card.style.pointerEvents = '';
        card.title = card.dataset.originalTitle || '';
    });
    
    buttonsDisabledForLoading = false;
}

// --- UTILITY & HELPER FUNCTIONS ---
function formatProcessingTime(ms) {
    return statusManager.formatTime(ms);
}

function formatFileSize(bytes) {
    return statusManager.formatFileSize(bytes);
}

function formatPercentage(value, total, precision = 1) {
    return statusManager.formatPercentage(value, total, precision);
}

function getBatchSize() {
    if (typeof window !== 'undefined' && window.ENV && window.ENV.NLP_BATCH_SIZE) {
        return parseInt(window.ENV.NLP_BATCH_SIZE, 10);
    }
    return 25; // Default batch size
}

function preventDefaults(e) { 
    e.preventDefault(); 
    e.stopPropagation();
}

function formatModelName(modelKey) {
    if (availableModels && availableModels[modelKey] && availableModels[modelKey].name) {
        return availableModels[modelKey].name;
    }
    const nameMap = {
        'default': 'BioLORD (Default)',
        'pubmed': 'PubMed',
        'biolord': 'BioLORD',
        'general': 'General',
        'experimental': 'Experimental'
    };
    return nameMap[modelKey] || modelKey.charAt(0).toUpperCase() + modelKey.slice(1);
}

function switchModel(modelKey) {
    if (!availableModels[modelKey] || availableModels[modelKey].status !== 'available') {
        console.warn(`Model ${modelKey} is not available.`);
        return;
    }
    currentModel = modelKey;
    localStorage.setItem('selectedModel', modelKey);
    document.querySelectorAll('.model-toggle').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`${modelKey}ModelBtn`)?.classList.add('active');
    statusManager.show(`Switched to ${formatModelName(modelKey)} model`, 'success', 3000);
    
    // Trigger workflow check if it exists
    if (window.workflowCheckFunction) {
        window.workflowCheckFunction();
    }
}


window.addEventListener('DOMContentLoaded', function() {
    // --- CENTRALIZED SOURCE NAMES ---
    function getSourceNames() {
        return {
            'SouthIsland-SIRS COMRAD': 'SIRS (Mid-Upper Sth Island)',
            'Central-Phillips': 'Central',
            'Southern-Karisma': 'Southern District',
            'Auckland Metro-Agfa': 'Auckland Metro',
            'Central-Philips': 'Central'
        };
    }

    // --- API & CONFIGURATION ---
    function detectApiUrls() {
        const hostname = window.location.hostname;
        const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
        const isRender = hostname.endsWith('.onrender.com');
        const isPagesDev = hostname.endsWith('.pages.dev');
        const isHNZDomain = hostname === 'hnzradtools.nz' || hostname.endsWith('.hnzradtools.nz');

        
        let apiBase, mode;
        
        if (isLocalhost) {
            apiBase = 'http://localhost:10000';
            mode = 'LOCAL';
        } else if (isRender) {
            apiBase = 'https://radiology-api-staging.onrender.com';
            mode = 'RENDER_STAGING';
        } else if (isPagesDev || isHNZDomain) {
            apiBase = 'https://radiology-api-staging.onrender.com';  
            mode = isHNZDomain ? 'HNZ_DOMAIN' : 'PAGES_DEV';
        } else {
            apiBase = 'https://radiology-api-staging.onrender.com';  // Default fallback
            mode = 'PROD';
        }
        
        return { baseUrl: apiBase, mode: mode };
    }
    
    const apiConfig = detectApiUrls();
    const BATCH_API_URL = `${apiConfig.baseUrl}/parse_batch`;
    const INDIVIDUAL_API_URL = `${apiConfig.baseUrl}/parse_enhanced`;
    const MODELS_URL = `${apiConfig.baseUrl}/models`;
    const HEALTH_URL = `${apiConfig.baseUrl}/health`;
    
    // Processing threshold: use individual API for datasets under 500 items
    const BATCH_THRESHOLD = 500;
    
    console.log(`Frontend running in ${apiConfig.mode} mode. API base: ${apiConfig.baseUrl}`);

    // --- DOM ELEMENTS ---
    const mainCard = document.querySelector('.main-card');
    const demosSection = document.getElementById('demosSection');
    
    // Create file input element if it doesn't exist
    let fileInput = document.getElementById('fileInput');
    if (!fileInput) {
        fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.id = 'fileInput';
        fileInput.accept = '.json';
        fileInput.style.display = 'none';
        document.body.appendChild(fileInput);
    }
    const resultsSection = document.getElementById('resultsSection');
    const resultsBody = document.getElementById('resultsBody');
    const sanityButton = document.getElementById('sanityTestBtn');
    const randomSampleButton = document.getElementById('randomSampleDemoBtn');
    
    // Config editor elements
    const editConfigButton = document.getElementById('editConfigBtn');
    const configEditorModal = document.getElementById('configEditorModal');
    const configEditor = document.getElementById('configEditor');
    const configStatus = document.getElementById('configStatus');
    const reloadConfigBtn = document.getElementById('reloadConfigBtn');
    const saveConfigBtn = document.getElementById('saveConfigBtn');
    const closeConfigEditorModal = document.getElementById('closeConfigEditorModal');
    const closeConfigEditorBtn = document.getElementById('closeConfigEditorBtn');

    // --- CORE INITIALIZATION ---
    async function testApiConnectivity() {
        try {
            const response = await fetch(HEALTH_URL, { method: 'GET' });
            if (response.ok) console.log('✓ API connectivity test passed');
            else console.warn('⚠ API health check failed:', response.status);
        } catch (error) {
            console.error('✗ API connectivity test failed:', error);
        }
    }

    async function warmupAPI() {
        let warmupMessageId = null;
        try {
            console.log('🔥 Warming up API...');
            const warmupStart = performance.now();
            warmupMessageId = statusManager.show('🔥 Warming up processing engine...', 'info');
            
            const response = await fetch(`${apiConfig.baseUrl}/warmup`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: AbortSignal.timeout(15000)
            });
            
            if (response.ok) {
                const result = await response.json();
                const warmupTime = performance.now() - warmupStart;
                console.log(`✅ API warmed up successfully in ${warmupTime.toFixed(0)}ms`);
                console.log('Warmup details:', result.components);
                
                // Clear the warming up message and show success
                if (warmupMessageId) statusManager.remove(warmupMessageId);
                statusManager.show(`✅ Processing engine ready (${warmupTime.toFixed(0)}ms)`, 'success', 6000);
                
                // Wait 2 seconds to let users see the success message before other status updates
                await new Promise(resolve => setTimeout(resolve, 2000));
                enableActionButtons(); // Enable buttons after successful warmup
            } else {
                throw new Error(`Warmup failed with status ${response.status}`);
            }
        } catch (error) {
            console.warn('⚠️ API warmup failed (processing will still work, but first request may be slower):', error);
            // Clear the warming up message and show warning
            if (warmupMessageId) statusManager.remove(warmupMessageId);
            statusManager.show('⚠️ Engine warmup incomplete - first processing may take longer', 'warning', 5000);
        }
    }

    async function loadAvailableModels(retryCount = 0, skipWarmupMessages = false) {
        let loadingMessageId = null;
        try {
            console.log(`Loading available models (attempt ${retryCount + 1})`);
            
            // Show loading message on first attempt
            if (retryCount === 0) {
                loadingMessageId = statusManager.show('Loading available models...', 'info');
            }
            
            // Use AbortSignal for timeout instead of timeout property
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);
            
            const response = await fetch(MODELS_URL, { 
                method: 'GET', 
                signal: controller.signal 
            });
            
            clearTimeout(timeoutId);
            if (response.ok) {
                const modelsData = await response.json();
                availableModels = modelsData.models || {};
                
                // Validate that models were actually loaded
                if (Object.keys(availableModels).length === 0) {
                    throw new Error('No models received from API');
                }
                
                // Use saved selection if available, otherwise fallback to default
                const savedModel = localStorage.getItem('selectedModel');
                if (savedModel && availableModels[savedModel]) {
                    currentModel = savedModel;
                } else {
                    currentModel = modelsData.default_model || 'retriever';
                }
                
                availableRerankers = modelsData.rerankers || {};
                // Use saved selection if available, otherwise fallback to default
                const savedReranker = localStorage.getItem('selectedReranker');
                if (savedReranker && availableRerankers[savedReranker]) {
                    currentReranker = savedReranker;
                } else {
                    currentReranker = modelsData.default_reranker || 'medcpt';
                }
                console.log('✓ Available models loaded:', Object.keys(availableModels));
                console.log('✓ Available rerankers loaded:', availableRerankers); // Added console.log for rerankers
                
                // Mark that we're not using fallback models
                isUsingFallbackModels = false;
                
                // Build UI immediately after data loads (before status messages)
                buildModelSelectionUI();
                buildRerankerSelectionUI();
                
                
                
                // Refresh workflow completion check
                if (window.workflowCheckFunction) {
                    window.workflowCheckFunction();
                }
                
                // Clear loading message after UI is built
                if (loadingMessageId) {
                    statusManager.remove(loadingMessageId);
                    loadingMessageId = null;
                }
                
                // Show success message
                statusManager.show('✓ Models loaded successfully', 'success', 3000);
                
                // Warm up the API after models are loaded
                if (!skipWarmupMessages) {
                    warmupAPI();
                }
            } else {
                throw new Error(`API responded with ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            // Clear loading message on error
            if (loadingMessageId) {
                statusManager.remove(loadingMessageId);
                loadingMessageId = null;
            }
            
            const isAbortError = error.name === 'AbortError';
            const errorType = isAbortError ? 'timeout' : 'network error';
            
            console.error(`✗ Failed to load models (attempt ${retryCount + 1}) - ${errorType}:`, error);
            
            if (retryCount < 2) {
                const retryDelay = (retryCount + 1) * 2;
                console.log(`Retrying in ${retryDelay} seconds...`);
                statusManager.show(`⚠️ Model loading failed (${errorType}), retrying in ${retryDelay}s...`, 'warning', retryDelay * 1000);
                setTimeout(() => loadAvailableModels(retryCount + 1, skipWarmupMessages), retryDelay * 1000);
            } else {
                console.warn('⚠ All retry attempts failed, using fallback models');
                statusManager.show('⚠️ Could not load models from server, using fallback models', 'warning', 5000);
                useFallbackModels();
            }
        }
    }
    
    function useFallbackModels() {
        availableModels = {
            'retriever': { name: 'BioLORD', status: 'available', description: 'Advanced biomedical language model for retrieval' }
        };
        availableRerankers = {
            'medcpt': { name: 'MedCPT (HuggingFace)', status: 'available', description: 'NCBI Medical Clinical Practice Text cross-encoder', type: 'huggingface' },
            'gpt-4o-mini': { name: 'GPT-4o Mini', status: 'unknown', description: 'Fast and cost-effective OpenAI model', type: 'openrouter' },
            'claude-3-haiku': { name: 'Claude 3 Haiku', status: 'unknown', description: 'Fast Anthropic model optimized for speed', type: 'openrouter' },
            'gemini-2.5-flash-lite': { name: 'Gemini 2.5 Flash Lite', status: 'unknown', description: 'Google\'s lightweight Gemini model', type: 'openrouter' }
        };
        currentModel = 'retriever';
        currentReranker = 'medcpt';
        isUsingFallbackModels = true; // Mark that we're using fallback models
        console.log('Using fallback models with all reranker options');
        
        buildModelSelectionUI();
        buildRerankerSelectionUI();
        
        // Update button states for fallback models - keep limited functionality
        disableActionButtons('Limited functionality with fallback models');
        
        // Refresh workflow completion check
        if (window.workflowCheckFunction) {
            window.workflowCheckFunction();
        }
        
        // Show that fallback models are being used
        statusManager.show('ℹ️ Using offline fallback models - some features may be limited', 'info', 5000);
    }
    
    function buildModelSelectionUI() {
        const modelContainer = document.querySelector('.model-selection-container');
        if (!modelContainer) {
            console.error('❌ Model selection container not found in HTML');
            return;
        }
        
        modelContainer.innerHTML = '';
        
        // Add reload button if using fallback models
        if (isUsingFallbackModels) {
            const reloadWrapper = document.createElement('div');
            reloadWrapper.style.cssText = 'margin-bottom: 15px; text-align: center;';
            
            const reloadBtn = document.createElement('button');
            reloadBtn.className = 'button secondary';
            reloadBtn.innerHTML = '🔄 Retry Loading Models';
            reloadBtn.style.cssText = 'font-size: 14px; padding: 8px 16px;';
            reloadBtn.onclick = () => {
                statusManager.clearAll();
                disableActionButtons('Retrying model loading...');
                loadAvailableModels(0, true);
            };
            
            reloadWrapper.appendChild(reloadBtn);
            modelContainer.appendChild(reloadWrapper);
        }
        
        Object.entries(availableModels).forEach(([modelKey, modelInfo]) => {
            const modelWrapper = document.createElement('div');
            modelWrapper.className = 'model-wrapper';
            modelWrapper.style.cssText = 'display: flex; align-items: center; gap: 15px; margin-bottom: 10px;';
            
            const button = document.createElement('button');
            button.className = `button secondary model-toggle ${modelKey === currentModel ? 'active' : ''}`;
            button.id = `${modelKey}ModelBtn`;
            button.dataset.model = modelKey;
            button.style.cssText = 'min-width: 150px; flex-shrink: 0;';
            
            const statusText = modelInfo.status === 'available' ? '' : ' (Unavailable)';
            button.innerHTML = `<span class="model-name">${formatModelName(modelKey)}${statusText}</span>`;
            
            const description = document.createElement('span');
            description.className = 'model-description';
            description.style.cssText = 'font-size: 0.85em; color: #666; flex: 1;';
            description.textContent = modelInfo.description || '';
            
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
        });
    }
    
    function buildRerankerSelectionUI() {
        const rerankerContainer = document.querySelector('.reranker-selection-container');
        if (!rerankerContainer) {
            console.error('❌ Reranker selection container not found in HTML');
            return;
        }
        
        rerankerContainer.innerHTML = '';
        
        // Sort rerankers to put MedCPT first, then others alphabetically
        const sortedRerankers = Object.entries(availableRerankers).sort(([keyA], [keyB]) => {
            if (keyA === 'medcpt') return -1;  // MedCPT goes first
            if (keyB === 'medcpt') return 1;   // MedCPT goes first
            return keyA.localeCompare(keyB);   // Others alphabetically
        });
        
        sortedRerankers.forEach(([rerankerKey, rerankerInfo]) => {
            const rerankerWrapper = document.createElement('div');
            rerankerWrapper.className = 'reranker-wrapper';
            rerankerWrapper.style.cssText = 'display: flex; align-items: center; gap: 15px; margin-bottom: 10px;';
            
            const button = document.createElement('button');
            button.className = `button reranker-toggle ${rerankerKey === currentReranker ? 'active' : ''}`;
            button.id = `${rerankerKey}RerankerBtn`;
            button.dataset.reranker = rerankerKey;
            button.style.cssText = 'min-width: 180px; flex-shrink: 0;';
            
            const statusText = rerankerInfo.status === 'available' ? '' : ' (Unavailable)';
            const typeInfo = rerankerInfo.type === 'openrouter' ? ' 🌐' : ' 🤗';
            button.innerHTML = `<span class="reranker-name">${formatRerankerName(rerankerKey)}${typeInfo}${statusText}</span>`;
            
            const description = document.createElement('span');
            description.className = 'reranker-description';
            description.style.cssText = 'font-size: 0.85em; color: #666; flex: 1;';
            description.textContent = rerankerInfo.description || '';
            
            if (rerankerInfo.status !== 'available') {
                button.disabled = true;
                button.title = `${rerankerInfo.name} is currently unavailable`;
                description.style.color = '#999';
            } else {
                button.addEventListener('click', () => switchReranker(rerankerKey));
            }
            
            rerankerWrapper.appendChild(button);
            rerankerWrapper.appendChild(description);
            rerankerContainer.appendChild(rerankerWrapper);
        });
    }
    
    function formatRerankerName(rerankerKey) {
        if (availableRerankers && availableRerankers[rerankerKey] && availableRerankers[rerankerKey].name) {
            return availableRerankers[rerankerKey].name;
        }
        const nameMap = {
            'medcpt': 'MedCPT (HuggingFace)',
            'gpt-4o-mini': 'GPT-4o Mini',
            'claude-3-haiku': 'Claude 3 Haiku', 
            'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite'
        };
        return nameMap[rerankerKey] || rerankerKey.charAt(0).toUpperCase() + rerankerKey.slice(1);
    }
    
    function switchReranker(rerankerKey) {
        if (!availableRerankers[rerankerKey] || availableRerankers[rerankerKey].status !== 'available') {
            console.warn(`Reranker ${rerankerKey} is not available.`);
            return;
        }
        currentReranker = rerankerKey;
        localStorage.setItem('selectedReranker', rerankerKey);
        document.querySelectorAll('.reranker-toggle').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`${rerankerKey}RerankerBtn`)?.classList.add('active');
        // Show reranker status message in local area instead of global status
        const rerankerStatusEl = document.getElementById('rerankerStatusMessage');
        if (rerankerStatusEl) {
            rerankerStatusEl.style.display = 'block';
            rerankerStatusEl.style.background = '#d4edda';
            rerankerStatusEl.style.color = '#155724';
            rerankerStatusEl.style.border = '1px solid #c3e6cb';
            rerankerStatusEl.textContent = `✓ Switched to ${formatRerankerName(rerankerKey)} reranker`;
            
            // Hide the message after 3 seconds
            setTimeout(() => {
                if (rerankerStatusEl) {
                    rerankerStatusEl.style.display = 'none';
                }
            }, 3000);
        }
        
        // Trigger workflow check if it exists
        if (window.workflowCheckFunction) {
            window.workflowCheckFunction();
        }
    }
    
    // --- MOBILE UX HELPERS ---
    function scrollToModelSelection() {
        // Only auto-scroll on mobile devices
        if (window.innerWidth <= 768) {
            setTimeout(() => {
                const modelStep = document.getElementById('retrieverStep');
                if (modelStep) {
                    modelStep.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'start'
                    });
                }
            }, 300); // Small delay to let the workflow section animate in
        }
    }
    
    // --- EVENT LISTENERS ---
    function setupEventListeners() {
        // Hamburger menu functionality
        const hamburgerToggle = document.getElementById('hamburgerToggle');
        const hamburgerDropdown = document.getElementById('hamburgerDropdown');
        
        if (hamburgerToggle && hamburgerDropdown) {
            hamburgerToggle.addEventListener('click', function() {
                const isHidden = hamburgerDropdown.classList.contains('hidden');
                if (isHidden) {
                    hamburgerDropdown.classList.remove('hidden');
                } else {
                    hamburgerDropdown.classList.add('hidden');
                }
            });
            
            // Close dropdown when clicking outside
            document.addEventListener('click', function(event) {
                if (!hamburgerToggle.contains(event.target) && !hamburgerDropdown.contains(event.target)) {
                    hamburgerDropdown.classList.add('hidden');
                }
            });
        }
        
        // Upload section drag-and-drop functionality removed - HTML elements no longer exist

        document.getElementById('newUploadBtn')?.addEventListener('click', startNewUpload);
        document.getElementById('exportMappingsBtn')?.addEventListener('click', exportResults);
        
        // Note: Demo buttons are now handled in the workflow section
        
        // New homepage workflow event listeners
        setupHomepageWorkflow();
        
        // Upload config functionality removed - Edit Config handles all config management
        
        // Config editor event listeners
        const editConfigButton = document.getElementById('editConfigBtn');
        const closeConfigEditorModal = document.getElementById('closeConfigEditorModal');
        const closeConfigEditorBtn = document.getElementById('closeConfigEditorBtn');
        const reloadConfigBtn = document.getElementById('reloadConfigBtn');
        const saveConfigBtn = document.getElementById('saveConfigBtn');
        const configEditorModal = document.getElementById('configEditorModal');
        
        if (editConfigButton) {
            editConfigButton.addEventListener('click', openConfigEditor);
        }
        
        if (closeConfigEditorModal) {
            closeConfigEditorModal.addEventListener('click', closeConfigEditor);
        }
        if (closeConfigEditorBtn) {
            closeConfigEditorBtn.addEventListener('click', closeConfigEditor);
        }
        if (reloadConfigBtn) {
            reloadConfigBtn.addEventListener('click', loadCurrentConfig);
        }
        if (saveConfigBtn) {
            saveConfigBtn.addEventListener('click', saveConfig);
        }
        
        // Close modal when clicking outside
        if (configEditorModal) {
            configEditorModal.addEventListener('click', (e) => {
                if (e.target === configEditorModal) {
                    closeConfigEditor();
                }
            });
        }
        
        document.getElementById('closeModalBtn')?.addEventListener('click', closeModal);
        document.getElementById('consolidationModal')?.addEventListener('click', (e) => e.target.id === 'consolidationModal' && closeModal());
        
        
        document.getElementById('viewToggleBtn')?.addEventListener('click', toggleView);
        document.getElementById('consolidatedSearch')?.addEventListener('input', filterConsolidatedResults);
        document.getElementById('consolidatedSort')?.addEventListener('change', sortConsolidatedResults);
        
        document.getElementById('prevPageBtn')?.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                displayCurrentPage();
            }
        });
        
        document.getElementById('nextPageBtn')?.addEventListener('click', () => {
            const totalPages = Math.ceil(sortedMappings.length / pageSize);
            if (currentPage < totalPages) {
                currentPage++;
                displayCurrentPage();
            }
        });
        
        document.getElementById('pageSizeSelector')?.addEventListener('change', (e) => {
            pageSize = parseInt(e.target.value);
            currentPage = 1; 
            displayCurrentPage();
        });
        
        document.getElementById('tableSortBy')?.addEventListener('change', (e) => {
            sortBy = e.target.value;
            currentPage = 1; 
            sortAndDisplayResults();
        });
    }

    // --- UPLOAD INTERFACE CONTROL ---
    // Upload interface functions removed - HTML sections no longer exist
    
    function startNewUpload() {
        // Hide all sections and return to initial view
        resultsSection.style.display = 'none';
        const advancedSection = document.getElementById('advancedSection');
        if (advancedSection) advancedSection.style.display = 'none';
        const modelSettingsSection = document.getElementById('modelSettingsSection');
        if (modelSettingsSection) modelSettingsSection.style.display = 'none';
        
        // Show hero section with action cards
        const heroSection = document.querySelector('.hero-section');
        const workflowSection = document.getElementById('workflowSection');
        if (heroSection) heroSection.style.display = 'block';
        if (workflowSection) workflowSection.style.display = 'none'; // Will be shown when path is selected
        
        // Show main card
        mainCard.style.display = 'block';
        statusManager.clearAll();
        fileInput.value = '';
        allMappings = [];
        summaryData = null;
        sortedMappings = [];
        currentPage = 1;
        pageSize = 100;
        sortBy = 'default';
        document.getElementById('paginationControls').style.display = 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // --- CORE PROCESSING FUNCTIONS ---
    async function processExams(codes, jobName) {
        const totalCodes = codes.length;
        
        if (totalCodes >= BATCH_THRESHOLD) {
            // Use batch processing for large datasets
            statusManager.show(`Large dataset detected (${totalCodes} items). Using batch processing for optimal performance.`, 'info', 3000);
            await processBatch(codes, jobName);
        } else {
            // Use individual processing for smaller datasets
            statusManager.show(`Small dataset detected (${totalCodes} items). Using individual processing for faster results.`, 'info', 3000);
            await processIndividual(codes, jobName);
        }
    }

    async function processFile(file) {
        disableActionButtons('Processing uploaded file...');
        if (!file.name.endsWith('.json')) {
            statusManager.show('Please upload a valid JSON file.', 'error', 5000);
            enableActionButtons(); // Re-enable if file type is wrong
            return;
        }
        statusManager.clearAll();
        statusManager.showFileInfo(file.name, file.size);
        resultsSection.style.display = 'none';
        
        const reader = new FileReader();
        reader.onload = async function(e) {
            try {
                const codes = JSON.parse(e.target.result);
                if (!Array.isArray(codes) || codes.length === 0) {
                    throw new Error('JSON file is empty or not in the correct array format.');
                }
                console.log(`Processing ${codes.length} exam records...`);
                await processExams(codes, `File: ${file.name}`);
            } catch (error) {
                statusManager.show(`Error processing file: ${error.message}`, 'error', 0);
            } finally {
                enableActionButtons(); // Re-enable buttons after file processing
            }
        };
        reader.readAsText(file);
    }
    
    async function runSanityTest() {
        disableActionButtons('Running sanity test...');
        let statusId = null;

        try {
            // Hide main content during processing
            if (mainCard) mainCard.style.display = 'none';
            
            statusManager.clearAll();
            const modelDisplayName = formatModelName(currentModel);
            const rerankerDisplayName = formatRerankerName(currentReranker);
            statusId = statusManager.show(`Running 100-exam sanity test with ${modelDisplayName} → ${rerankerDisplayName}...`, 'progress');

            const response = await fetch('./backend/core/hundred_test.json');
            if (!response.ok) throw new Error(`Could not load test file: ${response.statusText}`);
            const codes = await response.json();
            
            await processExams(codes, "94 Exam Test Suite");

        } catch (error) {
            console.error('Sanity test failed:', error);
            statusManager.show(`❌ Sanity Test Failed: ${error.message}`, 'error', 0);
            // Show main card again on error
            if (mainCard) mainCard.style.display = 'block';
        } finally {
            if (statusId) statusManager.remove(statusId);
            if (sanityButton) {
                 sanityButton.disabled = false;
                 sanityButton.innerHTML = '100 Exam Test Suite';
            }
            enableActionButtons(); // Re-enable buttons after processing
        }
    }

    async function runRandomSampleDemo() {
        disableActionButtons('Processing random sample demo...');
        let statusId = null;

        try {
            // Hide main content during processing
            if (mainCard) mainCard.style.display = 'none';
            
            statusManager.clearAll();
            const modelDisplayName = formatModelName(currentModel);
            const rerankerDisplayName = formatRerankerName(currentReranker);
            
            // Start with a progress bar (we'll update the total once we know it)
            statusId = statusManager.showProgress(`Running random sample demo with ${modelDisplayName} → ${rerankerDisplayName}`, 0, 100);

            let pollingActive = true;
            let batchId = null;
            
            // Start aggressive polling function
            const pollProgress = async () => {
                if (!pollingActive || !batchId) {
                    // If we don't have batch_id yet, keep trying
                    if (pollingActive) {
                        setTimeout(pollProgress, 100);
                    }
                    return;
                }
                
                try {
                    console.log(`Polling progress for batch_id: ${batchId}`);
                    const progressResponse = await fetch(`${apiConfig.baseUrl}/batch_progress/${batchId}`);
                    console.log(`Progress response status: ${progressResponse.status}`);
                    
                    if (progressResponse.ok && pollingActive) {
                        const progressData = await progressResponse.json();
                        console.log('Progress data:', progressData);
                        
                        const percentage = progressData.percentage || 0;
                        const processed = progressData.processed || 0;
                        const total = progressData.total || 100;
                        const success = progressData.success || 0;
                        const errors = progressData.errors || 0;
                        
                        if (statusId) {
                            statusManager.updateProgress(statusId, processed, total, 
                                `Random sample demo (${percentage}% - ${success} success, ${errors} errors)`);
                        }
                        
                        // Continue polling if not complete
                        if (percentage < 100 && processed < total && pollingActive) {
                            setTimeout(pollProgress, 500); // Poll every 500ms during processing
                        } else {
                            console.log('Processing complete, stopping polling');
                            pollingActive = false;
                        }
                    } else if (progressResponse.status === 404) {
                        // Progress file not found yet, keep trying
                        if (pollingActive) {
                            setTimeout(pollProgress, 500);
                        }
                    }
                } catch (progressError) {
                    console.log('Progress polling error:', progressError);
                    if (pollingActive) {
                        setTimeout(pollProgress, 1000); // Slower retry on error
                    }
                }
            };

            // Start polling immediately - even before we get the batch_id
            setTimeout(pollProgress, 100);
            
            // Set a maximum polling duration (2 minutes for 100 exams)
            setTimeout(() => {
                console.log('Maximum polling duration reached, stopping');
                pollingActive = false;
            }, 120000);

            // Check if secondary pipeline should be enabled
            const enableSecondary = document.getElementById('enableSecondaryPipeline')?.checked || false;
            
            // Start the API request
            // Get sample size from user input
            const sampleSizeInput = document.getElementById('sampleSizeInput');
            const sampleSize = parseInt(sampleSizeInput.value) || 100;
            
            const response = await fetch(`${apiConfig.baseUrl}/demo_random_sample`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: currentModel,
                    reranker: currentReranker,
                    enable_secondary_pipeline: enableSecondary,
                    sample_size: sampleSize
                })
            });
            
            if (!response.ok) {
                pollingActive = false;
                throw new Error(`Random sample demo failed: ${response.statusText}`);
            }

            const result = await response.json();
            
            if (result.error) {
                pollingActive = false;
                throw new Error(result.error);
            }

            // Set the batch_id so polling can start working
            if (result.batch_id) {
                batchId = result.batch_id;
                console.log(`Got batch_id: ${batchId}, polling should now be active`);
            }

            // Wait for processing to complete (polling will handle progress updates)
            // The API response comes back when processing is done
            console.log('API response received, processing should be complete');
            pollingActive = false;

            // Show processing completion
            if (statusId) statusManager.remove(statusId);
            statusId = statusManager.show(`✅ Processing completed! ${result.processing_stats.successful || result.processing_stats.processed_successfully || 'Unknown'} items processed`, 'success', 2000);
            
            // Small delay to show completion message
            await new Promise(resolve => setTimeout(resolve, 2000));

            // Fetch and display the results from R2
            if (statusId) statusManager.remove(statusId);
            statusId = statusManager.show('Fetching results for display...', 'progress');
            
            if (result.r2_url) {
                try {
                    const resultsResponse = await fetch(result.r2_url);
                    if (resultsResponse.ok) {
                        const resultsData = await resultsResponse.json();
                        console.log('R2 fetched resultsData:', resultsData); // Added for debugging
                        
                        // Handle multiple possible data structures from R2
                        const results = resultsData.results || resultsData;
                        if (results && results.length > 0) {
                            if (statusId) statusManager.remove(statusId);
                            statusId = statusManager.show('Analyzing results and generating display...', 'progress');
                            
                            // Map the R2 results to the expected flat structure
                            const mappedResults = results.map(item => {
                                // Use backend structure directly
                                return {
                                    data_source: item.input?.DATA_SOURCE || item.input?.data_source || item.output?.data_source,
                                    modality_code: item.input?.MODALITY_CODE || item.input?.modality_code || item.output?.modality_code,
                                    exam_code: item.input?.EXAM_CODE || item.input?.exam_code || item.output?.exam_code,
                                    exam_name: item.input?.EXAM_NAME || item.input?.exam_name || item.output?.exam_name,
                                    clean_name: item.status === 'success' ? item.output?.clean_name : `ERROR: ${item.error}`,
                                    snomed: item.status === 'success' ? item.output?.snomed || {} : {},
                                    components: item.status === 'success' ? item.output?.components || {} : {},
                                    all_candidates: item.status === 'success' ? item.output?.all_candidates || [] : [],
                                    ambiguous: item.status === 'success' ? item.output?.ambiguous : false,
                                    secondary_pipeline_applied: item.status === 'success' ? item.output?.secondary_pipeline_applied || false : false,
                                    secondary_pipeline_details: item.status === 'success' ? item.output?.secondary_pipeline_details : undefined
                                };
                            });
                            
                            // Set global variables to display the results
                            allMappings = mappedResults;
                            updatePageTitle(`Random Sample Demo (${result.processing_stats.sample_size || result.processing_stats.total_processed} items)`);
                            
                            // Use runAnalysis to properly display results UI
                            try {
                                runAnalysis(allMappings);
                                
                                const successMessage = `✅ Random sample demo completed! ${result.processing_stats?.processed_successfully || result.processing_stats.successful || 'Unknown'} items processed`;
                                statusManager.show(successMessage, 'success', 5000);
                                if (mainCard) mainCard.style.display = 'block'; // Ensure main content is visible after successful analysis
                            } catch (analysisError) {
                                console.error('Error during results analysis:', analysisError);
                                statusManager.show('❌ Error displaying results', 'error', 5000);
                                if (mainCard) mainCard.style.display = 'block';
                            }
                        } else {
                            console.log('R2 data structure:', resultsData);
                            throw new Error(`No results found in R2 data. Structure: ${JSON.stringify(Object.keys(resultsData || {}))}`);
                        }
                    } else {
                        throw new Error(`Failed to fetch results: ${resultsResponse.statusText}`);
                    }
                } catch (fetchError) {
                    console.error('Failed to fetch results from R2:', fetchError);
                    if (statusId) statusManager.remove(statusId);
                    
                    // If the fetch fails, provide a direct link as a fallback
                    const successMessage = `✅ Random sample demo completed! ${result.processing_stats.successful} items processed`;
                    const urlMessage = `<br><a href="${result.r2_url}" target="_blank" style="color: #4CAF50; text-decoration: underline;">View Results on R2</a>`;
                    statusManager.show(successMessage + urlMessage, 'success', 10000);
                }
            } else {
                if (statusId) statusManager.remove(statusId);
                statusManager.show('✅ Demo completed but no results URL available', 'warning', 5000);
            }

        } catch (error) {
            console.error('Random sample demo failed:', error);
            if (statusId) statusManager.remove(statusId);
            statusManager.show(`❌ Random Sample Demo Failed: ${error.message}`, 'error', 0);
            // Show main card again on error
            if (mainCard) mainCard.style.display = 'block';
        } finally {
            if (randomSampleButton) {
                randomSampleButton.disabled = false;
                randomSampleButton.innerHTML = 'Random Sample Demo';
            }
            enableActionButtons(); // Re-enable buttons after processing
        }
    }

    // Config upload functionality removed - Edit Config handles all config management

    // --- CONFIG EDITOR FUNCTIONS ---
    
    async function openConfigEditor() {
        if (configEditorModal) {
            configEditorModal.style.display = 'block';
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
            await loadCurrentConfig();
        }
    }
    
    function closeConfigEditor() {
        if (configEditorModal) {
            configEditorModal.style.display = 'none';
            document.body.style.overflow = 'auto'; // Restore scrolling
        }
    }
    
    async function loadCurrentConfig() {
        try {
            if (reloadConfigBtn) {
                reloadConfigBtn.disabled = true;
                reloadConfigBtn.innerHTML = '🔄 Loading...';
            }
            
            configStatus.textContent = 'Loading...';
            configEditor.value = 'Loading configuration from R2...';
            
            const response = await fetch(`${apiConfig.baseUrl}/config/current`, {
                method: 'GET'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Failed to load config: ${response.statusText}`);
            }
            
            const result = await response.json();
            configEditor.value = result.config_yaml;
            configStatus.textContent = `Loaded at ${new Date(result.timestamp).toLocaleTimeString()}`;
            
        } catch (error) {
            console.error('Failed to load config:', error);
            configEditor.value = `# Error loading configuration:\n# ${error.message}\n\n# Please try reloading or check the server logs.`;
            configStatus.textContent = 'Error loading config';
            statusManager.show(`❌ Failed to load config: ${error.message}`, 'error', 5000);
        } finally {
            if (reloadConfigBtn) {
                reloadConfigBtn.disabled = false;
                reloadConfigBtn.innerHTML = '🔄 Reload';
            }
        }
    }
    
    async function saveConfig() {
        try {
            if (saveConfigBtn) {
                saveConfigBtn.disabled = true;
                saveConfigBtn.innerHTML = '💾 Saving...';
            }
            
            const configYamlContent = configEditor.value;
            
            if (!configYamlContent.trim()) {
                statusManager.show('Configuration cannot be empty', 'error', 5000);
                return;
            }
            
            configStatus.textContent = 'Saving...';
            
            const response = await fetch(`${apiConfig.baseUrl}/config/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    config_yaml: configYamlContent
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Save failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            configStatus.textContent = `Saved at ${new Date(result.timestamp).toLocaleTimeString()}`;
            
            statusManager.show('✓ Config saved successfully. Cache rebuild initiated in the background.', 'success', 8000);
            
        } catch (error) {
            console.error('Failed to save config:', error);
            configStatus.textContent = 'Error saving config';
            statusManager.show(`❌ Failed to save config: ${error.message}`, 'error', 10000);
        } finally {
            if (saveConfigBtn) {
                saveConfigBtn.disabled = false;
                saveConfigBtn.innerHTML = '💾 Save';
            }
        }
    }

    async function processBatch(codes, jobName) {
        allMappings = [];
        const totalCodes = codes.length;
        // Note: getBatchSize() no longer used since we send everything at once
        let progressId = null;

        try {
            // Send all exams in one request - let backend handle chunking internally
            const allExams = codes.map(code => ({
                exam_name: code.EXAM_NAME,
                modality_code: code.MODALITY_CODE,
                data_source: code.DATA_SOURCE,
                exam_code: code.EXAM_CODE
            }));
            
            progressId = statusManager.showProgress(`Processing ${jobName}`, 0, totalCodes);

            const response = await fetch(BATCH_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ exams: allExams, model: currentModel, reranker: currentReranker })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Batch API failed: ${errorText}`);
            }

            const batchResult = await response.json();
            console.log('Backend response:', batchResult);

            // If we have a batch_id, poll for progress
            if (batchResult.batch_id && progressId) {
                // Poll for progress updates
                const pollProgress = async () => {
                    try {
                        const progressResponse = await fetch(`${apiConfig.baseUrl}/batch_progress/${batchResult.batch_id}`);
                        if (progressResponse.ok) {
                            const progressData = await progressResponse.json();
                            const percentage = progressData.percentage || 0;
                            const processed = progressData.processed || 0;
                            const total = progressData.total || totalCodes;
                            const success = progressData.success || 0;
                            const errors = progressData.errors || 0;
                            
                            statusManager.updateProgress(progressId, processed, total, 
                                `Processing ${jobName} (${percentage}% - ${success} success, ${errors} errors)`);
                            
                            // Continue polling if not complete
                            if (percentage < 100 && processed < total) {
                                setTimeout(pollProgress, 1000); // Poll every second
                            } else {
                                statusManager.updateProgress(progressId, total, total, 
                                    `Completed processing ${jobName} (${success} success, ${errors} errors)`);
                            }
                        } else {
                            // Progress file not found - processing likely complete
                            statusManager.updateProgress(progressId, totalCodes, totalCodes, 
                                `Completed processing ${jobName}`);
                        }
                    } catch (progressError) {
                        console.log('Progress polling ended:', progressError.message);
                        // Don't throw error, just complete the progress
                        statusManager.updateProgress(progressId, totalCodes, totalCodes, 
                            `Completed processing ${jobName}`);
                    }
                };
                
                // Start polling after a brief delay
                setTimeout(pollProgress, 500);
                
                // Wait a bit for initial progress updates
                await new Promise(resolve => setTimeout(resolve, 2000));
            } else if (progressId) {
                // Fallback if no batch_id available
                statusManager.updateProgress(progressId, totalCodes, totalCodes, 
                    `Completed processing ${jobName}`);
            }
                
                if (batchResult.r2_url) {
                // R2 URL available - fetch directly from R2 (preferred method)
                console.log('Fetching results from R2:', batchResult.r2_url);
                
                try {
                    const r2Response = await fetch(batchResult.r2_url);
                    if (r2Response.ok) {
                        const r2Data = await r2Response.json();
                        if (r2Data.results && r2Data.results.length > 0) {
                            const chunkMappings = r2Data.results.map(item => {
                                // Use backend structure directly
                                return {
                                    data_source: item.input.DATA_SOURCE || item.input.data_source || item.output.data_source,
                                    modality_code: item.input.MODALITY_CODE || item.input.modality_code || item.output.modality_code,
                                    exam_code: item.input.EXAM_CODE || item.input.exam_code || item.output.exam_code,
                                    exam_name: item.input.EXAM_NAME || item.input.exam_name || item.output.exam_name,
                                    clean_name: item.status === 'success' ? item.output.clean_name : `ERROR: ${item.error}`,
                                    snomed: item.status === 'success' ? item.output.snomed || {} : {},
                                    components: item.status === 'success' ? item.output.components || {} : {},
                                    all_candidates: item.status === 'success' ? item.output.all_candidates || [] : [],
                                    ambiguous: item.status === 'success' ? item.output.ambiguous : false,
                                    secondary_pipeline_applied: item.status === 'success' ? item.output.secondary_pipeline_applied || false : false,
                                    secondary_pipeline_details: item.status === 'success' ? item.output.secondary_pipeline_details : undefined
                                };
                            });
                            allMappings.push(...chunkMappings);
                            console.log(`Successfully loaded ${r2Data.results.length} results from R2`);
                        } else {
                            throw new Error('No results found in R2 data');
                        }
                    } else {
                        console.error('Failed to fetch from R2:', r2Response.statusText);
                        throw new Error(`Failed to fetch from R2: ${r2Response.statusText}`);
                    }
                } catch (error) {
                    console.error('Error fetching or processing R2 results:', error);
                    // Provide a fallback link for the user
                    statusManager.show(`Processing complete. <a href="${batchResult.r2_url}" target="_blank">View results on R2</a>`, 'success', 0);
                    return; // Stop further execution
                }
            } else if (batchResult.results) {
                // Old format - inline results (for smaller batches)
                const chunkMappings = batchResult.results.map(item => {
                    // Use backend structure directly
                    return {
                        data_source: item.input.DATA_SOURCE || item.input.data_source || item.output.data_source,
                        modality_code: item.input.MODALITY_CODE || item.input.modality_code || item.output.modality_code,
                        exam_code: item.input.EXAM_CODE || item.input.exam_code || item.output.exam_code,
                        exam_name: item.input.EXAM_NAME || item.input.exam_name || item.output.exam_name,
                        clean_name: item.status === 'success' ? item.output.clean_name : `ERROR: ${item.error}`,
                        snomed: item.status === 'success' ? item.output.snomed || {} : {},
                        components: item.status === 'success' ? item.output.components || {} : {},
                        all_candidates: item.status === 'success' ? item.output.all_candidates || [] : [],
                        ambiguous: item.status === 'success' ? item.output.ambiguous : false,
                        secondary_pipeline_applied: item.status === 'success' ? item.output.secondary_pipeline_applied || false : false,
                        secondary_pipeline_details: item.status === 'success' ? item.output.secondary_pipeline_details : undefined
                    };
                });
                allMappings.push(...chunkMappings);
            } else {
                console.error('Unexpected response format:', batchResult);
                throw new Error('Unexpected response format from server. No R2 URL or inline results found.');
            }
                
            statusManager.show(`Successfully processed ${allMappings.length} records from ${jobName}.`, 'success', 5000);
            
            // Models are already loaded - no need to reload after processing
            
            runAnalysis(allMappings);

        } catch (error) {
            if (progressId) statusManager.remove(progressId);
            statusManager.show(`Processing failed: ${error.message}`, 'error', 0);
            console.error('Batch processing error:', error);
        }
    }

    async function processIndividual(codes, jobName) {
        allMappings = [];
        const totalCodes = codes.length;
        let progressId = null;
        let processedCount = 0;
        let errorCount = 0;

        try {
            progressId = statusManager.showProgress(`Processing ${jobName}`, 0, totalCodes);

            // Process codes individually with concurrency limit
            const concurrencyLimit = 3; // Process 3 at a time to avoid overwhelming the API
            const results = [];

            for (let i = 0; i < codes.length; i += concurrencyLimit) {
                const batch = codes.slice(i, i + concurrencyLimit);
                const batchPromises = batch.map(async (code) => {
                    try {
                        const examData = {
                            exam_name: code.EXAM_NAME,
                            modality_code: code.MODALITY_CODE,
                            model: currentModel,
                            reranker: currentReranker
                        };

                        const response = await fetch(INDIVIDUAL_API_URL, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(examData)
                        });

                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`API failed: ${errorText}`);
                        }

                        const result = await response.json();
                        return {
                            status: 'success',
                            input: code,
                            output: result
                        };
                    } catch (error) {
                        console.error(`Error processing ${code.EXAM_NAME}:`, error);
                        return {
                            status: 'error',
                            input: code,
                            error: error.message
                        };
                    }
                });

                // Wait for this batch to complete
                const batchResults = await Promise.all(batchPromises);
                results.push(...batchResults);

                // Update progress
                processedCount = results.filter(r => r.status === 'success').length;
                errorCount = results.filter(r => r.status === 'error').length;
                
                if (progressId) {
                    statusManager.updateProgress(progressId, processedCount + errorCount, totalCodes, 
                        `Processing ${jobName}`);
                }
            }

            // Convert results to the same format as batch processing
            const chunkMappings = results.map(item => {
                // Use backend structure directly
                return {
                    data_source: item.input.DATA_SOURCE || item.input.data_source || item.output.data_source,
                    modality_code: item.input.MODALITY_CODE || item.input.modality_code || item.output.modality_code,
                    exam_code: item.input.EXAM_CODE || item.input.exam_code || item.output.exam_code,
                    exam_name: item.input.EXAM_NAME || item.input.exam_name || item.output.exam_name,
                    clean_name: item.status === 'success' ? item.output.clean_name : `ERROR: ${item.error}`,
                    snomed: item.status === 'success' ? item.output.snomed || {} : {},
                    components: item.status === 'success' ? item.output.components || {} : {},
                    all_candidates: item.status === 'success' ? item.output.all_candidates || [] : [],
                    ambiguous: item.status === 'success' ? item.output.ambiguous : false,
                    secondary_pipeline_applied: item.status === 'success' ? item.output.secondary_pipeline_applied || false : false,
                    secondary_pipeline_details: item.status === 'success' ? item.output.secondary_pipeline_details : undefined
                };
            });

            allMappings.push(...chunkMappings);

            statusManager.show(`Successfully processed ${processedCount} records from ${jobName}. ${errorCount > 0 ? `${errorCount} errors encountered.` : ''}`, 
                errorCount > 0 ? 'warning' : 'success', 5000);

            runAnalysis(allMappings);

        } catch (error) {
            if (progressId) statusManager.remove(progressId);
            statusManager.show(`Individual processing failed: ${error.message}`, 'error', 0);
            console.error('Individual processing error:', error);
        }
    }
    
    function runAnalysis(mappings) {
        statusManager.clearAll();
        summaryData = generateAnalyticsSummary(mappings);
        updateStatsUI(summaryData);
        updateResultsTitle();
        
        sortedMappings = [...mappings];
        sortAndDisplayResults();
        
        generateConsolidatedResults(mappings);
        generateSourceLegend(mappings);
        resultsSection.style.display = 'block';
        // Hide hero and workflow sections when showing results
        const heroSection = document.querySelector('.hero-section');
        const workflowSection = document.getElementById('workflowSection');
        if (heroSection) heroSection.style.display = 'none';
        if (workflowSection) workflowSection.style.display = 'none';
        // Show main card when displaying results
        mainCard.style.display = 'block';
    }

    // --- UI & DISPLAY FUNCTIONS ---
    function updateResultsTitle() {
        const titleElement = document.getElementById('resultsTitle');
        const modelDisplayName = formatModelName(currentModel);
        const rerankerDisplayName = formatRerankerName(currentReranker);
        titleElement.textContent = `Cleaning Results with ${modelDisplayName} → ${rerankerDisplayName}`;
    }
    
    function updatePageTitle(title) {
        // Update browser tab title
        document.title = `${title} - Radiology Cleaner`;
        
        // Update results title element if it exists
        const titleElement = document.getElementById('resultsTitle');
        if (titleElement) {
            titleElement.textContent = title;
        }
    }

    function generateSourceLegend(mappings) {
        const uniqueSources = [...new Set(mappings.map(item => {
            return item.data_source;
        }))];
        const sourceNames = getSourceNames();
        
        let legendContainer = document.getElementById('sourceLegend');
        if (!legendContainer) {
            legendContainer = document.createElement('div');
            legendContainer.id = 'sourceLegend';
            legendContainer.className = 'source-legend';
            const fullView = document.getElementById('fullView');
            if (fullView) {
                const firstChild = fullView.firstChild;
                fullView.insertBefore(legendContainer, firstChild);
            }
        }
        
        let legendHTML = '<div class="source-legend-grid">';
        uniqueSources.forEach(source => {
            const color = getSourceColor(source);
            const displayName = sourceNames[source] || source;
            legendHTML += `<div class="source-legend-item"><div class="source-legend-color" style="background-color: ${color};"></div><span>${displayName}</span></div>`;
        });
        legendHTML += '</div>';
        legendContainer.innerHTML = legendHTML;
    }

    function updateStatsUI(summary) {
        document.getElementById('originalCount').textContent = summary.totalOriginalCodes;
        document.getElementById('cleanCount').textContent = summary.uniqueCleanNames;
        document.getElementById('consolidationRatio').textContent = `${summary.consolidationRatio}:1`;
        document.getElementById('modalityCount').textContent = Object.keys(summary.modalityBreakdown).length;
        document.getElementById('avgConfidence').textContent = `${summary.avgConfidence}%`;
    }

    const sourceColorPalette = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#ff1493', '#00ced1', '#ff4500', '#32cd32', '#ba55d3'
    ];
    
    const sourceColors = {};
    function getSourceColor(source) {
        if (!sourceColors[source]) {
            const colorIndex = Object.keys(sourceColors).length % sourceColorPalette.length;
            sourceColors[source] = sourceColorPalette[colorIndex];
        }
        return sourceColors[source];
    }

    function sortAndDisplayResults() {
        applySortToMappings();
        displayCurrentPage();
    }

    function displayCurrentPage() {
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        const pageData = sortedMappings.slice(startIndex, endIndex);
        displayResults(pageData);
        
        document.getElementById('paginationControls').style.display = sortedMappings.length > pageSize ? 'flex' : 'none';
        const totalPages = Math.ceil(sortedMappings.length / pageSize);
        document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
        document.getElementById('prevPageBtn').disabled = currentPage <= 1;
        document.getElementById('nextPageBtn').disabled = currentPage >= totalPages;
        const tableInfo = document.getElementById('tableInfo');
        tableInfo.textContent = `Showing ${startIndex + 1}-${Math.min(endIndex, sortedMappings.length)} of ${sortedMappings.length} results`;
    }
    
    function applySortToMappings() {
        switch (sortBy) {
            case 'confidence-desc':
                sortedMappings.sort((a, b) => (b.components?.confidence || 0) - (a.components?.confidence || 0));
                break;
            case 'confidence-asc':
                sortedMappings.sort((a, b) => (a.components?.confidence || 0) - (b.components?.confidence || 0));
                break;
            case 'name-asc':
                sortedMappings.sort((a, b) => (a.clean_name || '').localeCompare(b.clean_name || ''));
                break;
            case 'name-desc':
                sortedMappings.sort((a, b) => (b.clean_name || '').localeCompare(a.clean_name || ''));
                break;
            default:
                sortedMappings = [...allMappings];
        }
    }

    // Removed normalizeResultItem function - now using backend structure directly

    function displayResults(results) {
        resultsBody.innerHTML = '';
        const resultsMobile = document.getElementById('resultsMobile');
        if (resultsMobile) resultsMobile.innerHTML = '';
        
        results.forEach(item => {
            // item is already in the correct format from the mapping above
            const row = resultsBody.insertRow();
            
            const sourceCell = row.insertCell();
            sourceCell.style.cssText = `width: 12px; padding: 0; background-color: ${getSourceColor(item.data_source)}; border-right: none; position: relative;`;
            const sourceNames = getSourceNames();
            sourceCell.title = sourceNames[item.data_source] || item.data_source;
            
            row.insertCell().textContent = item.exam_code;
            row.insertCell().textContent = item.exam_name;

            const cleanNameCell = row.insertCell();
            
            // Create tooltip content from all_candidates
            if (item.clean_name && item.clean_name.startsWith('ERROR')) {
                cleanNameCell.innerHTML = `<span class="error-message">${item.clean_name}</span>`;
            } else if (item.all_candidates && item.all_candidates.length > 1) {
                const tooltipHTML = item.all_candidates.map((candidate, index) => 
                    `<div class="candidate-item">${index + 1}. ${candidate.primary_name} <span class="confidence">(${candidate.confidence.toFixed(2)})</span></div>`
                ).join('');
                
                cleanNameCell.innerHTML = `
                    <div class="tooltip-container">
                        <strong class="clean-name-hover">${item.clean_name || 'Unknown'}</strong>
                        <div class="tooltip-content">
                            <div class="tooltip-header">All Candidates:</div>
                            ${tooltipHTML}
                        </div>
                    </div>
                `;
                
                // Add dynamic positioning for fixed tooltip
                const tooltipContainer = cleanNameCell.querySelector('.tooltip-container');
                const tooltipContent = cleanNameCell.querySelector('.tooltip-content');
                
                tooltipContainer.addEventListener('mouseenter', function(e) {
                    const rect = this.getBoundingClientRect();
                    const tooltipRect = tooltipContent.getBoundingClientRect();
                    
                    // Position to the right of the element
                    let left = rect.right + 10;
                    let top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                    
                    // Adjust if tooltip would go off-screen
                    if (left + tooltipRect.width > window.innerWidth) {
                        left = rect.left - tooltipRect.width - 10; // Position to the left instead
                    }
                    if (top < 0) {
                        top = 10;
                    }
                    if (top + tooltipRect.height > window.innerHeight) {
                        top = window.innerHeight - tooltipRect.height - 10;
                    }
                    
                    tooltipContent.style.left = left + 'px';
                    tooltipContent.style.top = top + 'px';
                });
            } else {
                cleanNameCell.innerHTML = `<strong>${item.clean_name || 'Unknown'}</strong>`;
            }

            const snomedFsnCell = row.insertCell();
            snomedFsnCell.innerHTML = item.snomed?.fsn ? `<div>${item.snomed.fsn}</div>` + (item.snomed.id ? `<div style="font-size: 0.8em; color: #666; margin-top: 2px;">${item.snomed.id}</div>` : '') : '<span style="color: #999;">-</span>';

            const tagsCell = row.insertCell();
            let tagsHTML = '';
            const { anatomy, laterality, contrast, technique, gender_context, age_context, clinical_context, clinical_equivalents } = item.components || {};
            const addTag = (value, className) => (value && value.trim()) ? `<span class="tag ${className}">${value}</span>` : '';
            const addTags = (arr, className) => Array.isArray(arr) ? arr.map(v => addTag(v, className)).join('') : addTag(arr, className);

            tagsHTML += addTags(anatomy, 'anatomy');
            tagsHTML += addTags(laterality, 'laterality');
            tagsHTML += addTags(contrast, 'contrast');
            tagsHTML += addTags(technique, 'technique');
            tagsHTML += addTag(gender_context, 'gender');
            tagsHTML += addTag(age_context, 'age');
            tagsHTML += addTags(clinical_context, 'clinical');
            if (clinical_equivalents) tagsHTML += addTags(clinical_equivalents.slice(0, 2), 'equivalent');
            tagsCell.innerHTML = tagsHTML;

            const confidenceCell = row.insertCell();
            const confidence = item.components?.confidence || 0;
            const confidencePercent = Math.round(confidence * 100);
            const confidenceClass = confidence >= 0.8 ? 'confidence-high' : confidence >= 0.6 ? 'confidence-medium' : 'confidence-low';
            const isSecondaryPipelineImproved = item.secondary_pipeline_applied && item.secondary_pipeline_details?.improved;
            const secondaryPipelineTag = isSecondaryPipelineImproved ? '<div class="secondary-pipeline-tag" title="Improved by Secondary Pipeline"><i class="fas fa-robot"></i> Super AI Mapped</div>' : '';
            confidenceCell.innerHTML = `<div class="confidence-bar"><div class="confidence-fill ${confidenceClass}" style="width: ${confidencePercent}%"></div></div><small>${confidencePercent}%</small>${secondaryPipelineTag}`;
            
            // Create mobile card
            if (resultsMobile) {
                const card = document.createElement('div');
                card.className = 'result-card';
                
                const sourceNames = getSourceNames();
                const sourceName = sourceNames[item.data_source] || item.data_source;
                
                // Build tags HTML (reuse from above)
                const { anatomy, laterality, contrast, technique, gender_context, age_context, clinical_context, clinical_equivalents } = item.components || {};
                const addTag = (value, className) => (value && value.trim()) ? `<span class="tag ${className}">${value}</span>` : '';
                const addTags = (arr, className) => Array.isArray(arr) ? arr.map(v => addTag(v, className)).join('') : addTag(arr, className);
                let tagsHTML = '';
                tagsHTML += addTags(anatomy, 'anatomy');
                tagsHTML += addTags(laterality, 'laterality');
                tagsHTML += addTags(contrast, 'contrast');
                tagsHTML += addTags(technique, 'technique');
                tagsHTML += addTag(gender_context, 'gender');
                tagsHTML += addTag(age_context, 'age');
                tagsHTML += addTags(clinical_context, 'clinical');
                if (clinical_equivalents) tagsHTML += addTags(clinical_equivalents.slice(0, 2), 'equivalent');
                
                const snomedInfo = item.snomed?.fsn ? 
                    `${item.snomed.fsn}${item.snomed.id ? ` (${item.snomed.id})` : ''}` : '-';
                
                card.innerHTML = `
                    <div class="result-card-header">
                        <div class="result-card-title">${item.clean_name || 'Unknown'}</div>
                        <div class="result-card-confidence ${confidenceClass}">${confidence >= 0.8 ? 'HIGH' : confidence >= 0.6 ? 'MEDIUM' : 'LOW'}</div>
                    </div>
                    <div class="result-card-body">
                        <div class="result-card-row">
                            <span class="result-card-label">Code:</span>
                            <span class="result-card-value">${item.exam_code}</span>
                        </div>
                        <div class="result-card-row">
                            <span class="result-card-label">Original:</span>
                            <span class="result-card-value">${item.exam_name}</span>
                        </div>
                        <div class="result-card-row">
                            <span class="result-card-label">Source:</span>
                            <span class="result-card-value">${sourceName}</span>
                        </div>
                        <div class="result-card-row">
                            <span class="result-card-label">SNOMED:</span>
                            <span class="result-card-value">${snomedInfo}</span>
                        </div>
                        ${tagsHTML ? `<div class="result-card-row">
                            <span class="result-card-label">Tags:</span>
                            <span class="result-card-value">${tagsHTML}</span>
                        </div>` : ''}
                    </div>
                `;
                
                resultsMobile.appendChild(card);
            }
        });
    }

    // --- UTILITY & EXPORT FUNCTIONS ---
    function generateAnalyticsSummary(mappings) {
        const summary = {
            totalOriginalCodes: mappings.length,
            uniqueCleanNames: new Set(mappings.map(m => {
                return m.clean_name;
            }).filter(n => n && !n.startsWith('ERROR'))).size,
            modalityBreakdown: {}, 
            avgConfidence: 0,
        };
        summary.consolidationRatio = summary.uniqueCleanNames > 0 ? (summary.totalOriginalCodes / summary.uniqueCleanNames).toFixed(2) : "0.00";
        
        let totalConfidence = 0, confidenceCount = 0;
        mappings.forEach(m => {
            if (!m.components || !m.clean_name || m.clean_name.startsWith('ERROR')) return;
            const modality = m.components.modality || m.modality_code;
            if (modality) summary.modalityBreakdown[modality] = (summary.modalityBreakdown[modality] || 0) + 1;
            if (m.components.confidence !== undefined) {
                totalConfidence += m.components.confidence;
                confidenceCount++;
            }
        });
        
        summary.avgConfidence = confidenceCount > 0 ? Math.round((totalConfidence / confidenceCount) * 100) : 0;
        return summary;
    }

    function exportResults() {
        if (!allMappings.length) return alert('No data to export.');
        downloadJSON(allMappings, 'radiology_codes_cleaned.json');
    }
    
    function closeModal() { 
        const modal = document.getElementById('consolidationModal');
        if (modal) modal.style.display = 'none'; 
    }
    
    // Make functions globally accessible
    window.closeModal = closeModal;
    
    // --- CONSOLIDATED VIEW FUNCTIONS ---
    let consolidatedData = [];
    let filteredConsolidatedData = [];

    function generateConsolidatedResults(mappings) {
        const consolidatedGroups = {};
        mappings.forEach(m => {
            if (!m.clean_name || m.clean_name.startsWith('ERROR')) return;
            const group = consolidatedGroups[m.clean_name] || {
                cleanName: m.clean_name,
                snomed: m.snomed,
                sourceCodes: [],
                totalCount: 0,
                components: m.components,
                dataSources: new Set(),
                modalities: new Set(),
                secondaryPipelineCount: 0
            };
            group.sourceCodes.push(m);
            group.totalCount++;
            group.dataSources.add(m.data_source);
            group.modalities.add(m.modality_code);
            if (m.secondary_pipeline_applied && m.secondary_pipeline_details?.improved) {
                group.secondaryPipelineCount++;
            }
            consolidatedGroups[m.clean_name] = group;
        });
        
        consolidatedData = Object.values(consolidatedGroups).map(group => {
            const totalConfidence = group.sourceCodes.reduce((sum, code) => sum + (code.components?.confidence || 0), 0);
            group.avgConfidence = group.sourceCodes.length > 0 ? totalConfidence / group.sourceCodes.length : 0;
            return group;
        });

        filteredConsolidatedData = [...consolidatedData];
        sortConsolidatedResults();
    }
    
    let isFullView = true;
    function toggleView() {
        isFullView = !isFullView;
        document.getElementById('fullView').style.display = isFullView ? 'block' : 'none';
        document.getElementById('consolidatedView').style.display = isFullView ? 'none' : 'block';
        const toggleBtn = document.getElementById('viewToggleBtn');
        toggleBtn.textContent = isFullView ? 'Switch to Consolidated View' : 'Switch to Full View';
        if (isFullView) {
            toggleBtn.classList.remove('secondary');
            toggleBtn.classList.add('active');
        } else {
            toggleBtn.classList.remove('active');
            toggleBtn.classList.add('secondary');
            displayConsolidatedResults();
        }
    }

    function toggleOriginalCodes(headerElement) {
        const groupElement = headerElement.closest('.consolidated-group');
        const codesContainer = groupElement.querySelector('.original-codes-container');
        if (codesContainer) {
            const isHidden = codesContainer.style.display === 'none';
            codesContainer.style.display = isHidden ? 'block' : 'none';
            headerElement.classList.toggle('expanded', isHidden);
        }
    }
    
    // Make functions globally accessible
    window.toggleOriginalCodes = toggleOriginalCodes;

    function displayConsolidatedResults() {
        const container = document.getElementById('consolidatedResults');
        container.innerHTML = '';
        
        filteredConsolidatedData.forEach(group => {
            const groupElement = document.createElement('div');
            groupElement.className = 'consolidated-group';
            const confidencePercent = Math.round(group.avgConfidence * 100);
            const confidenceClass = group.avgConfidence >= 0.8 ? 'confidence-high' : group.avgConfidence >= 0.6 ? 'confidence-medium' : 'confidence-low';
            
            const snomedId = group.snomed && group.snomed.id ? `(${group.snomed.id})` : '';
            
            const originalCodesList = group.sourceCodes.map(code =>
                `<li class="original-code-item">
                    <span class="original-code-source" style="background-color: ${getSourceColor(code.data_source)}" title="${getSourceDisplayName(code.data_source)}"></span>
                    <span class="original-code-name">${code.exam_name}</span>
                    <span class="original-code-details">(${code.exam_code})</span>
                </li>`
            ).join('');
            
            // Debug: Log if no codes found
            if (group.sourceCodes.length === 0) {
                console.warn('No source codes found for group:', group.cleanName);
            }

            groupElement.innerHTML = `
                <div class="consolidated-header" onclick="toggleOriginalCodes(this)">
                    <div class="consolidated-title-container">
                        <div class="consolidated-title">${group.cleanName}</div>
                        ${snomedId ? `<div class="snomed-code">SNOMED-CT ID: ${snomedId}</div>` : ''}
                    </div>
                    <div class="consolidated-count-container">
                        <span class="consolidated-count">${group.totalCount} codes</span>
                        <span class="expand-icon"></span>
                    </div>
                </div>
                <div class="consolidated-body">
                    <div class="consolidated-meta">
                        <div class="meta-item"><strong>Data Sources</strong><div class="source-indicators">${Array.from(group.dataSources).map(source => `<div class="source-item" title="${getSourceDisplayName(source)}"><span class="source-color-dot" style="background-color: ${getSourceColor(source)}"></span>${getSourceDisplayName(source)}</div>`).join('')}</div></div>
                        <div class="meta-item"><strong>Modalities</strong><div class="modality-list">${Array.from(group.modalities).filter(m => m && m.trim()).join(', ') || 'None specified'}</div></div>
                        <div class="meta-item"><strong>Avg Confidence</strong><div class="confidence-display"><div class="confidence-bar"><div class="confidence-fill ${confidenceClass}" style="width: ${confidencePercent}%"></div></div><div class="confidence-text">${confidencePercent}%</div></div>${group.secondaryPipelineCount > 0 ? `<div class="secondary-pipeline-tag" title="${group.secondaryPipelineCount} of ${group.totalCount} results improved by Secondary Pipeline"><i class="fas fa-robot"></i> ${group.secondaryPipelineCount} Super AI Mapped</div>` : ''}</div>
                        <div class="meta-item"><strong>Parsed Components</strong><div class="component-tags">${generateComponentTags(group.components)}</div></div>
                    </div>
                    <div class="original-codes-container" style="display: none;">
                        <ul class="original-codes-list">${originalCodesList}</ul>
                    </div>
                </div>`;
            container.appendChild(groupElement);
        });
    }
    
    function generateComponentTags(components) {
        let tags = '';
        const addTag = (value, className) => value ? `<span class="tag ${className}">${value}</span>` : '';
        const addTags = (arr, className) => Array.isArray(arr) ? arr.map(v => addTag(v, className)).join('') : addTag(arr, className);

        tags += addTags(components.anatomy, 'anatomy');
        tags += addTag(components.modality, 'modality');
        tags += addTags(components.laterality, 'laterality');
        tags += addTags(components.contrast, 'contrast');
        tags += addTags(components.technique, 'technique');
        tags += addTag(components.gender_context, 'gender');
        tags += addTags(components.clinical_context, 'clinical');
        
        return tags || '<span class="no-components">No parsed components</span>';
    }
    
    function getSourceDisplayName(source) {
        const sourceNames = getSourceNames();
        return sourceNames[source] || source;
    }
    
    function filterConsolidatedResults() {
        const searchTerm = document.getElementById('consolidatedSearch').value.toLowerCase();
        filteredConsolidatedData = consolidatedData.filter(group => 
            group.cleanName.toLowerCase().includes(searchTerm) ||
            group.sourceCodes.some(code => code.exam_name.toLowerCase().includes(searchTerm) || code.exam_code.toLowerCase().includes(searchTerm))
        );
        sortConsolidatedResults();
    }
    
    function sortConsolidatedResults() {
        const sortByValue = document.getElementById('consolidatedSort').value;
        filteredConsolidatedData.sort((a, b) => {
            if (sortByValue === 'count') return b.totalCount - a.totalCount;
            if (sortByValue === 'name') return a.cleanName.localeCompare(b.cleanName);
            if (sortByValue === 'confidence') return b.avgConfidence - a.avgConfidence;
            return b.totalCount - a.totalCount;
        });
        displayConsolidatedResults();
    }
    
    function downloadJSON(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }


    // --- HOMEPAGE WORKFLOW FUNCTIONALITY ---
    function setupHomepageWorkflow() {
        const quickDemoBtn = document.getElementById('quickDemoBtn');
        const uploadDataBtn = document.getElementById('uploadDataBtn');
        const advancedSetupBtn = document.getElementById('advancedSetupBtn');
        const workflowSection = document.getElementById('workflowSection');
        const uploadSection = document.getElementById('uploadSection');
        const advancedSection = document.getElementById('advancedSection');
        const runProcessingBtn = document.getElementById('runProcessingBtn');
        const runRandomDemoBtn = document.getElementById('runRandomDemoBtn');
        const runFixedTestBtn = document.getElementById('runFixedTestBtn');
        const demoOptions = document.getElementById('demoOptions');
        const dataSourceDisplay = document.getElementById('dataSourceDisplay');
        const dataSourceText = document.getElementById('dataSourceText');
        
        let currentDataSource = null;
        let selectedRetriever = null;
        let selectedReranker = null;
        
        // Action card click handlers - make entire cards clickable
        document.querySelector('.demo-path')?.addEventListener('click', () => {
            // Don't allow demo selection if models are still loading
            if (buttonsDisabledForLoading) {
                return;
            }
            selectPath('demo');
            currentDataSource = 'demo';
            checkWorkflowCompletion();
            
            // Auto-scroll to model selection on mobile
            scrollToModelSelection();
        });
        
        document.querySelector('.upload-path')?.addEventListener('click', () => {
            // Don't allow upload if models are still loading
            if (buttonsDisabledForLoading) {
                return;
            }
            selectPath('upload');
            fileInput.click();
        });
        
        document.querySelector('.advanced-path')?.addEventListener('click', () => {
            // Open config editor instead of advanced section
            openConfigEditor();
        });
        
        // File input handler for upload path
        fileInput?.addEventListener('change', (e) => {
            if (e.target.files[0]) {
                currentDataSource = 'upload';
                dataSourceText.textContent = `Uploaded File: ${e.target.files[0].name}`;
                dataSourceDisplay.style.display = 'block';
                checkWorkflowCompletion();
                
                // Auto-scroll to model selection on mobile
                scrollToModelSelection();
            }
        });
        
        // Demo buttons
        runRandomDemoBtn?.addEventListener('click', async () => {
            await runRandomSampleDemo();
        });
        
        // Sample size input listener
        const sampleSizeInput = document.getElementById('sampleSizeInput');
        const randomSampleSubtext = document.getElementById('randomSampleSubtext');
        
        function updateSampleSizeDisplay() {
            const sampleSize = parseInt(sampleSizeInput?.value) || 100;
            if (randomSampleSubtext) {
                randomSampleSubtext.textContent = `${sampleSize} random codes from live dataset`;
            }
        }
        
        sampleSizeInput?.addEventListener('input', updateSampleSizeDisplay);
        sampleSizeInput?.addEventListener('change', updateSampleSizeDisplay);
        
        // Initialize the display
        updateSampleSizeDisplay();
        
        runFixedTestBtn?.addEventListener('click', async () => {
            await runSanityTest();
        });

        // File upload processing button
        runProcessingBtn?.addEventListener('click', async () => {
            if (currentDataSource === 'upload' && fileInput.files[0]) {
                await processFile(fileInput.files[0]);
            }
        });
        
        function selectPath(path) {
            // Remove all previous selections
            document.querySelectorAll('.action-card').forEach(card => card.classList.remove('selected'));
            
            // Hide all sections (with null checks)
            if (workflowSection) workflowSection.style.display = 'none';
            if (uploadSection) uploadSection.style.display = 'none';
            if (advancedSection) advancedSection.style.display = 'none';
            
            if (path === 'demo' || path === 'upload') {
                // Show workflow for demo and upload paths
                if (workflowSection) workflowSection.style.display = 'block';
                
                // Select the appropriate card
                const selectedCard = path === 'demo' ? 
                    document.querySelector('.demo-path') : 
                    document.querySelector('.upload-path');
                selectedCard?.classList.add('selected');
                
                // Reset workflow state
                resetWorkflowSteps();
                
            } else if (path === 'advanced') {
                // Show advanced configuration
                if (advancedSection) advancedSection.style.display = 'block';
                document.querySelector('.advanced-path')?.classList.add('selected');
            }
        }
        
        function resetWorkflowSteps() {
            // Reset step indicators
            document.getElementById('step1')?.classList.add('active');
            document.getElementById('step2')?.classList.remove('active');
            document.getElementById('step3')?.classList.remove('active');
            
            // Reset step sections
            document.getElementById('retrieverStep')?.classList.add('active');
            document.getElementById('rerankerStep')?.classList.remove('active');
            document.getElementById('runStep')?.classList.remove('active');
            
            selectedRetriever = null;
            selectedReranker = null;
            runProcessingBtn.disabled = true;
            if (runRandomDemoBtn) runRandomDemoBtn.disabled = true;
            if (runFixedTestBtn) runFixedTestBtn.disabled = true;
        }
        
        function activateStep(stepNumber) {
            // Update step indicators
            for (let i = 1; i <= 3; i++) {
                const step = document.getElementById(`step${i}`);
                if (i <= stepNumber) {
                    step?.classList.add('active');
                } else {
                    step?.classList.remove('active');
                }
            }
            
            // Update step sections
            const steps = ['retrieverStep', 'rerankerStep', 'runStep'];
            steps.forEach((stepId, index) => {
                const stepElement = document.getElementById(stepId);
                if (index < stepNumber) {
                    stepElement?.classList.add('active');
                } else {
                    stepElement?.classList.remove('active');
                }
            });
        }
        
        function checkWorkflowCompletion() {
            // Update selected models based on current state
            selectedRetriever = currentModel;
            selectedReranker = currentReranker;
            
            if (selectedRetriever && selectedReranker && currentDataSource) {
                // Show appropriate buttons based on data source
                if (currentDataSource === 'demo') {
                    demoOptions.style.display = 'block';
                    runProcessingBtn.style.display = 'none';
                    // Show secondary pipeline option for demo
                    const secondaryPipelineOption = document.getElementById('secondaryPipelineOption');
                    if (secondaryPipelineOption) secondaryPipelineOption.style.display = 'block';
                    // Only enable if models are loaded and not using fallbacks
                    const canEnable = !buttonsDisabledForLoading && !isUsingFallbackModels;
                    runRandomDemoBtn.disabled = !canEnable;
                    runFixedTestBtn.disabled = !canEnable;
                } else if (currentDataSource === 'upload') {
                    demoOptions.style.display = 'none';
                    runProcessingBtn.style.display = 'block';
                    // Hide secondary pipeline option for file upload
                    const secondaryPipelineOption = document.getElementById('secondaryPipelineOption');
                    if (secondaryPipelineOption) secondaryPipelineOption.style.display = 'none';
                    // Only enable if models are loaded and not using fallbacks
                    const canEnable = !buttonsDisabledForLoading && !isUsingFallbackModels;
                    runProcessingBtn.disabled = !canEnable;
                }
                activateStep(3);
            } else if (selectedRetriever && currentDataSource) {
                activateStep(2);
            } else if (currentDataSource) {
                activateStep(1);
            }
        }
        
        // Expose workflow check function globally
        window.workflowCheckFunction = checkWorkflowCompletion;
    }

    // Make loadAvailableModels globally accessible for navigation handling
    window.loadAvailableModels = loadAvailableModels;
    
    // --- INITIALIZE APP ---
    // Disable action buttons initially until models load
    disableActionButtons('Models are loading...');
    
    testApiConnectivity();
    loadAvailableModels();
    setupEventListeners();
});

// Handle page navigation (back/forward) to ensure models reload
window.addEventListener('pageshow', function(event) {
    // If the page is loaded from cache (like when using back button)
    if (event.persisted) {
        // Check if models are loaded, if not reload them
        const modelButtons = document.querySelectorAll('.model-toggle');
        if (modelButtons.length === 0) {
            // Skip warmup messages when navigating back - API is likely already warm
            window.loadAvailableModels(0, true);
        }
    }
});
