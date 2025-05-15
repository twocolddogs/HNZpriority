import React, { useState, useEffect } from 'https://esm.sh/react';
import { createRoot } from 'https://esm.sh/react-dom/client';

function getModalityIcon(modality) {
  if (!modality) return null;
  const mod = modality.toUpperCase();
  if (mod.includes("CT")) return "icons/CT.png";
  if (mod.includes("XR")) return "icons/XR.png";
  if (mod.includes("MRI")) return "icons/MRI.png";
  if (mod.includes("US")) return "icons/US.png";
  return null;
}

function App() {
  const [data, setData] = useState([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetch('clinical_data.json')
      .then(res => res.json())
      .then(setData);
  }, []);

  const filtered = query.length >= 3
    ? data.filter(entry =>
        entry.clinical_scenario.toLowerCase().includes(query.toLowerCase())
      )
    : [];

  const groupedResults = filtered.reduce((acc, item) => {
    const section = item.section || "Other";
    if (!acc[section]) acc[section] = [];
    acc[section].push(item);
    return acc;
  }, {});

  const badgeStyles = {
    P1: { backgroundColor: '#FFBABA', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block' },
    P2: { backgroundColor: '#FFE2BA', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block' },
    P3: { backgroundColor: '#FFF8BA', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block' },
    default: { backgroundColor: '#E0E0E0', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block' }
  };

  const styles = {
    container: { padding: '1em', fontFamily: 'Arial, sans-serif', backgroundColor: '#FFFFFF', minHeight: '100vh', boxSizing: 'border-box' },
    header: { color: '#005EB8', fontSize: '1.4em', marginBottom: '0.75em', lineHeight: '1.2' },
    input: { width: '100%', padding: '0.75em', fontSize: '1em', border: '1px solid #ccc', borderRadius: '6px', marginBottom: '1em', boxSizing: 'border-box', position: 'sticky', top: 0, backgroundColor: '#F2F2F2', zIndex: 1000 },
    sectionHeader: { marginTop: '2em', fontSize: '1.1em', color: '#003B5C', borderBottom: '2px solid #00A9A0', paddingBottom: '0.25em' },
    result: { backgroundColor: '#FFFFFF', borderLeft: '5px solid #00A9A0', padding: '0.75em', marginBottom: '1em', borderRadius: '4px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' },
    label: { fontWeight: 'bold', color: '#003B5C', fontSize: '0.95em' },
    text: { fontSize: '0.95em', marginBottom: '0.5em', lineHeight: '1.4' },
    commentText: { fontSize: '0.95em', marginBottom: '0.5em', lineHeight: '1.4', color: '#666666' }
  };

  return React.createElement('div', { style: styles.container }, [
  // Logo + title wrapper
React.createElement(
  'div',
  {
    key: 'headerWrapper',
    style: { display: 'flex', alignItems: 'center', marginBottom: '1em' }
  },
  [
    React.createElement('img', {
      key: 'logo',
      src: 'logo.png',
      alt: 'Health NZ Te Whatu Ora',
      style: { height: '40px', marginRight: '10px' }
    }),
    React.createElement(
      'h2',
      { style: styles.header, key: 'title' },
      'Radiology Triage Helper'
    )
  ]
),
    React.createElement('input', {
      key: 'input',
      type: 'text',
      placeholder: 'Search clinical scenarios...',
      value: query,
      onChange: e => setQuery(e.target.value),
      style: styles.input
    }),
    query.length >= 3
      ? Object.keys(groupedResults).map(section =>
          React.createElement('div', { key: section }, [
            React.createElement('h3', { style: styles.sectionHeader, key: 'sh-' + section }, section),
            ...groupedResults[section].map((entry, i) =>
              React.createElement('div', { key: section + '-' + i, style: styles.result }, [
                // Scenario
                React.createElement('div', { style: styles.text }, [
                  React.createElement('span', { style: styles.label }, 'Scenario:'),
                  ' ' + entry.clinical_scenario
                ]),
                // Modality icons (supports multiple separated by comma, slash, or >)
                React.createElement('div', { style: styles.text }, [
                  React.createElement('span', { style: styles.label }, 'Modality:'),
                  ' ',
                  ...entry.modality.split(/[,>/]/).map((mod, idx) =>
                    React.createElement('img', {
                      key: mod.trim() + idx,
                      src: getModalityIcon(mod.trim()),
                      alt: mod.trim(),
                      style: { height: '32px', marginRight: '6px', verticalAlign: 'middle' }
                    })
                  ),
                  ' ' + entry.modality
                ]),
                // Priority badge
                React.createElement('div', { style: styles.text }, [
                  React.createElement('span', { style: styles.label }, 'Priority:'),
                  ' ',
                  React.createElement('span', { style: badgeStyles[entry.prioritisation] || badgeStyles.default }, entry.prioritisation)
                ]),
                // Comments

									React.createElement('div', { style: styles.commentText }, [
  									React.createElement('span', { style: styles.label }, 'Comments:'),
 									 ' ' + entry.comment
])
              ])
            )
          ])
        )
      : React.createElement('p', { style: { color: '#888', marginTop: '1em' } },
          'Please enter at least 3 characters to begin searching.'
        )
  ]);
}

createRoot(document.getElementById('root')).render(React.createElement(App));