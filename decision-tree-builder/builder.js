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
    this.bindEvents();
    this.updateUI();
  }

  bindEvents() {
    // Tab navigation
    document.getElementById('builderTab').addEventListener('click', () => this.showView('builder'));
    document.getElementById('birdseyeTab').addEventListener('click', () => this.showView('birdseye'));
    document.getElementById('previewTab').addEventListener('click', () => this.showView('preview'));
    document.getElementById('jsonTab').addEventListener('click', () => this.showView('json'));

    // Tree properties
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

    // Step management
    document.getElementById('addStep').addEventListener('click', () => this.addStep());
    document.getElementById('addGuide').addEventListener('click', () => this.addGuide());

    // Modal events
    document.getElementById('closeModal').addEventListener('click', () => this.closeModal());
    document.getElementById('saveStep').addEventListener('click', () => this.saveStep());
    document.getElementById('deleteStep').addEventListener('click', () => this.deleteStep());
    document.getElementById('cancelStep').addEventListener('click', () => this.closeModal());

    // Option modal events
    document.getElementById('closeOptionModal').addEventListener('click', () => this.closeOptionModal());
    document.getElementById('saveOption').addEventListener('click', () => this.saveOption());
    document.getElementById('deleteOption').addEventListener('click', () => this.deleteOption());
    document.getElementById('cancelOption').addEventListener('click', () => this.closeOptionModal());

    // Option form changes
    document.getElementById('optionAction').addEventListener('change', (e) => {
      this.updateOptionActionUI(e.target.value);
    });
    document.getElementById('targetStep').addEventListener('change', (e) => {
      this.updateTargetStepUI(e.target.value);
    });
    document.getElementById('existingEndpoint').addEventListener('change', (e) => {
      this.updateEndpointUI(e.target.value);
    });

    // Step type change
    document.getElementById('stepType').addEventListener('change', (e) => {
      this.updateStepTypeUI(e.target.value);
    });

    // Options management
    document.getElementById('addOption').addEventListener('click', () => this.addOption());

    // JSON export/import
    document.getElementById('exportJson').addEventListener('click', () => this.exportJSON());
    document.getElementById('importJson').addEventListener('click', () => this.importJSON());
    document.getElementById('loadExample').addEventListener('click', () => this.loadExample());
    document.getElementById('jsonFileInput').addEventListener('change', (e) => this.handleFileImport(e));

    // Close modal on overlay click
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

    // Birdseye view controls
    document.getElementById('autoLayout').addEventListener('click', () => this.autoLayoutFlowchart());
    document.getElementById('resetZoom').addEventListener('click', () => this.resetFlowchartZoom());
    document.getElementById('zoomIn').addEventListener('click', () => this.zoomFlowchart(1.2));
    document.getElementById('zoomOut').addEventListener('click', () => this.zoomFlowchart(0.8));
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
      
      guideItem.innerHTML = `
        <span>${guide.title || 'Untitled Guide'}</span>
        <button class="btn danger small" onclick="builder.removeGuideAtIndex(${index})">Remove</button>
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

    // Protocol info
    if (step.protocolInfo) {
      document.getElementById('protocolTitle').value = step.protocolInfo.title || '';
      document.getElementById('protocolDescription').value = step.protocolInfo.description || '';
      document.getElementById('protocolNote').value = step.protocolInfo.note || '';
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
      case 'protocol-info':
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

    // Protocol info
    if (type === 'protocol-info') {
      step.protocolInfo = {
        title: document.getElementById('protocolTitle').value,
        description: document.getElementById('protocolDescription').value,
        note: document.getElementById('protocolNote').value
      };
    } else {
      delete step.protocolInfo;
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
    const title = prompt('Guide title:');
    if (title) {
      const newGuide = {
        id: `guide-${Date.now()}`,
        title: title,
        sections: []
      };
      
      this.currentTree.guides.push(newGuide);
      this.updateGuidesList();
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
    
    // Update viewBox to fit content
    svg.setAttribute('viewBox', `0 0 ${Math.max(2000, maxX + 100)} ${Math.max(1000, maxY + 100)}`);
    
    // Create connections first (so they appear behind nodes)
    Object.entries(this.currentTree.steps).forEach(([stepId, step]) => {
      if (!step.options) return;
      
      step.options.forEach((option, index) => {
        let targetStep = null;
        let isRecommendation = false;
        
        if (option.action.type === 'navigate' && option.action.nextStep) {
          targetStep = option.action.nextStep;
        } else if (option.action.type === 'recommend') {
          isRecommendation = true;
        }
        
        if (targetStep && positions[stepId] && positions[targetStep]) {
          const connection = this.createConnection(
            positions[stepId], 
            positions[targetStep], 
            option.text,
            isRecommendation
          );
          contentGroup.appendChild(connection);
        }
      });
    });
    
    // Create nodes (so they appear on top of connections)
    Object.entries(positions).forEach(([stepId, pos]) => {
      const step = this.currentTree.steps[stepId];
      if (!step) return;
      
      const node = this.createFlowchartNode(step, pos.x, pos.y);
      nodes[stepId] = { element: node, step: step, pos: pos };
      contentGroup.appendChild(node);
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
        step.options.forEach(option => {
          if (option.action.type === 'navigate' && option.action.nextStep) {
            const nextId = option.action.nextStep;
            if (!visited.has(nextId) && steps[nextId]) {
              queue.push({id: nextId, level: level + 1});
            }
          }
        });
      }
    }
    
    // Calculate positions for left-to-right layout
    const nodeWidth = 200;
    const nodeHeight = 100;
    const levelWidth = 250;  // Horizontal spacing between levels
    const nodeSpacing = 120; // Vertical spacing between nodes
    const startX = 100;
    const startY = 100;
    
    // Calculate total height needed for proper centering
    const maxNodesInLevel = Math.max(...Object.values(levelCounts));
    const totalHeight = maxNodesInLevel * nodeHeight + (maxNodesInLevel - 1) * nodeSpacing;
    
    Object.entries(levels).forEach(([stepId, level]) => {
      const nodesInLevel = levelCounts[level];
      const levelHeight = nodesInLevel * nodeHeight + (nodesInLevel - 1) * nodeSpacing;
      const startYForLevel = startY + (totalHeight - levelHeight) / 2;
      
      const indexInLevel = Object.entries(levels)
        .filter(([id, l]) => l === level)
        .sort()
        .findIndex(([id]) => id === stepId);
      
      positions[stepId] = {
        x: startX + level * levelWidth,  // Left to right
        y: startYForLevel + indexInLevel * (nodeHeight + nodeSpacing)  // Top to bottom within level
      };
    });
    
    return positions;
  }

  createFlowchartNode(step, x, y) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', `flow-node ${step.type}`);
    group.setAttribute('transform', `translate(${x},${y})`);
    
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
    
    // Split long text into multiple lines
    const title = step.title || step.id;
    const words = title.split(' ');
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
    
    // Add click handler
    group.addEventListener('click', () => {
      this.showView('builder');
      this.editStep(step.id);
    });
    
    return group;
  }

  createConnection(fromPos, toPos, label, isRecommendation = false) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    
    // Calculate connection points for left-to-right layout
    const fromX = fromPos.x + 180; // Right edge of source node
    const fromY = fromPos.y + 40;  // Middle of source node
    const toX = toPos.x;           // Left edge of target node
    const toY = toPos.y + 40;      // Middle of target node
    
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
      <h4 style="margin: 0 0 8px 0; font-size: 14px;">Step Types</h4>
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
        <div class="legend-color protocol-info"></div>
        <span>Protocol Info</span>
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
    const svg = document.getElementById('flowchartSvg');
    const content = svg.querySelector('g') || svg;
    if (content !== svg) {
      content.setAttribute('transform', `translate(${this.currentPan.x}, ${this.currentPan.y}) scale(${this.currentZoom})`);
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
}

// Initialize the builder when DOM is loaded
let builder;
document.addEventListener('DOMContentLoaded', () => {
  builder = new DecisionTreeBuilder();
});