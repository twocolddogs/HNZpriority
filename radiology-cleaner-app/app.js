/* ===============================================================
   app.js – Radiology Code Semantic Cleaner Frontend
   =============================================================== */

// Global variables
let availableModels = {};
let availableRerankers = {};
let currentModel = null;
let currentReranker = null;
let isUsingFallbackModels = false;
let processingResults = null;
let currentView = 'full'; // 'full' or 'consolidated'

// API Configuration
const apiConfig = {
    baseUrl: 'https://radiology-api-staging.onrender.com',
    get healthUrl() { return `${this.baseUrl}/health`; },
    get modelsUrl() { return `${this.baseUrl}/models`; }
};

// Status Manager for user feedback
class StatusManager {
    constructor() {
        this.container = document.getElementById('statusMessageContainer');
        this.messages = new Map();
        this.nextId = 1;
    }

    show(message, type = 'info', duration = 0) {
        const id = this.nextId++;
        const messageEl = document.createElement('div');
        messageEl.className = `status-message status-${type}`;
        messageEl.innerHTML = `
            <span>${message}</span>
            <button class="status-close" onclick="statusManager.remove(${id})">&times;</button>
        `;
        
        this.container.appendChild(messageEl);
        this.messages.set(id, messageEl);
        
        if (duration > 0) {
            setTimeout(() => this.remove(id), duration);
        }
        
        return id;
    }

    remove(id) {
        const messageEl = this.messages.get(id);
        if (messageEl) {
            messageEl.remove();
            this.messages.delete(id);
        }
    }

    clear() {
        this.container.innerHTML = '';
        this.messages.clear();
    }
}

// Initialize status manager
const statusManager = new StatusManager();

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Radiology Cleaner App starting...');
    initializeApp();
});

async function initializeApp() {
    setupEventListeners();
    await testApiConnectivity();
    await loadAvailableModels();
}

function setupEventListeners() {
    // Hamburger menu
    const hamburgerToggle = document.getElementById('hamburgerToggle');
    const hamburgerDropdown = document.getElementById('hamburgerDropdown');
    
    if (hamburgerToggle && hamburgerDropdown) {
        hamburgerToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            hamburgerDropdown.classList.toggle('hidden');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function() {
            hamburgerDropdown.classList.add('hidden');
        });
    }

    // Action path cards
    setupActionCards();
    
    // Demo options
    setupDemoOptions();
    
    // File upload
    setupFileUpload();
    
    // Results handling
    setupResultsHandling();
    
    // Config modal
    setupConfigModal();
}

function setupActionCards() {
    // Demo Path
    const demoCard = document.getElementById('demoPathCard');
    if (demoCard) {
        demoCard.addEventListener('click', function() {
            showWorkflowSection();
            showDemoOptions();
            console.log('📊 Demo path selected');
        });
    }

    // Upload Path
    const uploadCard = document.getElementById('uploadPathCard');
    if (uploadCard) {
        uploadCard.addEventListener('click', function() {
            showWorkflowSection();
            showUploadOptions();
            console.log('📤 Upload path selected');
        });
    }

    // Advanced Path
    const advancedCard = document.getElementById('advancedPathCard');
    if (advancedCard) {
        advancedCard.addEventListener('click', function() {
            showConfigModal();
            console.log('⚙️ Advanced path selected');
        });
    }

    // Validation Path
    const validationCard = document.getElementById('validationPathCard');
    if (validationCard) {
        validationCard.addEventListener('click', function() {
            window.location.href = './validation_ui/index.html';
            console.log('✅ Validation path selected');
        });
    }
}

