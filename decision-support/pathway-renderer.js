// ==========================================================================
// HNZ Decision Support - Pathway Renderer
// Loads and renders individual decision support pathways
// ==========================================================================

class DecisionTreeRenderer {
  constructor(treeData) {
    this.treeData = treeData;
    this.currentStep = treeData.startStep;
    this.stepHistory = [treeData.startStep];
    this.answers = {};
    this.recommendation = null;
  }

  render() {
    this.container = document.createElement('div');
    this.container.className = 'decision-tree-container';
    
    // Create main content area (no header since it's in the page)
    const content = document.createElement('div');
    content.className = 'decision-content';
    content.id = 'decisionContent';
    this.container.appendChild(content);

    // Render current step
    this.renderStep();

    return this.container;
  }

  renderStep() {
    const content = this.container.querySelector('#decisionContent');
    if (!content) {
      console.error('Decision content container not found');
      return;
    }
    
    content.innerHTML = '';
    
    if (this.currentStep === 'result') {
      this.renderResult(content);
    } else {
      const step = this.treeData.steps[this.currentStep];
      if (!step) {
        content.innerHTML = '<div class="error">Step not found: ' + this.currentStep + '</div>';
        return;
      }
      
      this.renderStepContent(content, step);
    }
    
    // Add navigation controls
    if (this.currentStep !== this.treeData.startStep || this.currentStep === 'result') {
      const navContainer = this.createNavigationContainer();
      content.appendChild(navContainer);
    }
    
    // Add protocol reference if guides exist
    if (this.treeData.guides && this.treeData.guides.length > 0) {
      const protocolRef = this.createProtocolReference();
      content.appendChild(protocolRef);
    }
  }

  renderStepContent(container, step) {
    console.log('Rendering step:', step);
    
    // Handle endpoint steps as recommendation cards
    if (step.type === 'endpoint' && step.recommendation) {
      const stepCard = document.createElement('div');
      stepCard.className = 'step-card step-card-endpoint';
      
      // Title
      const title = document.createElement('h2');
      title.className = 'step-title';
      title.textContent = 'Imaging Recommendation';
      stepCard.appendChild(title);
      
      // Render recommendation card
      const recommendationCard = this.createRecommendationCard(step.recommendation);
      stepCard.appendChild(recommendationCard);
      
      container.appendChild(stepCard);
      return;
    }
    
    // Regular step rendering
    const stepCard = document.createElement('div');
    stepCard.className = `step-card step-card-${step.type || 'choice'}`;
    
    // Title
    const title = document.createElement('h2');
    title.className = 'step-title';
    title.textContent = step.title;
    stepCard.appendChild(title);
    
    // Subtitle
    if (step.subtitle) {
      const subtitle = document.createElement('p');
      subtitle.className = 'step-subtitle';
      subtitle.textContent = step.subtitle;
      stepCard.appendChild(subtitle);
    }
    
    // Guide info
    if (step.guideInfo) {
      const guideInfo = this.createGuideInfo(step.guideInfo);
      stepCard.appendChild(guideInfo);
    }
    
    // Description (with callout parsing)
    if (step.question) {
      const description = document.createElement('div');
      description.className = 'step-description';
      description.innerHTML = this.parseCallouts(step.question);
      stepCard.appendChild(description);
    }
    
    // Options
    if (step.options && step.options.length > 0) {
      console.log('Adding options:', step.options);
      const optionsContainer = this.createOptionsContainer(step);
      stepCard.appendChild(optionsContainer);
    } else {
      console.log('No options found for step');
    }
    
    container.appendChild(stepCard);
  }

  createOptionsContainer(step) {
    const container = document.createElement('div');
    container.className = step.type === 'yes-no' ? 'button-row' : 'button-group';
    
    step.options.forEach(option => {
      const button = this.createButton(option, step);
      container.appendChild(button);
    });
    
    return container;
  }

  createButton(option, step) {
    const button = document.createElement('button');
    button.className = `decision-button ${option.variant || 'primary'}`;
    button.textContent = option.text;
    
    button.addEventListener('click', () => {
      this.handleAnswer(step.id, option.text, option.action);
    });
    
    return button;
  }

  createGuideInfo(guideInfo) {
    const container = document.createElement('div');
    container.className = 'guide-info';
    
    const title = document.createElement('h4');
    title.textContent = guideInfo.title;
    container.appendChild(title);
    
    const description = document.createElement('p');
    description.textContent = guideInfo.description;
    container.appendChild(description);
    
    if (guideInfo.note) {
      const note = document.createElement('div');
      note.className = 'guide-note';
      const noteP = document.createElement('p');
      noteP.innerHTML = `<strong>Note:</strong> ${guideInfo.note}`;
      note.appendChild(noteP);
      container.appendChild(note);
    }
    
    return container;
  }

