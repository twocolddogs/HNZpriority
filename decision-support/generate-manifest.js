#!/usr/bin/env node

// ==========================================================================
// Pathway Manifest Generator
// Automatically creates a manifest of all JSON pathways in the pathways/ directory
// ==========================================================================

const fs = require('fs');
const path = require('path');

const PATHWAYS_DIR = './pathways';
const MANIFEST_FILE = './pathways/manifest.json';

function generateManifest() {
    console.log('🔍 Scanning pathways directory...');
    
    if (!fs.existsSync(PATHWAYS_DIR)) {
        console.error('❌ Pathways directory not found:', PATHWAYS_DIR);
        process.exit(1);
    }

    const pathways = [];
    const files = fs.readdirSync(PATHWAYS_DIR)
        .filter(file => file.endsWith('.json') && file !== 'manifest.json')
        .sort();

    console.log(`📁 Found ${files.length} JSON files`);

    for (const file of files) {
        try {
            const filePath = path.join(PATHWAYS_DIR, file);
            const content = fs.readFileSync(filePath, 'utf8');
            const data = JSON.parse(content);
            
            // Validate that this is a pathway file (has required fields)
            if (!data.title || !data.steps) {
                console.warn(`⚠️  Skipping ${file}: Missing required fields (title, steps)`);
                continue;
            }

            const stats = fs.statSync(filePath);
            const stepCount = Object.keys(data.steps || {}).length;
            const guideCount = (data.guides || []).length;

            const pathwayInfo = {
                filename: file,
                id: data.id || path.basename(file, '.json'),
                title: data.title,
                description: data.description || generateDescription(data, stepCount, guideCount),
                stepCount: stepCount,
                guideCount: guideCount,
                status: data.metadata?.status || 'published',
                lastModified: stats.mtime.toISOString(),
                size: stats.size
            };

            pathways.push(pathwayInfo);
            console.log(`✅ Added: ${file} - "${data.title}"`);

        } catch (error) {
            console.error(`❌ Error processing ${file}:`, error.message);
        }
    }

    // Sort by title for consistent ordering
    pathways.sort((a, b) => a.title.localeCompare(b.title));

    // Write the manifest
    fs.writeFileSync(MANIFEST_FILE, JSON.stringify(pathways, null, 2));
    console.log(`\n🎉 Generated manifest with ${pathways.length} pathways`);
    console.log(`📝 Manifest saved to: ${MANIFEST_FILE}`);
    
    return pathways;
}

function generateDescription(data, stepCount, guideCount) {
    // Generate a description based on the pathway data
    let description = `A clinical decision support pathway with ${stepCount} decision ${stepCount === 1 ? 'step' : 'steps'}`;
    if (guideCount > 0) {
        description += ` and ${guideCount} protocol ${guideCount === 1 ? 'guide' : 'guides'}`;
    }
    description += '.';
    return description;
}

// Run if called directly
if (require.main === module) {
    generateManifest();
}

module.exports = { generateManifest };