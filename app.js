/* ===============================================================
   app.js  –  Radiology Triage Tool
   =============================================================== */
import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
} from "https://esm.sh/react";
import { createRoot } from "https://esm.sh/react-dom/client";
import { HelperPage } from "./HelperPage.js"; // Ensure HelperPage.js is in the same directory

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

// Helper to generate badge class name
const getBadgeClass = (category) => {
    if (!category) return 'rtt-badge-default';
    const normalizedCat = String(category).toUpperCase().trim().replace(/[^A-Z0-9\s-]/g, '').replace(/\s+/g, '-');
    return `rtt-badge-${normalizedCat.toLowerCase() || 'default'}`;
};


/* ---------- AuthorPopOver Component ---------- */
function AuthorPopover({ content, position, onClose, isEdit, onSave }) {
  const [localAuthors, setLocalAuthors] = React.useState(() => content.authors || {});
  
  React.useEffect(() => {
    // Reset local authors whenever content changes (including section change)
    setLocalAuthors(content.authors || {});
  }, [content.authors, content._sectionName]);

  const handleFieldChange = (group, idx, field, value) => {
    setLocalAuthors((prev) => {
      const updated = JSON.parse(JSON.stringify(prev));
      if (!updated[group]) updated[group] = [];
      if (field === "__delete") {
        updated[group].splice(idx, 1);
        return updated;
      }
      while (updated[group].length <= idx) {
        updated[group].push({ name: "", region: "" });
      }
      updated[group][idx][field] = value;
      return updated;
    });
  };

 const renderLeads = (leads = [], title) => {
    const group = title.includes('Radiology') ? 'Radiology Leads' : 'Clinical Leads';
    return e('div', { className: 'rtt-author-leads-group' }, [
      e('h4', { className: 'rtt-author-lead-group-header' }, title),
      ...leads.map((lead, idx) =>
        isEdit
          ? e(
              "div",
              {
                key: group + idx,
                className: "rtt-author-lead-item-edit",
              },
              [
                e("input", {
                  value: lead.name,
                  placeholder: "Name",
                  onChange: (ev) =>
                    handleFieldChange(group, idx, "name", ev.target.value),
                  className: "rtt-author-input rtt-text-input rtt-author-input-flex-2", // Added rtt-text-input for base styling
                }),
                e("input", {
                  value: lead.region,
                  placeholder: "Region",
                  onChange: (ev) =>
                    handleFieldChange(group, idx, "region", ev.target.value),
                  className: "rtt-author-input rtt-text-input rtt-author-input-flex-1", // Added rtt-text-input
                }),
                e(
                  "button",
                  {
                    className: "rtt-author-lead-delete-btn",
                    onClick: () => handleFieldChange(group, idx, "__delete"),
                  },
                  "×",
                ),
              ],
            )
          : e("p", { key: group + idx, className: "rtt-author-lead-item-view" }, [
              e("strong", null, lead.name || "—"),
              lead.region && `  (${lead.region})`,
            ]),
      ),
      isEdit &&
        e(
          "button",
          {
            className: "rtt-author-pill-btn", // This is the smaller "add" button
            onClick: () => handleFieldChange(group, leads.length, "name", ""),
          },
          "+ Add Lead",
        ),
    ]);
  };

   return e('div', { className: 'rtt-author-popover' }, [
    e('button', { onClick:onClose, className: 'rtt-author-popover-close-btn' }, '×'),
    renderLeads(localAuthors['Radiology Leads'], 'Radiology Leads'),
    renderLeads(localAuthors['Clinical Leads'],  'Clinical Leads'),
    isEdit && e('div', { className: 'rtt-author-save-actions' },
      e('button',
          {
            onClick: () => onSave(localAuthors),
            className: 'rtt-author-save-btn',
          },
          "Save Authors",
        ),
      ),
  ]);
}


/* ---------- ScenarioCard Component ---------- */
const PRIORITY_CHOICES = [
  "P1", "P2", "P3", "P4", "P5",
  "S1", "S2", "S3", "S4", "S5",
];

