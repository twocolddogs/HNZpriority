#!/usr/bin/env node

// ==========================================================================
// Simple Publish Endpoint for Decision Tree Builder
// This creates a simple HTTP server to handle pathway publishing
// ==========================================================================

const http = require('http');
const fs = require('fs');
const path = require('path');
const { generateManifest } = require('./generate-manifest.js');

const PORT = 3001;
const PATHWAYS_DIR = './pathways';

function createPublishServer() {
  const server = http.createServer(async (req, res) => {
    // Enable CORS for local development
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    // Handle preflight requests
    if (req.method === 'OPTIONS') {
      res.writeHead(200);
      res.end();
      return;
    }

    console.log(`${req.method} ${req.url}`);

    // Handle pathway file saves
    if (req.method === 'PUT' && req.url.startsWith('/pathways/')) {
      const filename = path.basename(req.url);
      const filepath = path.join(PATHWAYS_DIR, filename);

      // Validate filename
      if (!filename.endsWith('.json')) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Only JSON files are allowed' }));
        return;
      }

      let body = '';
      req.on('data', chunk => {
        body += chunk.toString();
      });

      req.on('end', async () => {
        try {
          // Validate JSON
          const data = JSON.parse(body);
          
          // Ensure pathways directory exists
          if (!fs.existsSync(PATHWAYS_DIR)) {
            fs.mkdirSync(PATHWAYS_DIR, { recursive: true });
          }

          // Write the file
          fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
          console.log(`✅ Saved pathway: ${filename}`);

          // Regenerate manifest
          try {
            generateManifest();
            console.log('✅ Manifest regenerated');
          } catch (manifestError) {
            console.warn('⚠️  Failed to regenerate manifest:', manifestError.message);
          }

          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ 
            success: true, 
            message: `Pathway saved as ${filename}`,
            filepath: filepath
          }));

        } catch (error) {
          console.error('❌ Error saving pathway:', error.message);
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: error.message }));
        }
      });

      return;
    }

    // Handle manifest regeneration
    if (req.method === 'POST' && req.url === '/regenerate-manifest') {
      try {
        const manifest = generateManifest();
        console.log('✅ Manifest regenerated via API');
        
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ 
          success: true, 
          message: 'Manifest regenerated',
          pathwayCount: manifest.length
        }));
      } catch (error) {
        console.error('❌ Error regenerating manifest:', error.message);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: error.message }));
      }
      return;
    }

    // Handle health check
    if (req.method === 'GET' && req.url === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        status: 'ok',
        service: 'Decision Tree Publisher',
        pathwaysDir: PATHWAYS_DIR
      }));
      return;
    }

    // Default 404
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not found' }));
  });

  server.listen(PORT, () => {
    console.log(`🚀 Publish endpoint running on http://localhost:${PORT}`);
    console.log(`📁 Pathways directory: ${PATHWAYS_DIR}`);
    console.log('');
    console.log('Available endpoints:');
    console.log(`  PUT  /pathways/{filename}    - Save pathway file`);
    console.log(`  POST /regenerate-manifest    - Regenerate manifest`);
    console.log(`  GET  /health                 - Health check`);
  });

  return server;
}

// Run if called directly
if (require.main === module) {
  createPublishServer();
}

module.exports = { createPublishServer };