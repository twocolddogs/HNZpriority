// ==========================================================================
// API Client for HNZ Pathway Management
// ==========================================================================

class PathwayAPIClient {
  constructor(baseURL = '') {
    // Default to same origin for production, or configure as needed
    this.baseURL = baseURL || window.location.origin;
    this.apiPath = '/api';
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${this.apiPath}${endpoint}`;
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const response = await fetch(url, {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Get all pathways (draft and published)
  async getPathways() {
    return this.request('/pathways');
  }

  // Get specific pathway by ID
  async getPathway(id) {
    return this.request(`/pathways/${id}`);
  }

  // Save pathway (create or update)
  async savePathway(pathwayData) {
    return this.request('/pathways', {
      method: 'POST',
      body: JSON.stringify(pathwayData),
    });
  }

  // Publish pathway
  async publishPathway(id) {
    return this.request(`/pathways/${id}/publish`, {
      method: 'PUT',
    });
  }

  // Unpublish pathway
  async unpublishPathway(id) {
    return this.request(`/pathways/${id}/unpublish`, {
      method: 'PUT',
    });
  }

  // Delete pathway
  async deletePathway(id) {
    return this.request(`/pathways/${id}`, {
      method: 'DELETE',
    });
  }

  // Get only published pathways (for main app)
  async getPublishedPathways() {
    return this.request('/published-pathways');
  }
}

// Global API client instance - configure with your deployed API URL
window.pathwayAPI = new PathwayAPIClient('https://hnz-pathway-api.alistair-rumball-smith.workers.dev');

// Fallback to file-based system if API not available
window.pathwayAPI.isAPIAvailable = async function() {
  try {
    await this.getPathways();
    return true;
  } catch (error) {
    console.warn('API not available, falling back to file-based system:', error.message);
    return false;
  }
};