  handleAnswer(stepId, answer, action) {
    this.answers[stepId] = answer;
    
    if (action.type === 'navigate') {
      this.currentStep = action.nextStep;
      this.stepHistory.push(action.nextStep);
    } else if (action.type === 'recommend') {
      this.recommendation = action.recommendation;
      this.currentStep = 'result';
      this.stepHistory.push('result');
    }
    
    this.renderStep();
  }

  renderResult(container) {
    const stepCard = document.createElement('div');
    stepCard.className = 'step-card';
    
    const title = document.createElement('h2');
    title.className = 'step-title';
    title.textContent = 'Imaging Recommendation';
    stepCard.appendChild(title);
    
    if (this.recommendation) {
      const recommendationCard = this.createRecommendationCard(this.recommendation);
      stepCard.appendChild(recommendationCard);
    }
    
    container.appendChild(stepCard);
  }

  createRecommendationCard(rec) {
    const container = document.createElement('div');
    container.className = 'recommendation-card';
    
    const header = document.createElement('div');
    header.className = 'recommendation-header';
    
    const icon = document.createElement('span');
    icon.className = 'recommendation-icon';
    icon.innerHTML = '✓';
    
    const title = document.createElement('h3');
    title.className = 'recommendation-title';
    title.textContent = 'Recommended Imaging';
    
    header.appendChild(icon);
    header.appendChild(title);
    container.appendChild(header);
    
    const details = document.createElement('div');
    details.className = 'recommendation-details';
    
    const modalityDetail = document.createElement('div');
    modalityDetail.className = 'recommendation-detail';
    modalityDetail.innerHTML = '<strong>Modality:</strong> <span>' + rec.modality + '</span>';
    
    const contrastDetail = document.createElement('div');
    contrastDetail.className = 'recommendation-detail';
    contrastDetail.innerHTML = '<strong>Contrast:</strong> <span>' + rec.contrast + '</span>';
    
    details.appendChild(modalityDetail);
    details.appendChild(contrastDetail);
    
    if (rec.notes) {
      const notesDetail = document.createElement('div');
      notesDetail.className = 'recommendation-detail';
      notesDetail.innerHTML = '<strong>Notes:</strong> <span>' + rec.notes + '</span>';
      details.appendChild(notesDetail);
    }
    
    if (rec.priority) {
      const priorityDetail = document.createElement('div');
      priorityDetail.className = 'recommendation-detail';
      priorityDetail.innerHTML = '<strong>Priority:</strong> <span>' + rec.priority + '</span>';
      details.appendChild(priorityDetail);
    }
    
    container.appendChild(details);
    return container;
  }

  createNavigationContainer() {
    const navContainer = document.createElement('div');
    navContainer.className = 'external-navigation-controls';
    
    // Back button
    if (this.stepHistory.length > 1) {
      const backBtn = document.createElement('button');
      backBtn.className = 'decision-button secondary small';
      backBtn.innerHTML = '<span class="button-icon">←</span><span>Back</span>';
      backBtn.addEventListener('click', () => this.goBack());
      navContainer.appendChild(backBtn);
    }
    
    // Start over button
    const resetBtn = document.createElement('button');
    resetBtn.className = 'decision-button secondary small';
    resetBtn.innerHTML = '<span class="button-icon">↻</span><span>Start Over</span>';
    resetBtn.addEventListener('click', () => this.resetTool());
    navContainer.appendChild(resetBtn);
    
    return navContainer;
  }

  createProtocolReference() {
    const container = document.createElement('div');
    container.className = 'protocol-reference-container';
    
    const button = document.createElement('button');
    button.className = 'decision-button protocol-reference full-width';
    button.textContent = 'View Reference Guide';
    button.addEventListener('click', () => this.showProtocolModal());
    
    container.appendChild(button);
    return container;
  }

  goBack() {
    if (this.stepHistory.length > 1) {
      this.stepHistory.pop();
      const previousStep = this.stepHistory[this.stepHistory.length - 1];
      this.currentStep = previousStep;
      this.recommendation = null;
      this.renderStep();
    }
  }

  resetTool() {
    this.currentStep = this.treeData.startStep;
    this.stepHistory = [this.treeData.startStep];
    this.answers = {};
    this.recommendation = null;
    this.renderStep();
  }