function setupDemoOptions() {
    const sampleSizeInput = document.getElementById('sampleSizeInput');
    const randomSampleSubtext = document.getElementById('randomSampleSubtext');
    const runRandomDemoBtn = document.getElementById('runRandomDemoBtn');
    const runFixedTestBtn = document.getElementById('runFixedTestBtn');

    // Update subtext when sample size changes
    if (sampleSizeInput && randomSampleSubtext) {
        sampleSizeInput.addEventListener('input', function() {
            const size = this.value;
            randomSampleSubtext.textContent = `${size} random codes from live dataset`;
        });
    }

    // Random demo button
    if (runRandomDemoBtn) {
        runRandomDemoBtn.addEventListener('click', async function() {
            const sampleSize = sampleSizeInput ? parseInt(sampleSizeInput.value) : 100;
            await runRandomDemo(sampleSize);
        });
    }

    // Fixed test button
    if (runFixedTestBtn) {
        runFixedTestBtn.addEventListener('click', async function() {
            await runFixedTest();
        });
    }
}

function setupFileUpload() {
    // File input (hidden, triggered by upload card)
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.txt,.csv,.json';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });

    // Store reference for upload card to trigger
    window.triggerFileUpload = function() {
        fileInput.click();
    };
}

function setupResultsHandling() {
    // View toggle button
    const viewToggleBtn = document.getElementById('viewToggleBtn');
    if (viewToggleBtn) {
        viewToggleBtn.addEventListener('click', function() {
            toggleResultsView();
        });
    }

    // Export button
    const exportMappingsBtn = document.getElementById('exportMappingsBtn');
    if (exportMappingsBtn) {
        exportMappingsBtn.addEventListener('click', function() {
            exportMappings();
        });
    }

    // New upload button
    const newUploadBtn = document.getElementById('newUploadBtn');
    if (newUploadBtn) {
        newUploadBtn.addEventListener('click', function() {
            startOver();
        });
    }
}

function setupConfigModal() {
    const configModal = document.getElementById('configEditorModal');
    const closeConfigBtn = document.getElementById('closeConfigEditorModal');
    const closeConfigBtn2 = document.getElementById('closeConfigEditorBtn');

    if (closeConfigBtn) {
        closeConfigBtn.addEventListener('click', hideConfigModal);
    }
    if (closeConfigBtn2) {
        closeConfigBtn2.addEventListener('click', hideConfigModal);
    }

    // Close modal when clicking outside
    if (configModal) {
        configModal.addEventListener('click', function(e) {
            if (e.target === configModal) {
                hideConfigModal();
            }
        });
    }
}

// API Functions
async function testApiConnectivity() {
    try {
        const response = await fetch(apiConfig.healthUrl, { method: 'GET' });
        if (response.ok) {
            console.log('✓ API connectivity test passed');
            return true;
        } else {
            console.warn('⚠ API health check failed:', response.status);
            return false;
        }
    } catch (error) {
        console.error('✗ API connectivity test failed:', error);
        statusManager.show('⚠️ Cannot connect to backend server', 'error', 5000);
        return false;
    }
}

