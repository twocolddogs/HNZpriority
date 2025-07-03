# HNZ Decision Tree Builder

A comprehensive tool for creating, editing, and rendering clinical decision trees for Health New Zealand.

## Features

### Builder Interface
- **Visual Editor**: Drag-and-drop interface for creating decision trees
- **Step Types**: Support for multiple choice, yes/no, endpoint, and protocol information steps
- **Protocol Guides**: Add reference materials and protocol information
- **Real-time Preview**: See your decision tree in action as you build it
- **JSON Export/Import**: Save and share decision trees as standardized JSON files

### Universal Renderer
- **Consistent Styling**: All decision trees use the same HNZ branding and visual style
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Navigation**: Back buttons, start over functionality, and step history
- **Protocol References**: Modal overlays for protocol and reference information

## Quick Start

1. Open `index.html` in your browser
2. Use the **Builder** tab to create your decision tree:
   - Set tree properties (ID, title, description)
   - Add decision steps with the "Add Step" button
   - Configure each step's type, options, and actions
   - Add protocol guides for reference materials
3. Use the **Preview** tab to test your decision tree
4. Use the **JSON** tab to export your tree for use in production

## Decision Tree Schema

### Tree Structure
```json
{
  "id": "unique-tree-id",
  "title": "Decision Tree Title",
  "description": "Optional description",
  "startStep": "first-step-id",
  "guides": [...],
  "steps": {...}
}
```

### Step Types

#### 1. Multiple Choice (`choice`)
Present multiple options to the user. Use for scenarios with 3+ choices.

#### 2. Yes/No Decision (`yes-no`)
Binary decision with two options. Options are displayed side-by-side.

#### 3. Endpoint (`endpoint`)
Final step that provides a recommendation. No further navigation.

#### 4. Protocol Information (`protocol-info`)
Displays protocol details with optional navigation options.

### Actions

#### Navigate Action
```json
{
  "type": "navigate",
  "nextStep": "step-id"
}
```

#### Recommend Action
```json
{
  "type": "recommend",
  "recommendation": {
    "modality": "MRI liver",
    "contrast": "with Gadovist",
    "notes": "Optional notes",
    "priority": "P1"
  }
}
```

## Integration

### Using the Renderer Standalone

```javascript
// Load your decision tree JSON
const treeData = { /* your tree data */ };

// Create renderer instance
const renderer = new DecisionTreeRenderer(treeData);

// Render to container
const container = document.getElementById('decision-container');
container.appendChild(renderer.render());
```

### CSS Requirements

The renderer requires the decision-support CSS classes. Either:
1. Include the decision-support styles, or
2. Copy the relevant classes to your stylesheet

Key required classes:
- `.decision-tree-container`
- `.step-card`
- `.decision-button` (with variants: `.primary`, `.secondary`, `.success`, `.warning`)
- `.recommendation-card`
- `.protocol-info`
- `.modal-overlay` and related modal classes

## Examples

See the `examples/` directory for sample decision trees:
- `liver-imaging-example.json` - Complete liver imaging decision tree

## File Structure

```
decision-tree-builder/
├── index.html          # Main builder interface
├── builder.js          # Builder application logic
├── renderer.js         # Universal rendering engine
├── styles.css          # Builder interface styles
├── schema.json         # JSON schema for validation
├── examples/           # Example decision trees
└── README.md          # This file
```

## Development

### Adding New Step Types

1. Update the schema in `schema.json`
2. Add the step type to the builder interface in `builder.js`
3. Implement rendering logic in `renderer.js`
4. Add appropriate CSS classes

### Customizing Styling

The builder uses CSS custom properties for easy theming:
- `--primary`: Primary action color
- `--secondary`: Secondary action color
- `--success`: Success state color
- `--warning`: Warning state color
- `--danger`: Danger state color

## Best Practices

### Step Design
- Keep step titles clear and concise
- Use descriptive questions that guide the user
- Limit choices to 5 options maximum for readability
- Use yes/no steps for binary decisions

### Protocol Guides
- Include all relevant reference information
- Organize guides logically by topic
- Use clear, clinical language
- Update guides when protocols change

### Testing
- Test all decision paths thoroughly
- Verify recommendations are accurate
- Check mobile responsiveness
- Test with clinical staff before deployment

## Support

For questions or issues with the decision tree builder, please refer to the main HNZ repository documentation or contact the development team.