function ScenarioCard({
  item,
  section, // Keep section prop if used elsewhere, though not directly in this snippet
  sub,     // Keep sub prop if used elsewhere
  originalIdx,
  isEdit,
  saveScenario,
  removeScenario,
  compactMode,
  mobile,
  hasChanges,
}) {
  const [local, setLocal] = useState({ ...item });
  useEffect(() => setLocal({ ...item }), [item]);

  const onEditField = (field, value) => {
    const updatedLocal = { ...local, [field]: value };
    setLocal(updatedLocal);
    saveScenario(section, sub, originalIdx, updatedLocal);
  };

  const scenarioHash = scenarioToIdHash(item.clinical_scenario);
  const cardAnchorId = `scenario-${scenarioHash}-${originalIdx}`;

  const cardClasses = [
    "rtt-result",
    compactMode ? "rtt-scenario-card-padding-compact" : "rtt-scenario-card-padding-default",
    hasChanges ? "rtt-scenario-card-has-changes" : ""
  ].filter(Boolean).join(" ");


  if (!isEdit) {
    const rawCat = item.prioritisation_category || "";
    const categories = Array.isArray(rawCat)
      ? rawCat
      : rawCat
          .split(",")
          .map((p) => p.trim().toUpperCase())
          .filter(Boolean);

    // REORDERED HIERARCHY FOR VIEW MODE: Scenario -> Priority -> Modality -> Comment
    return e(
      "div",
      { className: cardClasses, id: cardAnchorId },
      // 1. Scenario
      e(
        "div",
        { className: "rtt-text" },
        e("span", { className: "rtt-label" }, "Scenario:"),
        " ",
        item.clinical_scenario,
      ),
      // 2. Priority
      e(
        "div",
        { className: "rtt-text" }, // You might want a specific class if styling differs
        e("span", { className: "rtt-label" }, "Priority:"),
        " ",
        e(
          "div",
          { className: "rtt-priority-container" }, // Container for badges
          categories.length > 0
            ? categories.map((cat, i) =>
                e(
                  "span",
                  {
                    key: "cat-" + i,
                    className: `${getBadgeClass(cat)} rtt-compact-badge`, // Badge classes
                  },
                  cat,
                ),
              )
            : e(
                "span",
                { className: `${getBadgeClass("N/A")} rtt-compact-badge` },
                "N/A",
              ),
        ),
      ),
      // 3. Modality
      e(
        "div",
        { className: "rtt-text" },
        e("span", { className: "rtt-label" }, "Modality:"),
        e(
          "div",
          { className: "rtt-modality-display" }, // Container for modality icons + text
          ...item.modality.split(/[,>/]/).flatMap((m, i) => {
            const u = getModalityIcon(m.trim());
            return u
              ? [
                  e("img", {
                    key: "icon-" + i,
                    src: u,
                    alt: m.trim(),
                    title: m.trim(),
                    className: "rtt-modality-icon",
                  }),
                ]
              : [];
          }),
          item.modality, // Display the modality text as well
        ),
      ),
      // 4. Comment (if exists)
      item.comment &&
        item.comment.toLowerCase() !== "none" &&
        item.comment.trim() !== "" &&
        e(
          "div",
          {
            className: `rtt-comment-text ${mobile && compactMode ? 'rtt-comment-text-conditional-hide' : ''}`,
          },
          e("span", { className: "rtt-label" }, "Comments:"),
          " ",
          item.comment,
        ),
    );
  }

  // Edit Mode
  return e(
    "div",
    { className: cardClasses, id: cardAnchorId },
    [
      e(
        "label",
        { className: "rtt-label" },
        "Scenario:",
        e("textarea", {
          className: "rtt-text-input rtt-scenario-edit-textarea",
          value: local.clinical_scenario,
          onChange: (ev) => onEditField("clinical_scenario", ev.target.value),
        }),
      ),
      e(
        "label",
        { className: "rtt-label" },
        "Modality:",
        e("input", {
          className: "rtt-text-input rtt-scenario-edit-input",
          value: local.modality,
          onChange: (ev) => onEditField("modality", ev.target.value),
        }),
      ),
      e(
        "div",
        { className: "rtt-priority-label-wrapper" },
        e(
          "span",
          {
            className: "rtt-label rtt-priority-label",
          },
          "Priority:",
        ),
        e(
          "div",
          { className: "rtt-priority-container" },
          PRIORITY_CHOICES.map((pri) => {
            const currentCategories = Array.isArray(local.prioritisation_category)
              ? local.prioritisation_category
              : (local.prioritisation_category || "")
                  .split(",")
                  .map((p) => p.trim().toUpperCase())
                  .filter(Boolean);
            const isSelected = currentCategories.includes(pri);
            const priorityButtonClasses = [
                getBadgeClass(pri),
                "rtt-compact-badge",
                "rtt-priority-choice-btn",
                isSelected ? "rtt-priority-choice-btn-selected" : ""
            ].filter(Boolean).join(" ");

            return e(
              "button",
              {
                key: "pri-" + pri,
                onClick: () => {
                  const next = isSelected
                    ? currentCategories.filter((p) => p !== pri)
                    : [...currentCategories, pri].filter(Boolean);
                  onEditField(
                    "prioritisation_category",
                    next.length > 0 ? next.join(",") : "",
                  );
                },
                className: priorityButtonClasses,
              },
              pri,
            );
          }),
        ),
      ),
      e(
        "label",
        { className: "rtt-label" },
        "Comments:",
        e("textarea", {
          className: "rtt-text-input rtt-scenario-edit-input rtt-scenario-edit-comment-textarea",
          value: local.comment,
          onChange: (ev) => onEditField("comment", ev.target.value),
        }),
      ),
      e(
        "div",
        { className: "rtt-scenario-remove-actions" },
        e(
          "button",
          {
            onClick: () => removeScenario(section, sub, originalIdx),
            className: "rtt-scenario-remove-btn",
          },
          "Remove",
        ),
      ),
    ]
  );
}


/* ---------- SubheadingSection Component ---------- */
function SubheadingSection({
  selected,
  sub,
  list,
  isExpanded,
  actualIsEmpty,
  edit,
  searchTerm,
  newlyAddedSubheading,
  subheadingHasChanges,
  toggleSubSection,
  removeSubheading,
  addScenario,
  saveScenario,
  removeScenario,
  scenarioHasChanges,
  keyOf,
  compactMode,
  mobile,
}) {
  const subKeyForId = `${selected}-${sub}`;
  const hasSubChangesResult = subheadingHasChanges(selected, sub);
  const showRemoveSubButton = edit && actualIsEmpty && searchTerm.length < 3 && sub !== "General";

  const arrowChar = mobile ? (isExpanded ? "−" : "+") : "▶";

  const disclosureArrowClasses = [
    "rtt-disclosure-arrow",
    mobile ? "" : "rtt-disclosure-arrow-desktop",
    !mobile && isExpanded ? "rtt-disclosure-arrow-desktop-expanded" : "",
    !mobile && !isExpanded ? "rtt-disclosure-arrow-desktop-collapsed" : ""
  ].filter(Boolean).join(" ");

  const subheadingCardClasses = [
    "rtt-subheading-card",
    hasSubChangesResult ? "rtt-subheading-card-highlighted" : "",
    (newlyAddedSubheading?.section === selected && newlyAddedSubheading?.sub === sub) ? "rtt-subheading-card-pulsing" : ""
  ].filter(Boolean).join(" ");

  return e(
    "div",
    {
      id: `subheading-${subKeyForId}`,
      className: subheadingCardClasses,
    },
    [
      e(
        "div",
        {
          className: "rtt-subheading-header",
          onClick: () => toggleSubSection(selected, sub),
        },
        [
          e(
            "div",
            { className: "rtt-subheading-title-wrapper" },
            [
              e(
                "span",
                { className: disclosureArrowClasses },
                arrowChar
              ),
              e("span", { style: { fontWeight: 600 } }, sub), // Subheading title text
              hasSubChangesResult && e( "span", { className: "rtt-subheading-changed-indicator" }),
            ]
          ),
          e(
            "div",
            { className: "rtt-subheading-actions" },
            [
              showRemoveSubButton && e(
                "button",
                {
                  className: "rtt-subheading-remove-btn",
                  title: `Remove "${sub}"`,
                  onClick: (ev) => {
                    ev.stopPropagation();
                    removeSubheading(selected, sub);
                  }
                },
                "Remove"
              ),
              edit && e(
                "button",
                {
                  className: "rtt-subheading-add-scenario-btn",
                  onClick: (ev) => {
                    ev.stopPropagation();
                    addScenario(selected, sub);
                  }
                },
                "+ Scenario"
              ),
            ]
          ),
        ]
      ),
      isExpanded && e(
        "div",
        {
          className: list.length > 0 ? "rtt-subheading-content" : "rtt-empty-subheading-content"
        },
        list.length > 0
          ? list.map((item, index) =>
              e(
                "div",
                {
                  key: keyOf(selected, sub, item._originalIdx),
                  className: `rtt-scenario-item-wrapper ${index === list.length - 1 ? 'is-last-scenario-item' : ''}`
                },
                [
                  e(ScenarioCard, {
                    item,
                    section: selected,
                    sub,
                    originalIdx: item._originalIdx,
                    isEdit: edit,
                    saveScenario,
                    removeScenario,
                    compactMode,
                    mobile,
                    hasChanges: scenarioHasChanges(selected, sub, item._originalIdx),
                  }),
                  index < list.length - 1 && e( "div", { className: "rtt-scenario-connector-line" })
                ]
              )
            )
          : e(
              "p",
              null,
              searchTerm.length >= 3 && list.length === 0 && !actualIsEmpty
                ? `No items match "${searchTerm}" in this sub-heading.`
                : edit && actualIsEmpty && searchTerm.length < 3
                ? 'No scenarios yet. Click "+ Scenario" to add one.'
                : !edit && actualIsEmpty
                ? "No scenarios in this sub-heading."
                : ""
            ),
      ),
    ]
  );
}

