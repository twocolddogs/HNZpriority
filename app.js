/* ===============================================================
   app.js  –  Radiology Triage Tool (VIEW ONLY)
   =============================================================== */
import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
} from "https://esm.sh/react";
import { createRoot } from "https://esm.sh/react-dom/client";

const e = React.createElement;
const deepClone = (o) => JSON.parse(JSON.stringify(o));

// HELPER FUNCTION for generating a hash from a card's clinical_scenario string
const scenarioToIdHash = (clinicalScenarioStr) => {
  const str = String(clinicalScenarioStr || '');
  let hash = 0;
  if (str.length === 0) return '0';
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return (hash >>> 0).toString(36);
};


/* ---------- Load fonts ---------- */
const loadFonts = () => {
  const link1 = document.createElement("link");
  link1.rel = "stylesheet";
  link1.href = "/fonts/poppins.css";
  document.head.appendChild(link1);

  const link2 = document.createElement("link");
  link2.rel = "stylesheet";
  link2.href = "/fonts/publicsans.css";
  document.head.appendChild(link2);

  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
      from { transform: translateX(0); opacity: 1; }
      to { transform: translateX(100%); opacity: 0; }
    }
    @keyframes pulse {
      0% { box-shadow: 0 2px 4px rgba(0,0,0,0.04); }
      50% { box-shadow: 0 4px 16px rgba(0, 84, 159, 0.15); }
      100% { box-shadow: 0 2px 4px rgba(0,0,0,0.04); }
    }
  `;
  document.head.appendChild(style);
};

loadFonts();

/* ---------- device helper ---------- */
function useIsMobile(bp = 768) {
  const [mobile, setMobile] = useState(window.innerWidth <= bp);
  useEffect(() => {
    const h = () => setMobile(window.innerWidth <= bp);
    window.addEventListener("resize", h);
    return () => window.removeEventListener("resize", h);
  }, [bp]);
  return mobile;
}

/* ---------- modality-icon helper ---------- */
function getModalityIcon(mo) {
  if (!mo) return null;
  const m = mo.toUpperCase().trim();
  if (m.includes("CT")) return "icons/CT.png";
  if (m.includes("XR")) return "icons/XR.png";
  if (m.includes("MRI")) return "icons/MRI.png";
  if (m.includes("US") && m.includes("ASPIRATION")) return "icons/MAMASP.png";
  if (m.includes("US")) return "icons/US.png";
  if (m.includes("PET")) return "icons/PET.png";
  if (m.includes("DBI")) return "icons/DBI.png";
  if (m.includes("BONE SCAN")) return "icons/BS.png";
  if (m.includes("NUC MED")) return "icons/NM.png";
  if (m.includes("MRA")) return "icons/MR.png";
  if (m.includes("CTA")) return "icons/CT.png";
  if (m.includes("FLUOROSCOPY")) return "icons/XR.png";
  if (m.includes("MAMMOGRAM")) return "icons/MAM.png";
  if (m.includes("ASPIRATION")) return "icons/MAMASP.png";
  return null;
}

/* ---------- AuthorPopOver ---------- */
// VIEW-ONLY: Pass isEdit as false to disable editing controls
function AuthorPopover({ content, position, onClose /*, isEdit, onSave */ }) { // Removed isEdit, onSave from props for view-only
  const isEdit = false; // Force isEdit to false

  const pillBtn = {
    padding: ".28em .8em",
    fontSize: ".75em",
    border: "1px dashed #FFA726",
    background: "#FFF7E6",
    color: "#FF8C00",
    borderRadius: "6px",
    fontWeight: 600,
    cursor: "pointer",
  };
  const [localAuthors, setLocalAuthors] = React.useState(content.authors || {});
  React.useEffect(() => {
    setLocalAuthors(content.authors || {});
  }, [content.authors]);

  // handleFieldChange is no longer needed for view-only
  // const handleFieldChange = (group, idx, field, value) => { ... };

  const popoverStyle = {
    position: 'relative', 
    background: '#fff',
    border: '1px solid #E0E6ED',
    borderRadius: '8px',
    padding: '1em 1.5em',
    minWidth:'280px',
    maxWidth:'100%',
    color:'#4B5563',
    marginTop: '1em', 
    marginBottom: '1em',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    zIndex: 1005,
  };

  const leadGroupHeaderStyle = {
    fontSize:'1em',
    fontWeight:'600',
    color:'#00549F',
    paddingBottom:'0.3em',
    marginBottom:'0.8em',
    fontFamily: "'Poppins', Arial, sans-serif",
  };
  // inputStyle no longer needed for view-only

 const renderLeads = (leads = [], title) => {
    const group = title.includes('Radiology') ? 'Radiology Leads' : 'Clinical Leads';
    return e('div', { style:{ marginBottom:'1.5em' }}, [
      e('h4', { style: leadGroupHeaderStyle }, title),
      ...leads.map((lead, idx) =>
        // VIEW-ONLY: Always render the non-edit version
        e("p", { key: group + idx, style: { fontSize: ".9em", margin: "0 0 0.35em 0" } }, [
          e("strong", null, lead.name || "—"),
          lead.region && `  (${lead.region})`,
        ]),
      ),
      // VIEW-ONLY: Remove "+ Add Lead" button
      // isEdit && e(...)
    ]);
  };

   return e('div', { style: popoverStyle }, [
    e('button', { onClick:onClose,
      style:{
        position:'absolute',
        top:'10px',
        right:'10px',
        border:'none',background:'none',fontSize:'1.4em',color:'#6B7280',cursor:'pointer'
      }
    }, '×'),
   renderLeads(localAuthors['Radiology Leads'], 'Radiology Leads'),
    renderLeads(localAuthors['Clinical Leads'],  'Clinical Leads'),
    // VIEW-ONLY: Remove "Save Authors" button
    // isEdit && e('div', { style:{ textAlign:'right',marginTop:'1em' } }, e('button', ...)),
  ]);
}

/* ---------- ScenarioCard ---------- */
const PRIORITY_CHOICES = [ // Still needed for rendering priorities if data contains them
  "P1", "P2", "P3", "P4", "P5",
  "S1", "S2", "S3", "S4", "S5",
];

// VIEW-ONLY: Pass isEdit as false, remove editing-related props
function ScenarioCard({
  item,
  // section, // Not needed for view-only card logic
  // sub,     // Not needed for view-only card logic
  originalIdx, // Still useful for keys/ID
  // isEdit,  // Will be forced to false
  styles,
  badgeStyles,
  compactBadgeStyle,
  // saveScenario, // Not needed
  // removeScenario, // Not needed
  compactMode,
  mobile,
  // hasChanges, // Not relevant for view-only
}) {
  const isEdit = false; // Force isEdit to false
  // const [local, setLocal] = useState({ ...item }); // Local state for editing not needed
  // useEffect(() => setLocal({ ...item }), [item]); // Not needed

  // onEditField not needed

  const scenarioHash = scenarioToIdHash(item.clinical_scenario);
  const cardAnchorId = `scenario-${scenarioHash}-${originalIdx}`;

  const cardStyles = {
    ...styles.result,
    padding: compactMode
      ? "0.6em 0.8em"
      : styles.result.padding || "0.9em 1.1em",
    // hasChanges styling removed
  };

  // VIEW-ONLY: Only the non-edit rendering path is relevant
  const rawCat = item.prioritisation_category || "";
  const categories = Array.isArray(rawCat)
    ? rawCat
    : rawCat
        .split(",")
        .map((p) => p.trim().toUpperCase())
        .filter(Boolean);
  return e(
    "div",
    { style: cardStyles, id: cardAnchorId },
    e(
      "div",
      { style: styles.text },
      e("span", { style: styles.label }, "Scenario:"),
      " ",
      item.clinical_scenario,
    ),
    e(
      "div",
      { style: styles.text },
      e("span", { style: styles.label }, "Modality:"),
      e(
        "div",
        { style: styles.modalityDisplay },
        ...item.modality.split(/[,>/]/).flatMap((m, i) => {
          const u = getModalityIcon(m.trim());
          return u
            ? [
                e("img", {
                  key: "icon-" + i,
                  src: u,
                  alt: m.trim(),
                  title: m.trim(),
                  style: styles.modalityIcon,
                }),
              ]
            : [];
        }),
        item.modality,
      ),
    ),
    e(
      "div",
      { style: styles.text },
      e("span", { style: styles.label }, "Priority:"),
      " ",
      e(
        "div",
        { style: styles.priorityContainer },
        categories.length > 0
          ? categories.map((cat, i) =>
              e(
                "span",
                {
                  key: "cat-" + i,
                  style: {
                    ...(badgeStyles[cat] || badgeStyles["DEFAULT"]),
                    ...compactBadgeStyle,
                  },
                },
                cat,
              ),
            )
          : e(
              "span",
              { style: { ...badgeStyles["N/A"], ...compactBadgeStyle } },
              "N/A",
            ),
      ),
    ),
    item.comment &&
      item.comment.toLowerCase() !== "none" &&
      item.comment.trim() !== "" &&
      e(
        "div",
        {
          style: {
            ...styles.commentText,
            display: mobile && compactMode ? "none" : "block",
          },
        },
        e("span", { style: styles.label }, "Comments:"),
        " ",
        item.comment,
      ),
  );
}

/* ---------- SubheadingSection Component ---------- */
// VIEW-ONLY: Pass edit as false, remove editing-related props
function SubheadingSection({
  selected,
  sub,
  list,
  isExpanded,
  actualIsEmpty,
  // edit, // Will be forced to false
  searchTerm,
  styles,
  badgeStyles,
  compactBadgeStyle,
  // newlyAddedSubheading, // Not relevant for view-only visuals
  // subheadingHasChanges, // Not relevant
  toggleSubSection,
  // removeSubheading, // Not needed
  // addScenario, // Not needed
  // saveScenario, // Not needed
  // removeScenario, // Not needed
  // scenarioHasChanges, // Not relevant
  keyOf,
  compactMode,
  mobile, 
}) {
  const edit = false; // Force edit to false
  const [isHovered, setIsHovered] = React.useState(false);
  const subKeyForId = `${selected}-${sub}`;
  // const hasSubChanges = subheadingHasChanges(selected, sub); // Not needed
  // const showRemoveSubButton = edit && actualIsEmpty && searchTerm.length < 3 && sub !== "General"; // Not needed

  // Button styles not needed as buttons are removed

  const arrowChar = mobile ? (isExpanded ? "−" : "+") : "▶";
  
  let arrowSpecificStyles = {};
  if (mobile) {
    arrowSpecificStyles = {
      fontSize: "1.2em", 
      fontWeight: "bold",
    };
  } else { 
    arrowSpecificStyles = {
      fontSize: "1.1em",
      fontWeight: "normal",
      transition: "transform 0.3s ease",
      transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
    };
  }

  const disclosureArrowStyle = {
    marginRight: "0.5em",
    display: "inline-block",
    width: "1.1em", 
    textAlign: "center",
    lineHeight: '1', 
    ...arrowSpecificStyles,
  };

  return e(
    "div",
    {
      id: `subheading-${subKeyForId}`,
      style: {
        ...(styles.subheadingCard || {}),
        // subheadingCardHighlighted not needed
        // pulse animation for newlyAddedSubheading not needed
      }
    },
    [
      e(
        "div",
        {
          style: {
            ...(styles.subheadingHeader || {}),
            ...(isHovered ? (styles.subheadingHeaderHover || {}) : {})
          },
          onClick: () => toggleSubSection(selected, sub),
          onMouseEnter: () => setIsHovered(true),
          onMouseLeave: () => setIsHovered(false),
        },
        [
          e(
            "div",
            { style: { display: "flex", alignItems: "center", flex: 1 } },
            [
              e(
                "span",
                { style: disclosureArrowStyle },
                arrowChar
              ),
              e("span", { style: { fontWeight: 600 } }, sub),
              // Change indicator removed
            ]
          ),
          // VIEW-ONLY: Action buttons div removed
          // e( "div", { style: { display: "flex", ... } }, [ ...buttons... ] )
        ]
      ),
      isExpanded && e(
        "div",
        {
          style: list.length > 0 ? (styles.subheadingContent || {}) : (styles.emptySubheadingContent || {})
        },
        list.length > 0
          ? list.map((item, index) =>
              e(
                "div",
                {
                  key: keyOf(selected, sub, item._originalIdx),
                  style: { position: "relative" }
                },
                [
                  e(ScenarioCard, {
                    item,
                    originalIdx: item._originalIdx,
                    // isEdit: edit, // Forced false inside ScenarioCard
                    styles: {
                      ...styles,
                      result: {
                        ...(styles.result || {}),
                        ...(index === list.length - 1 ? { marginBottom: 0 } : {})
                      }
                    },
                    badgeStyles,
                    compactBadgeStyle,
                    compactMode,
                    mobile,
                    // hasChanges: false, // Not relevant
                  }),
                  index < list.length - 1 && e(
                    "div",
                    {
                      style: {
                        position: "absolute",
                        left: "2em",
                        bottom: "0",
                        width: "2px",
                        height: "0.75em",
                        background: "linear-gradient(to bottom, #E0E6ED 0%, transparent 100%)",
                      }
                    }
                  )
                ]
              )
            )
          : e( // VIEW-ONLY: Simplified empty state message
              "p",
              { style: { fontStyle: 'italic', color: '#6B7280'} },
              searchTerm.length >= 3 && list.length === 0 && !actualIsEmpty
                ? `No items match "${searchTerm}" in this sub-heading.`
                : "No scenarios in this sub-heading."
            ),
      ),
    ]
  );
}

/* ---------- App ---------- */
function App() {
  console.log("[App] Component body start / Re-render start (VIEW ONLY)");
  const mobile = useIsMobile();
  const [data, setData] = useState(null);
  const [sections, setSections] = useState([]);
  const [selected, setSelected] = useState(null);
  // const [edit, setEdit] = useState(false); // VIEW-ONLY: edit is always false
  const edit = false; // VIEW-ONLY
  // const [dirty, setDirty] = useState({}); // VIEW-ONLY: No dirty state needed
  // const [rawJsonData, setRawJsonData] = useState(null); // VIEW-ONLY: Not needed if not saving/comparing
  // const [newlyAddedSubheading, setNewlyAddedSubheading] = useState(null); // VIEW-ONLY: No new subheadings
  const mainContentRef = React.useRef(null);

  const [authorPopoverContent, setAuthorPopoverContent] = useState(null);
  const [authorPopoverPosition, setAuthorPopoverPosition] = useState({
    visible: false,
    top: 0,
    left: 0,
  });
  const [collapsedSubs, setCollapsedSubs] = useState({});
  const [compactMode, setCompactMode] = useState(false); // Keep compact mode if desired for viewing
  const [searchTerm, setSearchTerm] = useState("");
  const [isDeepLinking, setIsDeepLinking] = useState(false);
  const [initialHashProcessed, setInitialHashProcessed] = useState(false);

  const APP_BAR_HEIGHT_DESKTOP = "3.2em"; 
  const APP_BAR_HEIGHT_MOBILE = "3.5em";  
  const STICKY_TOP_FOR_SECTION_HEADER = mobile ? APP_BAR_HEIGHT_MOBILE : APP_BAR_HEIGHT_DESKTOP;

  console.log("[App STATE] selected:", selected, "edit:", edit);

  // VIEW-ONLY: markDirtyKey and change tracking not needed
  // const markDirtyKey = ...
  // const sectionHasChanges = ...
  // const subheadingHasChanges = ...
  // const scenarioHasChanges = ...

  const formatLastUpdated = (dateStr) => {
    const trimmedDateStr = typeof dateStr === 'string' ? dateStr.trim() : null;
    if (!trimmedDateStr) return null;
    const date = new Date(trimmedDateStr);
    if (isNaN(date.getTime())) {
      console.error("Invalid date string received by formatLastUpdated:", dateStr, "(trimmed:", trimmedDateStr, ")");
      return "Invalid Date";
    }
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const updateDate = new Date(date); updateDate.setHours(0, 0, 0, 0);
    if (updateDate.getTime() === today.getTime()) return 'Today';
    const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
    if (updateDate.getTime() === yesterday.getTime()) return 'Yesterday';
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const closeAuthorPopover = useCallback(() => {
    setAuthorPopoverPosition({ visible: false, top: 0, left: 0 });
    setAuthorPopoverContent(null);
  }, []);

  useEffect(() => {
    console.log("[useEffect fetchInitialData] Firing");
    fetch(priority_data_set.json) // Production local
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
        return r.json();
      })
      .then((j) => {
        console.log("[useEffect fetchInitialData] Data fetched successfully");
        // setRawJsonData(deepClone(j)); // Not needed for view-only
        setData(deepClone(j)); // Original data is still needed
        const sS = Object.keys(j).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
        setSections(sS);
        const iCS = {};
        Object.keys(j).forEach((sK) => {
          Object.keys(j[sK]).forEach((subK) => {
            if (Array.isArray(j[sK][subK])) iCS[`${sK}-${subK}`] = true;
          });
        });
        setCollapsedSubs(iCS);
      })
      .catch((err) => {
        console.error("[useEffect fetchInitialData] Failed to load data:", err);
        setData({});
        setSections([]);
        alert("Error loading data.");
      });
  }, []);

  useEffect(() => {
    if (!data || isDeepLinking || initialHashProcessed) return;
    const fragment = window.location.hash.substring(1);
    if (fragment && fragment.startsWith('scenario-')) {
      console.log(`[DeepLink] Initial load: Attempting to locate card for fragment: '${fragment}'`);
      setIsDeepLinking(true); setInitialHashProcessed(true);
      let foundSection = null, foundSubheading = null;
      for (const sectionName of Object.keys(data)) {
        if (!data[sectionName] || typeof data[sectionName] !== 'object') continue;
        for (const subheadingName of Object.keys(data[sectionName])) {
          if (subheadingName === 'authors' || subheadingName === 'last_updated' || !Array.isArray(data[sectionName][subheadingName])) continue;
          const scenarios = data[sectionName][subheadingName];
          for (let i = 0; i < scenarios.length; i++) {
            const item = scenarios[i];
            const currentItemHash = scenarioToIdHash(item.clinical_scenario);
            const currentItemId = `scenario-${currentItemHash}-${i}`;
            if (currentItemId === fragment) {
              foundSection = sectionName; foundSubheading = subheadingName; break;
            }
          }
          if (foundSection) break;
        }
        if (foundSection) break;
      }
      if (foundSection && foundSubheading) {
        console.log(`[DeepLink] Card context found: Section='${foundSection}', Subheading='${foundSubheading}'`);
        setSelected(foundSection); setSearchTerm("");
        if (authorPopoverPosition.visible) closeAuthorPopover();
        // setNewlyAddedSubheading(null); // Not relevant
        const subKey = `${foundSection}-${foundSubheading}`;
        setCollapsedSubs(prev => ({ ...prev, [subKey]: false }));
        setTimeout(() => {
          const element = document.getElementById(fragment);
          if (element) {
            console.log(`[DeepLink] Element '${fragment}' found. Applying subtle highlight and clearing hash.`);
            const originalBgColor = element.style.backgroundColor;
            element.style.transition = 'background-color 2s ease-in-out'; element.style.backgroundColor = '#f3e1f7';
            const rect = element.getBoundingClientRect();
            const isCentered = (rect.top >= 0) && (rect.left >= 0) && (rect.bottom <= (window.innerHeight || document.documentElement.clientHeight)) && (rect.right <= (window.innerWidth || document.documentElement.clientWidth)) && (rect.top > window.innerHeight * 0.2 && rect.bottom < window.innerHeight * 0.8);
            if(!isCentered) element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            setTimeout(() => { if (document.body.contains(element)) element.style.backgroundColor = originalBgColor || ''; window.history.replaceState({}, document.title, window.location.pathname + window.location.search); console.log("[DeepLink] Hash cleared from URL."); }, 2500);
          } else { console.warn(`[DeepLink] Element '${fragment}' not found in DOM after delay for highlight.`); }
          setIsDeepLinking(false);
        }, 500);
      } else {
        console.warn(`[DeepLink] Card for fragment '${fragment}' not found in data.`);
        window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
        setIsDeepLinking(false); setInitialHashProcessed(false);
      }
    } else {
      if (fragment && !fragment.startsWith('scenario-')) window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
      setInitialHashProcessed(true);
    }
  }, [data, isDeepLinking, initialHashProcessed, closeAuthorPopover, authorPopoverPosition.visible]);

  // useEffect for edit state change not needed
  // useEffect(() => { if (!selected && edit) setEdit(false); }, [selected, edit]);

  useEffect(() => { // Popover management can stay
    console.log("[useEffect popoverManagement] Firing. authorPopoverPosition.visible:", authorPopoverPosition.visible);
    if (authorPopoverPosition.visible) {
        console.log("[useEffect popoverManagement] Popover is visible, closing it due to selected/compactMode change.");
        closeAuthorPopover();
    }
  }, [selected, /* edit, */ compactMode, closeAuthorPopover]);

  const itemsFilteredBySearch = useMemo(() => {
    const grouped = {};
    if (!data || !selected || !data[selected]) return grouped;
    const secObj = data[selected];
    const searchLower = searchTerm.toLowerCase();
    Object.entries(secObj).forEach(([sub, list]) => {
      if (sub === "authors" || sub === "last_updated" || !Array.isArray(list)) return;
      let scenarios = list.map((item, i) => ({ ...item, _originalIdx: i }));
      if (searchLower)
        scenarios = scenarios.filter(
          (item) =>
            item.clinical_scenario?.toLowerCase().includes(searchLower) ||
            item.modality?.toLowerCase().includes(searchLower) ||
            String(item.prioritisation_category)?.toLowerCase().includes(searchLower) ||
            item.comment?.toLowerCase().includes(searchLower),
        );
      grouped[sub] = scenarios;
    });
    return grouped;
  }, [data, selected, searchTerm]);

  const displayableSubHeadings = useMemo(() => {
    const result = {};
    if (!data || !selected || !data[selected]) return result;
    const searchActive = searchTerm.length >= 3;
    const sectionData = data[selected];
    let allKeys = Object.keys(sectionData).filter((key) => Array.isArray(sectionData[key]));
    allKeys.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
    // newlyAddedSubheading logic not relevant for view-only
    allKeys.forEach((subKey) => {
      const listFromSearch = itemsFilteredBySearch[subKey] || [];
      const actualIsEmpty = (sectionData[subKey] || []).length === 0;
      const collapsedKey = `${selected}-${subKey}`;
      const userPrefCollapsed = collapsedSubs[collapsedKey];
      let isExpanded = userPrefCollapsed === undefined ? true : !userPrefCollapsed;
      // newSubNameFromState logic not relevant
      if (searchActive) {
        if (listFromSearch.length > 0) result[subKey] = { list: listFromSearch, isExpanded: true, actualIsEmpty };
      } else {
        result[subKey] = { list: listFromSearch, isExpanded, actualIsEmpty };
      }
    });
    return result;
  }, [itemsFilteredBySearch, searchTerm, collapsedSubs, selected, data /*, newlyAddedSubheading */]);

  // newlyAddedSubheading useEffect not needed

  const keyOf = (s, sub, originalIdx) => `${s}|${sub}|${originalIdx}`;

  // VIEW-ONLY: Editing functions removed or simplified
  // const saveScenario = ...
  // const removeScenario = ...
  // const addScenario = ...
  // const addSubheadingInternal = ...
  // const addSubheadingViaPrompt = ...
  // const removeSubheading = ...
  // const addSection = ...
  // const downloadJson = ...
  // const generateChangelog = ...

  const handleInfoIconClick = (event, sectionName) => { // Still useful for viewing authors
    event.stopPropagation();
    if (authorPopoverPosition.visible && authorPopoverContent?._sectionName === sectionName) {
      setAuthorPopoverPosition({ visible: false }); setAuthorPopoverContent(null);
    } else {
      setAuthorPopoverPosition({ visible: true });
      setAuthorPopoverContent({ authors: data[sectionName]?.authors || {}, _sectionName: sectionName });
    }
  };
  // const handleSaveAuthors = ... // Not needed

  const toggleSubSection = (sec, sub) => {
    const k = `${sec}-${sub}`;
    setCollapsedSubs((p) => ({ ...p, [k]: !p[k] }));
    // newlyAddedSubheading logic removed
  };

  const headerPaddingBottomEM = 0.4;
  const topBarPaddingDesktopEM = 0.6;
  const topBarPaddingMobileEM = 0.8;
  const calculatedStickyHeaderTopOffsetDesktopEM = topBarPaddingDesktopEM * 2 + headerPaddingBottomEM + 0.5;

  const styles = {
    container: { padding: mobile ? "0.5em" : "1em", fontFamily: "'Public Sans', Arial, sans-serif", background: "#F9FAFB", minHeight: "100vh" },
    appLayout: { display: "grid", gridTemplateColumns: mobile ? "1fr" : "250px 1fr", gap: mobile ? "0.5em" : "1em", maxWidth: "1400px", margin: "0 auto" },
    stickyHeader: { // Main App Bar
      position: "sticky",
      top: 0,
      zIndex: 1002, // Highest
      background: "#F5F7FA",
      paddingBottom: `${headerPaddingBottomEM}em`, // Its own padding
      // No margin-bottom, as the next sticky element will be positioned relative to this.
      // boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
    },
    brandBar: { display: "flex", alignItems: "center", justifyContent: "space-between", background: "linear-gradient(90deg,#143345 45%,#41236a 100%)", padding: mobile ? `${topBarPaddingMobileEM}em 1.2em` : `${topBarPaddingDesktopEM}em 1em`, borderRadius: "6px", maxWidth: "1400px", margin: "0 auto" },
    title: { color: "#fff", fontSize: mobile ? "1em" : "1.3em", margin: 0, fontWeight: 600, fontFamily: "'Poppins', Arial, sans-serif", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
    headerDivider: { width: "1px", height: "30px", background: "rgba(255,255,255,0.3)", margin: mobile ? "0 0.8em" : "0 1.5em", flexShrink: 0 },
    headerControls: { display: "flex", alignItems: "center", gap: mobile ? "0.5em" : "0.8em" },
    sidebar: { position: mobile ? "relative" : "sticky", top: mobile ? "auto" : `${calculatedStickyHeaderTopOffsetDesktopEM}em`, alignSelf: "start", height: mobile ? "auto" : "fit-content", maxHeight: mobile ? "auto" : `calc(100vh - ${calculatedStickyHeaderTopOffsetDesktopEM}em - 2em)`, overflowY: "auto", background: "#fff", borderRadius: "8px", padding: "1em", border: "1px solid #E5EAF0", boxShadow: "0 1px 3px rgba(0,0,0,0.03)", zIndex: 500 },
    mainContent: { background: "#F5F7FA", borderRadius: "10px", padding: mobile ? "1em" : "1.5em", border: "1px solid #E5EAF0", boxShadow: "0 1px 3px rgba(0,0,0,0.03)", position: "relative", zIndex: 1 },
    sectionButtonsContainer: { display: "flex", flexDirection: "column", gap: "0.4em" },
    sectionBtn: { padding: "0.5em 1em", fontSize: "0.85em", textAlign: "left", border: "1px solid #00549F", background: "#fff", color: "#00549F", borderRadius: "6px", cursor: "pointer", fontWeight: 600, transition: "all .2s", width: "100%", fontFamily: "'Poppins', Arial, sans-serif" },
    sectionActive: { background: "#00549F", color: "#fff" },
    stickySectionHeaderWrapper: {
      position: "sticky",
      top: STICKY_TOP_FOR_SECTION_HEADER, 
      zIndex: 1001, 
      background: "#F5F7FA", 
      paddingTop: "1em",      
      paddingBottom: "1em",   
      boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
      // willChange: "top", // Optional: for performance tuning
    },
    sectionHeaderContainer: { 
      display: "flex",
      flexDirection: mobile ? "column" : "row",
      alignItems: mobile ? "flex-start" : "center",
      gap: mobile ? "0.5em" : "0.0em",
      marginBottom: "1em", 
    },
    sectionHeader: { fontSize: mobile ? "1.1em" : "1.25em", color: "#00549F", fontWeight: 700, margin: 0, fontFamily: "'Poppins', Arial, sans-serif" },
    sectionHeaderActions: { display: "flex", alignItems: "center", gap: "0.6em", ...(mobile && { width: "100%", justifyContent: "flex-end" }) },
    searchBar: {
      width: "100%", padding: "0.6em 1em", border: "1px solid #D1D5DB",
      borderRadius: "6px", fontSize: "0.9em", backgroundColor: "#fff",
      boxShadow: "inset 0 1px 2px rgba(0,0,0,0.05)",
    },
    subheadingHeader: { 
      background: "#E8F0F6",
      padding: mobile ? "0.6em 0.9em" : "0.75em 1.1em",
      display: "flex", alignItems: "center", justifyContent: "space-between", cursor: "pointer", color: "#00549F",
      fontWeight: 600, fontFamily: "'Poppins', Arial, sans-serif", fontSize: mobile ? "0.9em" : "0.95em",
      transition: "background 0.3s ease", borderBottom: "1px solid #D1D9E1",
    },
    subheadingHeaderHover: { background: "#D6E4EE", },
    result: { background: "#fff", border: "1px solid #E5EAF0", borderLeft: "4px solid #007A86", borderRadius: "6px", padding: compactMode ? "0.8em 1em" : "1em 1.2em", marginBottom: "0.75em", boxShadow: "0 1px 2px rgba(0,0,0,0.04)", transition: "all 0.2s ease", position: "relative" },
    label: { fontWeight: 700, color: "#00549F", display: "block", marginBottom: "0.25em" },
    text: { fontSize: "0.95em", marginBottom: "0.55em", display: "block", wordBreak: "break-word" },
    textInput: { padding: "0.3em 0.5em", border: "1px solid #ccc", borderRadius: "4px", fontSize: "0.9em" }, // Not used for view-only Scenarios
    commentText: { fontSize: "0.9em", background: "#F8F9FA", padding: "0.55em", borderRadius: "4px", border: "1px solid #D1D5DB", marginTop: "0.3em", wordBreak: "break-word" },
    infoIcon: { width: "20px", height: "20px", cursor: "pointer", flexShrink: 0 },
    // Edit-related button styles removed as buttons are removed
    // addBtn, addInlineBtn, downloadBtn, editBtnStyle
    modalityDisplay: { display: "flex", alignItems: "center", flexWrap: "wrap", gap: "0.3em", marginTop: "0.2em" },
    modalityIcon: { height: "24px", marginRight: "3px", verticalAlign: "middle", opacity: 0.9 },
    priorityContainer: { display: "flex", flexWrap: "wrap", gap: "0.25em", marginTop: "0.2em" },
    compactBadgeStyle: { padding: "2px 6px", fontSize: "0.8em", borderRadius: "3px", display: "inline-block" },
    subheadingCard: { background: "#fff", border: "1px solid #E0E6ED", borderRadius: "12px", marginBottom: "1.2em", overflow: "hidden", boxShadow: "0 2px 4px rgba(0,0,0,0.04)", transition: "all 0.3s ease", },
    subheadingCardHighlighted: { borderColor: "#FFA726", borderWidth: "2px", boxShadow: "0 4px 12px rgba(255, 167, 38, 0.15)", }, // Not used in view-only
    subheadingContent: { padding: "1em", background: "#FAFBFC", borderTop: "1px solid #E0E6ED", minHeight: "60px", },
    emptySubheadingContent: { padding: "2em", textAlign: "center", color: "#9CA3AF", fontStyle: "italic", },
  };

  const badgeStyles = {
    P1: { backgroundColor: "#FFBABA", color: "#D8000C", fontWeight: "bold", border: "1px solid #D8000C" }, "P1-P2": { backgroundColor: "#FFBABA", color: "#D8000C", fontWeight: "bold", border: "1px solid #D8000C" }, "P1-P2A": { backgroundColor: "#FFBABA", color: "#D8000C", fontWeight: "bold", border: "1px solid #D8000C" },
    P2: { backgroundColor: "#FFE2BA", color: "#AA5F00", fontWeight: "bold", border: "1px solid #AA5F00" }, P2A: { backgroundColor: "#FFE2BA", color: "#AA5F00", fontWeight: "bold", border: "1px solid #AA5F00" }, "P2A-P2": { backgroundColor: "#FFE2BA", color: "#AA5F00", fontWeight: "bold", border: "1px solid #AA5F00" }, "P2-P3": { backgroundColor: "#FFE2BA", color: "#7A5C00", fontWeight: "bold", border: "1px solid #7A5C00" },
    P3: { backgroundColor: "#FFF8BA", color: "#5C5000", fontWeight: "bold", border: "1px solid #5C5000" }, "P3 OR P2": { backgroundColor: "#FFE2BA", color: "#AA5F00", fontWeight: "bold", border: "1px solid #AA5F00" },
    P4: { backgroundColor: "#BAE7FF", color: "#004C7A", fontWeight: "bold", border: "1px solid #004C7A" }, "P3-P4": { backgroundColor: "#FFF8BA", color: "#00416A", fontWeight: "bold", border: "1px solid #00416A" },
    P5: { backgroundColor: "#D9D9D9", color: "#4F4F4F", fontWeight: "bold", border: "1px solid #4F4F4F" },
    S1: { backgroundColor: "#D1FAE5", color: "#065F46", fontWeight: "bold", border: "1px solid #065F46" }, S2: { backgroundColor: "#FFE2BA", color: "#AA5F00", fontWeight: "bold", border: "1px solid #AA5F00" }, S3: { backgroundColor: "#FFF8BA", color: "#5C5000", fontWeight: "bold", border: "1px solid #5C5000" }, S4: { backgroundColor: "#BAE7FF", color: "#004C7A", fontWeight: "bold", border: "1px solid #004C7A" }, S5: { backgroundColor: "#D9D9D9", color: "#4F4F4F", fontWeight: "bold", border: "1px solid #4F4F4F" },
    "N/A": { backgroundColor: "#F0F0F0", color: "#555555", fontWeight: "bold", border: "1px solid #555555" }, NIL: { backgroundColor: "#F0F0F0", color: "#555555", fontWeight: "bold", border: "1px solid #555555" }, DEFAULT: { backgroundColor: "#E0E0E0", color: "#333333", fontWeight: "bold", border: "1px solid #777" },
  };

  if (!data) {
    return e( "p", { style: { textAlign: "center", marginTop: "2em", fontSize: "1.2em", color: "#555" } }, "Loading application data…");
  }

  return e(
    "div", { style: styles.container },
    e( "header", { style: styles.stickyHeader },
      e( "div", { style: styles.brandBar },
          e("img", { src: "/images/HealthNZ_logo_v2.svg", alt: "Health NZ Logo", style: { width: mobile ? "80px" : "160px", height: "auto", marginRight: mobile ? "0.5em" : "1em" } }),
          e("div", { style: styles.headerDivider }),
          e( "h1", { style: styles.title }, mobile ? "Triage Tool" : "Radiology Triage Tool"), // VIEW-ONLY: Simplified title
          e("div", { style: { flex: 1 } }),
          // VIEW-ONLY: Header controls (Save, Edit buttons) removed
          // e( "div", { style: styles.headerControls }, ... ),
        )
    ),
    e( "div", { style: styles.appLayout },
      e( "aside", { style: styles.sidebar },
        e( "div", { style: styles.sectionButtonsContainer },
          // VIEW-ONLY: "+ Add Section" button removed
          // edit && e(...),
          sections.map((sec) => {
            // const hasChanges = sectionHasChanges(sec); // Not needed
            return e( "button", { key: "sec-" + sec, onClick: () => { setSelected(sec); setSearchTerm(""); if (authorPopoverPosition.visible) closeAuthorPopover(); /* setNewlyAddedSubheading(null); */ },
                style: { ...styles.sectionBtn, ...(selected === sec ? styles.sectionActive : {}), /* ...(hasChanges ? {...} : {}) */ }, // Change indicators removed
              },
              sec // Just the section name
            );
          }),
        )
      ),
      e( "main", { style: styles.mainContent, ref: mainContentRef },
        !selected
          ? e( "div", { style: { textAlign: "center", marginTop: "3em", color: "#6B7280" } },
              e( "h2", { style: { ...styles.sectionHeader, fontSize: "1.8em", marginBottom: "1em", color: "#4B5563" } }, "Welcome to the Radiology Triage Tool"), // VIEW-ONLY: Title
              e( "div", { style: { maxWidth: "600px", margin: "0 auto", lineHeight: "1.8" } },
                [
                  e( "p", { style: { fontSize: "1.1em", marginBottom: "1.5em" } }, "Select a section to view scenarios."),
                  e( "div", { style: { textAlign: "left", background: "#F8F9FA", padding: "1.5em", borderRadius: "8px", border: "1px solid #E5E7EB" } },
                    [
                      e( "h3", { style: { fontFamily: "'Poppins', Arial, sans-serif", fontSize: "1.1em", marginBottom: "0.8em", color: "#00549F" } }, "Quick Guide:"),
                      e( "ul", { style: { paddingLeft: "1.5em", lineHeight: "2" } },
                        // VIEW-ONLY: Updated Quick Guide
                        ['Choose a Section to browse its content.', 'Use the search bar to find specific scenarios.', 'Click on sub-headings to expand or collapse them.'].map((s) => e("li", {key: s}, s)),
                      ),
                    ],
                  ),
                ],
              ),
            )
          : e("div", { key: selected || 'selected-section-content' }, [
              e("div", { style: styles.stickySectionHeaderWrapper }, [
                e( 'div', { style: styles.sectionHeaderContainer },
                  e('div', { style: { display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '0.2em' } },
                    e('div', { style: { display: 'flex', alignItems: 'center', gap: '0.5em' } },
                      e('h2', { style: styles.sectionHeader }, selected),
                      e('img', { src: 'icons/info.png', alt: `Authors for ${selected}`, onClick: (ev) => handleInfoIconClick(ev, selected), style: styles.infoIcon, title: `View leads for ${selected}`}) // VIEW-ONLY: Title updated
                    ),
                    data[selected]?.last_updated && e( "div", { style: { fontSize: "0.8em", color: "#6B7280", marginTop: "-0.2em" } }, `Updated - ${formatLastUpdated(data[selected].last_updated)}`), // Change indicator logic removed
                  ),
                  e("div", { style: { flexGrow: 1 } }),
                  // VIEW-ONLY: "+ Sub-heading" button removed
                  // e( "div", { style: styles.sectionHeaderActions }, edit && e( "button", ... )),
                ),
                e("input", {
                  type: "search",
                  placeholder: `Search in ${selected}...`,
                  value: searchTerm,
                  onChange: (ev) => setSearchTerm(ev.target.value),
                  style: styles.searchBar
                }),
              ]),

              authorPopoverPosition.visible && authorPopoverContent && e(AuthorPopover, {
                content: authorPopoverContent,
                position: authorPopoverPosition,
                onClose: closeAuthorPopover,
                // isEdit: false, // Forced false in AuthorPopover
                // onSave: handleSaveAuthors // Not needed
              }),

              (Object.keys(displayableSubHeadings).length === 0 && searchTerm.length < 3 && (!data[selected] || Object.keys(data[selected]).filter((k) => Array.isArray(data[selected][k])).length === 0))
                ? e( "div", { style: { textAlign: "left", marginTop: "1em", fontStyle: "italic", color: "#6B7280" } },
                    e("p", null, "No sub-headings or scenarios yet in this section."),
                    // VIEW-ONLY: Edit buttons removed
                  )
                : (searchTerm.length >= 3 && Object.keys(displayableSubHeadings).length === 0)
                  ? e( "p", { style: { fontStyle: "italic", textAlign: "center", paddingTop: "1em", color: "#6B7280" } }, `No scenarios match "${searchTerm}".`)
                  : Object.entries(displayableSubHeadings).map(
                      ([sub, { list, isExpanded, actualIsEmpty }]) => {
                        return e(SubheadingSection, {
                          key: `${selected}-${sub}`, selected, sub, list, isExpanded, actualIsEmpty, /* edit: false, */ searchTerm, styles, badgeStyles,
                          compactBadgeStyle: styles.compactBadgeStyle, /* newlyAddedSubheading, subheadingHasChanges, */ toggleSubSection,
                          /* removeSubheading, addScenario, saveScenario, removeScenario, scenarioHasChanges, */ keyOf, compactMode, mobile,
                        });
                      }
                    ),
            ]),
      ),
    ),
  );
}

createRoot(document.getElementById("root")).render(e(App));
