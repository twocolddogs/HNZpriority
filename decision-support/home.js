// ==========================================================================
// HNZ Decision Support Tools - Home Page
// ==========================================================================

class DecisionSupportHome {
  constructor() {
    this.pathways = [];
    this.init();
  }

  async init() {
    try {
      await this.loadPathways();
      this.renderPathways();
    } catch (error) {
      console.error('Error initializing home page:', error);
      this.showError();
    }
  }

  async discoverPathways() {
    try {
      // Method 1: Try to fetch a manifest file if it exists
      try {
        const manifestResponse = await fetch('pathways/manifest.json');
        if (manifestResponse.ok) {
          const manifest = await manifestResponse.json();
          console.log('Found pathways manifest:', manifest);
          
          // Store manifest data for richer display
          this.pathwaysManifest = manifest;
          
          // Filter out draft pathways from public listing
          return manifest
            .filter(item => item.status !== 'draft')
            .map(item => item.filename);
        }
      } catch (e) {
        console.log('No manifest file found, trying alternative discovery methods');
      }

      // Method 2: Try common pathway filenames based on directory scanning
      const commonPatterns = [
        'liver-imaging-example.json',
        'liver-imaging-example-converted.json',
        'cardiac-imaging.json',
        'brain-imaging.json',
        'chest-imaging.json',
        'pediatric-imaging.json',
        'emergency-imaging.json'
      ];

      const existingFiles = [];
      for (const filename of commonPatterns) {
        try {
          const response = await fetch(`pathways/${filename}`, { method: 'HEAD' });
          if (response.ok) {
            existingFiles.push(filename);
          }
        } catch (e) {
          // File doesn't exist, continue
        }
      }

      return existingFiles;
    } catch (error) {
      console.warn('Pathway discovery failed:', error);
      return [];
    }
  }

  async loadPathways() {
    try {
      console.log('Starting to load pathways...');
      
      // Try API first for published pathways only
      if (await this.isAPIAvailable()) {
        console.log('Loading published pathways from API');
        const response = await fetch('https://hnz-pathway-api.alistair-rumball-smith.workers.dev/api/published-pathways');
        
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        
        const apiPathways = await response.json();
        console.log('API returned pathways:', apiPathways);
        
        // Convert API data to expected format for rendering
        this.pathways = await Promise.all(apiPathways.map(async (pathwayMeta) => {
          try {
            // Fetch the actual pathway data
            const pathwayResponse = await fetch(`https://hnz-pathway-api.alistair-rumball-smith.workers.dev/api/pathways/${pathwayMeta.id}`);
            if (!pathwayResponse.ok) {
              console.warn(`Failed to load pathway data for ${pathwayMeta.id}`);
              return null;
            }
            
            const pathwayData = await pathwayResponse.json();
            return {
              filename: pathwayMeta.filename,
              data: pathwayData,
              lastModified: pathwayMeta.lastModified
            };
          } catch (error) {
            console.warn(`Error loading pathway ${pathwayMeta.id}:`, error);
            return null;
          }
        }));
        
        // Filter out failed loads
        this.pathways = this.pathways.filter(pathway => pathway !== null);
        
        console.log(`Loaded ${this.pathways.length} published pathways from API`);
        
        // If no published pathways, show empty state
        if (this.pathways.length === 0) {
          console.log('No published pathways found via API');
        }
        return;
      }
      
      // Fallback to file-based system
      console.warn('⚠️ API not available, falling back to file-based system - this should not happen in production!');
      
      // Try to discover pathways dynamically first, then fallback to known files
      let pathwayFiles = await this.discoverPathways();
      
      // If discovery fails, fallback to known pathways
      if (pathwayFiles.length === 0) {
        pathwayFiles = [
          'liver-imaging-example.json',
          'liver-imaging-example-converted.json'
        ];
      }

      console.log('Pathway files to load:', pathwayFiles);

      const pathwayPromises = pathwayFiles.map(async (filename) => {
        try {
          console.log(`Attempting to fetch: pathways/${filename}`);
          const response = await fetch(`pathways/${filename}`);
          console.log(`Response for ${filename}:`, response.status, response.statusText);
          
          if (!response.ok) {
            throw new Error(`Failed to load ${filename}: ${response.status} ${response.statusText}`);
          }
          
          const data = await response.json();
          console.log(`Successfully loaded ${filename}:`, data);
          
          return {
            filename,
            data,
            lastModified: response.headers.get('last-modified') || new Date().toISOString()
          };
        } catch (error) {
          console.warn(`Failed to load pathway ${filename}:`, error);
          return null;
        }
      });

      const results = await Promise.all(pathwayPromises);
      console.log('All pathway results:', results);
      
      this.pathways = results.filter(pathway => pathway !== null);
      console.log('Filtered pathways:', this.pathways);

      if (this.pathways.length === 0) {
        throw new Error('No pathways could be loaded');
      }

    } catch (error) {
      console.error('Error loading pathways:', error);
      throw error;
    }
  }

