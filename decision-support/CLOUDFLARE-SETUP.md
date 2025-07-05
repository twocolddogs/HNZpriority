# Cloudflare Workers API Setup Guide

This guide walks you through setting up the automated pathway management system using Cloudflare Workers and KV storage.

## Prerequisites

- Cloudflare account
- Wrangler CLI installed (`npm install -g wrangler`)
- Domain configured in Cloudflare (optional)

## Step 1: Create KV Namespace

```bash
# Create production KV namespace
wrangler kv:namespace create "PATHWAYS_KV"

# Create preview KV namespace for testing
wrangler kv:namespace create "PATHWAYS_KV" --preview
```

Copy the namespace IDs returned and update `wrangler-api.toml`.

## Step 2: Update Configuration

Edit `wrangler-api.toml` and replace:
- `your-kv-namespace-id-here` with your production KV namespace ID
- `your-kv-preview-id-here` with your preview KV namespace ID

## Step 3: Deploy the Worker

```bash
# Deploy to Cloudflare
wrangler deploy --config wrangler-api.toml

# Your API will be available at:
# https://hnz-pathway-api.your-subdomain.workers.dev
```

## Step 4: Test the API

```bash
# Test the pathways endpoint
curl https://hnz-pathway-api.your-subdomain.workers.dev/api/pathways

# Should return an empty array initially: []
```

## Step 5: Migrate Existing Data (Optional)

If you have existing pathways in the `/pathways` directory, you can migrate them:

```bash
# Use the migration script (create this if needed)
node migrate-pathways.js
```

## API Endpoints

### GET /api/pathways
Returns manifest of all pathways (draft and published)

### POST /api/pathways
Create or update a pathway
```json
{
  "id": "liver-imaging-tool",
  "title": "Liver Imaging Decision Tool",
  "description": "Guide for liver imaging decisions",
  "startStep": "start",
  "steps": {...},
  "guides": [...]
}
```

### GET /api/pathways/:id
Get specific pathway by ID

### PUT /api/pathways/:id/publish
Publish a pathway (makes it available to end users)

### PUT /api/pathways/:id/unpublish
Unpublish a pathway (converts to draft)

### DELETE /api/pathways/:id
Delete a pathway permanently

### GET /api/published-pathways
Returns only published pathways (for main app consumption)

## Security Considerations

- The API is currently open (no authentication)
- For production, consider adding:
  - API key authentication
  - Rate limiting
  - Input validation
  - Cloudflare Access protection

## Environment Configuration

Update your applications to use the API:

```javascript
// Builder configuration
const API_BASE = 'https://hnz-pathway-api.your-subdomain.workers.dev';

// Main app configuration  
const PATHWAYS_API = 'https://hnz-pathway-api.your-subdomain.workers.dev/api/published-pathways';
```

## Troubleshooting

### Worker not deploying
- Check wrangler is authenticated: `wrangler auth login`
- Verify KV namespace IDs in wrangler-api.toml

### CORS errors
- API includes CORS headers for cross-origin requests
- Ensure your domain is allowed or use wildcard (*)

### KV storage limits
- Free tier: 100,000 read/day, 1,000 write/day
- Paid tier: Higher limits available

## Migration from File-Based System

The API maintains compatibility with the existing manifest.json structure, so the transition should be seamless for end users.