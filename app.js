import React, { useState, useEffect } from 'https://esm.sh/react';
import { createRoot } from 'https://esm.sh/react-dom/client';

// --- NEW SVG LOGO ---
const logoSvg = `
<svg width="240" height="70" viewBox="0 0 297 81" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M85.2979 11.25H97.0979L89.7979 22.35L97.0979 33.75H85.2979L81.6979 27.75L78.0979 22.35L81.6979 16.95L85.2979 11.25Z" fill="#00549F"/>
<path d="M105.398 11.25H117.198L110.198 22.35L117.198 33.75H105.398L101.798 27.75L98.1979 22.35L101.798 16.95L105.398 11.25Z" fill="#00549F"/>
<path d="M220.211 11.25H231.911L226.511 22.35L231.911 33.75H220.211L214.811 22.35L220.211 11.25Z" fill="#007A86"/>
<path d="M204.911 11.25H216.611L211.211 22.35L216.611 33.75H204.911L199.511 22.35L204.911 11.25Z" fill="#007A86"/>
<path d="M189.611 11.25H201.311L195.911 22.35L201.311 33.75H189.611L184.211 22.35L189.611 11.25Z" fill="#007A86"/>
<path d="M119.898 33.75V11.25H125.298V29.25H134.598V33.75H119.898Z" fill="#00549F"/>
<path d="M140.598 33.75V11.25H154.698V13.5H145.998V20.25H153.798V22.5H145.998V31.5H154.698V33.75H140.598Z" fill="#00549F"/>
<path d="M168.498 33.75L160.698 11.25H166.398L171.198 26.55L175.998 11.25H181.698L173.898 33.75H168.498Z" fill="#00549F"/>
<path d="M235.611 33.75V11.25H241.011V29.25H250.311V33.75H235.611Z" fill="#007A86"/>
<path d="M255.611 33.75V11.25H269.711V13.5H260.911V20.25H268.811V22.5H260.911V31.5H269.711V33.75H255.611Z" fill="#007A86"/>
<path d="M282.611 22.5C282.611 28.8 277.511 33.9 271.211 33.9C264.911 33.9 259.811 28.8 259.811 22.5C259.811 16.2 264.911 11.1 271.211 11.1C277.511 11.1 282.611 16.2 282.611 22.5ZM265.211 22.5C265.211 25.8 267.911 28.5 271.211 28.5C274.511 28.5 277.211 25.8 277.211 22.5C277.211 19.2 274.511 16.5 271.211 16.5C267.911 16.5 265.211 19.2 265.211 22.5Z" fill="#007A86"/>
<path d="M287.111 33.75V11.25H292.511V33.75H287.111Z" fill="#007A86"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M61.0979 33.75V11.25H66.4979V20.85L73.6979 11.25H79.6979L70.6979 22.05L79.9979 33.75H73.9979L66.4979 24.45V33.75H61.0979Z" fill="#00549F"/>
<path d="M0.968262 49.05H6.36826V71.55H0.968262V49.05Z" fill="#0D672F"/>
<path d="M14.8683 49.05H20.2683V71.55H14.8683V49.05Z" fill="#0D672F"/>
<path d="M23.0681 49.05H28.4681V71.55H23.0681V49.05Z" fill="#0D672F"/>
<path d="M10.6682 59.85C10.6682 55.95 13.0682 49.05 20.2682 49.05C27.5682 49.05 29.8682 55.95 29.8682 59.85C29.8682 63.75 27.5682 71.55 20.2682 71.55C13.0682 71.55 10.6682 63.75 10.6682 59.85ZM16.0682 59.85C16.0682 61.8 17.1682 66.15 20.2682 66.15C23.4682 66.15 24.4682 61.8 24.4682 59.85C24.4682 57.9 23.4682 54.45 20.2682 54.45C17.1682 54.45 16.0682 57.9 16.0682 59.85Z" fill="#0D672F"/>
<path d="M41.2683 71.55V49.05H50.8683L51.7683 55.65H52.0683C53.2683 51.75 56.5683 49.05 61.6683 49.05C68.7683 49.05 71.8683 53.85 71.8683 60.3V71.55H66.4683V60.9C66.4683 56.55 64.5683 54.45 61.0683 54.45C58.3683 54.45 56.2683 56.25 55.3683 58.95V71.55H49.9683V60.9C49.9683 56.55 48.0683 54.45 44.5683 54.45C41.8683 54.45 39.9683 55.95 38.8683 58.5V71.55H41.2683H33.4683V49.05H38.8683V71.55H41.2683Z" fill="#0D672F"/>
<path d="M80.4683 49.05H85.8683V54H86.1683C87.6683 50.7 91.3683 49.05 95.5683 49.05C96.5683 49.05 97.5683 49.2 98.4683 49.35V55.05C97.5683 54.6 96.4683 54.45 95.2683 54.45C91.9683 54.45 89.7683 56.25 88.5683 59.25V71.55H83.1683V49.05H80.4683Z" fill="#0D672F"/>
<path d="M112.968 49.05L118.668 63.3L124.368 49.05H131.268L121.668 67.8L131.568 71.55H124.068L118.668 65.85L113.268 71.55H105.768L115.668 67.8L106.068 49.05H112.968Z" fill="#0D672F"/>
<path d="M139.968 49.05H145.368V71.55H139.968V49.05Z" fill="#0D672F"/>
<path d="M153.168 60.3C153.168 53.85 156.268 49.05 163.368 49.05C170.568 49.05 173.568 53.85 173.568 60.3V71.55H168.168V60.9C168.168 56.55 166.268 54.45 162.768 54.45C160.068 54.45 157.968 56.25 157.068 58.95V71.55H151.668V49.05H157.068V58.95C157.068 58.95 153.168 60.3 153.168 60.3Z" fill="#0D672F"/>
<path d="M181.668 49.05H187.068V54H187.368C188.868 50.7 192.568 49.05 196.768 49.05C197.768 49.05 198.768 49.2 199.668 49.35V55.05C198.768 54.6 197.668 54.45 196.468 54.45C193.168 54.45 190.968 56.25 189.768 59.25V71.55H184.368V49.05H181.668Z" fill="#0D672F"/>
<path d="M219.168 60.3C219.168 53.85 222.268 49.05 229.368 49.05C236.568 49.05 239.568 53.85 239.568 60.3V71.55H234.168V60.9C234.168 56.55 232.268 54.45 228.768 54.45C226.068 54.45 223.968 56.25 223.068 58.95V71.55H217.668V49.05H223.068V58.95C223.068 58.95 219.168 60.3 219.168 60.3Z" fill="#0D672F"/>
<path d="M250.668 49.05L256.368 63.3L262.068 49.05H268.968L259.368 67.8L269.268 71.55H261.768L256.368 65.85L250.968 71.55H243.468L253.368 67.8L243.768 49.05H250.668Z" fill="#0D672F"/>
<path d="M284.568 54.15C282.168 54.15 280.568 55.65 280.568 57.9V71.55H275.168V49.05H280.568V52.5C282.168 50.1 284.868 49.05 287.868 49.05C291.768 49.05 294.168 51.3 294.168 55.5V71.55H288.768V56.25C288.768 54.9 288.168 54.15 286.968 54.15C286.068 54.15 285.168 54.6 284.568 55.35V54.15Z" fill="#0D672F"/>
</svg>
`;
// ... (getModalityIcon, processBigClinData functions remain the same) ...

