import React, {
    useState,
    useEffect
} from 'https://esm.sh/react';
import {
    createRoot
} from 'https://esm.sh/react-dom/client';

// NOTE: The SVG for the logo is loaded via an <img> tag now, so the large logoSvg constant is not needed here.
// Make sure you have /images/HealthNZ_logo_v2.svg in your public/project structure.


function useIsMobile(breakpoint = 600) {
  const [isMobile, setIsMobile] = useState(window.innerWidth <= breakpoint);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= breakpoint);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [breakpoint]);

  return isMobile;
}

function getModalityIcon(modality) {
    if (!modality) return null;
    const mod = modality.toUpperCase().trim(); // Ensure trimming
    if (mod.includes("CT")) return "icons/CT.png";
    if (mod.includes("XR")) return "icons/XR.png";
    if (mod.includes("MRI") || mod.includes("MR ")) return "icons/MRI.png"; // Added "MR " for "Breast MR" etc.
    if (mod.includes("US")) return "icons/US.png";
    // Add more specific icons if needed
    if (mod.includes("PET")) return "icons/PET.png"; // Example for PET
    if (mod.includes("DBI")) return "icons/DBI.png"; // Example for DBI
    if (mod.includes("BONE SCAN")) return "icons/BoneScan.png"; // Example
    if (mod.includes("NUC MED")) return "icons/NucMed.png"; // Example
    if (mod.includes("MRA")) return "icons/MRA.png"; // Example
    if (mod.includes("CTA")) return "icons/CTA.png"; // Example
    if (mod.includes("FLUOROSCOPY")) return "icons/Fluoro.png"; // Example
    if (mod.includes("MAMMOGRAM")) return "icons/Mammo.png"; // Example
    return null;
}

// Function to flatten the big_clin.json data
function processBigClinData(rawData) {
    const scenarios = [];
    for (const sectionName in rawData) {
        if (Object.hasOwnProperty.call(rawData, sectionName)) {
            const section = rawData[sectionName];
            for (const subheadingName in section) {
                if (Object.hasOwnProperty.call(section, subheadingName)) {
                    const scenarioList = section[subheadingName];
                    if (Array.isArray(scenarioList)) {
                        scenarioList.forEach(item => {
                            // Ensure all core properties exist, providing defaults if necessary
                            scenarios.push({
                                section: sectionName || "Unknown Section",
                                subheading: subheadingName || "General", // Default subheading if empty
                                clinical_scenario: item.clinical_scenario || "N/A",
                                modality: item.modality || "N/A",
                                prioritisation_category: item.prioritisation_category || "N/A",
                                comment: item.comment || "none"
                            });
                        });
                    }
                }
            }
        }
    }
    return scenarios;
}



