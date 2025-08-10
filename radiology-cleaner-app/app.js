// =================================================================================
// app.js - Core Application Logic for Radiology Cleaner
// =================================================================================
// This file contains the main client-side logic for the Radiology Cleaner application.
// It handles UI interactions, API communication, data processing, and results display.
//
// Organization:
// 1.  Status Manager: A class for displaying dynamic status messages and progress bars.
// 2.  Global State: Application-wide variables for models, results, and UI state.
// 3.  Button State Management: Functions to enable/disable UI elements during processing.
// 4.  Utility & Helper Functions: General-purpose functions used across the application.
// 5.  Core Application Setup (DOMContentLoaded): The main entry point that orchestrates
//     the entire application setup after the DOM is loaded. This includes:
//     5.1. Centralized Source Names
//     5.2. API & Configuration
//     5.3. DOM Element Caching
//     5.4. Core Initialization (API tests, warmup)
//     5.5. Model & Reranker Loading
//     5.6. UI Builders
//     5.7. Event Listener Setup
//     5.8. Main UI Flow Control (Upload, New, etc.)
//     5.9. Core Processing Logic (Batch, Individual, Samples)
//     5.10. Config Editor Logic
//     5.11. Results Analysis & Display
//     5.12. Consolidated View Logic
//     5.13. Validation Workflow
//     5.14. Homepage Workflow
//     5.15. Final Initialization Call
// 6.  Page Navigation Handling: Ensures application state is correct on back/forward.
// =================================================================================


// =================================================================================
// 1. STATUS MANAGER
// =================================================================================
// Manages all status messages, notifications, and progress indicators shown to the user.
// =================================================================================

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
        textElement.style.cssText = 'flex-grow: 1;';
        
        messageElement.appendChild(iconElement);
        messageElement.appendChild(textElement);
        
        if (autoHideDuration === 0) {
            const closeButton = document.createElement('button');
            closeButton.className = 'status-close';
            closeButton.innerHTML = '×';
            closeButton.style.cssText = 'background: none; border: none; font-size: 18px; cursor: pointer; padding: 0; line-height: 1; color: var(--color-gray-600, #666); opacity: 0.7; transition: opacity 0.2s; position: absolute; right: 12px; top: 50%; transform: translateY(-50%);';
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


// =================================================================================
// 2. GLOBAL VARIABLES & STATE
// =================================================================================
// Holds the application's state, including selected models, results data, and UI state.
// =================================================================================

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
let buttonsDisabledForLoading = true;


// =================================================================================
// 3. BUTTON STATE MANAGEMENT
// =================================================================================
// Functions to enable/disable primary action buttons during long-running operations.
// =================================================================================

function disableActionButtons(reason = 'Models are loading...') {
    const buttons = ['runRandomSampleBtn', 'runProcessingBtn'];
    buttons.forEach(buttonId => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = true;
            button.dataset.originalTitle = button.title || '';
            button.title = reason;
            button.classList.add('loading-disabled');
        }
    });
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
    const buttons = ['runRandomSampleBtn', 'runProcessingBtn'];
    buttons.forEach(buttonId => {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = false;
            button.title = button.dataset.originalTitle || '';
            button.classList.remove('loading-disabled');
        }
    });
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.classList.remove('loading-disabled');
        card.style.pointerEvents = '';
        card.title = card.dataset.originalTitle || '';
    });
    buttonsDisabledForLoading = false;
}


// =================================================================================
// 4. UTILITY & HELPER FUNCTIONS
// =================================================================================
// General-purpose helper functions used across the application.
// =================================================================================

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
    if (window.workflowCheckFunction) {
        window.workflowCheckFunction();
    }
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
    const rerankerStatusEl = document.getElementById('rerankerStatusMessage');
    if (rerankerStatusEl) {
        rerankerStatusEl.style.display = 'block';
        rerankerStatusEl.style.background = '#d4edda';
        rerankerStatusEl.style.color = '#155724';
        rerankerStatusEl.style.border = '1px solid #c3e6cb';
        rerankerStatusEl.textContent = `✓ Switched to ${formatRerankerName(rerankerKey)} reranker`;
        setTimeout(() => {
            if (rerankerStatusEl) {
                rerankerStatusEl.style.display = 'none';
            }
        }, 3000);
    }
    if (window.workflowCheckFunction) {
        window.workflowCheckFunction();
    }
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


// =================================================================================
// 5. CORE APPLICATION SETUP (DOMContentLoaded)
// =================================================================================
// Main entry point, running after the DOM is fully loaded.
// =================================================================================

