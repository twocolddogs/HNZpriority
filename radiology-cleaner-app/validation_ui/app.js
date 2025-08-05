/**
 * HITL Validation UI - JavaScript Application
 * 
 * This application provides a web interface for human validation of 
 * radiology exam standardization results.
 */

class ValidationApp {
    constructor() {
        this.viewData = null;
        this.userDecisions = {};
        this.currentFilter = 'all'; // 'all' or 'attention'
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Check for view_data URL parameter first
        const urlParams = new URLSearchParams(window.location.search);
        const viewDataUrl = urlParams.get('view_data');

        if (viewDataUrl) {
            this.loadViewDataFromUrl(viewDataUrl);
        } else {
            // File input for loading validation data (only if no URL param)
            document.getElementById('viewDataFile').addEventListener('change', (e) => {
                this.loadViewDataFromFile(e.target.files[0]);
            });
        }

        // Control buttons
        document.getElementById('saveDecisions').addEventListener('click', () => {
            this.saveDecisions();
        });

        document.getElementById('clearDecisions').addEventListener('click', () => {
            this.clearAllDecisions();
        });

        document.getElementById('showOnlyAttention').addEventListener('click', () => {
            this.setFilter('attention');
        });

        document.getElementById('showAll').addEventListener('click', () => {
            this.setFilter('all');
        });
    }

