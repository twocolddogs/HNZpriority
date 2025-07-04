# HNZ Decision Support Tools

Clinical decision support pathways for Health New Zealand healthcare professionals.

## Workflow: Build → Save → Publish

### 1. Builder (Create/Edit Pathways)
- Located in `builder/` directory
- Create and edit decision pathways
- Preview with birdseye view
- Test with interactive preview

### 2. Save Draft
- **Button**: "Save Draft" in builder JSON view
- **Action**: Downloads JSON with `draft-` prefix
- **Purpose**: Save work-in-progress locally
- **Location**: Downloads to your computer as `draft-{pathway-id}.json`

### 3. Publish Pathway
- **Button**: "Publish" in builder JSON view  
- **Validation**: Checks pathway completeness:
  - Title and ID required
  - Start step must exist
  - All navigation targets must be valid
  - No orphaned steps
- **Action**: Downloads JSON with `published-` prefix
- **Manual Step**: Copy file to `pathways/` directory
- **Generate Manifest**: Run `npm run generate-manifest`

## Directory Structure

```
decision-support/
├── builder/                    # Pathway builder tool
│   ├── index.html             # Builder interface
│   ├── builder.js             # Builder logic
│   ├── examples/              # Example pathway files
│   └── drafts/                # Draft pathways (local storage)
├── pathways/                  # Published pathways
│   ├── manifest.json          # Auto-generated pathway listing
│   ├── liver-imaging-example.json
│   └── [other pathway files]
├── index.html                 # Public pathway selection page
├── home.js                    # Pathway discovery logic
├── generate-manifest.js       # Manifest generation script
└── package.json               # Scripts for manifest generation
```

## Commands

```bash
# Generate manifest after adding new pathways
npm run generate-manifest

# Start development server
npm run dev

# Start production server  
npm start
```

## Publishing New Pathways

1. **Create** pathway in builder (`builder/index.html`)
2. **Save Draft** to save work-in-progress
3. **Publish** when ready (validates and downloads)
4. **Copy** published file to `pathways/` directory
5. **Run** `npm run generate-manifest` to update listing
6. **Refresh** main page to see new pathway

## Automatic Discovery

The system automatically discovers pathways using:

1. **Manifest file** (`pathways/manifest.json`) - preferred method
2. **Fallback scanning** - tries common pathway names if no manifest

Adding a JSON file to `pathways/` directory + running `npm run generate-manifest` is all that's needed to make it discoverable.

## Pathway Validation

Published pathways are automatically validated for:
- Required fields (title, ID, steps)
- Valid navigation flows
- No broken references
- Reachable steps from start point

## File Naming Convention

- **Drafts**: `draft-{pathway-id}.json` 
- **Published**: `{pathway-id}.json`
- **Examples**: Use descriptive names like `liver-imaging-example.json`