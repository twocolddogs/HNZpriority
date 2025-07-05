// ==========================================================================
// Migration Script: File-based Pathways to Cloudflare API
// ==========================================================================

const fs = require('fs');
const path = require('path');

// Configuration
const API_BASE = 'https://hnz-pathway-api.alistair-rumball-smith.workers.dev'; // Updated with actual URL
const PATHWAYS_DIR = './pathways';

async function migratePathways() {
  try {
    // Read manifest
    const manifestPath = path.join(PATHWAYS_DIR, 'manifest.json');
    if (!fs.existsSync(manifestPath)) {
      console.log('No manifest.json found. Nothing to migrate.');
      return;
    }

    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    console.log(`Found ${manifest.length} pathways to migrate`);

    let migrated = 0;
    let errors = 0;

    for (const entry of manifest) {
      try {
        console.log(`Migrating: ${entry.title} (${entry.id})`);
        
        // Read pathway file
        const pathwayPath = path.join(PATHWAYS_DIR, entry.filename);
        if (!fs.existsSync(pathwayPath)) {
          console.log(`  ⚠️  File not found: ${entry.filename}`);
          errors++;
          continue;
        }

        const pathwayData = JSON.parse(fs.readFileSync(pathwayPath, 'utf8'));
        
        // Add metadata from manifest
        pathwayData.status = entry.status || 'draft';
        pathwayData.lastModified = entry.lastModified || new Date().toISOString();

        // Send to API
        const response = await fetch(`${API_BASE}/api/pathways`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(pathwayData),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(`HTTP ${response.status}: ${errorData.message || response.statusText}`);
        }

        const result = await response.json();
        console.log(`  ✅ Migrated: ${result.id}`);
        migrated++;

      } catch (error) {
        console.log(`  ❌ Error migrating ${entry.title}: ${error.message}`);
        errors++;
      }
    }

    console.log('\n=== Migration Summary ===');
    console.log(`✅ Successfully migrated: ${migrated}`);
    console.log(`❌ Errors: ${errors}`);
    console.log(`📊 Total: ${manifest.length}`);

    if (errors === 0) {
      console.log('\n🎉 All pathways migrated successfully!');
      console.log('You can now switch to API mode in your applications.');
    } else {
      console.log('\n⚠️  Some pathways failed to migrate. Check the errors above.');
    }

  } catch (error) {
    console.error('Migration failed:', error.message);
    process.exit(1);
  }
}

// Verify API connectivity
async function testAPI() {
  try {
    console.log('Testing API connectivity...');
    const response = await fetch(`${API_BASE}/api/pathways`);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log(`✅ API is accessible. Found ${data.length} existing pathways.`);
    return true;
  } catch (error) {
    console.error('❌ API test failed:', error.message);
    console.error('Please check:');
    console.error('1. API_BASE URL is correct');
    console.error('2. Cloudflare Worker is deployed');
    console.error('3. KV namespace is configured');
    return false;
  }
}

// Main execution
async function main() {
  console.log('🚀 HNZ Pathway Migration Tool');
  console.log('==============================\n');

  // Test API first
  const apiWorking = await testAPI();
  if (!apiWorking) {
    process.exit(1);
  }

  // Confirm migration
  console.log('\n⚠️  This will migrate all pathways from the file system to the Cloudflare API.');
  console.log('   Existing pathways in the API with the same ID will be overwritten.');
  console.log('\nProceed with migration? (y/N)');

  // Simple confirmation (you might want to use a proper prompt library)
  const answer = process.argv[2];
  if (answer !== 'y' && answer !== 'yes') {
    console.log('Migration cancelled.');
    process.exit(0);
  }

  await migratePathways();
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}

module.exports = { migratePathways, testAPI };