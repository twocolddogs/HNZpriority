# 🎯 Frontend/Backend Separation Plan

## Overview

Split the current monorepo into separate frontend (Cloudflare Pages) and backend (Render) deployments for faster iteration, better performance, and clearer separation of concerns.

## Current Structure Analysis

### Frontend Files (to move)
- `index.html`
- `app.js`
- `unified-styles.css`
- `fonts/` directory
- `images/` directory
- `sanity_test.json`

### Backend Files (to keep)
- `backend/` directory (entire contents)
- All Python files and dependencies
- Configuration and training files

## Phase 1: Repository Structure

### Frontend Repository (New)
```
radiology-cleaner-frontend/
├── index.html
├── app.js  
├── unified-styles.css
├── fonts/
├── images/
├── sanity_test.json
├── wrangler.toml (for CF Pages)
└── README.md
```

### Backend Repository (Current - Cleaned)
```
radiology-cleaner-backend/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── [all Python files]
├── render.yaml
└── README.md
```

## Phase 2: Deployment Configuration

### Cloudflare Pages (Frontend)

**Advantages:**
- Lightning-fast global CDN
- Automatic HTTPS
- Zero-downtime deployments
- Perfect for static assets
- Git-based deployments
- Free tier with generous limits

**Configuration:**
- Build command: `echo "Static site"` (no build needed)
- Output directory: `./` (root)
- Custom domain: `radiology.hnzradtools.nz`
- Auto-deployment on git push

**Wrangler Configuration:**
```toml
# wrangler.toml
name = "radiology-cleaner"
compatibility_date = "2024-01-01"

[env.production]
routes = [
  { pattern = "radiology.hnzradtools.nz/*", zone_name = "hnzradtools.nz" }
]
```

### Render (Backend Only)

**Advantages:**
- Persistent disk for embeddings
- Environment variables for secrets
- Database connections
- Python runtime
- Existing setup working well

**Updated Configuration:**
```yaml
# render.yaml
services:
- type: web
  name: radiology-cleaner-backend
  env: python
  buildCommand: "cd backend && pip install -r requirements.txt"
  startCommand: "cd backend && python app.py"
  rootDir: backend
  envVars:
  - key: PYTHONPATH
    value: .
  disk:
    name: radiology-cache
    mountPath: /opt/render/project/src/cache
    sizeGB: 10
```

## Phase 3: Implementation Steps

### Step 1: Create Frontend Repository
```bash
# Create new frontend repository
mkdir radiology-cleaner-frontend
cd radiology-cleaner-frontend

# Copy frontend files
cp ../radiology-cleaner-app/index.html .
cp ../radiology-cleaner-app/app.js .
cp ../radiology-cleaner-app/unified-styles.css .
cp ../radiology-cleaner-app/sanity_test.json .
cp -r ../radiology-cleaner-app/fonts .
cp -r ../radiology-cleaner-app/images .

# Initialize git
git init
git add .
git commit -m "Initial frontend separation"
```

### Step 2: Update API Configuration

Update `app.js` to use production backend URL:
```javascript
// Replace current apiConfig with:
const apiConfig = {
    baseUrl: 'https://radiology-api-staging.onrender.com',
    // Remove localhost development fallback
};
```

### Step 3: Frontend Environment Detection

Add environment-aware configuration:
```javascript
// Enhanced API config with environment detection
const apiConfig = (() => {
    const hostname = window.location.hostname;
    
    // Production
    if (hostname === 'radiology.hnzradtools.nz' || hostname === 'hnzradtools.nz') {
        return {
            baseUrl: 'https://radiology-api-production.onrender.com',
            environment: 'production'
        };
    }
    
    // Staging/Preview
    return {
        baseUrl: 'https://radiology-api-staging.onrender.com',
        environment: 'staging'
    };
})();
```

### Step 4: Backend Cleanup

Remove frontend files from current repo:
```bash
# In radiology-cleaner-app/
rm index.html app.js unified-styles.css sanity_test.json
rm -rf fonts/ images/
# Keep backend/ directory and supporting files
```

Update backend root structure:
```bash
# Move backend contents to root level (optional)
mv backend/* .
rmdir backend
# Or keep backend/ structure and update Render config
```

### Step 5: Cloudflare Pages Setup

1. **Connect Repository**: Link new frontend repo to CF Pages
2. **Build Settings**:
   - Framework preset: None (static site)
   - Build command: `echo "No build required"`
   - Build output directory: `/`
