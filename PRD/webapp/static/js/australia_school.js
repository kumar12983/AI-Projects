/**
 * Australia School Search - Orchestrator (australia_school.js)
 * Defines global state, DOM refs, displaySchoolInfo, showLoading/hideLoading,
 * form submission, and address search button handler.
 * Module files are loaded after this file.
 */

console.log('Australia School Search JS loaded - v4');

// Global state
let map = null;
let selectedSchool = null;
let currentAcaraId = null;
let currentPage = 1;
let totalPages = 1;
let allAddresses = [];
let australiaMap = null;
let geojsonLayer = null;
let currentOffset = 0;
let totalAddresses = 0;
const PAGE_SIZE = 100;

// DOM Elements
const schoolInput = document.getElementById('schoolInput');
const schoolSuggestions = document.getElementById('schoolSuggestions');
const stateFilter = document.getElementById('stateFilter');
const australiaSchoolSearchForm = document.getElementById('australiaSchoolSearchForm');
const schoolInfoSection = document.getElementById('schoolInfoSection');
const mapSection = document.getElementById('mapSection');
const addressSearchSection = document.getElementById('addressSearchSection');
const resultsSection = document.getElementById('resultsSection');
const loadingIndicator = document.getElementById('loadingIndicator');

console.log('DOM Elements loaded:', {
    schoolInput: !!schoolInput,
    schoolSuggestions: !!schoolSuggestions,
    stateFilter: !!stateFilter,
    australiaSchoolSearchForm: !!australiaSchoolSearchForm
});

// Address search elements
const searchStreetNumber = document.getElementById('searchStreetNumber');
const searchStreet = document.getElementById('searchStreet');
const searchSuburb = document.getElementById('searchSuburb');
const searchPostcode = document.getElementById('searchPostcode');
const searchState = document.getElementById('searchState');
const searchAddressBtn = document.getElementById('searchAddressBtn');
const searchResults = document.getElementById('searchResults');
const searchStreetSuggestions = document.getElementById('search-street-suggestions');
const searchSuburbSuggestions = document.getElementById('search-suburb-suggestions');
const searchPostcodeSuggestions = document.getElementById('search-postcode-suggestions');

// ============================================
// Form Submission
// ============================================

australiaSchoolSearchForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!selectedSchool) {
        alert('Please select a school from the suggestions');
        return;
    }

    console.log('Form submitted, fetching school:', selectedSchool);
    showLoading();

    try {
        console.log('Fetching /api/australia-school/' + selectedSchool + '/info');
        const response = await fetch(`/api/australia-school/${selectedSchool}/info`);
        console.log('Response received, status:', response.status);
        const data = await response.json();
        
        console.log('School info received:', data);
        console.log('Has geom_5km_buffer:', !!data.geom_5km_buffer);

        if (data.error) {
            console.error('API returned error:', data.error);
            alert(data.error);
            hideLoading();
            return;
        }

        console.log('Calling displaySchoolInfo...');
        displaySchoolInfo(data);
        console.log('displaySchoolInfo completed');
        
        console.log('Calling displayMap...');
        displayMap(data);
        console.log('displayMap completed');

        console.log('Calling hideLoading...');
        hideLoading();
        console.log('hideLoading completed');

        // Load initial addresses after school info is displayed
        console.log('Loading addresses...');
        await loadAddresses(true);
        console.log('loadAddresses completed');

    } catch (error) {
        console.error('Error loading school data:', error);
        console.error('Error stack:', error.stack);
        alert('Error loading school information');
        hideLoading();
    }
});

// ============================================
// Display School Info
// ============================================

function displaySchoolInfo(data) {
    console.log('displaySchoolInfo called with:', data.school_name);
    currentAcaraId = data.acara_sml_id;
    console.log('Set currentAcaraId to:', currentAcaraId);
    
    document.getElementById('schoolName').textContent = data.school_name;
    document.getElementById('schoolTypeBadge').textContent = data.school_type || 'SCHOOL';
    document.getElementById('yearLevels').textContent = data.year_levels || 'N/A';
    document.getElementById('schoolType').textContent = data.school_type_full || 'N/A';

    // Display sector as badge
    const sectorBadge = document.getElementById('schoolSectorBadge');
    sectorBadge.textContent = data.school_sector || 'N/A';
    sectorBadge.className = 'sector-badge';
    if (data.school_sector) {
        sectorBadge.classList.add(data.school_sector.toLowerCase());
    }

    // Website
    if (data.school_url) {
        document.getElementById('schoolUrl').href = data.school_url;
        document.getElementById('schoolUrl-container').style.display = 'flex';
    } else {
        document.getElementById('schoolUrl-container').style.display = 'none';
    }

    // School Profile
    if (data.school_profile_url) {
        document.getElementById('schoolProfile').href = data.school_profile_url;
        document.getElementById('schoolProfile-container').style.display = 'flex';
    } else {
        document.getElementById('schoolProfile-container').style.display = 'none';
    }

    // NAPLAN Scores
    if (data.naplan_url) {
        document.getElementById('naplanScores').href = data.naplan_url;
        document.getElementById('naplanScores-container').style.display = 'flex';
    } else {
        document.getElementById('naplanScores-container').style.display = 'none';
    }

    // ICSEA Score
    if (data.icsea_score) {
        document.getElementById('icsea').textContent = data.icsea_score;
        document.getElementById('icsea-container').style.display = 'flex';
    } else {
        document.getElementById('icsea-container').style.display = 'none';
    }

    // ICSEA Percentile
    if (data.icsea_percentile) {
        document.getElementById('icsea-percentile').textContent = data.icsea_percentile + '%';
        document.getElementById('icsea-percentile-container').style.display = 'flex';
    } else {
        document.getElementById('icsea-percentile-container').style.display = 'none';
    }

    // Catchment Zone Button (only show if has_catchment = 'Y' and school_id exists)
    if (data.has_catchment === 'Y' && data.school_id) {
        document.getElementById('catchmentButton').href = `/school-search?school_id=${data.school_id}`;
        document.getElementById('catchmentButtonContainer').style.display = 'block';
    } else {
        document.getElementById('catchmentButtonContainer').style.display = 'none';
    }

    console.log('About to set schoolInfoSection display to block');
    console.log('schoolInfoSection element:', schoolInfoSection);
    schoolInfoSection.removeAttribute('style');
    schoolInfoSection.style.display = 'block';
    console.log('schoolInfoSection display set to:', schoolInfoSection.style.display);
    console.log('schoolInfoSection computed style:', window.getComputedStyle(schoolInfoSection).display);
}

// ============================================
// Loading State
// ============================================

function showLoading() {
    loadingIndicator.style.display = 'flex';
    schoolInfoSection.style.display = 'none';
    mapSection.style.display = 'none';
}

function hideLoading() {
    loadingIndicator.style.display = 'none';
}

// ============================================
// Address Search Button
// ============================================

// Address search button click handler
if (searchAddressBtn) {
    searchAddressBtn.addEventListener('click', () => {
        loadAddresses(false);
    });
}
