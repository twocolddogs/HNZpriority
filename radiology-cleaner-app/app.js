"""// --- STATUS MANAGER CLASS ---
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
            showLoadingIndicator('Warming up processing engine...');
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
            } else {
                throw new Error(`Warmup failed with status ${response.status}`);
            }
        } catch (error) {
            console.warn('⚠️ API warmup failed (processing will still work, but first request may be slower):', error);
            // Clear the warming up message and show warning
            if (warmupMessageId) statusManager.remove(warmupMessageId);
            statusManager.show('⚠️ Engine warmup incomplete - first processing may take longer', 'warning', 5000);
            // Hide loading indicator and enable buttons on failure
            hideLoadingIndicator();
            enableActionButtons();
        }
    }

async function loadAvailableModels(retryCount = 0, skipWarmupMessages = false) {
    let loadingMessageId = null;
    try {
        console.log(`Loading available models (attempt ${retryCount + 1})`);
        
        // Show loading message on first attempt
        if (retryCount === 0) {
            showLoadingIndicator('Loading available models...');
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
            hideLoadingIndicator();

            // Enable hero buttons now that models are loaded and UI is ready
            enableActionButtons();
            
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
        hideLoadingIndicator();
        
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
        'gemini-2.5-flash-lite': { name: 'Gemini 2.5 Flash Lite', status: 'unknown', description: 'Google's lightweight Gemini model', type: 'openrouter' }
    };
    currentModel = 'retriever';
    currentReranker = 'medcpt';
    isUsingFallbackModels = true; // Mark that we're using fallback models
    console.log('Using fallback models with all reranker options');
    
    buildModelSelectionUI();
    buildRerankerSelectionUI();
    
    // Enable buttons for fallback mode, but with limited functionality message
    enableActionButtons();
    
    // Refresh workflow completion check
    if (window.workflowCheckFunction) {
        window.workflowCheckFunction();
    }
    
    // Show that fallback models are being used
    statusManager.show('ℹ️ Using offline fallback models - some features may be limited', 'info', 5000);
}

function closeModal() { 
    const modal = document.getElementById('consolidationModal');
    if (modal) modal.style.display = 'none'; 
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

class StatusManager {
""