// --- START OF FILE app.js ---

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
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.id = 'statusMessageContainer';
                this.container.className = 'status-message-container';
                const fileInfo = document.getElementById('fileInfo');
                if (fileInfo && fileInfo.parentNode) {
                    fileInfo.parentNode.insertBefore(this.container, fileInfo.nextSibling);
                } else {
                    document.body.insertBefore(this.container, document.body.firstChild);
                }
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

        if (!this.progressMessage) {
            this.progressMessage = this.show(progressContent, type);
        } else {
            this.update(this.progressMessage, progressContent);
        }
        
        return this.progressMessage;
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
            .status-message-container { display: flex; flex-direction: column; gap: 8px; margin: 16px 0; }
            .processing-stage { display: flex; flex-direction: column; gap: 4px; }
            .stage-name { font-weight: 600; font-size: 15px; }
            .stage-description { font-size: 13px; opacity: 0.9; }
            .processing-stats { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; width: 100%; font-size: 13px; }
            .stats-item { display: flex; align-items: center; gap: 6px; }
            .stats-item strong { font-weight: 600; color: var(--color-gray-600, #666); }
            .progress-container { width: 100%; }
            .progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 14px; }
            .progress-message { font-weight: 500; }
            .progress-counter { font-family: var(--font-family-mono, monospace); font-size: 13px; color: var(--color-gray-600, #666); }
            .progress-bar { width: 100%; height: 8px; background-color: var(--color-gray-200, #e0e0e0); border-radius: 4px; overflow: hidden; }
            .progress-fill { height: 100%; background: linear-gradient(90deg, var(--color-primary, #3f51b5), var(--color-primary-dark, #303f9f)); border-radius: 4px; transition: width 0.3s ease; }
        `;
        document.head.appendChild(style);
    }
}

const statusManager = new StatusManager();

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

// --- GLOBAL VARIABLES ---
// --- FIX: Declare these variables in the global scope so all functions share the same state. ---
let currentModel = 'default';
let availableModels = {};

function switchModel(modelKey) {
    if (!availableModels[modelKey] || availableModels[modelKey].status !== 'available') {
        console.warn(`Model ${modelKey} is not available.`);
        return;
    }
    
    currentModel = modelKey;
    
    document.querySelectorAll('.model-toggle').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`${modelKey}ModelBtn`)?.classList.add('active');
    
    const displayName = formatModelName(modelKey);
    statusManager.show(`Switched to ${displayName} model`, 'success', 3000);
}

window.addEventListener('DOMContentLoaded', function() {
    function detectApiUrls() {
        const hostname = window.location.hostname;
        const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
        const isRender = hostname.endsWith('.onrender.com');
        const apiBase = isLocalhost ? 'http://localhost:10000' : (isRender ? 'https://radiology-api-staging.onrender.com' : '/api');
        const mode = isLocalhost ? 'LOCAL' : (isRender ? 'STAGING' : 'PROD');
        
        return {
            baseUrl: apiBase,
            mode: mode
        };
    }
    
    const apiConfig = detectApiUrls();
    const API_URL = `${apiConfig.baseUrl}/parse_enhanced`;
    const BATCH_API_URL = `${apiConfig.baseUrl}/parse_batch`;
    const MODELS_URL = `${apiConfig.baseUrl}/models`;
    // --- FIX: The sanity test will now use the batch API, so this dedicated URL is no longer needed. ---
    // const SANITY_TEST_URL = `${apiConfig.baseUrl}/process_sanity_test`;
    
    console.log(`Frontend running in ${apiConfig.mode} mode. API base: ${apiConfig.baseUrl}`);

    async function loadAvailableModels() {
        try {
            const response = await fetch(MODELS_URL);
            if (!response.ok) throw new Error(`API returned ${response.status}`);
            const modelsData = await response.json();
            availableModels = modelsData.models || {};
            currentModel = modelsData.default_model || 'default';
            buildModelSelectionUI();
        } catch (error) {
            console.error('Failed to load models:', error);
            statusManager.show('Could not load AI models from backend. Using fallback UI.', 'warning');
            useFallbackModels();
        }
    }
    
    function useFallbackModels() {
        availableModels = {
            'default': { name: 'BioLORD (Default)', status: 'available', description: 'Advanced biomedical language model (default)' },
            'experimental': { name: 'MedCPT (Experimental)', status: 'available', description: 'NCBI Clinical Practice Text encoder' }
        };
        currentModel = 'default';
        buildModelSelectionUI();
    }
    
    function buildModelSelectionUI() {
        const modelContainer = document.querySelector('.model-selection-container');
        if (!modelContainer) return;
        modelContainer.innerHTML = '';
        
        Object.entries(availableModels).forEach(([modelKey, modelInfo]) => {
            const modelWrapper = document.createElement('div');
            modelWrapper.className = 'model-wrapper';
            modelWrapper.style.cssText = 'display: flex; align-items: center; gap: 15px; margin-bottom: 10px;';
            
            const button = document.createElement('button');
            button.className = `button secondary model-toggle ${modelKey === currentModel ? 'active' : ''}`;
            button.id = `${modelKey}ModelBtn`;
            button.disabled = modelInfo.status !== 'available';
            button.innerHTML = `<span class="model-name">${formatModelName(modelKey)}</span>`;
            if (modelInfo.status === 'available') {
                button.addEventListener('click', () => switchModel(modelKey));
            }

            const description = document.createElement('span');
            description.className = 'model-description';
            description.style.cssText = 'font-size: 0.85em; color: #666;';
            description.textContent = modelInfo.description || '';

            modelWrapper.appendChild(button);
            modelWrapper.appendChild(description);
            modelContainer.appendChild(modelWrapper);
        });
    }
    
    function formatModelName(modelKey) {
        return availableModels[modelKey]?.name || modelKey.charAt(0).toUpperCase() + modelKey.slice(1);
    }
    
    loadAvailableModels();

    // --- STATE ---
    // --- FIX: Removed redundant declarations. Global variables are used instead. ---
    let allMappings = [];
    let summaryData = null;
    let sortedMappings = [];
    let currentPage = 1;
    let pageSize = 100;
    let sortBy = 'default';

    // --- DOM ELEMENTS ---
    const uploadSection = document.getElementById('uploadSection');
    const demosSection = document.getElementById('demosSection');
    const fileInput = document.getElementById('fileInput');
    const resultsSection = document.getElementById('resultsSection');
    const resultsBody = document.getElementById('resultsBody');
    const sanityButton = document.getElementById('sanityTestBtn');

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
    if (sanityButton) sanityButton.addEventListener('click', runSanityTest);

    // --- FILE PROCESSING ---
    async function processFile(file) {
        if (!file.name.endsWith('.json')) {
            statusManager.show('Please upload a valid JSON file.', 'error', 5000);
            return;
        }
        hideUploadInterface();
        statusManager.clearAll();
        statusManager.showFileInfo(file.name, file.size);
        
        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const codes = JSON.parse(e.target.result);
                if (!Array.isArray(codes) || codes.length === 0) throw new Error('JSON is empty or not an array.');
                await runBatchProcessing(codes, `file "${file.name}"`);
            } catch (error) {
                statusManager.show(`Error processing file: ${error.message}`, 'error');
                showUploadInterface();
            }
        };
        reader.readAsText(file);
    }

    // --- FIX: New, refactored sanity test function ---
    async function runSanityTest() {
        hideUploadInterface();
        statusManager.clearAll();
        statusManager.showTestInfo('Sanity Test', 'Loading test data...');
        
        try {
            // Fetch the sanity test data from a local file
            const response = await fetch('./core/sanity_test.json');
            if (!response.ok) throw new Error(`Could not load test file: ${response.statusText}`);
            const codes = await response.json();
            
            // Now, run the batch processing with this data
            await runBatchProcessing(codes, "Sanity Test");

        } catch (error) {
            statusManager.show(`Sanity Test Failed: ${error.message}`, 'error');
            console.error('Sanity test failed during setup:', error);
            showUploadInterface();
        }
    }

    // --- FIX: New, universal batch processing function with granular feedback ---
    async function runBatchProcessing(codes, jobName) {
        const button = document.getElementById('sanityTestBtn');
        if (button) button.disabled = true;

        allMappings = [];
        const totalCodes = codes.length;
        const batchSize = getBatchSize();
        let processedCount = 0;
        let progressId = null;

        try {
            // Loop through the data in chunks
            for (let i = 0; i < totalCodes; i += batchSize) {
                const chunk = codes.slice(i, i + batchSize);
                
                // Update progress before sending the batch
                progressId = statusManager.showProgress(`Processing ${jobName}`, processedCount, totalCodes);

                const exams = chunk.map(code => ({
                    exam_name: code.EXAM_NAME,
                    modality_code: code.MODALITY_CODE,
                    data_source: code.DATA_SOURCE,
                    exam_code: code.EXAM_CODE
                }));

                const response = await fetch(BATCH_API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ exams: exams, model: currentModel })
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Batch API failed (Chunk ${i / batchSize + 1}): ${errorText}`);
                }

                const batchResult = await response.json();
                
                // Process results from the chunk
                if (batchResult.results) {
                    const chunkMappings = batchResult.results.map(item => {
                        return item.status === 'success' ? {
                            data_source: item.input.data_source,
                            modality_code: item.input.modality_code,
                            exam_code: item.input.exam_code,
                            exam_name: item.input.exam_name,
                            clean_name: item.output.clean_name,
                            snomed: item.output.snomed || {},
                            components: item.output.components || {}
                        } : {
                            ...item.input,
                            clean_name: `ERROR: ${item.error}`,
                            components: {}
                        };
                    });
                    allMappings.push(...chunkMappings);
                }
                
                processedCount += chunk.length;
                statusManager.showProgress(`Processing ${jobName}`, processedCount, totalCodes);
            }

            statusManager.show(`Successfully processed ${allMappings.length} records from ${jobName}.`, 'success', 5000);
            runAnalysis(allMappings);

        } catch (error) {
            statusManager.show(`Processing failed: ${error.message}`, 'error', 0);
            console.error('Batch processing error:', error);
            showUploadInterface();
        } finally {
            if (button) button.disabled = false;
            // Clear progress bar on completion or error
            if (progressId) statusManager.remove(progressId);
        }
    }
    
    function runAnalysis(mappings) {
        summaryData = generateAnalyticsSummary(mappings);
        updateStatsUI(summaryData);
        updateResultsTitle();
        
        sortedMappings = [...mappings];
        applySortToMappings();
        
        resultsSection.style.display = 'block';
        displayCurrentPage();
    }

    // --- All other functions (UI, display, sorting, export, etc.) remain largely the same ---
    // They will now operate correctly because `allMappings` is populated by the new
    // robust `runBatchProcessing` function.

    // --- UI & DISPLAY FUNCTIONS (Simplified for brevity, no major changes needed here) ---
    function startNewUpload() {
        showUploadInterface();
        resultsSection.style.display = 'none';
        statusManager.clearAll();
        fileInput.value = '';
        allMappings = [];
        summaryData = null;
        sortedMappings = [];
        currentPage = 1;
        document.getElementById('paginationControls').style.display = 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

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

    function updateResultsTitle() {
        document.getElementById('resultsTitle').textContent = `Cleaning Results with ${formatModelName(currentModel)}`;
    }

    function updateStatsUI(summary) {
        document.getElementById('originalCount').textContent = summary.totalOriginalCodes;
        document.getElementById('cleanCount').textContent = summary.uniqueCleanNames;
        document.getElementById('consolidationRatio').textContent = `${summary.consolidationRatio}:1`;
        document.getElementById('modalityCount').textContent = Object.keys(summary.modalityBreakdown).length;
        document.getElementById('avgConfidence').textContent = `${summary.avgConfidence}%`;
        document.getElementById('genderContext').textContent = summary.genderContextCount;
    }

    function displayCurrentPage() {
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        const pageData = sortedMappings.slice(startIndex, endIndex);
        displayResults(pageData);
        updatePaginationInfo();
    }
    
    function updatePaginationInfo() {
        const totalPages = Math.ceil(sortedMappings.length / pageSize);
        document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages || 1}`;
        document.getElementById('prevPageBtn').disabled = currentPage <= 1;
        document.getElementById('nextPageBtn').disabled = currentPage >= totalPages;
        document.getElementById('paginationControls').style.display = totalPages > 1 ? 'flex' : 'none';
    }

    function applySortToMappings() {
        // This function remains the same
        sortedMappings = [...allMappings];
        switch (sortBy) {
            case 'confidence-desc': sortedMappings.sort((a, b) => (b.components?.confidence || 0) - (a.components?.confidence || 0)); break;
            case 'confidence-asc': sortedMappings.sort((a, b) => (a.components?.confidence || 0) - (b.components?.confidence || 0)); break;
            case 'name-asc': sortedMappings.sort((a, b) => (a.clean_name || '').localeCompare(b.clean_name || '')); break;
            case 'name-desc': sortedMappings.sort((a, b) => (b.clean_name || '').localeCompare(a.clean_name || '')); break;
        }
    }

    // Add event listeners for pagination and sorting controls
    document.getElementById('prevPageBtn').addEventListener('click', () => {
        if (currentPage > 1) { currentPage--; displayCurrentPage(); }
    });
    document.getElementById('nextPageBtn').addEventListener('click', () => {
        const totalPages = Math.ceil(sortedMappings.length / pageSize);
        if (currentPage < totalPages) { currentPage++; displayCurrentPage(); }
    });
    document.getElementById('pageSizeSelector').addEventListener('change', (e) => {
        pageSize = parseInt(e.target.value);
        currentPage = 1;
        displayCurrentPage();
    });
    document.getElementById('tableSortBy').addEventListener('change', (e) => {
        sortBy = e.target.value;
        currentPage = 1;
        applySortToMappings();
        displayCurrentPage();
    });

    // ... The rest of the display, export, and utility functions are unchanged ...
    // ... (displayResults, generateAnalyticsSummary, exportResults, etc.) ...
    
    // NOTE: For brevity, I'm omitting the very long display and utility functions that don't require changes.
    // The key fixes are in the variable declarations and the new runBatchProcessing/runSanityTest functions.
    // The existing displayResults, generateAnalyticsSummary, etc., will work correctly with the data
    // populated by the new processing logic.
    function getSourceColor(source) {
        const sourceColors = {'C': '#1f77b4', 'CO': '#2ca02c', 'K': '#9467bd', 'Default': '#6c757d'};
        return sourceColors[source] || sourceColors['Default'];
    }

    function displayResults(results) {
        resultsBody.innerHTML = '';
        results.forEach(item => {
            const row = resultsBody.insertRow();
            const sourceCell = row.insertCell();
            sourceCell.style.cssText = `width: 12px; padding: 0; background-color: ${getSourceColor(item.data_source)};`;
            row.insertCell().textContent = item.exam_code;
            row.insertCell().textContent = item.exam_name;
            const cleanNameCell = row.insertCell();
            if (item.clean_name?.startsWith('ERROR')) {
                cleanNameCell.innerHTML = `<span class="error-message">${item.clean_name}</span>`;
            } else {
                cleanNameCell.innerHTML = `<strong>${item.clean_name || ''}</strong>`;
            }
            
            const snomedCell = row.insertCell();
            snomedCell.textContent = item.snomed?.fsn || '-';

            const tagsCell = row.insertCell();
            tagsCell.innerHTML = ''; // Clear previous content
            const components = item.components || {};
            const { anatomy, laterality, contrast, technique, gender_context, age_context, clinical_context } = components;
            
            [...(anatomy || [])].forEach(a => { if (a) tagsCell.innerHTML += `<span class="tag anatomy">${a}</span>` });
            [...(laterality || [])].forEach(l => { if (l) tagsCell.innerHTML += `<span class="tag laterality">${l}</span>` });
            [...(contrast || [])].forEach(c => { if (c) tagsCell.innerHTML += `<span class="tag contrast">${c}</span>` });
            [...(technique || [])].forEach(t => { if (t) tagsCell.innerHTML += `<span class="tag technique">${t}</span>` });
            if (gender_context) tagsCell.innerHTML += `<span class="tag gender">${gender_context}</span>`;
            if (age_context) tagsCell.innerHTML += `<span class="tag age">${age_context}</span>`;
            [...(clinical_context || [])].forEach(cc => { if (cc) tagsCell.innerHTML += `<span class="tag clinical">${cc}</span>` });

            const confidenceCell = row.insertCell();
            const confidence = components.confidence || 0;
            const confidencePercent = Math.round(confidence * 100);
            const confidenceClass = confidence >= 0.8 ? 'confidence-high' : confidence >= 0.6 ? 'confidence-medium' : 'confidence-low';
            confidenceCell.innerHTML = `<div class="confidence-bar"><div class="confidence-fill ${confidenceClass}" style="width: ${confidencePercent}%"></div></div><small>${confidencePercent}%</small>`;
        });
    }

    function generateAnalyticsSummary(mappings) {
        const summary = {
            totalOriginalCodes: mappings.length,
            uniqueCleanNames: new Set(mappings.map(m => m.clean_name).filter(n => n && !n.startsWith('ERROR'))).size,
            modalityBreakdown: {},
            genderContextCount: 0,
            avgConfidence: 0
        };
        summary.consolidationRatio = summary.uniqueCleanNames > 0 ? (summary.totalOriginalCodes / summary.uniqueCleanNames).toFixed(2) : "0.00";
        
        let totalConfidence = 0, confidenceCount = 0;
        mappings.forEach(m => {
            if (!m.components || m.clean_name?.startsWith('ERROR')) return;
            const modality = m.components.modality || m.modality_code;
            if (modality) summary.modalityBreakdown[modality] = (summary.modalityBreakdown[modality] || 0) + 1;
            if (m.components.gender_context && m.components.gender_context !== 'none') summary.genderContextCount++;
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
});