function App() {
  const [allData, setAllData] = useState([]);
  const [query, setQuery] = useState("");
  const [selectedSection, setSelectedSection] = useState(null);
  const [uniqueSections, setUniqueSections] = useState([]);

  useEffect(() => {
    fetch('big_clin.json')
      .then(res => res.json())
      .then(rawJsonData => {
        const processed = processBigClinData(rawJsonData);
        setAllData(processed);
        const sections = [...new Set(processed.map(item => item.section))].sort();
        setUniqueSections(sections);
      });
  }, []);

  const handleSectionButtonClick = (sectionName) => {
    setQuery("");
    setSelectedSection(sectionName);
  };

  const handleSearchInputChange = (e) => {
    setQuery(e.target.value);
    if (selectedSection) {
        setSelectedSection(null);
    }
  };

  const handleSearchInputFocus = () => {
    // setSelectedSection(null); // Clears section filter when search is focused
  };
  
  const handleSearchInputClick = () => {
    setSelectedSection(null);
  };

  let filtered = [];
  if (selectedSection) {
    filtered = allData.filter(entry => entry.section === selectedSection);
  } else if (query.length >= 3) {
    filtered = allData.filter(entry =>
        (entry.section && entry.section.toLowerCase().includes(query.toLowerCase())) ||
        (entry.subheading && entry.subheading.toLowerCase().includes(query.toLowerCase())) ||
        (entry.clinical_scenario && entry.clinical_scenario.toLowerCase().includes(query.toLowerCase()))
      );
  }

  const groupedResults = filtered.reduce((acc, item) => {
    const sectionKey = item.section || "Uncategorized Section";
    const subheadingKey = item.subheading || "General";

    if (!acc[sectionKey]) {
        acc[sectionKey] = {};
    }
    if (!acc[sectionKey][subheadingKey]) {
        acc[sectionKey][subheadingKey] = [];
    }
    acc[sectionKey][subheadingKey].push(item);
    return acc;
  }, {});

  // --- UPDATED STYLES ---
  const teWhatuOraBlue = '#00549F';
  const teWhatuOraTeal = '#007A86';
  const lightBlueTint = '#E6F3FA';
  const lightGreyBg = '#F0F0F0'; // For very subtle backgrounds
  const midGreyBorder = '#D1D5DB';
  const darkGreyText = '#374151';
  const bodyTextGrey = '#4B5563';

  const badgeStyles = {
    // Prioritisation Badge Styles (using Te Whatu Ora inspired colors)
    // Reds/Oranges for high priority, Yellows for mid, Blues/Greens for lower/screening
    P1: { backgroundColor: '#FEE2E2', color: '#B91C1C', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #FCA5A5' }, // Light Red
    'P1-P2': { backgroundColor: '#FEE2E2', color: '#B91C1C', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #FCA5A5' },
    'P1-P2a': { backgroundColor: '#FEE2E2', color: '#B91C1C', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #FCA5A5' },
    P2: { backgroundColor: '#FEF3C7', color: '#B45309', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #FCD34D' }, // Light Orange/Yellow
    'P2a': { backgroundColor: '#FEF3C7', color: '#B45309', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #FCD34D' },
    'P2a-P2': { backgroundColor: '#FEF3C7', color: '#B45309', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #FCD34D' },
    'P2-P3': { backgroundColor: '#FEF9C3', color: '#A16207', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #FDE047' }, // Lighter Yellow
    P3: { backgroundColor: '#E0E7FF', color: '#3730A3', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #A5B4FC' }, // Light Indigo/Blue
    'P3 or P2': { backgroundColor: '#FEF3C7', color: '#B45309', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #FCD34D' },
    P4: { backgroundColor: lightBlueTint, color: teWhatuOraBlue, padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: `1px solid ${teWhatuOraBlue}` },
    'P3-P4': { backgroundColor: '#D1FAE5', color: '#047857', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #6EE7B7' }, // Light Green
    P5: { backgroundColor: '#F3F4F6', color: '#4B5563', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #D1D5DB' }, // Light Grey
    // Screening badges (using Greens from Te Whatu Ora palette or similar)
    S2: { backgroundColor: '#D1FAE5', color: '#047857', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #6EE7B7' },
    S3: { backgroundColor: '#A7F3D0', color: '#065F46', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #34D399' },
    S4: { backgroundColor: '#6EE7B7', color: '#047857', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #10B981' },
    S5: { backgroundColor: '#34D399', color: '#065F46', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #059669' },
    'N/A': { backgroundColor: lightGreyBg, color: bodyTextGrey, padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: `1px solid ${midGreyBorder}` },
    'Nil': { backgroundColor: lightGreyBg, color: bodyTextGrey, padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: `1px solid ${midGreyBorder}` },
    'nil': { backgroundColor: lightGreyBg, color: bodyTextGrey, padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: `1px solid ${midGreyBorder}` },
    default: { backgroundColor: '#E5E7EB', color: '#374151', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #9CA3AF' }
  };

  const styles = {
    container: { padding: '1em', fontFamily: "'Open Sans', Arial, sans-serif", backgroundColor: '#F9FAFB', minHeight: '100vh', boxSizing: 'border-box' },
    headerWrapper: { display: 'flex', alignItems: 'center', marginBottom: '1.5em', borderBottom: `3px solid ${teWhatuOraTeal}`, paddingBottom: '1em' },
    logoInline: { width: '240px', height: 'auto', marginRight: '1.5em' }, // Adjusted size
    header: { color: teWhatuOraBlue, fontSize: '1.6em', margin: '0', lineHeight: '1.2', fontWeight: '600' },
    input: { 
        width: '100%', 
        padding: '0.75em 1em', 
        fontSize: '1em', 
        border: `1px solid ${midGreyBorder}`, 
        borderRadius: '6px', 
        marginBottom: '0.5em', 
        boxSizing: 'border-box', 
        position: 'sticky', 
        top: '10px', // Add some space from top when sticky
        backgroundColor: '#FFFFFF', 
        zIndex: 1000, 
        boxShadow: '0 2px 5px rgba(0,0,0,0.07)',
        outlineOffset: '2px', // For better focus visibility
    },
    sectionButtonsContainer: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.6em',
        marginBottom: '2em', // Increased space after buttons
        paddingTop: '0.5em',
        position: 'sticky', // Make buttons sticky below search bar
        top: 'calc(0.75em + 1em + 0.75em + 1em + 10px + 10px)', // Approximate height of search bar + its padding/margins + sticky top of search
        backgroundColor: '#F9FAFB', // Match container bg for clean sticky look
        paddingBottom: '0.5em', // Padding for sticky state
        zIndex: 999, // Below search bar
        borderBottom: `1px solid ${lightGreyBg}` // Subtle separator when sticky
    },
    sectionButton: {
        padding: '0.6em 1.2em',
        fontSize: '0.9em',
        border: `1px solid ${teWhatuOraBlue}`,
        backgroundColor: '#FFFFFF',
        color: teWhatuOraBlue,
        borderRadius: '20px',
        cursor: 'pointer',
        fontWeight: '600',
        transition: 'background-color 0.2s, color 0.2s, box-shadow 0.2s',
    },
    sectionButtonActive: {
        backgroundColor: teWhatuOraBlue,
        color: '#FFFFFF',
        boxShadow: '0 2px 4px rgba(0, 84, 159, 0.3)',
    },
    sectionHeader: { 
        marginTop: '1em', // Adjusted because buttons are sticky now
        fontSize: '1.4em', 
        color: teWhatuOraBlue, 
        borderBottom: `2px solid ${teWhatuOraTeal}`, 
        paddingBottom: '0.4em', 
        fontWeight: '700',
        marginBottom: '1em',
    },
    subheadingGroupContainer: {
        backgroundColor: '#FFFFFF', // Kept white for better contrast with cards
        border: `1px solid ${midGreyBorder}`,
        padding: '1.2em',
        borderRadius: '8px',
        marginTop: '1em',
        marginBottom: '1.8em',
        boxShadow: '0 3px 7px rgba(0,0,0,0.07)' 
    },
    subheadingHeader: { 
        marginTop: '0',
        marginBottom: '1.2em',
        fontSize: '1.2em', 
        color: teWhatuOraTeal, 
        fontWeight: '600',
        paddingBottom: '0.3em',
        borderBottom: `1px dashed ${lightBlueTint}`
    },
    result: { 
        backgroundColor: lightBlueTint, // Light blue tint for cards
        borderLeft: `5px solid ${teWhatuOraTeal}`, 
        padding: '1em', 
        marginBottom: '1em',
        borderRadius: '6px', 
        boxShadow: '0 2px 5px rgba(0,0,0,0.05)'
    },
    label: { fontWeight: 'bold', color: teWhatuOraBlue, fontSize: '0.95em' },
    text: { fontSize: '0.95em', marginBottom: '0.6em', lineHeight: '1.5', color: bodyTextGrey },
    commentText: { 
        fontSize: '0.9em', 
        marginBottom: '0.5em', 
        lineHeight: '1.4', 
        color: '#52525B', // Slightly darker grey for better readability
        backgroundColor: '#F8F8F9', // Very light grey, almost white
        padding: '0.6em', 
        borderRadius: '4px', 
        border: `1px solid ${midGreyBorder}` 
    }
  };

  return React.createElement('div', { style: styles.container }, [
    React.createElement(
      'div',
      {
        key: 'headerWrapper',
        style: styles.headerWrapper
      },
      [
        React.createElement('div', {
          key: 'logoInline',
          style: styles.logoInline,
          dangerouslySetInnerHTML: { __html: logoSvg }
        }),
        React.createElement(
          'h1',
          { style: styles.header, key: 'title' },
          'Clinical Scenario Prioritisation' // Updated title
        )
      ]
    ),
    
    React.createElement('input', {
      key: 'input',
      type: 'text',
      placeholder: 'Search scenarios or select a section below...',
      value: query,
      onChange: handleSearchInputChange,
      onFocus: handleSearchInputFocus,
      onClick: handleSearchInputClick,
      style: styles.input
    }),

    React.createElement('div', { style: styles.sectionButtonsContainer, key: 'section-buttons' },
      uniqueSections.map(sectionName => 
        React.createElement('button', {
          key: sectionName,
          onClick: () => handleSectionButtonClick(sectionName),
          style: {
            ...styles.sectionButton,
            ...(selectedSection === sectionName ? styles.sectionButtonActive : {})
          }
        }, sectionName)
      )
    ),

    (selectedSection || query.length >= 3)
      ? Object.keys(groupedResults).length > 0 
        ? Object.keys(groupedResults).map(sectionName =>
            React.createElement('div', { key: sectionName }, [
              React.createElement('h2', { style: styles.sectionHeader, key: 'sh-' + sectionName }, sectionName),
              
              Object.keys(groupedResults[sectionName]).map(subheadingName =>
                React.createElement('div', { 
                    key: `${sectionName}-${subheadingName}-group`, 
                    style: styles.subheadingGroupContainer
                }, [ 
                  (subheadingName !== "General" || Object.keys(groupedResults[sectionName]).length === 1 || selectedSection) && // Show "General" if a section is selected
                    React.createElement('h3', { style: styles.subheadingHeader, key: 'subh-' + subheadingName }, subheadingName),
                  
                  ...groupedResults[sectionName][subheadingName].map((entry, i) =>
                    React.createElement('div', { 
                        style: { ...styles.result, marginBottom: i === groupedResults[sectionName][subheadingName].length - 1 ? '0' : '1em' },
                        key: `${sectionName}-${subheadingName}-${i}` 
                    }, [
                      React.createElement('div', { style: styles.text }, [
                        React.createElement('span', { style: styles.label }, 'Scenario:'),
                        ' ' + entry.clinical_scenario
                      ]),
                      React.createElement('div', { style: styles.text }, [
                        React.createElement('span', { style: styles.label }, 'Modality:'),
                        ' ',
                        ... (entry.modality || "N/A").split(/[,>/]/).flatMap((mod, idx) => {
                          const iconUrl = getModalityIcon(mod.trim());
                          const modalityName = mod.trim();
                          return iconUrl
                            ? [
                                React.createElement('img', {
                                  key: `icon-${idx}-${sectionName}-${subheadingName}-${i}`,
                                  src: iconUrl,
                                  alt: modalityName,
                                  title: modalityName,
                                  style: { height: '28px', marginRight: '5px', verticalAlign: 'middle' } // Slightly smaller icons
                                })
                              ]
                            : [];
                        }),
                        ' ' + (entry.modality || "N/A")
                      ]),
                      React.createElement('div', { style: styles.text }, [
                        React.createElement('span', { style: styles.label }, 'Priority:'),
                        ' ',
                        React.createElement('span', { style: badgeStyles[entry.prioritisation_category] || badgeStyles.default }, entry.prioritisation_category)
                      ]),
                      (entry.comment && entry.comment.toLowerCase() !== 'none' && entry.comment.toLowerCase() !== 'n/a') && 
                        React.createElement('div', { style: styles.commentText }, [
                          React.createElement('span', { style: styles.label }, 'Comments:'),
                          ' ' + entry.comment
                        ])
                    ])
                  )
                ])
              )
            ])
          )
        : React.createElement('p', { style: { color: bodyTextGrey, marginTop: '2em', textAlign: 'center', fontSize: '1.05em' } }, 
            query.length >= 3 ? 'No matching scenarios found for your search.' : 
            selectedSection ? `No scenarios found in section: ${selectedSection}.` : ''
          )
      : React.createElement('p', { style: { color: bodyTextGrey, marginTop: '2em', textAlign: 'center', fontSize: '1em' } }, // More prominent initial message
          query.length > 0 && query.length < 3 ? 'Please enter at least 3 characters to search.' : 'Please use the search bar or select a section to view clinical scenarios.'
        )
  ]);
}

createRoot(document.getElementById('root')).render(React.createElement(App));