window.addEventListener('DOMContentLoaded', function() {

    // -----------------------------------------------------------------------------
    // 5.1. Centralized Source Names
    // -----------------------------------------------------------------------------
    function getSourceNames() {
        return {
            'SouthIsland-SIRS COMRAD': 'SIRS (Mid-Upper Sth Island)',
            'Central-Phillips': 'Central',
            'Southern-Karisma': 'Southern District',
            'Auckland Metro-Agfa': 'Auckland Metro',
            'Central-Philips': 'Central'
        };
    }

    function getSourceDisplayName(source) {
        const sourceNames = getSourceNames();
        return sourceNames[source] || source;
    }

    // -----------------------------------------------------------------------------
    // 5.2. API & Configuration
    // -----------------------------------------------------------------------------
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
            apiBase = 'https://radiology-api-staging.onrender.com';
            mode = 'PROD';
        }
        return { baseUrl: apiBase, mode: mode };
    }
    
    const apiConfig = detectApiUrls();
    const BATCH_API_URL = `${apiConfig.baseUrl}/parse_batch`;
    const INDIVIDUAL_API_URL = `${apiConfig.baseUrl}/parse_enhanced`;
    const MODELS_URL = `${apiConfig.baseUrl}/models`;
    const HEALTH_URL = `${apiConfig.baseUrl}/health`;
    const BATCH_THRESHOLD = 500;
    console.log(`Frontend running in ${apiConfig.mode} mode. API base: ${apiConfig.baseUrl}`);

    // -----------------------------------------------------------------------------
    // 5.3. DOM Element Caching
    // -----------------------------------------------------------------------------
    const mainCard = document.querySelector('.main-card');
    const samplesSection = document.getElementById('samplesSection');
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
    const randomSampleButton = document.getElementById('randomSampleBtn');
    const editConfigButton = document.getElementById('editConfigBtn');
    const configEditorModal = document.getElementById('configEditorModal');
    const configEditor = document.getElementById('configEditor');
    const configStatus = document.getElementById('configStatus');
    const reloadConfigBtn = document.getElementById('reloadConfigBtn');
    const saveConfigBtn = document.getElementById('saveConfigBtn');
    const closeConfigEditorModal = document.getElementById('closeConfigEditorModal');
    const closeConfigEditorBtn = document.getElementById('closeConfigEditorBtn');

    // -----------------------------------------------------------------------------
    // 5.4. Core Initialization
    // -----------------------------------------------------------------------------
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
                if (warmupMessageId) statusManager.remove(warmupMessageId);
                statusManager.show(`✅ Processing engine ready (${warmupTime.toFixed(0)}ms)`, 'success', 6000);
                await new Promise(resolve => setTimeout(resolve, 2000));
                enableActionButtons();
            } else {
                throw new Error(`Warmup failed with status ${response.status}`);
            }
        } catch (error) {
            console.warn('⚠️ API warmup failed (processing will still work, but first request may be slower):', error);
            if (warmupMessageId) statusManager.remove(warmupMessageId);
            statusManager.show('⚠️ Engine warmup incomplete - first processing may take longer', 'warning', 5000);
        }
    }

    // -----------------------------------------------------------------------------
    // 5.5. Model & Reranker Loading
    // -----------------------------------------------------------------------------
    async function loadAvailableModels(retryCount = 0, skipWarmupMessages = false) {
        let loadingMessageId = null;
        try {
            console.log(`Loading available models (attempt ${retryCount + 1})`);
            if (retryCount === 0) {
                loadingMessageId = statusManager.show('Loading available models...', 'info');
            }
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000);
            const response = await fetch(MODELS_URL, { method: 'GET', signal: controller.signal });
            clearTimeout(timeoutId);
            if (response.ok) {
                const modelsData = await response.json();
                availableModels = modelsData.models || {};
                if (Object.keys(availableModels).length === 0) {
                    throw new Error('No models received from API');
                }
                const savedModel = localStorage.getItem('selectedModel');
                if (savedModel && availableModels[savedModel]) {
                    currentModel = savedModel;
                } else {
                    currentModel = modelsData.default_model || 'retriever';
                }
                availableRerankers = modelsData.rerankers || {};
                const savedReranker = localStorage.getItem('selectedReranker');
                if (savedReranker && availableRerankers[savedReranker]) {
                    currentReranker = savedReranker;
                } else {
                    currentReranker = modelsData.default_reranker || 'medcpt';
                }
                console.log('✓ Available models loaded:', Object.keys(availableModels));
                console.log('✓ Available rerankers loaded:', availableRerankers);
                isUsingFallbackModels = false;
                buildModelSelectionUI();
                buildRerankerSelectionUI();
                if (window.workflowCheckFunction) {
                    window.workflowCheckFunction();
                }
                if (loadingMessageId) {
                    statusManager.remove(loadingMessageId);
                    loadingMessageId = null;
                }
                statusManager.show('✓ Models loaded successfully', 'success', 3000);
                if (!skipWarmupMessages) {
                    warmupAPI();
                }
            } else {
                throw new Error(`API responded with ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
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
        isUsingFallbackModels = true;
        console.log('Using fallback models with all reranker options');
        buildModelSelectionUI();
        buildRerankerSelectionUI();
        disableActionButtons('Limited functionality with fallback models');
        if (window.workflowCheckFunction) {
            window.workflowCheckFunction();
        }
        statusManager.show('ℹ️ Using offline fallback models - some features may be limited', 'info', 5000);
    }

    // -----------------------------------------------------------------------------
    // 5.6. UI Builders
    // -----------------------------------------------------------------------------
    function buildModelSelectionUI() {
        const modelContainer = document.querySelector('.model-selection-container');
        if (!modelContainer) {
            console.error('❌ Model selection container not found in HTML');
            return;
        }
        modelContainer.innerHTML = '';
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
        const sortedRerankers = Object.entries(availableRerankers).sort(([keyA], [keyB]) => {
            if (keyA === 'medcpt') return -1;
            if (keyB === 'medcpt') return 1;
            return keyA.localeCompare(keyB);
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

    // -----------------------------------------------------------------------------
    // 5.7. Event Listener Setup
    // -----------------------------------------------------------------------------
    function setupEventListeners() {
        const hamburgerToggle = document.getElementById('hamburgerToggle');
        const hamburgerDropdown = document.getElementById('hamburgerDropdown');
        if (hamburgerToggle && hamburgerDropdown) {
            hamburgerToggle.addEventListener('click', function() {
                hamburgerDropdown.classList.toggle('hidden');
            });
            document.addEventListener('click', function(event) {
                if (!hamburgerToggle.contains(event.target) && !hamburgerDropdown.contains(event.target)) {
                    hamburgerDropdown.classList.add('hidden');
                }
            });
        }
        document.getElementById('newUploadBtn')?.addEventListener('click', startNewUpload);
        document.getElementById('exportMappingsBtn')?.addEventListener('click', exportResults);
        document.getElementById('validateResultsBtn')?.addEventListener('click', startValidation);
        setupHomepageWorkflow();
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

    // -----------------------------------------------------------------------------
    // 5.8. Main UI Flow Control
    // -----------------------------------------------------------------------------
    function startNewUpload() {
        resultsSection.style.display = 'none';
        const advancedSection = document.getElementById('advancedSection');
        if (advancedSection) advancedSection.style.display = 'none';
        const modelSettingsSection = document.getElementById('modelSettingsSection');
        if (modelSettingsSection) modelSettingsSection.style.display = 'none';
        const heroSection = document.querySelector('.hero-section');
        const workflowSection = document.getElementById('workflowSection');
        if (heroSection) heroSection.style.display = 'block';
        if (workflowSection) workflowSection.style.display = 'none';
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

    function scrollToModelSelection() {
        if (window.innerWidth <= 768) {
            setTimeout(() => {
                const modelStep = document.getElementById('retrieverStep');
                if (modelStep) {
                    modelStep.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 300);
        }
    }

    // -----------------------------------------------------------------------------
    // 5.9. Core Processing Logic
    // -----------------------------------------------------------------------------
    async function processExams(codes, jobName) {
        const totalCodes = codes.length;
        if (totalCodes >= BATCH_THRESHOLD) {
            statusManager.show(`Large dataset detected (${totalCodes} items). Using batch processing.`, 'info', 3000);
            await processBatch(codes, jobName);
        } else {
            statusManager.show(`Small dataset detected (${totalCodes} items). Using individual processing.`, 'info', 3000);
            await processIndividual(codes, jobName);
        }
    }

    async function processFile(file) {
        disableActionButtons('Processing uploaded file...');
        if (!file.name.endsWith('.json')) {
            statusManager.show('Please upload a valid JSON file.', 'error', 5000);
            enableActionButtons();
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
                enableActionButtons();
            }
        };
        reader.readAsText(file);
    }
    
    async function runRandomSample() {
        disableActionButtons('Processing random sample...');
        let statusId = null;
        try {
            if (mainCard) mainCard.style.display = 'none';
            statusManager.clearAll();
            const modelDisplayName = formatModelName(currentModel);
            const rerankerDisplayName = formatRerankerName(currentReranker);
            statusId = statusManager.showProgress(`Running random sample with ${modelDisplayName} → ${rerankerDisplayName}`, 0, 100);
            let pollingActive = true;
            let batchId = null;
            const pollProgress = async () => {
                if (!pollingActive || !batchId) {
                    if (pollingActive) setTimeout(pollProgress, 100);
                    return;
                }
                try {
                    const progressResponse = await fetch(`${apiConfig.baseUrl}/batch_progress/${batchId}`);
                    if (progressResponse.ok && pollingActive) {
                        const progressData = await progressResponse.json();
                        const { percentage = 0, processed = 0, total = 100, success = 0, errors = 0 } = progressData;
                        if (statusId) {
                            statusManager.updateProgress(statusId, processed, total, `Random sample (${percentage}% - ${success} success, ${errors} errors)`);
                        }
                        if (percentage < 100 && processed < total && pollingActive) {
                            setTimeout(pollProgress, 500);
                        } else {
                            pollingActive = false;
                        }
                    } else if (progressResponse.status === 404 && pollingActive) {
                        setTimeout(pollProgress, 500);
                    }
                } catch (progressError) {
                    if (pollingActive) setTimeout(pollProgress, 1000);
                }
            };
            setTimeout(pollProgress, 100);
            setTimeout(() => { pollingActive = false; }, 120000);

            const enableSecondary = document.getElementById('enableSecondaryPipeline')?.checked || false;
            const sampleSize = parseInt(document.getElementById('sampleSizeInput').value) || 100;
            const response = await fetch(`${apiConfig.baseUrl}/random_sample`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: currentModel, reranker: currentReranker, enable_secondary_pipeline: enableSecondary, sample_size: sampleSize })
            });
            
            if (!response.ok) {
                pollingActive = false;
                throw new Error(`Random sample failed: ${response.statusText}`);
            }
            const result = await response.json();
            if (result.error) {
                pollingActive = false;
                throw new Error(result.error);
            }
            if (result.batch_id) {
                batchId = result.batch_id;
            }
            pollingActive = false;
            if (statusId) statusManager.remove(statusId);
            statusId = statusManager.show(`✅ Processing completed! ${result.processing_stats.successful || result.processing_stats.processed_successfully || 'Unknown'} items processed`, 'success', 2000);
            await new Promise(resolve => setTimeout(resolve, 2000));
            if (statusId) statusManager.remove(statusId);
            statusId = statusManager.show('Fetching results for display...', 'progress');
            
            if (result.r2_url) {
                try {
                    const resultsResponse = await fetch(result.r2_url);
                    if (resultsResponse.ok) {
                        const resultsData = await resultsResponse.json();
                        const results = resultsData.results || resultsData;
                        if (results && results.length > 0) {
                            if (statusId) statusManager.remove(statusId);
                            statusId = statusManager.show('Analyzing results and generating display...', 'progress');
                            const mappedResults = results.map(item => ({
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
                            }));
                            allMappings = mappedResults;
                            updatePageTitle(`Random Sample (${result.processing_stats.sample_size || result.processing_stats.total_processed} items)`);
                            try {
                                runAnalysis(allMappings);
                                const successMessage = `✅ Random sample completed! ${result.processing_stats?.processed_successfully || result.processing_stats.successful || 'Unknown'} items processed`;
                                statusManager.show(successMessage, 'success', 5000);
                                if (mainCard) mainCard.style.display = 'block';
                            } catch (analysisError) {
                                console.error('Error during results analysis:', analysisError);
                                statusManager.show('❌ Error displaying results', 'error', 5000);
                                if (mainCard) mainCard.style.display = 'block';
                            }
                        } else {
                            throw new Error(`No results found in R2 data. Structure: ${JSON.stringify(Object.keys(resultsData || {}))}`);
                        }
                    } else {
                        throw new Error(`Failed to fetch results: ${resultsResponse.statusText}`);
                    }
                } catch (fetchError) {
                    console.error('Failed to fetch results from R2:', fetchError);
                    if (statusId) statusManager.remove(statusId);
                    const successMessage = `✅ Random sample completed! ${result.processing_stats.successful} items processed`;
                    const urlMessage = `<br><a href="${result.r2_url}" target="_blank" style="color: #4CAF50; text-decoration: underline;">View Results on R2</a>`;
                    statusManager.show(successMessage + urlMessage, 'success', 10000);
                }
            } else {
                if (statusId) statusManager.remove(statusId);
                statusManager.show('✅ Processing completed but no results URL available', 'warning', 5000);
            }
        } catch (error) {
            console.error('Random sample failed:', error);
            if (statusId) statusManager.remove(statusId);
            statusManager.show(`❌ Random Sample Failed: ${error.message}`, 'error', 0);
            if (mainCard) mainCard.style.display = 'block';
        } finally {
            if (randomSampleButton) {
                randomSampleButton.disabled = false;
                randomSampleButton.innerHTML = 'Random Sample';
            }
            enableActionButtons();
        }
    }

    async function processBatch(codes, jobName) {
        allMappings = [];
        const totalCodes = codes.length;
        let progressId = null;
        try {
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
            if (batchResult.batch_id && progressId) {
                const pollProgress = async () => {
                    try {
                        const progressResponse = await fetch(`${apiConfig.baseUrl}/batch_progress/${batchResult.batch_id}`);
                        if (progressResponse.ok) {
                            const progressData = await progressResponse.json();
                            const { percentage = 0, processed = 0, total = totalCodes, success = 0, errors = 0 } = progressData;
                            statusManager.updateProgress(progressId, processed, total, `Processing ${jobName} (${percentage}% - ${success} success, ${errors} errors)`);
                            if (percentage < 100 && processed < total) {
                                setTimeout(pollProgress, 1000);
                            } else {
                                statusManager.updateProgress(progressId, total, total, `Completed processing ${jobName} (${success} success, ${errors} errors)`);
                            }
                        } else {
                            statusManager.updateProgress(progressId, totalCodes, totalCodes, `Completed processing ${jobName}`);
                        }
                    } catch (progressError) {
                        statusManager.updateProgress(progressId, totalCodes, totalCodes, `Completed processing ${jobName}`);
                    }
                };
                setTimeout(pollProgress, 500);
                await new Promise(resolve => setTimeout(resolve, 2000));
            } else if (progressId) {
                statusManager.updateProgress(progressId, totalCodes, totalCodes, `Completed processing ${jobName}`);
            }
            if (batchResult.r2_url) {
                try {
                    const r2Response = await fetch(batchResult.r2_url);
                    if (r2Response.ok) {
                        const r2Data = await r2Response.json();
                        if (r2Data.results && r2Data.results.length > 0) {
                            const chunkMappings = r2Data.results.map(item => ({
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
                            }));
                            allMappings.push(...chunkMappings);
                        } else {
                            throw new Error('No results found in R2 data');
                        }
                    } else {
                        throw new Error(`Failed to fetch from R2: ${r2Response.statusText}`);
                    }
                } catch (error) {
                    statusManager.show(`Processing complete. <a href="${batchResult.r2_url}" target="_blank">View results on R2</a>`, 'success', 0);
                    return;
                }
            } else if (batchResult.results) {
                const chunkMappings = batchResult.results.map(item => ({
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
                }));
                allMappings.push(...chunkMappings);
            } else {
                throw new Error('Unexpected response format from server. No R2 URL or inline results found.');
            }
            statusManager.show(`Successfully processed ${allMappings.length} records from ${jobName}.`, 'success', 5000);
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
            const concurrencyLimit = 3;
            const results = [];
            for (let i = 0; i < codes.length; i += concurrencyLimit) {
                const batch = codes.slice(i, i + concurrencyLimit);
                const batchPromises = batch.map(async (code) => {
                    try {
                        const examData = { exam_name: code.EXAM_NAME, modality_code: code.MODALITY_CODE, model: currentModel, reranker: currentReranker };
                        const response = await fetch(INDIVIDUAL_API_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(examData) });
                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`API failed: ${errorText}`);
                        }
                        const result = await response.json();
                        return { status: 'success', input: code, output: result };
                    } catch (error) {
                        return { status: 'error', input: code, error: error.message };
                    }
                });
                const batchResults = await Promise.all(batchPromises);
                results.push(...batchResults);
                processedCount = results.filter(r => r.status === 'success').length;
                errorCount = results.filter(r => r.status === 'error').length;
                if (progressId) {
                    statusManager.updateProgress(progressId, processedCount + errorCount, totalCodes, `Processing ${jobName}`);
                }
            }
            const chunkMappings = results.map(item => ({
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
            }));
            allMappings.push(...chunkMappings);
            statusManager.show(`Successfully processed ${processedCount} records. ${errorCount > 0 ? `${errorCount} errors.` : ''}`, errorCount > 0 ? 'warning' : 'success', 5000);
            runAnalysis(allMappings);
        } catch (error) {
            if (progressId) statusManager.remove(progressId);
            statusManager.show(`Individual processing failed: ${error.message}`, 'error', 0);
            console.error('Individual processing error:', error);
        }
    }

    // -----------------------------------------------------------------------------
    // 5.10. Config Editor Logic
    // -----------------------------------------------------------------------------
    async function openConfigEditor() {
        if (configEditorModal) {
            configEditorModal.style.display = 'block';
            document.body.style.overflow = 'hidden';
            await loadCurrentConfig();
        }
    }
    
    function closeConfigEditor() {
        if (configEditorModal) {
            configEditorModal.style.display = 'none';
            document.body.style.overflow = 'auto';
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
            const response = await fetch(`${apiConfig.baseUrl}/config/current`, { method: 'GET' });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Failed to load config: ${response.statusText}`);
            }
            const result = await response.json();
            configEditor.value = result.config_yaml;
            configStatus.textContent = `Loaded at ${new Date(result.timestamp).toLocaleTimeString()}`;
        } catch (error) {
            console.error('Failed to load config:', error);
            configEditor.value = `# Error loading configuration:
# ${error.message}`;
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
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config_yaml: configYamlContent })
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Save failed: ${response.statusText}`);
            }
            const result = await response.json();
            configStatus.textContent = `Saved at ${new Date(result.timestamp).toLocaleTimeString()}`;
            statusManager.show('✓ Config saved successfully. Cache rebuild initiated.', 'success', 8000);
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

    // -----------------------------------------------------------------------------
    // 5.11. Results Analysis & Display
    // -----------------------------------------------------------------------------
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
        const heroSection = document.querySelector('.hero-section');
        const workflowSection = document.getElementById('workflowSection');
        if (heroSection) heroSection.style.display = 'none';
        if (workflowSection) workflowSection.style.display = 'none';
        mainCard.style.display = 'block';
    }

    function updateResultsTitle() {
        const titleElement = document.getElementById('resultsTitle');
        const modelDisplayName = formatModelName(currentModel);
        const rerankerDisplayName = formatRerankerName(currentReranker);
        titleElement.textContent = `Cleaning Results with ${modelDisplayName} → ${rerankerDisplayName}`;
    }
    
    function updatePageTitle(title) {
        document.title = `${title} - Radiology Cleaner`;
        const titleElement = document.getElementById('resultsTitle');
        if (titleElement) {
            titleElement.textContent = title;
        }
    }

    function generateSourceLegend(mappings) {
        const uniqueSources = [...new Set(mappings.map(item => item.data_source))];
        const sourceNames = getSourceNames();
        let legendContainer = document.getElementById('sourceLegend');
        if (!legendContainer) {
            legendContainer = document.createElement('div');
            legendContainer.id = 'sourceLegend';
            legendContainer.className = 'source-legend';
            const fullView = document.getElementById('fullView');
            if (fullView) {
                fullView.insertBefore(legendContainer, fullView.firstChild);
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

    const sourceColorPalette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#ff1493', '#00ced1', '#ff4500', '#32cd32', '#ba55d3'];
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
        document.getElementById('tableInfo').textContent = `Showing ${startIndex + 1}-${Math.min(endIndex, sortedMappings.length)} of ${sortedMappings.length} results`;
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

    function displayResults(results) {
        resultsBody.innerHTML = '';
        const resultsMobile = document.getElementById('resultsMobile');
        if (resultsMobile) resultsMobile.innerHTML = '';
        results.forEach(item => {
            const row = resultsBody.insertRow();
            const sourceCell = row.insertCell();
            sourceCell.style.cssText = `width: 12px; padding: 0; background-color: ${getSourceColor(item.data_source)}; border-right: none; position: relative;`;
            const sourceNames = getSourceNames();
            sourceCell.title = sourceNames[item.data_source] || item.data_source;
            row.insertCell().textContent = item.exam_code;
            row.insertCell().textContent = item.exam_name;
            const cleanNameCell = row.insertCell();
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
                const tooltipContainer = cleanNameCell.querySelector('.tooltip-container');
                const tooltipContent = cleanNameCell.querySelector('.tooltip-content');
                tooltipContainer.addEventListener('mouseenter', function(e) {
                    const rect = this.getBoundingClientRect();
                    const tooltipRect = tooltipContent.getBoundingClientRect();
                    let left = rect.right + 10;
                    let top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                    if (left + tooltipRect.width > window.innerWidth) {
                        left = rect.left - tooltipRect.width - 10;
                    }
                    if (top < 0) top = 10;
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
            if (resultsMobile) {
                const card = document.createElement('div');
                card.className = 'result-card';
                const sourceName = getSourceDisplayName(item.data_source);
                const snomedInfo = item.snomed?.fsn ? `${item.snomed.fsn}${item.snomed.id ? ` (${item.snomed.id})` : ''}` : '-';
                card.innerHTML = `
                    <div class="result-card-header">
                        <div class="result-card-title">${item.clean_name || 'Unknown'}</div>
                        <div class="result-card-confidence ${confidenceClass}">${confidence >= 0.8 ? 'HIGH' : confidence >= 0.6 ? 'MEDIUM' : 'LOW'}</div>
                    </div>
                    <div class="result-card-body">
                        <div class="result-card-row"><span class="result-card-label">Code:</span><span class="result-card-value">${item.exam_code}</span></div>
                        <div class="result-card-row"><span class="result-card-label">Original:</span><span class="result-card-value">${item.exam_name}</span></div>
                        <div class="result-card-row"><span class="result-card-label">Source:</span><span class="result-card-value">${sourceName}</span></div>
                        <div class="result-card-row"><span class="result-card-label">SNOMED:</span><span class="result-card-value">${snomedInfo}</span></div>
                        ${tagsHTML ? `<div class="result-card-row"><span class="result-card-label">Tags:</span><span class="result-card-value">${tagsHTML}</span></div>` : ''}
                    </div>
                `;
                resultsMobile.appendChild(card);
            }
        });
    }

    function generateAnalyticsSummary(mappings) {
        const summary = {
            totalOriginalCodes: mappings.length,
            uniqueCleanNames: new Set(mappings.map(m => m.clean_name).filter(n => n && !n.startsWith('ERROR'))).size,
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
    window.closeModal = closeModal;

    // -----------------------------------------------------------------------------
    // 5.12. Consolidated View Logic
    // -----------------------------------------------------------------------------
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
    window.toggleOriginalCodes = toggleOriginalCodes;

    function displayConsolidatedResults() {
        const container = document.getElementById('consolidatedResults');
        container.innerHTML = '';
        filteredConsolidatedData.forEach(group => {
            const groupElement = document.createElement('div');
            groupElement.className = 'consolidated-group';
            const confidencePercent = Math.round(group.avgConfidence * 100);
            const confidenceClass = group.avgConfidence >= 0.8 ? 'confidence-high' : group.avgConfidence >= 0.6 ? 'confidence-medium' : 'confidence-low';
            
            const sourceNames = getSourceNames();
            const sourcesHTML = [...group.dataSources].map(source => {
                const color = getSourceColor(source);
                const displayName = sourceNames[source] || source;
                return `<span class="source-tag" style="background-color: ${color};" title="${displayName}"></span>`;
            }).join('');
            
            const secondaryPipelineHTML = group.secondaryPipelineCount > 0 ? 
                `<div class="secondary-pipeline-indicator" title="${group.secondaryPipelineCount} items improved by Secondary Pipeline">
                    <i class="fas fa-robot"></i> ${group.secondaryPipelineCount}
                 </div>` : '';

            groupElement.innerHTML = `
                <div class="consolidated-group-header" onclick="toggleOriginalCodes(this)">
                    <div class="header-main-content">
                        <div class="header-title-section">
                            <div class="consolidated-name">${group.cleanName}</div>
                            <div class="consolidated-snomed">${group.snomed?.fsn || 'No SNOMED mapping'}</div>
                        </div>
                        <div class="header-meta-section">
                            <div class="consolidated-count" title="${group.totalCount} original codes">${group.totalCount} codes</div>
                            <div class="consolidated-sources">${sourcesHTML}</div>
                            ${secondaryPipelineHTML}
                            <div class="consolidated-confidence">
                                <div class="confidence-bar-small">
                                    <div class="confidence-fill-small ${confidenceClass}" style="width: ${confidencePercent}%"></div>
                                </div>
                                <small>${confidencePercent}%</small>
                            </div>
                        </div>
                    </div>
                    <div class="expand-indicator">›</div>
                </div>
                <div class="original-codes-container" style="display: none;">
                    <table>
                        <thead>
                            <tr>
                                <th>Original Name</th>
                                <th>Code</th>
                                <th>Source</th>
                                <th>Confidence</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${group.sourceCodes.map(code => `
                                <tr>
                                    <td>${code.exam_name}</td>
                                    <td>${code.exam_code}</td>
                                    <td>${sourceNames[code.data_source] || code.data_source}</td>
                                    <td>${Math.round((code.components?.confidence || 0) * 100)}%</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            container.appendChild(groupElement);
        });
    }

    function filterConsolidatedResults(event) {
        const searchTerm = event.target.value.toLowerCase();
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
    
    
    // This function is defined later in the file - removing duplicate
    
    
    window.updateGroupDecision = function(groupId, decision) {
        const groupElement = document.querySelector(`[data-group-id="${groupId}"]`);
        if (!groupElement) return;
        const header = groupElement.querySelector('.validation-header');
        const decisionColors = { approve: '#e8f5e8', reject: '#ffebee', review: '#fff3e0', skip: '#f3e5f5', pending: '' };
        if(header) header.style.background = decisionColors[decision];
        if (['approve', 'reject', 'skip'].includes(decision)) {
            groupElement.querySelectorAll('.validation-mapping-item').forEach(el => {
                updateMappingDecisionInState(el.dataset.mappingId, decision);
                const decisionBorders = { approve: '3px solid #4caf50', reject: '3px solid #f44336', skip: '3px solid #9c27b0' };
                el.style.borderLeft = decisionBorders[decision];
                el.style.background = decisionColors[decision];
            });
        }
        statusManager.show(`Group decision: ${decision}`, 'success', 2000);
    }
    
    window.quickApproveGroup = function(groupId) {
        updateGroupDecision(groupId, 'approve');
    }
    
    
    window.skipSingletonGroup = function(groupId) {
        updateGroupDecision(groupId, 'skip');
    }
    
    window.updateMappingDecision = function(mappingId, decision) {
        updateMappingDecisionInState(mappingId, decision);
        const mappingElement = document.querySelector(`[data-mapping-id="${mappingId}"]`);
        if (mappingElement) {
            const decisionStyles = { 
                approve: { border: '3px solid #4caf50', bg: '#e8f5e8' },
                reject: { border: '3px solid #f44336', bg: '#ffebee' },
                modify: { border: '3px solid #ff9800', bg: '#fff8e1' },
                skip: { border: '3px solid #9c27b0', bg: '#f3e5f5' }
            };
            mappingElement.style.borderLeft = decisionStyles[decision].border;
            mappingElement.style.background = decisionStyles[decision].bg;
        }
        statusManager.show(`Mapping ${decision}d`, 'success', 1500);
    }
    
    function updateMappingDecisionInState(mappingId, decision) {
        if (window.currentValidationState && window.currentValidationState[mappingId]) {
            if (decision === 'unapprove') {
                // Reset to pending state when unapproving
                window.currentValidationState[mappingId].validator_decision = null;
                window.currentValidationState[mappingId].validation_status = 'pending_review';
                window.currentValidationState[mappingId].timestamp_reviewed = null;
            } else {
                window.currentValidationState[mappingId].validator_decision = decision;
                window.currentValidationState[mappingId].validation_status = 'reviewed';
                window.currentValidationState[mappingId].timestamp_reviewed = new Date().toISOString();
            }
        }
    }
    
    window.showMappingDetails = function(mappingId) {
        const state = window.currentValidationState?.[mappingId];
        if (!state) return;
        const mapping = state.original_mapping;
        const modalHTML = `
            <div id="mappingDetailsModal" class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header"><h3>Mapping Details</h3><button onclick="closeMappingDetails()" class="modal-close">&times;</button></div>
                    <div class="modal-body">
                        <div class="detail-section"><h4>Original Exam</h4><div class="detail-box"><strong>${mapping.exam_name || 'N/A'}</strong><br><small>Source: ${mapping.data_source || 'N/A'} | Code: ${mapping.exam_code || 'N/A'}</small></div></div>
                        <div class="detail-section"><h4>Matched NHS Reference</h4><div class="detail-box success"><strong>${mapping.clean_name || 'N/A'}</strong><br><small>Confidence: ${(mapping.components?.confidence || 0).toFixed(3)}</small></div></div>
                        ${mapping.components?.reasoning ? `<div class="detail-section"><h4>AI Reasoning</h4><div class="detail-box info">${mapping.components.reasoning}</div></div>` : ''}
                        ${state.needs_attention_flags.length > 0 ? `<div class="detail-section"><h4>Attention Flags</h4><div class="flag-container">${state.needs_attention_flags.map(flag => `<span class="flag-badge flag-${normalizeFlag(flag)}">${getFlagLabel(flag)}</span>`).join('')}</div></div>` : ''}
                        <div class="detail-section"><h4>Validation Notes</h4><textarea id="validationNotes" class="notes-textarea">${state.validation_notes || ''}</textarea></div>
                    </div>
                    <div class="modal-footer">
                        <button onclick="saveValidationDecision('${mappingId}', 'approve')" class="button button-success"><i class="fas fa-check"></i> Approve</button>
                        <button onclick="saveValidationDecision('${mappingId}', 'reject')" class="button button-danger"><i class="fas fa-times"></i> Reject</button>
                        <button onclick="saveValidationDecision('${mappingId}', 'modify')" class="button button-warning"><i class="fas fa-edit"></i> Modify</button>
                        <button onclick="closeMappingDetails()" class="button button-secondary">Cancel</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
    
    window.closeMappingDetails = function() {
        document.getElementById('mappingDetailsModal')?.remove();
    }
    
    window.saveValidationDecision = function(mappingId, decision) {
        const notes = document.getElementById('validationNotes')?.value || '';
        if (window.currentValidationState?.[mappingId]) {
            window.currentValidationState[mappingId].validation_notes = notes;
        }
        updateMappingDecision(mappingId, decision);
        closeMappingDetails();
    }

    async function commitValidatedDecisions() {
        console.log('💾 Committing validated decisions');
        
        if (!window.currentValidationState) {
            statusManager.show('❌ No validation state found', 'error', 3000);
            return;
        }
        
        const decisions = Object.values(window.currentValidationState);
        const approved = decisions.filter(d => d.validator_decision === 'approve').length;
        const rejected = decisions.filter(d => d.validator_decision === 'reject').length;
        const skipped = decisions.filter(d => d.validator_decision === 'skip').length;
        const pending = decisions.filter(d => !d.validator_decision || d.validator_decision === 'pending').length;
        
        if (approved === 0 && rejected === 0 && skipped === 0) {
            statusManager.show('⚠️ No decisions made yet', 'warning', 3000);
            return;
        }
        
        const message = `Commit ${approved} approved, ${rejected} rejected, and ${skipped} skipped decisions?${pending > 0 ? ` (${pending} will remain pending)` : ''}`;
        if (!confirm(message)) {
            return;
        }
        
        try {
            statusManager.show('🔄 Committing validation decisions...', 'info');
            
            // Convert currentValidationState object to array format expected by backend
            const decisionsArray = [];
            for (const [mappingId, state] of Object.entries(window.currentValidationState)) {
                if (state.validator_decision && state.validator_decision !== 'pending') {
                    const om = state.original_mapping || {};
                    // Ensure a single modality code for consistent request_hash computation on server
                    const modality_code = Array.isArray(om.modality_code) ? (om.modality_code[0] || null) : (typeof om.modality_code === 'string' ? om.modality_code : null);
                    decisionsArray.push({
                        mapping_id: mappingId,
                        decision: state.validator_decision,
                        notes: state.validation_notes || '',
                        original_mapping: om,
                        data_source: om.data_source || '',
                        exam_code: om.exam_code || '',
                        exam_name: om.exam_name || '',
                        modality_code: modality_code || (Array.isArray(om.components?.modality) ? om.components.modality[0] : undefined)
                    });
                }
            }
            
            // Prepare the payload for the backend
            const payload = {
                decisions: decisionsArray,
                summary: {
                    approved_count: approved,
                    rejected_count: rejected,
                    skipped_count: skipped,
                    pending_count: pending,
                    total_count: decisions.length,
                    timestamp: new Date().toISOString()
                }
            };
            
            // Send to validation/batch_decisions endpoint
            const response = await fetch(`${apiConfig.baseUrl}/validation/batch_decisions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Success - clear the validation state and provide feedback
            window.currentValidationState = {};
            statusManager.show(`✅ Successfully committed ${approved + rejected + skipped} validation decisions`, 'success', 5000);
            
            // Optionally clear the validation interface
            const validationInterface = document.getElementById('validationInterface');
            if (validationInterface) {
                validationInterface.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-check-circle" style="font-size: 48px; color: #4CAF50; margin-bottom: 16px;"></i>
                        <h3>Validation Decisions Committed</h3>
                        <p>Successfully processed ${approved + rejected + skipped} validation decisions.</p>
                        <p style="margin-top: 20px;">
                            <strong>Approved:</strong> ${approved} &nbsp;|&nbsp; 
                            <strong>Rejected:</strong> ${rejected} &nbsp;|&nbsp; 
                            <strong>Skipped:</strong> ${skipped}
                        </p>
                        ${result.cache_updated ? '<p style="color: #4CAF50;"><i class="fas fa-sync"></i> Validation caches updated successfully</p>' : ''}
                    </div>
                `;
            }
            
        } catch (error) {
            console.error('Error committing validation decisions:', error);
            statusManager.show(`❌ Failed to commit decisions: ${error.message}`, 'error', 5000);
        }
    }

    // -----------------------------------------------------------------------------
    // 5.13. Validation Workflow
    // -----------------------------------------------------------------------------
    // Complete validation system for human-in-the-loop mapping review and approval.
    // Provides consolidated grouping, attention flags, and decision tracking.
    // -----------------------------------------------------------------------------
    
    function startValidation() {
        console.log('🔍 Starting validation with current results');
        
        // Check if we have current results to validate
        if (!allMappings || allMappings.length === 0) {
            statusManager.show('❌ No results to validate. Please run a sample or process data first.', 'error', 5000);
            return;
        }
        
        // Switch to validation mode
        const validationCard = document.querySelector('.validation-path');
        if (validationCard) {
            validationCard.click();
        }
        
        // Auto-select "Validate Current Results" option
        setTimeout(() => {
            const validateCurrentBtn = document.getElementById('validateCurrentResultsBtn');
            if (validateCurrentBtn) {
                validateCurrentBtn.click();
            }
        }, 200);
        
        statusManager.show(`📋 Ready to validate ${allMappings.length} mappings`, 'info', 3000);
    }
    
    // JavaScript equivalent of load_mappings.py functionality
    function generateMappingId(mapping) {
        // Create a simple hash based on key mapping properties
        const keyString = `${mapping.data_source}-${mapping.exam_code}-${mapping.exam_name}-${mapping.clean_name}`;
        return btoa(keyString).replace(/[+/=]/g, '').substring(0, 32);
    }
    
    function applyAttentionFlags(mapping) {
        const flags = [];
        const confidence = mapping.components?.confidence || 0;
        
        // Low confidence flag
        if (confidence < 0.85) {
            flags.push('low_confidence');
        }
        
        // Ambiguous flag
        if (mapping.ambiguous === true) {
            flags.push('ambiguous');
        }
        
        // Singleton mapping flag (only one candidate or top candidate much higher than second)
        const candidates = mapping.all_candidates || [];
        if (candidates.length === 1) {
            flags.push('singleton_mapping');
        } else if (candidates.length > 1) {
            const topConfidence = candidates[0]?.confidence || 0;
            const secondConfidence = candidates[1]?.confidence || 0;
            if (topConfidence - secondConfidence > 0.15) {
                flags.push('high confidence gap');
            }
        }
        
        // Secondary pipeline applied flag
        if (mapping.secondary_pipeline_applied === true) {
            flags.push('secondary_pipeline');
        }
        
        return flags;
    }
    
    async function initializeValidationFromMappings(mappings) {
        console.log(`🔧 Transforming ${mappings.length} mappings into validation state`);
        
        // Include approved mappings but note their status
        const validationState = {};
        const timestamp = new Date().toISOString();
        let approvedCount = 0;
        
        for (const mapping of mappings) {
            const mappingId = generateMappingId(mapping);
            const flags = applyAttentionFlags(mapping);
            
            // Check if mapping is already approved
            const isApproved = mapping.validation_status === 'approved';
            if (isApproved) {
                approvedCount++;
                console.log(`📋 Including already approved mapping: ${mapping.exam_name} (${mapping.data_source})`);
            }
            
            validationState[mappingId] = {
                unique_mapping_id: mappingId,
                original_mapping: mapping,
                validation_status: isApproved ? 'approved' : 'pending_review',
                validator_decision: isApproved ? 'approve' : null,
                validation_notes: isApproved ? (mapping.validation_notes || 'Previously approved') : null,
                needs_attention_flags: flags,
                timestamp_created: timestamp,
                timestamp_reviewed: isApproved ? (mapping.timestamp_reviewed || timestamp) : null
            };
        }
        
        if (approvedCount > 0) {
            console.log(`📋 Included ${approvedCount} already approved mappings, ${mappings.length - approvedCount} pending for validation`);
            statusManager.show(`📋 ${approvedCount} mappings already approved, ${mappings.length - approvedCount} pending review`, 'info', 3000);
        }
        
        console.log(`✅ Created validation state for ${Object.keys(validationState).length} mappings`);
        return validationState;
    }
    
    async function handleValidateCurrentResults() {
        console.log('📋 Loading current results for validation');
        console.log('🔍 handleValidateCurrentResults called, allMappings:', allMappings?.length || 'undefined');
        
        if (!allMappings || allMappings.length === 0) {
            statusManager.show('❌ No current results found to validate', 'error', 5000);
            return;
        }
        
        try {
            statusManager.show('🔄 Initializing validation state...', 'info');
            
            // Transform allMappings into validation state
            const validationState = await initializeValidationFromMappings(allMappings);
            
            // Hide mode selection and results display, show validation interface
            const modeSelection = document.getElementById('validationModeSelection');
            const validationInterface = document.getElementById('validationInterface');
            const resultsDisplay = document.getElementById('resultsDisplay');
            const resultsSection = document.getElementById('resultsSection');
            const validationSection = document.getElementById('validationSection');
            
            if (modeSelection) modeSelection.style.display = 'none';
            if (resultsDisplay) resultsDisplay.style.display = 'none';
            if (resultsSection) resultsSection.style.display = 'none';
            
            // Make sure the validation section is visible and active
            if (validationSection) {
                console.log('🔍 Validation section element found:', validationSection);
                validationSection.classList.remove('hidden');
                validationSection.classList.add('active');
                validationSection.style.display = 'block';
                console.log('🔍 Validation section made visible and active');
            } else {
                console.error('❌ Validation section element not found!');
            }
            
            if (validationInterface) {
                console.log('🔍 Validation interface element found:', validationInterface);
                console.log('🔍 Before changes - classList:', validationInterface.classList.toString());
                console.log('🔍 Before changes - style.display:', validationInterface.style.display);
                validationInterface.classList.remove('hidden');
                validationInterface.style.display = 'block';
                validationInterface.style.visibility = 'visible';
                validationInterface.hidden = false;
                console.log('🔍 After changes - classList:', validationInterface.classList.toString());
                console.log('🔍 After changes - style.display:', validationInterface.style.display);
            } else {
                console.error('❌ Validation interface element not found!');
            }
            
            // Load mappings into validation interface with validation state
            loadValidationInterface(validationState);
            
            statusManager.show(`✅ Initialized validation for ${Object.keys(validationState).length} mappings`, 'success', 3000);
        } catch (error) {
            console.error('Failed to initialize validation:', error);
            statusManager.show('❌ Failed to initialize validation', 'error', 5000);
        }
    }
    
    function handleUploadValidationFile() {
        console.log('📁 Showing file upload for validation');
        
        // Hide mode selection, show file upload
        const modeSelection = document.getElementById('validationModeSelection');
        const fileUpload = document.getElementById('validationFileUpload');
        
        if (modeSelection) modeSelection.style.display = 'none';
        if (fileUpload) {
            fileUpload.classList.remove('hidden');
            fileUpload.style.display = 'block';
        }
        
        // Trigger file input
        const fileInput = document.getElementById('decisionsFileInput');
        if (fileInput) {
            fileInput.click();
        }
    }
    
    window.loadValidationInterface = function(validationState) {
        const mappingCount = Object.keys(validationState).length;
        console.log(`🔧 Building validation interface for ${mappingCount} mappings`);
        console.log('🔍 loadValidationInterface called with state:', validationState);
        
        const validationInterface = document.getElementById('validationInterface');
        if (!validationInterface) return;
        
        // Count mappings by attention flags
        let flagCounts = {
            low_confidence: 0,
            ambiguous: 0,
            singleton_mapping: 0,
            'high confidence gap': 0,
            secondary_pipeline: 0
        };
        
        Object.values(validationState).forEach(state => {
            state.needs_attention_flags.forEach(flag => {
                if (flagCounts.hasOwnProperty(flag)) {
                    flagCounts[flag]++;
                }
            });
        });
        
        // Group mappings by NHS reference (consolidated view)
        const consolidatedGroups = window.createConsolidatedValidationGroups(validationState);
        
        // Create validation interface with statistics and consolidated groups
        const interfaceHTML = `
            <div class="validation-header">
                <div class="validation-title-container">
                    <h3 class="validation-title">
                        <i class="fas fa-clipboard-check"></i> Validation Review
                    </h3>
                    <p class="validation-subtitle">Review ${mappingCount} mappings grouped by NHS reference for efficient validation</p>
                </div>
                
                <div class="validation-stats">
                    <div class="stat-item stat-total">
                        <div class="stat-number">${mappingCount}</div>
                        <div class="stat-label">Total Mappings</div>
                    </div>
                    <div class="stat-item stat-groups">
                        <div class="stat-number">${Object.keys(consolidatedGroups).length}</div>
                        <div class="stat-label">NHS References</div>
                    </div>
                    <div class="stat-item stat-flagged">
                        <div class="stat-number">${flagCounts.low_confidence}</div>
                        <div class="stat-label">Low Confidence</div>
                    </div>
                    <div class="stat-item stat-ambiguous">
                        <div class="stat-number">${flagCounts.ambiguous}</div>
                        <div class="stat-label">Ambiguous</div>
                    </div>
                </div>
                
                <div class="validation-controls">
                    <div class="control-group">
                        <button id="expandAllBtn" class="button button-primary">
                            <i class="fas fa-expand-alt"></i> Expand All
                        </button>
                        <button id="collapseAllBtn" class="button button-secondary">
                            <i class="fas fa-compress-alt"></i> Collapse All
                        </button>
                    </div>
                    <div class="control-info">
                        <i class="fas fa-info-circle"></i>
                        <span><strong>Consolidated View:</strong> Mappings are grouped by NHS reference for bulk approval. Individual mappings can be overridden within each group.</span>
                    </div>
                </div>
            </div>
            
            <!-- Validation Toolbar -->
            <div class="validation-toolbar">
                <div class="validation-counters">
                    <div class="counter-item approved">
                        <i class="fas fa-check"></i>
                        <span>Approved:</span>
                        <span class="count" id="approvedCount">0</span>
                    </div>
                    <div class="counter-item rejected">
                        <i class="fas fa-times"></i>
                        <span>Rejected:</span>
                        <span class="count" id="rejectedCount">0</span>
                    </div>
                    <div class="counter-item skipped">
                        <i class="fas fa-clock"></i>
                        <span>Skipped:</span>
                        <span class="count" id="skippedCount">0</span>
                    </div>
                    <div class="counter-item pending">
                        <i class="fas fa-hourglass-half"></i>
                        <span>Pending:</span>
                        <span class="count" id="pendingCount">${mappingCount}</span>
                    </div>
                </div>
                
                <div class="validation-filters">
                    <label class="filter-toggle" data-filter="flagged">
                        <input type="checkbox" style="display: none;" />
                        <i class="fas fa-flag"></i>
                        <span>Flagged Only</span>
                    </label>
                    <label class="filter-toggle" data-filter="low-confidence">
                        <input type="checkbox" style="display: none;" />
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>Low Confidence</span>
                    </label>
                    <label class="filter-toggle" data-filter="ambiguous">
                        <input type="checkbox" style="display: none;" />
                        <i class="fas fa-question-circle"></i>
                        <span>Ambiguous</span>
                    </label>
                    <label class="filter-toggle" data-filter="singleton">
                        <input type="checkbox" style="display: none;" />
                        <i class="fas fa-dot-circle"></i>
                        <span>Singleton</span>
                    </label>
                    <label class="filter-toggle" data-filter="secondary">
                        <input type="checkbox" style="display: none;" />
                        <i class="fas fa-layers"></i>
                        <span>Secondary Pipeline</span>
                    </label>
                    
                    <div class="validation-sort">
                        <label for="sortSelect" style="font-size: var(--font-size-sm); margin-right: var(--space-2);">Sort:</label>
                        <select id="sortSelect" class="sort-select">
                            <option value="flagged-first">Flagged First</option>
                            <option value="group-size">Group Size (Desc)</option>
                            <option value="confidence">Avg Confidence (Asc)</option>
                            <option value="alphabetical">Alphabetical A-Z</option>
                        </select>
                    </div>
                    
                    <button class="next-flagged-btn" id="nextFlaggedBtn">
                        <i class="fas fa-arrow-right"></i>
                        Next Flagged
                    </button>
                </div>
                
                <div class="validation-search">
                    <input type="text" id="searchInput" class="search-input" placeholder="Search groups by NHS reference, exam name, code, or source..." />
                    <div class="threshold-slider-container">
                        <span style="font-size: var(--font-size-sm);">Confidence Threshold:</span>
                        <input type="range" id="confidenceThreshold" class="threshold-slider" min="0.5" max="0.95" step="0.01" value="0.7" />
                        <span class="threshold-value" id="thresholdValue">0.70</span>
                    </div>
                </div>
            </div>
            
            <div id="validationGroups" class="validation-groups-container">
                ${window.renderValidationGroups(consolidatedGroups)}
            </div>
        `;
        
        console.log('🔍 Setting validation interface HTML, length:', interfaceHTML.length);
        validationInterface.innerHTML = interfaceHTML + `
            <div class="validation-actions">
                <div class="action-group">
                    <button id="exportValidationStateBtn" class="button button-primary">
                        <i class="fas fa-download"></i> Export Validation State
                    </button>
                    <button id="commitDecisionsBtn" class="button button-success">
                        <i class="fas fa-cloud-upload-alt"></i> Commit Validated Decisions
                    </button>
                </div>
            </div>
        `;
        
        // Add event listeners for validation buttons
        window.setupValidationEventListeners(validationState);
        
        // Initialize validation toolbar functionality
        initializeValidationToolbar(validationState, consolidatedGroups);
        
        // Store validation state globally for access by other functions
        window.currentValidationState = validationState;
        window.currentConsolidatedGroups = consolidatedGroups;
    }
    
    window.createConsolidatedValidationGroups = function(validationState) {
        const groups = {};
        
        Object.values(validationState).forEach(state => {
            const mapping = state.original_mapping;
            const nhsReference = mapping.clean_name || 'Unknown';
            
            if (!groups[nhsReference]) {
                groups[nhsReference] = {
                    nhs_reference: nhsReference,
                    mappings: [],
                    group_flags: new Set(),
                    group_decision: 'pending',
                    total_mappings: 0,
                    flagged_count: 0
                };
            }
            
            groups[nhsReference].mappings.push(state);
            groups[nhsReference].total_mappings++;
            
            // Aggregate flags at group level
            state.needs_attention_flags.forEach(flag => {
                groups[nhsReference].group_flags.add(flag);
            });
            
            if (state.needs_attention_flags.length > 0) {
                groups[nhsReference].flagged_count++;
            }
        });
        
        // Convert Set to Array for easier handling
        Object.values(groups).forEach(group => {
            group.group_flags = Array.from(group.group_flags);
        });
        
        return groups;
    }
    
    // Simple hash function for stable group IDs
    window.hashString = function(str) {
        let hash = 0;
        if (str.length === 0) return hash;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash).toString(36);
    }

    // Normalize attention flag values to slug-safe CSS classnames
    window.normalizeFlag = function(flag) {
        return flag.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
    }

    // Get human-friendly label for flag
    window.getFlagLabel = function(flag) {
        return flag.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    window.renderValidationGroups = function(consolidatedGroups) {
        let html = '';
        
        Object.values(consolidatedGroups).forEach((group, index) => {
            // Use stable group ID based on NHS reference hash instead of array index
            const groupId = `group_${window.hashString(group.nhs_reference)}`;
            const hasFlags = group.flagged_count > 0;
            const flagBadges = group.group_flags.map(flag => 
                `<span class="flag-badge flag-${window.normalizeFlag(flag)}">${window.getFlagLabel(flag)}</span>`
            ).join('');
            
            // Get SNOMED-ID from first mapping in the group
            const snomedId = group.mappings[0]?.original_mapping?.snomed?.id || 'Unknown';
            const isSingleton = group.total_mappings === 1;
            
            html += `
                <div class="validation-group consolidated-group ${hasFlags ? 'validation-flagged' : ''}" data-group-id="${groupId}">
                    <div class="validation-header consolidated-header ${hasFlags ? 'flagged-header' : ''}" onclick="toggleValidationGroup('${groupId}')" style="display: grid; grid-template-rows: auto auto; gap: 8px;">
                        <div class="validation-header-row-1" style="display: flex; justify-content: space-between; align-items: center;">
                            <div class="consolidated-title-container" style="flex: 1;">
                                <div class="consolidated-title" style="font-weight: 600; font-size: 14px;">${group.nhs_reference}</div>
                                ${snomedId && snomedId !== 'Unknown' ? `<span class="snomed-inline" style="color: #666; font-size: 12px; margin-left: 8px;">SNOMED: ${snomedId}</span>` : ''}
                            </div>
                            <div class="validation-controls-inline" style="display: flex; gap: 4px;">
                                <button class="button button-sm button-success" onclick="event.stopPropagation(); quickApproveGroup('${groupId}')" title="Quick approve" style="padding: 4px 8px;">
                                    <i class="fas fa-check" style="font-size: 12px;"></i>
                                </button>
                                ${isSingleton ? `
                                    <button class="button button-sm button-secondary" onclick="event.stopPropagation(); skipSingletonGroup('${groupId}')" title="Skip for later review" style="padding: 4px 8px;">
                                        Skip
                                    </button>
                                ` : ''}
                            </div>
                            <span class="expand-icon" style="margin-left: 8px;"></span>
                        </div>
                        <div class="validation-header-row-2" style="display: flex; justify-content: space-between; align-items: center;">
                            <div class="validation-meta-info" style="display: flex; gap: 12px; align-items: center;">
                                <span class="consolidated-count" style="color: #666; font-size: 12px;">${group.total_mappings} mapping${group.total_mappings !== 1 ? 's' : ''}</span>
                                ${group.flagged_count > 0 ? `<span class="flagged-count" style="color: #ff9800; font-size: 12px;"><i class="fas fa-exclamation-triangle"></i> ${group.flagged_count} flagged</span>` : ''}
                            </div>
                            <div class="validation-flags" style="display: flex; gap: 4px;">
                                ${flagBadges}
                            </div>
                        </div>
                    </div>
                    <div class="validation-body consolidated-body" id="${groupId}_content" style="display: none;">
                        ${window.renderGroupMappings(group.mappings, groupId)}
                    </div>
                </div>
            `;
        });
        
        return html;
    }
    
    window.renderGroupMappings = function(mappings, groupId) {
        let html = '<div class="validation-mappings-container">';
        
        mappings.forEach((state, index) => {
            const mapping = state.original_mapping;
            const mappingId = state.unique_mapping_id;
            const hasFlags = state.needs_attention_flags.length > 0;
            const confidence = mapping.components?.confidence || 0;
            const confidencePercent = Math.round(confidence * 100);
            const confidenceClass = confidence >= 0.8 ? 'confidence-high' : confidence >= 0.6 ? 'confidence-medium' : 'confidence-low';
            
            // Check validation status
            const isApproved = state.validation_status === 'approved';
            const isRejected = state.validation_status === 'rejected';
            const isPending = state.validation_status === 'pending_review';
            
            const flagBadges = state.needs_attention_flags.map(flag => 
                `<span class="flag-badge flag-${window.normalizeFlag(flag)}">${window.getFlagLabel(flag)}</span>`
            ).join('');
            
            // Status badge
            let statusBadge = '';
            if (isApproved) {
                statusBadge = '<span class="status-badge status-approved"><i class="fas fa-check"></i> Approved</span>';
            } else if (isRejected) {
                statusBadge = '<span class="status-badge status-rejected"><i class="fas fa-times"></i> Rejected</span>';
            }
            
            html += `
                <div class="validation-mapping-item ${hasFlags ? 'mapping-flagged' : ''} ${isApproved ? 'mapping-approved' : ''} ${isRejected ? 'mapping-rejected' : ''}" data-mapping-id="${mappingId}">
                    <div class="mapping-content">
                        <div class="mapping-header">
                            <div class="mapping-title">
                                ${mapping.exam_name || 'Unknown Exam'}
                                ${statusBadge}
                            </div>
                            <div class="mapping-actions">
                                ${isApproved ? `
                                    <button class="button button-sm button-warning" onclick="updateMappingDecision('${mappingId}', 'unapprove')" title="Unapprove mapping" style="padding: 4px 8px;">
                                        <i class="fas fa-undo" style="font-size: 12px;"></i>
                                    </button>
                                ` : `
                                    <button class="button button-sm button-success" onclick="updateMappingDecision('${mappingId}', 'approve')" title="Approve mapping" style="padding: 4px 8px;">
                                        <i class="fas fa-check" style="font-size: 12px;"></i>
                                    </button>
                                    <button class="button button-sm button-danger" onclick="updateMappingDecision('${mappingId}', 'reject')" title="Reject mapping" style="padding: 4px 8px;">
                                        <i class="fas fa-times" style="font-size: 12px;"></i>
                                    </button>
                                `}
                                <button class="button button-sm button-warning" onclick="showMappingDetails('${mappingId}')" title="View details" style="padding: 4px 8px;">
                                    <i class="fas fa-info-circle" style="font-size: 12px;"></i>
                                </button>
                            </div>
                        </div>
                        <div class="mapping-details">
                            <div class="mapping-meta-inline">
                                <span class="meta-item-inline">
                                    <i class="fas fa-database"></i> <strong>Source:</strong> ${mapping.data_source || 'Unknown'}
                                </span>
                                <span class="meta-separator">•</span>
                                <span class="meta-item-inline">
                                    <i class="fas fa-barcode"></i> <strong>Code:</strong> ${mapping.exam_code || 'N/A'}
                                </span>
                                <span class="meta-separator">•</span>
                                <span class="meta-item-inline">
                                    <i class="fas fa-chart-bar"></i> <strong>Confidence:</strong> 
                                    <span class="confidence-inline ${confidenceClass}">${confidencePercent}%</span>
                                </span>
                                ${isApproved && state.timestamp_reviewed ? `
                                    <span class="meta-separator">•</span>
                                    <span class="meta-item-inline">
                                        <i class="fas fa-clock"></i> <strong>Approved:</strong> ${new Date(state.timestamp_reviewed).toLocaleDateString()}
                                    </span>
                                ` : ''}
                            </div>
                            ${flagBadges ? `<div class="mapping-flags">${flagBadges}</div>` : ''}
                            ${state.validation_notes ? `
                                <div class="mapping-notes">
                                    <div class="notes-header">
                                        <i class="fas fa-sticky-note"></i>
                                        <strong>Validation Notes:</strong>
                                    </div>
                                    <div class="notes-content">${state.validation_notes}</div>
                                </div>
                            ` : ''}
                            ${mapping.components?.reasoning ? `
                                <div class="mapping-reasoning">
                                    <div class="reasoning-header">
                                        <i class="fas fa-brain"></i>
                                        <strong>AI Reasoning:</strong>
                                    </div>
                                    <div class="reasoning-content">${mapping.components.reasoning}</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        return html;
    }
    
    window.setupValidationEventListeners = function(validationState) {
        // Bulk action buttons
        const expandAllBtn = document.getElementById('expandAllBtn');
        const collapseAllBtn = document.getElementById('collapseAllBtn');
        const commitBtn = document.getElementById('commitDecisionsBtn');
        const exportBtn = document.getElementById('exportValidationStateBtn');
        
        if (expandAllBtn) {
            expandAllBtn.addEventListener('click', () => toggleAllGroups(true));
        }
        
        if (collapseAllBtn) {
            collapseAllBtn.addEventListener('click', () => toggleAllGroups(false));
        }
        
        if (commitBtn) {
            commitBtn.addEventListener('click', commitValidatedDecisions);
        }
        
        if (exportBtn) {
            exportBtn.addEventListener('click', () => exportValidationState(validationState));
        }
    }
    
    // Validation Toolbar State Management
    let validationToolbarState = {
        filters: {
            flagged: false,
            'low-confidence': false,
            ambiguous: false,
            singleton: false,
            secondary: false
        },
        sort: 'flagged-first',
        search: '',
        confidenceThreshold: 0.7,
        activeGroupIndex: -1,
        activeMappingIndex: -1
    };

    function initializeValidationToolbar(validationState, consolidatedGroups) {
        // Initialize filter toggles
        const filterToggles = document.querySelectorAll('[data-filter]');
        filterToggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                const filter = toggle.getAttribute('data-filter');
                validationToolbarState.filters[filter] = !validationToolbarState.filters[filter];
                toggle.classList.toggle('active', validationToolbarState.filters[filter]);
                filterAndDisplayGroups();
            });
        });

        // Initialize sort dropdown
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                validationToolbarState.sort = e.target.value;
                filterAndDisplayGroups();
            });
        }

        // Initialize search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    validationToolbarState.search = e.target.value.toLowerCase();
                    filterAndDisplayGroups();
                }, 300); // Debounce search
            });
        }

        // Initialize confidence threshold slider
        const thresholdSlider = document.getElementById('confidenceThreshold');
        const thresholdValue = document.getElementById('thresholdValue');
        if (thresholdSlider && thresholdValue) {
            thresholdSlider.addEventListener('input', (e) => {
                validationToolbarState.confidenceThreshold = parseFloat(e.target.value);
                thresholdValue.textContent = validationToolbarState.confidenceThreshold.toFixed(2);
                filterAndDisplayGroups();
            });
        }

        // Initialize next flagged button
        const nextFlaggedBtn = document.getElementById('nextFlaggedBtn');
        if (nextFlaggedBtn) {
            nextFlaggedBtn.addEventListener('click', () => {
                jumpToNextFlaggedGroup();
            });
        }

        // Initialize keyboard shortcuts
        initializeKeyboardShortcuts();

        // Initial render
        filterAndDisplayGroups();
    }

    function filterAndDisplayGroups() {
        if (!window.currentConsolidatedGroups) return;
        
        const groups = window.currentConsolidatedGroups;
        let filteredGroups = Object.values(groups);

        // Apply filters
        if (validationToolbarState.filters.flagged) {
            filteredGroups = filteredGroups.filter(group => group.flagged_count > 0);
        }

        if (validationToolbarState.filters['low-confidence']) {
            filteredGroups = filteredGroups.filter(group => 
                group.mappings.some(m => (m.original_mapping.components?.confidence || 0) < validationToolbarState.confidenceThreshold)
            );
        }

        if (validationToolbarState.filters.ambiguous) {
            filteredGroups = filteredGroups.filter(group => 
                group.group_flags.includes('ambiguous')
            );
        }

        if (validationToolbarState.filters.singleton) {
            filteredGroups = filteredGroups.filter(group => group.total_mappings === 1);
        }

        if (validationToolbarState.filters.secondary) {
            filteredGroups = filteredGroups.filter(group => 
                group.group_flags.includes('secondary_pipeline')
            );
        }

        // Apply search
        if (validationToolbarState.search) {
            filteredGroups = filteredGroups.filter(group => {
                const searchTerm = validationToolbarState.search;
                return group.nhs_reference.toLowerCase().includes(searchTerm) ||
                       group.mappings.some(m => 
                           (m.original_mapping.exam_name || '').toLowerCase().includes(searchTerm) ||
                           (m.original_mapping.data_source || '').toLowerCase().includes(searchTerm)
                       );
            });
        }

        // Apply sorting
        switch (validationToolbarState.sort) {
            case 'flagged-first':
                filteredGroups.sort((a, b) => {
                    if (a.flagged_count > 0 && b.flagged_count === 0) return -1;
                    if (a.flagged_count === 0 && b.flagged_count > 0) return 1;
                    return b.flagged_count - a.flagged_count;
                });
                break;
            case 'group-size':
                filteredGroups.sort((a, b) => b.total_mappings - a.total_mappings);
                break;
            case 'confidence':
                filteredGroups.sort((a, b) => {
                    const avgA = a.mappings.reduce((sum, m) => sum + (m.original_mapping.components?.confidence || 0), 0) / a.mappings.length;
                    const avgB = b.mappings.reduce((sum, m) => sum + (m.original_mapping.components?.confidence || 0), 0) / b.mappings.length;
                    return avgA - avgB;
                });
                break;
            case 'alphabetical':
                filteredGroups.sort((a, b) => a.nhs_reference.localeCompare(b.nhs_reference));
                break;
        }

        // Update the display
        const container = document.getElementById('validationGroups');
        if (container) {
            // Convert array back to object structure for renderValidationGroups
            const filteredGroupsObj = {};
            filteredGroups.forEach(group => {
                filteredGroupsObj[group.nhs_reference] = group;
            });
            container.innerHTML = renderValidationGroups(filteredGroupsObj);
        }

        // Update next flagged button state
        updateNextFlaggedButton(filteredGroups);
    }

    function updateNextFlaggedButton(filteredGroups) {
        const nextFlaggedBtn = document.getElementById('nextFlaggedBtn');
        if (!nextFlaggedBtn) return;

        const flaggedGroups = filteredGroups.filter(group => group.flagged_count > 0);
        nextFlaggedBtn.disabled = flaggedGroups.length === 0;
    }

    function jumpToNextFlaggedGroup() {
        const flaggedGroups = document.querySelectorAll('.validation-group.validation-flagged');
        if (flaggedGroups.length === 0) return;

        let nextIndex = 0;
        if (validationToolbarState.activeGroupIndex >= 0) {
            const currentGroup = document.querySelector(`[data-group-id="group_${validationToolbarState.activeGroupIndex}"]`);
            if (currentGroup) {
                const allGroups = Array.from(document.querySelectorAll('.validation-group'));
                const currentIdx = allGroups.indexOf(currentGroup);
                
                // Find next flagged group after current
                for (let i = currentIdx + 1; i < allGroups.length; i++) {
                    if (allGroups[i].classList.contains('validation-flagged')) {
                        nextIndex = i;
                        break;
                    }
                }
            }
        }

        if (flaggedGroups[nextIndex]) {
            flaggedGroups[nextIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
            // Optionally expand the group
            const groupId = flaggedGroups[nextIndex].getAttribute('data-group-id');
            if (groupId) {
                window.toggleValidationGroup(groupId);
            }
        }
    }

    function initializeKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Only handle shortcuts when not in input fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
                // Allow specific shortcuts even in inputs
                if (e.key === 'Escape') {
                    e.target.blur();
                }
                return;
            }

            switch (e.key.toLowerCase()) {
                case 'a':
                    e.preventDefault();
                    // Approve focused mapping or group
                    console.log('Keyboard shortcut: Approve');
                    break;
                case 'r':
                    e.preventDefault();
                    // Reject focused mapping or group
                    console.log('Keyboard shortcut: Reject');
                    break;
                case 's':
                    e.preventDefault();
                    // Skip focused mapping or group
                    console.log('Keyboard shortcut: Skip');
                    break;
                case 'j':
                    e.preventDefault();
                    // Next mapping within group
                    navigateMapping(1);
                    break;
                case 'k':
                    e.preventDefault();
                    // Previous mapping within group
                    navigateMapping(-1);
                    break;
                case 'g':
                    e.preventDefault();
                    if (e.shiftKey) {
                        // Previous group
                        navigateGroup(-1);
                    } else {
                        // Next group
                        navigateGroup(1);
                    }
                    break;
                case ' ':
                case 'enter':
                    e.preventDefault();
                    // Toggle focused group
                    toggleFocusedGroup();
                    break;
                case 'f':
                    e.preventDefault();
                    // Toggle flagged filter
                    const flaggedToggle = document.querySelector('[data-filter="flagged"]');
                    if (flaggedToggle) flaggedToggle.click();
                    break;
                case '/':
                    e.preventDefault();
                    // Focus search box
                    const searchInput = document.getElementById('searchInput');
                    if (searchInput) searchInput.focus();
                    break;
                case '?':
                    e.preventDefault();
                    // Show shortcuts help
                    showKeyboardShortcutsHelp();
                    break;
                case 'z':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        // Undo last action
                        undoLastAction();
                    }
                    break;
            }
        });
    }

    function navigateMapping(direction) {
        // Implementation for J/K navigation within groups
        console.log('Navigate mapping:', direction);
    }

    function navigateGroup(direction) {
        // Implementation for G/Shift+G navigation between groups
        console.log('Navigate group:', direction);
    }

    function toggleFocusedGroup() {
        // Implementation for Space/Enter to toggle group
        console.log('Toggle focused group');
    }

    function showKeyboardShortcutsHelp() {
        // Implementation for ? to show help overlay
        alert(`Keyboard Shortcuts:
        
A - Approve focused mapping/group
R - Reject focused mapping/group  
S - Skip focused mapping/group
J/K - Next/Previous mapping within group
G/Shift+G - Next/Previous group
Space/Enter - Expand/Collapse focused group
F - Toggle "Flagged only" filter
/ - Focus search box
? - Show this help
Ctrl+Z - Undo last action`);
    }

    function undoLastAction() {
        // Implementation for Ctrl+Z undo
        console.log('Undo last action');
    }
    
    function exportValidationState(validationState) {
        console.log('📥 Exporting validation state');
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `validation_state_${timestamp}.json`;
        
        const exportData = {
            export_timestamp: new Date().toISOString(),
            mapping_count: Object.keys(validationState).length,
            validation_state: validationState
        };
        
        downloadJSON(exportData, filename);
        statusManager.show(`✅ Exported validation state: ${filename}`, 'success', 3000);
    }
    
    // Validation interaction functions - exposed globally for HTML onclick handlers
    window.toggleValidationGroup = function(groupId) {
        const content = document.getElementById(`${groupId}_content`);
        const toggle = document.querySelector(`[data-group-id="${groupId}"] .expand-icon`);
        const header = document.querySelector(`[data-group-id="${groupId}"] .validation-header`);
        
        if (content) {
            if (content.style.display === 'none' || content.style.display === '') {
                content.style.display = 'block';
                if (header) header.classList.add('expanded');
                if (toggle) toggle.style.transform = 'rotate(90deg)';
            } else {
                content.style.display = 'none';
                if (header) header.classList.remove('expanded');
                if (toggle) toggle.style.transform = 'rotate(0deg)';
            }
        }
    }
    
    function toggleAllGroups(expand) {
        const groups = document.querySelectorAll('.validation-group');
        groups.forEach((group) => {
            // Get groupId from data attribute instead of using index
            const groupId = group.getAttribute('data-group-id');
            const content = document.getElementById(`${groupId}_content`);
            const toggle = group.querySelector('.expand-icon');
            const header = group.querySelector('.validation-header');
            
            if (content) {
                if (expand) {
                    content.style.display = 'block';
                    if (header) header.classList.add('expanded');
                    if (toggle) toggle.style.transform = 'rotate(90deg)';
                } else {
                    content.style.display = 'none';
                    if (header) header.classList.remove('expanded');
                    if (toggle) toggle.style.transform = 'rotate(0deg)';
                }
            }
        });
    }
    
    window.updateGroupDecision = function(groupId, decision) {
        console.log(`📝 Updating group ${groupId} decision to: ${decision}`);
        
        const groupElement = document.querySelector(`[data-group-id="${groupId}"]`);
        if (!groupElement) return;
        
        // Update visual state
        const header = groupElement.querySelector('.validation-header');
        const bgColors = {
            approve: '#e8f5e8',
            reject: '#ffebee', 
            review: '#fff3e0',
            skip: '#f3e5f5',
            default: '#f5f5f5'
        };
        if (header) header.style.background = bgColors[decision] || bgColors.default;
        
        // Update all mappings in the group if bulk decision
        if (['approve', 'reject', 'skip'].includes(decision)) {
            const mappingElements = groupElement.querySelectorAll('[data-mapping-id]');
            mappingElements.forEach(mappingEl => {
                const mappingId = mappingEl.dataset.mappingId;
                updateMappingDecisionInState(mappingId, decision);
                
                // Update visual state
                const borderColors = { approve: '#4caf50', reject: '#f44336', skip: '#9c27b0' };
                const bgColors = { approve: '#e8f5e8', reject: '#ffebee', skip: '#f3e5f5' };
                if (borderColors[decision]) {
                    mappingEl.style.borderLeft = `3px solid ${borderColors[decision]}`;
                    mappingEl.style.background = bgColors[decision];
                }
            });
        }
        
        statusManager.show(`✅ Group decision: ${decision}`, 'success', 2000);
    }
    
    window.quickApproveGroup = function(groupId) {
        updateGroupDecision(groupId, 'approve');
    }
    
    
    window.skipSingletonGroup = function(groupId) {
        updateGroupDecision(groupId, 'skip');
    }
    
    window.updateMappingDecision = function(mappingId, decision) {
        console.log(`📝 Updating mapping ${mappingId} decision to: ${decision}`);
        
        updateMappingDecisionInState(mappingId, decision);
        
        const mappingElement = document.querySelector(`[data-mapping-id="${mappingId}"]`);
        if (mappingElement) {
            // Update visual state
            const styles = {
                approve: { border: '3px solid #4caf50', bg: '#e8f5e8' },
                reject: { border: '3px solid #f44336', bg: '#ffebee' },
                modify: { border: '3px solid #ff9800', bg: '#fff8e1' },
                skip: { border: '3px solid #9c27b0', bg: '#f3e5f5' },
                unapprove: { border: '', bg: '' } // Reset to default for unapprove
            };
            
            if (styles[decision]) {
                mappingElement.style.borderLeft = styles[decision].border;
                mappingElement.style.background = styles[decision].bg;
                
                // Remove status-specific classes and add new ones
                mappingElement.classList.remove('mapping-approved', 'mapping-rejected');
                if (decision === 'approve') {
                    mappingElement.classList.add('mapping-approved');
                } else if (decision === 'reject') {
                    mappingElement.classList.add('mapping-rejected');
                } else if (decision === 'unapprove') {
                    // For unapprove, refresh the entire validation interface to update UI
                    if (window.currentValidationState && window.currentConsolidatedGroups) {
                        const validationInterface = document.getElementById('validationInterface');
                        if (validationInterface) {
                            window.loadValidationInterface(window.currentValidationState);
                        }
                    }
                }
            }
        }
        
        const actionText = decision === 'unapprove' ? 'unapproved' : `${decision}d`;
        statusManager.show(`✅ Mapping ${actionText}`, 'success', 1500);
    }
    
    window.showMappingDetails = function(mappingId) {
        const state = window.currentValidationState?.[mappingId];
        if (!state) {
            statusManager.show('❌ Mapping not found', 'error', 3000);
            return;
        }
        
        const mapping = state.original_mapping;
        
        // Create detailed view modal
        const modalHTML = `
            <div id="mappingDetailsModal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;">
                <div style="background: white; border-radius: 8px; padding: 20px; max-width: 600px; max-height: 80vh; overflow-y: auto; margin: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px;">
                        <h3 style="margin: 0; color: #1976d2;">Mapping Details</h3>
                        <button onclick="closeMappingDetails()" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <h4 style="margin: 0 0 8px 0; color: #333;">Original Exam</h4>
                        <div style="background: #f5f5f5; padding: 10px; border-radius: 4px;">
                            <strong>${mapping.exam_name || 'Unknown'}</strong><br>
                            <small>Source: ${mapping.data_source || 'Unknown'} | Code: ${mapping.exam_code || 'N/A'}</small>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <h4 style="margin: 0 0 8px 0; color: #333;">Matched NHS Reference</h4>
                        <div style="background: #e8f5e8; padding: 10px; border-radius: 4px;">
                            <strong>${mapping.clean_name || 'N/A'}</strong><br>
                            <small>Confidence: ${(mapping.components?.confidence || 0).toFixed(3)}</small>
                        </div>
                    </div>
                    
                    ${mapping.components?.reasoning ? `
                        <div style="margin-bottom: 15px;">
                            <h4 style="margin: 0 0 8px 0; color: #333;">AI Reasoning</h4>
                            <div style="background: #f0f7ff; padding: 10px; border-radius: 4px; border-left: 3px solid #2196f3;">
                                ${mapping.components.reasoning}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${state.needs_attention_flags.length > 0 ? `
                        <div style="margin-bottom: 15px;">
                            <h4 style="margin: 0 0 8px 0; color: #333;">Attention Flags</h4>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                                ${state.needs_attention_flags.map(flag => 
                                    `<span style="background: #ffecb3; color: #e65100; padding: 4px 8px; border-radius: 4px; font-size: 12px;">${getFlagLabel(flag)}</span>`
                                ).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    <div style="margin-bottom: 20px;">
                        <h4 style="margin: 0 0 8px 0; color: #333;">Validation Notes</h4>
                        <textarea id="validationNotes" placeholder="Add validation notes..." style="width: 100%; height: 60px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; resize: vertical;">${state.validation_notes || ''}</textarea>
                    </div>
                    
                    <div style="display: flex; gap: 10px; justify-content: flex-end;">
                        <button onclick="saveValidationDecision('${mappingId}', 'approve')" style="background: #4caf50; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
                            <i class="fas fa-check"></i> Approve
                        </button>
                        <button onclick="saveValidationDecision('${mappingId}', 'reject')" style="background: #f44336; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
                            <i class="fas fa-times"></i> Reject
                        </button>
                        <button onclick="saveValidationDecision('${mappingId}', 'modify')" style="background: #ff9800; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
                            <i class="fas fa-edit"></i> Modify
                        </button>
                        <button onclick="closeMappingDetails()" style="background: #607d8b; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">Cancel</button>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
    
    window.closeMappingDetails = function() {
        const modal = document.getElementById('mappingDetailsModal');
        if (modal) {
            modal.remove();
        }
    }
    
    window.saveValidationDecision = function(mappingId, decision) {
        const notes = document.getElementById('validationNotes')?.value || '';
        
        // Update state with notes
        if (window.currentValidationState?.[mappingId]) {
            window.currentValidationState[mappingId].validation_notes = notes;
        }
        
        updateMappingDecision(mappingId, decision);
        closeMappingDetails();
    }

    // -----------------------------------------------------------------------------
    // 5.14. Homepage Workflow
    // -----------------------------------------------------------------------------
    function setupHomepageWorkflow() {
        const workflowSection = document.getElementById('workflowSection');
        const runProcessingBtn = document.getElementById('runProcessingBtn');
        const runRandomSampleBtn = document.getElementById('runRandomSampleBtn');
        const sampleOptions = document.getElementById('sampleOptions');
        const dataSourceDisplay = document.getElementById('dataSourceDisplay');
        const dataSourceText = document.getElementById('dataSourceText');
        let currentDataSource = null;
        let selectedRetriever = null;
        let selectedReranker = null;

        document.querySelector('.sample-path')?.addEventListener('click', () => {
            if (buttonsDisabledForLoading) return;
            selectPath('sample');
            currentDataSource = 'sample';
            checkWorkflowCompletion();
            scrollToModelSelection();
        });
        
        document.querySelector('.upload-path')?.addEventListener('click', () => {
            if (buttonsDisabledForLoading) return;
            selectPath('upload');
            fileInput.click();
        });
        
        document.querySelector('.advanced-path')?.addEventListener('click', () => openConfigEditor());
        
        document.querySelector('.validation-path')?.addEventListener('click', () => {
            if (buttonsDisabledForLoading) return;
            selectPath('validation');
        });
        
        document.getElementById('validateCurrentResultsBtn')?.addEventListener('click', handleValidateCurrentResults);
        document.getElementById('uploadValidationFileBtn')?.addEventListener('click', handleUploadValidationFile);
        
        fileInput?.addEventListener('change', (e) => {
            if (e.target.files[0]) {
                currentDataSource = 'upload';
                dataSourceText.textContent = `File: ${e.target.files[0].name}`;
                dataSourceDisplay.style.display = 'block';
                checkWorkflowCompletion();
                scrollToModelSelection();
            }
        });
        
        runRandomSampleBtn?.addEventListener('click', async () => await runRandomSample());
        
        const sampleSizeInput = document.getElementById('sampleSizeInput');
        const randomSampleSubtext = document.getElementById('randomSampleSubtext');
        function updateSampleSizeDisplay() {
            const sampleSize = parseInt(sampleSizeInput?.value) || 100;
            if (randomSampleSubtext) randomSampleSubtext.textContent = `${sampleSize} random codes`;
        }
        sampleSizeInput?.addEventListener('input', updateSampleSizeDisplay);
        sampleSizeInput?.addEventListener('change', updateSampleSizeDisplay);
        updateSampleSizeDisplay();

        runProcessingBtn?.addEventListener('click', async () => {
            if (currentDataSource === 'upload' && fileInput.files[0]) {
                await processFile(fileInput.files[0]);
            }
        });
        
        function selectPath(path) {
            document.querySelectorAll('.action-card').forEach(card => card.classList.remove('selected'));
            const validationSection = document.getElementById('validationSection');
            if(workflowSection) workflowSection.style.display = 'none';
            if(validationSection) validationSection.style.display = 'none';

            if (path === 'sample' || path === 'upload') {
                if (workflowSection) workflowSection.style.display = 'block';
                const card = path === 'sample' ? document.querySelector('.sample-path') : document.querySelector('.upload-path');
                card?.classList.add('selected');
                resetWorkflowSteps();
            } else if (path === 'validation') {
                if (validationSection) {
                    validationSection.style.display = 'block';
                    setTimeout(() => validationSection.scrollIntoView({ behavior: 'smooth' }), 100);
                }
                document.querySelector('.validation-path')?.classList.add('selected');
            }
        }
        
        function resetWorkflowSteps() {
            ['step1', 'step2', 'step3'].forEach((s, i) => document.getElementById(s)?.classList.toggle('active', i === 0));
            ['retrieverStep', 'rerankerStep', 'runStep'].forEach((s, i) => document.getElementById(s)?.classList.toggle('active', i === 0));
            selectedRetriever = null;
            selectedReranker = null;
            runProcessingBtn.disabled = true;
            if (runRandomSampleBtn) runRandomSampleBtn.disabled = true;
        }
        
        function activateStep(stepNumber) {
            for (let i = 1; i <= 3; i++) document.getElementById(`step${i}`)?.classList.toggle('active', i <= stepNumber);
            ['retrieverStep', 'rerankerStep', 'runStep'].forEach((s, i) => document.getElementById(s)?.classList.toggle('active', i < stepNumber));
        }
        
        function checkWorkflowCompletion() {
            selectedRetriever = currentModel;
            selectedReranker = currentReranker;
            if (selectedRetriever && selectedReranker && currentDataSource) {
                if (currentDataSource === 'sample') {
                    sampleOptions.style.display = 'block';
                    runProcessingBtn.style.display = 'none';
                    const secondaryPipelineOption = document.getElementById('secondaryPipelineOption');
                    if (secondaryPipelineOption) secondaryPipelineOption.style.display = 'block';
                    runRandomSampleBtn.disabled = buttonsDisabledForLoading || isUsingFallbackModels;
                } else if (currentDataSource === 'upload') {
                    sampleOptions.style.display = 'none';
                    runProcessingBtn.style.display = 'block';
                    const secondaryPipelineOption2 = document.getElementById('secondaryPipelineOption');
                    if (secondaryPipelineOption2) secondaryPipelineOption2.style.display = 'none';
                    runProcessingBtn.disabled = buttonsDisabledForLoading || isUsingFallbackModels;
                }
                activateStep(3);
            } else if (selectedRetriever && currentDataSource) {
                activateStep(2);
            } else if (currentDataSource) {
                activateStep(1);
            }
        }
        window.workflowCheckFunction = checkWorkflowCompletion;
    }

    // -----------------------------------------------------------------------------
    // 5.15. Final Initialization Call
    // -----------------------------------------------------------------------------
    function initApp() {
        disableActionButtons('Models are loading...');
        testApiConnectivity();
        loadAvailableModels();
        setupEventListeners();
        document.getElementById('fullView').style.display = 'block';
        document.getElementById('consolidatedView').style.display = 'none';
    }

    initApp();
});


// =================================================================================
// 6. PAGE NAVIGATION HANDLING
// =================================================================================
// Ensures application state is correct on back/forward browser navigation.
// =================================================================================

window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
        const modelButtons = document.querySelectorAll('.model-toggle');
        if (modelButtons.length === 0) {
            window.loadAvailableModels(0, true);
        }
    }
});

// =================================================================================
// TESTING: Mock Validation Data (Development Only)
// =================================================================================

// Test function to create mock validation data for UI testing
window.loadMockValidationData = function() {
    console.log('Loading mock validation data for testing...');
    
    const mockValidationState = {
        "mapping_1": {
            unique_mapping_id: "mapping_1",
            original_mapping: {
                exam_name: "CT Chest without contrast",
                clean_name: "CT CHEST",
                data_source: "Test Hospital A",
                components: {
                    confidence: 0.95
                },
                snomed: {
                    id: "169069000",
                    fsn: "Computed tomography of chest"
                },
                all_candidates: [
                    { primary_name: "CT CHEST", confidence: 0.95 },
                    { primary_name: "CT THORAX", confidence: 0.82 }
                ]
            },
            needs_attention_flags: [],
            validator_decision: 'pending',
            validation_notes: ''
        },
        "mapping_2": {
            unique_mapping_id: "mapping_2",
            original_mapping: {
                exam_name: "Xray Chest PA",
                clean_name: "X-RAY CHEST",
                data_source: "Test Hospital B",
                components: {
                    confidence: 0.65
                },
                snomed: {
                    id: "399208008",
                    fsn: "Plain chest X-ray"
                },
                all_candidates: [
                    { primary_name: "X-RAY CHEST", confidence: 0.65 },
                    { primary_name: "CHEST RADIOGRAPH", confidence: 0.62 }
                ]
            },
            needs_attention_flags: ['low_confidence', 'ambiguous'],
            validator_decision: 'pending',
            validation_notes: ''
        },
        "mapping_3": {
            unique_mapping_id: "mapping_3",
            original_mapping: {
                exam_name: "CT Chest with contrast",
                clean_name: "CT CHEST",
                data_source: "Test Hospital C", 
                components: {
                    confidence: 0.88
                },
                snomed: {
                    id: "169069000",
                    fsn: "Computed tomography of chest"
                },
                all_candidates: [
                    { primary_name: "CT CHEST", confidence: 0.88 }
                ]
            },
            needs_attention_flags: [],
            validator_decision: 'pending',
            validation_notes: ''
        },
        "mapping_4": {
            unique_mapping_id: "mapping_4",
            original_mapping: {
                exam_name: "MRI Brain",
                clean_name: "MRI BRAIN",
                data_source: "Test Hospital A",
                components: {
                    confidence: 0.45
                },
                snomed: {
                    id: "278107002",
                    fsn: "Magnetic resonance imaging of brain"
                },
                all_candidates: [
                    { primary_name: "MRI BRAIN", confidence: 0.45 },
                    { primary_name: "MRI HEAD", confidence: 0.43 },
                    { primary_name: "BRAIN MRI", confidence: 0.41 }
                ]
            },
            needs_attention_flags: ['low_confidence', 'singleton_mapping'],
            validator_decision: 'pending',
            validation_notes: ''
        },
        "mapping_5": {
            unique_mapping_id: "mapping_5",
            original_mapping: {
                exam_name: "Ultrasound Abdomen",
                clean_name: "US ABDOMEN",
                data_source: "Test Hospital D",
                components: {
                    confidence: 0.78
                },
                snomed: {
                    id: "241527001",
                    fsn: "Ultrasonography of abdomen"
                },
                all_candidates: [
                    { primary_name: "US ABDOMEN", confidence: 0.78 }
                ]
            },
            needs_attention_flags: ['secondary_pipeline'],
            validator_decision: 'pending',
            validation_notes: ''
        }
    };
    
    // Load the validation interface with mock data
    loadValidationInterface(mockValidationState);
    
    // Show the validation interface
    const validationInterface = document.getElementById('validationInterface');
    if (validationInterface) {
        validationInterface.classList.remove('hidden');
        validationInterface.style.display = 'block';
    }
    
    // Hide other sections to focus on validation
    const workflowSection = document.getElementById('workflowSection');
    if (workflowSection) {
        workflowSection.style.display = 'none';
    }
    
    statusManager.show('✅ Mock validation data loaded for UI testing', 'success', 3000);
};

// Add test button to page when in development mode
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    document.addEventListener('DOMContentLoaded', function() {
        // Add test button after a delay to ensure other elements are loaded
        setTimeout(() => {
            const heroSection = document.querySelector('.hero-section');
            if (heroSection) {
                const testButton = document.createElement('button');
                testButton.textContent = '🧪 Load Mock Validation Data (DEV)';
                testButton.className = 'button button-primary';
                testButton.style.cssText = 'margin: 20px auto; display: block; background: #e91e63; border-color: #e91e63;';
                testButton.onclick = window.loadMockValidationData;
                heroSection.appendChild(testButton);
            }
        }, 1000);
    });
}