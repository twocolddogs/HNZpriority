
const { useState, useEffect } = React;

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
    // Calculate equipment breakdown by modality
    const equipmentBreakdown = Object.entries(siteData.equipment).reduce((breakdown, [modalityKey, eq]) => {
        let count = 0;
        // Handle both new machines array and legacy count structure
        if (eq.machines) {
            count = eq.machines.length;
        } else if (eq.count) {
            count = eq.count;
        }
        if (count > 0) {
            // Proper capitalization for modalities
            const modalityName = modalityKey === 'ultrasound' ? 'Ultrasound' : 
                                modalityKey === 'mammography' ? 'Mammography' : 
                                modalityKey.toUpperCase();
            breakdown[modalityName] = count;
        }
        return breakdown;
    }, {});

    // Calculate staffing for key roles only (Radiologist, MIT, RA)
    const keyStaffingCategories = [
        { key: 'radiologist', label: 'Radiologist' },
        { key: 'mit', label: 'MIT' },
        { key: 'radiology_healthcare_assistant', label: 'RA' }
    ];
    
    const staffVacancyData = keyStaffingCategories.map(category => {
        const staff = siteData.staffing[category.key] || siteData.staffing[category.key + 's'];
        if (staff && staff.total_fte > 0) {
            const vacancyRate = (staff.current_vacancies / staff.total_fte) * 100;
            return {
                label: category.label,
                vacancyRate: vacancyRate,
                totalFTE: staff.total_fte,
                vacancies: staff.current_vacancies
            };
        }
        return null;
    }).filter(Boolean);

    // Helper function to get color based on vacancy rate
    const getVacancyColor = (rate) => {
        const filledRate = 100 - rate;
        if (filledRate >= 80) return '#28a745'; // Green
        if (filledRate >= 60) return '#ffc107'; // Orange/Yellow
        return '#dc3545'; // Red
    };

    // Determine archetype based on annual examinations (hard-coded logic)
    const getArchetype = (annualExams) => {
        if (annualExams >= 120000) return 'X-Large';
        if (annualExams >= 80000) return 'Large';
        if (annualExams >= 50000) return 'Medium';
        if (annualExams >= 25000) return 'Small';
        return 'X-Small';
    };

    const archetype = getArchetype(siteData.performance_metrics.annual_examinations);

    return (
        <div
            className='name-card'
            onClick={onClick}
            style={{ cursor: 'pointer', margin: '1rem 0' }}
        >
            <div className='name-card-header'>
                <h2>{siteData.site_name}</h2>
                <p style={{ margin: 0, fontSize: '0.9rem', opacity: 0.8 }}>
                    {`${siteData.site_code} • ${siteData.location} • ${archetype}`}
                </p>
            </div>
            <div className='name-card-content'>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                    <div>
                        <strong>Equipment:</strong>
                        <div style={{ marginTop: '0.25rem', lineHeight: '1.4' }}>
                            {Object.entries(equipmentBreakdown).length > 0 ? 
                                Object.entries(equipmentBreakdown)
                                    .map(([modality, count], index) => (
                                        <div key={index}>{`${modality}: ${count}`}</div>
                                    )) :
                                '0 machines'
                            }
                        </div>
                    </div>
                    <div>
                        <strong>Annual Exams:</strong>
                        <div style={{ marginTop: '0.25rem' }}>
                            {siteData.performance_metrics.annual_examinations.toLocaleString()}
                        </div>
                    </div>
                </div>
                
                {/* Clinical Workforce Section */}
                <div style={{ marginTop: '1rem' }}>
                    <strong>Clinical Workforce:</strong>
                    <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {staffVacancyData.map((staff, index) => {
                            const vacancyColor = getVacancyColor(staff.vacancyRate);
                            return (
                                <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <span style={{ minWidth: '80px', fontSize: '0.9rem' }}>{staff.label}:</span>
                                    <div style={{ 
                                        flex: 1, 
                                        height: '20px', 
                                        backgroundColor: '#f0f0f0', 
                                        borderRadius: '10px',
                                        position: 'relative',
                                        overflow: 'hidden'
                                    }}>
                                        <div style={{
                                            height: '100%',
                                            width: `${Math.max(0, 100 - staff.vacancyRate)}%`,
                                            backgroundColor: vacancyColor,
                                            borderRadius: '10px',
                                            transition: 'width 0.3s ease'
                                        }}></div>
                                        <span style={{
                                            position: 'absolute',
                                            left: '50%',
                                            top: '50%',
                                            transform: 'translate(-50%, -50%)',
                                            fontSize: '0.75rem',
                                            fontWeight: 'bold',
                                            color: staff.vacancyRate > 50 ? '#333' : '#fff',
                                            textShadow: staff.vacancyRate > 50 ? 'none' : '1px 1px 1px rgba(0,0,0,0.3)'
                                        }}>
                                            {staff.vacancyRate.toFixed(1)}%
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
                
                <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: '#666' }}>
                    {`Ops/Service Manager: ${siteData.contact.ops_service_manager || siteData.contact.manager}`}
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
        { id: 'productivity', label: 'Productivity' },
        { id: 'digital', label: 'Digital' }
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
        const newProfile = JSON.parse(JSON.stringify(editedProfile)); // Deep clone
        const keys = path.split('.');
        let current = newProfile;
        
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!current[key]) {
                current[key] = {};
            }
            current = current[key];
        }
        
        current[keys[keys.length - 1]] = value;
        setEditedProfile(newProfile);
    };

    const renderEditableField = (label, value, path, type = 'text') => {
        if (editMode) {
            if (type === 'select' && path === 'archetype') {
                const archetypeOptions = ['X-Large', 'Large', 'Medium', 'Small', 'X-Small', 'Other'];
                return (
                    <div className='contact-item'>
                        <label className='contact-label'>{label}</label>
                        <select
                            value={value}
                            className='contact-value'
                            style={{ 
                                border: '1px solid #D1D5DB', 
                                borderRadius: '4px', 
                                padding: '0.5rem',
                                fontFamily: 'var(--font-body)'
                            }}
                            onChange={(event) => updateField(path, event.target.value)}
                        >
                            {archetypeOptions.map(option => (
                                <option key={option} value={option}>{option}</option>
                            ))}
                        </select>
                    </div>
                );
            }
            
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
                {renderEditableField('Archetype', editedProfile.archetype || 'Medium', 'archetype', 'select')}
                {renderEditableField('Ops/Service Manager', editedProfile.contact.ops_service_manager || editedProfile.contact.manager, 'contact.ops_service_manager')}
                {renderEditableField('Ops/Service Manager Email', editedProfile.contact.ops_service_manager_email || editedProfile.contact.email, 'contact.ops_service_manager_email', 'email')}
                {renderEditableField('Clinical Lead', editedProfile.contact.clinical_lead || '', 'contact.clinical_lead')}
                {renderEditableField('Clinical Lead Email', editedProfile.contact.clinical_lead_email || '', 'contact.clinical_lead_email', 'email')}
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
            const addMachine = (modalityKey) => {
                const newMachine = {
                    id: `${modalityKey}_${Date.now()}`,
                    name: '',
                    model: '',
                    routine_hours_per_day: 8,
                    routine_days_per_week: 5,
                    out_of_hours_available: false,
                    out_of_hours_days_per_week: 0
                };
                
                // Add interventional_only field for CT machines
                if (modalityKey === 'ct') {
                    newMachine.interventional_only = false;
                }
                
                const currentMachines = editedProfile.equipment[modalityKey].machines || [];
                const updatedMachines = [...currentMachines, newMachine];
                updateField(`equipment.${modalityKey}.machines`, updatedMachines);
            };

            const removeMachine = (modalityKey, machineIndex) => {
                const currentMachines = editedProfile.equipment[modalityKey].machines || [];
                const updatedMachines = currentMachines.filter((_, index) => index !== machineIndex);
                updateField(`equipment.${modalityKey}.machines`, updatedMachines);
            };

            return (
                <div key={modalityKey} style={{ marginBottom: '2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <h5>{`${modalityKey.replace('_', ' ').toUpperCase()} (${modalityData.machines.length} machines)`}</h5>
                        {editMode && (
                            <button
                                onClick={() => addMachine(modalityKey)}
                                style={{
                                    padding: '0.5rem 1rem',
                                    backgroundColor: '#007bff',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '0.9rem'
                                }}
                            >
                                + Add Machine
                            </button>
                        )}
                    </div>
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
                                        modalityKey === 'ct' && <th key="interventional">Interventional Only</th>,
                                        editMode && <th key="actions">Actions</th>
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
                                            </td>,
                                            editMode && <td key="actions">
                                                <button
                                                    onClick={() => removeMachine(modalityKey, index)}
                                                    style={{
                                                        padding: '0.25rem 0.5rem',
                                                        backgroundColor: '#dc3545',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        fontSize: '0.8rem'
                                                    }}
                                                >
                                                    Remove
                                                </button>
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

    const renderStaffingTab = () => {
        // Define the new standardized staff categories (alphabetized)
        const standardStaffCategories = [
            'admin_scheduler',
            'business_analyst', 
            'clinical_nurse',
            'clinical_support',
            'fellow',
            'mit',
            'pacs',
            'quality_lead',
            'radiology_healthcare_assistant',
            'radiologist',
            'rmo',
            'sho'
        ];
        
        const categoryLabels = {
            'admin_scheduler': 'Admin/Scheduler',
            'business_analyst': 'Business Analyst',
            'clinical_nurse': 'Clinical Nurse', 
            'clinical_support': 'Clinical Support',
            'fellow': 'Fellow',
            'mit': 'MIT',
            'pacs': 'PACS',
            'quality_lead': 'Quality Lead',
            'radiology_healthcare_assistant': 'Radiology/Healthcare Assistant',
            'radiologist': 'Radiologist',
            'rmo': 'RMO',
            'sho': 'SHO'
        };

        // Initialize missing categories with default values
        const currentStaffing = { ...editedProfile.staffing };
        standardStaffCategories.forEach(category => {
            if (!currentStaffing[category]) {
                currentStaffing[category] = {
                    total_fte: 0.0,
                    current_vacancies: 0.0
                };
            }
        });

        return (
            <section className='profile-detail-section'>
                <h4>Staffing</h4>
                <div className='table-container'>
                    <table className='staffing-table'>
                        <thead>
                            <tr>
                                <th>Staff Type</th>
                                <th>Total FTE</th>
                                <th>Current Vacancies</th>
                            </tr>
                        </thead>
                        <tbody>
                            {standardStaffCategories.map(key => {
                                const staff = currentStaffing[key];
                                return (
                                    <tr key={key}>
                                        <td className='staff-type'> 
                                            {categoryLabels[key]}
                                        </td>
                                        <td> 
                                            {editMode ? renderEditableNumber(staff.total_fte, `staffing.${key}.total_fte`) : staff.total_fte.toFixed(1)}
                                        </td>
                                        <td> 
                                            {editMode ? renderEditableNumber(staff.current_vacancies, `staffing.${key}.current_vacancies`) : staff.current_vacancies.toFixed(1)}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </section>
        );
    };

    const renderProductivityTab = () => (
        <section className='profile-detail-section'>
            <h4>Productivity</h4>
            <div style={{ 
                textAlign: 'center', 
                padding: '3rem', 
                fontSize: '1.2rem', 
                color: '#666',
                border: '2px dashed #ddd',
                borderRadius: '8px',
                backgroundColor: '#f9f9f9'
            }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⏳</div>
                <div>Coming Soon</div>
                <div style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
                    Productivity metrics and analysis tools are being developed
                </div>
            </div>
        </section>
    );

    const renderDigitalTab = () => {
        // Initialize digital tools if not present
        if (!editedProfile.digital_tools) {
            editedProfile.digital_tools = {
                pacs: { name: 'PACS', system: '', version: '' },
                ris: { name: 'RIS', system: '', version: '' },
                custom_tools: []
            };
        }

        const addDigitalTool = () => {
            const newTool = { name: '', description: '', vendor: '' };
            const updatedTools = [...(editedProfile.digital_tools.custom_tools || []), newTool];
            updateField('digital_tools.custom_tools', updatedTools);
        };

        const removeDigitalTool = (index) => {
            const updatedTools = editedProfile.digital_tools.custom_tools.filter((_, i) => i !== index);
            updateField('digital_tools.custom_tools', updatedTools);
        };

        return (
            <section className='profile-detail-section'>
                <h4>Digital Systems</h4>
                
                <div style={{ marginBottom: '2rem' }}>
                    <h5>Core Systems</h5>
                    <div className='table-container'>
                        <table className='equipment-table'>
                            <thead>
                                <tr>
                                    <th>System Type</th>
                                    <th>System Name</th>
                                    <th>Version</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td className='equipment-type'>PACS</td>
                                    <td>
                                        {editMode ? 
                                            <input
                                                type='text'
                                                value={editedProfile.digital_tools.pacs.system || ''}
                                                placeholder='Enter PACS system'
                                                onChange={(event) => updateField('digital_tools.pacs.system', event.target.value)}
                                            /> :
                                            editedProfile.digital_tools.pacs.system || 'Not specified'
                                        }
                                    </td>
                                    <td>
                                        {editMode ? 
                                            <input
                                                type='text'
                                                value={editedProfile.digital_tools.pacs.version || ''}
                                                placeholder='Enter version'
                                                onChange={(event) => updateField('digital_tools.pacs.version', event.target.value)}
                                            /> :
                                            editedProfile.digital_tools.pacs.version || 'Not specified'
                                        }
                                    </td>
                                </tr>
                                <tr>
                                    <td className='equipment-type'>RIS</td>
                                    <td>
                                        {editMode ? 
                                            <input
                                                type='text'
                                                value={editedProfile.digital_tools.ris.system || ''}
                                                placeholder='Enter RIS system'
                                                onChange={(event) => updateField('digital_tools.ris.system', event.target.value)}
                                            /> :
                                            editedProfile.digital_tools.ris.system || 'Not specified'
                                        }
                                    </td>
                                    <td>
                                        {editMode ? 
                                            <input
                                                type='text'
                                                value={editedProfile.digital_tools.ris.version || ''}
                                                placeholder='Enter version'
                                                onChange={(event) => updateField('digital_tools.ris.version', event.target.value)}
                                            /> :
                                            editedProfile.digital_tools.ris.version || 'Not specified'
                                        }
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <h5>Digital Tools</h5>
                        {editMode && (
                            <button
                                onClick={addDigitalTool}
                                style={{
                                    padding: '0.5rem 1rem',
                                    backgroundColor: '#007bff',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer'
                                }}
                            >
                                + Add Tool
                            </button>
                        )}
                    </div>
                    <div className='table-container'>
                        <table className='equipment-table'>
                            <thead>
                                <tr>
                                    <th>Tool Name</th>
                                    <th>Description</th>
                                    <th>Vendor</th>
                                    {editMode && <th>Actions</th>}
                                </tr>
                            </thead>
                            <tbody>
                                {(editedProfile.digital_tools.custom_tools || []).map((tool, index) => (
                                    <tr key={index}>
                                        <td>
                                            {editMode ? 
                                                <input
                                                    type='text'
                                                    value={tool.name || ''}
                                                    placeholder='Tool name'
                                                    onChange={(event) => updateField(`digital_tools.custom_tools.${index}.name`, event.target.value)}
                                                /> :
                                                tool.name || 'Unnamed tool'
                                            }
                                        </td>
                                        <td>
                                            {editMode ? 
                                                <input
                                                    type='text'
                                                    value={tool.description || ''}
                                                    placeholder='Description'
                                                    onChange={(event) => updateField(`digital_tools.custom_tools.${index}.description`, event.target.value)}
                                                /> :
                                                tool.description || 'No description'
                                            }
                                        </td>
                                        <td>
                                            {editMode ? 
                                                <input
                                                    type='text'
                                                    value={tool.vendor || ''}
                                                    placeholder='Vendor'
                                                    onChange={(event) => updateField(`digital_tools.custom_tools.${index}.vendor`, event.target.value)}
                                                /> :
                                                tool.vendor || 'Not specified'
                                            }
                                        </td>
                                        {editMode && (
                                            <td>
                                                <button
                                                    onClick={() => removeDigitalTool(index)}
                                                    style={{
                                                        padding: '0.25rem 0.5rem',
                                                        backgroundColor: '#dc3545',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        fontSize: '0.8rem'
                                                    }}
                                                >
                                                    Remove
                                                </button>
                                            </td>
                                        )}
                                    </tr>
                                ))}
                                {(editedProfile.digital_tools.custom_tools || []).length === 0 && (
                                    <tr>
                                        <td colSpan={editMode ? 4 : 3} style={{ textAlign: 'center', fontStyle: 'italic', color: '#666' }}>
                                            No custom digital tools configured
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>
        );
    };

    // Render content based on active tab
    const renderTabContent = () => {
        switch (activeTab) {
            case 'contact': return renderContactTab();
            case 'equipment': return renderEquipmentTab();
            case 'staffing': return renderStaffingTab();
            case 'productivity': return renderProductivityTab();
            case 'digital': return renderDigitalTab();
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
const root = ReactDOM.createRoot(container);
root.render(<App />);
