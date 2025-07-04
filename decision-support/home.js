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
          
          // Fallback to embedded data for liver imaging
          if (filename === 'liver-imaging-example.json') {
            return {
              filename,
              data: this.getEmbeddedLiverPathway(),
              lastModified: new Date().toISOString()
            };
          }
          
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

  getEmbeddedLiverPathway() {
    // Embedded liver imaging pathway as fallback
    return {
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
          <div class="pathway-steps">${stepCount} ${stepCount === 1 ? 'step' : 'steps'}</div>
          ${guideCount > 0 ? `<div class="pathway-guides">${guideCount} ${guideCount === 1 ? 'guide' : 'guides'}</div>` : ''}
          ${lastModified ? `<div class="pathway-modified">Updated ${lastModified}</div>` : ''}
          <div class="pathway-badge">Available</div>
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
    let description = `A clinical decision support pathway with ${stepCount} decision ${stepCount === 1 ? 'step' : 'steps'}`;
    if (guideCount > 0) {
      description += ` and ${guideCount} protocol ${guideCount === 1 ? 'guide' : 'guides'}`;
    }
    description += '.';

    return description;
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