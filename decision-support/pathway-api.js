// ==========================================================================
// Cloudflare Worker API for HNZ Decision Support Pathways
// ==========================================================================

// CORS headers for browser requests
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

// Response helper with CORS and cache control
function corsResponse(body, status = 200, headers = {}) {
  return new Response(body, {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=300, s-maxage=300', // 5 minutes cache
      'Vary': 'Accept-Encoding',
      ...corsHeaders,
      ...headers,
    },
  });
}

// Generate manifest from stored pathways
async function generateManifest(env) {
  try {
    // List all pathway keys
    const list = await env.PATHWAYS_KV.list({ prefix: 'pathway:' });
    const manifest = [];

    for (const key of list.keys) {
      const pathwayData = await env.PATHWAYS_KV.get(key.name, 'json');
      if (pathwayData) {
        const stepCount = Object.keys(pathwayData.steps || {}).length;
        const guideCount = (pathwayData.guides || []).length;
        
        manifest.push({
          filename: `${pathwayData.id}.json`,
          id: pathwayData.id,
          title: pathwayData.title,
          description: pathwayData.description || '',
          stepCount: stepCount,
          guideCount: guideCount,
          status: pathwayData.status || 'draft',
          lastModified: pathwayData.lastModified || new Date().toISOString(),
          size: JSON.stringify(pathwayData).length
        });
      }
    }

    // Sort by last modified (newest first)
    manifest.sort((a, b) => new Date(b.lastModified) - new Date(a.lastModified));
    
    return manifest;
  } catch (error) {
    console.error('Error generating manifest:', error);
    return [];
  }
}

// Main request handler
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Handle CORS preflight
    if (method === 'OPTIONS') {
      return corsResponse('', 204);
    }

    try {
      // Route handling
      if (path === '/api/pathways' && method === 'GET') {
        // Get all pathways manifest
        const manifest = await generateManifest(env);
        return corsResponse(JSON.stringify(manifest));
      }

      if (path === '/api/pathways' && method === 'POST') {
        // Create or update pathway
        const body = await request.json();
        
        // Validate required fields
        if (!body.id || !body.title) {
          return corsResponse(JSON.stringify({ 
            error: 'Missing required fields: id and title' 
          }), 400);
        }

        // Add metadata
        body.lastModified = new Date().toISOString();
        body.status = body.status || 'draft';

        // Store pathway
        await env.PATHWAYS_KV.put(`pathway:${body.id}`, JSON.stringify(body));

        return corsResponse(JSON.stringify({ 
          success: true, 
          id: body.id,
          message: 'Pathway saved successfully' 
        }));
      }

      if (path.startsWith('/api/pathways/') && method === 'GET') {
        // Get specific pathway
        const pathwayId = path.split('/').pop();
        const pathway = await env.PATHWAYS_KV.get(`pathway:${pathwayId}`, 'json');
        
        if (!pathway) {
          return corsResponse(JSON.stringify({ 
            error: 'Pathway not found' 
          }), 404);
        }

        return corsResponse(JSON.stringify(pathway));
      }

      if (path.startsWith('/api/pathways/') && path.endsWith('/publish') && method === 'PUT') {
        // Publish pathway
        const pathwayId = path.split('/')[3]; // Extract ID from /api/pathways/:id/publish
        const pathway = await env.PATHWAYS_KV.get(`pathway:${pathwayId}`, 'json');
        
        if (!pathway) {
          return corsResponse(JSON.stringify({ 
            error: 'Pathway not found' 
          }), 404);
        }

        // Update status and timestamp
        pathway.status = 'published';
        pathway.lastModified = new Date().toISOString();
        
        await env.PATHWAYS_KV.put(`pathway:${pathwayId}`, JSON.stringify(pathway));

        return corsResponse(JSON.stringify({ 
          success: true, 
          message: 'Pathway published successfully' 
        }));
      }

      if (path.startsWith('/api/pathways/') && path.endsWith('/unpublish') && method === 'PUT') {
        // Unpublish pathway
        const pathwayId = path.split('/')[3]; // Extract ID from /api/pathways/:id/unpublish
        const pathway = await env.PATHWAYS_KV.get(`pathway:${pathwayId}`, 'json');
        
        if (!pathway) {
          return corsResponse(JSON.stringify({ 
            error: 'Pathway not found' 
          }), 404);
        }

        // Update status and timestamp
        pathway.status = 'draft';
        pathway.lastModified = new Date().toISOString();
        
        await env.PATHWAYS_KV.put(`pathway:${pathwayId}`, JSON.stringify(pathway));

        return corsResponse(JSON.stringify({ 
          success: true, 
          message: 'Pathway unpublished successfully' 
        }));
      }

      if (path.startsWith('/api/pathways/') && method === 'DELETE') {
        // Delete pathway
        const pathwayId = path.split('/').pop();
        const pathway = await env.PATHWAYS_KV.get(`pathway:${pathwayId}`, 'json');
        
        if (!pathway) {
          return corsResponse(JSON.stringify({ 
            error: 'Pathway not found' 
          }), 404);
        }

        await env.PATHWAYS_KV.delete(`pathway:${pathwayId}`);

        return corsResponse(JSON.stringify({ 
          success: true, 
          message: 'Pathway deleted successfully' 
        }));
      }

      // Legacy endpoint for published pathways only (for main app)
      if (path === '/api/published-pathways' && method === 'GET') {
        const manifest = await generateManifest(env);
        const publishedOnly = manifest.filter(p => p.status === 'published');
        return corsResponse(JSON.stringify(publishedOnly));
      }

      // Route not found
      return corsResponse(JSON.stringify({ 
        error: 'Route not found' 
      }), 404);

    } catch (error) {
      console.error('API Error:', error);
      return corsResponse(JSON.stringify({ 
        error: 'Internal server error',
        message: error.message 
      }), 500);
    }
  },
};