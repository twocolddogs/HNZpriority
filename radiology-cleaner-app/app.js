window.addEventListener('DOMContentLoaded', function() {
    // --- DYNAMIC API CONFIGURATION ---
    // Environment-aware API URL detection
    function detectApiUrls() {
        const hostname = window.location.hostname;
        const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
        const isProduction = hostname.includes('radiology-cleaner-frontend-prod') || hostname.includes('hnzradtools');
        const isStaging = hostname.includes('radiology-cleaner-frontend-staging');
        
        // API base URLs - Use relative /api/ for static sites (proxied by Render)
        const apiConfigs = {
            local: {
                base: 'http://localhost:10000',
                mode: 'LOCAL DEVELOPMENT'
            },
            staging: {
                base: '/api', // Proxied to backend by Render static site
                mode: 'STAGING (Static)'
            },
            production: {
                base: '/api', // Proxied to backend by Render static site
                mode: 'PRODUCTION (Static)'
            },
            fallback: {
                base: 'https://radiology-api-staging.onrender.com',
                mode: 'STAGING (Direct)'
            }
        };
        
        let config;
        if (isLocalhost) {
            config = apiConfigs.local;
        } else if (isProduction) {
            config = apiConfigs.production;
        } else if (isStaging) {
            config = apiConfigs.staging;
        } else {
            config = apiConfigs.fallback;
        }
        
        return {
            API_URL: `${config.base}/parse_enhanced`,
            BATCH_API_URL: `${config.base}/parse_batch`,
            mode: config.mode,
            baseUrl: config.base
        };
    }
    
    const apiConfig = detectApiUrls();
    const API_URL = apiConfig.API_URL;
    const BATCH_API_URL = apiConfig.BATCH_API_URL;
    
    console.log(`Frontend running in ${apiConfig.mode} mode`);
    console.log(`API endpoints: ${apiConfig.baseUrl}`);
    
    // Global model selection state
    let currentModel = 'default';
    
    // Test API connectivity on page load
    async function testApiConnectivity() {
        try {
            const response = await fetch(`${apiConfig.baseUrl}/health`, { 
                method: 'GET',
                timeout: 5000 
            });
            if (response.ok) {
                console.log('✓ API connectivity test passed');
            } else {
                console.warn('⚠ API health check returned non-200 status:', response.status);
            }
        } catch (error) {
            console.error('✗ API connectivity test failed:', error);
            console.error(`Check if backend is deployed at: ${apiConfig.baseUrl}`);
        }
    }
    
    // Test API on page load
    testApiConnectivity();

    // --- STATE ---
    let allMappings = [];
    let summaryData = null;

    // --- DOM ELEMENTS ---
    const uploadSection = document.getElementById('uploadSection');
    const sanityTestSection = document.getElementById('sanityTestSection');
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
    
    // Model toggle event listeners
    document.getElementById('defaultModelBtn').addEventListener('click', () => switchModel('default'));
    document.getElementById('pubmedModelBtn').addEventListener('click', () => switchModel('pubmed'));
    
    // Help button event listener
    document.getElementById('helpButton').addEventListener('click', showHelpModal);
    document.getElementById('closeHelpModal').addEventListener('click', closeHelpModal);
    document.getElementById('closeHelpBtn').addEventListener('click', closeHelpModal);
    
    document.getElementById('helpModal').addEventListener('click', (e) => {
        if (e.target.id === 'helpModal') closeHelpModal();
    });
    
    function showHelpModal() {
        
        // Populate modal with system architecture content
        const helpContent = document.getElementById('helpContent');
        helpContent.innerHTML = `
            <h2>🏥 Radiology Code Semantic Cleaner</h2>
            <p><strong>What it does:</strong> This application transforms messy, inconsistent radiology exam names from different hospital systems into standardized, clinically meaningful names with structured components.</p>
            
            <h3>📋 How to Use This App</h3>
            
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

            <h3>🔄 What Happens During Processing</h3>
            
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

            <h3>📊 Understanding Your Results</h3>
            
            <p><strong>Full View:</strong> See every individual exam with its clean name, components, and confidence score</p>
            <p><strong>Consolidated View:</strong> Groups identical clean names together to show consolidation patterns</p>
            
            <h4>📈 Key Metrics</h4>
            <ul>
                <li><strong>Consolidation Ratio:</strong> How many original names were simplified (e.g., 500 → 200 = 2.5:1)</li>
                <li><strong>Confidence:</strong> AI certainty level (Green: >80%, Yellow: 60-80%, Red: <60%)</li>
                <li><strong>Gender Context:</strong> Number of exams with gender-specific components</li>
                <li><strong>Processing Stats:</strong> Speed, cache hits, and success rates</li>
            </ul>

            <h3>💾 Export Options</h3>
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

    // --- UPLOAD INTERFACE CONTROL ---
    function hideUploadInterface() {
        uploadSection.style.display = 'none';
        sanityTestSection.style.display = 'none';
    }
    
    function showUploadInterface() {
        uploadSection.style.display = 'block';
        sanityTestSection.style.display = 'block';
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
        updateStatusMessage(`🔄 Processing ${codes.length} exam records individually (one by one)...`);
        
        for (let i = 0; i < codes.length; i++) {
            const code = codes[i];
            
            // Update progress message every 10 items or so
            if (i % 10 === 0 || i === codes.length - 1) {
                updateStatusMessage(`🔄 Processing exam ${i + 1} of ${codes.length}: "${code.EXAM_NAME}"...`);
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
        updateStatusMessage(`✅ Individual processing complete! ${allMappings.length} exam records processed.`);
    }
    
    // Process files in batches (for large files)
    async function processBatch(codes) {
        console.log(`Using batch processing for ${codes.length} records...`);
        
        // Update status message
        updateStatusMessage(`🔄 Preparing ${codes.length} exam records for processing...`);
        
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
            updateStatusMessage(`📤 Sending ${codes.length} exam records to AI processing engine...`);
            
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
                updateStatusMessage(`✅ Processing complete! ${stats.successful} successful, ${stats.cache_hits} from cache (${hitRate}% hit rate), ${formattedTime} total`);
                console.log(`Batch processing completed: ${stats.successful} successful, ${stats.errors} errors, ${stats.cache_hits} cache hits (${hitRate}% hit rate), ${formattedTime} total`);
            } else {
                updateStatusMessage(`✅ Processing complete! ${allMappings.length} exam records processed successfully.`);
            }
            
        } catch (error) {
            console.error('Batch processing failed:', error);
            updateStatusMessage(`⚠️ Batch processing failed, falling back to individual processing...`);
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
                    // Show upload interface again on error
                    showUploadInterface();
                    return;
                }

                console.log(`Processing ${codes.length} exam records...`);
                updateStatusMessage(`📁 Loaded ${codes.length} exam records from ${file.name}. Starting processing...`);
                
                // Use batch processing for larger files (>50 records) or for efficiency
                if (codes.length > 50) {
                    await processBatch(codes);
                } else {
                    // Use batch processing even for smaller files for consistency
                    await processBatch(codes);
                }
                
                runAnalysis(allMappings);

            } catch (error) {
                alert('Error processing file: ' + error.message);
                progressBar.style.display = 'none';
                // Show upload interface again on error
                showUploadInterface();
            }
        };
        
        reader.readAsText(file);
    }

    async function runSanityTest() {
        console.log('🧪 Sanity test button clicked - starting test...');
        console.log('Current window location:', window.location.href);
        console.log('API config:', apiConfig);
        
        try {
            // Update button state
            const button = document.getElementById('sanityTestBtn');
            const originalText = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '⏳ Loading Test Data...';
            console.log('Button state updated, attempting to fetch test data...');
            
            // Fetch the sanity test file - try multiple paths for different deployments
            let response;
            const possiblePaths = ['./sanity_test.json', '/sanity_test.json', 'sanity_test.json'];
            let lastError;
            
            for (const path of possiblePaths) {
                try {
                    console.log(`Trying to fetch sanity test file from: ${path}`);
                    response = await fetch(path);
                    if (response.ok) {
                        console.log(`Successfully fetched from: ${path}`);
                        break;
                    } else {
                        console.warn(`Failed to fetch from ${path}: ${response.status} ${response.statusText}`);
                        lastError = new Error(`Failed to load from ${path}: ${response.statusText}`);
                    }
                } catch (error) {
                    console.warn(`Error fetching from ${path}:`, error);
                    lastError = error;
                }
            }
            
            if (!response || !response.ok) {
                throw lastError || new Error('Failed to load sanity test file from all attempted paths');
            }
            
            const sanityData = await response.json();
            console.log(`Loaded sanity test file with ${sanityData.length} test cases`);
            
            // Hide upload interface during processing (same as file upload)
            hideUploadInterface();
            
            // MATCH FILE UPLOAD BEHAVIOR - Set up UI exactly like processFile()
            fileInfo.innerHTML = `
                <div class="file-details">
                    <h3>🧪 Sanity Test Dataset</h3>
                    <p><strong>Test Cases:</strong> ${sanityData.length}</p>
                    <p><strong>Purpose:</strong> Engine performance verification</p>
                </div>
            `;
            fileInfo.style.display = 'block';
            
            // Reset progress bar and show it
            progressBar.style.display = 'block';
            progressFill.style.width = '0%';
            
            // Hide results section initially (like file upload)
            resultsSection.style.display = 'none';
            
            // Reset global state (like file upload)
            allMappings = [];
            summaryData = null;
            
            // Clear any existing status message (like file upload)
            const existingStatus = document.getElementById('statusMessage');
            if (existingStatus) existingStatus.style.display = 'none';
            
            button.innerHTML = '🔄 Processing Test Cases...';
            
            console.log(`Starting to process ${sanityData.length} sanity test cases...`);
            updateStatusMessage(`🧪 Starting sanity test with ${sanityData.length} test cases...`);
            
            // Validate data structure (same validation as file upload)
            if (!Array.isArray(sanityData) || sanityData.length === 0) {
                // Show upload interface again on error
                showUploadInterface();
                throw new Error('Sanity test data is empty or not in the correct array format.');
            }
            
            // Process the sanity test data using the SAME logic as file upload
            // Use batch processing for consistency (same as processFile does)
            if (sanityData.length > 50) {
                await processBatch(sanityData);
            } else {
                // Use batch processing even for smaller files for consistency
                await processBatch(sanityData);
            }
            
            console.log(`Completed processing. Generated ${allMappings.length} results.`);
            
            // Run analysis on the results (uses global allMappings) - SAME AS FILE UPLOAD
            runAnalysis(allMappings);
            
            // Restore button state
            button.disabled = false;
            button.innerHTML = originalText;
            
            console.log('Sanity test completed successfully');
            
        } catch (error) {
            console.error('Sanity test failed:', error);
            
            // Show error in UI
            fileInfo.innerHTML = `
                <div class="file-details error">
                    <h3>❌ Sanity Test Failed</h3>
                    <p><strong>Error:</strong> ${error.message}</p>
                </div>
            `;
            
            // Hide progress bar on error (like file upload)
            progressBar.style.display = 'none';
            
            // Show upload interface again on error
            showUploadInterface();
            
            // Restore button state
            const button = document.getElementById('sanityTestBtn');
            button.disabled = false;
            button.innerHTML = '🧪 Run Sanity Test';
        }
    }

    function runAnalysis(mappings) {
        summaryData = generateAnalyticsSummary(mappings);
        updateStatsUI(summaryData);
        displayResults(mappings);
        generateConsolidatedResults(mappings);
        resultsSection.style.display = 'block';
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

    function displayResults(results) {
        resultsBody.innerHTML = '';
        results.forEach(item => {
            const row = resultsBody.insertRow();
            row.insertCell().textContent = item.data_source;
            row.insertCell().textContent = item.exam_code;
            row.insertCell().textContent = item.exam_name;
            const cleanNameCell = row.insertCell();
            if (item.clean_name && item.clean_name.startsWith('ERROR')) {
                cleanNameCell.innerHTML = `<span class="error-message">${item.clean_name}</span>`;
            } else {
                cleanNameCell.innerHTML = `<strong>${item.clean_name}</strong>`;
            }

            // Add SNOMED Code cell
            const snomedCodeCell = row.insertCell();
            /*if (item.snomed && item.snomed.id) {
                snomedCodeCell.textContent = item.snomed.id;
            } else {
                snomedCodeCell.innerHTML = '<span style="color: #999;">-</span>';
            }*/

            // Add SNOMED FSN cell
            const snomedFsnCell = row.insertCell();
            if (item.snomed && item.snomed.fsn) {
                snomedFsnCell.textContent = item.snomed.fsn;
            } else {
                snomedFsnCell.innerHTML = '<span style="color: #999;">-</span>';
            }

            const componentsCell = row.insertCell();
            const { anatomy, laterality, contrast, technique } = item.components;
            if(anatomy && anatomy.length > 0) anatomy.forEach(a => { if (a && a.trim()) componentsCell.innerHTML += `<span class="tag anatomy">${a}</span>`});
            if(laterality && Array.isArray(laterality)) laterality.forEach(l => { if (l && l.trim()) componentsCell.innerHTML += `<span class="tag laterality">${l}</span>`});
            else if(laterality && typeof laterality === 'string' && laterality.trim()) componentsCell.innerHTML += `<span class="tag laterality">${laterality}</span>`;
            if(contrast && Array.isArray(contrast)) contrast.forEach(c => { if (c && c.trim()) componentsCell.innerHTML += `<span class="tag contrast">${c}</span>`});
            else if(contrast && typeof contrast === 'string' && contrast.trim()) componentsCell.innerHTML += `<span class="tag contrast">${contrast}</span>`;
            if(technique && technique.length > 0) technique.forEach(t => { if (t && t.trim()) componentsCell.innerHTML += `<span class="tag technique">${t}</span>`});
            
            // Add context cell
            const contextCell = row.insertCell();
            const { gender_context, age_context, clinical_context, clinical_equivalents } = item.components;
            
            if(gender_context && gender_context.trim()) contextCell.innerHTML += `<span class="tag gender">${gender_context}</span>`;
            if(age_context && age_context.trim()) contextCell.innerHTML += `<span class="tag age">${age_context}</span>`;
            if(clinical_context && clinical_context.length > 0) clinical_context.forEach(c => { if (c && c.trim()) contextCell.innerHTML += `<span class="tag clinical">${c}</span>`});
            if(clinical_equivalents && clinical_equivalents.length > 0) {
                clinical_equivalents.slice(0, 2).forEach(e => { if (e && e.trim()) contextCell.innerHTML += `<span class="tag equivalent">${e}</span>`});
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
    function switchModel(modelType) {
        // Update global state
        currentModel = modelType;
        
        // Update UI - toggle active states
        document.querySelectorAll('.model-toggle').forEach(btn => btn.classList.remove('active'));
        
        if (modelType === 'default') {
            document.getElementById('defaultModelBtn').classList.add('active');
            document.getElementById('modelDescription').textContent = 'Using default clinical model optimized for healthcare terminology';
        } else if (modelType === 'pubmed') {
            document.getElementById('pubmedModelBtn').classList.add('active');
            document.getElementById('modelDescription').textContent = 'Using NeuML/pubmedbert-base-embeddings model optimized for biomedical research texts';
        }
        
        console.log(`Switched to ${modelType} model`);
        
        // Show notification
        updateStatusMessage(`🔄 Switched to ${modelType === 'default' ? 'Clinical' : 'PubMedBERT'} model`);
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