  async isAPIAvailable() {
    try {
      console.log('Checking API availability...');
      const response = await fetch('https://hnz-pathway-api.alistair-rumball-smith.workers.dev/api/published-pathways');
      console.log('API response status:', response.status, response.statusText);
      console.log('API response headers:', response.headers);
      
      if (response.ok) {
        const data = await response.json();
        console.log('API returned data:', data);
        return true;
      } else {
        console.warn('API returned non-OK status:', response.status);
        return false;
      }
    } catch (error) {
      console.error('API availability check failed:', error);
      return false;
    }
  }


  renderPathways() {
    const loadingState = document.getElementById('loadingState');
    const pathwaysGrid = document.getElementById('pathwaysGrid');

    loadingState.classList.add('hidden');
    pathwaysGrid.classList.remove('hidden');

    pathwaysGrid.innerHTML = '';

    this.pathways.forEach(pathway => {
      const card = this.createPathwayCard(pathway);
      pathwaysGrid.appendChild(card);
    });
  }

  createPathwayCard(pathway) {
    const { data, filename } = pathway;
    
    const card = document.createElement('div');
    card.className = 'pathway-card';
    card.addEventListener('click', () => this.openPathway(filename));

    // Get manifest data if available for richer display
    const manifestData = this.pathwaysManifest?.find(item => item.filename === filename);
    
    // Calculate some metadata
    const stepCount = manifestData?.stepCount || Object.keys(data.steps || {}).length;
    const guideCount = manifestData?.guideCount || (data.guides || []).length;
    const description = manifestData?.description || data.description || this.generateDescription(data, stepCount, guideCount);
    const lastModified = manifestData?.lastModified ? new Date(manifestData.lastModified).toLocaleDateString() : null;

    card.innerHTML = `
      <div class="pathway-header">
        <h3 class="pathway-title">${data.title || 'Untitled Pathway'}</h3>
      </div>
      <div class="pathway-body">
        <div class="pathway-description">${description}</div>
        <div class="pathway-meta">
          ${lastModified ? `<div class="pathway-modified">Last updated ${lastModified}</div>` : ''}
        </div>
      </div>
    `;

    return card;
  }

  generateDescription(data, stepCount, guideCount) {
    // Generate a description based on the pathway data
    if (data.id === 'liver-imaging-decision-tool') {
      return 'Interactive decision support for selecting appropriate liver imaging modality and contrast agent based on clinical presentation and patient factors.';
    }

    // Default description
    return 'Clinical decision support pathway to guide evidence-based care decisions.';
  }

  openPathway(filename) {
    // Navigate to the pathway page with the filename as a parameter
    const pathwayId = filename.replace('.json', '');
    window.location.href = `pathway.html?id=${pathwayId}`;
  }

  showError() {
    const loadingState = document.getElementById('loadingState');
    const errorState = document.getElementById('errorState');

    loadingState.classList.add('hidden');
    errorState.classList.remove('hidden');
  }
}

// Initialize the home page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new DecisionSupportHome();
});