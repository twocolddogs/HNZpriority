
import React, { useState, useEffect } from 'https://esm.sh/react@18';
import { createRoot } from 'https://esm.sh/react-dom@18/client';

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
        return (
            <div className='lora-container'>
                <div style={{ textAlign: 'center', padding: '4rem' }}>
                    <div className='loading-spinner'></div>
                    <p>Loading site profiles...</p>
                </div>
            </div>
        );
    }

    if (!siteData) {
        return (
            <div className='lora-container'>
                <div style={{ textAlign: 'center', padding: '4rem' }}>
                    <p>Error loading site data. Please refresh the page.</p>
                </div>
            </div>
        );
    }

    return (
        <div className='lora-container'>
            <Header
                isMenuOpen={isMenuOpen}
                toggleMenu={toggleMenu}
                closeMenu={closeMenu}
                exportAllProfiles={exportAllProfiles}
                setEditMode={setEditMode}
                editMode={editMode}
                requestEditAccess={requestEditAccess}
                authenticatedRegions={authenticatedRegions}
                currentRegion={currentRegion}
            />

            <div id='main-content'>
                <RegionNavigation
                    currentRegion={currentRegion}
                    handleRegionChange={handleRegionChange}
                    regions={Object.keys(siteData)}
                    authenticatedRegions={authenticatedRegions}
                />

                <ProfilesContainer
                    siteData={siteData}
                    currentRegion={currentRegion}
                    openProfileModal={openProfileModal}
                />
            </div>

            {isModalOpen && <ProfileModal
                profile={selectedProfile}
                closeModal={closeModal}
                exportProfile={exportProfile}
                editMode={editMode && authenticatedRegions.has(currentRegion)}
            />}

            {isPasswordModalOpen && <PasswordModal
                closeModal={closePasswordModal}
                onPasswordSubmit={handlePasswordSubmit}
                regionName={currentAuthRegion && passwordConfig?.regional_passwords[currentAuthRegion]?.region_name}
                currentAuthRegion={currentAuthRegion}
            />}
        </div>
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

    return (
        <div className='lora-sticky-header'>
            <div className='lora-brand-bar'>
                <img
                    src='../images/HealthNZ_logo_v2.svg'
                    alt='Health New Zealand Logo'
                    className='lora-app-logo'
                />
                <div className='lora-header-divider'></div>
                <h1 className='lora-title'>NZ Radiology Site Profiles</h1>
                <div className='lora-flex-spacer'></div>
                <div className='lora-header-controls'>
                    <div className='actions-menu-container'>
                        <button
                            className='lora-hamburger-btn'
                            onClick={toggleMenu}
                        >
                            <span></span>
                            <span></span>
                            <span></span>
                        </button>
                        <ul
                            className={`actions-dropdown-menu ${isMenuOpen ? '' : 'hidden'}`}
                        >
                            <li>
                                <button
                                    onClick={() => {
                                        alert('New Profile functionality coming soon');
                                        closeMenu();
                                    }}
                                >New Profile</button>
                            </li>
                            <li>
                                <button
                                    onClick={() => {
                                        alert('Import functionality coming soon');
                                        closeMenu();
                                    }}
                                >Import Profiles</button>
                            </li>
                            <li>
                                <button
                                    onClick={exportAllProfiles}
                                >Export All Profiles</button>
                            </li>
                            <li className='menu-divider'></li>
                            <li>
                                <button
                                    onClick={() => {
                                        setEditMode(false);
                                        closeMenu();
                                    }}
                                >View Mode</button>
                            </li>
                            <li>
                                <button
                                    onClick={() => requestEditAccess()}
                                    style={authenticatedRegions.has(currentRegion) ? 
                                        { color: '#2E7D2E', fontWeight: '600' } : {}}
                                > 
                                {authenticatedRegions.has(currentRegion) ? 
                                    `Edit Mode (${currentRegion.charAt(0).toUpperCase() + currentRegion.slice(1)} ✓)` : 
                                    'Edit Mode (Authentication Required)'}
                                </button>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Region Navigation Component
function RegionNavigation({ currentRegion, handleRegionChange, regions, authenticatedRegions }) {
    return (
        <div id='sticky-tabs-wrapper'>
            <div className='tabs-nav'>
                {regions.map(region =>
                    <button
                        key={region}
                        className={`tab-button ${currentRegion === region ? 'active' : ''}`}
                        data-region={region}
                        onClick={() => handleRegionChange(region)}
                    > 
                    {region.charAt(0).toUpperCase() + region.slice(1) + ' Region' +
                    (authenticatedRegions.has(region) ? ' ✓' : '')}
                    </button>
                )}
            </div>
        </div>
    );
}

// Profiles Container Component
function ProfilesContainer({ siteData, currentRegion, openProfileModal }) {
    const regionData = siteData[currentRegion];
    
    if (!regionData) return null;

    return (
        <div id='profiles-container'>
            <div className='tab-panel active' id={`${currentRegion}-panel`}>
                <h3>{`${regionData.region_name} Sites`}</h3>
                <div className='profiles-grid'>
                    {Object.entries(regionData.sites).map(([siteKey, siteData]) =>
                        <ProfileCard
                            key={siteKey}
                            siteKey={siteKey}
                            siteData={siteData}
                            onClick={() => openProfileModal(siteKey, siteData)}
                        />
                    )}
                </div>
            </div>
        </div>
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

    return (
        <div
            className='name-card'
            onClick={onClick}
            style={{ cursor: 'pointer', margin: '1rem 0' }}
        >
            <div className='name-card-header'>
                <h2>{siteData.site_name}</h2>
                <p style={{ margin: 0, fontSize: '0.9rem', opacity: 0.8 }}>
                    {`${siteData.site_code} • ${siteData.location}`}
                </p>
            </div>
            <div className='name-card-content'>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                    <div>
                        <strong>Equipment: </strong>
                        {`${totalEquipment} machines`}
                    </div>
                    <div>
                        <strong>Staff: </strong>
                        {`${totalStaff.toFixed(1)} FTE`}
                    </div>
                    <div>
                        <strong>Vacancies: </strong>
                        {`${totalVacancies.toFixed(1)} FTE`}
                    </div>
                    <div>
                        <strong>Annual Exams: </strong>
                        {`${siteData.performance_metrics.annual_examinations.toLocaleString()}`}
                    </div>
                </div>
                <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#666' }}>
                    {`Manager: ${siteData.contact.manager}`}
                </div>
            </div>
        </div>
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

    return (
        <div 
            className='modal-overlay'
            onClick={handleOverlayClick}
        >
            <div className='modal-container' style={{ maxWidth: '900px', maxHeight: '90vh', overflow: 'auto' }}>
                <div className='modal-title'>{data.site_name}</div>
                
                <div className='modal-tabs'>
                    {tabs.map(tab =>
                        <button
                            key={tab.id}
                            className={`modal-tab ${activeTab === tab.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                        >{tab.label}</button>
                    )}
                </div>
                
                <div id='modal-content' className='modal-tab-content'>
                    <ProfileDetails profile={data} editMode={editMode} activeTab={activeTab} />
                </div>
                <div className='modal-buttons'>
                    <button
                        className='modal-btn modal-btn-cancel'
                        onClick={closeModal}
                    >Close</button>
                    {editMode && <button
                        className='modal-btn modal-btn-confirm'
                        onClick={() => alert('Save functionality coming soon')}
                    >Save Changes</button>}
                    <button
                        className='modal-btn modal-btn-confirm'
                        onClick={() => exportProfile(data)}
                    >Export JSON</button>
                </div>
            </div>
        </div>
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
            return (
                <div className='contact-item'>
                    <label className='contact-label'>{label}</label>
                    <input
                        type={type}
                        value={value}
                        className='contact-value'
                        style={{ 
                            border: '1px solid #D1D5DB', 
                            borderRadius: '4px', 
                            padding: '0.5rem',
                            fontFamily: 'var(--font-body)'
                        }}
                        onChange={(event) => updateField(path, event.target.value)}
                    />
                </div>
            );
        }
        
        return (
            <div className='contact-item'>
                <div className='contact-label'>{label}</div>
                <div className='contact-value'>{value}</div>
            </div>
        );
    };

    const renderEditableNumber = (value, path) => {
        if (editMode) {
            return (
                <input
                    type='number'
                    value={value}
                    style={{ 
                        border: '1px solid #D1D5DB', 
                        borderRadius: '4px', 
                        padding: '0.25rem',
                        width: '60px',
                        fontFamily: 'var(--font-body)'
                    }}
                    onChange={(event) => updateField(path, parseInt(event.target.value) || 0)}
                />
            );
        }
        return value;
    };

    const renderEditableBoolean = (value, path) => {
        if (editMode) {
            return (
                <select
                    value={value ? 'true' : 'false'}
                    style={{ 
                        border: '1px solid #D1D5DB', 
                        borderRadius: '4px', 
                        padding: '0.25rem',
                        fontFamily: 'var(--font-body)'
                    }}
                    onChange={(event) => updateField(path, event.target.value === 'true')}
                >
                    <option value='true'>Yes</option>
                    <option value='false'>No</option>
                </select>
            );
        }
        return value ? 'Yes' : 'No';
    };

    const renderContactTab = () => (
        <section className='profile-detail-section'>
            <h4>Contact Information</h4>
            <div className='contact-grid'>
                {renderEditableField('Site Code', editedProfile.site_code, 'site_code')}
                {renderEditableField('Location', editedProfile.location, 'location')}
                {renderEditableField('Manager', editedProfile.contact.manager, 'contact.manager')}
                {renderEditableField('Email', editedProfile.contact.email, 'contact.email', 'email')}
                {renderEditableField('Phone', editedProfile.contact.phone, 'contact.phone', 'tel')}
            </div>
        </section>
    );

    const renderEquipmentTab = () => (
    <section className='profile-detail-section'>
        <h4>Equipment</h4>
        {Object.entries(editedProfile.equipment).map(([modalityKey, modalityData]) => {
            // Handle legacy data structure
            if (!modalityData.machines) {
                return (
                    <div key={modalityKey} style={{ marginBottom: '2rem' }}>
                        <h5>{`${modalityKey.replace('_', ' ').toUpperCase()} (${modalityData.count || 0} machines)`}</h5>
                        <div className='table-container'>
                            <table className='equipment-table'>
                                <thead>
                                    <tr>
                                        <th>Count</th>
                                        <th>Models</th>
                                        <th>Routine Hours/Day</th>
                                        <th>Routine Days/Week</th>
                                        <th>Out of Hours Available</th>
                                        <th>Out of Hours Days/Week</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>{renderEditableNumber(modalityData.count, `equipment.${modalityKey}.count`)}</td>
                                        <td>{modalityData.models ? modalityData.models.join(', ') : ''}</td>
                                        <td>{renderEditableNumber(modalityData.routine_hours_per_day, `equipment.${modalityKey}.routine_hours_per_day`)}</td>
                                        <td>{renderEditableNumber(modalityData.routine_days_per_week, `equipment.${modalityKey}.routine_days_per_week`)}</td>
                                        <td className={modalityData.out_of_hours_available ? 'available-yes' : 'available-no'}> 
                                            {renderEditableBoolean(modalityData.out_of_hours_available, `equipment.${modalityKey}.out_of_hours_available`)}
                                        </td>
                                        <td>{renderEditableNumber(modalityData.out_of_hours_days_per_week, `equipment.${modalityKey}.out_of_hours_days_per_week`)}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                );
            }

            // New machines array structure
            return (
                <div key={modalityKey} style={{ marginBottom: '2rem' }}>
                    <h5>{`${modalityKey.replace('_', ' ').toUpperCase()} (${modalityData.machines.length} machines)`}</h5>
                    <div className='table-container'>
                        <table className='equipment-table'>
                            <thead>
                                <tr>
                                    {[
                                        <th key="machine-name">Machine Name</th>,
                                        <th key="model">Model</th>,
                                        <th key="routine-hours">Routine Hours/Day</th>,
                                        <th key="routine-days">Routine Days/Week</th>,
                                        <th key="ooh-available">Out of Hours Available</th>,
                                        <th key="ooh-days">Out of Hours Days/Week</th>,
                                        modalityKey === 'ct' && <th key="interventional">Interventional Only</th>
                                    ].filter(Boolean)}
                                </tr>
                            </thead>
                            <tbody>
                                {modalityData.machines.map((machine, index) =>
                                    <tr 
                                        key={machine.id || index}
                                        className={modalityKey === 'ct' && machine.interventional_only ? 'interventional-row' : ''}
                                    >
                                        {[
                                            <td key="machine-name" className='equipment-type'> 
                                                {editMode ? 
                                                    <input
                                                        type='text'
                                                        value={machine.name || ''}
                                                        placeholder='Machine name (optional)'
                                                        onChange={(event) => updateField(`equipment.${modalityKey}.machines.${index}.name`, event.target.value)}
                                                    /> :
                                                    (machine.name || `${modalityKey.toUpperCase()} ${index + 1}`)}
                                            </td>,
                                            <td key="model"> 
                                                {editMode ? 
                                                    <input
                                                        type='text'
                                                        value={machine.model || ''}
                                                        placeholder='Enter model'
                                                        onChange={(event) => updateField(`equipment.${modalityKey}.machines.${index}.model`, event.target.value)}
                                                    /> :
                                                    machine.model}
                                            </td>,
                                            <td key="routine-hours"> 
                                                {renderEditableNumber(machine.routine_hours_per_day, `equipment.${modalityKey}.machines.${index}.routine_hours_per_day`)}
                                            </td>,
                                            <td key="routine-days"> 
                                                {renderEditableNumber(machine.routine_days_per_week, `equipment.${modalityKey}.machines.${index}.routine_days_per_week`)}
                                            </td>,
                                            <td key="ooh-available" className={machine.out_of_hours_available ? 'available-yes' : 'available-no'}> 
                                                {renderEditableBoolean(machine.out_of_hours_available, `equipment.${modalityKey}.machines.${index}.out_of_hours_available`)}
                                            </td>,
                                            <td key="ooh-days"> 
                                                {renderEditableNumber(machine.out_of_hours_days_per_week, `equipment.${modalityKey}.machines.${index}.out_of_hours_days_per_week`)}
                                            </td>,
                                            modalityKey === 'ct' && <td key="interventional" className={machine.interventional_only ? 'available-yes' : 'available-no'}> 
                                                {renderEditableBoolean(machine.interventional_only, `equipment.${modalityKey}.machines.${index}.interventional_only`)}
                                            </td>
                                        ].filter(Boolean)}
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )})}
        </section>
    );

    const renderStaffingTab = () => (
        <section className='profile-detail-section'>
            <h4>Staffing</h4>
            <div className='table-container'>
                <table className='staffing-table'>
                    <thead>
                        <tr>
                            <th>Staff Type</th>
                            <th>Total FTE</th>
                            <th>Current Vacancies</th>
                            <th>Breakdown</th>
                        </tr>
                    </thead>
                    <tbody>
                        {Object.entries(editedProfile.staffing).map(([key, staff]) =>
                            <tr key={key}>
                                <td className='staff-type'> 
                                    {key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                </td>
                                <td> 
                                    {editMode ? renderEditableNumber(staff.total_fte, `staffing.${key}.total_fte`) : staff.total_fte.toFixed(1)}
                                </td>
                                <td> 
                                    {editMode ? renderEditableNumber(staff.current_vacancies, `staffing.${key}.current_vacancies`) : staff.current_vacancies.toFixed(1)}
                                </td>
                                <td>
                                    {Object.entries(staff.breakdown).map(([level, fte]) =>
                                        `${level}: ${fte}`
                                    ).join(', ')}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );

    const renderPerformanceTab = () => (
        <section className='profile-detail-section'>
            <h4>Performance Metrics</h4>
            <div className='metrics-grid'>
                <div className='metric-card'>
                    <div className='metric-card-label'>Annual Examinations</div>
                    <div className='metric-card-value'> 
                        {editMode ? 
                            renderEditableNumber(editedProfile.performance_metrics.annual_examinations, 'performance_metrics.annual_examinations') :
                            editedProfile.performance_metrics.annual_examinations.toLocaleString()}
                    </div>
                </div>
                <div className='metric-card'>
                    <div className='metric-card-label'>Average Wait Time (Days)</div>
                    <div className='metric-card-value'> 
                        {editMode ? 
                            renderEditableNumber(editedProfile.performance_metrics.average_wait_time_days, 'performance_metrics.average_wait_time_days') :
                            editedProfile.performance_metrics.average_wait_time_days}
                    </div>
                </div>
                <div className='metric-card'>
                    <div className='metric-card-label'>Urgent Cases 24h Target (%)</div>
                    <div className='metric-card-value'> 
                        {editMode ? 
                            renderEditableNumber(editedProfile.performance_metrics.urgent_cases_24h_target, 'performance_metrics.urgent_cases_24h_target') :
                            `${editedProfile.performance_metrics.urgent_cases_24h_target}%`}
                    </div>
                </div>
                <div className='metric-card'>
                    <div className='metric-card-label'>Routine Cases 30 Day Target (%)</div>
                    <div className='metric-card-value'> 
                        {editMode ? 
                            renderEditableNumber(editedProfile.performance_metrics.routine_cases_30_day_target, 'performance_metrics.routine_cases_30_day_target') :
                            `${editedProfile.performance_metrics.routine_cases_30_day_target}%`}
                    </div>
                </div>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#666', textAlign: 'right', marginTop: '2rem' }}>
                {`Last updated: ${editedProfile.last_updated}`}
            </div>
        </section>
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

    return <div>{renderTabContent()}</div>;
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

    return (
        <div 
            className='modal-overlay'
            onClick={handleOverlayClick}
        >
            <div className='modal-container' style={{ maxWidth: '500px' }}>
                <div className='modal-title'>Authentication Required</div>
                <form onSubmit={handleSubmit}>
                    <div className='modal-body-text'>
                        {`Please enter the password for ${regionName || 'this region'} to enable editing mode.`}
                        <br />
                        <br />
                        <small style={{ color: '#666', fontSize: '0.9rem' }}>
                            Note: Admin password grants access to all regions.
                        </small>
                    </div>
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label 
                            style={{ 
                                display: 'block', 
                                marginBottom: '0.5rem',
                                fontFamily: 'var(--font-body)',
                                fontWeight: 'var(--font-weight-semibold)',
                                color: 'var(--text-secondary)'
                            }} 
                        >Password</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                placeholder='Enter regional or admin password'
                                autoFocus
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    paddingRight: '3rem',
                                    border: error ? '2px solid #B91C1C' : '1px solid #D1D5DB',
                                    borderRadius: '6px',
                                    fontFamily: 'var(--font-body)',
                                    fontSize: 'var(--font-size-base)',
                                    boxSizing: 'border-box'
                                }}
                                required
                            />
                            <button
                                type='button'
                                onClick={() => setShowPassword(!showPassword)}
                                style={{
                                    position: 'absolute',
                                    right: '0.75rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    background: 'none',
                                    border: 'none',
                                    color: '#6B7280',
                                    cursor: 'pointer',
                                    fontSize: '0.9rem'
                                }}
                            >{showPassword ? '🙈' : '👁️'}</button>
                        </div>
                        {error && <div
                            style={{
                                color: '#B91C1C',
                                fontSize: '0.875rem',
                                marginTop: '0.5rem',
                                fontFamily: 'var(--font-body)'
                            }}
                        >{error}</div>}
                    </div>
                    <div className='modal-buttons'>
                        <button
                            type='button'
                            className='modal-btn modal-btn-cancel'
                            onClick={handleCancel}
                        >Cancel</button>
                        <button
                            type='submit'
                            className='modal-btn modal-btn-confirm'
                        >Authenticate</button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// Initialize the application
const container = document.querySelector('.lora-container');
const root = createRoot(container);
root.render(<App />);