function App() {
    const [allData, setAllData] = useState([]);
    const [query, setQuery] = useState("");
    const [selectedSection, setSelectedSection] = useState(null);
    const [uniqueSections, setUniqueSections] = useState([]);

    // --- ESTIMATED HEIGHTS FOR STICKY POSITIONING ---
    // IMPORTANT: Adjust these pixel values after inspecting your rendered elements in browser dev tools
    // These values determine the `top` offset for the search bar (if sticky separately)
    // and the `marginTop` for the main content area to clear all sticky elements.
    const brandingHeaderRenderedHeightPx = 0; // Approximate height of the gradient header (e.g., 60px to 80px)
    const searchInputWrapperRenderedHeightPx = 0; // Approximate height of the search bar wrapper (e.g., 50px to 70px)


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
        // Optional: setSelectedSection(null);
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
        if (!acc[sectionKey]) acc[sectionKey] = {};
        if (!acc[sectionKey][subheadingKey]) acc[sectionKey][subheadingKey] = [];
        acc[sectionKey][subheadingKey].push(item);
        return acc;
    }, {});

    const badgeStyles = {
        P1: { backgroundColor: '#FFBABA', color: '#D8000C', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #D8000C' },
        'P1-P2': { backgroundColor: '#FFBABA', color: '#D8000C', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #D8000C' },
        'P1-P2a': { backgroundColor: '#FFBABA', color: '#D8000C', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #D8000C' },
        P2: { backgroundColor: '#FFE2BA', color: '#AA5F00', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #AA5F00' },
        'P2a': { backgroundColor: '#FFE2BA', color: '#AA5F00', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #AA5F00' },
        'P2a-P2': { backgroundColor: '#FFE2BA', color: '#AA5F00', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #AA5F00' },
        'P2-P3': { backgroundColor: '#FFE2BA', color: '#7A5C00', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #7A5C00' },
        P3: { backgroundColor: '#FFF8BA', color: '#5C5000', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #5C5000' },
        'P3 or P2': { backgroundColor: '#FFE2BA', color: '#AA5F00', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #AA5F00' },
        P4: { backgroundColor: '#BAE7FF', color: '#004C7A', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #004C7A' },
        'P3-P4': { backgroundColor: '#FFF8BA', color: '#00416A', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #00416A' },
        P5: { backgroundColor: '#D9D9D9', color: '#4F4F4F', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #4F4F4F' },
        S2: { backgroundColor: '#FFE2BA', color: '#AA5F00', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #00591E' },
        S3: { backgroundColor: '#FFF8BA', color: '#5C5000', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #004D1A' },
        S4: { backgroundColor: '#BAE7FF', color: '#004C7A', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #004015' },
        S5: { backgroundColor: '#D9D9D9', color: '#4F4F4F', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #003310' },
        'N/A': { backgroundColor: '#F0F0F0', color: '#555555', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #555555' },
        'Nil': { backgroundColor: '#F0F0F0', color: '#555555', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #555555' },
        'nil': { backgroundColor: '#F0F0F0', color: '#555555', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #555555' },
        default: { backgroundColor: '#E0E0E0', padding: '3px 8px', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block', border: '1px solid #777' }
    };

const isMobile = useIsMobile();

    const styles = {
        container: {
            padding: '1em',
            fontFamily: "'Open Sans', Arial, sans-serif",
            backgroundColor: '#F9FAFB', // Main page background
            minHeight: '100vh',
            boxSizing: 'border-box'
        },
        // This div wraps ONLY the sticky elements: branding header and search bar
        stickyHeaderArea: {
            position: 'sticky',
            backgroundColor: '#F9FAFB',
            top: 0,
            left: 0,
            right: 0,
            
            zIndex: 1001, // High z-index for the entire sticky block
            // Background for this area will be shown if elements inside are transparent or have gaps
            // For this setup, the children (brandingHeader, searchInputWrapper) will have their own backgrounds.
        },
        brandingHeader: { // This is the gradient part
            display: 'flex',
            alignItems: 'center',
            background: 'linear-gradient(90deg, #143345 44.5%, #41236a 100%)',
            padding: '0.75em 1.0em',
            borderRadius: '6px', 
            margin: '0.5em .2em',
            
        },
        logoInline: {
            marginRight: '1.5em'
        },
        headerSeparator: {
            width: '1px',
            height: '40px',
            backgroundColor: 'rgba(255, 255, 255, 0.5)',
            marginRight: '1.5em'
        },
        headerTitle: {
    color: '#FFFFFF',
    fontSize: isMobile ? '1em' : '1.4em',
    margin: '0',
    lineHeight: '1.2',
    fontWeight: '600'
        },
        searchInputWrapper: { // Wrapper for the search input for its own styling
            
            padding: '0.75em .5em', // Padding around the search input
           
        },
        input: { // Search Bar itself
            width: '100%',
            padding: '0.6em 1em',
            fontSize: '1em',
            border: '1px solid #D1D5DB',
            borderRadius: '6px',
            boxSizing: 'border-box',
            boxShadow: '0 2px 4px rgba(0,0,0,0.07)',
        },
        sectionButtonsContainer: { // Non-sticky
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.6em',
            padding: '.5em 0.5em', // Add some padding around buttons
            backgroundColor: '#F9FAFB', // Match page background if desired, or remove for transparency
            margin: '.5em 1em', // Space before main content starts and side padding
        },
        sectionButton: { 
            padding: '0.6em 1.2em',
            fontSize: isMobile ? '0.8em' : '0.9em',
            border: `1px solid #00549F`,
            backgroundColor: '#FFFFFF',
            color: '#00549F',
            borderRadius: '10px',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background-color 0.2s, color 0.2s, box-shadow 0.2s',
        },
        sectionButtonActive: { 
            backgroundColor: '#00549F',
            color: '#FFFFFF',
            boxShadow: '0 2px 4px rgba(0, 84, 159, 0.3)',
        },
        mainContentArea: {
            // This marginTop pushes the main scrollable content down to clear ALL sticky elements
            margin: '0 auto',
            maxWidth: '95%',
            top: '130px',
            
        },
        sectionHeader: { 
             
            fontSize: '1.4em', 
            color: '#00549F', 
            borderBottom: `2px solid #007A86`, 
            paddingBottom: '0.4em', 
            paddingTop: '0.5em',
            paddingLeft: '-0.05em',
            paddingRight: '-0.05em',
            fontWeight: '700',
            marginBottom: '1em',
            position: 'sticky',
      top: '128px',
            backgroundColor: '#F9FAFB',
        },
        subheadingGroupContainer: {
            backgroundColor: '#FFFFFF',
            border: `1px solid #D1D5DB`,
            padding: '1.2em',
            borderRadius: '8px',
            margin: '1em 0.4em',
            boxShadow: '0 3px 7px rgba(0,0,0,0.07)',
            maxWidth: '90%',
        
        },
        subheadingHeader: { 
            marginTop: '0',
            marginBottom: '1.2em',
            fontSize: '1.2em', 
            color: '#007A86', 
            fontWeight: '600',
            paddingBottom: '0.3em',
            borderBottom: `1.5px dotted #E6F3FA`
        },
        result: { 
            backgroundColor: '#E6F3FA',
            borderLeft: `5px solid #007A86`, 
            padding: '1em', 
            marginBottom: '1em',
            borderRadius: '6px', 
            boxShadow: '0 2px 5px rgba(0,0,0,0.05)'
        },
        label: { 
            fontWeight: 'bold', 
            color: '#00549F', 
            fontSize: '0.95em' 
        },
        text: { 
            fontSize: '0.95em', 
            marginBottom: '0.6em', 
            lineHeight: '1.5', 
            color: '#4B5563' 
        },
        commentText: { 
            fontSize: '0.9em', 
            marginBottom: '0.5em', 
            lineHeight: '1.4', 
            color: '#52525B',
            backgroundColor: '#F8F8F9',
            padding: '0.6em', 
            borderRadius: '4px', 
            border: `1px solid #D1D5DB` 
        }
    };

    return React.createElement('div', { style: styles.container }, [
        // --- WRAPPER FOR ALL STICKY ELEMENTS AT THE TOP ---
        React.createElement('div', {
            key: 'app-sticky-header-area',
            style: styles.stickyHeaderArea // This div becomes the sticky container
        }, [
            // 1. Branding Header (Gradient part) - inside the sticky container
            React.createElement(
                'div', {
                    style: styles.brandingHeader,
                    key: 'branding-header-div'
                }, [
                    React.createElement('img', {
                        key: 'logoImage',
                        src: '/images/HealthNZ_logo_v2.svg',
                        alt: 'Health New Zealand Logo',
                        style: { width: '200px', height: 'auto', marginRight: '1.5em' }
                    }),
                    React.createElement('div', {
                        key: 'headerSeparator',
                        style: styles.headerSeparator
                    }),
                    React.createElement(
                        'h1', {
                            style: styles.headerTitle,
                            key: 'title'
                        },
                        'Radiology Triage Tool'
                    ),
                ]
            ),
            // 2. Search Input Wrapper (also inside the sticky container, below branding)
            React.createElement('div', { style: styles.searchInputWrapper, key: 'search-wrapper' },
                React.createElement('input', {
                    key: 'input',
                    type: 'text',
                    placeholder: 'Search clinical scenarios...',
                    value: query,
                    onChange: handleSearchInputChange,
                    onFocus: handleSearchInputFocus,
                    onClick: handleSearchInputClick,
                    style: styles.input // Input style itself
                })
            )
        ]),

        // --- NON-STICKY SECTION BUTTONS ---
        // (Rendered after the sticky block, so they will scroll with main content)
        query.length < 3 ?
        React.createElement(
            'div', {
                style: styles.sectionButtonsContainer,
                key: 'section-buttons'
            },
            uniqueSections.map(sectionName =>
                React.createElement('button', {
                    key: sectionName,
                    onClick: () => handleSectionButtonClick(sectionName),
                    style: {
                        ...styles.sectionButton,
                        ...(selectedSection === sectionName ?
                            styles.sectionButtonActive :
                            {})
                    }
                }, sectionName)
            )
        ) :
        null,

        // --- MAIN CONTENT AREA ---
        
        React.createElement('div', {
            key: 'main-content',
            style: styles.mainContentArea
        }, [
            (selectedSection || query.length >= 3) ?
            Object.keys(groupedResults).length > 0 ?
            Object.keys(groupedResults).map(sectionName =>
                React.createElement('div', {
                    key: sectionName
                }, [
                    React.createElement('h2', {
                        style: styles.sectionHeader,
                        key: 'sh-' + sectionName
                    }, sectionName),

                    Object.keys(groupedResults[sectionName]).map(subheadingName =>
                        React.createElement('div', {
                            key: `${sectionName}-${subheadingName}-group`,
                            style: styles.subheadingGroupContainer
                        }, [
                            (subheadingName !== "General" || Object.keys(groupedResults[sectionName]).length === 1 || selectedSection) &&
                            React.createElement('h3', {
                                style: styles.subheadingHeader,
                                key: 'subh-' + subheadingName
                            }, subheadingName),

                            ...groupedResults[sectionName][subheadingName].map((entry, i) =>
                                React.createElement('div', {
                                    style: {...styles.result,
                                        marginBottom: i === groupedResults[sectionName][subheadingName].length - 1 ? '0' : '1em'
                                    },
                                    key: `${sectionName}-${subheadingName}-${i}`
                                }, [
                                    React.createElement('div', { style: styles.text }, [ React.createElement('span', { style: styles.label }, 'Scenario:'), ' ' + entry.clinical_scenario ]),
                                    React.createElement('div', { style: styles.text }, [
                                        React.createElement('span', { style: styles.label }, 'Modality:'), ' ',
                                        ...(entry.modality || "N/A").split(/[,>/]/).flatMap((mod, idx) => {
                                            const iconUrl = getModalityIcon(mod.trim());
                                            const modalityName = mod.trim();
                                            return iconUrl ? [ React.createElement('img', { key: `icon-${idx}-${sectionName}-${subheadingName}-${i}`, src: iconUrl, alt: modalityName, title: modalityName, style: { height: '28px', marginRight: '5px', verticalAlign: 'middle' } }) ] : [];
                                        }), ' ' + (entry.modality || "N/A")
                                    ]),
                                    React.createElement('div', { style: styles.text }, [ React.createElement('span', { style: styles.label }, 'Priority:'), ' ', React.createElement('span', { style: badgeStyles[entry.prioritisation_category] || badgeStyles.default }, entry.prioritisation_category) ]),
                                    (entry.comment && entry.comment.toLowerCase() !== 'none' && entry.comment.toLowerCase() !== 'n/a') &&
                                    React.createElement('div', { style: styles.commentText }, [ React.createElement('span', { style: styles.label }, 'Comments:'), ' ' + entry.comment ])
                                ])
                            )
                        ])
                    )
                ])
            ) :
            React.createElement('p', { style: { color: '#4B5563', marginTop: '2em', textAlign: 'center', fontSize: '1.05em' } },
                query.length >= 3 ? 'No matching scenarios found for your search.' :
                selectedSection ? `No scenarios found in section: ${selectedSection}.` : ''
            ) :
            React.createElement('p', { style: { color: '#4B5563', marginTop: '2em', textAlign: 'center', fontSize: '1em' } },
                query.length > 0 && query.length < 3 ? 'Please enter at least 3 characters to search.' : 'Please use the search bar or select a section to view clinical scenarios.'
            )
        ])
    ]);
}

createRoot(document.getElementById('root')).render(React.createElement(App));
