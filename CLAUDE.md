# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains two separate applications for New Zealand's Health system:

### 1. HNZ Radiology Triage Tool (Root Directory)
A React-based web application that helps with radiology prioritization and triage decisions. The application has two main modes:
- **View Mode**: Public tool for viewing radiology triage scenarios and priority guidelines
- **Editor Mode**: Administrative interface for editing scenarios and priority data

The application is deployed using Cloudflare Workers and serves healthcare professionals in New Zealand.

### 2. LORA Scenario Configurator (lora/ Directory)
A separate standalone application for configuring LORA (Local Operational Resource Allocation) scenarios. This is a distinct tool with its own HTML interface, styles, and CSV data management.

## Architecture

### HNZ Radiology Triage Tool (Root Directory)
- `index.html` - Main HTML entry point for triage tool
- `app.js` - Primary React application (1300+ lines, contains all main logic)
- `HelperPage.js` - Priority guide/helper page component  
- `styles.css` - Main stylesheet for triage tool
- `priority_data_set.json` - Core data file containing all triage scenarios organized by medical sections
- `wrangler.jsonc` - Cloudflare Workers configuration

### LORA Configurator (lora/ Directory)
- `lora/configurator.html` - Standalone HTML application for LORA scenario configuration
- `lora/styles.css` - Dedicated stylesheet for LORA configurator
- `lora/input_configuration_snowflake_baseline_2023_2024.csv` - CSV data file for baseline configurations
- `lora/input_configuration_snowflake_baseline_2023_2024_backup.csv` - Backup of CSV data

### Key Components in app.js
- `App` - Main application component with dual mode functionality
- `ScenarioCard` - Individual triage scenario display/editing
- `SubheadingSection` - Collapsible sections within medical areas
- `AuthorPopover` - Management of clinical and radiology leads

### Data Structure
The `priority_data_set.json` follows this structure:
```json
{
  "MedicalSection": {
    "authors": {
      "Radiology Leads": [{"name": "...", "region": "..."}],
      "Clinical Leads": [{"name": "...", "region": "..."}]  
    },
    "last_updated": "YYYY-MM-DD",
    "SubheadingName": [
      {
        "clinical_scenario": "description",
        "modality": "imaging type", 
        "prioritisation_category": "P1-P5 or S1-S5",
        "comment": "additional notes"
      }
    ]
  }
}
```


## Development Commands

Both applications are static web applications with no build process. They run directly in the browser.

### HNZ Radiology Triage Tool
Since there's no package.json, this project doesn't use npm/node build tools. To develop locally:
- Serve files from root directory using a local web server (e.g., `python -m http.server` or VS Code Live Server)
- The app uses CDN imports for React from esm.sh
- Deployed via Cloudflare Workers using the wrangler configuration (`wrangler.jsonc`)

### LORA Configurator  
- Serve files from the `lora/` directory using a local web server
- Standalone HTML/CSS/JavaScript application
- No external dependencies or build process required

## Critical Branch Management Rules

**NEVER make any code changes directly to the `main` branch. Always use the `develop` branch for all modifications.**

### Workflow Requirements:
1. **Always check current branch** before making any changes
2. **Switch to `develop` branch** if not already on it: `git checkout develop`
3. **Make all code changes on `develop` branch only**
4. **Test changes thoroughly** on develop branch
5. **Automatically push commits to develop branch** after committing
6. **Create pull requests** from develop to main when changes are ready for production
7. **Never commit directly to main** - this is a protected production branch

### Auto-Push Configuration:
- **ALWAYS push commits immediately** after creating them on develop branch
- Use `git push origin develop` or `git push` (if upstream is configured)
- This ensures changes are backed up and available for collaboration

This is a healthcare-critical application where uncontrolled changes to main could impact patient care. All development must follow proper branch management.

## Code Search and Analysis

When searching for code, functions, or specific implementations:
- **ALWAYS use Gemini CLI** to load files and find code instead of using other search tools
- Use the `@filename` syntax to have Gemini analyze specific files
- This ensures more accurate code location and analysis

## Code Patterns

### HNZ Radiology Triage Tool (React Application)

#### React Usage
- Uses React without JSX - all components built with `React.createElement` (aliased as `e`)
- Hooks-based functional components throughout
- No traditional build pipeline - runs directly in browser with ES modules

#### State Management  
- Uses React built-in state management (useState, useEffect)
- Complex state for editing mode with dirty tracking via `dirty` object
- Deep cloning used extensively for immutable updates

#### Data Flow
- Editor mode: Load JSON → Edit in memory → Download updated JSON + changelog
- View mode: Load JSON → Display filtered/searched scenarios  
- Dual hostname detection for mode switching (editor.hnzradtools.nz vs main domain)

#### Key Features
- Deep linking support for individual scenarios via URL hash
- Mobile-responsive with hamburger navigation
- Search/filter functionality within medical sections
- Real-time change tracking with visual indicators
- Export functionality with automatic changelog generation

### LORA Configurator (Standalone Application)
- Pure HTML/CSS/JavaScript implementation
- CSV data import/export functionality
- Separate styling and interface design
- Independent of the main triage tool

## Common Tasks

### HNZ Radiology Triage Tool

#### Adding New Medical Sections
New sections are added through the editor interface, creating entries in the JSON structure with default "General" subheading.

#### Modifying Scenarios
Individual scenarios can be edited through the ScenarioCard component when in editor mode, with immediate state updates and dirty tracking.

#### Priority Categories
- P1-P5: Standard priority levels (P1 = highest priority)
- S1-S5: Specified date priorities  
- Special handling for priority badge display and filtering

#### Data Export
Editor mode generates two files on save:
1. Updated JSON data file
2. Text changelog with detailed change summary

### LORA Configurator

#### Working with CSV Data
- Import/export CSV files for scenario configuration
- Modify baseline configurations
- Separate data management from the main triage tool

## Available Font Icons

### Nerd Font Icons (SymbolsNerdFont-Regular.ttf)
The project has access to **10,413 icons** from Nerd Fonts. Some commonly useful icons include:

**Interface Icons:**
- `U+E0A0` () - Git branch
- `U+E0B0` () - Hard divider left  
- `U+E0B2` () - Hard divider right
- `U+2665` (♥) - Heart
- `U+26A1` (⚡) - Lightning/zap
- `U+23FB` (⏻) - Power symbol
- `U+276F` (❯) - Arrow right

**Usage in CSS:**
```css
.icon::before {
  font-family: 'Symbols Nerd Font', monospace;
  content: '\E0A0'; /* Git branch icon */
}
```

**Complete icon reference:** Run `python3 extract_nerd_font_names.py` in project root for full list.

## Important Notes

- **CRITICAL: This is a healthcare application serving New Zealand's health system**
- **ALWAYS work on the `develop` branch - NEVER make changes directly to `main`**
- Priority data affects real clinical decision-making
- Editor mode requires specific hostname authentication
- All changes are tracked and logged for audit purposes
- The application handles both desktop and mobile interfaces
- Font files (Poppins, Public Sans) are locally hosted in the fonts/ directory
- Nerd Font icons available via SymbolsNerdFont-Regular.ttf (10,413 icons)
- Proper branch management is essential due to the healthcare-critical nature of this application