async function loadAvailableModels(retryCount = 0) {
    try {
        console.log(`Loading available models (attempt ${retryCount + 1})`);
        
        const response = await fetch(apiConfig.modelsUrl, { 
            method: 'GET',
            signal: AbortSignal.timeout(10000)
        });
        
        if (response.ok) {
            const modelsData = await response.json();
            availableModels = modelsData.models || {};
            availableRerankers = modelsData.rerankers || {};
            
            currentModel = modelsData.default_model || 'retriever';
            currentReranker = modelsData.default_reranker || 'medcpt';
            
            isUsingFallbackModels = false;
            
            buildModelSelectionUI();
            buildRerankerSelectionUI();
            enableActionButtons();
            
            console.log('✓ Models loaded successfully:', Object.keys(availableModels));
            statusManager.show('✓ Models loaded successfully', 'success', 3000);
            
        } else {
            throw new Error(`API responded with ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        console.error(`✗ Failed to load models (attempt ${retryCount + 1}):`, error);
        
        if (retryCount < 2) {
            const retryDelay = (retryCount + 1) * 2;
            statusManager.show(`⚠️ Model loading failed, retrying in ${retryDelay}s...`, 'warning', retryDelay * 1000);
            setTimeout(() => loadAvailableModels(retryCount + 1), retryDelay * 1000);
        } else {
            console.warn('⚠ All retry attempts failed, using fallback models');
            statusManager.show('⚠️ Using fallback models - some features may be limited', 'warning', 5000);
            useFallbackModels();
        }
    }
}

function useFallbackModels() {
    availableModels = {
        'retriever': { name: 'BioLORD', status: 'available', description: 'Advanced biomedical language model' }
    };
    availableRerankers = {
        'medcpt': { name: 'MedCPT', status: 'available', description: 'Medical cross-encoder', type: 'huggingface' }
    };
    currentModel = 'retriever';
    currentReranker = 'medcpt';
    isUsingFallbackModels = true;
    
    buildModelSelectionUI();
    buildRerankerSelectionUI();
    enableActionButtons();
}

// UI Building Functions
function buildModelSelectionUI() {
    const container = document.querySelector('.model-selection-container');
    if (!container) return;

    container.innerHTML = '';
    
    Object.entries(availableModels).forEach(([key, model]) => {
        const modelWrapper = document.createElement('div');
        modelWrapper.className = 'model-wrapper';
        modelWrapper.style.cssText = 'display: flex; align-items: center; gap: 15px; margin-bottom: 10px;';
        
        const button = document.createElement('button');
        button.className = `button secondary model-toggle ${key === currentModel ? 'active' : ''}`;
        button.id = `${key}ModelBtn`;
        button.dataset.model = key;
        button.style.cssText = 'min-width: 150px; flex-shrink: 0;';
        
        const statusText = model.status === 'available' ? '' : ' (Unavailable)';
        button.innerHTML = `<span class="model-name">${model.name}${statusText}</span>`;
        
        const description = document.createElement('span');
        description.className = 'model-description';
        description.style.cssText = 'font-size: 0.85em; color: #666; flex: 1;';
        description.textContent = model.description || '';
        
        if (model.status !== 'available') {
            button.disabled = true;
            button.title = `${model.name} is currently unavailable`;
            description.style.color = '#999';
        } else {
            button.addEventListener('click', () => selectModel(key));
        }
        
        modelWrapper.appendChild(button);
        modelWrapper.appendChild(description);
        container.appendChild(modelWrapper);
    });
}

function buildRerankerSelectionUI() {
    const container = document.querySelector('.reranker-selection-container');
    if (!container) return;

    container.innerHTML = '';
    
    // Sort rerankers to put MedCPT first, then others alphabetically
    const sortedRerankers = Object.entries(availableRerankers).sort(([keyA], [keyB]) => {
        if (keyA === 'medcpt') return -1;  // MedCPT goes first
        if (keyB === 'medcpt') return 1;   // MedCPT goes first
        return keyA.localeCompare(keyB);   // Others alphabetically
    });
    
    sortedRerankers.forEach(([key, reranker]) => {
        const rerankerWrapper = document.createElement('div');
        rerankerWrapper.className = 'reranker-wrapper';
        rerankerWrapper.style.cssText = 'display: flex; align-items: center; gap: 15px; margin-bottom: 10px;';
        
        const button = document.createElement('button');
        button.className = `button reranker-toggle ${key === currentReranker ? 'active' : ''}`;
        button.id = `${key}RerankerBtn`;
        button.dataset.reranker = key;
        button.style.cssText = 'min-width: 180px; flex-shrink: 0;';
        
        const statusText = reranker.status === 'available' ? '' : ' (Unavailable)';
        const typeInfo = reranker.type === 'openrouter' ? ' 🌐' : ' 🤗';
        button.innerHTML = `<span class="reranker-name">${formatRerankerName(key)}${typeInfo}${statusText}</span>`;
        
        const description = document.createElement('span');
        description.className = 'reranker-description';
        description.style.cssText = 'font-size: 0.85em; color: #666; flex: 1;';
        description.textContent = reranker.description || '';
        
        if (reranker.status !== 'available') {
            button.disabled = true;
            button.title = `${reranker.name} is currently unavailable`;
            description.style.color = '#999';
        } else {
            button.addEventListener('click', () => selectReranker(key));
        }
        
        rerankerWrapper.appendChild(button);
        rerankerWrapper.appendChild(description);
        container.appendChild(rerankerWrapper);
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

function selectModel(modelKey) {
    currentModel = modelKey;
    // Update button states
    document.querySelectorAll('.model-toggle').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`${modelKey}ModelBtn`)?.classList.add('active');
    updateWorkflowProgress();
    console.log('📋 Selected model:', modelKey);
}

function selectReranker(rerankerKey) {
    if (!availableRerankers[rerankerKey] || availableRerankers[rerankerKey].status !== 'available') {
        console.warn(`Reranker ${rerankerKey} is not available.`);
        return;
    }
    currentReranker = rerankerKey;
    // Update button states
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
    
    updateWorkflowProgress();
    console.log('🔄 Selected reranker:', rerankerKey);
}

function enableActionButtons() {
    const buttons = [
        'runRandomDemoBtn',
        'runFixedTestBtn', 
        'runProcessingBtn'
    ];
    
    buttons.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.disabled = false;
        }
    });
}

// UI State Management
function showWorkflowSection() {
    const workflowSection = document.getElementById('workflowSection');
    if (workflowSection) {
        workflowSection.classList.remove('hidden');
    }
}

function showDemoOptions() {
    const demoOptions = document.getElementById('demoOptions');
    const dataSourceDisplay = document.getElementById('dataSourceDisplay');
    const runProcessingBtn = document.getElementById('runProcessingBtn');
    
    if (demoOptions) demoOptions.classList.remove('hidden');
    if (dataSourceDisplay) dataSourceDisplay.classList.add('hidden');
    if (runProcessingBtn) runProcessingBtn.classList.add('hidden');
}

function showUploadOptions() {
    const demoOptions = document.getElementById('demoOptions');
    const dataSourceDisplay = document.getElementById('dataSourceDisplay');
    const runProcessingBtn = document.getElementById('runProcessingBtn');
    
    if (demoOptions) demoOptions.classList.add('hidden');
    if (dataSourceDisplay) dataSourceDisplay.classList.remove('hidden');
    if (runProcessingBtn) runProcessingBtn.classList.remove('hidden');
    
    // Trigger file selection
    if (window.triggerFileUpload) {
        window.triggerFileUpload();
    }
}

function showConfigModal() {
    const modal = document.getElementById('configEditorModal');
    if (modal) {
        modal.style.display = 'block';
        loadConfigEditor();
    }
}

function hideConfigModal() {
    const modal = document.getElementById('configEditorModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function updateWorkflowProgress() {
    // Update visual indicators of workflow progress
    // This would update the step indicators based on current state
    console.log('📊 Workflow progress updated');
}

// Processing Functions
async function runRandomDemo(sampleSize) {
    console.log(`🎲 Starting random demo with ${sampleSize} samples`);
    statusManager.show(`🎲 Starting random demo with ${sampleSize} samples...`, 'info');
    
    // Hide workflow section when processing starts
    const workflowSection = document.getElementById('workflowSection');
    if (workflowSection) {
        workflowSection.classList.add('hidden');
    }
    
    try {
        const response = await fetch(`${apiConfig.baseUrl}/demo_random_sample`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sample_size: sampleSize,
                model: currentModel,
                reranker: currentReranker
            })
        });
        
        if (response.ok) {
            const results = await response.json();
            console.log('📥 Random demo response received:', results);
            displayResults(results);
            statusManager.show('✅ Random demo completed successfully', 'success', 3000);
        } else {
            const errorText = await response.text();
            console.error('❌ Random demo failed:', response.status, response.statusText, errorText);
            throw new Error(`Demo failed: ${response.status} ${response.statusText}`);
        }
    } catch (error) {
        console.error('Random demo failed:', error);
        statusManager.show('❌ Random demo failed', 'error', 5000);
    }
}

async function runFixedTest() {
    console.log('🧪 Starting fixed test suite');
    statusManager.show('🧪 Running fixed test suite...', 'info');
    
    // Hide workflow section when processing starts
    const workflowSection = document.getElementById('workflowSection');
    if (workflowSection) {
        workflowSection.classList.add('hidden');
    }
    
    try {
        const response = await fetch(`${apiConfig.baseUrl}/process_sanity_test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: currentModel,
                reranker: currentReranker
            })
        });
        
        if (response.ok) {
            const results = await response.json();
            displayResults(results);
            statusManager.show('✅ Fixed test completed successfully', 'success', 3000);
        } else {
            throw new Error(`Test failed: ${response.statusText}`);
        }
    } catch (error) {
        console.error('Fixed test failed:', error);
        statusManager.show('❌ Fixed test failed', 'error', 5000);
    }
}

