# Publishing Decision Trees

This document explains how to use the Publish functionality in the Decision Tree Builder.

## How Publishing Works

The Publish button in the Decision Tree Builder will:

1. **Validate** the decision tree is complete and ready for publication
2. **Save** the pathway file to the `pathways/` directory 
3. **Add metadata** including publication date, version, and status
4. **Regenerate** the manifest.json file automatically
5. **Make available** the pathway in the home page listing

## Setup Instructions

### 1. Start the Publish Server

Before using the Publish button, you need to start the publish server:

```bash
# In the decision-support directory
npm run publish-server
```

This starts a simple HTTP server on port 3001 that handles pathway saving and manifest generation.

### 2. Use the Builder

1. Open the Decision Tree Builder at `builder/index.html`
2. Create or edit your decision tree
3. Click the hamburger menu (☰) in the top right
4. Click **Publish**

### 3. Verify Publication

1. Check that your pathway appears in the `pathways/` directory
2. Verify the `pathways/manifest.json` file was updated
3. Visit the home page to see your published pathway listed

## Fallback Behavior

If the publish server is not running or there's an error:

- The pathway will be **downloaded** as a JSON file instead
- You'll get instructions to manually copy the file to `pathways/`
- You'll need to run `npm run generate-manifest` manually

## Development Workflow

For development, run both servers:

```bash
# Terminal 1: Start the main development server
npm run dev

# Terminal 2: Start the publish server  
npm run publish-server
```

Then access:
- Main app: http://localhost:8000
- Builder: http://localhost:8000/builder/
- Publish endpoint: http://localhost:3001 (health check: http://localhost:3001/health)

## Production Deployment

For production deployments, integrate the publish endpoint functionality into your main backend server rather than running it as a separate service.

## Troubleshooting

### "Failed to save pathway" error
- Ensure the publish server is running (`npm run publish-server`)
- Check the console for detailed error messages
- Verify file permissions on the `pathways/` directory

### Pathway not appearing on home page
- Check that `pathways/manifest.json` was updated
- Refresh the home page
- Check browser console for loading errors

### CORS errors
- The publish server includes CORS headers for local development
- For production, configure CORS appropriately for your domain