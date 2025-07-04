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
      document.getElementById('stepType').addEventListener('change', (e) => {
        this.updateStepTypeUI(e.target.value);
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
      console.log('Options management events bound successfully');
    } catch (error) {
      console.error('Error binding options management events:', error);
      throw error;
    }

    try {
      // Hamburger menu events
      console.log('Binding hamburger menu events...');
      document.getElementById('hamburgerToggle').addEventListener('click', () => this.toggleHamburgerMenu());
      document.getElementById('menuSaveDraft').addEventListener('click', () => { this.closeHamburgerMenu(); this.saveDraft(); });
      document.getElementById('menuPublish').addEventListener('click', () => { this.closeHamburgerMenu(); this.publishPathway(); });
      document.getElementById('menuLiveApp').addEventListener('click', () => this.closeHamburgerMenu());
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
      document.getElementById('refreshLibrary').addEventListener('click', () => this.loadPathways());
      document.getElementById('statusFilter').addEventListener('change', () => this.filterPathways());
      document.getElementById('searchFilter').addEventListener('input', () => this.filterPathways());
      console.log('Library view events bound successfully');
    } catch (error) {
      console.error('Error binding library view events:', error);
      throw error;
    }

    try {
      // Close modal on overlay click
      console.log('Binding modal overlay events...');
      document.getElementById('stepModal').addEventListener('click', (e) => {
        if (e.target.id === 'stepModal') {
          this.closeModal();
        }
      });
      
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
  }

  showView(viewName) {
    // Update tabs
    document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
    document.getElementById(viewName + 'Tab').classList.add('active');

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
    }
  }

  updateUI() {
    this.updateTreeProperties();
    this.updateStepsList();
    this.updateStartStepSelect();
    this.updateGuidesList();
    this.updateJSON();
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
      stepItem.className = 'step-item';
      stepItem.addEventListener('click', () => this.editStep(step.id));

      stepItem.innerHTML = `
        <h4>${step.title || 'Untitled Step'}</h4>
        <p>ID: ${step.id}</p>
        <span class="step-type">${step.type}</span>
      `;

      stepsList.appendChild(stepItem);
    });

    // Show virtual recommendation endpoints
    this.getRecommendationEndpoints().forEach(endpoint => {
      const stepItem = document.createElement('div');
      stepItem.className = 'step-item recommendation-endpoint';
      stepItem.addEventListener('click', () => this.editRecommendationEndpoint(endpoint.id));
      
      // Visual styling for recommendation endpoints
      stepItem.style.border = '1px solid #10B981';
      stepItem.style.backgroundColor = '#ECFDF5';

      stepItem.innerHTML = `
        <h4>✓ ${endpoint.recommendation.modality || 'Recommendation'}</h4>
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
      option.textContent = `${step.title || 'Untitled'} (${step.id})`;
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
    const stepId = `step-${Date.now()}`;
    const newStep = {
      id: stepId,
      title: '',
      type: 'choice',
      options: []
    };

    this.currentTree.steps[stepId] = newStep;
    this.updateUI();
    this.editStep(stepId);
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
    document.getElementById('stepType').value = 'endpoint';
    
    // Populate endpoint fields
    document.getElementById('endpointModality').value = endpoint.recommendation.modality || '';
    document.getElementById('endpointContrast').value = endpoint.recommendation.contrast || '';
    document.getElementById('endpointNotes').value = endpoint.recommendation.notes || '';
    document.getElementById('endpointPriority').value = endpoint.recommendation.priority || '';
    
    // Update UI to show endpoint section
    this.updateStepTypeUI('endpoint');
    
    // Show the modal
    document.getElementById('stepModal').classList.remove('hidden');
  }

  editStep(stepId) {
    this.currentEditingStep = stepId;
    const step = this.currentTree.steps[stepId];
    
    if (!step) return;

    // Populate modal fields
    document.getElementById('stepId').value = step.id;
    document.getElementById('stepTitle').value = step.title || '';
    document.getElementById('stepSubtitle').value = step.subtitle || '';
    document.getElementById('stepQuestion').value = step.question || '';
    document.getElementById('stepType').value = step.type;

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
      document.getElementById('endpointModality').value = step.recommendation.modality || '';
      document.getElementById('endpointContrast').value = step.recommendation.contrast || '';
      document.getElementById('endpointNotes').value = step.recommendation.notes || '';
      document.getElementById('endpointPriority').value = step.recommendation.priority || '';
    } else {
      document.getElementById('endpointModality').value = '';
      document.getElementById('endpointContrast').value = '';
      document.getElementById('endpointNotes').value = '';
      document.getElementById('endpointPriority').value = '';
    }

    this.updateStepTypeUI(step.type);
    this.updateOptionsList(step.options || []);
    this.showModal();
  }

  updateStepTypeUI(stepType) {
    const protocolSection = document.getElementById('protocolSection');
    const optionsSection = document.getElementById('optionsSection');
    const endpointSection = document.getElementById('endpointSection');

    // Hide all sections first
    protocolSection.classList.add('hidden');
    optionsSection.classList.add('hidden');
    endpointSection.classList.add('hidden');

    // Show relevant sections
    switch (stepType) {
      case 'guide':
        protocolSection.classList.remove('hidden');
        optionsSection.classList.remove('hidden');
        break;
      case 'endpoint':
        endpointSection.classList.remove('hidden');
        break;
      case 'choice':
      case 'yes-no':
        optionsSection.classList.remove('hidden');
        break;
    }
  }

  updateOptionsList(options) {
    const optionsList = document.getElementById('optionsList');
    optionsList.innerHTML = '';

    options.forEach((option, index) => {
      const optionItem = document.createElement('div');
      optionItem.className = 'option-item';
      
      let actionText = '';
      if (option.action.type === 'navigate') {
        actionText = `󰁔 ${option.action.nextStep}`;
      } else if (option.action.type === 'recommend') {
        actionText = `󰯯 ${option.action.recommendation.modality}`;
      }

      optionItem.innerHTML = `
        <div class="option-content">
          <div><strong>${option.text}</strong></div>
          <div style="font-size: 0.875rem; color: var(--text-muted);">${actionText}</div>
        </div>
        <div class="option-controls">
          <button class="btn secondary small" onclick="builder.editOptionAtIndex(${index})">Edit</button>
          <button class="btn danger small" onclick="builder.removeOptionAtIndex(${index})">Remove</button>
        </div>
      `;
      
      optionsList.appendChild(optionItem);
    });
  }

  addOption() {
    if (!this.currentEditingStep) return;

    const step = this.currentTree.steps[this.currentEditingStep];
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
        modality: document.getElementById('endpointModality').value,
        contrast: document.getElementById('endpointContrast').value,
        notes: document.getElementById('endpointNotes').value,
        priority: document.getElementById('endpointPriority').value
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
      this.closeModal();
      return;
    }

    const step = this.currentTree.steps[this.currentEditingStep];
    
    // Basic properties
    const newId = document.getElementById('stepId').value;
    const title = document.getElementById('stepTitle').value;
    const subtitle = document.getElementById('stepSubtitle').value;
    const question = document.getElementById('stepQuestion').value;
    const type = document.getElementById('stepType').value;

    // Handle ID change
    if (newId !== step.id) {
      delete this.currentTree.steps[step.id];
      this.currentTree.steps[newId] = step;
      step.id = newId;
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
        modality: document.getElementById('endpointModality').value,
        contrast: document.getElementById('endpointContrast').value,
        notes: document.getElementById('endpointNotes').value,
        priority: document.getElementById('endpointPriority').value
      };
      delete step.options;
    } else {
      delete step.recommendation;
    }

    this.closeModal();
    this.updateUI();
    this.updateJSON();
  }

  deleteStep() {
    if (!this.currentEditingStep) return;
    
    if (confirm('Are you sure you want to delete this step?')) {
      delete this.currentTree.steps[this.currentEditingStep];
      this.closeModal();
      this.updateUI();
      this.updateJSON();
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
    this.closeGuideModal();
  }

  deleteGuide() {
    if (this.currentEditingGuideIndex >= 0) {
      if (confirm('Are you sure you want to delete this guide?')) {
        this.currentTree.guides.splice(this.currentEditingGuideIndex, 1);
        this.updateGuidesList();
        this.updateJSON();
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
        protocol: 'Guide (Blue)',
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
    document.getElementById('sectionType').value = 'protocol';
    document.getElementById('sectionContent').value = '';
    document.getElementById('sectionItems').value = '';
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
    document.getElementById('sectionType').value = section.type || 'protocol';
    document.getElementById('sectionContent').value = section.content || '';
    document.getElementById('sectionItems').value = section.items ? section.items.join('\n') : '';
    document.getElementById('guideSectionModalTitle').textContent = 'Edit Section';
    document.getElementById('deleteGuideSection').style.display = 'inline-flex';
    
    this.showGuideSectionModal();
  }

  showGuideSectionModal() {
    document.getElementById('guideSectionModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
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
    const itemsText = document.getElementById('sectionItems').value.trim();
    
    if (!title) {
      alert('Please enter a section title');
      return;
    }

    const sectionData = {
      title: title,
      type: type,
      content: content
    };

    if (itemsText) {
      sectionData.items = itemsText.split('\n').map(item => item.trim()).filter(item => item);
    }

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
    this.closeGuideSectionModal();
  }

  deleteGuideSection() {
    if (this.currentEditingSectionIndex >= 0) {
      if (confirm('Are you sure you want to delete this section?')) {
        this.currentEditingGuide.sections.splice(this.currentEditingSectionIndex, 1);
        this.updateGuideSectionsList(this.currentEditingGuide.sections);
        this.closeGuideSectionModal();
      }
    }
  }

  removeGuideSection(index) {
    if (confirm('Are you sure you want to remove this section?')) {
      this.currentEditingGuide.sections.splice(index, 1);
      this.updateGuideSectionsList(this.currentEditingGuide.sections);
    }
  }


  showModal() {
    document.getElementById('stepModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  closeModal() {
    document.getElementById('stepModal').classList.add('hidden');
    document.body.style.overflow = 'auto';
    this.currentEditingStep = null;
    this.currentEditingOption = null;
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
    
    if (this.advancedMode) {
      jsonTab.classList.remove('hidden');
      toggleIndicator.textContent = 'ON';
      toggleIndicator.classList.add('on');
    } else {
      jsonTab.classList.add('hidden');
      toggleIndicator.textContent = 'OFF';
      toggleIndicator.classList.remove('on');
      
      // If JSON tab is currently active, switch to builder tab
      if (jsonTab.classList.contains('active')) {
        this.showView('builder');
      }
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
      
      const modality = document.createElement('div');
      modality.innerHTML = `<strong>Modality:</strong> ${rec.modality}`;
      recCard.appendChild(modality);
      
      const contrast = document.createElement('div');
      contrast.innerHTML = `<strong>Contrast:</strong> ${rec.contrast}`;
      recCard.appendChild(contrast);
      
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
    const calloutRegex = /\[(protocol|guide|info|warning|success|danger)\](.*?)\[\/\1\]/g;
    
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
  }

  // Public methods for button onclick handlers
  removeGuideAtIndex(index) {
    if (confirm('Are you sure you want to remove this guide?')) {
      this.currentTree.guides.splice(index, 1);
      this.updateGuidesList();
      this.updateJSON();
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
        document.getElementById('recModality').value = option.action.recommendation.modality || '';
        document.getElementById('recContrast').value = option.action.recommendation.contrast || '';
        document.getElementById('recNotes').value = option.action.recommendation.notes || '';
        document.getElementById('recPriority').value = option.action.recommendation.priority || '';
      }
    }
    
    this.showOptionModal();
  }

  removeOptionAtIndex(index) {
    if (!this.currentEditingStep) return;
    
    const step = this.currentTree.steps[this.currentEditingStep];
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
        option.textContent = `${step.title || 'Untitled'} (${step.id})`;
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
        
        this.currentTree.steps[newStepId] = newStep;
        
        option.action = {
          type: 'navigate',
          nextStep: newStepId
        };
      } else {
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
          modality: document.getElementById('recModality').value,
          contrast: document.getElementById('recContrast').value,
          notes: document.getElementById('recNotes').value,
          priority: document.getElementById('recPriority').value
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
        const modality = document.getElementById('recModality').value || 'Recommendation';
        
        // Create the new endpoint step
        const recommendation = {
          modality: document.getElementById('recModality').value,
          contrast: document.getElementById('recContrast').value,
          notes: document.getElementById('recNotes').value,
          priority: document.getElementById('recPriority').value
        };
        
        const newEndpointStep = {
          id: newEndpointId,
          title: `${modality} Recommendation`,
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
  }

  deleteOption() {
    if (!this.currentEditingStep || this.currentEditingOption === null) return;
    
    if (confirm('Are you sure you want to delete this option?')) {
      const step = this.currentTree.steps[this.currentEditingStep];
      step.options.splice(this.currentEditingOption, 1);
      this.closeOptionModal();
      this.updateOptionsList(step.options);
      this.updateJSON();
    }
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
            isOptionNode: true
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
    
    // Determine colors based on step type with better differentiation
    let fillColor = '#F59E0B'; // default orange for choice
    if (step.id === this.currentTree.startStep) {
      fillColor = '#059669'; // darker green for start step
    } else if (step.type === 'endpoint') {
      fillColor = '#2563EB'; // blue for endpoints
    } else if (step.type === 'yes-no') {
      fillColor = '#EA580C'; // darker orange for yes/no
    } else if (step.type === 'guide') {
      fillColor = '#4338CA'; // indigo for guide/protocol
    } else if (step.type === 'choice') {
      fillColor = '#F59E0B'; // orange for multiple choice
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
    
    // Birdseye view is read-only - no click handlers to edit steps
    
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
    rect.setAttribute('fill', '#2563EB'); // blue for recommendations to match endpoint color
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
    
    // Modality
    const modalityText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    modalityText.setAttribute('class', 'flow-node-text');
    modalityText.setAttribute('x', '110');
    modalityText.setAttribute('y', '40');
    modalityText.setAttribute('font-size', '11');
    modalityText.setAttribute('font-weight', '600');
    modalityText.textContent = rec.modality || 'Imaging';
    
    // Contrast
    if (rec.contrast) {
      const contrastText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      contrastText.setAttribute('class', 'flow-node-text');
      contrastText.setAttribute('x', '110');
      contrastText.setAttribute('y', '55');
      contrastText.setAttribute('font-size', '10');
      contrastText.textContent = rec.contrast;
      group.appendChild(contrastText);
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
    group.appendChild(modalityText);
    group.appendChild(typeText);
    
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
    
    // Determine color based on variant
    let fillColor = '#6B7280'; // grey for option buttons
    let strokeColor = '#2563EB';
    
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
    
    // Create smaller rectangle for option nodes
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('class', 'flow-option-rect');
    rect.setAttribute('width', '140');
    rect.setAttribute('height', '50');
    rect.setAttribute('fill', fillColor);
    rect.setAttribute('rx', '25'); // More rounded for button look
    rect.setAttribute('ry', '25');
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
    
    // Create horizontal curved path that always ends horizontally for proper arrowhead alignment
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
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
    
    const pathData = `M ${fromX} ${fromY} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${toX} ${toY}`;
    
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
    
    path.setAttribute('class', connectionClass);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#6B7280');
    path.setAttribute('stroke-width', '2');
    
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
              <div class="legend-color guide"></div>
              <span>Guide/Protocol</span>
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
        <div class="legend-section" style="margin-top: 12px;">
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