function handleFileUpload(file) {
    const dataSourceText = document.getElementById('dataSourceText');
    if (dataSourceText) {
        dataSourceText.textContent = file.name;
    }
    
    console.log('📁 File uploaded:', file.name);
    statusManager.show(`📁 File loaded: ${file.name}`, 'success', 3000);
}

// Results Display
function displayResults(results) {
    console.log('📊 Displaying results:', results);
    processingResults = results;
    
    // Validate results structure - handle both array format and object format
    if (!results) {
        console.error('❌ No results data provided');
        statusManager.show('❌ No results data received', 'error', 5000);
        return;
    }
    
    // Support both formats: direct array or object with mappings property
    let mappingsArray;
    if (Array.isArray(results)) {
        mappingsArray = results;
        console.log(`📋 Processing direct array with ${results.length} items`);
    } else if (results.mappings && Array.isArray(results.mappings)) {
        mappingsArray = results.mappings;
        console.log(`📋 Processing results.mappings with ${results.mappings.length} items`);
    } else {
        console.error('❌ Results invalid format:', results);
        statusManager.show('❌ Invalid results format - expected array or object with mappings', 'error', 5000);
        return;
    }
    
    // Show results section
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) {
        resultsSection.classList.remove('hidden');
    }
    
    // Update stats - pass the mappings array
    updateResultsStats({ mappings: mappingsArray, stats: results.stats });
    
    // Build results table - pass the mappings array
    buildResultsTable({ mappings: mappingsArray });
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function updateResultsStats(results) {
    // Update statistics display
    const stats = results.stats || {};
    const mappings = results.mappings || [];
    
    // Calculate stats from mappings if not provided in stats object
    const originalCount = stats.original_count || mappings.length;
    const cleanCount = stats.clean_count || new Set(mappings.map(m => m.clean_name)).size;
    const consolidationRatio = stats.consolidation_ratio || (originalCount > 0 ? `${originalCount}:${cleanCount}` : '0:1');
    const modalityCount = stats.modality_count || new Set(mappings.map(m => m.modality)).size;
    
    // Calculate average confidence if not provided
    let avgConfidence = stats.avg_confidence;
    if (!avgConfidence && mappings.length > 0) {
        const confidences = mappings.map(m => {
            const conf = m.confidence || m.confidence_score;
            if (typeof conf === 'string' && conf.includes('%')) {
                return parseFloat(conf.replace('%', ''));
            }
            return parseFloat(conf) || 0;
        });
        const avg = confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length;
        avgConfidence = `${Math.round(avg)}%`;
    }
    
    const elements = {
        'originalCount': originalCount,
        'cleanCount': cleanCount,
        'consolidationRatio': consolidationRatio,
        'modalityCount': modalityCount,
        'avgConfidence': avgConfidence || '0%'
    };
    
    console.log('📊 Updating stats:', elements);
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    });
}