3. **Environment Variables**: None needed (all client-side)
4. **Custom Domain**: Configure `radiology.hnzradtools.nz`
5. **Security Headers**: Configure via `_headers` file

### Step 6: Update CORS Configuration

Backend needs to allow CF Pages domains:
```python
# In backend/app.py
CORS(app, 
     origins=[
         'https://radiology.hnzradtools.nz',
         'https://*.pages.dev',  # CF Pages preview URLs
         'https://hnzradtools.nz'
     ], 
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=False)
```

## Phase 4: Benefits Analysis

### Development Workflow
- **Frontend**: Edit → Git push → CF Pages auto-deploys (30 seconds)
- **Backend**: Edit → Git push → Render auto-deploys (2-3 minutes)
- **Independent scaling** and deployment cycles
- **Faster feedback** loops for UI changes

### Performance Improvements
- **Frontend**: Served from CF's 200+ global edge locations
- **Static assets**: Cached globally, instant loading worldwide
- **API calls**: Direct to Render backend, no proxy overhead
- **Reduced backend load**: No static file serving

### Maintenance & Operations
- **Clear separation**: Frontend devs work on UX, backend devs on API
- **Faster iterations**: Frontend changes deploy instantly
- **Better caching**: Static assets cached indefinitely
- **Independent monitoring**: Separate error tracking and analytics
- **Scalability**: Frontend scales automatically, backend scales independently

### Cost Optimization
- **CF Pages**: Free tier covers most usage
- **Render**: Only pays for backend compute, not static file serving
- **Bandwidth**: CF absorbs frontend bandwidth costs

## Phase 5: Migration Strategy

### Pre-Migration Testing
1. **Create frontend repo** and test locally
2. **Deploy to CF Pages** with preview URL
3. **Test integration** with existing backend
4. **Performance testing** with CF CDN
5. **Load testing** API endpoints

### Migration Execution
1. **DNS preparation**: Lower TTL on existing DNS records
2. **CF Pages deployment**: Deploy and verify
3. **Backend cleanup**: Remove frontend files, redeploy
4. **DNS cutover**: Point domain to CF Pages
5. **Monitor**: Both frontend and backend deployments
6. **Rollback plan**: Keep old deployment ready

### Post-Migration Verification
- [ ] Frontend loads correctly from CF Pages
- [ ] API calls work from new frontend
- [ ] All features functional
- [ ] Performance improved
- [ ] Error rates normal
- [ ] R2 config system working
- [ ] Batch processing functional

## Phase 6: Future Enhancements

### Frontend Optimizations
- **Progressive Web App**: Add service worker for offline capability
- **Code splitting**: Lazy load non-critical features
- **Image optimization**: CF Image Resizing
- **Analytics**: CF Web Analytics integration

### Backend Optimizations
- **API versioning**: Prepare for API evolution
- **Rate limiting**: Implement proper rate limiting
- **Monitoring**: Enhanced backend-specific monitoring
- **Scaling**: Auto-scaling based on load

### Development Experience
- **Preview deployments**: Every PR gets preview URL
- **Environment parity**: Staging mirrors production
- **Automated testing**: CI/CD for both repos
- **Documentation**: Separate docs for frontend/backend

## Risk Assessment & Mitigation

### Risks
- **CORS issues**: Different domains may have CORS problems
- **Deployment coordination**: Need to coordinate API changes
- **Learning curve**: Team needs to manage two repos
- **DNS propagation**: Domain changes take time

### Mitigation
- **Thorough CORS testing**: Test all endpoints from CF Pages
- **API versioning**: Maintain backward compatibility
- **Documentation**: Clear deployment procedures
- **Rollback plan**: Always have previous version ready
- **Staging environment**: Test integration before production

## Success Metrics

### Performance
- [ ] Frontend load time < 1 second globally
- [ ] API response times maintain current levels
- [ ] 99.9% uptime for both frontend and backend

### Development
- [ ] Frontend deployment time < 30 seconds
- [ ] Backend deployment time < 3 minutes
- [ ] Zero-downtime deployments achieved

### User Experience
- [ ] No functionality regression
- [ ] Improved global performance
- [ ] Better mobile experience (CF optimization)

## Conclusion

This separation will provide significant benefits in terms of performance, development velocity, and operational clarity. The investment in migration will pay dividends in faster iteration cycles and better user experience globally.

**Recommended Timeline**: 2-3 days for implementation, 1 week for thorough testing and migration.