  showProtocolModal() {
    const modal = document.getElementById('protocolModal');
    const protocolContent = document.getElementById('protocolContent');
    
    if (modal && protocolContent) {
      protocolContent.innerHTML = '';
      
      // Render guides content
      this.treeData.guides.forEach(guide => {
        const guideSection = this.createGuideSection(guide);
        protocolContent.appendChild(guideSection);
      });
      
      modal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
    }
  }

  parseCallouts(text) {
    if (!text) return '';
    
    // Parse callout syntax: [type]content[/type]
    const calloutRegex = /\[(protocol|guide|info|warning|success|danger)\](.*?)\[\/\1\]/g;
    
    return text.replace(calloutRegex, (match, type, content) => {
      return `<div class="step-callout step-callout-${type}">${content.trim()}</div>`;
    });
  }

  createGuideSection(guide) {
    const section = document.createElement('div');
    section.className = 'protocol-section';
    
    guide.sections.forEach(sectionData => {
      const card = document.createElement('div');
      card.className = `protocol-card ${sectionData.type || 'info'}`;
      
      const title = document.createElement('h4');
      title.textContent = sectionData.title;
      card.appendChild(title);
      
      const content = document.createElement('p');
      content.textContent = sectionData.content;
      card.appendChild(content);
      
      if (sectionData.items && sectionData.items.length > 0) {
        const list = document.createElement('ul');
        sectionData.items.forEach(item => {
          const listItem = document.createElement('li');
          listItem.textContent = item;
          list.appendChild(listItem);
        });
        card.appendChild(list);
      }
      
      section.appendChild(card);
    });
    
    return section;
  }
}

// Pathway Page Controller
class PathwayPage {
  constructor() {
    this.pathwayId = null;
    this.pathwayData = null;
    this.renderer = null;
    this.init();
  }

  init() {
    // Get pathway ID from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    this.pathwayId = urlParams.get('id');
    
    if (!this.pathwayId) {
      this.showError('No pathway specified');
      return;
    }

    this.loadPathway();
    this.bindEvents();
  }

  async loadPathway() {
    try {
      console.log(`Loading pathway: ${this.pathwayId}`);
      
      // Try API first
      if (await this.isAPIAvailable()) {
        console.log('Loading pathway from API');
        const response = await fetch(`https://hnz-pathway-api.alistair-rumball-smith.workers.dev/api/pathways/${this.pathwayId}`);
        
        if (response.ok) {
          this.pathwayData = await response.json();
          console.log('Successfully loaded pathway from API:', this.pathwayData);
          this.renderPathway();
          return;
        } else {
          console.warn(`API pathway not found: ${response.status} ${response.statusText}`);
        }
      }
      
      // Fallback to file-based system
      console.log('Falling back to file-based pathway loading');
      try {
        const response = await fetch(`pathways/${this.pathwayId}.json`);
        if (!response.ok) {
          throw new Error(`Failed to load pathway: ${response.status} ${response.statusText}`);
        }
        
        this.pathwayData = await response.json();
        console.log('Successfully loaded pathway data from file:', this.pathwayData);
      } catch (fetchError) {
        console.warn('Failed to fetch pathway file, trying embedded fallback:', fetchError);
        
        // Fallback to embedded data
        if (this.pathwayId === 'liver-imaging-example' || this.pathwayId === 'liver-imaging-decision-tool') {
          this.pathwayData = this.getEmbeddedLiverPathway();
          console.log('Using embedded pathway data');
        } else {
          throw new Error(`Pathway not found: ${this.pathwayId}`);
        }
      }
      
      this.renderPathway();
      
    } catch (error) {
      console.error('Error loading pathway:', error);
      this.showError(`Unable to load pathway: ${error.message}`);
    }
  }

  async isAPIAvailable() {
    try {
      const response = await fetch('https://hnz-pathway-api.alistair-rumball-smith.workers.dev/api/published-pathways');
      return response.ok;
    } catch (error) {
      console.warn('API availability check failed:', error);
      return false;
    }
  }

