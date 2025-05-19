import React, {
    useState,
    useEffect,
    useRef // Added useRef
} from 'https://esm.sh/react';
import {
    createRoot
} from 'https://esm.sh/react-dom/client';

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
    if (mod.includes("MRI")) return "icons/MRI.png";
    if (mod.includes("US") && mod.includes("ASPIRATION")) return "icons/MAMASP.png";
    if (mod.includes("US")) return "icons/US.png";
    if (mod.includes("PET")) return "icons/PET.png";
    if (mod.includes("DBI")) return "icons/DBI.png";
    if (mod.includes("BONE SCAN")) return "icons/BS.png";
    if (mod.includes("NUC MED")) return "icons/NM.png";
    if (mod.includes("MRA")) return "icons/MR.png";
    if (mod.includes("CTA")) return "icons/CT.png";
    if (mod.includes("FLUOROSCOPY")) return "icons/XR.png";
    if (mod.includes("MAMMOGRAM")) return "icons/MAM.png";
    if (mod.includes("ASPIRATION")) return "icons/MAMASP.png";
    return null;
}

function processBigClinData(rawData) {
    const scenarios = [];
    for (const sectionName in rawData) {
        if (Object.hasOwnProperty.call(rawData, sectionName)) {
            const section = rawData[sectionName];
            for (const subheadingName in section) {
                if (subheadingName === "authors") { // Skip the authors key
                    continue;
                }
                if (Object.hasOwnProperty.call(section, subheadingName)) {
                    const scenarioList = section[subheadingName];
                    if (Array.isArray(scenarioList)) {
                        scenarioList.forEach(item => {
                            scenarios.push({
                                section: sectionName || "Unknown Section",
                                subheading: subheadingName || "General",
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

function AuthorPopover({ content, position, onClose }) {
    if (!position.visible || !content) return null;

    const popoverStyle = {
        position: 'absolute',
        top: `${position.top}px`,
        left: `${position.left}px`,
        backgroundColor: '#FFFFFF',
        border: `1px solid #D1D5DB`,
        borderRadius: '8px',
        padding: '1.5em',
        boxShadow: '0 5px 15px rgba(0,0,0,0.15)',
        zIndex: 1002,
        minWidth: '280px',
        maxWidth: '400px',
        color: '#4B5563', // Default text color for popover
    };

    const leadBlockStyle = { marginBottom: '1.2em' };
    const leadHeaderStyle = {
        fontSize: '1.1em',
        fontWeight: 'bold', // Bolder for lead type
        color: '#00549F', // Primary accent color
        marginBottom: '0.6em',
        paddingBottom: '0.4em',
        borderBottom: `1.5px solid #E6F3FA`, // Subtle separator
    };
    const authorEntryStyle = {
        fontSize: '0.95em',
        marginBottom: '0.4em',
        lineHeight: '1.4',
    };
    const authorNameStyle = {
        fontWeight: '500', // Slightly bolder for names
    };
    const regionStyle = {
        fontSize: '0.85em',
        color: '#6B7280', // Softer color for region
    };

    const closeButtonStyle = {
        position: 'absolute',
        top: '10px',
        right: '15px',
        background: 'none',
        border: 'none',
        fontSize: '1.5em', // Larger close button
        cursor: 'pointer',
        color: '#6B7280', // Standard icon color
        padding: '0',
        lineHeight: '1'
    };

    const renderLeads = (leads, title) => {
        if (!leads || leads.length === 0) {
            return React.createElement('div', { style: leadBlockStyle }, [
                React.createElement('h4', { style: leadHeaderStyle, key: title + '-header' }, title),
                React.createElement('p', { style: {...authorEntryStyle, fontStyle: 'italic'} , key: title + '-empty'}, 'No leads listed.')
            ]);
        }
        return React.createElement('div', { style: leadBlockStyle }, [
            React.createElement('h4', { style: leadHeaderStyle, key: title + '-header' }, title),
            ...leads.map((lead, index) =>
                React.createElement('p', { style: authorEntryStyle, key: title + '-' + index },
                    React.createElement('span', { style: authorNameStyle }, lead.name),
                    lead.region ? React.createElement('span', { style: regionStyle }, ` (${lead.region})`) : ''
                )
            )
        ]);
    };

    return React.createElement('div', { style: popoverStyle, 'data-popover-id': 'author-popover' }, [
        React.createElement('button', { onClick: onClose, style: closeButtonStyle, key: 'close-popover', title: 'Close' }, '×'),
        renderLeads(content.authors['Radiology Leads'], 'Radiology Leads'),
        renderLeads(content.authors['Clinical Leads'], 'Clinical Leads')
    ]);
}


function App() {
    const [allData, setAllData] = useState([]);
    const [rawJsonData, setRawJsonData] = useState(null); // For authors
    const [query, setQuery] = useState("");
    const [selectedSection, setSelectedSection] = useState(null);
    const [uniqueSections, setUniqueSections] = useState([]);

    const [popoverContent, setPopoverContent] = useState(null);
    const [popoverPosition, setPopoverPosition] = useState({ top: 0, left: 0, visible: false });

    const [stickyHeaderAreaHeight, setStickyHeaderAreaHeight] = useState(0);
    const stickyHeaderAreaRef = useRef(null);

    useEffect(() => {
        if (stickyHeaderAreaRef.current) {
            // Delay slightly to ensure all styles are applied
            requestAnimationFrame(() => {
                 if (stickyHeaderAreaRef.current) {
                    setStickyHeaderAreaHeight(stickyHeaderAreaRef.current.offsetHeight);
                 }
            });
        }
    }, [query, selectedSection, rawJsonData]); // Re-evaluate if query/section changes, or data loads

    useEffect(() => {
        fetch('big_clin.json')
            .then(res => res.json())
            .then(data => {
                setRawJsonData(data);
                const processedScenarios = processBigClinData(data);
                setAllData(processedScenarios);
                const sections = [...new Set(processedScenarios.map(item => item.section))].sort();
                setUniqueSections(sections);
            });
    }, []);

    const handleSectionButtonClick = (sectionName) => {
        setQuery("");
        setSelectedSection(sectionName);
        setPopoverPosition(prev => ({ ...prev, visible: false })); // Close popover on section change
    };

    const handleSearchInputChange = (e) => {
        setQuery(e.target.value);
        if (selectedSection) {
            setSelectedSection(null);
        }
        setPopoverPosition(prev => ({ ...prev, visible: false })); // Close popover on search
    };
    
    const handleSearchInputClick = () => {
        setSelectedSection(null);
        setPopoverPosition(prev => ({ ...prev, visible: false })); // Close popover on search click
    };


    const handleInfoIconClick = (event, sectionName) => {
        event.stopPropagation();

        if (popoverPosition.visible && popoverContent && popoverContent.sectionName === sectionName) {
            setPopoverPosition(prev => ({ ...prev, visible: false }));
            setPopoverContent(null);
        } else {
            if (rawJsonData && rawJsonData[sectionName] && rawJsonData[sectionName].authors) {
                const rect = event.target.getBoundingClientRect();
                const popoverWidthEstimate = 300; // Approximate width
                const popoverHeightEstimate = 200; // Approximate height

                let newTop = rect.bottom + window.scrollY + 8;
                let newLeft = rect.left + window.scrollX - (popoverWidthEstimate / 2) + (rect.width / 2) ; // Center below icon

                // Adjust if too far right
                if (newLeft + popoverWidthEstimate > window.innerWidth - 15) {
                    newLeft = window.innerWidth - popoverWidthEstimate - 15;
                }
                // Adjust if too far left
                if (newLeft < 15) {
                    newLeft = 15;
                }
                // Adjust if too low (though less common for click-below)
                if (newTop + popoverHeightEstimate > window.innerHeight + window.scrollY - 15) {
                    newTop = rect.top + window.scrollY - popoverHeightEstimate - 8; // Position above icon
                }
                if (newTop < window.scrollY + 5) { // Ensure it's not above the very top of viewport
                    newTop = window.scrollY + 5;
                }


                setPopoverContent({
                    sectionName: sectionName,
                    authors: rawJsonData[sectionName].authors
                });
                setPopoverPosition({
                    top: newTop,
                    left: newLeft,
                    visible: true
                });
            } else {
                setPopoverPosition(prev => ({ ...prev, visible: false }));
                setPopoverContent(null);
            }
        }
    };

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (popoverPosition.visible) {
                const popoverElement = document.querySelector('[data-popover-id="author-popover"]');
                const clickedInfoIcon = event.target.closest('[data-info-icon-section]');

                if (clickedInfoIcon) {
                    return; // Let the icon click handler manage this
                }

                if (popoverElement && !popoverElement.contains(event.target)) {
                    setPopoverPosition(prev => ({ ...prev, visible: false }));
                    setPopoverContent(null);
                }
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [popoverPosition.visible]);


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
            backgroundColor: '#F9FAFB',
            minHeight: '100vh',
            boxSizing: 'border-box'
        },
        stickyHeaderArea: {
            position: 'sticky',
            backgroundColor: '#F9FAFB', // Ensure background for sticky area
            top: 0,
            left: 0,
            right: 0,
            zIndex: 1001,
        },
        brandingHeader: {
            display: 'flex',
            alignItems: 'center',
            background: 'linear-gradient(90deg, #143345 44.5%, #41236a 100%)',
            padding: '0.75em 1.0em',
            borderRadius: '6px',
            margin: '0.5em .2em',
        },
        logoInline: { marginRight: '1.5em' },
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
        searchInputWrapper: { padding: '0.75em .5em' },
        input: {
            width: '100%',
            padding: '0.6em 1em',
            fontSize: '1em',
            border: '1px solid #D1D5DB',
            borderRadius: '6px',
            boxSizing: 'border-box',
            boxShadow: '0 2px 4px rgba(0,0,0,0.07)',
        },
        sectionButtonsContainer: {
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.6em',
            padding: '.5em 0.5em',
            backgroundColor: '#F9FAFB',
            margin: '.5em .5em',
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
            margin: '0 auto',
            maxWidth: '95%',
        },
        sectionHeader: {
            fontSize: '1.4em',
            color: '#00549F',
            borderBottom: `2px solid #007A86`,
            paddingBottom: '0.4em',
            paddingTop: '0.5em',
            marginLeft: '-0.2em',
            marginRight: '-0.2em',
            fontWeight: '700',
            marginBottom: '1em',
            position: 'sticky',
            top: `${stickyHeaderAreaHeight}px`, // Use dynamic height
            backgroundColor: '#F9FAFB', // Match page background
            zIndex: 1000, // Below main sticky header but above content
            display: 'flex', // For aligning title and icon
            justifyContent: 'space-between',
            alignItems: 'center'
        },
        infoIcon: {
            marginLeft: '10px',
            cursor: 'pointer',
            color: '#007A86',
            fontWeight: 'bold',
            fontSize: '0.8em', // Smaller than header
            padding: '2px 5px',
            borderRadius: '50%',
            border: '1px solid #007A86',
            userSelect: 'none',
            transition: 'background-color 0.2s, color 0.2s'
        },
        subheadingGroupContainer: {
            backgroundColor: '#FFFFFF',
            border: `1px solid #D1D5DB`,
            padding: '1.2em',
            borderRadius: '8px',
            margin: '1em auto',
            boxShadow: '0 3px 7px rgba(0,0,0,0.07)',
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
            fontSize: '1em'
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
    
    // Effect for info icon hover (optional enhancement)
    useEffect(() => {
        document.querySelectorAll('[data-info-icon-section]').forEach(icon => {
            const originalColor = styles.infoIcon.color;
            const originalBg = 'transparent'; // Assuming default
            icon.onmouseenter = () => {
                icon.style.backgroundColor = '#007A86';
                icon.style.color = '#FFFFFF';
            };
            icon.onmouseleave = () => {
                icon.style.backgroundColor = originalBg;
                icon.style.color = originalColor;
            };
        });
    }, [uniqueSections]); // Re-apply if sections change (though icons are fairly static once rendered)


    return React.createElement('div', { style: styles.container }, [
        React.createElement('div', {
            key: 'app-sticky-header-area',
            ref: stickyHeaderAreaRef,
            style: styles.stickyHeaderArea
        }, [
            React.createElement(
                'div', { style: styles.brandingHeader, key: 'branding-header-div' },
                [
                    React.createElement('img', {
                        key: 'logoImage',
                        src: '/images/HealthNZ_logo_v2.svg',
                        alt: 'Health New Zealand Logo',
                        style: { width: '200px', height: 'auto', marginRight: '1.5em' }
                    }),
                    React.createElement('div', { key: 'headerSeparator', style: styles.headerSeparator }),
                    React.createElement('h1', { style: styles.headerTitle, key: 'title' }, 'Radiology Triage Tool'),
                ]
            ),
            React.createElement('div', { style: styles.searchInputWrapper, key: 'search-wrapper' },
                React.createElement('input', {
                    key: 'input',
                    type: 'text',
                    placeholder: 'Search clinical scenarios...',
                    value: query,
                    onChange: handleSearchInputChange,
                    onClick: handleSearchInputClick,
                    style: styles.input
                })
            )
        ]),

        query.length < 3 ?
        React.createElement(
            'div', { style: styles.sectionButtonsContainer, key: 'section-buttons' },
            uniqueSections.map(sectionName =>
                React.createElement('button', {
                    key: sectionName,
                    onClick: () => handleSectionButtonClick(sectionName),
                    style: { ...styles.sectionButton, ...(selectedSection === sectionName ? styles.sectionButtonActive : {}) }
                }, sectionName)
            )
        ) : null,
        
        React.createElement(AuthorPopover, {
            key: 'author-popover',
            content: popoverContent,
            position: popoverPosition,
            onClose: () => {
                setPopoverPosition(prev => ({ ...prev, visible: false }));
                setPopoverContent(null);
            }
        }),

        React.createElement('div', { key: 'main-content', style: styles.mainContentArea }, [
            (selectedSection || query.length >= 3) ?
            Object.keys(groupedResults).length > 0 ?
            Object.keys(groupedResults).map(sectionName =>
                React.createElement('div', { key: sectionName + '-section-content' }, [
                    React.createElement('h2', {
                        style: styles.sectionHeader,
                        key: 'sh-' + sectionName
                    }, [
                        React.createElement('span', { key: sectionName + '-title-text'}, sectionName), // Title text
                        (rawJsonData && rawJsonData[sectionName] && rawJsonData[sectionName].authors) ? // Only show icon if authors exist
                            React.createElement('span', { // Info icon
                                key: 'info-icon-' + sectionName,
                                onClick: (e) => handleInfoIconClick(e, sectionName),
                                style: styles.infoIcon,
                                title: `Show leads for ${sectionName}`,
                                'data-info-icon-section': sectionName // For click outside logic
                            }, 'ⓘ') : null
                    ]),

                    Object.keys(groupedResults[sectionName]).map(subheadingName =>
                        React.createElement('div', {
                            key: `${sectionName}-${subheadingName}-group`,
                            style: styles.subheadingGroupContainer
                        }, [
                            (subheadingName !== "General" || Object.keys(groupedResults[sectionName]).length === 1 || selectedSection) &&
                            React.createElement('h3', { style: styles.subheadingHeader, key: 'subh-' + subheadingName }, subheadingName),

                            ...groupedResults[sectionName][subheadingName].map((entry, i) =>
                                React.createElement('div', {
                                    style: {...styles.result, marginBottom: i === groupedResults[sectionName][subheadingName].length - 1 ? '0' : '1em' },
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
