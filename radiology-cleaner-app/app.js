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
        
        // Clear any status messages
        const existingStatus = document.getElementById('statusMessage');
        if (existingStatus) existingStatus.style.display = 'none';
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // --- STATUS MESSAGING ---
    function updateStatusMessage(message) {
        const statusDiv = document.getElementById('statusMessage');
        if (!statusDiv) {
            // Create status message div if it doesn't exist
            const newStatusDiv = document.createElement('div');
            newStatusDiv.id = 'statusMessage';
            newStatusDiv.style.cssText = `
                margin: 10px 0;
                padding: 12px 16px;
                background: var(--color-info-light, #e3f2fd);
                border: 1px solid var(--color-info, #2196f3);
                border-radius: 6px;
                font-size: 14px;
                color: var(--color-gray-700, #555);
                font-weight: 500;
            `;
            // Insert after progress bar
            const progressBar = document.getElementById('progressBar');
            progressBar.parentNode.insertBefore(newStatusDiv, progressBar.nextSibling);
        }
        document.getElementById('statusMessage').innerHTML = message;
        document.getElementById('statusMessage').style.display = 'block';
    }

    // --- CORE PROCESSING FUNCTIONS ---
    // Process files individually (for small files)
    async function processIndividually(codes) {
        updateStatusMessage(`Processing ${codes.length} exam records individually (one by one)...`);
        
        for (let i = 0; i < codes.length; i++) {
            const code = codes[i];
            
            // Update progress message every 10 items or so
            if (i % 10 === 0 || i === codes.length - 1) {
                updateStatusMessage(`Processing exam ${i + 1} of ${codes.length}: "${code.EXAM_NAME}"...`);
            }
            
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
            progressFill.style.width = `${((i + 1) / codes.length) * 100}%`;
        }
        
        // Individual processing complete
        updateStatusMessage(`Individual processing complete! ${allMappings.length} exam records processed.`);
    }
    
    // Process files in batches (for large files)
    async function processBatch(codes) {
        console.log(`Using batch processing for ${codes.length} records...`);
        
        // Update status message
        updateStatusMessage(`Preparing ${codes.length} exam records for processing...`);
        
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
            updateStatusMessage(`Sending ${codes.length} exam records to AI processing engine...`);
            
            const response = await fetch(BATCH_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    exams: exams,
                    chunk_size: 1000, // Process in chunks of 1000
                    model: currentModel
                })
            });
            
            if (!response.ok) throw new Error(`Batch API returned status ${response.status}`);
            
            // Set progress to 75% while processing response
            progressFill.style.width = '75%';
            updateStatusMessage(`🧠 AI engine processing exam names using biomedical BERT model...`);
            
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
                const hitRate = (stats.cache_hit_ratio * 100).toFixed(1);
                const formattedTime = formatProcessingTime(stats.processing_time_ms);
                updateStatusMessage(`Processing complete! ${stats.successful} successful, ${stats.cache_hits} from cache (${hitRate}% hit rate), ${formattedTime} total`);
                console.log(`Batch processing completed: ${stats.successful} successful, ${stats.errors} errors, ${stats.cache_hits} cache hits (${hitRate}% hit rate), ${formattedTime} total`);
            } else {
                updateStatusMessage(`Processing complete! ${allMappings.length} exam records processed successfully.`);
            }
            
        } catch (error) {
            console.error('Batch processing failed:', error);
            updateStatusMessage(`Batch processing failed, falling back to individual processing...`);
            // Fall back to individual processing if batch fails
            console.log('Falling back to individual processing...');
            await processIndividually(codes);
        }
        
        // Set progress to 100%
        progressFill.style.width = '100%';
    }

    // --- CORE LOGIC ---
    async function processFile(file) {
        if (!file.name.endsWith('.json')) {
            alert('Please upload a valid JSON file.');
            return;
        }

        // Hide upload interface during processing
        hideUploadInterface();
        
        fileInfo.innerHTML = `<strong>File loaded:</strong> ${file.name} (${formatFileSize(file.size)})`;
        fileInfo.style.display = 'block';
        progressBar.style.display = 'block';
        progressFill.style.width = '0%';
        resultsSection.style.display = 'none';
        allMappings = [];
        summaryData = null;
        
        // Clear any existing status message
        const existingStatus = document.getElementById('statusMessage');
        if (existingStatus) existingStatus.style.display = 'none';

        const reader = new FileReader();
        reader.onload = async function(e) {
  		    try {
        		const codes = JSON.parse(e.target.result);
        		if (!Array.isArray(codes) || codes.length === 0) {
            		alert('JSON file is empty or not in the correct array format.');
            		progressBar.style.display = 'none';
            		showUploadInterface();
            		return;
        		}

        		console.log(`Processing ${codes.length} exam records...`);
        		updateStatusMessage(`📁 Loaded ${codes.length} exam records from ${file.name}. Starting processing...`);
        
				
        		await processBatch(codes);
        
        		runAnalysis(allMappings);

   			 } catch (error) {
        		alert('Error processing file: ' + error.message);
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
            fileInfo.innerHTML = `<strong>Test running:</strong> Verifying engine performance...`;
            fileInfo.style.display = 'block';
            progressBar.style.display = 'block';
            progressFill.style.width = '25%';
            updateStatusMessage(`Calling backend sanity test endpoint with model: '${currentModel}'...`);

            // Debug: Log the URL being called
            console.log('Sanity test URL:', apiConfig.SANITY_TEST_URL);
            console.log('API config:', apiConfig);

            // Call the correct backend endpoint
            const response = await fetch(apiConfig.SANITY_TEST_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: currentModel })
            });
            
            progressFill.style.width = '75%';

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`API returned status ${response.status}: ${errorText}`);
            }

            allMappings = await response.json();
            console.log(`Completed processing. Generated ${allMappings.length} results.`);
            
            progressFill.style.width = '100%';
            updateStatusMessage(`Sanity test complete!`);
            
            // Run analysis on the results
            runAnalysis(allMappings);

        } catch (error) {
            console.error('Sanity test failed:', error);
            fileInfo.innerHTML = `<div class="file-details error"><h3>❌ Sanity Test Failed</h3><p><strong>Error:</strong> ${error.message}</p></div>`;
            progressBar.style.display = 'none';
            showUploadInterface();
        } finally {
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
    
    // --- MODEL TOGGLE FUNCTIONS ---
    function switchModel(modelKey) {
        // Validate model exists and is available
        if (!availableModels[modelKey] || availableModels[modelKey].status !== 'available') {
            console.warn(`Model ${modelKey} is not available`);
            return;
        }
        
        // Update global state
        currentModel = modelKey;
        
        // Update UI - toggle active states
        document.querySelectorAll('.model-toggle').forEach(btn => btn.classList.remove('active'));
        
        // Activate selected model button
        const selectedButton = document.getElementById(`${modelKey}ModelBtn`);
        if (selectedButton) {
            selectedButton.classList.add('active');
        }
        
        console.log(`Switched to ${modelKey} model (${availableModels[modelKey].name})`);
        
        // Show notification with dynamic model name
        const displayName = formatModelName(modelKey);
        updateStatusMessage(`Switched to ${displayName} model`);
        setTimeout(() => {
            const statusDiv = document.getElementById('statusMessage');
            if (statusDiv) statusDiv.style.display = 'none';
        }, 3000);
    }
    
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
    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024, sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    }
    
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