  getEmbeddedLiverPathway() {
    // Same embedded data as in home.js
    return {
      "id": "liver-imaging-decision-tool",
      "title": "HNZ Liver Imaging Decision Support Tool",
      "description": "Interactive guide for selecting appropriate imaging modality and contrast",
      "startStep": "start",
      "guides": [
        {
          "id": "protocol-guide",
          "title": "Reference Guide",
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
                "type": "recommend",
                "recommendation": {
                  "modality": "MRI liver",
                  "contrast": "with Gadovist (in line with Auckland unless specified by MDM)",
                  "notes": "Direct pathway for cirrhosis/risk factors with no other malignancy suspected"
                }
              }
            },
            {
              "text": "Known liver malignancy or suspicion of malignancy",
              "variant": "primary",
              "action": {
                "type": "navigate",
                "nextStep": "malignancy-assessment"
              }
            },
            {
              "text": "Gallbladder or biliary assessment",
              "variant": "primary",
              "action": {
                "type": "navigate",
                "nextStep": "gallbladder-assessment"
              }
            }
          ]
        },
        "malignancy-assessment": {
          "id": "malignancy-assessment",
          "title": "Malignancy Assessment",
          "question": "Is there evidence of malignancy on prior imaging?",
          "type": "yes-no",
          "options": [
            {
              "text": "Yes",
              "variant": "primary",
              "action": {
                "type": "recommend",
                "recommendation": {
                  "modality": "MRI liver",
                  "contrast": "with Primovist",
                  "notes": "Primovist recommended for confirmed or suspected malignancy"
                }
              }
            },
            {
              "text": "No",
              "variant": "secondary",
              "action": {
                "type": "navigate",
                "nextStep": "lesion-type"
              }
            }
          ]
        },
        "lesion-type": {
          "id": "lesion-type",
          "title": "Lesion Characterization",
          "question": "What type of liver lesion is suspected?",
          "type": "choice",
          "options": [
            {
              "text": "Solid or complex liver lesion",
              "variant": "primary",
              "action": {
                "type": "recommend",
                "recommendation": {
                  "modality": "MRI liver",
                  "contrast": "with Primovist",
                  "notes": "Solid/complex lesions require Primovist for optimal characterization"
                }
              }
            },
            {
              "text": "Question of haemangioma with no other malignancy",
              "variant": "primary",
              "action": {
                "type": "recommend",
                "recommendation": {
                  "modality": "MRI liver",
                  "contrast": "with Dotarem or Gadovist",
                  "notes": "Standard contrast adequate for haemangioma characterization"
                }
              }
            }
          ]
        },
        "gallbladder-assessment": {
          "id": "gallbladder-assessment",
          "title": "Gallbladder Assessment",
          "question": "Is malignancy suspected in gallbladder lesions?",
          "type": "yes-no",
          "options": [
            {
              "text": "Yes",
              "variant": "primary",
              "action": {
                "type": "recommend",
                "recommendation": {
                  "modality": "MRI liver",
                  "contrast": "with Primovist",
                  "notes": "Primovist recommended for suspected gallbladder malignancy"
                }
              }
            },
            {
              "text": "No",
              "variant": "secondary",
              "action": {
                "type": "recommend",
                "recommendation": {
                  "modality": "MRI liver",
                  "contrast": "with Dotarem or Gadovist",
                  "notes": "Standard contrast adequate for benign gallbladder assessment"
                }
              }
            }
          ]
        }
      }
    };
  }

  renderPathway() {
    // Update page title and banner
    document.title = this.pathwayData.title || 'HNZ Decision Support Tool';
    document.getElementById('pathwayTitle').textContent = this.pathwayData.title || 'Decision Support Tool';
    
    // Show subtitle if available
    if (this.pathwayData.description) {
      const subtitleElement = document.getElementById('pathwaySubtitle');
      subtitleElement.textContent = this.pathwayData.description;
      subtitleElement.classList.remove('hidden');
    }

    // Hide loading and show content
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('appContent').classList.remove('hidden');

    // Create and render the decision tree
    this.renderer = new DecisionTreeRenderer(this.pathwayData);
    const renderedTree = this.renderer.render();
    
    document.getElementById('appContent').appendChild(renderedTree);
  }

  showError(message) {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('errorState').classList.remove('hidden');
    document.getElementById('errorMessage').textContent = message;
  }

  bindEvents() {
    // Close protocol modal
    const closeProtocol = document.getElementById('closeProtocol');
    if (closeProtocol) {
      closeProtocol.addEventListener('click', () => {
        document.getElementById('protocolModal').classList.add('hidden');
        document.body.style.overflow = 'auto';
      });
    }

    // Close modal on overlay click
    const protocolModal = document.getElementById('protocolModal');
    if (protocolModal) {
      protocolModal.addEventListener('click', (e) => {
        if (e.target === protocolModal) {
          protocolModal.classList.add('hidden');
          document.body.style.overflow = 'auto';
        }
      });
    }
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new PathwayPage();
});