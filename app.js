
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
    fetch('./clinical_data.json')
      .then(res => res.json())
      .then(setData);
  }, []);

  const filtered = query.length >= 3
    ? data.filter(entry =>
        entry.clinical_scenario.toLowerCase().includes(query.toLowerCase())
      )
    : [];

  const groupedResults = filtered.reduce((acc, item) => {
    if (!acc[item.section]) acc[item.section] = [];
    acc[item.section].push(item);
    return acc;
  }, {});

  const styles = {
    container: {
      padding: '1em',
      fontFamily: 'Arial, sans-serif',
      backgroundColor: '#F2F2F2',
      minHeight: '100vh',
      boxSizing: 'border-box',
    },
    header: {
      color: '#005EB8',
      fontSize: '1.4em',
      marginBottom: '0.75em',
      lineHeight: '1.2',
    },
    input: {
      width: '100%',
      padding: '0.75em',
      fontSize: '1em',
      border: '1px solid #ccc',
      borderRadius: '6px',
      marginBottom: '1em',
      boxSizing: 'border-box',
      position: 'sticky',
      top: 0,
      backgroundColor: '#F2F2F2',
      zIndex: 1000,
    },
    sectionHeader: {
      marginTop: '2em',
      fontSize: '1.1em',
      color: '#003B5C',
      borderBottom: '2px solid #00A9A0',
      paddingBottom: '0.25em',
    },
    result: {
      backgroundColor: '#FFFFFF',
      borderLeft: '5px solid #00A9A0',
      padding: '0.75em',
      marginBottom: '1em',
      borderRadius: '4px',
      boxShadow: '0 2px 5px rgba(0,0,0,0.05)',
    },
    label: {
      fontWeight: 'bold',
      color: '#003B5C',
      fontSize: '0.95em',
    },
    text: {
      fontSize: '0.95em',
      marginBottom: '0.5em',
      lineHeight: '1.4',
    }
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.header}>Clinical Imaging Search</h2>
      <input
        type="text"
        placeholder="Search clinical scenarios..."
        value={query}
        onChange={e => setQuery(e.target.value)}
        style={styles.input}
      />
      {query.length >= 3 ? (
        Object.keys(groupedResults).map(section => (
          <div key={section}>
            <h3 style={styles.sectionHeader}>{section}</h3>
            {groupedResults[section].map((entry, i) => (
              <div key={i} style={styles.result}>
                <div style={styles.text}><span style={styles.label}>Scenario:</span> {entry.clinical_scenario}</div>
                <div style={styles.text}>
                  <span style={styles.label}>Modality:</span>
                  <img src={getModalityIcon(entry.modality)} alt="" style={{ height: '20px', marginRight: '8px', verticalAlign: 'middle' }} />
                  {entry.modality}
                </div>
                <div style={styles.text}><span style={styles.label}>Priority:</span> {entry.prioritisation}</div>
                <div style={styles.text}><span style={styles.label}>Comments:</span> {entry.comment}</div>
              </div>
            ))}
          </div>
        ))
      ) : (
        <p style={{ color: '#888', marginTop: '1em' }}>Please enter at least 3 characters to begin searching.</p>
      )}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