function buildResultsTable(results) {
    const tbody = document.getElementById('resultsBody');
    if (!tbody) {
        console.error('❌ Results table body not found');
        return;
    }
    
    if (!results.mappings) {
        console.error('❌ No mappings in results');
        return;
    }
    
    console.log(`🏗️ Building table with ${results.mappings.length} rows`);
    tbody.innerHTML = '';
    
    results.mappings.forEach((mapping, index) => {
        const row = document.createElement('tr');
        
        // Handle both formats: V5-Secondary-Pipeline format (exam_code, exam_name) 
        // and develop branch format (original_code, original_name)
        const originalCode = mapping.exam_code || mapping.original_code || '';
        const originalName = mapping.exam_name || mapping.original_name || '';
        const cleanName = mapping.clean_name || '';
        const snomedFsn = mapping.snomed_fsn || '';
        const tags = mapping.tags ? (Array.isArray(mapping.tags) ? mapping.tags.join(', ') : mapping.tags) : '';
        const confidence = mapping.confidence || mapping.confidence_score || '0%';
        
        row.innerHTML = `
            <td style="width: 12px; padding: 0;"></td>
            <td>${originalCode}</td>
            <td>${originalName}</td>
            <td>${cleanName}</td>
            <td>${snomedFsn}</td>
            <td>${tags}</td>
            <td>${confidence}</td>
        `;
        tbody.appendChild(row);
    });
    
    console.log(`✅ Table populated with ${tbody.children.length} rows`);
}