/* ---------- App Component ---------- */
function App() {
  const isEditorMode = window.location.hostname === 'editor.hnzradtools.nz' ||
                       window.location.hostname === 'localhost';

  console.log(`[App] Mode: ${isEditorMode ? 'Editor' : 'View-Only'} | Hostname: ${window.location.hostname}`);
  const mobile = useIsMobile();
  const [data, setData] = useState(null);
  const [sections, setSections] = useState([]);
  const [selected, setSelected] = useState(null);
  const [edit, setEdit] = useState(false);
  const [dirty, setDirty] = useState({});
  const [rawJsonData, setRawJsonData] = useState(null);
  const [newlyAddedSubheading, setNewlyAddedSubheading] = useState(null);
  const mainContentRef = React.useRef(null);
  const [currentPage, setCurrentPage] = useState('triage');

   const [hamburgerOpen, setHamburgerOpen] = useState(false);

      useEffect(() => {
        if (!mobile) setHamburgerOpen(false);
         }, [mobile, currentPage, selected, edit]);

  const [authorPopoverContent, setAuthorPopoverContent] = useState(null);
  const [authorPopoverPosition, setAuthorPopoverPosition] = useState({
    visible: false, top: 0, left: 0,
  });
  const [collapsedSubs, setCollapsedSubs] = useState({});
  const [compactMode, setCompactMode] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [isDeepLinking, setIsDeepLinking] = useState(false);
  const [initialHashProcessed, setInitialHashProcessed] = useState(false);

  console.log("[App STATE] currentPage:", currentPage, "selected:", selected, "edit:", edit, "isEditorMode:", isEditorMode);

  const markDirtyKey = (k, v = true) => setDirty((p) => ({ ...p, [k]: v }));

  const sectionHasChanges = useCallback((sectionName) =>
    isEditorMode && Object.keys(dirty).some((key) => {
      let s = key.split("|")[0];
      if (key.startsWith("new_section_")) s = key.replace("new_section_", "");
      else if (key.includes("_new_subheading_")) s = key.split("_new_subheading_")[0];
      else if (key.endsWith("_authors")) s = key.replace("_authors", "");
      else if (key.includes("_subheading_removed_")) s = key.split("_subheading_removed_")[0];
      return s === sectionName;
    }), [dirty, isEditorMode]);

  const subheadingHasChanges = useCallback((sectionName, subName) =>
    isEditorMode && Object.keys(dirty).some((key) => {
      if (
        key === `${sectionName}_new_subheading_${subName}` ||
        key === `${sectionName}_subheading_removed_${subName}`
      ) return true;
      const [s, sub] = key.split("|");
      return s === sectionName && sub === subName;
    }), [dirty, isEditorMode]);

  const scenarioHasChanges = useCallback((sectionName, subName, idx) => {
    if (!isEditorMode) return false;
    const k = keyOf(sectionName, subName, idx);
    return dirty[k] || dirty[k + "_added"] || dirty[k + "_removed"];
  }, [dirty, isEditorMode]);


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

  useEffect(() => { // Fetch initial data
    console.log("[useEffect fetchInitialData] Firing");
    fetch("priority_data_set.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
        return r.json();
      })
      .then((j) => {
        console.log("[useEffect fetchInitialData] Data fetched successfully");
        setRawJsonData(deepClone(j));
        setData(deepClone(j));
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

  useEffect(() => { // Page navigation and edit mode management
    if (currentPage !== 'triage' && edit) {
        console.log("[useEffect currentPageChange] Navigating away from triage while in edit mode. Turning edit off.");
        setEdit(false);
    }
    if (currentPage === 'triage' && window.location.hash === '#helper') {
      window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
    } else if (currentPage === 'helper' && window.location.hash.startsWith('#scenario-')) {
      window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
    }
  }, [currentPage, edit]);


  useEffect(() => { // Deep linking logic
    if (!data || isDeepLinking ) return;

    const processHash = () => {
        const fragment = window.location.hash.substring(1);
        console.log("[DeepLink] Processing hash:", fragment, " initialHashProcessed:", initialHashProcessed);

        if (initialHashProcessed && !fragment) {
            return;
        }

        if (fragment === 'helper') {
            if (currentPage !== 'helper') {
                console.log("[DeepLink] Navigating to Helper page via hash.");
                setCurrentPage('helper');
            }
            setInitialHashProcessed(true);
            return;
        }

        if (currentPage !== 'triage') {
            console.log("[DeepLink] Not on triage page, skipping scenario deep link. Current page:", currentPage);
            if (fragment.startsWith('scenario-')) {
                 window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
            }
            setInitialHashProcessed(true);
            return;
        }

        if (fragment && fragment.startsWith('scenario-')) {
          console.log(`[DeepLink] Triage page: Attempting to locate card for fragment: '${fragment}'`);
          setIsDeepLinking(true);
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
            setNewlyAddedSubheading(null);
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
            setIsDeepLinking(false);
          }
        } else if (fragment) {
            console.log("[DeepLink] Clearing unknown hash:", fragment);
            window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
        }
        setInitialHashProcessed(true);
    };

    if (!initialHashProcessed) {
      processHash();
    }

    const handleHashChange = () => {
        console.log("[DeepLink] Hash changed event fired. New hash:", window.location.hash);
        setInitialHashProcessed(false);
        setIsDeepLinking(false);
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);

  }, [data, isDeepLinking, initialHashProcessed, closeAuthorPopover, authorPopoverPosition.visible, currentPage]);


  useEffect(() => { // Edit mode consistency check
    console.log("[useEffect selectedOrEditChange] Firing. Selected:", selected, "Edit:", edit, "currentPage:", currentPage);
    if ((!isEditorMode && edit) || (currentPage === 'triage' && !selected && edit)) {
      console.log("[useEffect selectedOrEditChange] Forcing edit mode off due to invalid state.");
      setEdit(false);
    }
  }, [selected, edit, isEditorMode, currentPage]);

  useEffect(() => { // Popover management
    if (authorPopoverPosition.visible && currentPage === 'triage') {
        // Check if selected, edit, or compactMode changed *while* popover was visible.
        // This effect will also run if `closeAuthorPopover` identity changes, which is fine.
        // Or if `currentPage` changes away from 'triage'
        // The primary goal is to close the popover if the context it was opened in changes significantly.
        // Consider if this logic is too aggressive or if it should be more targeted.
        // For now, if selected section changes, or edit mode toggles, or compact mode toggles, it closes.
        // And if page changes, it should close.
        // This seems reasonable. The original was:
        // if (authorPopoverPosition.visible && currentPage === 'triage') {
        // console.log("[useEffect popoverManagement] Popover is visible, closing it due to selected/edit/compactMode change.");
        // closeAuthorPopover();
        // }
        // No specific action needed here if the popover content/position is reset by other effects (e.g., when `selected` changes).
        // However, if `selected` is the *same* but `edit` toggles, we might want to close it.
        // Let's refine: close if `selected` changes, or `edit` changes for the *current* selected section, or `currentPage` isn't triage.
    }
  }, [selected, edit, compactMode, currentPage, closeAuthorPopover]); // Added currentPage and closeAuthorPopover to dependencies

  const itemsFilteredBySearch = useMemo(() => {
    const grouped = {};
    if (!data || !selected || !data[selected] || currentPage !== 'triage') return grouped;
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
  }, [data, selected, searchTerm, currentPage]);

  const displayableSubHeadings = useMemo(() => {
    const result = {};
    if (!data || !selected || !data[selected] || currentPage !== 'triage') return result;

    const searchActive = searchTerm.length >= 3;
    const sectionData = data[selected];
    let allKeys = Object.keys(sectionData).filter((key) => Array.isArray(sectionData[key]));
    allKeys.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));

    const isNewlyAddedRelevant = newlyAddedSubheading && newlyAddedSubheading.section === selected;
    const newSubNameFromState = isNewlyAddedRelevant ? newlyAddedSubheading.sub : null;

    if (newSubNameFromState) {
      if (sectionData[newSubNameFromState] && !allKeys.includes(newSubNameFromState)) {
        allKeys.unshift(newSubNameFromState);
      } else if (allKeys.includes(newSubNameFromState)) {
        allKeys = [newSubNameFromState, ...allKeys.filter(key => key !== newSubNameFromState)];
      }
    }

    allKeys.forEach((subKey) => {
      const listFromSearch = itemsFilteredBySearch[subKey] || [];
      const actualIsEmpty = (sectionData[subKey] || []).length === 0;
      const collapsedKey = `${selected}-${subKey}`;
      const userPrefCollapsed = collapsedSubs[collapsedKey];
      let isExpanded = userPrefCollapsed === undefined ? true : !userPrefCollapsed;
      if (subKey === newSubNameFromState) isExpanded = true;

      if (searchActive) {
        if (listFromSearch.length > 0) {
          result[subKey] = { list: listFromSearch, isExpanded: true, actualIsEmpty };
        } else if (subKey === newSubNameFromState) { // Ensure newly added (empty) subheading shows if it's the one added
          result[subKey] = { list: [], isExpanded: true, actualIsEmpty: true };
        }
      } else {
        result[subKey] = { list: listFromSearch, isExpanded, actualIsEmpty };
      }
    });
    return result;
  }, [itemsFilteredBySearch, searchTerm, collapsedSubs, selected, data, newlyAddedSubheading, currentPage]);


  useEffect(() => { // newlyAddedSubheading timeout
    if (newlyAddedSubheading) {
      const timer = setTimeout(() => setNewlyAddedSubheading(null), 30000); // Increased timeout
      return () => clearTimeout(timer);
    }
  }, [newlyAddedSubheading]);

  const keyOf = (s, sub, originalIdx) => `${s}|${sub}|${originalIdx}`;

  const saveScenario = (sec, sub, originalIdx, obj) => {
    if (!isEditorMode) return;
    setData((p) => { const c = deepClone(p); c[sec][sub][originalIdx] = obj; return c; });
    markDirtyKey(keyOf(sec, sub, originalIdx), true);
  };
  const removeScenario = (sec, sub, originalIdx) => {
    if (!isEditorMode) return;
    if (!confirm("Remove scenario?")) return;
    setData((p) => { const c = deepClone(p); c[sec][sub].splice(originalIdx, 1); return c; });
    markDirtyKey(keyOf(sec, sub, originalIdx) + "_removed", true);
  };
  const addScenario = (sec, sub = "General") => {
    if (!isEditorMode) return;
    const txt = prompt("Scenario:");
    if (!txt || !txt.trim()) return;
    setData((p) => {
      const c = deepClone(p);
      if (!c[sec]) c[sec] = { authors: {}, last_updated: "" };
      if (!c[sec][sub]) c[sec][sub] = [];
      c[sec][sub].unshift({ clinical_scenario: txt, modality: "N/A", prioritisation_category: "", comment: "" });
      return c;
    });
    markDirtyKey(keyOf(sec, sub, 0) + "_added", true);
    setCollapsedSubs((prev) => ({ ...prev, [`${sec}-${sub}`]: false })); // Expand subheading
  };

  const addSubheadingInternal = (sec, name) => {
    if (!isEditorMode) return false;
    if (!data || !data[sec]) { alert(`Error: Section '${sec}' not found.`); return false; }
    if (name === "authors" || name === "last_updated") { alert("The names 'authors' and 'last_updated' are reserved."); return false; }
    if (data[sec][name] && Array.isArray(data[sec][name])) { alert(`The sub-heading "${name}" already exists.`); return false; }

    setData((prevData) => {
      const currentSectionData = deepClone(prevData[sec]);
      const { authors, last_updated, ...restSubheadings } = currentSectionData;

      // Preserve authors and last_updated if they exist
      const newSectionStructure = {};
      if (authors !== undefined) newSectionStructure.authors = authors;
      if (last_updated !== undefined) newSectionStructure.last_updated = last_updated;

      // Add the new subheading and existing ones
      const updatedSubheadings = { [name]: [], ...restSubheadings };

      // Sort only the array-holding keys (subheadings)
      const sortedSubheadingKeys = Object.keys(updatedSubheadings)
        .filter(k => Array.isArray(updatedSubheadings[k]))
        .sort((a,b) => a.localeCompare(b, undefined, {sensitivity: 'base'}));

      const finalSortedSubheadings = {};
      sortedSubheadingKeys.forEach(key => {
        finalSortedSubheadings[key] = updatedSubheadings[key];
      });

      return { ...prevData, [sec]: { ...newSectionStructure, ...finalSortedSubheadings } };
    });
    markDirtyKey(sec + "_new_subheading_" + name, true);
    setCollapsedSubs((prev) => ({ ...prev, [`${sec}-${name}`]: false })); // Expand new subheading
    setNewlyAddedSubheading({ section: sec, sub: name });
    return true;
  };

  const addSubheadingViaPrompt = (sec) => {
    if (!isEditorMode) return;
    const n = prompt("New sub-heading name:");
    if (!n || !n.trim()) return;
    const trimmedName = n.trim();
    if (addSubheadingInternal(sec, trimmedName)) {
      // Show success toast
      const successMsg = document.createElement('div');
      successMsg.textContent = `Sub-heading "${trimmedName}" created successfully!`;
      successMsg.className = 'rtt-success-toast';
      document.body.appendChild(successMsg);
      setTimeout(() => {
        successMsg.classList.add('rtt-success-toast-slideout');
        setTimeout(() => { if (document.body.contains(successMsg)) document.body.removeChild(successMsg); }, 300);
      }, 3000);
    }
  };
  const removeSubheading = (sec, subToRemove) => {
    if (!isEditorMode) return;
    if (!confirm(`Remove "${subToRemove}"? This will also remove all scenarios under it.`)) return;
    setData((p) => { const c = deepClone(p); if (c[sec] && c[sec][subToRemove]) delete c[sec][subToRemove]; return c; });
    markDirtyKey(`${sec}_subheading_removed_${subToRemove}`, true);
  };
  const addSection = () => {
    if (!isEditorMode) return;
    const n = prompt("New section name:");
    if (!n || !n.trim()) return;
    if (data[n]) { alert("A section with this name already exists."); return; }
    const nSD = { authors: {}, General: [] }; // New section includes authors and a default "General" subheading
    setData((p) => ({ ...p, [n]: nSD }));
    setSections((p) => [...p, n].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" })));
    setSelected(n); // Select the new section
    setEdit(true); // Ensure edit mode is active
    markDirtyKey("new_section_" + n, true);
    setCollapsedSubs((p) => ({ ...p, [`${n}-General`]: false })); // Expand the default "General"
  };

  const downloadJson = () => {
    if (!isEditorMode) return;
    if (!Object.keys(dirty).length) { alert("No changes to save."); return; }
    const uD = deepClone(data);
    const today = new Date().toISOString().split("T")[0];
    const mS = new Set(); // Modified Sections
    Object.keys(dirty).forEach((k) => {
      let s; // section name
      if (k.startsWith("new_section_")) s = k.replace("new_section_", "");
      else if (k.includes("_new_subheading_")) s = k.split("_new_subheading_")[0];
      else if (k.endsWith("_authors")) s = k.replace("_authors", "");
      else if (k.includes("_subheading_removed_")) s = k.split("_subheading_removed_")[0];
      else if (k.includes("|")) s = k.split("|")[0];

      if (s && uD[s]) mS.add(s);
    });
    mS.forEach((s) => { if (uD[s]) uD[s].last_updated = today; }); // Update last_updated for modified sections
    const cL = generateChangelog(dirty, rawJsonData, uD, today);
    const jB = new Blob([JSON.stringify(uD, null, 2)], { type: "application/json" });
    const jU = URL.createObjectURL(jB);
    const jL = document.createElement("a"); jL.href = jU; jL.download = "updated_priority_data_set.json"; jL.click();
    setTimeout(() => { // Delay changelog download slightly
      const cB = new Blob([cL], { type: "text/plain" });
      const cU = URL.createObjectURL(cB);
      const cLk = document.createElement("a"); cLk.href = cU; cLk.download = `changelog_${today}_${Date.now()}.txt`; cLk.click();
      URL.revokeObjectURL(jU); URL.revokeObjectURL(cU);
    }, 100);
    setData(uD); // Update internal state to reflect saved data
    setDirty({}); // Clear dirty flags
    setRawJsonData(deepClone(uD)); // Update base data for future diffs
  };

  const generateChangelog = (dK, oD, cD, date) => { // dirtyKeys, oldData, currentData
    let l = `RADIOLOGY TRIAGE TOOL - CHANGELOG\nDate: ${date}\nTime: ${new Date().toLocaleTimeString()}\n=======================================\n\n`;
    const C = { s: { a: [], m: new Set() }, h: { a: [], r: [] }, x: { a: [], r: [], m: [] }, u: [] }; // Sections, subHeadings, scenarios(X), authors(U)

    Object.keys(dK).forEach((k) => {
      if (k.startsWith("new_section_")) C.s.a.push(k.replace("new_section_", ""));
      else if (k.includes("_new_subheading_")) { const [s, h] = k.replace("_new_subheading_", "|").split("|"); C.h.a.push({ s, h }); C.s.m.add(s); }
      else if (k.includes("_subheading_removed_")) { const [s, h] = k.replace("_subheading_removed_", "|").split("|"); C.h.r.push({ s, h }); C.s.m.add(s); }
      else if (k.endsWith("_authors")) { const s = k.replace("_authors", ""); C.u.push({ s, d: cD[s]?.authors || {} }); C.s.m.add(s); }
      else if (k.includes("|")) { // Scenario changes
        const [s, h, iS] = k.split("|"); const oI = parseInt(iS); C.s.m.add(s); // Mark section as modified
        if (k.endsWith("_added")) { const x = cD[s]?.[h]?.[0]; if (x) C.x.a.push({ s, h, ...x }); } // New scenario is at index 0
        else if (k.endsWith("_removed")) C.x.r.push({ s, h, oI }); // original Index for removed
        else { const x = cD[s]?.[h]?.[oI]; if (x) C.x.m.push({ s, h, i: oI, ...x }); } // Modified scenario
      }
    });

    if (C.s.a.length) { l += `NEW SECTIONS ADDED:\n`; C.s.a.forEach((s) => { l += ` • ${s}\n`; const sd = cD[s]; if (sd) { const hs = Object.keys(sd).filter((k) => Array.isArray(sd[k])); if (hs.length) l += `    Initial Sub-headings: ${hs.join(", ")}\n`; } }); l += `\n`; }
    if (C.s.m.size) { l += `MODIFIED SECTIONS (Updates within these sections):\n`; Array.from(C.s.m).forEach((s) => { if (!C.s.a.includes(s)) l += ` • ${s}\n`; }); l += `\n`; } // List modified sections not already listed as new

    if (C.h.a.length) { l += `NEW SUB-HEADINGS ADDED:\n`; C.h.a.forEach(({ s, h }) => (l += ` • "${h}" (in section "${s}")\n`)); l += `\n`; }
    if (C.h.r.length) { l += `SUB-HEADINGS REMOVED:\n`; C.h.r.forEach(({ s, h }) => (l += ` • "${h}" (from section "${s}")\n`)); l += `\n`; }

    const logScenarios = (type, list) => {
      if (!list.length) return;
      l += `${type.toUpperCase()} SCENARIOS (${list.length}):\n`;
      list.forEach((item, idx) => {
        l += `\n ${idx + 1}. Section: "${item.s}" > Sub-heading: "${item.h}"`;
        if (type === "modified" || type === "removed") l += ` (Original Index: ${item.i !== undefined ? item.i : item.oI})`;
        l += `\n`;
        if (item.clinical_scenario) { // For new or modified
          l += `    Scenario: ${item.clinical_scenario}\n`;
          l += `    Modality: ${item.modality || "Not Specified"}\n`;
          l += `    Priority: ${item.prioritisation_category || "N/A"}\n`;
          if (item.comment && item.comment.trim() && item.comment.toLowerCase() !== "none") l += `    Comment: ${item.comment}\n`;
        } else if (type === "removed") { // For removed, try to get old data if available for context (complex, skip for now)
           l += `    (Scenario details for removed items are not fully logged here, refer to JSON diff if needed)\n`;
        }
      });
      l += `\n`;
    };
    logScenarios("new", C.x.a); logScenarios("modified", C.x.m); logScenarios("removed", C.x.r);

    if (C.u.length) {
      l += `AUTHOR DETAILS UPDATED:\n`;
      C.u.forEach(({ s, d }) => {
        l += `\n Section: "${s}"\n`;
        if (d["Radiology Leads"]?.length) { l += `   Radiology Leads:\n`; d["Radiology Leads"].forEach((L) => (l += `    • ${L.name}${L.region ? ` (${L.region})` : ""}\n`)); }
        else { l += `   Radiology Leads: (None specified or removed)\n`;}
        if (d["Clinical Leads"]?.length) { l += `   Clinical Leads:\n`; d["Clinical Leads"].forEach((L) => (l += `    • ${L.name}${L.region ? ` (${L.region})` : ""}\n`)); }
        else { l += `   Clinical Leads: (None specified or removed)\n`;}
      });
      l += `\n`;
    }

    l += `\n=======================================\nSUMMARY OF CHANGES:\n`;
    l += ` • Total individual dirty keys processed: ${Object.keys(dK).length}\n`;
    l += ` • Sections Added: ${C.s.a.length}\n`;
    l += ` • Sections Modified (content changes): ${Array.from(C.s.m).filter((s) => !C.s.a.includes(s)).length}\n`;
    l += ` • Sub-headings Added: ${C.h.a.length}\n`;
    l += ` • Sub-headings Removed: ${C.h.r.length}\n`;
    l += ` • Scenarios Added: ${C.x.a.length}\n`;
    l += ` • Scenarios Modified: ${C.x.m.length}\n`;
    l += ` • Scenarios Removed: ${C.x.r.length}\n`;
    l += ` • Author Sets Updated: ${C.u.length}\n`;
    return l;
  };


  const handleInfoIconClick = (event, sectionName) => {
    event.stopPropagation(); // Prevent section selection if clicking icon within button
    if (authorPopoverPosition.visible && authorPopoverContent?._sectionName === sectionName) {
      // If already open for this section, close it
      closeAuthorPopover();
    } else {
      // Open for this section
      // Calculate position (simplified example, you might need a more robust solution)
      const rect = event.currentTarget.getBoundingClientRect();
      setAuthorPopoverPosition({
        visible: true,
        // top: rect.bottom + window.scrollY + 5, // Position below the icon
        // left: rect.left + window.scrollX - 100, // Adjust as needed
      });
      // Ensure we have a stable structure for authors
      const sectionAuthors = data[sectionName]?.authors;
      const authorsContent = sectionAuthors ? sectionAuthors : {
        "Radiology Leads": [],
        "Clinical Leads": []
      };
      setAuthorPopoverContent({
        authors: authorsContent,
        _sectionName: sectionName,
      });
    }
  };
  const handleSaveAuthors = (uA) => { // updatedAuthors
    if (!isEditorMode) return;
    if (!authorPopoverContent || !authorPopoverContent._sectionName) return;
    const sU = authorPopoverContent._sectionName; // sectionToUpdate
    setData((pD) => { const nD = deepClone(pD); if (!nD[sU]) nD[sU] = {}; nD[sU].authors = uA; return nD; });
    markDirtyKey(sU + "_authors", true);
    closeAuthorPopover();
  };
  const toggleSubSection = (sec, sub) => {
    const k = `${sec}-${sub}`;
    setCollapsedSubs((p) => ({ ...p, [k]: !p[k] }));
    if (newlyAddedSubheading && newlyAddedSubheading.section === sec && newlyAddedSubheading.sub === sub) {
      setNewlyAddedSubheading(null); // Clear pulse effect if user interacts
    }
  };

  const navigateToHelperPage = () => {
    setCurrentPage('helper');
    window.location.hash = 'helper'; // Update hash for deep linking/bookmarking
  };
  const navigateToTriagePage = () => {
    setCurrentPage('triage');
    if (window.location.hash === '#helper') { // Clean up hash if coming from helper
        window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
    }
  };


  if (!data) {
    return e( "p", { className: "rtt-app-loading-message" }, "Loading application data…");
  }

  const appRootClasses = [
    "rtt-container",
    mobile ? "app-mobile" : "",
    compactMode ? "app-compact-mode" : "",
    isEditorMode && edit && currentPage === 'triage' ? "app-edit-mode" : ""
  ].filter(Boolean).join(" ");

  const editorQuickGuidePoints = [
    'Choose a Section from the left panel.',
    'Click "Switch to Edit Mode" in the top right to enable editing for the selected section.',
    'Use the "+ Sub-heading" or "+ Scenario" buttons to add new content.',
    'Click on existing scenarios or author details to modify them in edit mode.',
    'Orange indicators highlight unsaved changes to sections or items.',
    'Click "Save & Download Updates" when finished. This will download two files: the updated data (JSON) and a changelog (TXT).',
    'Email both downloaded files to HNZRadTools@TeWhatuOra.govt.nz for the changes to be applied to the live tool.'
  ];

  const viewerQuickGuidePoints = [
    'Select a clinical area from the list on the left to view relevant triage scenarios.',
    'Expand sub-headings using the arrow or by clicking the sub-heading title.',
    'Use the search bar to filter scenarios within the selected clinical area by keywords (e.g., "headache", "CT", "P2").',
    'Click the info icon (ⓘ) next to a section title to view the clinical and radiology leads for that area.',
    'Click the "Priority Guide" link in the header for detailed information on prioritisation codes.',
    'This tool provides guidance only and does not replace clinical judgment.'
  ];
  const currentQuickGuidePoints = isEditorMode ? editorQuickGuidePoints : viewerQuickGuidePoints;
  const quickGuideTitleText = isEditorMode ? "Editor Quick Guide:" : "Quick Guide:";

  const pageTitleBase = isEditorMode ? "Radiology Triage Tool - Editor" : "Radiology Triage Tool";
  const pageTitleMobileBase = isEditorMode ? "Triage Tool Editor" : "Triage Tool";

  let currentHeaderTitle = mobile ? pageTitleMobileBase : pageTitleBase;
  if (currentPage === 'triage' && isEditorMode && edit && selected) {
    currentHeaderTitle = `Editing: ${selected}`;
  } else if (currentPage === 'helper') {
    currentHeaderTitle = mobile ? "Priority Guide" : "National Prioritisation Guide";
  }


  return e(
    "div", { className: appRootClasses },
    e("header", { className: "rtt-sticky-header"}, // Added relative for dropdown positioning
  e("div", { className: "rtt-brand-bar", style: { position: "relative" } },
    e("img", { src: "/images/HealthNZ_logo_v2.svg", alt: "Health NZ Logo", className: "rtt-app-logo" }),
    e("div", { className: "rtt-header-divider" }),
    e("h1", { className: "rtt-title" }, currentHeaderTitle),
    e("div", { style: { flexGrow: 1 } }), // Spacer

    // Header controls: hamburger for mobile, buttons for desktop
    e("div", { className: "rtt-header-controls" },
      mobile &&
        e("button", {
          className: "rtt-hamburger-btn",
          onClick: () => setHamburgerOpen(!hamburgerOpen),
          "aria-label": "Open menu",
          // Inline styles for hamburger were moved to CSS
        }, "☰"), // Hamburger Icon
      !mobile && [ // Desktop buttons
        currentPage === 'triage' && e("button", {
          key: 'desktop-priority-guide',
          className: "rtt-header-button-link rtt-priority-guide-nav-link",
          onClick: navigateToHelperPage,
          title: "View Priority Guide"
        }, "Priority Guide"),
        currentPage === 'helper' && e("button", {
          key: 'desktop-back-to-triage',
          className: "rtt-header-button-link rtt-back-to-triage-link",
          onClick: navigateToTriagePage,
          title: "Back to Triage Tool"
        }, "← Back to Triage Tool"),
        isEditorMode && currentPage === 'triage' && selected && e("button", {
          key: 'desktop-edit-toggle',
          onClick: () => setEdit(!edit),
          className: `rtt-edit-btn ${edit ? "rtt-edit-btn-active" : "rtt-edit-btn-inactive"}`,
          title: edit ? "Exit Edit Mode" : "Switch to Edit Mode"
        }, edit ? "Exit Edit Mode" : "Switch to Edit Mode"),
        isEditorMode && currentPage === 'triage' && Object.keys(dirty).length > 0 && e("button", {
          key: 'desktop-download',
          onClick: downloadJson,
          className: "rtt-download-btn",
          title: "Save and Download Updates"
        }, "Save & Download Updates")
      ]
    ),

    // Mobile dropdown menu (conditionally rendered after hamburger icon)
    mobile && hamburgerOpen && e("div", {
      className: "rtt-mobile-menu-dropdown", // Styling for this in CSS
      style: { // Basic positioning, refined in CSS if needed
        position: "absolute",
        top: "calc(100% + 5px)", // Position below the brand bar
        right: "10px", // Align to the right
        background: "#fff",
        boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
        zIndex: 1010, // Ensure it's above other content
        borderRadius: "8px",
        minWidth: "200px", // Decent width for options
        padding: "8px", // Internal padding
      }
    },
      [ // Array of buttons for the dropdown
        currentPage === 'triage' && e("button", {
          key: 'mobile-priority-guide',
          className: "rtt-header-button-link rtt-priority-guide-nav-link", // Reuses desktop classes, styled by dropdown specific CSS
          onClick: () => { navigateToHelperPage(); setHamburgerOpen(false); },
          // style: { width: "100%" } // width is handled by .rtt-mobile-menu-dropdown button
        }, "Priority Guide"),
        currentPage === 'helper' && e("button", {
          key: 'mobile-back-to-triage',
          className: "rtt-header-button-link rtt-back-to-triage-link",
          onClick: () => { navigateToTriagePage(); setHamburgerOpen(false); },
        }, "← Back to Triage Tool"),
        isEditorMode && currentPage === 'triage' && selected && e("button", {
          key: 'mobile-edit-toggle',
          onClick: () => { setEdit(!edit); setHamburgerOpen(false); },
          className: `rtt-edit-btn ${edit ? "rtt-edit-btn-active" : "rtt-edit-btn-inactive"}`,
        }, edit ? "Exit Edit Mode" : "Switch to Edit Mode"),
        isEditorMode && currentPage === 'triage' && Object.keys(dirty).length > 0 && e("button", {
          key: 'mobile-download',
          onClick: () => { downloadJson(); setHamburgerOpen(false); },
          className: "rtt-download-btn",
        }, "Save & Download Updates")
      ].filter(Boolean) // Filter out any null/false items if conditions not met
    )
  )
),
    currentPage === 'helper'
      ? e(HelperPage, { /* Props can be added if HelperPage needs them */ })
      : e( "div", { className: "rtt-app-layout" },
          e( "aside", { className: "rtt-sidebar" },
            e( "div", { className: "rtt-section-buttons-container" },
              isEditorMode && edit && e('button',{ key: 'add-section-top', onClick: addSection, className: "rtt-add-btn rtt-add-btn-specific" }, '+ Add Section'),
              sections.map((sec) => {
                const hasSecChanges = sectionHasChanges(sec);
                const sectionButtonClasses = [
                    "rtt-section-btn",
                    selected === sec ? "rtt-section-btn-active" : "",
                    hasSecChanges ? "rtt-section-btn-has-changes" : ""
                ].filter(Boolean).join(" ");
                return e( "button", { key: "sec-" + sec, onClick: () => { setSelected(sec); setSearchTerm(""); if (authorPopoverPosition.visible) closeAuthorPopover(); setNewlyAddedSubheading(null); if(mobile) setHamburgerOpen(false); }, // Close hamburger on section select
                    className: sectionButtonClasses,
                  },
                  [ sec, hasSecChanges && e("span", { className: "rtt-section-btn-change-indicator" }) ],
                );
              }),
            )
          ),
          e( "main", { className: "rtt-main-content", ref: mainContentRef },
            !selected
              ? e( "div", { className: "rtt-welcome-screen" },
                  e( "h2", { className: "rtt-section-header rtt-welcome-title" }, // Reuses rtt-section-header for consistency
                     isEditorMode ? "Welcome to the Radiology Triage Tool Editor" : "Welcome to the Radiology Triage Tool"
                  ),
                  e( "div", { className: "rtt-welcome-text-container" },
                    [
                      e( "p", { className: "rtt-welcome-intro-text" },
                        isEditorMode ? "Select a section to view or edit scenarios." : "Select a section to view scenarios."
                      ),
                      e( "div", { className: "rtt-quick-guide-box" },
                        [
                          e( "h3", { className: "rtt-quick-guide-title" }, quickGuideTitleText),
                          e( "ul", { className: "rtt-quick-guide-list" },
                            currentQuickGuidePoints.map((s, index) => e("li", {key: `guide-${index}`}, s)),
                          ),
                        ],
                      ),
                    ],
                  ),
                )
              : e("div", { key: selected || 'selected-section-content' }, [ // Key ensures re-render on section change
                  e("div", { className: "rtt-sticky-section-header-wrapper" }, [
                    e( 'div', { className: "rtt-section-header-container" },
                      e('div', { className: "rtt-section-title-group" },
                        e('div', { className: "rtt-section-title-line" },
                          e('h2', { className: "rtt-section-header" }, selected),
                          e('img', { src: 'icons/info.png', alt: `Authors for ${selected}`, onClick: (ev) => handleInfoIconClick(ev, selected), className: "rtt-info-icon", title: `Show/Edit leads for ${selected}`})
                        ),
                        data[selected]?.last_updated && e( "div", { className: "rtt-section-last-updated" }, `Updated - ${sectionHasChanges(selected) ? "Today (unsaved)" : formatLastUpdated(data[selected].last_updated)}`),
                      ),
                      e("div", { className: "rtt-flex-spacer" }),
                      e( "div", { className: "rtt-section-header-actions" }, isEditorMode && edit && e( "button", { className: "rtt-add-inline-btn", onClick: () => addSubheadingViaPrompt(selected) }, "+ Sub-heading")),
                    ),
                    e("input", {
                      type: "search",
                      placeholder: `Search in ${selected}...`,
                      value: searchTerm,
                      onChange: (ev) => setSearchTerm(ev.target.value),
                      className: "rtt-search-bar"
                    }),
                  ]),

                  authorPopoverPosition.visible && authorPopoverContent && e(AuthorPopover, {
                    content: authorPopoverContent,
                    position: authorPopoverPosition, // JS might need to set top/left on the popover style itself
                    onClose: closeAuthorPopover,
                    isEdit: isEditorMode && edit && authorPopoverContent._sectionName === selected,
                    onSave: handleSaveAuthors
                  }),

                  (Object.keys(displayableSubHeadings).length === 0 && searchTerm.length < 3 && (!data[selected] || Object.keys(data[selected]).filter((k) => Array.isArray(data[selected][k])).length === 0))
                    ? e( "div", { className: "rtt-no-subheadings-message" },
                        e("p", null, "No sub-headings or scenarios yet in this section."),
                        isEditorMode && edit && e( "button", { className: "rtt-add-inline-btn rtt-add-subheading-inline-btn", onClick: () => addSubheadingViaPrompt(selected) }, "+ Add Sub-heading"),
                        isEditorMode && edit && data[selected] && (!data[selected]["General"] || (Array.isArray(data[selected]["General"]) && !data[selected]["General"].length)) &&
                          e( "button", { className: "rtt-add-inline-btn rtt-add-scenario-general-inline-btn",
                              onClick: () => { if (!data[selected]["General"]) { const ok = addSubheadingInternal(selected, "General"); if (ok) setTimeout(() => addScenario(selected, "General"), 0); else alert("Error creating 'General'."); } else addScenario(selected, "General"); },
                            }, "+ Scenario to 'General'"),
                      )
                    : (searchTerm.length >= 3 && Object.keys(displayableSubHeadings).length === 0)
                      ? e( "p", { className: "rtt-search-no-results-message" }, `No scenarios match "${searchTerm}" in "${selected}".`)
                      : Object.entries(displayableSubHeadings).map(
                          ([sub, { list, isExpanded, actualIsEmpty }]) => {
                            return e(SubheadingSection, {
                              key: `${selected}-${sub}`, selected, sub, list, isExpanded, actualIsEmpty,
                              edit: isEditorMode && edit,
                              searchTerm,
                              newlyAddedSubheading,
                              subheadingHasChanges: subheadingHasChanges,
                              toggleSubSection,
                              removeSubheading, addScenario, saveScenario, removeScenario,
                              scenarioHasChanges: scenarioHasChanges,
                              keyOf, compactMode, mobile,
                            });
                          }
                        ),
                ]),
          ),
        )
  );
}

createRoot(document.getElementById("root")).render(e(App));
