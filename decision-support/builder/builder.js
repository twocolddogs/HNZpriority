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
    
    this.init();
  }

  init() {
    console.log('Initializing DecisionTreeBuilder...');
    try {
      this.bindEvents();
      console.log('Events bound successfully');
      this.updateUI();
      console.log('UI updated successfully');
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
      // JSON export/import
      console.log('Binding JSON import/export events...');
      document.getElementById('exportJson').addEventListener('click', () => this.exportJSON());
      document.getElementById('importJson').addEventListener('click', () => this.importJSON());
      document.getElementById('loadExample').addEventListener('click', () => this.loadExample());
      document.getElementById('jsonFileInput').addEventListener('change', (e) => this.handleFileImport(e));
      console.log('JSON import/export events bound successfully');
    } catch (error) {
      console.error('Error binding JSON import/export events:', error);
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
      console.log('Modal overlay events bound successfully');
    } catch (error) {
      console.error('Error binding modal overlay events:', error);
      throw error;
    }

    try {
      // Birdseye view controls
      console.log('Binding birdseye view controls...');
      document.getElementById('autoLayout').addEventListener('click', () => this.autoLayoutFlowchart());
      document.getElementById('resetZoom').addEventListener('click', () => this.resetFlowchartZoom());
      document.getElementById('zoomIn').addEventListener('click', () => this.zoomFlowchart(1.2));
      document.getElementById('zoomOut').addEventListener('click', () => this.zoomFlowchart(0.8));
      console.log('Birdseye view controls bound successfully');
    } catch (error) {
      console.error('Error binding birdseye view controls:', error);
      throw error;
    }

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

    if (viewName === 'birdseye') {
      this.updateBirdseye();
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
        actionText = `→ ${option.action.nextStep}`;
      } else if (option.action.type === 'recommend') {
        actionText = `🎯 ${option.action.recommendation.modality}`;
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
  }

  deleteStep() {
    if (!this.currentEditingStep) return;
    
    if (confirm('Are you sure you want to delete this step?')) {
      delete this.currentTree.steps[this.currentEditingStep];
      this.closeModal();
      this.updateUI();
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
        alert('Decision tree imported successfully!');
      } catch (error) {
        alert('Error importing file: ' + error.message);
      }
    };
    reader.readAsText(file);
  }

  loadExample() {
    // Embed the example directly to avoid fetch issues
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
                "Dotarem or Gadovist: Question of haemangioma with no other malignancy"
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
              "text": "Cirrhosis or risk factors for cirrhosis and no other malignancy suspected",
              "variant": "primary",
              "action": {
                "type": "recommend",
                "recommendation": {
                  "modality": "MRI liver",
                  "contrast": "with Gadovist (in line with Auckland unless specified by MDM)"
                }
              }
            },
            {
              "text": "Patients less than 40 years old",
              "variant": "primary", 
              "action": {
                "type": "navigate",
                "nextStep": "under-40-branch"
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
                "type": "recommend",
                "recommendation": {
                  "modality": "MRCP/MRI liver/pancreas",
                  "contrast": "with Gadolinium"
                }
              }
            }
          ]
        }
      }
    };
    
    this.currentTree = exampleTree;
    this.updateUI();
    alert('Liver imaging example loaded successfully!');
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
        // Direct recommendation
        option.action = {
          type: 'recommend',
          recommendation: {
            modality: document.getElementById('recModality').value,
            contrast: document.getElementById('recContrast').value,
            notes: document.getElementById('recNotes').value,
            priority: document.getElementById('recPriority').value
          }
        };
      }
    }

    this.closeOptionModal();
    this.updateOptionsList(step.options);
    this.updateUI();
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
    
    // Add arrow marker definition
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    marker.setAttribute('id', 'arrowhead');
    marker.setAttribute('markerWidth', '10');
    marker.setAttribute('markerHeight', '7');
    marker.setAttribute('refX', '9');
    marker.setAttribute('refY', '3.5');
    marker.setAttribute('orient', 'auto');
    
    const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygon.setAttribute('points', '0 0, 10 3.5, 0 7');
    polygon.setAttribute('class', 'flow-arrow-marker');
    
    marker.appendChild(polygon);
    defs.appendChild(marker);
    svg.appendChild(defs);
    
    // Create main content group for zoom/pan
    const contentGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    contentGroup.setAttribute('id', 'flowchartContent');
    contentGroup.setAttribute('transform', 'translate(0,0) scale(1)');
    svg.appendChild(contentGroup);
    
    // Calculate positions for nodes
    const positions = this.calculateNodePositions();
    const nodes = {};
    
    // Calculate SVG dimensions based on positions
    let maxX = 0, maxY = 0;
    Object.values(positions).forEach(pos => {
      maxX = Math.max(maxX, pos.x + 200);
      maxY = Math.max(maxY, pos.y + 100);
    });
    
    // Update viewBox to fit content with more padding
    svg.setAttribute('viewBox', `0 0 ${Math.max(3000, maxX + 200)} ${Math.max(1200, maxY + 200)}`);
    
    // Create connections first (so they appear behind nodes)
    Object.entries(this.currentTree.steps).forEach(([stepId, step]) => {
      if (!step.options) return;
      
      step.options.forEach((option, optionIndex) => {
        const optionId = `option_${stepId}_${optionIndex}`;
        
        // Connection from step to option node
        if (positions[stepId] && positions[optionId]) {
          const stepToOption = this.createConnection(
            positions[stepId], 
            positions[optionId], 
            '', // No label needed for step to option
            false,
            'step',
            'option'
          );
          contentGroup.appendChild(stepToOption);
        }
        
        // Connection from option node to target
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
            targetNodeType
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
    
    // Initialize zoom/pan
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
    
    // Calculate positions for left-to-right layout
    const nodeWidth = 200;
    const nodeHeight = 100;
    const levelWidth = 320;  // Increased horizontal spacing for breathing room
    const nodeSpacing = 120; // Increased vertical spacing
    const startX = 150;      // More margin from left edge
    const startY = 100;
    
    // Calculate total height needed for proper centering
    const maxNodesInLevel = Math.max(...Object.values(levelCounts));
    const totalHeight = maxNodesInLevel * nodeHeight + (maxNodesInLevel - 1) * nodeSpacing;
    
    Object.entries(levels).forEach(([nodeId, level]) => {
      const nodesInLevel = levelCounts[level];
      const levelHeight = nodesInLevel * nodeHeight + (nodesInLevel - 1) * nodeSpacing;
      const startYForLevel = startY + (totalHeight - levelHeight) / 2;
      
      const indexInLevel = Object.entries(levels)
        .filter(([id, l]) => l === level)
        .sort()
        .findIndex(([id]) => id === nodeId);
      
      positions[nodeId] = {
        x: startX + level * levelWidth,  // Left to right
        y: startYForLevel + indexInLevel * (nodeHeight + nodeSpacing)  // Top to bottom within level
      };
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
    
    // Determine colors based on step type
    let fillColor = '#3B82F6'; // default blue
    if (step.id === this.currentTree.startStep) fillColor = '#10B981'; // green for start
    else if (step.type === 'endpoint') fillColor = '#F59E0B'; // orange for endpoints
    else if (step.type === 'yes-no') fillColor = '#6366F1'; // indigo for yes/no
    else if (step.type === 'protocol-info') fillColor = '#6B7280'; // gray for protocol
    
    // Create rectangle - larger for better readability
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('class', 'flow-node-rect');
    rect.setAttribute('width', '180');
    rect.setAttribute('height', '80');
    rect.setAttribute('fill', fillColor);
    rect.setAttribute('rx', '8');
    rect.setAttribute('ry', '8');
    rect.setAttribute('stroke', '#fff');
    rect.setAttribute('stroke-width', '2');
    
    // Create title text - no truncation, use full title
    const titleText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    titleText.setAttribute('class', 'flow-node-text flow-node-title');
    titleText.setAttribute('x', '90');
    titleText.setAttribute('y', '30');
    
    // Split long text into multiple lines - show question for decision steps, title for others
    let displayText = step.title || step.id;
    
    // For decision steps, show the question if available
    if ((step.type === 'choice' || step.type === 'yes-no') && step.question) {
      displayText = step.question;
    }
    
    const words = displayText.split(' ');
    const maxCharsPerLine = 18;
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
    
    // Add text lines
    if (lines.length === 1) {
      titleText.textContent = lines[0];
      titleText.setAttribute('y', '35');
    } else {
      titleText.textContent = lines[0];
      titleText.setAttribute('y', '25');
      
      if (lines[1]) {
        const titleText2 = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        titleText2.setAttribute('class', 'flow-node-text flow-node-title');
        titleText2.setAttribute('x', '90');
        titleText2.setAttribute('y', '42');
        titleText2.textContent = lines[1];
        group.appendChild(titleText2);
      }
    }
    
    // Create type text
    const typeText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    typeText.setAttribute('class', 'flow-node-text flow-node-type');
    typeText.setAttribute('x', '90');
    typeText.setAttribute('y', '65');
    typeText.textContent = step.type.replace('-', ' ');
    
    group.appendChild(rect);
    group.appendChild(titleText);
    group.appendChild(typeText);
    
    // Add click handler for real steps
    group.addEventListener('click', () => {
      this.showView('builder');
      this.editStep(step.id);
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
    rect.setAttribute('fill', '#10B981'); // green for recommendations
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
    titleText.textContent = '✓ Recommendation';
    
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
    
    return group;
  }

  createOptionNode(optionData, x, y) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', 'flow-node option');
    group.setAttribute('transform', `translate(${x},${y})`);
    
    // Determine color based on variant
    let fillColor = '#3B82F6'; // primary blue
    let strokeColor = '#3B82F6';
    
    switch (optionData.variant) {
      case 'secondary':
        fillColor = '#6B7280';
        strokeColor = '#6B7280';
        break;
      case 'success':
        fillColor = '#10B981';
        strokeColor = '#10B981';
        break;
      case 'warning':
        fillColor = '#F59E0B';
        strokeColor = '#F59E0B';
        break;
      case 'danger':
        fillColor = '#EF4444';
        strokeColor = '#EF4444';
        break;
      default:
        fillColor = '#3B82F6';
        strokeColor = '#3B82F6';
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
    
    return group;
  }

  createConnection(fromPos, toPos, label, isRecommendation = false, fromNodeType = 'step', toNodeType = 'step') {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    
    // Calculate connection points based on node types
    let fromX, fromY, toX, toY;
    
    // From node calculations
    if (fromNodeType === 'option') {
      fromX = fromPos.x + 140; // Right edge of option node (140px wide)
      fromY = fromPos.y + 25;  // Middle of option node (50px tall)
    } else {
      fromX = fromPos.x + 180; // Right edge of step node (180px wide)
      fromY = fromPos.y + 40;  // Middle of step node (80px tall)
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
      toY = toPos.y + 40;      // Middle of step node (80px tall)
    }
    
    // Create curved path for left-to-right connections
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const midX = fromX + (toX - fromX) / 2;
    const pathData = `M ${fromX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}`;
    
    path.setAttribute('d', pathData);
    path.setAttribute('class', `flow-connection ${isRecommendation ? 'recommendation' : ''}`);
    path.setAttribute('marker-end', 'url(#arrowhead)');
    
    // Create label
    const labelX = (fromX + toX) / 2;
    const labelY = (fromY + toY) / 2;
    
    const labelText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    labelText.setAttribute('class', 'flow-connection-label');
    labelText.setAttribute('x', labelX);
    labelText.setAttribute('y', labelY);
    
    // Don't truncate labels, use full text
    const displayLabel = label || '';
    labelText.textContent = displayLabel;
    
    // Create background rectangle for label
    const labelBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    
    // Estimate text dimensions
    const textWidth = displayLabel.length * 7; // Rough estimation
    const textHeight = 16;
    
    labelBg.setAttribute('x', labelX - textWidth/2 - 4);
    labelBg.setAttribute('y', labelY - textHeight/2 - 2);
    labelBg.setAttribute('width', textWidth + 8);
    labelBg.setAttribute('height', textHeight + 4);
    labelBg.setAttribute('fill', '#fff');
    labelBg.setAttribute('stroke', '#e5e7eb');
    labelBg.setAttribute('rx', '4');
    labelBg.setAttribute('opacity', '0.9');
    
    group.appendChild(path);
    group.appendChild(labelBg);
    group.appendChild(labelText);
    
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
      <h4 style="margin: 0 0 8px 0; font-size: 14px;">Node Types</h4>
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
        <div class="legend-color protocol-info"></div>
        <span>Protocol Info</span>
      </div>
      <div class="legend-item">
        <div class="legend-color option"></div>
        <span>Option Button</span>
      </div>
      <div class="legend-item">
        <div class="legend-color endpoint"></div>
        <span>Recommendation</span>
      </div>
    `;
    
    container.appendChild(legend);
  }

  initializeFlowchartInteraction() {
    // Initialize zoom/pan functionality
    this.currentZoom = 1;
    this.currentPan = {x: 0, y: 0};
    
    const svg = document.getElementById('flowchartSvg');
    let isPanning = false;
    let startPan = {x: 0, y: 0};
    
    svg.addEventListener('mousedown', (e) => {
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
    
    // Zoom with mouse wheel
    svg.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      this.zoomFlowchart(zoomFactor);
    });
  }

  updateFlowchartTransform() {
    const contentGroup = document.getElementById('flowchartContent');
    if (contentGroup) {
      contentGroup.setAttribute('transform', `translate(${this.currentPan.x}, ${this.currentPan.y}) scale(${this.currentZoom})`);
    }
  }

  autoLayoutFlowchart() {
    this.currentZoom = 1;
    this.currentPan = {x: 0, y: 0};
    this.updateFlowchartTransform();
    this.renderFlowchart();
  }

  resetFlowchartZoom() {
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