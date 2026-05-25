/**
 * School Catchment Search - Orchestrator (school.js)
 * Defines global state, DOM refs, and core event handlers.
 * Module files (school-utils.js, school-map.js, school-results.js,
 * school-hazards.js, school-autocomplete.js) are loaded after this file.
 */

// Global state
let currentSchoolId = null;
let currentSchoolLocation = null;
let allAddresses = [];
let filteredAddresses = [];
let debounceTimer = null;
let catchmentMap = null;
let catchmentLayer = null;
let currentPage = 1;
let totalPages = 1;
let pageSize = 500;
let totalAddresses = 0;

// DOM Elements
const schoolInput = document.getElementById('schoolInput');
const schoolSuggestions = document.getElementById('schoolSuggestions');
const stateFilter = document.getElementById('stateFilter');
const schoolSearchForm = document.getElementById('schoolSearchForm');
const schoolInfoSection = document.getElementById('schoolInfoSection');
const mapSection = document.getElementById('mapSection');
const addressSearchSection = document.getElementById('addressSearchSection');
const resultsSection = document.getElementById('resultsSection');
const loadingIndicator = document.getElementById('loadingIndicator');
const searchResults = document.getElementById('searchResults');

// Search form elements
const searchStreetNumber = document.getElementById('searchStreetNumber');
const searchStreet = document.getElementById('searchStreet');
const searchSuburb = document.getElementById('searchSuburb');
const searchPostcode = document.getElementById('searchPostcode');
const searchState = document.getElementById('searchState');
const searchLimit = document.getElementById('searchLimit');
const searchAddressBtn = document.getElementById('searchAddressBtn');
const searchStreetSuggestions = document.getElementById('search-street-suggestions');
const searchSuburbSuggestions = document.getElementById('search-suburb-suggestions');
const searchPostcodeSuggestions = document.getElementById('search-postcode-suggestions');

// Debug: Log if elements are found
console.log('DOM Elements initialized:', {
    searchStreet: !!searchStreet,
    searchSuburb: !!searchSuburb,
    searchPostcode: !!searchPostcode,
    searchStreetSuggestions: !!searchStreetSuggestions,
    searchSuburbSuggestions: !!searchSuburbSuggestions,
    searchPostcodeSuggestions: !!searchPostcodeSuggestions
});

// Check for URL parameters to auto-load a school
const urlParams = new URLSearchParams(window.location.search);
const schoolIdParam = urlParams.get('school_id');
if (schoolIdParam) {
    currentSchoolId = parseInt(schoolIdParam);
    // Auto-load the school after a short delay to ensure DOM is ready
    setTimeout(() => {
        loadSchoolData(currentSchoolId);
    }, 100);
}

// ============================================
// Form Submission
// ============================================

schoolSearchForm.addEventListener('submit', function (e) {
    e.preventDefault();

    if (currentSchoolId) {
        console.log('Selected school ID:', currentSchoolId);
        loadSchoolData(currentSchoolId);
    } else {
        const searchText = schoolInput.value.trim();
        if (searchText && searchText.length >= 3) {
            console.log('No school selected, searching for:', searchText);
            alert('Please select a school from the suggestions dropdown');
            schoolInput.focus();
        } else {
            alert('Please type at least 3 characters and select a school from the suggestions');
        }
    }
});

// ============================================
// Load School Data
// ============================================

async function loadSchoolData(schoolId) {
    console.log('loadSchoolData called with schoolId:', schoolId, 'type:', typeof schoolId);
    showLoading(true);
    hideAllSections();

    try {
        // Load school info and boundary
        console.log('Fetching /api/school/' + schoolId + '/info');
        const [infoResponse, boundaryResponse] = await Promise.all([
            fetch(`/api/school/${schoolId}/info`),
            fetch(`/api/school/${schoolId}/boundary`)
        ]);

        if (!infoResponse.ok) {
            throw new Error(`Info API error: ${infoResponse.status} ${infoResponse.statusText}`);
        }
        if (!boundaryResponse.ok) {
            throw new Error(`Boundary API error: ${boundaryResponse.status} ${boundaryResponse.statusText}`);
        }

        const info = await infoResponse.json();
        console.log('API response:', info);
        const boundaryData = await boundaryResponse.json();

        // Display school info and map
        displaySchoolInfo(info);
        displayCatchmentMap(boundaryData, info.school_location);

        // Show sections
        schoolInfoSection.style.display = 'block';
        mapSection.style.display = 'block';
        addressSearchSection.style.display = 'block';

        // Scroll to results
        schoolInfoSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (error) {
        console.error('Error loading school data:', error);
        alert('Error loading school data. Please try again.');
    } finally {
        showLoading(false);
    }
}

// ============================================
// Address Search Functionality
// ============================================

searchAddressBtn.addEventListener('click', async function () {
    const streetNumber = searchStreetNumber.value.trim();
    const street = searchStreet.value.trim();
    const suburb = searchSuburb.value.trim();
    const postcode = searchPostcode.value.trim();
    const state = searchState.value.trim();
    const limit = searchLimit.value;

    if (!currentSchoolId) {
        searchResults.innerHTML = '<div class="error">Please select a school first</div>';
        resultsSection.style.display = 'block';
        return;
    }

    if (!street && !suburb && !postcode && !state && !streetNumber) {
        searchResults.innerHTML = '<div class="error">Please enter at least one search criteria</div>';
        resultsSection.style.display = 'block';
        return;
    }

    showLoading(true);

    try {
        const params = new URLSearchParams();
        if (streetNumber) params.append('street_number', streetNumber);
        if (street) params.append('street', street);
        if (suburb) params.append('suburb', suburb);
        if (postcode) params.append('postcode', postcode);
        if (state) params.append('state', state);
        params.append('limit', limit);

        // Use school-specific endpoint to get addresses with distance
        const response = await fetch(`/api/school/${currentSchoolId}/addresses?${params}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch data');
        }

        if (data.addresses.length === 0) {
            searchResults.innerHTML = `
                <div class="no-results">
                    No addresses found matching your search criteria within this school catchment
                </div>
            `;
            resultsSection.style.display = 'block';
            return;
        }

        // Display results in the same format as address lookup
        displaySearchResults(data);
        resultsSection.style.display = 'block';

    } catch (error) {
        console.error('Error searching addresses:', error);
        searchResults.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        resultsSection.style.display = 'block';
    } finally {
        showLoading(false);
    }
});

// Allow Enter key on search inputs
[searchStreetNumber, searchStreet, searchSuburb, searchPostcode].forEach(input => {
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchAddressBtn.click();
            }
        });
    }
});
