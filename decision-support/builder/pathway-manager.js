// ==========================================================================
// Pathway Library Management Functions
// ==========================================================================

// Add to DecisionTreeBuilder class
const PathwayManager = {
  pathways: [],
  filteredPathways: [],
  currentTree: null,
  isLoading: false,
  hasError: false,
  
  async loadPathways() {
    try {
      console.log('Loading pathways...');
      
      // Set loading state
      this.isLoading = true;
      this.hasError = false;
      
      // Show loading spinner
      this.showLoadingState();
      
      // Try API first
      if (await window.pathwayAPI.isAPIAvailable()) {
        console.log('Using API to load pathways');
        const pathways = await window.pathwayAPI.getPathways();
        this.pathways = pathways;
        this.filteredPathways = [...pathways];
        this.filterPathways(); // Apply current filter state and render
        console.log('Pathways loaded from API, count:', this.pathways.length);
      } else {
        // Fallback to file-based system
        console.log('Falling back to file-based system');
        const response = await fetch('../pathways/manifest.json');
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const manifest = await response.json();
        console.log('Loaded manifest:', manifest);
        
        this.pathways = manifest;
        this.filteredPathways = [...manifest];
        this.filterPathways(); // Apply current filter state and render
        console.log('Pathways loaded from files, count:', this.pathways.length);
      }
    } catch (error) {
      console.error('Error loading pathways:', error);
      this.hasError = true;
      this.pathways = [];
      this.filteredPathways = [];
      this.renderPathwaysList(); // Still render to show error state
    } finally {
      // Clear loading state and hide spinner
      this.isLoading = false;
      this.hideLoadingState();
      
      // Render pathways now that loading is complete
      this.renderPathwaysList();
    }
  },

  showLoadingState() {
    const loadingElement = document.getElementById('pathwaysLoading');
    if (loadingElement) {
      loadingElement.style.display = 'flex';
    }
  },

  hideLoadingState() {
    const loadingElement = document.getElementById('pathwaysLoading');
    if (loadingElement) {
      loadingElement.style.display = 'none';
    }
  },

  renderPathwaysList() {
    console.log('Rendering pathways list...');
    const container = document.getElementById('pathwaysList');
    if (!container) {
      console.error('pathwaysList container not found');
      return;
    }

    console.log('Filtered pathways:', this.filteredPathways);
    
    // Don't show empty state if we're still loading
    if (this.isLoading) {
      return; // Let the spinner handle the loading state
    }
    
    if (this.filteredPathways.length === 0) {
      if (this.hasError) {
        container.innerHTML = '<div class="empty-state">Failed to load pathways. Please check your connection and try refreshing.</div>';
      } else {
        container.innerHTML = '<div class="empty-state">No pathways found. Create your first pathway to get started.</div>';
      }
      return;
    }

    // Sort pathways by date (newest first)
    const sortedPathways = [...this.filteredPathways].sort((a, b) => 
      new Date(b.lastModified) - new Date(a.lastModified)
    );

    // Check if we should show sections (when "all" filter is selected)
    const statusFilter = document.getElementById('statusFilter').value;
    const showSections = statusFilter === 'all';

    let html = '';

    if (showSections) {
      // Group pathways by status
      const drafts = sortedPathways.filter(p => p.status === 'draft');
      const published = sortedPathways.filter(p => p.status === 'published');

      // Render drafts section
      if (drafts.length > 0) {
        html += '<div class="pathway-section"><h2 class="section-title">Drafts</h2>';
        html += drafts.map(pathway => this.renderPathwayItem(pathway)).join('');
        html += '</div>';
      }

      // Render published section
      if (published.length > 0) {
        html += '<div class="pathway-section"><h2 class="section-title">Published</h2>';
        html += published.map(pathway => this.renderPathwayItem(pathway)).join('');
        html += '</div>';
      }
    } else {
      // Single list without sections
      html = sortedPathways.map(pathway => this.renderPathwayItem(pathway)).join('');
    }

    container.innerHTML = html;

    // Bind action buttons
    container.querySelectorAll('.pathway-delete').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent card click
        this.deletePathway(e.target.dataset.filename);
      });
    });
    
    container.querySelectorAll('.pathway-publish').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent card click
        this.publishPathway(e.target.dataset.filename);
      });
    });
    
    container.querySelectorAll('.pathway-unpublish').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent card click
        this.unpublishPathway(e.target.dataset.filename);
      });
    });
    
    // Make entire card clickable to edit pathway
    container.querySelectorAll('.pathway-item-clickable').forEach(card => {
      card.addEventListener('click', (e) => {
        // Don't trigger if any action button was clicked
        if (e.target.closest('.pathway-actions-container')) return;
        
        // Check if pathway is published
        const pathway = this.pathways.find(p => p.filename === card.dataset.filename);
        if (pathway && pathway.status === 'published') {
          this.previewPathway(card.dataset.filename);
        } else {
          this.editPathway(card.dataset.filename);
        }
      });
      card.style.cursor = 'pointer';
    });
  },

  renderPathwayItem(pathway) {
    return `
      <div class="pathway-item pathway-item-clickable" data-id="${pathway.id}" data-filename="${pathway.filename}">
        <span class="status-badge status-${pathway.status} pathway-status-badge">${pathway.status}</span>
        <div class="pathway-main">
          <div class="pathway-header">
            <h3 class="pathway-title">${pathway.title}</h3>
          </div>
          <div class="pathway-description">${pathway.description}</div>
          <div class="pathway-meta">
            <span class="pathway-steps">${pathway.stepCount} steps</span>
            <span class="pathway-modified">${this.formatDate(pathway.lastModified)}</span>
          </div>
        </div>
        <div class="pathway-actions-container">
          ${pathway.status === 'draft' 
            ? `<button class="btn btn-sm btn-success pathway-publish" data-filename="${pathway.filename}">Publish</button>`
            : `<button class="btn btn-sm btn-warning pathway-unpublish" data-filename="${pathway.filename}">Unpublish</button>`
          }
          ${pathway.status === 'draft' 
            ? `<button class="btn btn-sm btn-danger pathway-delete" data-filename="${pathway.filename}">Delete</button>`
            : ''
          }
        </div>
      </div>
    `;
  },

  async createPathway() {
    const id = prompt('Enter pathway ID:');
    if (!id) return;
    
    const title = prompt('Enter pathway title:');
    if (!title) return;

    const description = prompt('Enter pathway description:') || '';

    const newPathway = {
      id,
      title,
      description,
      startStep: '',
      guides: [],
      steps: {}
    };

    this.currentTree = newPathway;
    
    // Show builder tab for new pathways
    const builderTab = document.getElementById('builderTab');
    if (builderTab) {
      builderTab.style.display = 'block';
    }
    
    this.showView('builder');
    // Reset save draft state for new pathway
    this.captureInitialTreeState();
  },

  async editPathway(filename) {
    try {
      console.log('Loading pathway:', filename);
      
      // Extract pathway ID from filename
      const pathwayId = filename.replace('.json', '').replace('_draft', '').replace('_published', '');
      
      let pathway;
      
      // Try API first
      if (await window.pathwayAPI.isAPIAvailable()) {
        pathway = await window.pathwayAPI.getPathway(pathwayId);
      } else {
        // Fallback to file-based system
        const response = await fetch(`../pathways/${filename}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        pathway = await response.json();
      }
      
      console.log('Loaded pathway data:', pathway);
      
      this.currentTree = pathway;
      
      // Show builder tab for draft pathways
      const builderTab = document.getElementById('builderTab');
      if (builderTab) {
        builderTab.style.display = 'block';
      }
      
      this.showView('builder');
      // Need to update UI after view is shown
      setTimeout(() => {
        this.updateUI(); // Update the builder UI with loaded data
        this.updateTreeProperties(); // Ensure form fields are populated
        this.captureInitialTreeState(); // Reset save draft state for loaded pathway
      }, 100);
    } catch (error) {
      console.error('Error loading pathway:', error);
      alert(`Error loading pathway: ${error.message}`);
    }
  },

  async previewPathway(filename) {
    try {
      console.log('Loading pathway for preview:', filename);
      
      // Extract pathway ID from filename
      const pathwayId = filename.replace('.json', '').replace('_draft', '').replace('_published', '');
      
      let pathway;
      
      // Try API first
      if (await window.pathwayAPI.isAPIAvailable()) {
        pathway = await window.pathwayAPI.getPathway(pathwayId);
      } else {
        // Fallback to file-based system
        const response = await fetch(`../pathways/${filename}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        pathway = await response.json();
      }
      
      console.log('Loaded pathway data for preview:', pathway);
      
      this.currentTree = pathway;
      
      // Hide builder tab for published pathways
      const builderTab = document.getElementById('builderTab');
      if (builderTab) {
        builderTab.style.display = 'none';
      }
      
      // Show preview tab
      this.showView('preview');
      
      // Need to update UI after view is shown
      setTimeout(() => {
        this.updateUI(); // Update the builder UI with loaded data
        this.updateTreeProperties(); // Ensure form fields are populated
        this.captureInitialTreeState(); // Reset save draft state for loaded pathway
      }, 100);
    } catch (error) {
      console.error('Error loading pathway for preview:', error);
      alert(`Error loading pathway: ${error.message}`);
    }
  },

  async publishPathway(filename) {
    if (!confirm('Publish this pathway? It will be available to all users.')) return;
    
    try {
      // Extract pathway ID from filename
      const pathwayId = filename.replace('.json', '').replace('_draft', '').replace('_published', '');
      
      // Show loading state
      this.isLoading = true;
      this.showLoadingState();
      
      // Try API first
      if (await window.pathwayAPI.isAPIAvailable()) {
        console.log('Publishing pathway via API:', pathwayId);
        const result = await window.pathwayAPI.publishPathway(pathwayId);
        console.log('API publish response:', result);
        
        // Wait for successful response before reloading
        if (result) {
          console.log('Publish confirmed, reloading pathways...');
          await this.loadPathways(); // Reload fresh data - this handles rendering internally
        } else {
          throw new Error('API did not confirm successful publish');
        }
      } else {
        console.log('Publishing pathway via file system:', filename);
        // Fallback to file-based system
        const pathway = this.pathways.find(p => p.filename === filename);
        if (pathway) {
          pathway.status = 'published';
          await this.updateManifest();
          this.filterPathways(); // Apply current filter and re-render
        }
      }
      
      console.log('Pathway published successfully, list refreshed');
    } catch (error) {
      console.error('Error publishing pathway:', error);
      alert(`Error publishing pathway: ${error.message}`);
    } finally {
      // Hide loading state
      this.isLoading = false;
      this.hideLoadingState();
    }
  },

  async unpublishPathway(filename) {
    if (!confirm('Unpublish this pathway? It will no longer be available to users.')) return;
    
    try {
      // Extract pathway ID from filename
      const pathwayId = filename.replace('.json', '').replace('_draft', '').replace('_published', '');
      
      // Show loading state
      this.isLoading = true;
      this.showLoadingState();
      
      // Try API first
      if (await window.pathwayAPI.isAPIAvailable()) {
        console.log('Unpublishing pathway via API:', pathwayId);
        const result = await window.pathwayAPI.unpublishPathway(pathwayId);
        console.log('API unpublish response:', result);
        
        // Wait for successful response before reloading
        if (result) {
          console.log('Unpublish confirmed, reloading pathways...');
          await this.loadPathways(); // Reload fresh data - this handles rendering internally
        } else {
          throw new Error('API did not confirm successful unpublish');
        }
      } else {
        console.log('Unpublishing pathway via file system:', filename);
        // Fallback to file-based system
        const pathway = this.pathways.find(p => p.filename === filename);
        if (pathway) {
          pathway.status = 'draft';
          await this.updateManifest();
          this.filterPathways(); // Apply current filter and re-render
        }
      }
      
      console.log('Pathway unpublished successfully, list refreshed');
    } catch (error) {
      console.error('Error unpublishing pathway:', error);
      alert(`Error unpublishing pathway: ${error.message}`);
    } finally {
      // Hide loading state
      this.isLoading = false;
      this.hideLoadingState();
    }
  },

  async deletePathway(filename) {
    if (!confirm('Delete this pathway permanently? This cannot be undone.')) return;
    
    try {
      // Extract pathway ID from filename
      const pathwayId = filename.replace('.json', '').replace('_draft', '').replace('_published', '');
      
      // Try API first
      if (await window.pathwayAPI.isAPIAvailable()) {
        await window.pathwayAPI.deletePathway(pathwayId);
        await this.loadPathways(); // Reload to get updated data
      } else {
        // Fallback to file-based system
        this.pathways = this.pathways.filter(p => p.filename !== filename);
        await this.updateManifest();
        this.loadPathways();
      }
    } catch (error) {
      console.error('Error deleting pathway:', error);
      alert(`Error deleting pathway: ${error.message}`);
    }
  },

  filterPathways() {
    const statusFilter = document.getElementById('statusFilter').value;
    const searchFilter = document.getElementById('searchFilter').value.toLowerCase();

    this.filteredPathways = this.pathways.filter(pathway => {
      const matchesStatus = statusFilter === 'all' || pathway.status === statusFilter;
      const matchesSearch = !searchFilter || 
        pathway.title.toLowerCase().includes(searchFilter) ||
        pathway.description.toLowerCase().includes(searchFilter);
      
      return matchesStatus && matchesSearch;
    });

    this.renderPathwaysList();
  },

  async updateManifest() {
    // In a real implementation, this would send to a server
    // For now, we'll just update the local data
    console.log('Manifest updated:', this.pathways);
  },

  async updateManifestEntry(filename, status) {
    // Create or update manifest entry for the pathway
    const stepCount = Object.keys(this.currentTree.steps || {}).length;
    const guideCount = (this.currentTree.guides || []).length;
    
    const existingIndex = this.pathways.findIndex(p => p.id === this.currentTree.id);
    
    const manifestEntry = {
      filename: filename,
      id: this.currentTree.id,
      title: this.currentTree.title,
      description: this.currentTree.description || '',
      stepCount: stepCount,
      guideCount: guideCount,
      status: status,
      lastModified: new Date().toISOString(),
      size: JSON.stringify(this.currentTree).length
    };

    if (existingIndex >= 0) {
      this.pathways[existingIndex] = manifestEntry;
    } else {
      this.pathways.push(manifestEntry);
    }

    // Download updated manifest
    const manifestStr = JSON.stringify(this.pathways, null, 2);
    const manifestBlob = new Blob([manifestStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(manifestBlob);
    link.download = 'manifest.json';
    link.click();
    
    console.log('Manifest entry updated:', manifestEntry);
  },


  formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
  }
};

// Extend DecisionTreeBuilder with pathway management
Object.assign(DecisionTreeBuilder.prototype, PathwayManager);