function toggleResultsView() {
    const fullView = document.getElementById('fullView');
    const consolidatedView = document.getElementById('consolidatedView');
    const toggleBtn = document.getElementById('viewToggleBtn');
    
    if (currentView === 'full') {
        currentView = 'consolidated';
        fullView.classList.add('hidden');
        consolidatedView.classList.remove('hidden');
        toggleBtn.textContent = 'Switch to Full View';
    } else {
        currentView = 'full';
        fullView.classList.remove('hidden');
        consolidatedView.classList.add('hidden');
        toggleBtn.textContent = 'Switch to Consolidated View';
    }
}

function exportMappings() {
    if (!processingResults) {
        statusManager.show('❌ No results to export', 'error', 3000);
        return;
    }
    
    const data = JSON.stringify(processingResults, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `radiology-mappings-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
    statusManager.show('📥 Mappings exported successfully', 'success', 3000);
}

function startOver() {
    // Reset the application state
    processingResults = null;
    currentView = 'full';
    
    // Hide results section
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) {
        resultsSection.classList.add('hidden');
    }
    
    // Hide workflow section
    const workflowSection = document.getElementById('workflowSection');
    if (workflowSection) {
        workflowSection.classList.add('hidden');
    }
    
    // Clear status messages
    statusManager.clear();
    
    console.log('🔄 Application reset');
    statusManager.show('🔄 Ready for new processing', 'info', 2000);
}

// Config Editor Functions
async function loadConfigEditor() {
    const editor = document.getElementById('configEditor');
    const status = document.getElementById('configStatus');
    
    if (!editor) return;
    
    try {
        status.textContent = 'Loading...';
        const response = await fetch(`${apiConfig.baseUrl}/config/current`);
        
        if (response.ok) {
            const config = await response.text();
            editor.value = config;
            status.textContent = 'Loaded from server';
        } else {
            throw new Error('Failed to load config');
        }
    } catch (error) {
        console.error('Failed to load config:', error);
        editor.value = '# Failed to load configuration\n# Please check server connection';
        status.textContent = 'Load failed';
    }
}

// Export functions to global scope for HTML event handlers
window.statusManager = statusManager;
window.testApiConnectivity = testApiConnectivity;
window.loadAvailableModels = loadAvailableModels;

console.log('📱 Radiology Cleaner App JavaScript loaded');