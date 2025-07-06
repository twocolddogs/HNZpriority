// ==========================================================================
// HNZ Decision Tree Builder
// ==========================================================================

class DecisionTreeBuilder {
  constructor() {
    this.currentTree = {
      id: '',
      title: '',
      description: '',
      startStep: '',
      guides: [],
      steps: {}
    };
    
    this.currentEditingStep = null;
    this.currentEditingOption = null;
    this.advancedMode = false;
    this.pathways = [];
    this.filteredPathways = [];
    
    // Change tracking for builder
    this.hasUnsavedChanges = false;
    this.initialTreeState = null;
    
    this.init();
  }

  init() {
    console.log('Initializing DecisionTreeBuilder...');
    try {
      this.bindEvents();
      console.log('Events bound successfully');
      this.loadPathways();
      console.log('Pathways loaded successfully');
      this.updateUI();
      console.log('UI updated successfully');
      this.showView('library');
      console.log('DecisionTreeBuilder initialization complete');
    } catch (error) {
      console.error('Error during initialization:', error);
      throw error;
    }
  }

  bindEvents() {
    console.log('Binding events...');
    
    try {
      // Tab navigation
      console.log('Binding tab navigation events...');
      document.getElementById('libraryTab').addEventListener('click', () => this.showView('library'));
      document.getElementById('builderTab').addEventListener('click', () => this.showView('builder'));
      document.getElementById('birdseyeTab').addEventListener('click', () => this.showView('birdseye'));
      document.getElementById('previewTab').addEventListener('click', () => this.showView('preview'));
      document.getElementById('jsonTab').addEventListener('click', () => this.showView('json'));
      console.log('Tab navigation events bound successfully');
    } catch (error) {
      console.error('Error binding tab navigation:', error);
      throw error; // Re-throw to stop initialization
    }

    try {
      // Tree properties
      console.log('Binding tree properties events...');
      document.getElementById('treeId').addEventListener('input', (e) => {
        this.currentTree.id = e.target.value;
        this.updateJSON();
      });
      
      document.getElementById('treeTitle').addEventListener('input', (e) => {
        this.currentTree.title = e.target.value;
        this.currentTree.id = this.generateIdFromTitle(e.target.value);
        document.getElementById('treeId').value = this.currentTree.id;
        this.updateJSON();
      });
      
      document.getElementById('treeDescription').addEventListener('input', (e) => {
        this.currentTree.description = e.target.value;
        this.updateJSON();
      });
      
      document.getElementById('startStep').addEventListener('change', (e) => {
        this.currentTree.startStep = e.target.value;
        this.updateJSON();
      });
      console.log('Tree properties events bound successfully');
    } catch (error) {
      console.error('Error binding tree properties:', error);
      throw error;
    }

    try {
      // Step management
      console.log('Binding step management events...');
      document.getElementById('addStep').addEventListener('click', () => this.addStep());
      document.getElementById('addGuide').addEventListener('click', () => this.addGuide());
      console.log('Step management events bound successfully');
    } catch (error) {
      console.error('Error binding step management:', error);
      throw error;
    }

    try {
      // Modal events
      console.log('Binding modal events...');
      document.getElementById('closeModal').addEventListener('click', () => this.closeModal());
      document.getElementById('closeHelp').addEventListener('click', () => this.showView('library'));
      document.getElementById('saveStep').addEventListener('click', () => this.saveStep());
      document.getElementById('deleteStep').addEventListener('click', () => this.deleteStep());
      document.getElementById('cancelStep').addEventListener('click', () => this.closeModal());
      console.log('Modal events bound successfully');
    } catch (error) {
      console.error('Error binding modal events:', error);
      throw error;
    }

    try {
      // Option modal events
      console.log('Binding option modal events...');
      document.getElementById('closeOptionModal').addEventListener('click', () => this.closeOptionModal());
      document.getElementById('saveOption').addEventListener('click', () => this.saveOption());
      document.getElementById('deleteOption').addEventListener('click', () => this.deleteOption());
      document.getElementById('cancelOption').addEventListener('click', () => this.closeOptionModal());
      console.log('Option modal events bound successfully');
    } catch (error) {
      console.error('Error binding option modal events:', error);
      throw error;
    }

    try {
      // Option form changes
      console.log('Binding option form events...');
      document.getElementById('optionAction').addEventListener('change', (e) => {
        this.updateOptionActionUI(e.target.value);
      });
      document.getElementById('targetStep').addEventListener('change', (e) => {
        this.updateTargetStepUI(e.target.value);
      });
      document.getElementById('existingEndpoint').addEventListener('change', (e) => {
        this.updateEndpointUI(e.target.value);
      });
      console.log('Option form events bound successfully');
    } catch (error) {
      console.error('Error binding option form events:', error);
      throw error;
    }

    try {
      // Step type change
      console.log('Binding step type events...');
      // Handle radio button changes for step type
      document.querySelectorAll('input[name="stepType"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
          if (e.target.checked) {
            this.updateStepTypeUI(e.target.value);
          }
        });
      });
      console.log('Step type events bound successfully');
    } catch (error) {
      console.error('Error binding step type events:', error);
      throw error;
    }

    try {
      // Options management
      console.log('Binding options management events...');
      document.getElementById('addOption').addEventListener('click', () => this.addOption());
      // Yes/No options are now auto-populated
      console.log('Options management events bound successfully');
    } catch (error) {
      console.error('Error binding options management events:', error);
      throw error;
    }

    try {
      // Hamburger menu events
      console.log('Binding hamburger menu events...');
      document.getElementById('hamburgerToggle').addEventListener('click', () => this.toggleHamburgerMenu());
      document.getElementById('saveDraftButton').addEventListener('click', () => this.saveDraft());
      document.getElementById('publishButton').addEventListener('click', () => this.publishPathway());
      document.getElementById('menuLiveApp').addEventListener('click', () => this.closeHamburgerMenu());
      document.getElementById('menuHelp').addEventListener('click', () => { this.closeHamburgerMenu(); this.showView('help'); });
      document.getElementById('menuAdvanced').addEventListener('click', () => this.toggleAdvancedMode());
      console.log('Hamburger menu events bound successfully');
    } catch (error) {
      console.error('Error binding hamburger menu events:', error);
      throw error;
    }

    try {
      // Library view events
      console.log('Binding library view events...');
      document.getElementById('newPathway').addEventListener('click', () => this.createPathway());
      document.getElementById('statusFilter').addEventListener('change', () => this.filterPathways());
      document.getElementById('searchFilter').addEventListener('input', () => this.filterPathways());
      console.log('Library view events bound successfully');
    } catch (error) {
      console.error('Error binding library view events:', error);
      throw error;
    }

    try {
      // JSON editor events
      console.log('Binding JSON editor events...');
      document.getElementById('loadFromJson').addEventListener('click', () => this.loadFromJson());
      document.getElementById('formatJson').addEventListener('click', () => this.formatJson());
      document.getElementById('jsonOutput').addEventListener('input', () => this.validateJson());
      console.log('JSON editor events bound successfully');
    } catch (error) {
      console.error('Error binding JSON editor events:', error);
      throw error;
    }

    try {
      // Close modal on overlay click
      console.log('Binding modal overlay events...');
      
      document.getElementById('optionModal').addEventListener('click', (e) => {
        if (e.target.id === 'optionModal') {
          this.closeOptionModal();
        }
      });
      
      // Close hamburger menu on outside click
      document.addEventListener('click', (e) => {
        const hamburgerMenu = document.querySelector('.hamburger-menu');
        if (hamburgerMenu && !hamburgerMenu.contains(e.target)) {
          this.closeHamburgerMenu();
        }
      });
      
      console.log('Modal overlay events bound successfully');
    } catch (error) {
      console.error('Error binding modal overlay events:', error);
      throw error;
    }

    // Birdseye view controls are now bound dynamically in the legend

    try {
      // Guide modal events
      document.getElementById('closeGuideModal').addEventListener('click', () => this.closeGuideModal());
      document.getElementById('saveGuide').addEventListener('click', () => this.saveGuide());
      document.getElementById('deleteGuide').addEventListener('click', () => this.deleteGuide());
      document.getElementById('cancelGuide').addEventListener('click', () => this.closeGuideModal());
      document.getElementById('addGuideSection').addEventListener('click', () => this.addGuideSection());

      // Guide section modal events
      document.getElementById('closeGuideSectionModal').addEventListener('click', () => this.closeGuideSectionModal());
      document.getElementById('saveGuideSection').addEventListener('click', () => this.saveGuideSection());
      document.getElementById('deleteGuideSection').addEventListener('click', () => this.deleteGuideSection());
      document.getElementById('cancelGuideSection').addEventListener('click', () => this.closeGuideSectionModal());

      // Modal overlay clicks
      document.getElementById('guideModal').addEventListener('click', (e) => {
        if (e.target.id === 'guideModal') this.closeGuideModal();
      });
      document.getElementById('guideSectionModal').addEventListener('click', (e) => {
        if (e.target.id === 'guideSectionModal') this.closeGuideSectionModal();
      });
      console.log('Guide modal events bound successfully');
    } catch (error) {
      console.error('Error binding guide modal events:', error);
    }

    try {
      // Callout helper buttons
      console.log('Binding callout helper events...');
      document.querySelectorAll('.btn-callout').forEach(button => {
        button.addEventListener('click', () => {
          const calloutType = button.getAttribute('data-callout');
          this.insertCallout(calloutType);
        });
      });
      console.log('Callout helper events bound successfully');
    } catch (error) {
      console.error('Error binding callout helper events:', error);
    }

    try {
      // Tree property change tracking
      console.log('Binding tree property change events...');
      const treePropertyFields = ['treeId', 'treeTitle', 'treeDescription', 'startStep'];
      treePropertyFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
          field.addEventListener('input', () => this.checkForTreeChanges());
          field.addEventListener('change', () => this.checkForTreeChanges());
        }
      });
      console.log('Tree property change events bound successfully');
    } catch (error) {
      console.error('Error binding tree property change events:', error);
    }
  }

  createPathway() {
    // Initialize a new empty pathway
    this.currentTree = {
      id: `pathway-${Date.now()}`,
      title: 'New Pathway',
      subtitle: '',
      description: '',
      startStep: '',
      steps: {},
      guides: []
    };
    
    this.updateUI();
    this.updatePreview();
    this.showView('builder');
  }

  showView(viewName) {
    // Update tabs (help view doesn't have a tab)
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    if (viewName !== 'help') {
      document.getElementById(viewName + 'Tab').classList.add('active');
    }

    // Update views
    document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
    document.getElementById(viewName + 'View').classList.add('active');

    if (viewName === 'library') {
      this.renderPathwaysList();
    } else if (viewName === 'birdseye') {
      this.updateBirdseye();
      // Don't auto-fit automatically - let user use Auto Layout button if needed
    } else if (viewName === 'preview') {
      this.updatePreview();
    } else if (viewName === 'json') {
      this.updateJSON();
    } else if (viewName === 'help') {
      // Help view is static, no special handling needed
    }
  }

  updateUI() {
    this.updateTreeProperties();
    this.updateStepsList();
    this.updateStartStepSelect();
    this.updateGuidesList();
    this.updateJSON();
    
    // Capture initial state if not already captured
    if (!this.initialTreeState) {
      this.captureInitialTreeState();
    }
  }

  updateTreeProperties() {
    document.getElementById('treeId').value = this.currentTree.id;
    document.getElementById('treeTitle').value = this.currentTree.title;
    document.getElementById('treeDescription').value = this.currentTree.description;
    document.getElementById('startStep').value = this.currentTree.startStep;
  }

  updateStepsList() {
    const stepsList = document.getElementById('stepsList');
    stepsList.innerHTML = '';

    // Show regular steps
    Object.values(this.currentTree.steps).forEach(step => {
      const stepItem = document.createElement('div');
      stepItem.className = `step-card-builder${step.id === this.currentTree.startStep ? ' start-step' : ''}`;
      stepItem.addEventListener('click', () => this.editStep(step.id));

      const startBadge = step.id === this.currentTree.startStep ? '<span class="start-step-badge">Start</span>' : '';
      
      stepItem.innerHTML = `
        <div class="step-badges">
          ${startBadge}
          <span class="step-type-badge ${step.type}">${step.type.replace('-', ' ').toUpperCase()}</span>
        </div>
        <h4>${step.title || 'Untitled Step'}</h4>
        ${step.subtitle ? `<p>${step.subtitle}</p>` : ''}
      `;

      stepsList.appendChild(stepItem);
    });

    // Show virtual recommendation endpoints
    this.getRecommendationEndpoints().forEach(endpoint => {
      const stepItem = document.createElement('div');
      stepItem.className = 'step-item recommendation-endpoint';
      stepItem.addEventListener('click', () => this.editRecommendationEndpoint(endpoint.id));
      
      // Visual styling for recommendation endpoints
      stepItem.style.border = '1px solid #FB923C';
      stepItem.style.backgroundColor = '#FFF7ED';

      stepItem.innerHTML = `
        <h4>Recommendation</h4>
        <p>From: ${endpoint.sourceStep} → "${endpoint.optionText}"</p>
        <span class="step-type">recommendation endpoint</span>
      `;

      stepsList.appendChild(stepItem);
    });
  }

  getRecommendationEndpoints() {
    const endpoints = [];
    
    Object.entries(this.currentTree.steps).forEach(([stepId, step]) => {
      if (step.options) {
        step.options.forEach((option, optionIndex) => {
          if (option.action.type === 'recommend' && option.action.recommendation) {
            endpoints.push({
              id: `endpoint_${stepId}_${optionIndex}`,
              sourceStep: step.title || stepId,
              optionText: option.text,
              recommendation: option.action.recommendation,
              isVirtual: true
            });
          }
        });
      }
    });
    
    return endpoints;
  }

  updateStartStepSelect() {
    const select = document.getElementById('startStep');
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">Select start step...</option>';
    
    Object.values(this.currentTree.steps).forEach(step => {
      const option = document.createElement('option');
      option.value = step.id;
      const stepTypeText = step.type.replace('-', ' ').toUpperCase();
      option.textContent = `[${stepTypeText}] ${step.title || 'Untitled'} (${step.id})`;
      select.appendChild(option);
    });
    
    select.value = currentValue;
  }

  updateGuidesList() {
    const guidesList = document.getElementById('guidesList');
    guidesList.innerHTML = '';

    this.currentTree.guides.forEach((guide, index) => {
      const guideItem = document.createElement('div');
      guideItem.className = 'guide-item';
      
      guideItem.style.flexDirection = 'column';
      guideItem.style.alignItems = 'stretch';
      
      guideItem.innerHTML = `
        <div style="width: 100%; margin-bottom: 0.75rem;">
          <span style="font-weight: 500;">${guide.title || 'Untitled Guide'}</span>
          <p style="margin: 0; font-size: 0.875rem; color: #6B7280;">${guide.sections?.length || 0} sections</p>
        </div>
        <div style="display: flex; gap: 0.5rem; width: 100%;">
          <button class="btn secondary small" onclick="builder.editGuide(${index})" style="flex: 1; text-align: center;">Edit</button>
          <button class="btn danger small" onclick="builder.removeGuideAtIndex(${index})" style="flex: 1; text-align: center;">Remove</button>
        </div>
      `;
      
      guidesList.appendChild(guideItem);
    });
  }

  addStep() {
    // Create temporary step for editing - don't add to tree until saved
    const stepId = `step-${Date.now()}`;
    this.pendingStep = {
      id: stepId,
      title: '',
      type: 'choice',
      options: []
    };
    
    // Set up modal for new step
    this.currentEditingStep = stepId;
    
    // Reset modal fields
    document.getElementById('stepId').value = stepId;
    document.getElementById('stepTitle').value = '';
    document.getElementById('stepSubtitle').value = '';
    document.getElementById('stepQuestion').value = '';
    document.querySelector('input[name="stepType"][value="choice"]').checked = true;
    
    // Clear all sections
    document.getElementById('protocolTitle').value = '';
    document.getElementById('protocolDescription').value = '';
    document.getElementById('protocolNote').value = '';
    document.getElementById('endpointRecommendation').value = '';
    document.getElementById('endpointNotes').value = '';
    
    // Update modal for new step
    document.getElementById('modalTitle').textContent = 'Add New Step';
    document.getElementById('deleteStep').style.display = 'none';
    
    this.updateStepTypeUI('choice');
    this.updateOptionsList([]);
    this.showModal();
  }

  editRecommendationEndpoint(endpointId) {
    // Find the endpoint from our virtual endpoints
    const endpoint = this.getRecommendationEndpoints().find(ep => ep.id === endpointId);
    if (!endpoint) return;
    
    // Set up editing mode for this virtual endpoint
    this.currentEditingStep = endpointId;
    this.editingVirtualEndpoint = true;
    
    // Populate modal fields with endpoint data
    document.getElementById('stepId').value = endpointId;
    document.getElementById('stepTitle').value = `${endpoint.recommendation.modality || 'Recommendation'} Endpoint`;
    document.getElementById('stepSubtitle').value = '';
    document.getElementById('stepQuestion').value = '';
    document.querySelector('input[name="stepType"][value="endpoint"]').checked = true;
    
    // Populate endpoint fields
    document.getElementById('endpointRecommendation').value = endpoint.recommendation.recommendation || '';
    document.getElementById('endpointNotes').value = endpoint.recommendation.notes || '';
    
    // Update UI to show endpoint section
    this.updateStepTypeUI('endpoint');
    
    // Show the modal and reset scroll position
    const modal = document.getElementById('stepModal');
    modal.classList.remove('hidden');
    
    // Reset modal scroll to top
    setTimeout(() => {
      const modalContainer = modal.querySelector('.modal-container');
      if (modalContainer) {
        modalContainer.scrollTop = 0;
      }
      modal.scrollTop = 0;
    }, 0);
  }

  editStep(stepId) {
    this.currentEditingStep = stepId;
    const step = this.currentTree.steps[stepId];
    
    if (!step) return;

    // Set modal for editing existing step
    document.getElementById('modalTitle').textContent = 'Edit Step';
    document.getElementById('deleteStep').style.display = 'inline-flex';

    // Populate modal fields
    document.getElementById('stepId').value = step.id;
    document.getElementById('stepTitle').value = step.title || '';
    document.getElementById('stepSubtitle').value = step.subtitle || '';
    document.getElementById('stepQuestion').value = step.question || '';
    document.querySelector(`input[name="stepType"][value="${step.type}"]`).checked = true;

    // Guide info
    if (step.guideInfo) {
      document.getElementById('protocolTitle').value = step.guideInfo.title || '';
      document.getElementById('protocolDescription').value = step.guideInfo.description || '';
      document.getElementById('protocolNote').value = step.guideInfo.note || '';
    } else {
      document.getElementById('protocolTitle').value = '';
      document.getElementById('protocolDescription').value = '';
      document.getElementById('protocolNote').value = '';
    }

    // Endpoint info
    if (step.recommendation) {
      document.getElementById('endpointRecommendation').value = step.recommendation.recommendation || '';
      document.getElementById('endpointNotes').value = step.recommendation.notes || '';
    } else {
      document.getElementById('endpointRecommendation').value = '';
      document.getElementById('endpointNotes').value = '';
    }

    this.updateStepTypeUI(step.type);
    this.updateOptionsList(step.options || []);
    this.showModal();
  }

  updateStepTypeUI(stepType) {
    const protocolSection = document.getElementById('protocolSection');
    const optionsSection = document.getElementById('optionsSection');
    const endpointSection = document.getElementById('endpointSection');
    const stepTypeGuidance = document.getElementById('stepTypeGuidance');
    const stepQuestionLabel = document.getElementById('stepQuestionLabel');
    const stepQuestion = document.getElementById('stepQuestion');

    // Hide all sections first
    protocolSection.classList.add('hidden');
    optionsSection.classList.add('hidden');
    endpointSection.classList.add('hidden');

    // Update guidance and labels based on step type
    const guidanceConfig = {
      'choice': {
        guidance: '<h5>Multiple Choice Decision</h5><p>Present 3+ options to guide decision-making. Create clear, distinct options that cover all scenarios. Best for complex decisions with multiple pathways.</p>',
        questionLabel: 'Clinical Scenario',
        questionPlaceholder: 'Describe the clinical scenario or question that requires multiple choice selection. You can use callouts like [info]Important note[/info]'
      },
      'yes-no': {
        guidance: '<h5>Yes/No Decision</h5><p>Binary clinical decisions with clear yes/no answers. Frame as a specific clinical question that can be answered definitively. Use two fixed options: Yes and No.</p>',
        questionLabel: 'Clinical Question',
        questionPlaceholder: 'Frame as a clear clinical question with a yes/no answer. You can use callouts like [warning]Be careful[/warning]'
      },
      'endpoint': {
        guidance: '<h5>Clinical Recommendation</h5><p>Final step that provides specific, actionable clinical recommendations. This ends the decision pathway with clear guidance for healthcare professionals.</p>',
        questionLabel: 'Clinical Question',
        questionPlaceholder: 'Describe the clinical scenario or question that leads to this recommendation. You can use callouts like [info]Important note[/info]'
      }
    };

    const config = guidanceConfig[stepType] || guidanceConfig['choice'];
    
    // Update guidance section
    stepTypeGuidance.innerHTML = config.guidance;
    stepTypeGuidance.className = `step-type-guidance ${stepType}`;
    
    // Update field labels and placeholders
    stepQuestionLabel.textContent = config.questionLabel;
    stepQuestion.placeholder = config.questionPlaceholder;

    // Show relevant sections and handle special cases
    const addOptionBtn = document.getElementById('addOption');
    
    switch (stepType) {
      case 'endpoint':
        endpointSection.classList.remove('hidden');
        break;
      case 'choice':
        optionsSection.classList.remove('hidden');
        addOptionBtn.style.display = 'inline-flex';
        this.updateOptionsButtonText('Add Option');
        break;
      case 'yes-no':
        optionsSection.classList.remove('hidden');
        addOptionBtn.style.display = 'none'; // Hide add option button - yes/no has fixed 2 options
        
        // Update the step type in the data model
        const step = this.pendingStep || this.currentTree.steps[this.currentEditingStep];
        if (step) {
          step.type = 'yes-no';
        }
        
        this.ensureYesNoOptions();
        break;
    }
  }

  updateOptionsButtonText(text) {
    const addOptionBtn = document.getElementById('addOption');
    if (addOptionBtn) {
      addOptionBtn.textContent = text;
    }
  }

  ensureYesNoOptions() {
    console.log('ensureYesNoOptions called, currentEditingStep:', this.currentEditingStep);
    console.log('pendingStep:', this.pendingStep);
    
    if (!this.currentEditingStep) {
      console.log('No currentEditingStep, returning');
      return;
    }
    
    const step = this.pendingStep || this.currentTree.steps[this.currentEditingStep];
    console.log('Found step:', step);
    
    if (!step) {
      console.log('No step found, returning');
      return;
    }
    
    if (step.type !== 'yes-no') {
      console.log('Step type is not yes-no:', step.type, 'returning');
      return;
    }
    
    console.log('Step type is yes-no, checking options:', step.options);
    
    // Only auto-create options for new steps (pendingStep), not when editing existing ones
    if (this.pendingStep && (!step.options || step.options.length === 0)) {
      // Auto-create Yes/No options for new yes-no steps
      step.options = [
        { text: 'Yes', variant: 'success', action: { type: 'navigate', nextStep: '' } },
        { text: 'No', variant: 'secondary', action: { type: 'navigate', nextStep: '' } }
      ];
      console.log('Auto-created Yes/No options for new step:', step.id, step.options);
    } else if (!this.pendingStep) {
      // For existing steps, just ensure we have the minimum structure but don't overwrite
      if (!step.options || step.options.length === 0) {
        step.options = [
          { text: 'Yes', variant: 'success', action: { type: 'navigate', nextStep: '' } },
          { text: 'No', variant: 'secondary', action: { type: 'navigate', nextStep: '' } }
        ];
        console.log('Added missing Yes/No options for existing step:', step.id);
      } else {
        console.log('Existing step has options, preserving them:', step.options);
      }
      // If options exist, leave them alone to preserve user's targets and details
    }
    
    // Update the UI with current options
    console.log('Updating options list with:', step.options);
    this.updateOptionsList(step.options);
  }

  editYesNoOption(index) {
    const step = this.pendingStep || this.currentTree.steps[this.currentEditingStep];
    if (!step) return;
    
    this.ensureYesNoOptions();
    this.editOptionAtIndex(index);
  }

  updateOptionsList(options) {
    const optionsList = document.getElementById('optionsList');
    optionsList.innerHTML = '';

    // Get the current step to check its type
    const currentStep = this.pendingStep || this.currentTree.steps[this.currentEditingStep];
    const isYesNoStep = currentStep && currentStep.type === 'yes-no';

    options.forEach((option, index) => {
      const optionItem = document.createElement('div');
      optionItem.className = 'option-item';
      
      let actionText = '';
      if (option.action.type === 'navigate') {
        actionText = `→ ${option.action.nextStep}`;
      } else if (option.action.type === 'recommend') {
        actionText = `⚡ ${option.action.recommendation.recommendation || 'Recommendation'}`;
      }

      // For yes-no steps, hide the remove button to prevent deletion of Yes/No options
      const removeButtonHtml = isYesNoStep ? '' : `<button class="btn danger small" onclick="builder.removeOptionAtIndex(${index})">Remove</button>`;

      optionItem.innerHTML = `
        <div class="option-content">
          <div><strong>${option.text}</strong></div>
          <div style="font-size: 0.875rem; color: var(--text-muted);">${actionText}</div>
        </div>
        <div class="option-controls">
          <button class="btn secondary small" onclick="builder.editOptionAtIndex(${index})">Edit</button>
          ${removeButtonHtml}
        </div>
      `;
      
      optionsList.appendChild(optionItem);
    });
  }

  addOption() {
    if (!this.currentEditingStep) return;

    const step = this.pendingStep || this.currentTree.steps[this.currentEditingStep];
    if (!step) return;
    
    if (!step.options) step.options = [];

    const newOption = {
      text: 'New Option',
      variant: 'primary',
      action: {
        type: 'navigate',
        nextStep: ''
      }
    };

    step.options.push(newOption);
    this.updateOptionsList(step.options);
    this.editOptionAtIndex(step.options.length - 1);
  }


  saveStep() {
    if (!this.currentEditingStep) return;

    // Handle virtual endpoint editing
    if (this.editingVirtualEndpoint) {
      const endpointId = this.currentEditingStep;
      const newRecommendation = {
        recommendation: document.getElementById('endpointRecommendation').value,
        notes: document.getElementById('endpointNotes').value
      };
      
      // Find all steps that point to this recommendation endpoint and update them
      Object.values(this.currentTree.steps).forEach(step => {
        if (step.options) {
          step.options.forEach(option => {
            if (option.action && option.action.type === 'recommend') {
              // Check if this recommendation matches the endpoint we're editing
              const endpoint = this.getRecommendationEndpoints().find(ep => ep.id === endpointId);
              if (endpoint && JSON.stringify(option.action.recommendation) === JSON.stringify(endpoint.recommendation)) {
                option.action.recommendation = { ...newRecommendation };
              }
            }
          });
        }
      });
      
      this.editingVirtualEndpoint = false;
      this.updateUI();
      this.updateJSON();
      this.updatePreview();
      this.closeModal();
      return;
    }

    // Handle new step creation vs editing existing step
    let step;
    if (this.pendingStep && !this.currentTree.steps[this.currentEditingStep]) {
      // This is a new step - create it in the tree
      step = this.pendingStep;
      this.currentTree.steps[this.currentEditingStep] = step;
      
      // If no startStep is set, make this the startStep
      if (!this.currentTree.startStep) {
        this.currentTree.startStep = step.id;
      }
      
      this.pendingStep = null;
    } else {
      // This is an existing step
      step = this.currentTree.steps[this.currentEditingStep];
    }
    
    // Basic properties
    const newId = document.getElementById('stepId').value;
    const title = document.getElementById('stepTitle').value;
    const subtitle = document.getElementById('stepSubtitle').value;
    const question = document.getElementById('stepQuestion').value;
    const type = document.querySelector('input[name="stepType"]:checked')?.value;

    // Handle ID change
    if (newId !== step.id) {
      const oldId = step.id;
      
      // Update all references to the old ID throughout the tree
      this.updateStepIdReferences(oldId, newId);
      
      // Update the step in the steps object
      delete this.currentTree.steps[oldId];
      this.currentTree.steps[newId] = step;
      step.id = newId;
      
      // Update current editing reference
      this.currentEditingStep = newId;
    }

    step.title = title;
    step.subtitle = subtitle;
    step.question = question;
    step.type = type;

    // Guide info
    if (type === 'guide') {
      step.guideInfo = {
        title: document.getElementById('protocolTitle').value,
        description: document.getElementById('protocolDescription').value,
        note: document.getElementById('protocolNote').value
      };
    } else {
      delete step.guideInfo;
    }

    // Endpoint info
    if (type === 'endpoint') {
      step.recommendation = {
        recommendation: document.getElementById('endpointRecommendation').value,
        notes: document.getElementById('endpointNotes').value
      };
      delete step.options;
    } else {
      delete step.recommendation;
    }

    this.closeModal();
    this.updateUI();
    this.updateJSON();
    this.updatePreview();
    
    // Mark as changed
    this.checkForTreeChanges();
  }

  updateStepIdReferences(oldId, newId) {
    // Update startStep if it matches the old ID
    if (this.currentTree.startStep === oldId) {
      this.currentTree.startStep = newId;
    }
    
    // Update all option navigation targets that point to the old ID
    Object.values(this.currentTree.steps).forEach(step => {
      if (step.options) {
        step.options.forEach(option => {
          if (option.action && option.action.type === 'navigate' && option.action.nextStep === oldId) {
            option.action.nextStep = newId;
          }
        });
      }
    });
    
    console.log(`Updated all references from step ID "${oldId}" to "${newId}"`);
  }

  deleteStep() {
    if (!this.currentEditingStep) return;
    
    if (confirm('Are you sure you want to delete this step?')) {
      delete this.currentTree.steps[this.currentEditingStep];
      this.closeModal();
      this.updateUI();
      this.updateJSON();
      this.updatePreview();
    }
  }

  addGuide() {
    this.currentEditingGuide = null;
    this.currentEditingGuideIndex = -1;
    
    // Reset form
    document.getElementById('guideTitle').value = '';
    document.getElementById('guideModalTitle').textContent = 'Add Guide';
    document.getElementById('deleteGuide').style.display = 'none';
    
    this.updateGuideSectionsList([]);
    this.showGuideModal();
  }

  editGuide(index) {
    const guide = this.currentTree.guides[index];
    this.currentEditingGuide = { ...guide };
    this.currentEditingGuideIndex = index;
    
    // Populate form
    document.getElementById('guideTitle').value = guide.title || '';
    document.getElementById('guideModalTitle').textContent = 'Edit Guide';
    document.getElementById('deleteGuide').style.display = 'inline-flex';
    
    this.updateGuideSectionsList(guide.sections || []);
    this.showGuideModal();
  }

  showGuideModal() {
    document.getElementById('guideModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  closeGuideModal() {
    document.getElementById('guideModal').classList.add('hidden');
    document.body.style.overflow = 'auto';
    this.currentEditingGuide = null;
    this.currentEditingGuideIndex = -1;
  }

  saveGuide() {
    const title = document.getElementById('guideTitle').value.trim();
    if (!title) {
      alert('Please enter a guide title');
      return;
    }

    const guideData = {
      id: this.currentEditingGuide?.id || `guide-${Date.now()}`,
      title: title,
      sections: this.currentEditingGuide?.sections || []
    };

    if (this.currentEditingGuideIndex >= 0) {
      // Update existing guide
      this.currentTree.guides[this.currentEditingGuideIndex] = guideData;
    } else {
      // Add new guide
      this.currentTree.guides.push(guideData);
    }

    this.updateGuidesList();
    this.updateJSON();
    this.updatePreview();
    this.closeGuideModal();
  }

  deleteGuide() {
    if (this.currentEditingGuideIndex >= 0) {
      if (confirm('Are you sure you want to delete this guide?')) {
        this.currentTree.guides.splice(this.currentEditingGuideIndex, 1);
        this.updateGuidesList();
        this.updateJSON();
        this.updatePreview();
        this.closeGuideModal();
      }
    }
  }

  updateGuideSectionsList(sections) {
    const sectionsList = document.getElementById('guideSectionsList');
    sectionsList.innerHTML = '';

    sections.forEach((section, index) => {
      const sectionItem = document.createElement('div');
      sectionItem.className = 'option-item';
      
      const typeLabels = {
        guide: 'Guide (Blue)',
        info: 'Information (Purple)', 
        warning: 'Warning (Orange)',
        success: 'Success (Green)',
        danger: 'Danger (Red)'
      };

      sectionItem.innerHTML = `
        <div class="option-content">
          <strong>${section.title || 'Untitled Section'}</strong>
          <p>${typeLabels[section.type] || section.type}</p>
          <p style="color: var(--text-muted); font-size: 0.875rem;">${section.content ? section.content.substring(0, 60) + '...' : 'No content'}</p>
        </div>
        <div class="option-controls">
          <button class="btn secondary small" onclick="builder.editGuideSection(${index})">Edit</button>
          <button class="btn danger small" onclick="builder.removeGuideSection(${index})">Remove</button>
        </div>
      `;

      sectionsList.appendChild(sectionItem);
    });
  }

  addGuideSection() {
    this.currentEditingSection = null;
    this.currentEditingSectionIndex = -1;
    
    // Reset form
    document.getElementById('sectionTitle').value = '';
    document.getElementById('sectionType').value = 'guide';
    document.getElementById('sectionContent').value = '';
    document.getElementById('guideSectionModalTitle').textContent = 'Add Section';
    document.getElementById('deleteGuideSection').style.display = 'none';
    
    this.showGuideSectionModal();
  }

  editGuideSection(index) {
    const sections = this.currentEditingGuide?.sections || [];
    const section = sections[index];
    this.currentEditingSection = { ...section };
    this.currentEditingSectionIndex = index;
    
    // Populate form
    document.getElementById('sectionTitle').value = section.title || '';
    document.getElementById('sectionType').value = section.type || 'guide';
    document.getElementById('sectionContent').value = section.content || '';
    document.getElementById('guideSectionModalTitle').textContent = 'Edit Section';
    document.getElementById('deleteGuideSection').style.display = 'inline-flex';
    
    this.showGuideSectionModal();
  }

  showGuideSectionModal() {
    document.getElementById('guideSectionModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Bind callout buttons for guide section content
    this.bindCalloutButtons('sectionContent');
  }

  closeGuideSectionModal() {
    document.getElementById('guideSectionModal').classList.add('hidden');
    document.body.style.overflow = 'auto';
    this.currentEditingSection = null;
    this.currentEditingSectionIndex = -1;
  }

  saveGuideSection() {
    const title = document.getElementById('sectionTitle').value.trim();
    const type = document.getElementById('sectionType').value;
    const content = document.getElementById('sectionContent').value.trim();
    
    if (!title) {
      alert('Please enter a section title');
      return;
    }

    const sectionData = {
      title: title,
      type: type,
      content: content
    };

    // Initialize guide editing object if needed
    if (!this.currentEditingGuide) {
      this.currentEditingGuide = { sections: [] };
    }
    if (!this.currentEditingGuide.sections) {
      this.currentEditingGuide.sections = [];
    }

    if (this.currentEditingSectionIndex >= 0) {
      // Update existing section
      this.currentEditingGuide.sections[this.currentEditingSectionIndex] = sectionData;
    } else {
      // Add new section
      this.currentEditingGuide.sections.push(sectionData);
    }

    this.updateGuideSectionsList(this.currentEditingGuide.sections);
    this.updateJSON();
    this.updatePreview();
    this.closeGuideSectionModal();
  }

  deleteGuideSection() {
    if (this.currentEditingSectionIndex >= 0) {
      if (confirm('Are you sure you want to delete this section?')) {
        this.currentEditingGuide.sections.splice(this.currentEditingSectionIndex, 1);
        this.updateGuideSectionsList(this.currentEditingGuide.sections);
        this.updateJSON();
        this.updatePreview();
        this.closeGuideSectionModal();
      }
    }
  }

  removeGuideSection(index) {
    if (confirm('Are you sure you want to remove this section?')) {
      this.currentEditingGuide.sections.splice(index, 1);
      this.updateGuideSectionsList(this.currentEditingGuide.sections);
      this.updateJSON();
      this.updatePreview();
    }
  }


  showModal() {
    const modal = document.getElementById('stepModal');
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Store initial form state for change tracking
    this.captureInitialStepState();
    
    // Set up change listeners
    this.setupStepChangeListeners();
    
    // Hide save button initially
    this.updateSaveButtonVisibility(false);
    
    // Reset modal scroll to top
    setTimeout(() => {
      const modalContainer = modal.querySelector('.modal-container');
      if (modalContainer) {
        modalContainer.scrollTop = 0;
      }
      modal.scrollTop = 0;
    }, 0);
  }

  captureInitialStepState() {
    this.initialStepState = {
      stepId: document.getElementById('stepId').value,
      stepTitle: document.getElementById('stepTitle').value,
      stepSubtitle: document.getElementById('stepSubtitle').value,
      stepQuestion: document.getElementById('stepQuestion').value,
      stepType: document.querySelector('input[name="stepType"]:checked')?.value || '',
      protocolTitle: document.getElementById('protocolTitle').value,
      protocolDescription: document.getElementById('protocolDescription').value,
      protocolNote: document.getElementById('protocolNote').value,
      endpointRecommendation: document.getElementById('endpointRecommendation').value,
      endpointNotes: document.getElementById('endpointNotes').value
    };
  }

  setupStepChangeListeners() {
    // Remove existing listeners to avoid duplicates
    this.removeStepChangeListeners();
    
    const fields = [
      'stepId', 'stepTitle', 'stepSubtitle', 'stepQuestion',
      'protocolTitle', 'protocolDescription', 'protocolNote',
      'endpointRecommendation', 'endpointNotes'
    ];
    
    this.stepChangeHandler = () => this.checkForStepChanges();
    
    fields.forEach(fieldId => {
      const field = document.getElementById(fieldId);
      if (field) {
        field.addEventListener('input', this.stepChangeHandler);
      }
    });
    
    // Add listeners for radio buttons
    const radioButtons = document.querySelectorAll('input[name="stepType"]');
    radioButtons.forEach(radio => {
      radio.addEventListener('change', this.stepChangeHandler);
    });
  }

  removeStepChangeListeners() {
    if (!this.stepChangeHandler) return;
    
    const fields = [
      'stepId', 'stepTitle', 'stepSubtitle', 'stepQuestion',
      'protocolTitle', 'protocolDescription', 'protocolNote',
      'endpointRecommendation', 'endpointNotes'
    ];
    
    fields.forEach(fieldId => {
      const field = document.getElementById(fieldId);
      if (field) {
        field.removeEventListener('input', this.stepChangeHandler);
      }
    });
    
    const radioButtons = document.querySelectorAll('input[name="stepType"]');
    radioButtons.forEach(radio => {
      radio.removeEventListener('change', this.stepChangeHandler);
    });
  }

  checkForStepChanges() {
    if (!this.initialStepState) return;
    
    const currentState = {
      stepId: document.getElementById('stepId').value,
      stepTitle: document.getElementById('stepTitle').value,
      stepSubtitle: document.getElementById('stepSubtitle').value,
      stepQuestion: document.getElementById('stepQuestion').value,
      stepType: document.querySelector('input[name="stepType"]:checked')?.value || '',
      protocolTitle: document.getElementById('protocolTitle').value,
      protocolDescription: document.getElementById('protocolDescription').value,
      protocolNote: document.getElementById('protocolNote').value,
      endpointRecommendation: document.getElementById('endpointRecommendation').value,
      endpointNotes: document.getElementById('endpointNotes').value
    };
    
    const hasChanges = Object.keys(this.initialStepState).some(key => 
      this.initialStepState[key] !== currentState[key]
    );
    
    this.updateSaveButtonVisibility(hasChanges);
  }

  updateSaveButtonVisibility(hasChanges) {
    const saveButton = document.getElementById('saveStep');
    if (saveButton) {
      saveButton.style.display = hasChanges ? 'inline-flex' : 'none';
    }
  }

  closeModal() {
    document.getElementById('stepModal').classList.add('hidden');
    document.body.style.overflow = 'auto';
    this.currentEditingStep = null;
    this.currentEditingOption = null;
    
    // Clean up change listeners
    this.removeStepChangeListeners();
    this.initialStepState = null;
  }

  toggleHamburgerMenu() {
    const dropdown = document.getElementById('hamburgerDropdown');
    const button = document.getElementById('hamburgerToggle');
    
    dropdown.classList.toggle('hidden');
    button.classList.toggle('active');
  }

  closeHamburgerMenu() {
    const dropdown = document.getElementById('hamburgerDropdown');
    const button = document.getElementById('hamburgerToggle');
    
    dropdown.classList.add('hidden');
    button.classList.remove('active');
  }

  toggleAdvancedMode() {
    this.advancedMode = !this.advancedMode;
    
    const jsonTab = document.getElementById('jsonTab');
    const toggleIndicator = document.getElementById('advancedToggle');
    const jsonOutput = document.getElementById('jsonOutput');
    const loadFromJsonBtn = document.getElementById('loadFromJson');
    const formatJsonBtn = document.getElementById('formatJson');
    
    if (this.advancedMode) {
      jsonTab.classList.remove('hidden');
      toggleIndicator.textContent = 'ON';
      toggleIndicator.classList.add('on');
      
      // Enable JSON editing
      jsonOutput.readOnly = false;
      jsonOutput.placeholder = 'Edit JSON directly here. Changes will be applied when you click "Load from JSON".';
      loadFromJsonBtn.style.display = 'inline-flex';
      formatJsonBtn.style.display = 'inline-flex';
      
      this.updateJsonStatus('editing', 'Editing enabled');
    } else {
      jsonTab.classList.add('hidden');
      toggleIndicator.textContent = 'OFF';
      toggleIndicator.classList.remove('on');
      
      // Disable JSON editing
      jsonOutput.readOnly = true;
      jsonOutput.placeholder = 'JSON output will appear here. Enable Advanced mode to edit.';
      loadFromJsonBtn.style.display = 'none';
      formatJsonBtn.style.display = 'none';
      
      this.updateJsonStatus('', '');
      
      // If JSON tab is currently active, switch to builder tab
      if (jsonTab.classList.contains('active')) {
        this.showView('builder');
      }
    }
  }

  updateJsonStatus(type, message) {
    const status = document.getElementById('jsonStatus');
    status.className = `json-status ${type}`;
    status.textContent = message;
  }

  validateJson() {
    if (!this.advancedMode) return;
    
    const jsonOutput = document.getElementById('jsonOutput');
    const jsonText = jsonOutput.value.trim();
    
    if (!jsonText) {
      this.updateJsonStatus('editing', 'Editing enabled');
      return;
    }
    
    try {
      JSON.parse(jsonText);
      this.updateJsonStatus('valid', 'Valid JSON');
    } catch (error) {
      this.updateJsonStatus('invalid', `Invalid JSON: ${error.message}`);
    }
  }

  formatJson() {
    if (!this.advancedMode) return;
    
    const jsonOutput = document.getElementById('jsonOutput');
    const jsonText = jsonOutput.value.trim();
    
    if (!jsonText) {
      alert('No JSON content to format');
      return;
    }
    
    try {
      const parsed = JSON.parse(jsonText);
      jsonOutput.value = JSON.stringify(parsed, null, 2);
      this.updateJsonStatus('valid', 'Formatted and valid');
    } catch (error) {
      alert(`Cannot format invalid JSON: ${error.message}`);
      this.updateJsonStatus('invalid', `Invalid JSON: ${error.message}`);
    }
  }

  loadFromJson() {
    if (!this.advancedMode) return;
    
    const jsonOutput = document.getElementById('jsonOutput');
    const jsonText = jsonOutput.value.trim();
    
    if (!jsonText) {
      alert('No JSON content to load');
      return;
    }
    
    try {
      const pathwayData = JSON.parse(jsonText);
      
      // Validate required fields
      if (!pathwayData.id || !pathwayData.title) {
        throw new Error('Pathway must have id and title fields');
      }
      
      if (!pathwayData.steps || typeof pathwayData.steps !== 'object') {
        throw new Error('Pathway must have a steps object');
      }
      
      // Load the pathway data
      this.currentTree = {
        id: pathwayData.id || '',
        title: pathwayData.title || '',
        description: pathwayData.description || '',
        startStep: pathwayData.startStep || '',
        guides: pathwayData.guides || [],
        steps: pathwayData.steps || {}
      };
      
      // Update all UI elements
      this.updateUI();
      this.updateJSON();
      this.updatePreview();
      
      // Switch to builder view to see the loaded pathway
      this.showView('builder');
      
      this.updateJsonStatus('valid', 'Pathway loaded successfully!');
      
      // Show success message
      alert('Pathway loaded successfully from JSON!');
      
    } catch (error) {
      this.updateJsonStatus('invalid', `Load failed: ${error.message}`);
      alert(`Failed to load pathway: ${error.message}`);
    }
  }

  showStepHoverModal(step, event) {
    // Create or get the hover modal
    let hoverModal = document.getElementById('stepHoverModal');
    if (!hoverModal) {
      hoverModal = this.createStepHoverModal();
      document.body.appendChild(hoverModal);
    }

    // Clear previous content
    const modalContent = hoverModal.querySelector('.hover-modal-content');
    modalContent.innerHTML = '';

    // Create scaled-down step card
    const stepCard = this.createMiniStepCard(step);
    modalContent.appendChild(stepCard);

    // Position modal near cursor
    const rect = event.target.getBoundingClientRect();
    hoverModal.style.left = (rect.right + 10) + 'px';
    hoverModal.style.top = (rect.top) + 'px';

    // Show modal
    hoverModal.classList.remove('hidden');
  }

  showOptionHoverModal(optionData, event) {
    // Create or get the hover modal
    let hoverModal = document.getElementById('stepHoverModal');
    if (!hoverModal) {
      hoverModal = this.createStepHoverModal();
      document.body.appendChild(hoverModal);
    }

    // Clear previous content
    const modalContent = hoverModal.querySelector('.hover-modal-content');
    modalContent.innerHTML = '';

    // Create option preview
    const optionCard = this.createMiniOptionCard(optionData);
    modalContent.appendChild(optionCard);

    // Position modal near cursor
    const rect = event.target.getBoundingClientRect();
    hoverModal.style.left = (rect.right + 10) + 'px';
    hoverModal.style.top = (rect.top) + 'px';

    // Show modal
    hoverModal.classList.remove('hidden');
  }

  hideStepHoverModal() {
    const hoverModal = document.getElementById('stepHoverModal');
    if (hoverModal) {
      hoverModal.classList.add('hidden');
    }
  }

  createStepHoverModal() {
    const modal = document.createElement('div');
    modal.id = 'stepHoverModal';
    modal.className = 'hover-modal hidden';
    modal.innerHTML = `
      <div class="hover-modal-content"></div>
    `;
    return modal;
  }

  createMiniStepCard(step) {
    const card = document.createElement('div');
    card.className = `mini-step-card mini-step-card-${step.type || 'choice'}`;
    
    // Title
    const title = document.createElement('h4');
    title.className = 'mini-step-title';
    title.textContent = step.title || step.id;
    card.appendChild(title);
    
    // Description (if exists)
    if (step.question) {
      const description = document.createElement('div');
      description.className = 'mini-step-description';
      description.innerHTML = this.parseCallouts(step.question);
      card.appendChild(description);
    }
    
    // Guide info (if exists)
    if (step.guideInfo) {
      const guideInfo = document.createElement('div');
      guideInfo.className = 'mini-guide-info';
      
      const guideTitle = document.createElement('h5');
      guideTitle.textContent = step.guideInfo.title;
      guideInfo.appendChild(guideTitle);
      
      const guideDesc = document.createElement('p');
      guideDesc.textContent = step.guideInfo.description;
      guideInfo.appendChild(guideDesc);
      
      if (step.guideInfo.note) {
        const note = document.createElement('div');
        note.className = 'mini-guide-note';
        note.innerHTML = `<strong>Note:</strong> ${step.guideInfo.note}`;
        guideInfo.appendChild(note);
      }
      
      card.appendChild(guideInfo);
    }
    
    // Options (if exists)
    if (step.options && step.options.length > 0) {
      const optionsTitle = document.createElement('h5');
      optionsTitle.className = 'mini-options-title';
      optionsTitle.textContent = 'Options:';
      card.appendChild(optionsTitle);
      
      const optionsList = document.createElement('ul');
      optionsList.className = 'mini-options-list';
      
      step.options.forEach(option => {
        const optionItem = document.createElement('li');
        optionItem.className = `mini-option-item variant-${option.variant || 'primary'}`;
        optionItem.textContent = option.text;
        optionsList.appendChild(optionItem);
      });
      
      card.appendChild(optionsList);
    }
    
    // Recommendation (if endpoint)
    if (step.type === 'endpoint' && step.recommendation) {
      const rec = step.recommendation;
      const recCard = document.createElement('div');
      recCard.className = 'mini-recommendation-card';
      
      const recTitle = document.createElement('h5');
      recTitle.textContent = 'Recommendation';
      recCard.appendChild(recTitle);
      
      
      if (rec.notes) {
        const notes = document.createElement('div');
        notes.innerHTML = `<strong>Notes:</strong> ${rec.notes}`;
        recCard.appendChild(notes);
      }
      
      card.appendChild(recCard);
    }
    
    return card;
  }

  createMiniOptionCard(optionData) {
    const card = document.createElement('div');
    card.className = `mini-option-card variant-${optionData.variant || 'primary'}`;
    
    const text = document.createElement('div');
    text.className = 'mini-option-text';
    text.textContent = optionData.text;
    card.appendChild(text);
    
    const action = document.createElement('div');
    action.className = 'mini-option-action';
    if (optionData.action.type === 'navigate') {
      action.textContent = `→ ${optionData.action.nextStep}`;
    } else if (optionData.action.type === 'recommend') {
      action.textContent = '→ Recommendation';
    }
    card.appendChild(action);
    
    return card;
  }

  parseCallouts(text) {
    if (!text) return '';
    
    // Parse callout syntax: [type]content[/type]
    const calloutRegex = /\[(guide|info|warning|success|danger)\](.*?)\[\/\1\]/g;
    
    return text.replace(calloutRegex, (match, type, content) => {
      return `<div class="mini-step-callout mini-step-callout-${type}">${content.trim()}</div>`;
    });
  }

  updatePreview() {
    const previewContent = document.getElementById('previewContent');
    
    console.log('Updating preview with tree:', this.currentTree);
    
    if (!this.currentTree.title) {
      previewContent.innerHTML = '<p>Add a title to your decision tree to get started.</p>';
      return;
    }
    
    if (!this.currentTree.startStep || !this.currentTree.steps[this.currentTree.startStep]) {
      previewContent.innerHTML = '<p>Add steps and set a start step to preview the decision tree.</p>';
      console.log('Missing start step or start step not found:', this.currentTree.startStep, this.currentTree.steps);
      return;
    }

    // Initialize renderer with current tree
    if (window.DecisionTreeRenderer) {
      try {
        console.log('Creating renderer with tree data:', this.currentTree);
        const renderer = new DecisionTreeRenderer(this.currentTree);
        previewContent.innerHTML = '';
        const rendered = renderer.render();
        console.log('Rendered element:', rendered);
        previewContent.appendChild(rendered);
      } catch (error) {
        previewContent.innerHTML = '<p>Error rendering preview: ' + error.message + '</p>';
        console.error('Preview error:', error);
      }
    } else {
      previewContent.innerHTML = '<p>Renderer not loaded. Please check renderer.js.</p>';
    }
  }

  updateJSON() {
    const jsonOutput = document.getElementById('jsonOutput');
    jsonOutput.value = JSON.stringify(this.currentTree, null, 2);
  }

  exportJSON() {
    const dataStr = JSON.stringify(this.currentTree, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `${this.currentTree.id || 'decision-tree'}.json`;
    link.click();
  }

  async saveDraft() {
    try {
      // Validate the pathway has required fields
      if (!this.currentTree.title || !this.currentTree.id) {
        alert('Please provide a title and ID for the pathway before saving.');
        return;
      }

      // Prepare the pathway data
      const pathwayData = {
        ...this.currentTree,
        status: 'draft'
      };

      // Try API first
      if (await window.pathwayAPI.isAPIAvailable()) {
        console.log('Saving pathway via API');
        const result = await window.pathwayAPI.savePathway(pathwayData);
        console.log('Pathway saved:', result);
        
        // Refresh the library
        await this.loadPathways();
        
        // Reset change tracking
        this.captureInitialTreeState();
        
        alert('Draft saved successfully!');
      } else {
        // Fallback to file-based system
        console.log('API not available, falling back to file download');
        
        // Create filename with draft suffix
        const filename = `${this.currentTree.id}_draft.json`;
        
        // Download the draft file
        const dataStr = JSON.stringify(pathwayData, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = filename;
        link.click();

        // Update/add to manifest
        await this.updateManifestEntry(filename, 'draft');
        
        // Reset change tracking
        this.captureInitialTreeState();
        
        alert('Draft saved successfully! File downloaded. Please place it in the pathways/ directory.');
      }
      
    } catch (error) {
      console.error('Error saving draft:', error);
      alert(`Error saving draft: ${error.message}`);
    }
  }

  async publishPathway() {
    try {
      // Validate the pathway is complete
      const validation = this.validatePathway();
      if (!validation.isValid) {
        alert('Cannot publish pathway:\n' + validation.errors.join('\n'));
        return;
      }

      // Confirm publication
      const confirmed = confirm(
        `Are you sure you want to publish "${this.currentTree.title}"?\n\n` +
        'This will save the pathway to the pathways directory and update the manifest.'
      );
      
      if (!confirmed) return;

      // Add publication metadata
      const publishData = {
        ...this.currentTree,
        metadata: {
          publishedAt: new Date().toISOString(),
          version: '1.0',
          status: 'published'
        }
      };

      const filename = `${this.currentTree.id || 'pathway'}.json`;
      
      try {
        // Save the pathway file
        await this.savePathwayFile(filename, publishData);
        
        // Regenerate the manifest
        await this.regenerateManifest();
        
        alert(
          `Pathway "${this.currentTree.title}" published successfully!\n\n` +
          `Saved as: ${filename}\n` +
          'Manifest updated automatically.'
        );
        
        // Auto-refresh the library to show updated pathways
        await this.loadPathways();
        
      } catch (saveError) {
        console.error('Error saving pathway:', saveError);
        
        // Fallback to download if save fails
        console.log('Falling back to download method...');
        const dataStr = JSON.stringify(publishData, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = filename;
        link.click();
        
        alert(
          `Unable to save directly to server.\n\n` +
          `File downloaded as: ${filename}\n\n` +
          'Please manually copy this file to the pathways/ directory and run:\n' +
          'node generate-manifest.js'
        );
      }
      
    } catch (error) {
      console.error('Error publishing pathway:', error);
      alert('Error publishing pathway: ' + error.message);
    }
  }

  async savePathwayFile(filename, data) {
    // Try to save the file using the publish endpoint
    const response = await fetch(`http://localhost:3001/pathways/${filename}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data, null, 2)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`Failed to save pathway: ${response.status} ${response.statusText} - ${errorData.error || ''}`);
    }

    return await response.json();
  }

  async regenerateManifest() {
    // Try to trigger manifest regeneration via the publish endpoint
    const response = await fetch('http://localhost:3001/regenerate-manifest', {
      method: 'POST'
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`Failed to regenerate manifest: ${response.status} ${response.statusText} - ${errorData.error || ''}`);
    }

    return await response.json();
  }

  validatePathway() {
    const errors = [];
    
    // Check required fields
    if (!this.currentTree.title) errors.push('- Title is required');
    if (!this.currentTree.id) errors.push('- ID is required');
    if (!this.currentTree.startStep) errors.push('- Start step must be specified');
    
    // Check that start step exists
    if (this.currentTree.startStep && !this.currentTree.steps[this.currentTree.startStep]) {
      errors.push('- Start step does not exist in steps');
    }
    
    // Check that all steps have required fields
    Object.entries(this.currentTree.steps || {}).forEach(([stepId, step]) => {
      if (!step.title) errors.push(`- Step "${stepId}" missing title`);
      if (!step.type) errors.push(`- Step "${stepId}" missing type`);
      
      // Check that navigation targets exist
      if (step.options) {
        step.options.forEach((option, index) => {
          if (option.action?.type === 'navigate' && option.action.nextStep) {
            if (!this.currentTree.steps[option.action.nextStep]) {
              errors.push(`- Step "${stepId}" option ${index + 1} references non-existent step "${option.action.nextStep}"`);
            }
          }
        });
      }
    });
    
    // Check for orphaned steps (unreachable from start)
    const reachableSteps = new Set();
    const visitStep = (stepId) => {
      if (reachableSteps.has(stepId)) return;
      reachableSteps.add(stepId);
      
      const step = this.currentTree.steps[stepId];
      if (step?.options) {
        step.options.forEach(option => {
          if (option.action?.type === 'navigate' && option.action.nextStep) {
            visitStep(option.action.nextStep);
          }
        });
      }
    };
    
    if (this.currentTree.startStep) {
      visitStep(this.currentTree.startStep);
    }
    
    Object.keys(this.currentTree.steps || {}).forEach(stepId => {
      if (!reachableSteps.has(stepId)) {
        errors.push(`- Step "${stepId}" is not reachable from the start step`);
      }
    });
    
    // Check for circular references
    Object.keys(this.currentTree.steps || {}).forEach(stepId => {
      const step = this.currentTree.steps[stepId];
      if (step?.options) {
        step.options.forEach((option, index) => {
          if (option.action?.type === 'navigate' && option.action.nextStep) {
            if (this.detectCircularReference(stepId, option.action.nextStep)) {
              errors.push(`- Step "${stepId}" option ${index + 1} creates a circular reference (infinite loop)`);
            }
          }
        });
      }
    });
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }

  importJSON() {
    document.getElementById('jsonFileInput').click();
  }

  handleFileImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const importedTree = JSON.parse(e.target.result);
        this.currentTree = importedTree;
        this.updateUI();
        this.updatePreview();
      } catch (error) {
        alert('Error importing file: ' + error.message);
      }
    };
    reader.readAsText(file);
  }

  loadExample() {
    // Load the demo from examples/demo.json
    const exampleTree = {
      "id": "liver-imaging-decision-tool",
      "title": "HNZ Liver Imaging Decision Support Tool",
      "description": "Interactive guide for selecting appropriate imaging modality and contrast",
      "startStep": "start",
      "guides": [
        {
          "id": "protocol-guide",
          "title": "Protocol Reference Guide",
          "sections": [
            {
              "title": "Pancreatic Protocol CT",
              "content": "Early arterial phase upper abdomen + portal venous phase abdomen and pelvis",
              "type": "protocol"
            },
            {
              "title": "TYPE OF MRI CONTRAST",
              "content": "Selection guidelines for MRI contrast agents",
              "type": "info",
              "items": [
                "Primovist: If there is evidence of malignancy on prior imaging",
                "Primovist: Solid/complex liver lesion",
                "Primovist: Gallbladder lesions ?malignancy",
                "Primovist: Pancreatic malignancy including high risk or large/enlarging IPMNs",
                "Dotarem or Gadovist: Question of haemangioma with no other malignancy",
                "Dotarem or Gadovist: Routine low risk IPMN follow up"
              ]
            }
          ]
        }
      ],
      "steps": {
        "start": {
          "id": "start",
          "title": "Patient Presentation",
          "question": "What is the primary clinical scenario?",
          "type": "choice",
          "options": [
            {
              "text": "Cirrhosis or risk factors for cirrhosis and no other malignancy suspected. Outside CT or US showing liver lesion",
              "variant": "primary",
              "action": {
                "type": "navigate",
                "nextStep": "endpoint-mri-liver-gadovist"
              }
            },
            {
              "text": "Patients less than 40 years old",
              "variant": "primary",
              "action": {
                "type": "navigate",
                "nextStep": "under-40-branch"
              }
            },
            {
              "text": "Patients greater than 40 years old",
              "variant": "primary",
              "action": {
                "type": "navigate",
                "nextStep": "over-40-branch"
              }
            }
          ]
        },
        "under-40-branch": {
          "id": "under-40-branch",
          "title": "Patients Less Than 40 Years Old",
          "question": "What was found on initial imaging?",
          "type": "choice",
          "options": [
            {
              "text": "Incidentally detected liver lesions on ultrasound",
              "variant": "primary",
              "action": {
                "type": "navigate",
                "nextStep": "under-40-ct-pancreas"
              }
            },
            {
              "text": "Symptoms or abnormal LFTs and ultrasound/CT confirms gallstones",
              "variant": "primary",
              "action": {
                "type": "navigate",
                "nextStep": "under-40-symptoms-decision"
              }
            }
          ]
        },
        "under-40-ct-pancreas": {
          "id": "under-40-ct-pancreas",
          "title": "CT Pancreatic Mass Protocol",
          "question": "Has the CT already been completed?",
          "type": "yes-no",
          "guideInfo": {
            "title": "CT Pancreatic Mass Protocol",
            "description": "Early arterial phase upper abdomen + portal venous phase abdomen and pelvis",
            "note": "MRI preferred, but CT undertaken first due to MRI resource constraints"
          },
          "options": [
            {
              "text": "Yes",
              "variant": "success",
              "action": {
                "type": "navigate",
                "nextStep": "under-40-characterization"
              }
            },
            {
              "text": "No",
              "variant": "warning",
              "action": {
                "type": "navigate",
                "nextStep": "endpoint-ct-pancreatic-protocol"
              }
            }
          ]
        },
        "under-40-characterization": {
          "id": "under-40-characterization",
          "title": "Pancreatic CT Completed",
          "question": "Is further characterisation or assessment required?",
          "type": "yes-no",
          "options": [
            {
              "text": "Yes",
              "variant": "success",
              "action": {
                "type": "navigate",
                "nextStep": "endpoint-mrcp-mri-gadolinium"
              }
            }
          ]
        },
        "under-40-symptoms-decision": {
          "id": "under-40-symptoms-decision",
          "title": "Patient < 40 symptoms or proven gallstones",
          "question": "?CBD stone is the only question",
          "type": "yes-no",
          "options": [
            {
              "text": "Yes",
              "variant": "success",
              "action": {
                "type": "navigate",
                "nextStep": "endpoint-mrcp-no-ct"
              }
            },
            {
              "text": "No",
              "variant": "warning",
              "action": {
                "type": "navigate",
                "nextStep": "under-40-ct-check"
              }
            }
          ]
        },
        "under-40-ct-check": {
          "id": "under-40-ct-check",
          "title": "CT Pancreatic Mass Protocol",
          "question": "Has the CT already been completed and there is still diagnostic uncertainty?",
          "type": "yes-no",
          "guideInfo": {
            "title": "CT Pancreatic Mass Protocol",
            "description": "Early arterial phase upper abdomen + portal venous phase abdomen and pelvis"
          },
          "options": [
            {
              "text": "Yes",
              "variant": "success",
              "action": {
                "type": "navigate",
                "nextStep": "endpoint-mrcp-mri-gadolinium"
              }
            }
          ]
        },
        "over-40-branch": {
          "id": "over-40-branch",
          "title": "Patients Greater Than 40 Years Old",
          "question": "What clinical scenario applies?",
          "type": "choice",
          "options": [
            {
              "text": "Incidentally detected new/concerning liver lesions on ultrasound",
              "variant": "primary",
              "action": {
                "type": "navigate",
                "nextStep": "over-40-ct-pancreas"
              }
            },
            {
              "text": "Abdominal ultrasound for abnormal LFTs. Question is ?gallstone or pancreaticobiliary pathology",
              "variant": "primary",
              "action": {
                "type": "navigate",
                "nextStep": "over-40-ct-pancreas"
              }
            }
          ]
        },
        "over-40-ct-pancreas": {
          "id": "over-40-ct-pancreas",
          "title": "CT Pancreatic Mass Protocol",
          "question": "Has the CT already been completed?",
          "type": "yes-no",
          "guideInfo": {
            "title": "CT Pancreatic Mass Protocol",
            "description": "Early arterial phase upper abdomen + portal venous phase abdomen and pelvis"
          },
          "options": [
            {
              "text": "Yes",
              "variant": "success",
              "action": {
                "type": "navigate",
                "nextStep": "over-40-characterization"
              }
            },
            {
              "text": "No",
              "variant": "warning",
              "action": {
                "type": "navigate",
                "nextStep": "endpoint-ct-pancreatic-protocol"
              }
            }
          ]
        },
        "over-40-characterization": {
          "id": "over-40-characterization",
          "title": "Pancreatic CT Completed",
          "question": "Is further characterisation or assessment required?",
          "type": "yes-no",
          "options": [
            {
              "text": "Yes",
              "variant": "success",
              "action": {
                "type": "navigate",
                "nextStep": "endpoint-mrcp-mri-gadolinium"
              }
            }
          ]
        },
        "endpoint-mri-liver-gadovist": {
          "id": "endpoint-mri-liver-gadovist",
          "title": "MRI liver Recommendation",
          "type": "endpoint",
          "recommendation": {
            "modality": "MRI liver",
            "contrast": "with Gadovist (in line with Auckland unless specified by MDM)",
            "notes": "Direct pathway for cirrhosis/risk factors with no other malignancy suspected"
          }
        },
        "endpoint-ct-pancreatic-protocol": {
          "id": "endpoint-ct-pancreatic-protocol",
          "title": "CT Pancreatic Mass Protocol Recommendation",
          "type": "endpoint",
          "recommendation": {
            "modality": "CT Pancreatic Mass Protocol",
            "contrast": "Early arterial phase upper abdomen + portal venous phase abdomen and pelvis"
          }
        },
        "endpoint-mrcp-mri-gadolinium": {
          "id": "endpoint-mrcp-mri-gadolinium",
          "title": "MRCP/MRI liver/pancreas Recommendation",
          "type": "endpoint",
          "recommendation": {
            "modality": "MRCP/MRI liver/pancreas",
            "contrast": "with Gadolinium (see protocol reference for contrast selection)"
          }
        },
        "endpoint-mrcp-no-ct": {
          "id": "endpoint-mrcp-no-ct",
          "title": "MRCP Recommendation",
          "type": "endpoint",
          "recommendation": {
            "modality": "MRCP",
            "contrast": "(CT not required)"
          }
        }
      }
    };
    
    this.currentTree = exampleTree;
    this.updateUI();
    this.updatePreview();
  }

  // Public methods for button onclick handlers
  removeGuideAtIndex(index) {
    if (confirm('Are you sure you want to remove this guide?')) {
      this.currentTree.guides.splice(index, 1);
      this.updateGuidesList();
      this.updateJSON();
      this.updatePreview();
    }
  }

  editOptionAtIndex(index) {
    this.currentEditingOption = index;
    
    const step = this.currentTree.steps[this.currentEditingStep];
    const option = step.options[index];
    
    // Populate the option modal
    document.getElementById('optionText').value = option.text || '';
    document.getElementById('optionVariant').value = option.variant || 'primary';
    document.getElementById('optionAction').value = option.action.type || 'navigate';
    
    // Update the action-specific UI
    this.updateOptionActionUI(option.action.type);
    
    if (option.action.type === 'navigate') {
      this.populateTargetSteps();
      document.getElementById('targetStep').value = option.action.nextStep || '';
      this.updateTargetStepUI(option.action.nextStep || '');
    } else if (option.action.type === 'recommend') {
      this.populateExistingEndpoints();
      if (option.action.recommendation) {
        document.getElementById('recRecommendation').value = option.action.recommendation.recommendation || '';
        document.getElementById('recNotes').value = option.action.recommendation.notes || '';
      }
    }
    
    this.showOptionModal();
  }

  removeOptionAtIndex(index) {
    if (!this.currentEditingStep) return;
    
    const step = this.currentTree.steps[this.currentEditingStep];
    
    // Prevent removal of options from yes-no steps
    if (step.type === 'yes-no') {
      alert('Cannot remove options from Yes/No steps. Yes and No options are required.');
      return;
    }
    
    step.options.splice(index, 1);
    this.updateOptionsList(step.options);
    this.updateJSON();
  }

  showOptionModal() {
    document.getElementById('optionModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  closeOptionModal() {
    document.getElementById('optionModal').classList.add('hidden');
    document.body.style.overflow = 'auto';
    this.currentEditingOption = null;
  }

  updateOptionActionUI(actionType) {
    const navigationSection = document.getElementById('navigationSection');
    const recommendationSection = document.getElementById('recommendationSection');

    if (actionType === 'navigate') {
      navigationSection.classList.remove('hidden');
      recommendationSection.classList.add('hidden');
      this.populateTargetSteps();
    } else if (actionType === 'recommend') {
      navigationSection.classList.add('hidden');
      recommendationSection.classList.remove('hidden');
      this.populateExistingEndpoints();
    }
  }

  populateTargetSteps() {
    const select = document.getElementById('targetStep');
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">Select existing step...</option>';
    select.innerHTML += '<option value="__NEW__">+ Create New Step</option>';
    
    Object.values(this.currentTree.steps).forEach(step => {
      if (step.id !== this.currentEditingStep) { // Don't allow self-reference
        const option = document.createElement('option');
        option.value = step.id;
        const stepTypeText = step.type.replace('-', ' ').toUpperCase();
        option.textContent = `[${stepTypeText}] ${step.title || 'Untitled'} (${step.id})`;
        select.appendChild(option);
      }
    });
    
    select.value = currentValue;
  }

  populateExistingEndpoints() {
    const select = document.getElementById('existingEndpoint');
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">Create new recommendation...</option>';
    select.innerHTML += '<option value="__NEW__">+ Create New Endpoint Step</option>';
    
    // Find existing endpoint steps
    Object.values(this.currentTree.steps).forEach(step => {
      if (step.type === 'endpoint') {
        const option = document.createElement('option');
        option.value = step.id;
        option.textContent = `${step.title || 'Untitled'} (${step.id})`;
        select.appendChild(option);
      }
    });
    
    select.value = currentValue;
  }

  updateTargetStepUI(value) {
    const newStepSection = document.getElementById('newStepSection');
    
    if (value === '__NEW__') {
      newStepSection.classList.remove('hidden');
      // Generate a suggested ID
      const timestamp = Date.now();
      document.getElementById('newStepId').value = `step-${timestamp}`;
    } else {
      newStepSection.classList.add('hidden');
    }
  }

  updateEndpointUI(value) {
    const newEndpointSection = document.getElementById('newEndpointSection');
    const recommendationDetails = document.getElementById('recommendationDetails');
    
    if (value === '__NEW__') {
      newEndpointSection.classList.remove('hidden');
      recommendationDetails.classList.remove('hidden');
      // Generate a suggested ID
      const timestamp = Date.now();
      document.getElementById('newEndpointId').value = `endpoint-${timestamp}`;
    } else if (value === '') {
      newEndpointSection.classList.add('hidden');
      recommendationDetails.classList.remove('hidden');
    } else {
      // Existing endpoint selected
      newEndpointSection.classList.add('hidden');
      recommendationDetails.classList.add('hidden');
    }
  }

  saveOption() {
    if (!this.currentEditingStep || this.currentEditingOption === null) return;

    const step = this.currentTree.steps[this.currentEditingStep];
    const option = step.options[this.currentEditingOption];

    // Basic option properties
    option.text = document.getElementById('optionText').value;
    option.variant = document.getElementById('optionVariant').value;
    
    const actionType = document.getElementById('optionAction').value;
    
    if (actionType === 'navigate') {
      const targetStep = document.getElementById('targetStep').value;
      
      if (targetStep === '__NEW__') {
        // Create new step
        const newStepId = document.getElementById('newStepId').value;
        const newStepTitle = document.getElementById('newStepTitle').value;
        const newStepType = document.getElementById('newStepType').value;
        
        if (!newStepId || !newStepTitle) {
          alert('Please provide both ID and title for the new step.');
          return;
        }
        
        if (this.currentTree.steps[newStepId]) {
          alert('A step with this ID already exists. Please choose a different ID.');
          return;
        }
        
        // Create the new step
        const newStep = {
          id: newStepId,
          title: newStepTitle,
          type: newStepType,
          options: newStepType === 'endpoint' ? undefined : []
        };
        
        if (newStepType === 'endpoint') {
          newStep.recommendation = {
            modality: '',
            contrast: ''
          };
        }
        
        // Check for circular reference with new step
        if (this.detectCircularReference(this.currentEditingStep, newStepId)) {
          alert('This action would create a circular reference (infinite loop) in your pathway. Please choose a different target or create a different step structure.');
          return;
        }
        
        this.currentTree.steps[newStepId] = newStep;
        
        option.action = {
          type: 'navigate',
          nextStep: newStepId
        };
      } else {
        // Check for circular reference with existing step
        if (this.detectCircularReference(this.currentEditingStep, targetStep)) {
          alert('This action would create a circular reference (infinite loop) in your pathway. Please choose a different target step.');
          return;
        }
        
        option.action = {
          type: 'navigate',
          nextStep: targetStep
        };
      }
    } else if (actionType === 'recommend') {
      const existingEndpoint = document.getElementById('existingEndpoint').value;
      
      if (existingEndpoint === '__NEW__') {
        // Create new endpoint step
        const newEndpointId = document.getElementById('newEndpointId').value;
        const newEndpointTitle = document.getElementById('newEndpointTitle').value;
        
        if (!newEndpointId || !newEndpointTitle) {
          alert('Please provide both ID and title for the new endpoint.');
          return;
        }
        
        if (this.currentTree.steps[newEndpointId]) {
          alert('A step with this ID already exists. Please choose a different ID.');
          return;
        }
        
        // Create the new endpoint step
        const recommendation = {
          recommendation: document.getElementById('recRecommendation').value,
          notes: document.getElementById('recNotes').value
        };
        
        const newEndpointStep = {
          id: newEndpointId,
          title: newEndpointTitle,
          type: 'endpoint',
          recommendation: recommendation
        };
        
        this.currentTree.steps[newEndpointId] = newEndpointStep;
        
        option.action = {
          type: 'navigate',
          nextStep: newEndpointId
        };
      } else if (existingEndpoint) {
        // Use existing endpoint
        option.action = {
          type: 'navigate',
          nextStep: existingEndpoint
        };
      } else {
        // Create new endpoint step for inline recommendation - make every recommendation reusable
        const timestamp = Date.now();
        const newEndpointId = `endpoint-${timestamp}`;
        const recommendationText = document.getElementById('recRecommendation').value || 'Recommendation';
        
        // Create the new endpoint step
        const recommendation = {
          recommendation: document.getElementById('recRecommendation').value,
          notes: document.getElementById('recNotes').value
        };
        
        const newEndpointStep = {
          id: newEndpointId,
          title: `${recommendationText} Recommendation`,
          type: 'endpoint',
          recommendation: recommendation
        };
        
        this.currentTree.steps[newEndpointId] = newEndpointStep;
        
        // Point to the new endpoint step
        option.action = {
          type: 'navigate',
          nextStep: newEndpointId
        };
      }
    }

    this.closeOptionModal();
    this.updateOptionsList(step.options);
    this.updateUI();
    this.updateJSON();
    this.updatePreview();
  }

  deleteOption() {
    if (!this.currentEditingStep || this.currentEditingOption === null) return;
    
    if (confirm('Are you sure you want to delete this option?')) {
      const step = this.currentTree.steps[this.currentEditingStep];
      step.options.splice(this.currentEditingOption, 1);
      this.closeOptionModal();
      this.updateOptionsList(step.options);
      this.updateJSON();
      this.updatePreview();
    }
  }

  // ==========================================================================
  // Circular Reference Detection
  // ==========================================================================

  detectCircularReference(fromStepId, toStepId) {
    // Special case: Allow navigation back to the start step (this is intentional pathway completion)
    if (toStepId === this.currentTree.startStep && fromStepId !== this.currentTree.startStep) {
      return false; // This is allowed - it's a "restart pathway" feature
    }

    // If we're linking to the same step, that's immediately circular
    if (fromStepId === toStepId) {
      return true;
    }

    // Use depth-first search to detect if toStepId can eventually lead back to fromStepId
    const visited = new Set();
    const stack = [toStepId];

    while (stack.length > 0) {
      const currentStepId = stack.pop();
      
      // If we've already visited this step, skip it to avoid infinite loops
      if (visited.has(currentStepId)) {
        continue;
      }
      
      visited.add(currentStepId);
      
      // If we've reached back to our starting step, we found a cycle
      if (currentStepId === fromStepId) {
        return true;
      }

      // Get the current step and examine its options
      const currentStep = this.currentTree.steps[currentStepId];
      if (!currentStep || !currentStep.options) {
        continue;
      }

      // Add all navigation targets to the stack for further exploration
      for (const option of currentStep.options) {
        if (option.action && option.action.type === 'navigate' && option.action.nextStep) {
          // Skip checking paths that go back to start step (these are allowed)
          if (option.action.nextStep !== this.currentTree.startStep) {
            stack.push(option.action.nextStep);
          }
        }
      }
    }

    return false; // No circular reference found
  }

  // ==========================================================================
  // Birdseye View / Flowchart Methods
  // ==========================================================================

  updateBirdseye() {
    if (!this.currentTree.title) {
      document.getElementById('flowchartSvg').innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#6B7280" font-family="sans-serif">Add a title to your decision tree to get started.</text>';
      return;
    }
    
    if (!this.currentTree.startStep || Object.keys(this.currentTree.steps).length === 0) {
      document.getElementById('flowchartSvg').innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#6B7280" font-family="sans-serif">Add steps to see the flowchart.</text>';
      return;
    }

    this.renderFlowchart();
  }

  renderFlowchart() {
    const svg = document.getElementById('flowchartSvg');
    
    // Clear existing content
    svg.innerHTML = '';
    
    // Set SVG viewBox to handle large content
    svg.setAttribute('viewBox', '0 0 2000 1000');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    
    
    // Create main content group for zoom/pan
    const contentGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    contentGroup.setAttribute('id', 'flowchartContent');
    contentGroup.setAttribute('transform', 'translate(0,0) scale(1)');
    svg.appendChild(contentGroup);
    
    // Calculate positions for nodes
    const positions = this.calculateNodePositions();
    const nodes = {};
    
    // Calculate SVG dimensions based on actual content
    let maxX = 0, maxY = 0;
    Object.values(positions).forEach(pos => {
      maxX = Math.max(maxX, pos.x + 250); // Account for node width + padding
      maxY = Math.max(maxY, pos.y + 120); // Account for node height + padding
    });
    
    // Set viewBox to fit actual content size (not a huge fixed minimum!)
    const viewBoxWidth = maxX + 100;  // Just add some padding
    const viewBoxHeight = maxY + 100;
    svg.setAttribute('viewBox', `0 0 ${viewBoxWidth} ${viewBoxHeight}`);
    
    // Create connections first (so they appear behind nodes)
    Object.entries(this.currentTree.steps).forEach(([stepId, step]) => {
      if (!step.options) return;
      
      step.options.forEach((option, optionIndex) => {
        const optionId = `option_${stepId}_${optionIndex}`;
        
        // Dotted connection from step to option node
        if (positions[stepId] && positions[optionId]) {
          const stepToOption = this.createConnection(
            positions[stepId], 
            positions[optionId], 
            '', // No label needed for step to option
            false,
            'step',
            'option',
            true // isDotted = true for step to option connections
          );
          contentGroup.appendChild(stepToOption);
        }
        
        // Solid connection from option node to target
        let targetStep = null;
        let isRecommendation = false;
        let targetNodeType = 'step';
        
        if (option.action.type === 'navigate' && option.action.nextStep) {
          targetStep = option.action.nextStep;
          targetNodeType = 'step';
        } else if (option.action.type === 'recommend') {
          targetStep = `endpoint_${stepId}_${optionIndex}`;
          isRecommendation = true;
          targetNodeType = 'endpoint';
        }
        
        if (targetStep && positions[optionId] && positions[targetStep]) {
          const optionToTarget = this.createConnection(
            positions[optionId], 
            positions[targetStep], 
            '', // No label needed since option node shows the text
            isRecommendation,
            'option',
            targetNodeType,
            false // isDotted = false for option to target connections (solid lines)
          );
          contentGroup.appendChild(optionToTarget);
        }
      });
    });
    
    // Create nodes (so they appear on top of connections)
    Object.entries(positions).forEach(([nodeId, pos]) => {
      let node = null;
      let nodeData = null;
      
      // Check what type of node this is
      if (this.currentTree.steps[nodeId]) {
        // Regular step
        nodeData = this.currentTree.steps[nodeId];
        node = this.createFlowchartNode(nodeData, pos.x, pos.y);
      } else if (this.virtualEndpoints && this.virtualEndpoints.has(nodeId)) {
        // Virtual endpoint
        nodeData = this.virtualEndpoints.get(nodeId);
        node = this.createFlowchartNode(nodeData, pos.x, pos.y);
      } else if (this.optionNodes && this.optionNodes.has(nodeId)) {
        // Option node
        nodeData = this.optionNodes.get(nodeId);
        node = this.createOptionNode(nodeData, pos.x, pos.y);
      }
      
      if (node && nodeData) {
        nodes[nodeId] = { element: node, step: nodeData, pos: pos };
        contentGroup.appendChild(node);
      }
    });
    
    // Add legend
    this.addFlowchartLegend();
    
    // Initialize zoom/pan without auto-fit
    this.initializeFlowchartInteraction();
  }

  calculateNodePositions() {
    const steps = this.currentTree.steps;
    const positions = {};
    const visited = new Set();
    const levels = {};
    const virtualEndpoints = new Map(); // Store virtual endpoint nodes
    const optionNodes = new Map(); // Store option nodes
    
    // Start with the start step
    const startStep = this.currentTree.startStep;
    if (!startStep || !steps[startStep]) return positions;
    
    // Calculate levels using BFS (left-to-right layout)
    const queue = [{id: startStep, level: 0}];
    const levelCounts = {};
    
    while (queue.length > 0) {
      const {id, level} = queue.shift();
      
      if (visited.has(id)) continue;
      visited.add(id);
      
      levels[id] = level;
      levelCounts[level] = (levelCounts[level] || 0) + 1;
      
      const step = steps[id];
      if (step && step.options) {
        step.options.forEach((option, optionIndex) => {
          // Create option node for each option
          const optionId = `option_${id}_${optionIndex}`;
          const optionLevel = level + 0.5; // Position option nodes between levels
          
          optionNodes.set(optionId, {
            id: optionId,
            type: 'option',
            text: option.text,
            variant: option.variant || 'primary',
            parentStep: id,
            isOptionNode: true,
            targetStep: option.action?.nextStep || null,
            actionType: option.action?.type || null
          });
          
          levels[optionId] = optionLevel;
          levelCounts[optionLevel] = (levelCounts[optionLevel] || 0) + 1;
          
          if (option.action.type === 'navigate' && option.action.nextStep) {
            const nextId = option.action.nextStep;
            if (!visited.has(nextId) && steps[nextId]) {
              queue.push({id: nextId, level: level + 1});
            }
          } else if (option.action.type === 'recommend' && option.action.recommendation) {
            // Create virtual endpoint node for recommendation
            const endpointId = `endpoint_${id}_${optionIndex}`;
            const endpointLevel = level + 1;
            
            if (!virtualEndpoints.has(endpointId)) {
              virtualEndpoints.set(endpointId, {
                id: endpointId,
                type: 'endpoint',
                title: option.action.recommendation.modality || 'Recommendation',
                recommendation: option.action.recommendation,
                isVirtual: true
              });
              
              levels[endpointId] = endpointLevel;
              levelCounts[endpointLevel] = (levelCounts[endpointLevel] || 0) + 1;
            }
          }
        });
      }
    }
    
    // Calculate positions for left-to-right layout with good spacing
    const nodeWidth = 220;   // Step node width
    const nodeHeight = 100;  // Step node height
    const levelWidth = 600;  // Expanded horizontal spacing between levels
    const nodeSpacing = 12;  // Tight vertical spacing for option nodes - almost touching
    const stepSpacing = 200; // Increased vertical spacing for step cards
    const startX = 80;       // Reasonable margin from left edge
    const startY = 80;
    
    // First, position all step nodes with increased spacing
    const stepsByLevel = {};
    Object.entries(levels).forEach(([nodeId, level]) => {
      if (this.currentTree.steps[nodeId]) {
        if (!stepsByLevel[level]) stepsByLevel[level] = [];
        stepsByLevel[level].push(nodeId);
      }
    });
    
    // First position guide steps near the start card
    const guideSteps = [];
    const nonGuideStepsByLevel = {};
    
    Object.entries(stepsByLevel).forEach(([level, stepIds]) => {
      nonGuideStepsByLevel[level] = [];
      stepIds.forEach(stepId => {
        const step = this.currentTree.steps[stepId];
        if (step && step.type === 'guide') {
          guideSteps.push(stepId);
        } else {
          nonGuideStepsByLevel[level].push(stepId);
        }
      });
    });
    
    // Position guide steps below the start card
    guideSteps.forEach((guideId, index) => {
      positions[guideId] = {
        x: startX, // Same x position as start card
        y: startY + (nodeHeight + stepSpacing) + index * (nodeHeight + stepSpacing) // Below start card
      };
    });
    
    // Position non-guide steps normally
    Object.entries(nonGuideStepsByLevel).forEach(([level, stepIds]) => {
      const levelNum = parseFloat(level);
      const baseX = startX + levelNum * levelWidth;
      
      stepIds.forEach((stepId, index) => {
        positions[stepId] = {
          x: baseX,
          y: startY + index * (nodeHeight + stepSpacing)
        };
      });
    });
    
    // Position option nodes grouped by their parent step and centered vertically
    Object.entries(this.currentTree.steps).forEach(([stepId, step]) => {
      if (step.options && positions[stepId]) {
        const parentPos = positions[stepId];
        const parentCenterY = parentPos.y + nodeHeight / 2;
        const optionLevel = levels[stepId] + 0.5;
        const optionX = startX + optionLevel * levelWidth;
        
        // Calculate total height needed for all options from this step
        const optionCount = step.options.length;
        const totalOptionHeight = (optionCount - 1) * (50 + nodeSpacing);
        const optionStartY = parentCenterY - totalOptionHeight / 2;
        
        step.options.forEach((option, optionIndex) => {
          const optionId = `option_${stepId}_${optionIndex}`;
          if (optionNodes.has(optionId)) {
            positions[optionId] = {
              x: optionX,
              y: optionStartY + optionIndex * (50 + nodeSpacing)
            };
          }
        });
      }
    });
    
    // Position virtual endpoints with step spacing
    const endpointsByLevel = {};
    virtualEndpoints.forEach((endpoint, endpointId) => {
      const level = levels[endpointId];
      if (!endpointsByLevel[level]) endpointsByLevel[level] = [];
      endpointsByLevel[level].push(endpointId);
    });
    
    Object.entries(endpointsByLevel).forEach(([level, endpointIds]) => {
      const levelNum = parseFloat(level);
      const baseX = startX + levelNum * levelWidth;
      
      endpointIds.forEach((endpointId, index) => {
        positions[endpointId] = {
          x: baseX,
          y: startY + index * (nodeHeight + stepSpacing)
        };
      });
    });
    
    // Store virtual endpoints and option nodes for later use
    this.virtualEndpoints = virtualEndpoints;
    this.optionNodes = optionNodes;
    
    return positions;
  }

  createFlowchartNode(step, x, y) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', `flow-node ${step.type}`);
    group.setAttribute('transform', `translate(${x},${y})`);
    
    // For virtual recommendation endpoints, create a detailed recommendation card
    if (step.isVirtual && step.recommendation) {
      return this.createRecommendationNode(step, x, y);
    }
    
    // Determine colors based on step type to match step card colors
    let fillColor = '#3B82F6'; // default blue for choice
    if (step.id === this.currentTree.startStep) {
      fillColor = '#8B5CF6'; // purple for start step
    } else if (step.type === 'endpoint') {
      fillColor = '#FB923C'; // orange for endpoints
    } else if (step.type === 'yes-no') {
      fillColor = '#10B981'; // green for yes/no
    } else if (step.type === 'guide') {
      fillColor = '#4338CA'; // indigo for guide
    } else if (step.type === 'choice') {
      fillColor = '#3B82F6'; // blue for multiple choice
    }
    
    // Create larger rectangle for full title display
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('class', 'flow-node-rect');
    rect.setAttribute('width', '220');
    rect.setAttribute('height', '100');
    rect.setAttribute('fill', fillColor);
    rect.setAttribute('rx', '8');
    rect.setAttribute('ry', '8');
    rect.setAttribute('stroke', '#fff');
    rect.setAttribute('stroke-width', '2');
    
    // Show only the title (not question or description)
    let displayText = step.title || step.id;
    
    // Create title text with dynamic sizing - centered in box
    const titleText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    titleText.setAttribute('class', 'flow-node-text flow-node-title');
    titleText.setAttribute('x', '110'); // Center of 220px width
    titleText.setAttribute('text-anchor', 'middle');
    titleText.setAttribute('dominant-baseline', 'central');
    titleText.setAttribute('font-size', '13');
    titleText.setAttribute('font-weight', '600');
    titleText.setAttribute('fill', 'white');
    
    // Split text into multiple lines for better readability
    const words = displayText.split(' ');
    const maxCharsPerLine = 25; // Increased for larger box
    const lines = [];
    let currentLine = '';
    
    for (const word of words) {
      if ((currentLine + word).length > maxCharsPerLine && currentLine) {
        lines.push(currentLine.trim());
        currentLine = word + ' ';
      } else {
        currentLine += word + ' ';
      }
    }
    if (currentLine) lines.push(currentLine.trim());
    
    // Limit to maximum 3 lines for cleaner appearance
    const maxLines = 3;
    const displayLines = lines.slice(0, maxLines);
    if (lines.length > maxLines) {
      displayLines[maxLines - 1] += '...';
    }
    
    // Position text based on number of lines - centered vertically
    const lineHeight = 16;
    const totalTextHeight = displayLines.length * lineHeight;
    const startY = 50 - (totalTextHeight / 2) + (lineHeight / 2); // Center vertically in 100px box
    
    displayLines.forEach((line, index) => {
      const lineText = index === 0 ? titleText : document.createElementNS('http://www.w3.org/2000/svg', 'text');
      if (index > 0) {
        lineText.setAttribute('class', 'flow-node-text flow-node-title');
        lineText.setAttribute('x', '110');
        lineText.setAttribute('text-anchor', 'middle');
        lineText.setAttribute('font-size', '13');
        lineText.setAttribute('font-weight', '600');
        lineText.setAttribute('fill', 'white');
      }
      lineText.setAttribute('y', startY + (index * lineHeight));
      lineText.textContent = line;
      if (index > 0) group.appendChild(lineText);
    });
    
    group.appendChild(rect);
    group.appendChild(titleText);
    
    // Add click handler to edit step
    group.addEventListener('click', () => {
      this.editStep(step.id);
    });
    group.style.cursor = 'pointer';
    
    // Add hover handlers for step preview modal
    group.addEventListener('mouseenter', (e) => {
      this.showStepHoverModal(step, e);
    });
    
    group.addEventListener('mouseleave', () => {
      this.hideStepHoverModal();
    });
    
    return group;
  }

  createRecommendationNode(step, x, y) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', 'flow-node endpoint recommendation');
    group.setAttribute('transform', `translate(${x},${y})`);
    
    const rec = step.recommendation;
    
    // Create larger rectangle for recommendation details
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('class', 'flow-node-rect');
    rect.setAttribute('width', '220');
    rect.setAttribute('height', '120');
    rect.setAttribute('fill', '#FB923C'); // orange for recommendations to match endpoint color
    rect.setAttribute('rx', '8');
    rect.setAttribute('ry', '8');
    rect.setAttribute('stroke', '#fff');
    rect.setAttribute('stroke-width', '2');
    
    // Title - "Recommendation"
    const titleText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    titleText.setAttribute('class', 'flow-node-text flow-node-title');
    titleText.setAttribute('x', '110');
    titleText.setAttribute('y', '20');
    titleText.setAttribute('font-size', '12');
    titleText.setAttribute('font-weight', '600');
    titleText.textContent = '󰄬 Recommendation';
    
    // Recommendation title
    const recTitleText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    recTitleText.setAttribute('class', 'flow-node-text');
    recTitleText.setAttribute('x', '110');
    recTitleText.setAttribute('y', '40');
    recTitleText.setAttribute('font-size', '11');
    recTitleText.setAttribute('font-weight', '600');
    recTitleText.textContent = step.title || rec.recommendation || 'Recommendation';
    
    // Action or description
    if (rec.action || rec.description) {
      const actionText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      actionText.setAttribute('class', 'flow-node-text');
      actionText.setAttribute('x', '110');
      actionText.setAttribute('y', '55');
      actionText.setAttribute('font-size', '10');
      actionText.textContent = rec.action || rec.notes || 'Clinical recommendation';
      group.appendChild(actionText);
    }
    
    // Priority
    if (rec.priority) {
      const priorityText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      priorityText.setAttribute('class', 'flow-node-text');
      priorityText.setAttribute('x', '110');
      priorityText.setAttribute('y', '70');
      priorityText.setAttribute('font-size', '10');
      priorityText.setAttribute('font-weight', '600');
      priorityText.textContent = `Priority: ${rec.priority}`;
      group.appendChild(priorityText);
    }
    
    // Notes (truncated)
    if (rec.notes) {
      const notesText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      notesText.setAttribute('class', 'flow-node-text');
      notesText.setAttribute('x', '110');
      notesText.setAttribute('y', '85');
      notesText.setAttribute('font-size', '9');
      const truncatedNotes = rec.notes.length > 25 ? rec.notes.substring(0, 25) + '...' : rec.notes;
      notesText.textContent = truncatedNotes;
      group.appendChild(notesText);
    }
    
    // Type indicator
    const typeText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    typeText.setAttribute('class', 'flow-node-text flow-node-type');
    typeText.setAttribute('x', '110');
    typeText.setAttribute('y', '105');
    typeText.setAttribute('font-size', '9');
    typeText.setAttribute('opacity', '0.8');
    typeText.textContent = 'endpoint';
    
    group.appendChild(rect);
    group.appendChild(titleText);
    group.appendChild(recTitleText);
    group.appendChild(typeText);
    
    // Add click handler to edit step
    group.addEventListener('click', () => {
      this.editStep(step.id);
    });
    group.style.cursor = 'pointer';
    
    // Add hover handlers for recommendation node preview
    group.addEventListener('mouseenter', (e) => {
      this.showStepHoverModal(step, e);
    });
    
    group.addEventListener('mouseleave', () => {
      this.hideStepHoverModal();
    });
    
    return group;
  }

  createOptionNode(optionData, x, y) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', 'flow-node option');
    group.setAttribute('transform', `translate(${x},${y})`);
    
    // Check if this option targets the start step
    const isBackToStart = optionData.targetStep === this.currentTree.startStep;
    
    // Determine color based on variant and target
    let fillColor = '#6B7280'; // grey for option buttons
    let strokeColor = '#2563EB';
    
    if (isBackToStart) {
      // Style as endpoint for back-to-start options
      fillColor = '#FB923C'; // orange like endpoints
      strokeColor = '#FB923C';
    } else {
      switch (optionData.variant) {
        case 'secondary':
          fillColor = '#6B7280';
          strokeColor = '#6B7280';
          break;
        case 'success':
          fillColor = '#6B7280';
          strokeColor = '#6B7280';
          break;
        case 'warning':
          fillColor = '#6B7280';
          strokeColor = '#6B7280';
          break;
        case 'danger':
          fillColor = '#EF4444';
          strokeColor = '#EF4444';
          break;
        default:
          fillColor = '#6B7280';
          strokeColor = '#6B7280';
      }
    }
    
    // Create smaller rectangle for option nodes
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('class', 'flow-option-rect');
    rect.setAttribute('width', '140');
    rect.setAttribute('height', '50');
    rect.setAttribute('fill', fillColor);
    
    // Use sharp corners for back-to-start options, rounded for others
    if (isBackToStart) {
      rect.setAttribute('rx', '0'); // Sharp rectangle for back-to-start
      rect.setAttribute('ry', '0');
    } else {
      rect.setAttribute('rx', '25'); // More rounded for button look
      rect.setAttribute('ry', '25');
    }
    
    rect.setAttribute('stroke', '#fff');
    rect.setAttribute('stroke-width', '2');
    
    // Create option text
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('class', 'flow-option-text');
    text.setAttribute('x', '70'); // Center of 140px width
    text.setAttribute('y', '25'); // Center of 50px height
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'central');
    text.setAttribute('font-size', '13');
    text.setAttribute('font-weight', '500');
    text.setAttribute('fill', 'white');
    
    // Truncate long option text
    const maxLength = 16;
    const displayText = optionData.text.length > maxLength 
      ? optionData.text.substring(0, maxLength - 3) + '...' 
      : optionData.text;
    text.textContent = displayText;
    
    group.appendChild(rect);
    group.appendChild(text);
    
    // Add hover handlers for option preview
    group.addEventListener('mouseenter', (e) => {
      this.showOptionHoverModal(optionData, e);
    });
    
    group.addEventListener('mouseleave', () => {
      this.hideStepHoverModal();
    });
    
    return group;
  }

  createConnection(fromPos, toPos, label, isRecommendation = false, fromNodeType = 'step', toNodeType = 'step', isDotted = false) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    
    // Calculate connection points based on node types
    let fromX, fromY, toX, toY;
    
    // From node calculations
    if (fromNodeType === 'option') {
      fromX = fromPos.x + 140; // Right edge of option node (140px wide)
      fromY = fromPos.y + 25;  // Middle of option node (50px tall)
    } else {
      fromX = fromPos.x + 220; // Right edge of step node (220px wide)
      fromY = fromPos.y + 50;  // Middle of step node (100px tall)
    }
    
    // To node calculations
    if (toNodeType === 'option') {
      toX = toPos.x;           // Left edge of option node
      toY = toPos.y + 25;      // Middle of option node (50px tall)
    } else if (toNodeType === 'endpoint') {
      toX = toPos.x;           // Left edge of recommendation node
      toY = toPos.y + 60;      // Middle of recommendation node (120px tall)
    } else {
      toX = toPos.x;           // Left edge of step node
      toY = toPos.y + 50;      // Middle of step node (100px tall)
    }
    
    // Check if this is a "back to start" connection (going backwards/left significantly)
    const isBackToStart = toX < fromX - 100; // Going left by more than 100px indicates back to start
    
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    let pathData;
    
    if (isBackToStart) {
      // Create elegant loop-back path that routes around content
      const horizontalOffset = 300; // How far right to extend before looping back
      const verticalOffset = 200;   // How far down/up to route around content
      
      // Determine if we should route above or below content
      const routeBelow = fromY < toY + 100; // Route below if starting above target area
      const verticalDirection = routeBelow ? 1 : -1;
      
      // Create multi-segment path that routes around content
      const segmentY = fromY + (verticalOffset * verticalDirection);
      
      pathData = `M ${fromX} ${fromY} 
                  L ${fromX + 60} ${fromY}
                  C ${fromX + 100} ${fromY}, ${fromX + 100} ${segmentY}, ${fromX + 60} ${segmentY}
                  L ${toX - 60} ${segmentY}
                  C ${toX - 100} ${segmentY}, ${toX - 100} ${toY}, ${toX - 60} ${toY}
                  L ${toX} ${toY}`;
    } else {
      // Standard curved path for normal connections
      const horizontalDistance = toX - fromX;
      const verticalDistance = Math.abs(toY - fromY);
      
      // Calculate control points to ensure horizontal entry
      const midPoint = Math.max(80, horizontalDistance * 0.6); // Stronger horizontal preference
      
      // First control point: extends horizontally from start point
      const cp1X = fromX + midPoint;
      const cp1Y = fromY;
      
      // Second control point: positioned to ensure horizontal approach to target
      const cp2X = toX - Math.max(40, horizontalDistance * 0.2); // Ensure horizontal approach
      const cp2Y = toY; // Same Y as target for horizontal entry
      
      pathData = `M ${fromX} ${fromY} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${toX} ${toY}`;
    }
    
    path.setAttribute('d', pathData);
    
    // Set line style based on connection type
    let connectionClass = 'flow-connection';
    if (isDotted) {
      connectionClass += ' dotted';
      path.setAttribute('stroke-dasharray', '8,4');
    }
    if (isRecommendation) {
      connectionClass += ' recommendation';
    }
    
    // Standard styling for all connections (removed special green styling for back-to-start)
    path.setAttribute('stroke', '#6B7280');
    path.setAttribute('stroke-width', '2');
    
    path.setAttribute('class', connectionClass);
    path.setAttribute('fill', 'none');
    
    group.appendChild(path);
    
    return group;
  }

  addFlowchartLegend() {
    const container = document.getElementById('flowchartContainer');
    
    // Remove existing legend
    const existingLegend = container.querySelector('.flowchart-legend');
    if (existingLegend) {
      existingLegend.remove();
    }
    
    const legend = document.createElement('div');
    legend.className = 'flowchart-legend';
    legend.innerHTML = `
      <div class="legend-sections-horizontal">
        <div class="legend-section">
          <h4 style="margin: 0 0 8px 0; font-size: 14px;">Step Types</h4>
          <div class="legend-items-horizontal">
            <div class="legend-item">
              <div class="legend-color start"></div>
              <span>Start Step</span>
            </div>
            <div class="legend-item">
              <div class="legend-color choice"></div>
              <span>Multiple Choice</span>
            </div>
            <div class="legend-item">
              <div class="legend-color yes-no"></div>
              <span>Yes/No Decision</span>
            </div>
            <div class="legend-item">
              <div class="legend-color endpoint"></div>
              <span>Endpoint</span>
            </div>
            <div class="legend-item">
              <div class="legend-color option"></div>
              <span>Option Button</span>
            </div>
          </div>
        </div>
        <div class="legend-section">
          <h4 style="margin: 0 0 8px 0; font-size: 14px;">Line Types</h4>
          <div class="legend-items-horizontal">
            <div class="legend-item">
              <div style="width: 20px; height: 2px; background: transparent; border-top: 2px dashed #9CA3AF;"></div>
              <span>Options</span>
            </div>
            <div class="legend-item">
              <div style="width: 20px; height: 2px; background: #6B7280;"></div>
              <span>Next Step</span>
            </div>
          </div>
        </div>
        <div class="legend-section" style="margin-top: 20px;">
          <div class="legend-controls" style="display: flex; gap: 6px; flex-wrap: wrap;">
            <button id="resetZoomLegend" style="padding: 4px 8px; font-size: 11px; height: auto; background: white; border: 1px solid #D1D5DB; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); cursor: pointer;">Reset Zoom</button>
            <button id="zoomInLegend" style="padding: 4px 8px; font-size: 11px; height: auto; min-width: 28px; background: white; border: 1px solid #D1D5DB; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); cursor: pointer;">+</button>
            <button id="zoomOutLegend" style="padding: 4px 8px; font-size: 11px; height: auto; min-width: 28px; background: white; border: 1px solid #D1D5DB; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); cursor: pointer;">-</button>
          </div>
        </div>
      </div>
    `;
    
    // Insert legend at the beginning of the container (above the SVG)
    const svgContainer = container.querySelector('.flowchart-svg-container');
    if (svgContainer) {
      container.insertBefore(legend, svgContainer);
    } else {
      container.insertBefore(legend, container.firstChild);
    }
    
    // Bind legend control events
    const resetZoomBtn = legend.querySelector('#resetZoomLegend');
    const zoomInBtn = legend.querySelector('#zoomInLegend');
    const zoomOutBtn = legend.querySelector('#zoomOutLegend');
    
    if (resetZoomBtn) {
      resetZoomBtn.addEventListener('click', () => this.resetToInitialState());
      resetZoomBtn.addEventListener('mouseenter', () => resetZoomBtn.style.boxShadow = '0 2px 6px rgba(0,0,0,0.15)');
      resetZoomBtn.addEventListener('mouseleave', () => resetZoomBtn.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)');
    }
    if (zoomInBtn) {
      zoomInBtn.addEventListener('click', () => this.zoomFlowchart(1.2));
      zoomInBtn.addEventListener('mouseenter', () => zoomInBtn.style.boxShadow = '0 2px 6px rgba(0,0,0,0.15)');
      zoomInBtn.addEventListener('mouseleave', () => zoomInBtn.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)');
    }
    if (zoomOutBtn) {
      zoomOutBtn.addEventListener('click', () => this.zoomFlowchart(0.8));
      zoomOutBtn.addEventListener('mouseenter', () => zoomOutBtn.style.boxShadow = '0 2px 6px rgba(0,0,0,0.15)');
      zoomOutBtn.addEventListener('mouseleave', () => zoomOutBtn.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)');
    }
  }

  initializeFlowchartInteraction() {
    // Initialize zoom/pan functionality
    this.currentZoom = 1;
    this.currentPan = {x: 0, y: 0};
    
    const svg = document.getElementById('flowchartSvg');
    const container = document.querySelector('.flowchart-container');
    let isPanning = false;
    let startPan = {x: 0, y: 0};
    
    // Prevent right-click context menu
    svg.addEventListener('contextmenu', (e) => {
      e.preventDefault();
    });
    
    svg.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      isPanning = true;
      startPan = {x: e.clientX - this.currentPan.x, y: e.clientY - this.currentPan.y};
      svg.style.cursor = 'grabbing';
    });
    
    svg.addEventListener('mousemove', (e) => {
      if (!isPanning) return;
      
      this.currentPan.x = e.clientX - startPan.x;
      this.currentPan.y = e.clientY - startPan.y;
      this.updateFlowchartTransform();
    });
    
    svg.addEventListener('mouseup', () => {
      isPanning = false;
      svg.style.cursor = 'grab';
    });
    
    svg.addEventListener('mouseleave', () => {
      isPanning = false;
      svg.style.cursor = 'grab';
    });
    
    // Zoom with mouse wheel
    svg.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      this.zoomFlowchart(zoomFactor);
    });
    
    // Don't auto-fit on initial load - let the SVG viewBox handle initial sizing
  }

  updateFlowchartTransform() {
    const contentGroup = document.getElementById('flowchartContent');
    if (contentGroup) {
      contentGroup.setAttribute('transform', `translate(${this.currentPan.x}, ${this.currentPan.y}) scale(${this.currentZoom})`);
    }
  }

  autoLayoutFlowchart() {
    // Re-render the flowchart with fresh positioning
    this.renderFlowchart();
    // Then auto-fit to viewport
    this.autoFitFlowchart();
  }

  autoFitFlowchart() {
    // Wait a bit for DOM to be ready, then calculate auto-fit
    setTimeout(() => {
      const contentGroup = document.getElementById('flowchartContent');
      const svg = document.getElementById('flowchartSvg');
      const container = document.querySelector('.flowchart-container');
      
      if (!contentGroup || !svg || !container) return;
      
      try {
        // Get the bounding box of all content
        const bbox = contentGroup.getBBox();
        
        console.log('Raw bbox:', bbox);
        
        if (bbox.width === 0 || bbox.height === 0) {
          // No content yet, use default positioning
          this.currentZoom = 1;
          this.currentPan = {x: 0, y: 0};
          this.updateFlowchartTransform();
          return;
        }
        
        // Get container dimensions
        const containerRect = container.getBoundingClientRect();
        const legendHeight = 60; // Reduce legend space
        const margin = 20; // Reduce margins
        
        const availableWidth = containerRect.width - (margin * 2);
        const availableHeight = containerRect.height - legendHeight - (margin * 2);
        
        console.log('Container dimensions:', {
          containerWidth: containerRect.width,
          containerHeight: containerRect.height,
          availableWidth,
          availableHeight
        });
        
        // Be much more aggressive with width usage
        const targetWidthUsage = 0.95; // Use 95% of available width
        const widthScale = (availableWidth * targetWidthUsage) / bbox.width;
        const heightScale = availableHeight / bbox.height;
        
        console.log('Calculated scales:', { widthScale, heightScale });
        
        // Use the smaller scale to ensure everything fits, but prefer width
        let scale = Math.min(widthScale, heightScale);
        
        // If the content is very small, allow some zoom-in up to 1.5x
        scale = Math.min(scale, 1.5);
        
        // But don't go below a minimum useful scale
        scale = Math.max(scale, 0.3);
        
        console.log('Final scale chosen:', scale);
        
        // Calculate positioning to center the content
        const scaledWidth = bbox.width * scale;
        const scaledHeight = bbox.height * scale;
        
        // Center horizontally and vertically in available space
        const panX = (availableWidth - scaledWidth) / 2 - (bbox.x * scale) + margin;
        const panY = (availableHeight - scaledHeight) / 2 - (bbox.y * scale) + margin + legendHeight;
        
        // Apply the calculated zoom and pan
        this.currentZoom = scale;
        this.currentPan = {x: panX, y: panY};
        this.updateFlowchartTransform();
        
        console.log('Auto-fit result:', { 
          scale: scale.toFixed(3), 
          panX: panX.toFixed(0), 
          panY: panY.toFixed(0), 
          contentSize: `${bbox.width.toFixed(0)}x${bbox.height.toFixed(0)}`,
          scaledSize: `${scaledWidth.toFixed(0)}x${scaledHeight.toFixed(0)}`,
          containerSize: `${availableWidth.toFixed(0)}x${availableHeight.toFixed(0)}`,
          widthUsage: `${((scaledWidth / availableWidth) * 100).toFixed(1)}%`,
          heightUsage: `${((scaledHeight / availableHeight) * 100).toFixed(1)}%`
        });
        
      } catch (error) {
        console.warn('Auto-fit calculation failed:', error);
        // Fallback to a larger default
        this.currentZoom = 1;
        this.currentPan = {x: 50, y: 100};
        this.updateFlowchartTransform();
      }
    }, 250);
  }

  resetToInitialState() {
    // Reset to initial load state - no zoom, no pan, just SVG viewBox sizing
    this.currentZoom = 1;
    this.currentPan = {x: 0, y: 0};
    this.updateFlowchartTransform();
  }

  zoomFlowchart(factor) {
    this.currentZoom *= factor;
    this.currentZoom = Math.max(0.1, Math.min(3, this.currentZoom)); // Limit zoom range
    this.updateFlowchartTransform();
  }

  truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength - 3) + '...' : text;
  }

  insertCallout(calloutType) {
    const textarea = document.getElementById('stepQuestion');
    if (!textarea) return;

    const cursorPosition = textarea.selectionStart;
    const currentValue = textarea.value;
    
    // Insert callout syntax at cursor position
    const calloutText = `[${calloutType}]Insert your ${calloutType} text here[/${calloutType}]`;
    const newValue = currentValue.slice(0, cursorPosition) + calloutText + currentValue.slice(cursorPosition);
    
    textarea.value = newValue;
    
    // Position cursor inside the callout content for easy editing
    const contentStart = cursorPosition + calloutType.length + 2; // After [type]
    const contentEnd = contentStart + `Insert your ${calloutType} text here`.length;
    textarea.setSelectionRange(contentStart, contentEnd);
    
    // Focus the textarea
    textarea.focus();
  }

  generateIdFromTitle(title) {
    if (!title || title.trim() === '') {
      return '';
    }
    
    return title
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, '') // Remove special characters except spaces and hyphens
      .replace(/\s+/g, '-') // Replace spaces with hyphens
      .replace(/-+/g, '-') // Replace multiple hyphens with single hyphen
      .replace(/^-|-$/g, ''); // Remove leading/trailing hyphens
  }

  // Change tracking for builder view
  captureInitialTreeState() {
    this.initialTreeState = JSON.stringify(this.currentTree);
    this.hasUnsavedChanges = false;
    this.updateSaveDraftVisibility();
  }

  checkForTreeChanges() {
    if (!this.initialTreeState) return;
    
    const currentState = JSON.stringify(this.currentTree);
    this.hasUnsavedChanges = this.initialTreeState !== currentState;
    this.updateSaveDraftVisibility();
  }

  updateSaveDraftVisibility() {
    const saveDraftButton = document.getElementById('saveDraftButton');
    if (saveDraftButton) {
      saveDraftButton.style.display = this.hasUnsavedChanges ? 'inline-flex' : 'none';
    }
  }

  markAsChanged() {
    this.hasUnsavedChanges = true;
    this.updateSaveDraftVisibility();
  }
}

// Initialize the builder when DOM is loaded
let builder;
document.addEventListener('DOMContentLoaded', () => {
  try {
    console.log('Initializing Decision Tree Builder...');
    
    // Debug: Check if key elements exist
    const criticalElements = [
      'builderTab', 'birdseyeTab', 'previewTab', 'jsonTab',
      'addStep', 'addGuide', 'closeModal', 'saveStep'
    ];
    
    console.log('Checking for critical elements:');
    criticalElements.forEach(id => {
      const element = document.getElementById(id);
      console.log(`- ${id}: ${element ? 'FOUND' : 'MISSING'}`);
    });
    
    builder = new DecisionTreeBuilder();
    console.log('Decision Tree Builder initialized successfully');
  } catch (error) {
    console.error('Failed to initialize Decision Tree Builder:', error);
    console.error('Error details:', error.message);
    console.error('Stack trace:', error.stack);
  }
});