    async loadViewDataFromFile(file) {
        if (!file) return;

        this.showLoading(true);
        this.showError(null);

        try {
            const text = await this.readFileAsText(file);
            const data = JSON.parse(text);
            this.processViewData(data);
        } catch (error) {
            this.showError(`Error loading view data from file: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    async loadViewDataFromUrl(url) {
        this.showLoading(true);
        this.showError(null);

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.processViewData(data);
        } catch (error) {
            this.showError(`Error loading view data from URL: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    processViewData(data) {
        this.viewData = data;
        this.validateViewData();
        this.renderSummary();
        this.renderValidationView();
        
        // Show the UI sections
        document.getElementById('summarySection').style.display = 'block';
        document.getElementById('controlsSection').style.display = 'block';
        document.getElementById('validationContent').style.display = 'block';
    }

    readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }

    validateViewData() {
        if (!this.viewData || typeof this.viewData !== 'object') {
            throw new Error('Invalid view data format');
        }

        if (!this.viewData.grouped_results) {
            throw new Error('View data missing grouped_results');
        }

        if (!this.viewData._metadata || !this.viewData._metadata.summary) {
            throw new Error('View data missing metadata or summary');
        }
    }

    renderSummary() {
        const summary = this.viewData._metadata.summary;
        
        document.getElementById('totalItems').textContent = summary.total_items || 0;
        document.getElementById('totalGroups').textContent = summary.total_groups || 0;
        document.getElementById('needsAttention').textContent = summary.needs_attention_items || 0;
        document.getElementById('singletonGroups').textContent = summary.singleton_groups || 0;
        document.getElementById('autoApprovalRate').textContent = 
            Math.round((summary.approval_rate || 0) * 100) + '%';
    }

    renderValidationView() {
        const container = document.getElementById('groupsContainer');
        container.innerHTML = '';

        const groupedResults = this.viewData.grouped_results;
        
        for (const [snomedId, results] of Object.entries(groupedResults)) {
            const groupElement = this.createGroupElement(snomedId, results);
            container.appendChild(groupElement);
        }
    }

    createGroupElement(snomedId, results) {
        const hasAttention = results.some(result => result.needs_attention);
        
        // Skip group if filtering and no attention needed
        if (this.currentFilter === 'attention' && !hasAttention) {
            const div = document.createElement('div');
            div.style.display = 'none';
            return div;
        }

        const group = document.createElement('div');
        group.className = 'group';

        // Group header
        const header = document.createElement('div');
        header.className = `group-header ${hasAttention ? 'attention' : ''}`;
        
        const title = document.createElement('div');
        title.className = 'group-title';
        title.textContent = this.getGroupTitle(snomedId, results);
        
        const badge = document.createElement('div');
        badge.className = 'group-badge';
        badge.textContent = `${results.length} item${results.length !== 1 ? 's' : ''}`;
        
        header.appendChild(title);
        header.appendChild(badge);

        // Group content
        const content = document.createElement('div');
        content.className = 'group-content';

        results.forEach(result => {
            const itemElement = this.createResultItemElement(result);
            content.appendChild(itemElement);
        });

        group.appendChild(header);
        group.appendChild(content);

        return group;
    }

    getGroupTitle(snomedId, results) {
        if (snomedId === 'ERROR') {
            return 'Processing Errors';
        } else if (snomedId === 'UNMATCHED') {
            return 'No Match Found';
        } else {
            // Get the clean name from the first result
            const firstResult = results[0];
            const cleanName = firstResult.clean_name || firstResult.snomed_fsn || 'Unknown';
            return `${cleanName} (${snomedId})`;
        }
    }

    createResultItemElement(result) {
        const item = document.createElement('div');
        item.className = `result-item ${result.needs_attention ? 'highlight' : ''}`;
        
        const uniqueId = result.unique_input_id;

        // Input information
        const inputInfo = document.createElement('div');
        inputInfo.className = 'input-info';
        inputInfo.innerHTML = `
            <div>${this.escapeHtml(result.input_exam || result.exam_name || 'Unknown')}</div>
            <div class="input-details">
                ${result.exam_code ? `Code: ${this.escapeHtml(result.exam_code)} | ` : ''}
                ${result.data_source ? `Source: ${this.escapeHtml(result.data_source)}` : ''}
            </div>
        `;

        // Match information
        const matchInfo = document.createElement('div');
        matchInfo.className = 'match-info';
        if (result.error) {
            matchInfo.innerHTML = `<div class="match-name" style="color: #e74c3c;">Error</div>
                                  <div class="match-details">${this.escapeHtml(result.error)}</div>`;
        } else {
            matchInfo.innerHTML = `
                <div class="match-name">${this.escapeHtml(result.clean_name || 'No match')}</div>
                <div class="match-details">${this.escapeHtml(result.snomed_fsn || '')}</div>
            `;
        }

        // Confidence
        const confidence = document.createElement('div');
        confidence.className = 'confidence';
        const conf = result.confidence || 0;
        confidence.textContent = `${Math.round(conf * 100)}%`;
        
        if (conf >= 0.85) confidence.classList.add('high');
        else if (conf >= 0.65) confidence.classList.add('medium');
        else confidence.classList.add('low');

        // Flags
        const flags = document.createElement('div');
        flags.className = 'flags';
        
        if (result.error) {
            flags.appendChild(this.createFlag('error', 'Error'));
        }
        
        if (result.suspicion_flag === 'singleton_mapping') {
            flags.appendChild(this.createFlag('singleton', 'Singleton'));
        }
        
        if (result.ambiguous) {
            flags.appendChild(this.createFlag('', 'Ambiguous'));
        }

        // Actions
        const actions = document.createElement('div');
        actions.className = 'actions';
        
        // Check if user has already made a decision
        const existingDecision = this.userDecisions[uniqueId];
        
        // Action buttons
        const actionButtons = [
            { action: 'approve', label: 'Approve', class: 'approve' },
            { action: 'fail', label: 'Fail', class: 'fail' },
            { action: 'review', label: 'Review', class: 'review' },
            { action: 'defer', label: 'Defer', class: 'defer' }
        ];

        actionButtons.forEach(({ action, label, class: btnClass }) => {
            const btn = document.createElement('button');
            btn.className = `action-btn ${btnClass}`;
            btn.textContent = label;
            btn.dataset.uniqueId = uniqueId;
            btn.dataset.action = action;
            
            if (existingDecision && existingDecision.action === action) {
                btn.classList.add('selected');
            }
            
            btn.addEventListener('click', (e) => {
                this.handleActionClick(e, result);
            });
            
            actions.appendChild(btn);
        });

        // Status indicator
        if (existingDecision) {
            const statusIndicator = document.createElement('div');
            statusIndicator.className = 'status-indicator status-actioned';
            statusIndicator.textContent = `Marked for ${existingDecision.action}`;
            actions.appendChild(statusIndicator);
        }

        item.appendChild(inputInfo);
        item.appendChild(matchInfo);
        item.appendChild(confidence);
        item.appendChild(flags);
        item.appendChild(actions);

        return item;
    }

    createFlag(className, text) {
        const flag = document.createElement('span');
        flag.className = `flag ${className}`;
        flag.textContent = text;
        return flag;
    }

    handleActionClick(event, result) {
        const uniqueId = event.target.dataset.uniqueId;
        const action = event.target.dataset.action;
        
        // Remove selected class from all buttons in this group
        const allButtons = event.target.parentElement.querySelectorAll('.action-btn');
        allButtons.forEach(btn => btn.classList.remove('selected'));
        
        // Add selected class to clicked button
        event.target.classList.add('selected');
        
        // Handle special actions that require additional input
        let note = '';
        let hint = null;
        
        if (action === 'fail') {
            note = prompt('Why is this mapping incorrect? (Optional note)') || '';
        } else if (action === 'review') {
            note = prompt('Why does this need reprocessing? (Optional note)') || '';
            // For review actions, we could add reprocessing hints
            // hint = { force_secondary_pipeline: true };
        } else if (action === 'defer') {
            note = prompt('Why are you deferring this decision? (Optional note)') || '';
        }
        
        // Store the decision
        this.userDecisions[uniqueId] = {
            action: action,
            note: note
        };
        
        if (hint) {
            this.userDecisions[uniqueId].hint = hint;
        }
        
        // Update status indicator
        this.updateStatusIndicator(event.target.parentElement, action);
        
        // Update decision count
        this.updateDecisionCount();
    }

    updateStatusIndicator(actionsContainer, action) {
        // Remove existing status indicator
        const existingStatus = actionsContainer.querySelector('.status-indicator');
        if (existingStatus) {
            existingStatus.remove();
        }
        
        // Add new status indicator
        const statusIndicator = document.createElement('div');
        statusIndicator.className = 'status-indicator status-actioned';
        statusIndicator.textContent = `Marked for ${action}`;
        actionsContainer.appendChild(statusIndicator);
    }

    updateDecisionCount() {
        const decisionCount = Object.keys(this.userDecisions).length;
        const saveButton = document.getElementById('saveDecisions');
        saveButton.textContent = `Save Decisions (${decisionCount})`;
    }

    setFilter(filter) {
        this.currentFilter = filter;
        
        // Update button states
        document.getElementById('showOnlyAttention').classList.toggle('active', filter === 'attention');
        document.getElementById('showAll').classList.toggle('active', filter === 'all');
        
        // Re-render the view
        this.renderValidationView();
    }

    saveDecisions() {
        if (Object.keys(this.userDecisions).length === 0) {
            alert('No decisions to save. Make some validation decisions first.');
            return;
        }
        
        // Create decisions file content
        const decisionsData = JSON.stringify(this.userDecisions, null, 2);
        
        // Trigger download
        const blob = new Blob([decisionsData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'decisions.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        URL.revokeObjectURL(url);
        
        // Show success message
        this.showInfo(`Saved ${Object.keys(this.userDecisions).length} decisions to decisions.json`);
    }

    clearAllDecisions() {
        if (Object.keys(this.userDecisions).length === 0) {
            return;
        }
        
        if (confirm('Are you sure you want to clear all decisions? This cannot be undone.')) {
            this.userDecisions = {};
            this.updateDecisionCount();
            this.renderValidationView(); // Re-render to remove status indicators
        }
    }

    showLoading(show) {
        document.getElementById('loadingMessage').style.display = show ? 'block' : 'none';
    }

    showError(message) {
        const errorElement = document.getElementById('errorMessage');
        if (message) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        } else {
            errorElement.style.display = 'none';
        }
    }

    showInfo(message) {
        // Create temporary info message
        const infoDiv = document.createElement('div');
        infoDiv.className = 'info-message';
        infoDiv.textContent = message;
        
        const container = document.querySelector('.container');
        container.insertBefore(infoDiv, container.firstChild);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (infoDiv.parentNode) {
                infoDiv.parentNode.removeChild(infoDiv);
            }
        }, 5000);
    }

    escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new ValidationApp();
});