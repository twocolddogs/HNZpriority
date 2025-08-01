// ==========================================================================
// HNZ Decision Tree Renderer
// Universal rendering engine for decision trees
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
    
    // Create header
    const header = this.createHeader();
    this.container.appendChild(header);

    // Create main content area
    const content = document.createElement('div');
    content.className = 'decision-content';
    content.id = 'decisionContent';
    this.container.appendChild(content);

    // Render current step
    this.renderStep();

    return this.container;
  }

  createHeader() {
    const header = document.createElement('div');
    header.className = 'decision-header';
    
    const title = document.createElement('h1');
    title.className = 'decision-title';
    title.textContent = this.treeData.title;
    
    header.appendChild(title);
    
    if (this.treeData.description) {
      const description = document.createElement('p');
      description.className = 'decision-description';
      description.textContent = this.treeData.description;
      header.appendChild(description);
    }
    
    return header;
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
      title.textContent = step.title || 'Clinical Recommendation';
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
      description.className = 'step-description markdown-content';
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
    
    // Map yes/no button variants for better styling
    let variant = option.variant || 'primary';
    if (step.type === 'yes-no') {
      if (option.text.toLowerCase() === 'yes' || variant === 'success') {
        variant = 'yes';
      } else if (option.text.toLowerCase() === 'no' || variant === 'secondary') {
        variant = 'no';
      }
    }
    
    button.className = `decision-button ${variant}`;
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
      // Check if navigating back to start step (pathway completion)
      if (action.nextStep === this.treeData.startStep && this.currentStep !== this.treeData.startStep) {
        // Show completion popup
        alert('🎉 Pathway Complete!\n\nYou have completed this decision pathway and will now be taken back to the beginning to start again.');
      }
      
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
    
    
    if (this.recommendation) {
      const recommendationCard = this.createRecommendationCard(this.recommendation);
      stepCard.appendChild(recommendationCard);
    }
    
    container.appendChild(stepCard);
  }

  createRecommendationCard(rec) {
    const container = document.createElement('div');
    container.className = 'recommendation-card';
    
    const details = document.createElement('div');
    details.className = 'recommendation-details';
    
    // Main recommendation text
    if (rec.recommendation) {
      const recommendationDetail = document.createElement('div');
      recommendationDetail.className = 'recommendation-detail recommendation-main markdown-content';
      recommendationDetail.innerHTML = this.parseCallouts(rec.recommendation);
      details.appendChild(recommendationDetail);
    }
    
    // Additional notes
    if (rec.notes) {
      const notesDetail = document.createElement('div');
      notesDetail.className = 'recommendation-detail recommendation-notes markdown-content';
      notesDetail.innerHTML = '<strong>Additional Notes:</strong><br>' + this.parseCallouts(rec.notes);
      details.appendChild(notesDetail);
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
    // Create modal if it doesn't exist
    let modal = document.getElementById('protocolModal');
    if (!modal) {
      modal = this.createProtocolModal();
      document.body.appendChild(modal);
    }
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  createProtocolModal() {
    const modal = document.createElement('div');
    modal.id = 'protocolModal';
    modal.className = 'modal-overlay hidden';
    
    const modalContainer = document.createElement('div');
    modalContainer.className = 'modal-container protocol-modal';
    
    const modalHeader = document.createElement('div');
    modalHeader.className = 'modal-header';
    
    const title = document.createElement('h3');
    title.className = 'modal-title';
    title.textContent = 'Reference Guide';
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'modal-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => this.hideProtocolModal());
    
    modalHeader.appendChild(title);
    modalHeader.appendChild(closeBtn);
    
    const modalBody = document.createElement('div');
    modalBody.className = 'modal-body';
    
    // Add guides content
    this.treeData.guides.forEach(guide => {
      const guideSection = this.createGuideSection(guide);
      modalBody.appendChild(guideSection);
    });
    
    modalContainer.appendChild(modalHeader);
    modalContainer.appendChild(modalBody);
    modal.appendChild(modalContainer);
    
    // Close on overlay click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        this.hideProtocolModal();
      }
    });
    
    return modal;
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
      
      const content = document.createElement('div');
      content.className = 'markdown-content';
      content.innerHTML = this.parseCallouts(sectionData.content);
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

  parseCallouts(text) {
    if (!text) return '';
    
    // First parse markdown, then callouts
    let processedText = this.parseMarkdown(text);
    
    // Parse callout syntax: [type]content[/type]
    const calloutRegex = /\[(guide|info|warning|success|danger)\](.*?)\[\/\1\]/g;
    
    return processedText.replace(calloutRegex, (match, type, content) => {
      return `<div class="step-callout step-callout-${type}">${this.parseMarkdown(content.trim())}</div>`;
    });
  }

  parseMarkdown(text) {
    if (!text) return '';
    
    // Simple markdown parsing for common elements
    let result = text;
    
    // Bold: **text** or __text__
    result = result.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    result = result.replace(/__(.*?)__/g, '<strong>$1</strong>');
    
    // Italic: *text* or _text_
    result = result.replace(/\*(.*?)\*/g, '<em>$1</em>');
    result = result.replace(/_(.*?)_/g, '<em>$1</em>');
    
    // Inline code: `text`
    result = result.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Line breaks
    result = result.replace(/\n/g, '<br>');
    
    // Lists - handle bullet points
    const lines = result.split('<br>');
    let inList = false;
    let listItems = [];
    let processedLines = [];
    
    for (let line of lines) {
      const trimmed = line.trim();
      
      // Check for bullet point (*, -, •, or number.)
      if (trimmed.match(/^[\*\-•]\s/) || trimmed.match(/^\d+\.\s/)) {
        const isNumbered = trimmed.match(/^\d+\.\s/);
        const content = trimmed.replace(/^[\*\-•]\s/, '').replace(/^\d+\.\s/, '');
        
        if (!inList) {
          inList = true;
          listItems = [];
        }
        
        listItems.push({
          content: content,
          isNumbered: isNumbered
        });
      } else if (inList && trimmed === '') {
        // Empty line continues the list
        continue;
      } else {
        // End of list or non-list line
        if (inList) {
          const isNumbered = listItems.length > 0 && listItems[0].isNumbered;
          const tag = isNumbered ? 'ol' : 'ul';
          const listHtml = `<${tag}>` + 
            listItems.map(item => `<li>${item.content}</li>`).join('') + 
            `</${tag}>`;
          processedLines.push(listHtml);
          inList = false;
          listItems = [];
        }
        
        if (trimmed !== '') {
          processedLines.push(line);
        }
      }
    }
    
    // Handle any remaining list
    if (inList) {
      const isNumbered = listItems.length > 0 && listItems[0].isNumbered;
      const tag = isNumbered ? 'ol' : 'ul';
      const listHtml = `<${tag}>` + 
        listItems.map(item => `<li>${item.content}</li>`).join('') + 
        `</${tag}>`;
      processedLines.push(listHtml);
    }
    
    return processedLines.join('<br>');
  }

  hideProtocolModal() {
    const modal = document.getElementById('protocolModal');
    if (modal) {
      modal.classList.add('hidden');
      document.body.style.overflow = 'auto';
    }
  }
}

// Make renderer available globally
window.DecisionTreeRenderer = DecisionTreeRenderer;