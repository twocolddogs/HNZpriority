import React, { useState, useEffect } from 'https://esm.sh/react@18';
import { createRoot } from 'https://esm.sh/react-dom@18/client';

const e = React.createElement;

// Main App Component
function App() {
    const [siteData, setSiteData] = useState(null);
    const [passwordConfig, setPasswordConfig] = useState(null);
    const [currentRegion, setCurrentRegion] = useState('northern');
    const [selectedProfile, setSelectedProfile] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editMode, setEditMode] = useState(false);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [loading, setLoading] = useState(true);
    const [authenticatedRegions, setAuthenticatedRegions] = useState(new Set());
    const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
    const [currentAuthRegion, setCurrentAuthRegion] = useState(null);

    // Load site data and password config on component mount
    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [siteResponse, passwordResponse] = await Promise.all([
                fetch('./site_profiles_data.json'),
                fetch('./regional_passwords.json')
            ]);
            
            const siteData = await siteResponse.json();
            const passwordData = await passwordResponse.json();
            
            setSiteData(siteData);
            setPasswordConfig(passwordData);
            setLoading(false);
        } catch (error) {
            console.error('Error loading data:', error);
            setLoading(false);
        }
    };

    const handleRegionChange = (region) => {
        setCurrentRegion(region);
        closeModal();
    };

    const openProfileModal = (siteKey, profile) => {
        setSelectedProfile({ key: siteKey, data: profile });
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setSelectedProfile(null);
    };

    const closePasswordModal = () => {
        setIsPasswordModalOpen(false);
        setCurrentAuthRegion(null);
    };

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const closeMenu = () => {
        setIsMenuOpen(false);
    };

    const requestEditAccess = (region = null) => {
        const targetRegion = region || currentRegion;
        if (authenticatedRegions.has(targetRegion)) {
            setEditMode(true);
            closeMenu();
        } else {
            setCurrentAuthRegion(targetRegion);
            setIsPasswordModalOpen(true);
            closeMenu();
        }
    };

    const handlePasswordSubmit = (password) => {
        if (!passwordConfig || !currentAuthRegion) return false;

        const regionConfig = passwordConfig.regional_passwords[currentAuthRegion];
        const isValidPassword = regionConfig && regionConfig.password === password;
        const isAdminPassword = passwordConfig.admin_password === password;

        if (isValidPassword || isAdminPassword) {
            const newAuthRegions = new Set(authenticatedRegions);
            if (isAdminPassword) {
                // Admin password grants access to all regions
                Object.keys(passwordConfig.regional_passwords).forEach(region => {
                    newAuthRegions.add(region);
                });
            } else {
                newAuthRegions.add(currentAuthRegion);
            }
            setAuthenticatedRegions(newAuthRegions);
            setEditMode(true);
            closePasswordModal();
            return true;
        }
        return false;
    };

    const exportProfile = (profile) => {
        const dataStr = JSON.stringify(profile, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${profile.site_code}_profile.json`;
        link.click();
        URL.revokeObjectURL(url);
    };

    const exportAllProfiles = () => {
        const dataStr = JSON.stringify(siteData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'all_radiology_profiles.json';
        link.click();
        URL.revokeObjectURL(url);
        closeMenu();
    };

    if (loading) {
        return e('div', { className: 'lora-container' },
            e('div', { style: { textAlign: 'center', padding: '4rem' } },
                e('div', { className: 'loading-spinner' }),
                e('p', null, 'Loading site profiles...')
            )
        );
    }

    if (!siteData) {
        return e('div', { className: 'lora-container' },
            e('div', { style: { textAlign: 'center', padding: '4rem' } },
                e('p', null, 'Error loading site data. Please refresh the page.')
            )
        );
    }

    return e('div', { className: 'lora-container' },
        // Header
        e(Header, {
            isMenuOpen,
            toggleMenu,
            closeMenu,
            exportAllProfiles,
            setEditMode,
            editMode,
            requestEditAccess,
            authenticatedRegions,
            currentRegion
        }),

        // Main Content
        e('div', { id: 'main-content' },
            // Region Navigation
            e(RegionNavigation, {
                currentRegion,
                handleRegionChange,
                regions: Object.keys(siteData),
                authenticatedRegions
            }),

            // Profiles Container
            e(ProfilesContainer, {
                siteData,
                currentRegion,
                openProfileModal
            })
        ),

        // Profile Modal
        isModalOpen && e(ProfileModal, {
            profile: selectedProfile,
            closeModal,
            exportProfile,
            editMode: editMode && authenticatedRegions.has(currentRegion)
        }),

        // Password Modal
        isPasswordModalOpen && e(PasswordModal, {
            closeModal: closePasswordModal,
            onPasswordSubmit: handlePasswordSubmit,
            regionName: currentAuthRegion && passwordConfig?.regional_passwords[currentAuthRegion]?.region_name,
            currentAuthRegion
        })
    );
}

// Header Component
function Header({ isMenuOpen, toggleMenu, closeMenu, exportAllProfiles, setEditMode, editMode, requestEditAccess, authenticatedRegions, currentRegion }) {
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (isMenuOpen && !event.target.closest('.actions-menu-container')) {
                closeMenu();
            }
        };

        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, [isMenuOpen, closeMenu]);

    return e('div', { className: 'lora-sticky-header' },
        e('div', { className: 'lora-brand-bar' },
            e('img', {
                src: '../images/HealthNZ_logo_v2.svg',
                alt: 'Health New Zealand Logo',
                className: 'lora-app-logo'
            }),
            e('div', { className: 'lora-header-divider' }),
            e('h1', { className: 'lora-title' }, 'NZ Radiology Site Profiles'),
            e('div', { className: 'lora-flex-spacer' }),
            e('div', { className: 'lora-header-controls' },
                e('div', { className: 'actions-menu-container' },
                    e('button', {
                        className: 'lora-hamburger-btn',
                        onClick: toggleMenu
                    },
                        e('span'),
                        e('span'),
                        e('span')
                    ),
                    e('ul', {
                        className: `actions-dropdown-menu ${isMenuOpen ? '' : 'hidden'}`
                    },
                        e('li', null,
                            e('button', {
                                onClick: () => {
                                    alert('New Profile functionality coming soon');
                                    closeMenu();
                                }
                            }, 'New Profile')
                        ),
                        e('li', null,
                            e('button', {
                                onClick: () => {
                                    alert('Import functionality coming soon');
                                    closeMenu();
                                }
                            }, 'Import Profiles')
                        ),
                        e('li', null,
                            e('button', {
                                onClick: exportAllProfiles
                            }, 'Export All Profiles')
                        ),
                        e('li', { className: 'menu-divider' }),
                        e('li', null,
                            e('button', {
                                onClick: () => {
                                    setEditMode(false);
                                    closeMenu();
                                }
                            }, 'View Mode')
                        ),
                        e('li', null,
                            e('button', {
                                onClick: () => requestEditAccess(),
                                style: authenticatedRegions.has(currentRegion) ? 
                                    { color: '#2E7D2E', fontWeight: '600' } : {}
                            }, 
                            authenticatedRegions.has(currentRegion) ? 
                                `Edit Mode (${currentRegion.charAt(0).toUpperCase() + currentRegion.slice(1)} ✓)` : 
                                'Edit Mode (Authentication Required)'
                            )
                        )
                    )
                )
            )
        )
    );
}

// Region Navigation Component
function RegionNavigation({ currentRegion, handleRegionChange, regions, authenticatedRegions }) {
    return e('div', { id: 'sticky-tabs-wrapper' },
        e('div', { className: 'tabs-nav' },
            regions.map(region =>
                e('button', {
                    key: region,
                    className: `tab-button ${currentRegion === region ? 'active' : ''}`,
                    'data-region': region,
                    onClick: () => handleRegionChange(region)
                }, 
                region.charAt(0).toUpperCase() + region.slice(1) + ' Region' +
                (authenticatedRegions.has(region) ? ' ✓' : '')
                )
            )
        )
    );
}

// Profiles Container Component
function ProfilesContainer({ siteData, currentRegion, openProfileModal }) {
    const regionData = siteData[currentRegion];
    
    if (!regionData) return null;

    return e('div', { id: 'profiles-container' },
        e('div', { className: 'tab-panel active', id: `${currentRegion}-panel` },
            e('h3', null, `${regionData.region_name} Sites`),
            e('div', { className: 'profiles-grid' },
                Object.entries(regionData.sites).map(([siteKey, siteData]) =>
                    e(ProfileCard, {
                        key: siteKey,
                        siteKey,
                        siteData,
                        onClick: () => openProfileModal(siteKey, siteData)
                    })
                )
            )
        )
    );
}

// Profile Card Component
function ProfileCard({ siteKey, siteData, onClick }) {
    const totalEquipment = Object.values(siteData.equipment).reduce((sum, eq) => {
        // Handle both new machines array and legacy count structure
        if (eq.machines) {
            return sum + eq.machines.length;
        } else if (eq.count) {
            return sum + eq.count;
        }
        return sum;
    }, 0);
    const totalStaff = Object.values(siteData.staffing).reduce((sum, staff) => sum + staff.total_fte, 0);
    const totalVacancies = Object.values(siteData.staffing).reduce((sum, staff) => sum + staff.current_vacancies, 0);

    return e('div', {
        className: 'name-card',
        onClick,
        style: { cursor: 'pointer', margin: '1rem 0' }
    },
        e('div', { className: 'name-card-header' },
            e('h2', null, siteData.site_name),
            e('p', { style: { margin: 0, fontSize: '0.9rem', opacity: 0.8 } },
                `${siteData.site_code} • ${siteData.location}`
            )
        ),
        e('div', { className: 'name-card-content' },
            e('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' } },
                e('div', null,
                    e('strong', null, 'Equipment: '),
                    `${totalEquipment} machines`
                ),
                e('div', null,
                    e('strong', null, 'Staff: '),
                    `${totalStaff.toFixed(1)} FTE`
                ),
                e('div', null,
                    e('strong', null, 'Vacancies: '),
                    `${totalVacancies.toFixed(1)} FTE`
                ),
                e('div', null,
                    e('strong', null, 'Annual Exams: '),
                    `${siteData.performance_metrics.annual_examinations.toLocaleString()}`
                )
            ),
            e('div', { style: { marginTop: '0.5rem', fontSize: '0.8rem', color: '#666' } },
                `Manager: ${siteData.contact.manager}`
            )
        )
    );
}

// Profile Modal Component
function ProfileModal({ profile, closeModal, exportProfile, editMode }) {
    const [activeTab, setActiveTab] = useState('contact');
    
    if (!profile) return null;

    const { data } = profile;

    const tabs = [
        { id: 'contact', label: 'Contact' },
        { id: 'equipment', label: 'Equipment' },
        { id: 'staffing', label: 'Staffing' },
        { id: 'performance', label: 'Performance' }
    ];

    const handleOverlayClick = (event) => {
        // Only close modal if clicking on the overlay itself, not the modal content
        if (event.target === event.currentTarget) {
            closeModal();
        }
    };

    return e('div', { 
            className: 'modal-overlay',
            onClick: handleOverlayClick
        },
        e('div', { className: 'modal-container', style: { maxWidth: '900px', maxHeight: '90vh', overflow: 'auto' } },
            e('div', { className: 'modal-title' }, data.site_name),
            
            // Tab Navigation
            e('div', { className: 'modal-tabs' },
                tabs.map(tab =>
                    e('button', {
                        key: tab.id,
                        className: `modal-tab ${activeTab === tab.id ? 'active' : ''}`,
                        onClick: () => setActiveTab(tab.id)
                    }, tab.label)
                )
            ),
            
            // Tab Content
            e('div', { id: 'modal-content', className: 'modal-tab-content' },
                e(ProfileDetails, { profile: data, editMode, activeTab })
            ),
            e('div', { className: 'modal-buttons' },
                e('button', {
                    className: 'modal-btn modal-btn-cancel',
                    onClick: closeModal
                }, 'Close'),
                editMode && e('button', {
                    className: 'modal-btn modal-btn-confirm',
                    onClick: () => alert('Save functionality coming soon')
                }, 'Save Changes'),
                e('button', {
                    className: 'modal-btn modal-btn-confirm',
                    onClick: () => exportProfile(data)
                }, 'Export JSON')
            )
        )
    );
}

// Profile Details Component
function ProfileDetails({ profile, editMode, activeTab }) {
    const [editedProfile, setEditedProfile] = useState(profile);

    const updateField = (path, value) => {
        const newProfile = { ...editedProfile };
        const keys = path.split('.');
        let current = newProfile;
        
        for (let i = 0; i < keys.length - 1; i++) {
            current = current[keys[i]];
        }
        
        current[keys[keys.length - 1]] = value;
        setEditedProfile(newProfile);
    };

    const renderEditableField = (label, value, path, type = 'text') => {
        if (editMode) {
            return e('div', { className: 'contact-item' },
                e('label', { className: 'contact-label' }, label),
                e('input', {
                    type,
                    value,
                    className: 'contact-value',
                    style: { 
                        border: '1px solid #D1D5DB', 
                        borderRadius: '4px', 
                        padding: '0.5rem',
                        fontFamily: 'var(--font-body)'
                    },
                    onChange: (event) => updateField(path, event.target.value)
                })
            );
        }
        
        return e('div', { className: 'contact-item' },
            e('div', { className: 'contact-label' }, label),
            e('div', { className: 'contact-value' }, value)
        );
    };

    const renderEditableNumber = (value, path) => {
        if (editMode) {
            return e('input', {
                type: 'number',
                value,
                style: { 
                    border: '1px solid #D1D5DB', 
                    borderRadius: '4px', 
                    padding: '0.25rem',
                    width: '60px',
                    fontFamily: 'var(--font-body)'
                },
                onChange: (event) => updateField(path, parseInt(event.target.value) || 0)
            });
        }
        return value;
    };

    const renderEditableBoolean = (value, path) => {
        if (editMode) {
            return e('select', {
                value: value ? 'true' : 'false',
                style: { 
                    border: '1px solid #D1D5DB', 
                    borderRadius: '4px', 
                    padding: '0.25rem',
                    fontFamily: 'var(--font-body)'
                },
                onChange: (event) => updateField(path, event.target.value === 'true')
            },
                e('option', { value: 'true' }, 'Yes'),
                e('option', { value: 'false' }, 'No')
            );
        }
        return value ? 'Yes' : 'No';
    };

    const renderContactTab = () => (
        e('section', { className: 'profile-detail-section' },
            e('h4', null, 'Contact Information'),
            e('div', { className: 'contact-grid' },
                renderEditableField('Site Code', editedProfile.site_code, 'site_code'),
                renderEditableField('Location', editedProfile.location, 'location'),
                renderEditableField('Manager', editedProfile.contact.manager, 'contact.manager'),
                renderEditableField('Email', editedProfile.contact.email, 'contact.email', 'email'),
                renderEditableField('Phone', editedProfile.contact.phone, 'contact.phone', 'tel')
            )
        )
    );

    const renderEquipmentTab = () => (
    e('section', { className: 'profile-detail-section' },
        e('h4', null, 'Equipment'),
        // FIX: Spread the array of elements returned by .map()
        ...Object.entries(editedProfile.equipment).map(([modalityKey, modalityData]) => {
            // Handle legacy data structure
            if (!modalityData.machines) {
                return e('div', { key: modalityKey, style: { marginBottom: '2rem' } },
                    e('h5', null, `${modalityKey.replace('_', ' ').toUpperCase()} (${modalityData.count || 0} machines)`),
                    e('div', { className: 'table-container' },
                        e('table', { className: 'equipment-table' },
                            e('thead', null,
                                e('tr', null,
                                    e('th', null, 'Count'),
                                    e('th', null, 'Models'),
                                    e('th', null, 'Routine Hours/Day'),
                                    e('th', null, 'Routine Days/Week'),
                                    e('th', null, 'Out of Hours Available'),
                                    e('th', null, 'Out of Hours Days/Week')
                                )
                            ),
                            e('tbody', null,
                                e('tr', null,
                                    e('td', null, renderEditableNumber(modalityData.count, `equipment.${modalityKey}.count`)),
                                    e('td', null, modalityData.models ? modalityData.models.join(', ') : ''),
                                    e('td', null, renderEditableNumber(modalityData.routine_hours_per_day, `equipment.${modalityKey}.routine_hours_per_day`)),
                                    e('td', null, renderEditableNumber(modalityData.routine_days_per_week, `equipment.${modalityKey}.routine_days_per_week`)),
                                    e('td', { className: modalityData.out_of_hours_available ? 'available-yes' : 'available-no' }, 
                                        renderEditableBoolean(modalityData.out_of_hours_available, `equipment.${modalityKey}.out_of_hours_available`)
                                    ),
                                    e('td', null, renderEditableNumber(modalityData.out_of_hours_days_per_week, `equipment.${modalityKey}.out_of_hours_days_per_week`))
                                )
                            )
                        )
                    )
                );
            }

            // New machines array structure
            return e('div', { key: modalityKey, style: { marginBottom: '2rem' } },
                e('h5', null, `${modalityKey.replace('_', ' ').toUpperCase()} (${modalityData.machines.length} machines)`),
                e('div', { className: 'table-container' },
                    e('table', { className: 'equipment-table' },
                        e('thead', null,
                            e('tr', null,
                                ...[
                                    e('th', null, 'Machine Name'),
                                    e('th', null, 'Model'),
                                    e('th', null, 'Routine Hours/Day'),
                                    e('th', null, 'Routine Days/Week'),
                                    e('th', null, 'Out of Hours Available'),
                                    e('th', null, 'Out of Hours Days/Week'),
                                    modalityKey === 'ct' && e('th', null, 'Interventional Only')
                                ].filter(Boolean)
                            )
                        ),
                        e('tbody', null,
                            modalityData.machines.map((machine, index) =>
                                e('tr', { 
                                    key: machine.id || index,
                                    className: modalityKey === 'ct' && machine.interventional_only ? 'interventional-row' : ''
                                },
                                    ...[
                                        e('td', { className: 'equipment-type' }, 
                                            editMode ? 
                                                e('input', {
                                                    type: 'text',
                                                    value: machine.name || '',
                                                    placeholder: 'Machine name (optional)',
                                                    onChange: (event) => updateField(`equipment.${modalityKey}.machines.${index}.name`, event.target.value)
                                                }) :
                                                (machine.name || `${modalityKey.toUpperCase()} ${index + 1}`)
                                        ),
                                        e('td', null, 
                                            editMode ? 
                                                e('input', {
                                                    type: 'text',
                                                    value: machine.model || '',
                                                    placeholder: 'Enter model',
                                                    onChange: (event) => updateField(`equipment.${modalityKey}.machines.${index}.model`, event.target.value)
                                                }) :
                                                machine.model
                                        ),
                                        e('td', null, 
                                            renderEditableNumber(machine.routine_hours_per_day, `equipment.${modalityKey}.machines.${index}.routine_hours_per_day`)
                                        ),
                                        e('td', null, 
                                            renderEditableNumber(machine.routine_days_per_week, `equipment.${modalityKey}.machines.${index}.routine_days_per_week`)
                                        ),
                                        e('td', { className: machine.out_of_hours_available ? 'available-yes' : 'available-no' }, 
                                            renderEditableBoolean(machine.out_of_hours_available, `equipment.${modalityKey}.machines.${index}.out_of_hours_available`)
                                        ),
                                        e('td', null, 
                                            renderEditableNumber(machine.out_of_hours_days_per_week, `equipment.${modalityKey}.machines.${index}.out_of_hours_days_per_week`)
                                        ),
                                        modalityKey === 'ct' && e('td', { className: machine.interventional_only ? 'available-yes' : 'available-no' }, 
                                            renderEditableBoolean(machine.interventional_only, `equipment.${modalityKey}.machines.${index}.interventional_only`)
                                        )
                                    ].filter(Boolean)
                                )
                            )
                        )
                    )
                )
            })
        )
    );

    const renderStaffingTab = () => (
        e('section', { className: 'profile-detail-section' },
            e('h4', null, 'Staffing'),
            e('div', { className: 'table-container' },
                e('table', { className: 'staffing-table' },
                    e('thead', null,
                        e('tr', null,
                            e('th', null, 'Staff Type'),
                            e('th', null, 'Total FTE'),
                            e('th', null, 'Current Vacancies'),
                            e('th', null, 'Breakdown')
                        )
                    ),
                    e('tbody', null,
                        Object.entries(editedProfile.staffing).map(([key, staff]) =>
                            e('tr', { key },
                                e('td', { className: 'staff-type' }, 
                                    key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
                                ),
                                e('td', null, 
                                    editMode ? renderEditableNumber(staff.total_fte, `staffing.${key}.total_fte`) : staff.total_fte.toFixed(1)
                                ),
                                e('td', null, 
                                    editMode ? renderEditableNumber(staff.current_vacancies, `staffing.${key}.current_vacancies`) : staff.current_vacancies.toFixed(1)
                                ),
                                e('td', null,
                                    Object.entries(staff.breakdown).map(([level, fte]) =>
                                        `${level}: ${fte}`
                                    ).join(', ')
                                )
                            )
                        )
                    )
                )
            )
        )
    );

    const renderPerformanceTab = () => (
        e('section', { className: 'profile-detail-section' },
            e('h4', null, 'Performance Metrics'),
            e('div', { className: 'metrics-grid' },
                e('div', { className: 'metric-card' },
                    e('div', { className: 'metric-card-label' }, 'Annual Examinations'),
                    e('div', { className: 'metric-card-value' }, 
                        editMode ? 
                            renderEditableNumber(editedProfile.performance_metrics.annual_examinations, 'performance_metrics.annual_examinations') :
                            editedProfile.performance_metrics.annual_examinations.toLocaleString()
                    )
                ),
                e('div', { className: 'metric-card' },
                    e('div', { className: 'metric-card-label' }, 'Average Wait Time (Days)'),
                    e('div', { className: 'metric-card-value' }, 
                        editMode ? 
                            renderEditableNumber(editedProfile.performance_metrics.average_wait_time_days, 'performance_metrics.average_wait_time_days') :
                            editedProfile.performance_metrics.average_wait_time_days
                    )
                ),
                e('div', { className: 'metric-card' },
                    e('div', { className: 'metric-card-label' }, 'Urgent Cases 24h Target (%)'),
                    e('div', { className: 'metric-card-value' }, 
                        editMode ? 
                            renderEditableNumber(editedProfile.performance_metrics.urgent_cases_24h_target, 'performance_metrics.urgent_cases_24h_target') :
                            `${editedProfile.performance_metrics.urgent_cases_24h_target}%`
                    )
                ),
                e('div', { className: 'metric-card' },
                    e('div', { className: 'metric-card-label' }, 'Routine Cases 30 Day Target (%)'),
                    e('div', { className: 'metric-card-value' }, 
                        editMode ? 
                            renderEditableNumber(editedProfile.performance_metrics.routine_cases_30_day_target, 'performance_metrics.routine_cases_30_day_target') :
                            `${editedProfile.performance_metrics.routine_cases_30_day_target}%`
                    )
                )
            ),
            e('div', { style: { fontSize: '0.8rem', color: '#666', textAlign: 'right', marginTop: '2rem' } },
                `Last updated: ${editedProfile.last_updated}`
            )
        )
    );

    // Render content based on active tab
    const renderTabContent = () => {
        switch (activeTab) {
            case 'contact': return renderContactTab();
            case 'equipment': return renderEquipmentTab();
            case 'staffing': return renderStaffingTab();
            case 'performance': return renderPerformanceTab();
            default: return renderContactTab();
        }
    };

    return e('div', null, renderTabContent());
}

// Password Modal Component
function PasswordModal({ closeModal, onPasswordSubmit, regionName, currentAuthRegion }) {
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    const handleSubmit = (event) => {
        event.preventDefault();
        if (onPasswordSubmit(password)) {
            setPassword('');
            setError('');
        } else {
            setError('Invalid password. Please try again.');
            setPassword('');
        }
    };

    const handleCancel = () => {
        setPassword('');
        setError('');
        closeModal();
    };

    const handleOverlayClick = (event) => {
        // Only close modal if clicking on the overlay itself, not the modal content
        if (event.target === event.currentTarget) {
            closeModal();
        }
    };

    return e('div', { 
            className: 'modal-overlay',
            onClick: handleOverlayClick
        },
        e('div', { className: 'modal-container', style: { maxWidth: '500px' } },
            e('div', { className: 'modal-title' }, 'Authentication Required'),
            e('form', { onSubmit: handleSubmit },
                e('div', { className: 'modal-body-text' },
                    `Please enter the password for ${regionName || 'this region'} to enable editing mode.`,
                    e('br'),
                    e('br'),
                    e('small', { style: { color: '#666', fontSize: '0.9rem' } },
                        'Note: Admin password grants access to all regions.'
                    )
                ),
                e('div', { style: { marginBottom: '1.5rem' } },
                    e('label', { 
                        style: { 
                            display: 'block', 
                            marginBottom: '0.5rem',
                            fontFamily: 'var(--font-body)',
                            fontWeight: 'var(--font-weight-semibold)',
                            color: 'var(--text-secondary)'
                        } 
                    }, 'Password'),
                    e('div', { style: { position: 'relative' } },
                        e('input', {
                            type: showPassword ? 'text' : 'password',
                            value: password,
                            onChange: (event) => setPassword(event.target.value),
                            placeholder: 'Enter regional or admin password',
                            autoFocus: true,
                            style: {
                                width: '100%',
                                padding: '0.75rem',
                                paddingRight: '3rem',
                                border: error ? '2px solid #B91C1C' : '1px solid #D1D5DB',
                                borderRadius: '6px',
                                fontFamily: 'var(--font-body)',
                                fontSize: 'var(--font-size-base)',
                                boxSizing: 'border-box'
                            },
                            required: true
                        }),
                        e('button', {
                            type: 'button',
                            onClick: () => setShowPassword(!showPassword),
                            style: {
                                position: 'absolute',
                                right: '0.75rem',
                                top: '50%',
                                transform: 'translateY(-50%)',
                                background: 'none',
                                border: 'none',
                                color: '#6B7280',
                                cursor: 'pointer',
                                fontSize: '0.9rem'
                            }
                        }, showPassword ? '🙈' : '👁️')
                    ),
                    error && e('div', {
                        style: {
                            color: '#B91C1C',
                            fontSize: '0.875rem',
                            marginTop: '0.5rem',
                            fontFamily: 'var(--font-body)'
                        }
                    }, error)
                ),
                e('div', { className: 'modal-buttons' },
                    e('button', {
                        type: 'button',
                        className: 'modal-btn modal-btn-cancel',
                        onClick: handleCancel
                    }, 'Cancel'),
                    e('button', {
                        type: 'submit',
                        className: 'modal-btn modal-btn-confirm'
                    }, 'Authenticate')
                )
            )
        )
    );
}

// Initialize the application
const container = document.querySelector('.lora-container');
const root = createRoot(container);
root.render(e(App));