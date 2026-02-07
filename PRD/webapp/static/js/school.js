/**
 * School Catchment Search JavaScript
 * Handles school autocomplete, address filtering, and map visualization
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
// Address Search Autocomplete
// ============================================

// Autocomplete for Street Name in address filter
let streetSearchDebounce;
if (searchStreet && searchStreetSuggestions) {
    searchStreet.addEventListener('input', (e) => {
        clearTimeout(streetSearchDebounce);
        const query = e.target.value.trim();

        if (query.length < 2) {
            searchStreetSuggestions.innerHTML = '';
            searchStreetSuggestions.style.display = 'none';
            return;
        }

        streetSearchDebounce = setTimeout(async () => {
            try {
                const response = await fetch(`/api/autocomplete/streets?q=${encodeURIComponent(query)}`);
                const data = await response.json();

                if (data.length > 0) {
                    searchStreetSuggestions.innerHTML = data.map(item => {
                        const streetFull = item.street_type ? `${item.street_name} ${item.street_type}` : item.street_name;
                        return `<div class="suggestion-item" data-value="${item.street_name}">${streetFull}</div>`;
                    }).join('');
                    searchStreetSuggestions.style.display = 'block';

                    // Add click handlers
                    searchStreetSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            searchStreet.value = item.dataset.value;
                            searchStreetSuggestions.style.display = 'none';
                        });
                    });
                } else {
                    searchStreetSuggestions.style.display = 'none';
                }
            } catch (error) {
                console.error('Error fetching street suggestions:', error);
            }
        }, 300);
    });
}

// Autocomplete for Suburb in address filter
let suburbSearchDebounce;
if (searchSuburb && searchSuburbSuggestions) {
    searchSuburb.addEventListener('input', (e) => {
        clearTimeout(suburbSearchDebounce);
        const query = e.target.value.trim();

        if (query.length < 2) {
            searchSuburbSuggestions.innerHTML = '';
            searchSuburbSuggestions.style.display = 'none';
            return;
        }

        suburbSearchDebounce = setTimeout(async () => {
            try {
                const response = await fetch(`/api/autocomplete/suburbs?q=${encodeURIComponent(query)}`);
                const data = await response.json();

                if (data.length > 0) {
                    searchSuburbSuggestions.innerHTML = data.map(item =>
                        `<div class="suggestion-item" data-value="${item.suburb}">
                            ${item.suburb} <span class="suggestion-meta">${item.state} ${item.postcode}</span>
                        </div>`
                    ).join('');
                    searchSuburbSuggestions.style.display = 'block';

                    // Add click handlers
                    searchSuburbSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            searchSuburb.value = item.dataset.value;
                            searchSuburbSuggestions.style.display = 'none';
                        });
                    });
                } else {
                    searchSuburbSuggestions.style.display = 'none';
                }
            } catch (error) {
                console.error('Error fetching suburb suggestions:', error);
            }
        }, 300);
    });
}

// Hide suggestions when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.autocomplete-wrapper')) {
        if (searchStreetSuggestions) searchStreetSuggestions.style.display = 'none';
        if (searchSuburbSuggestions) searchSuburbSuggestions.style.display = 'none';
    }
});

// ============================================
// School Autocomplete
// ============================================

schoolInput.addEventListener('input', function () {
    const query = this.value.trim();

    // Clear previous timer
    clearTimeout(debounceTimer);

    if (query.length < 3) {
        schoolSuggestions.innerHTML = '';
        schoolSuggestions.style.display = 'none';
        return;
    }

    // Debounce API call
    debounceTimer = setTimeout(() => {
        fetchSchoolSuggestions(query);
    }, 300);
});

async function fetchSchoolSuggestions(query) {
    try {
        const url = `/api/autocomplete/schools?q=${encodeURIComponent(query)}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displaySchoolSuggestions(data);
    } catch (error) {
        console.error('Error fetching school suggestions:', error);
        schoolSuggestions.innerHTML = '<div class="autocomplete-item error">Error loading suggestions</div>';
        schoolSuggestions.style.display = 'block';
    }
}

function displaySchoolSuggestions(schools) {
    if (!schools || schools.length === 0) {
        schoolSuggestions.innerHTML = '<div class="autocomplete-item no-results">No schools found</div>';
        schoolSuggestions.style.display = 'block';
        return;
    }

    schoolSuggestions.innerHTML = schools.map(school => `
        <div class="autocomplete-item" data-school-id="${school.school_id}" data-school-name="${school.school_name}">
            <div class="school-suggestion">
                <span class="school-name">${school.school_name}</span>
                <span class="school-meta">
                    <span class="badge badge-${school.school_type.toLowerCase()}">${school.school_type}</span>
                </span>
            </div>
        </div>
    `).join('');

    schoolSuggestions.style.display = 'block';

    // Add click handlers
    document.querySelectorAll('#schoolSuggestions .autocomplete-item').forEach(item => {
        item.addEventListener('click', function () {
            const schoolId = this.dataset.schoolId;
            const schoolName = this.dataset.schoolName;

            schoolInput.value = schoolName;
            currentSchoolId = schoolId;
            schoolSuggestions.style.display = 'none';

            // Auto-submit form
            loadSchoolData(schoolId);
        });
    });
}

// Close suggestions when clicking outside
document.addEventListener('click', function (e) {
    if (!schoolInput.contains(e.target) && !schoolSuggestions.contains(e.target)) {
        schoolSuggestions.style.display = 'none';
    }
});

// ============================================
// Form Submission
// ============================================

schoolSearchForm.addEventListener('submit', function (e) {
    e.preventDefault();

    if (currentSchoolId) {
        console.log('Selected school ID:', currentSchoolId);
        loadSchoolData(currentSchoolId);
    } else {
        // If user typed something but didn't select from dropdown,
        // try to find the best match by name
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

async function loadPage(page) {
    if (page < 1 || page > totalPages) return;

    showLoading(true);
    currentPage = page;
    const offset = (page - 1) * pageSize;

    try {
        const response = await fetch(`/api/school/${currentSchoolId}/addresses?limit=${pageSize}&offset=${offset}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const addressData = await response.json();

        // Update total based on search results
        totalAddresses = addressData.total_count;
        totalPages = Math.ceil(totalAddresses / pageSize);

        // Replace addresses with new page
        allAddresses = addressData.addresses || [];
        filteredAddresses = [...allAddresses];

        // Re-display addresses
        displayAddresses(filteredAddresses);

        // Update filter count
        document.getElementById('filterResultCount').textContent = totalAddresses.toLocaleString();

        // Update pagination UI
        updatePagination();

        // Scroll to filter section
        if (page > 1) {
            filterSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    } catch (error) {
        console.error('Error loading page:', error);
        alert('Error loading addresses. Please try again.');
    } finally {
        showLoading(false);
    }
}

function updatePagination() {
    const paginationDiv = document.getElementById('paginationControls');
    if (!paginationDiv) return;

    if (totalPages <= 1) {
        paginationDiv.style.display = 'none';
        return;
    }

    paginationDiv.style.display = 'flex';

    // Update page info
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages} (${totalAddresses.toLocaleString()} total addresses)`;

    // Generate page buttons
    const pageButtonsDiv = document.getElementById('pageButtons');
    pageButtonsDiv.innerHTML = '';

    // First button
    const firstBtn = document.createElement('button');
    firstBtn.textContent = 'First';
    firstBtn.className = 'btn-page';
    firstBtn.disabled = currentPage === 1;
    firstBtn.onclick = () => loadPage(1);
    pageButtonsDiv.appendChild(firstBtn);

    // Previous button
    const prevBtn = document.createElement('button');
    prevBtn.textContent = 'Previous';
    prevBtn.className = 'btn-page';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => loadPage(currentPage - 1);
    pageButtonsDiv.appendChild(prevBtn);

    // Page number buttons (show max 7 pages)
    const maxButtons = 7;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);

    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }

    if (startPage > 1) {
        const ellipsis = document.createElement('span');
        ellipsis.textContent = '...';
        ellipsis.className = 'page-ellipsis';
        pageButtonsDiv.appendChild(ellipsis);
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = i === currentPage ? 'btn-page active' : 'btn-page';
        pageBtn.onclick = () => loadPage(i);
        pageButtonsDiv.appendChild(pageBtn);
    }

    if (endPage < totalPages) {
        const ellipsis = document.createElement('span');
        ellipsis.textContent = '...';
        ellipsis.className = 'page-ellipsis';
        pageButtonsDiv.appendChild(ellipsis);
    }

    // Next button
    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Next';
    nextBtn.className = 'btn-page';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => loadPage(currentPage + 1);
    pageButtonsDiv.appendChild(nextBtn);

    // Last button
    const lastBtn = document.createElement('button');
    lastBtn.textContent = 'Last';
    lastBtn.className = 'btn-page';
    lastBtn.disabled = currentPage === totalPages;
    lastBtn.onclick = () => loadPage(totalPages);
    pageButtonsDiv.appendChild(lastBtn);

    // Jump to page
    const jumpInput = document.getElementById('jumpToPage');
    if (jumpInput) {
        jumpInput.max = totalPages;
        jumpInput.value = currentPage;
    }
}

// ============================================
// Display Functions
// ============================================

function displaySchoolInfo(info) {
    // Debug: Log full API response
    console.log('displaySchoolInfo received:', info);

    document.getElementById('schoolName').textContent = info.school_name;
    document.getElementById('schoolTypeBadge').textContent = info.school_type;
    document.getElementById('schoolTypeBadge').className = `badge badge-${info.school_type.toLowerCase()}`;
    document.getElementById('yearLevels').textContent = info.year_levels;

    // Display school type description
    const typeDescriptions = {
        'PRIMARY': 'Government Primary School',
        'SECONDARY': 'Government Secondary School',
        'FUTURE': 'Planned Future School',
        'HIGH_GIRLS': 'Selective Girls High School',
        'HIGH_BOYS': 'Selective Boys High School',
        'HIGH_CO_ED': 'Selective Co-Ed High School',
        'HIGH': 'Selective High School'
    };
    document.getElementById('schoolType').textContent = typeDescriptions[info.school_type] || (info.school_type ? `Government ${info.school_type} School` : 'Government School');

    // Display school sector
    document.getElementById('schoolSector').textContent = info.school_sector || 'N/A';

    // Display school URL if available
    if (info.school_url && info.school_url.trim()) {
        let urlString = info.school_url.trim();
        // Add https:// if no protocol is specified
        if (!urlString.startsWith('http://') && !urlString.startsWith('https://')) {
            urlString = 'https://' + urlString;
        }
        document.getElementById('schoolUrl').href = urlString;
        document.getElementById('schoolUrlText').textContent = info.school_name;
        document.getElementById('schoolUrl-container').style.display = 'block';
    } else {
        document.getElementById('schoolUrl-container').style.display = 'none';
    }

    // Display school profile URL if available
    if (info.acara_url && info.acara_url.trim()) {
        let profileUrlString = info.acara_url.trim();
        // Add https:// if no protocol is specified
        if (!profileUrlString.startsWith('http://') && !profileUrlString.startsWith('https://')) {
            profileUrlString = 'https://' + profileUrlString;
        }
        document.getElementById('schoolProfile').href = profileUrlString;
        document.getElementById('schoolProfile-container').style.display = 'block';
    } else {
        document.getElementById('schoolProfile-container').style.display = 'none';
    }

    // Display NAPLAN scores URL if available
    if (info.naplan_url && info.naplan_url.trim()) {
        let naplanUrlString = info.naplan_url.trim();
        // Add https:// if no protocol is specified
        if (!naplanUrlString.startsWith('http://') && !naplanUrlString.startsWith('https://')) {
            naplanUrlString = 'https://' + naplanUrlString;
        }
        document.getElementById('naplanScores').href = naplanUrlString;
        document.getElementById('naplanScores-container').style.display = 'block';
    } else {
        document.getElementById('naplanScores-container').style.display = 'none';
    }

    // Display ICSEA if available
    console.log('ICSEA value:', info.icsea, 'Type:', typeof info.icsea);
    if (info.icsea !== null && info.icsea !== undefined && info.icsea !== '') {
        document.getElementById('icsea').textContent = Math.round(info.icsea);
        document.getElementById('icsea-container').style.display = 'block';
        console.log('✓ ICSEA displayed:', Math.round(info.icsea));
    } else {
        document.getElementById('icsea-container').style.display = 'none';
        console.log('✗ ICSEA hidden (value is:', info.icsea, ')');
    }

    // Display ICSEA percentile if available
    console.log('ICSEA percentile value:', info.icsea_percentile, 'Type:', typeof info.icsea_percentile);
    if (info.icsea_percentile !== null && info.icsea_percentile !== undefined && info.icsea_percentile !== '') {
        document.getElementById('icsea-percentile').textContent = Math.round(info.icsea_percentile) + '%';
        document.getElementById('icsea-percentile-container').style.display = 'block';
        console.log('✓ ICSEA percentile displayed:', Math.round(info.icsea_percentile) + '%');
    } else {
        document.getElementById('icsea-percentile-container').style.display = 'none';
        console.log('✗ ICSEA percentile hidden (value is:', info.icsea_percentile, ')');
    }
}

function displayCatchmentMap(boundaryData, schoolLocation) {
    // Initialize map if not exists
    if (!catchmentMap) {
        catchmentMap = L.map('catchmentMap').setView([-33.8688, 151.2093], 13); // Default to Sydney

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(catchmentMap);
    }

    // Remove existing layer
    if (catchmentLayer) {
        catchmentMap.removeLayer(catchmentLayer);
    }

    // Add catchment boundary with light green styling
    catchmentLayer = L.geoJSON(boundaryData.geojson, {
        style: {
            color: '#059669',
            weight: 2,
            opacity: 0.8,
            fillColor: '#86efac',
            fillOpacity: 0.3
        }
    }).addTo(catchmentMap);

    // Fix map size and fit to boundary
    setTimeout(() => {
        catchmentMap.invalidateSize();
        catchmentMap.fitBounds(catchmentLayer.getBounds());
    }, 100);

    // Add school marker at centroid with custom SVG icon
    console.log('School location data:', schoolLocation);

    if (schoolLocation && schoolLocation.latitude && schoolLocation.longitude) {
        console.log(`Adding marker at: ${schoolLocation.latitude}, ${schoolLocation.longitude}`);

        // Get school name from DOM (already displayed in schoolName element)
        const schoolNameDisplay = document.getElementById('schoolName') ? document.getElementById('schoolName').textContent : 'School';

        // Create custom SVG school icon
        const schoolSvgIcon = L.divIcon({
            className: 'school-marker-custom',
            html: `
                <div style="position: relative; width: 40px; height: 50px; cursor: pointer;">
                    <svg viewBox="0 0 24 24" style="width: 100%; height: 100%; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));" xmlns="http://www.w3.org/2000/svg">
                        <!-- Building shape -->
                        <path d="M6 2h12v2H6V2z" fill="#c41230" stroke="#fff" stroke-width="0.5"/>
                        <path d="M6 4h12v16H6V4z" fill="#e6244a" stroke="#fff" stroke-width="0.5"/>
                        <!-- Windows -->
                        <rect x="8" y="6" width="2" height="2" fill="#fff" opacity="0.8"/>
                        <rect x="12" y="6" width="2" height="2" fill="#fff" opacity="0.8"/>
                        <rect x="14" y="6" width="2" height="2" fill="#fff" opacity="0.8"/>
                        <rect x="8" y="10" width="2" height="2" fill="#fff" opacity="0.8"/>
                        <rect x="12" y="10" width="2" height="2" fill="#fff" opacity="0.8"/>
                        <rect x="14" y="10" width="2" height="2" fill="#fff" opacity="0.8"/>
                        <rect x="8" y="14" width="2" height="2" fill="#fff" opacity="0.8"/>
                        <rect x="12" y="14" width="2" height="2" fill="#fff" opacity="0.8"/>
                        <rect x="14" y="14" width="2" height="2" fill="#fff" opacity="0.8"/>
                        <!-- Door -->
                        <rect x="11" y="16" width="2" height="4" fill="#fff" opacity="0.8"/>
                        <!-- Flag pole and flag -->
                        <rect x="16" y="2" width="1" height="6" fill="#333"/>
                        <path d="M17 3 L17 7 L21 5 Z" fill="#ffd700" stroke="#333" stroke-width="0.5"/>
                    </svg>
                    <!-- Pointer -->
                    <div style="position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 8px solid transparent; border-right: 8px solid transparent; border-top: 8px solid #c41230;"></div>
                </div>
            `,
            iconSize: [40, 50],
            iconAnchor: [20, 50],
            popupAnchor: [0, -50]
        });

        const marker = L.marker([schoolLocation.latitude, schoolLocation.longitude], {
            icon: schoolSvgIcon,
            title: schoolNameDisplay
        }).addTo(catchmentMap);

        console.log('Marker added successfully');

        // Add popup with school information
        const popupContent = `
            <div style="font-family: Arial, sans-serif; min-width: 180px;">
                <strong style="font-size: 14px; color: #1e3a8a;">${schoolNameDisplay}</strong>
                <div style="margin-top: 6px; font-size: 12px; color: #333;">
                    <div><strong>Location:</strong></div>
                    <div>Lat: ${schoolLocation.latitude.toFixed(4)}</div>
                    <div>Lon: ${schoolLocation.longitude.toFixed(4)}</div>
                    ${schoolLocation.suburb ? `<div style="margin-top: 6px;"><strong>${schoolLocation.suburb}, ${schoolLocation.state || ''} ${schoolLocation.postcode || ''}</strong></div>` : ''}
                </div>
            </div>
        `;

        marker.bindPopup(popupContent, {
            maxWidth: 250,
            className: 'school-popup'
        });

        // Optional: Open popup on click
        marker.on('click', function () {
            this.openPopup();
        });

        // Add hover effect
        marker.on('mouseover', function () {
            this.getElement().style.filter = 'drop-shadow(0 4px 8px rgba(0,0,0,0.4)) brightness(1.1)';
        });
        marker.on('mouseout', function () {
            this.getElement().style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))';
        });
    } else {
        console.warn('School location data is missing or incomplete:', schoolLocation);
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

// ============================================
// Helper Functions
// ============================================

function calculateDistance(lat1, lon1, lat2, lon2) {
    // Haversine formula
    const R = 6371; // Earth's radius in km
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);

    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;

    if (distance < 1) {
        return `${Math.round(distance * 1000)} m`;
    } else {
        return `${distance.toFixed(2)} km`;
    }
}

function toRad(degrees) {
    return degrees * Math.PI / 180;
}

function generatePropertyLinks(address) {
    if (!address.street_name || !address.suburb || !address.street_number) {
        return '-';
    }

    // Helper function to format text for URLs
    const formatForUrl = (text) => {
        if (!text) return '';
        return text.toLowerCase()
            .replace(/\s+/g, '-')
            .replace(/[^a-z0-9-]/g, '');
    };

    // Build street number
    const urlStreetNumber = address.street_number.replace('N/A', '').trim();

    // Get unit number (just the number, not the type)
    const urlUnitNumber = address.unit_number ? address.unit_number.toString().trim() : '';

    const expandedTypeRE = expandStreetTypeRealEstate(address.street_type);
    const expandedTypeDomain = expandStreetTypeDomain(address.street_type);

    const urlStreetNameRealEstate = formatForUrl([address.street_name, expandedTypeRE].filter(Boolean).join(' '));
    const urlStreetNameDomain = formatForUrl([address.street_name, expandedTypeDomain].filter(Boolean).join(' '));
    const urlSuburb = formatForUrl(address.suburb);
    const urlState = (address.state || 'nsw').toLowerCase();
    const urlPostcode = address.postcode || '';

    // Build RealEstate URL with unit prefix if unit exists
    let realEstateUrl = '';
    if (urlStreetNumber && urlStreetNameRealEstate && urlSuburb && urlState && urlPostcode) {
        if (urlUnitNumber) {
            // Format: unit-4-53-57-burdett-cres-hornsby-nsw-2077
            realEstateUrl = `https://www.realestate.com.au/property/unit-${urlUnitNumber}-${urlStreetNumber}-${urlStreetNameRealEstate}-${urlSuburb}-${urlState}-${urlPostcode}/`;
        } else {
            realEstateUrl = `https://www.realestate.com.au/property/${urlStreetNumber}-${urlStreetNameRealEstate}-${urlSuburb}-${urlState}-${urlPostcode}/`;
        }
    }

    // Build Domain URL with unit number (no prefix) if unit exists
    let domainUrl = '';
    if (urlStreetNumber && urlStreetNameDomain && urlSuburb && urlState && urlPostcode) {
        if (urlUnitNumber) {
            // Format: 4-53-57-burdett-crescent-hornsby-nsw-2077
            domainUrl = `https://www.domain.com.au/property-profile/${urlUnitNumber}-${urlStreetNumber}-${urlStreetNameDomain}-${urlSuburb}-${urlState}-${urlPostcode}`;
        } else {
            domainUrl = `https://www.domain.com.au/property-profile/${urlStreetNumber}-${urlStreetNameDomain}-${urlSuburb}-${urlState}-${urlPostcode}`;
        }
    }

    if (!realEstateUrl && !domainUrl) {
        return '-';
    }

    return `
        <div style="display: flex; flex-direction: column; gap: 8px;">
            ${realEstateUrl ? `<a href="${realEstateUrl}" target="_blank" class="property-link" style="display: block; text-align: center; padding: 6px 12px; background: #c41230; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500; white-space: nowrap; min-width: 85px;" title="View on RealEstate.com.au">RealEstate</a>` : ''}
            ${domainUrl ? `<a href="${domainUrl}" target="_blank" class="property-link" style="display: block; text-align: center; padding: 6px 12px; background: #16a34a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500; white-space: nowrap; min-width: 85px;" title="View on Domain.com.au">Domain</a>` : ''}
        </div>
    `;
}

function expandStreetTypeRealEstate(streetType) {
    if (!streetType) return '';
    const abbreviations = {
        'avenue': 'ave', 'av': 'ave', 'ave': 'ave',
        'street': 'st', 'st': 'st',
        'road': 'rd', 'rd': 'rd',
        'drive': 'dr', 'dr': 'dr',
        'court': 'ct', 'ct': 'ct',
        'place': 'pl', 'pl': 'pl',
        'crescent': 'cres', 'cres': 'cres', 'cr': 'cres',
        'lane': 'ln', 'ln': 'ln',
        'terrace': 'tce', 'tce': 'tce',
        'parade': 'pde', 'pde': 'pde',
        'way': 'way',
        'highway': 'hwy', 'hwy': 'hwy',
        'esplanade': 'esp', 'espl': 'esp', 'esp': 'esp'
    };
    const lowerType = streetType.toLowerCase();
    return abbreviations[lowerType] || lowerType;
}

function expandStreetTypeDomain(streetType) {
    if (!streetType) return '';
    const expansions = {
        'av': 'avenue', 'ave': 'avenue', 'avenue': 'avenue',
        'st': 'street', 'street': 'street',
        'rd': 'road', 'road': 'road',
        'dr': 'drive', 'drive': 'drive',
        'ct': 'court', 'court': 'court',
        'pl': 'place', 'place': 'place',
        'cr': 'crescent', 'cres': 'crescent', 'crescent': 'crescent',
        'ln': 'lane', 'lane': 'lane',
        'tce': 'terrace', 'terrace': 'terrace',
        'pde': 'parade', 'parade': 'parade',
        'way': 'way',
        'hwy': 'highway', 'highway': 'highway',
        'espl': 'esplanade', 'esp': 'esplanade', 'esplanade': 'esplanade'
    };
    const lowerType = streetType.toLowerCase();
    return expansions[lowerType] || lowerType;
}

function getGeocodeTypeDescription(code) {
    const descriptions = {
        'BAP': 'Building Access Point - Point of access to the building',
        'BC': 'Building Centroid - Centre of building footprint',
        'BCP': 'Building Centroid Point - Centre of building',
        'CDF': 'Cadastral Frontage - Property boundary on street',
        'EC': 'Emergency Access - Emergency service access point',
        'ECP': 'Emergency Centroid Point - Emergency centroid',
        'FC': 'Frontage Centre - Centre of property frontage',
        'FCP': 'Frontage Centre Point - Centre point of frontage',
        'GAP': 'Gazetted Address Point - Official gazetted location',
        'LCP': 'Locality Centre Point - Centre of locality',
        'PAP': 'Property Access Point - Main property access',
        'PC': 'Property Centroid - Centre of property',
        'UC': 'Unit Centroid - Centre of unit'
    };
    return descriptions[code] || 'Unknown geocode type';
}

function getConfidenceDescription(confidence) {
    const descriptions = {
        'HIGH': 'High confidence in coordinate accuracy',
        'MEDIUM': 'Medium confidence in coordinate accuracy',
        'LOW': 'Low confidence in coordinate accuracy',
        'VERY LOW': 'Very low confidence in coordinate accuracy',
        'UNKNOWN': 'Confidence level unknown'
    };
    return descriptions[confidence] || 'Unknown confidence level';
}

function openGoogleMaps(lat, lng) {
    window.open(`https://www.google.com/maps?q=${lat},${lng}`, '_blank');
}

function showLoading(show) {
    loadingIndicator.style.display = show ? 'flex' : 'none';
}

function displaySearchResults(data) {
    // Use the same format as address lookup page
    searchResults.innerHTML = `
        <div class="results-header">
            <div class="results-title">Search Results in this School Catchment</div>
            <div class="results-count">${data.count} result(s)</div>
        </div>
        
        <!-- Desktop: Compact table with expandable rows -->
        <table class="results-table">
            <thead>
                <tr>
                    <th style="width: 50px;"></th>
                    <th>Address</th>
                    <th>Distance</th>
                    <th>Confidence</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="schoolAddressResultsTableBody">
                ${data.addresses.map((addr, index) => {
        const streetName = [addr.street_name, addr.street_type].filter(Boolean).join(' ').trim();

        // Build street number - only show if number_first exists
        let streetNumber = '';
        if (addr.number_first) {
            if (addr.number_last) {
                streetNumber = `${addr.number_first}${addr.number_first_suffix || ''}-${addr.number_last}${addr.number_last_suffix || ''}`;
            } else {
                streetNumber = `${addr.number_first}${addr.number_first_suffix || ''}`;
            }
        }

        const unit = addr.flat_number
            ? (addr.flat_type ? `${addr.flat_type} ${addr.flat_number}` : addr.flat_number)
            : '';

        // Full address for display
        const fullAddress = [
            unit,
            streetNumber,
            streetName
        ].filter(Boolean).join(' ');

        const coords = addr.latitude && addr.longitude
            ? `${parseFloat(addr.latitude).toFixed(6)}, ${parseFloat(addr.longitude).toFixed(6)}`
            : 'N/A';

        const distanceFromSchool = addr.distance_km !== null && addr.distance_km !== undefined
            ? parseFloat(addr.distance_km).toFixed(2)
            : 'N/A';

        // Calculate distance from state CBD using Haversine formula
        let distanceFromCBD = '';
        if (addr.latitude && addr.longitude) {
            // Define CBD coordinates for each state
            const stateCBDs = {
                'NSW': { lat: -33.8688, lng: 151.2093, city: 'Sydney' },
                'VIC': { lat: -37.8136, lng: 144.9631, city: 'Melbourne' },
                'QLD': { lat: -27.4698, lng: 153.0251, city: 'Brisbane' },
                'SA': { lat: -34.9285, lng: 138.6007, city: 'Adelaide' },
                'WA': { lat: -31.9505, lng: 115.8605, city: 'Perth' },
                'TAS': { lat: -42.8821, lng: 147.3272, city: 'Hobart' },
                'NT': { lat: -12.4634, lng: 130.8456, city: 'Darwin' },
                'ACT': { lat: -35.2809, lng: 149.1300, city: 'Canberra' }
            };

            const stateCBD = stateCBDs[addr.state];
            if (stateCBD) {
                const lat1 = parseFloat(addr.latitude);
                const lng1 = parseFloat(addr.longitude);
                const lat2 = stateCBD.lat;
                const lng2 = stateCBD.lng;

                // Haversine formula
                const R = 6371; // Earth's radius in km
                const dLat = (lat2 - lat1) * Math.PI / 180;
                const dLng = (lng2 - lng1) * Math.PI / 180;
                const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                    Math.sin(dLng / 2) * Math.sin(dLng / 2);
                const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
                const distance = R * c;

                distanceFromCBD = `${distance.toFixed(2)} km from ${stateCBD.city} CBD`;
            }
        }

        const googleMapsUrl = addr.latitude && addr.longitude
            ? `https://www.google.com/maps?q=${parseFloat(addr.latitude).toFixed(6)},${parseFloat(addr.longitude).toFixed(6)}`
            : '';

        const geocodeType = addr.geocode_type_code || 'N/A';

        let confidenceText = 'Unknown';
        let confidenceColor = '#999';

        if (addr.confidence !== null && addr.confidence !== undefined) {
            const confValue = parseInt(addr.confidence);
            if (confValue === 3) {
                confidenceText = 'Very High';
                confidenceColor = '#28a745';
            } else if (confValue === 2) {
                confidenceText = 'High';
                confidenceColor = '#5cb85c';
            } else if (confValue === 1) {
                confidenceText = 'Medium';
                confidenceColor = '#ffc107';
            } else if (confValue === 0) {
                confidenceText = 'Low';
                confidenceColor = '#ff9800';
            } else if (confValue === -1) {
                confidenceText = 'None';
                confidenceColor = '#dc3545';
            }
        }

        // Helper function for URL formatting
        const formatForUrl = (str) => {
            if (!str) return '';
            return str.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
        };

        // Expand street type for RealEstate
        const expandStreetTypeRealEstate = (type) => {
            if (!type) return '';
            const abbreviations = {
                'avenue': 'ave', 'av': 'ave', 'ave': 'ave',
                'street': 'st', 'st': 'st',
                'road': 'rd', 'rd': 'rd',
                'drive': 'dr', 'dr': 'dr',
                'court': 'ct', 'ct': 'ct',
                'place': 'pl', 'pl': 'pl',
                'crescent': 'cres', 'cres': 'cres', 'cr': 'cres',
                'lane': 'ln', 'ln': 'ln',
                'terrace': 'tce', 'tce': 'tce',
                'parade': 'pde', 'pde': 'pde',
                'way': 'way',
                'highway': 'hwy', 'hwy': 'hwy',
                'esplanade': 'esp', 'espl': 'esp', 'esp': 'esp'
            };
            return abbreviations[type.toLowerCase()] || type.toLowerCase();
        };

        // Expand street type for Domain
        const expandStreetTypeDomain = (type) => {
            if (!type) return '';
            const abbreviations = {
                'av': 'avenue', 'ave': 'avenue', 'avenue': 'avenue',
                'st': 'street', 'street': 'street',
                'rd': 'road', 'road': 'road',
                'dr': 'drive', 'drive': 'drive',
                'ct': 'court', 'court': 'court',
                'pl': 'place', 'place': 'place',
                'cr': 'crescent', 'cres': 'crescent', 'crescent': 'crescent',
                'ln': 'lane', 'lane': 'lane',
                'tce': 'terrace', 'terrace': 'terrace',
                'pde': 'parade', 'parade': 'parade',
                'way': 'way',
                'hwy': 'highway', 'highway': 'highway',
                'espl': 'esplanade', 'esp': 'esplanade', 'esplanade': 'esplanade'
            };
            return abbreviations[type.toLowerCase()] || type.toLowerCase();
        };

        // Build property URLs
        const urlStreetNumber = streetNumber.trim();
        const urlUnitNumber = addr.flat_number ? addr.flat_number.toString() : '';
        const urlStreetNameRealEstate = formatForUrl([addr.street_name, expandStreetTypeRealEstate(addr.street_type)].filter(Boolean).join(' '));
        const urlStreetNameDomain = formatForUrl([addr.street_name, expandStreetTypeDomain(addr.street_type)].filter(Boolean).join(' '));
        const urlSuburb = formatForUrl(addr.suburb);
        const urlState = (addr.state || '').toLowerCase();
        const urlPostcode = addr.postcode || '';

        // Build RealEstate URL
        let realEstateUrl = '';
        if (urlStreetNumber && urlStreetNameRealEstate && urlSuburb && urlState && urlPostcode) {
            if (urlUnitNumber) {
                realEstateUrl = `https://www.realestate.com.au/property/unit-${urlUnitNumber}-${urlStreetNumber}-${urlStreetNameRealEstate}-${urlSuburb}-${urlState}-${urlPostcode}/`;
            } else {
                realEstateUrl = `https://www.realestate.com.au/property/${urlStreetNumber}-${urlStreetNameRealEstate}-${urlSuburb}-${urlState}-${urlPostcode}/`;
            }
        }

        // Build Domain URL
        let domainUrl = '';
        if (urlStreetNumber && urlStreetNameDomain && urlSuburb && urlState && urlPostcode) {
            if (urlUnitNumber) {
                domainUrl = `https://www.domain.com.au/property-profile/${urlUnitNumber}-${urlStreetNumber}-${urlStreetNameDomain}-${urlSuburb}-${urlState}-${urlPostcode}`;
            } else {
                domainUrl = `https://www.domain.com.au/property-profile/${urlStreetNumber}-${urlStreetNameDomain}-${urlSuburb}-${urlState}-${urlPostcode}`;
            }
        }

        // Desktop: Compact main row + expandable details row
        return `
                        <!-- Main row (always visible) -->
                        <tr class="results-row-main" data-row-index="${index}" data-lat="${addr.latitude || ''}" data-lng="${addr.longitude || ''}" onclick="toggleRowDetails(${index})">
                            <td><span class="expand-icon">▸</span></td>
                            <td>
                                <strong>${fullAddress}</strong><br>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">${addr.suburb || 'N/A'}, ${addr.state || 'N/A'} ${addr.postcode || ''}</span>
                            </td>
                            <td style="font-weight: 600; color: #059669;">${distanceFromSchool} km</td>
                            <td>
                                <span style="color: ${confidenceColor}; font-weight: 500; font-size: 0.9rem;">
                                    ${confidenceText}
                                </span>
                            </td>
                            <td style="white-space: nowrap;">
                                ${googleMapsUrl ? `<a href="${googleMapsUrl}" target="_blank" class="coords-button" title="View on Google Maps" onclick="event.stopPropagation()">📍 Map</a>` : ''}
                            </td>
                        </tr>
                        <!-- Details row (expandable) -->
                        <tr class="results-row-details" id="details-${index}" data-row-index="${index}">
                            <td colspan="5">
                                <div class="detail-grid">
                                    <div class="detail-item">
                                        <div class="detail-label">Coordinates</div>
                                        <div class="detail-value">${coords}</div>
                                    </div>
                                    <div class="detail-item">
                                        <div class="detail-label">Distance from CBD</div>
                                        <div class="detail-value">${distanceFromCBD || 'N/A'}</div>
                                    </div>
                                    <div class="detail-item">
                                        <div class="detail-label">Geocode Type</div>
                                        <div class="detail-value">${geocodeType}</div>
                                    </div>
                                    <div class="detail-item school-catchment-detail">
                                        <div class="detail-label">School Catchments</div>
                                        <div class="detail-value"><span style="color: #999;">Loading...</span></div>
                                    </div>
                                    <div class="detail-item" style="grid-column: 1 / -1;">
                                        <div class="detail-label">Property Links</div>
                                        <div class="detail-value" style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px;">
                                            ${realEstateUrl ? `<a href="${realEstateUrl}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #c41230; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500;">🏠 RealEstate.com.au</a>` : ''}
                                            ${domainUrl ? `<a href="${domainUrl}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #16a34a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500;">🏡 Domain.com.au</a>` : ''}
                                            ${!realEstateUrl && !domainUrl ? '<span style="color: #999;">No property links available</span>' : ''}
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `;
    }).join('')}
            </tbody>
        </table>
        
        <!-- Mobile: Card layout -->
        <div class="results-cards">
            ${data.addresses.map((addr, index) => {
        const streetName = [addr.street_name, addr.street_type].filter(Boolean).join(' ').trim();

        let streetNumber = '';
        if (addr.number_first) {
            if (addr.number_last) {
                streetNumber = `${addr.number_first}${addr.number_first_suffix || ''}-${addr.number_last}${addr.number_last_suffix || ''}`;
            } else {
                streetNumber = `${addr.number_first}${addr.number_first_suffix || ''}`;
            }
        }

        const unit = addr.flat_number
            ? (addr.flat_type ? `${addr.flat_type} ${addr.flat_number}` : addr.flat_number)
            : '';

        const fullAddress = [unit, streetNumber, streetName].filter(Boolean).join(' ');
        const coords = addr.latitude && addr.longitude
            ? `${parseFloat(addr.latitude).toFixed(6)}, ${parseFloat(addr.longitude).toFixed(6)}`
            : 'N/A';

        const distanceFromSchool = addr.distance_km !== null && addr.distance_km !== undefined
            ? parseFloat(addr.distance_km).toFixed(2)
            : 'N/A';

        const googleMapsUrl = addr.latitude && addr.longitude
            ? `https://www.google.com/maps?q=${parseFloat(addr.latitude).toFixed(6)},${parseFloat(addr.longitude).toFixed(6)}`
            : '';

        const geocodeType = addr.geocode_type_code || 'N/A';

        let confidenceText = 'Unknown';
        let confidenceColor = '#999';

        if (addr.confidence !== null && addr.confidence !== undefined) {
            const confValue = parseInt(addr.confidence);
            if (confValue === 3) {
                confidenceText = 'Very High';
                confidenceColor = '#28a745';
            } else if (confValue === 2) {
                confidenceText = 'High';
                confidenceColor = '#5cb85c';
            } else if (confValue === 1) {
                confidenceText = 'Medium';
                confidenceColor = '#ffc107';
            } else if (confValue === 0) {
                confidenceText = 'Low';
                confidenceColor = '#ff9800';
            } else if (confValue === -1) {
                confidenceText = 'None';
                confidenceColor = '#dc3545';
            }
        }

        // Property URLs (same logic as desktop)
        const formatForUrl = (str) => !str ? '' : str.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
        const expandStreetTypeRealEstate = (type) => {
            if (!type) return '';
            const abbreviations = {
                'avenue': 'ave', 'av': 'ave', 'ave': 'ave', 'street': 'st', 'st': 'st',
                'road': 'rd', 'rd': 'rd', 'drive': 'dr', 'dr': 'dr', 'court': 'ct', 'ct': 'ct',
                'place': 'pl', 'pl': 'pl', 'crescent': 'cres', 'cres': 'cres', 'cr': 'cres',
                'lane': 'ln', 'ln': 'ln', 'terrace': 'tce', 'tce': 'tce', 'parade': 'pde', 'pde': 'pde',
                'way': 'way', 'highway': 'hwy', 'hwy': 'hwy', 'esplanade': 'esp', 'espl': 'esp', 'esp': 'esp'
            };
            return abbreviations[type.toLowerCase()] || type.toLowerCase();
        };
        const expandStreetTypeDomain = (type) => {
            if (!type) return '';
            const abbreviations = {
                'av': 'avenue', 'ave': 'avenue', 'avenue': 'avenue', 'st': 'street', 'street': 'street',
                'rd': 'road', 'road': 'road', 'dr': 'drive', 'drive': 'drive', 'ct': 'court', 'court': 'court',
                'pl': 'place', 'place': 'place', 'cr': 'crescent', 'cres': 'crescent', 'crescent': 'crescent',
                'ln': 'lane', 'lane': 'lane', 'tce': 'terrace', 'terrace': 'terrace', 'pde': 'parade', 'parade': 'parade',
                'way': 'way', 'hwy': 'highway', 'highway': 'highway', 'espl': 'esplanade', 'esp': 'esplanade', 'esplanade': 'esplanade'
            };
            return abbreviations[type.toLowerCase()] || type.toLowerCase();
        };

        const urlStreetNumber = streetNumber.trim();
        const urlUnitNumber = addr.flat_number ? addr.flat_number.toString() : '';
        const urlStreetNameRealEstate = formatForUrl([addr.street_name, expandStreetTypeRealEstate(addr.street_type)].filter(Boolean).join(' '));
        const urlStreetNameDomain = formatForUrl([addr.street_name, expandStreetTypeDomain(addr.street_type)].filter(Boolean).join(' '));
        const urlSuburb = formatForUrl(addr.suburb);
        const urlState = (addr.state || '').toLowerCase();
        const urlPostcode = addr.postcode || '';

        let realEstateUrl = '';
        if (urlStreetNumber && urlStreetNameRealEstate && urlSuburb && urlState && urlPostcode) {
            if (urlUnitNumber) {
                realEstateUrl = `https://www.realestate.com.au/property/unit-${urlUnitNumber}-${urlStreetNumber}-${urlStreetNameRealEstate}-${urlSuburb}-${urlState}-${urlPostcode}/`;
            } else {
                realEstateUrl = `https://www.realestate.com.au/property/${urlStreetNumber}-${urlStreetNameRealEstate}-${urlSuburb}-${urlState}-${urlPostcode}/`;
            }
        }

        let domainUrl = '';
        if (urlStreetNumber && urlStreetNameDomain && urlSuburb && urlState && urlPostcode) {
            if (urlUnitNumber) {
                domainUrl = `https://www.domain.com.au/property-profile/${urlUnitNumber}-${urlStreetNumber}-${urlStreetNameDomain}-${urlSuburb}-${urlState}-${urlPostcode}`;
            } else {
                domainUrl = `https://www.domain.com.au/property-profile/${urlStreetNumber}-${urlStreetNameDomain}-${urlSuburb}-${urlState}-${urlPostcode}`;
            }
        }

        return `
                    <div class="result-card" data-row-index="${index}" data-lat="${addr.latitude || ''}" data-lng="${addr.longitude || ''}">
                        <div class="card-header">
                            <div class="card-address">${fullAddress}</div>
                            <div class="card-suburb">${addr.suburb || 'N/A'}, ${addr.state || 'N/A'} ${addr.postcode || ''}</div>
                        </div>
                        <div class="card-body">
                            <div class="card-info-grid">
                                <div class="card-info-item">
                                    <div class="card-info-label">Distance from School</div>
                                    <div class="card-info-value" style="color: #059669; font-weight: 600;">${distanceFromSchool} km</div>
                                </div>
                                <div class="card-info-item">
                                    <div class="card-info-label">Confidence</div>
                                    <div class="card-info-value" style="color: ${confidenceColor}; font-weight: 500;">${confidenceText}</div>
                                </div>
                                <div class="card-info-item">
                                    <div class="card-info-label">Coordinates</div>
                                    <div class="card-info-value" style="font-size: 0.85rem;">${coords}</div>
                                </div>
                                <div class="card-info-item">
                                    <div class="card-info-label">Geocode Type</div>
                                    <div class="card-info-value">${geocodeType}</div>
                                </div>
                            </div>
                            <div class="card-info-item" style="margin-top: var(--spacing-sm);">
                                <div class="card-info-label">School Catchments</div>
                                <div class="card-info-value card-school-catchment-${index}"><span style="color: #999;">Loading...</span></div>
                            </div>
                            <div class="card-actions">
                                ${googleMapsUrl ? `<a href="${googleMapsUrl}" target="_blank" class="card-action-btn btn-maps">📍 Maps</a>` : ''}
                                ${realEstateUrl ? `<a href="${realEstateUrl}" target="_blank" class="card-action-btn btn-realestate">RealEstate</a>` : ''}
                                ${domainUrl ? `<a href="${domainUrl}" target="_blank" class="card-action-btn btn-domain">Domain</a>` : ''}
                            </div>
                        </div>
                    </div>
                `;
    }).join('')}
        </div>
    `;

    // Fetch school catchments for each address
    fetchSchoolCatchmentsForResults();
}

// Toggle row details (desktop table)
function toggleRowDetails(index) {
    const mainRow = document.querySelector(`.results-row-main[data-row-index="${index}"]`);
    const detailsRow = document.getElementById(`details-${index}`);

    if (!mainRow || !detailsRow) return;

    const isExpanded = detailsRow.classList.contains('show');

    if (isExpanded) {
        detailsRow.classList.remove('show');
        mainRow.classList.remove('expanded');
    } else {
        detailsRow.classList.add('show');
        mainRow.classList.add('expanded');
    }
}

// Function to fetch school catchments for all addresses in search results
async function fetchSchoolCatchmentsForResults() {
    // Desktop table rows
    const mainRows = document.querySelectorAll('.results-row-main');

    for (const row of mainRows) {
        const rowIndex = row.dataset.rowIndex;
        const lat = row.dataset.lat;
        const lng = row.dataset.lng;
        const detailsRow = document.getElementById(`details-${rowIndex}`);
        const schoolCell = detailsRow ? detailsRow.querySelector('.school-catchment-detail .detail-value') : null;

        if (!lat || !lng || !schoolCell) {
            if (schoolCell) schoolCell.innerHTML = '<span style="color: #999;">No coordinates</span>';
            continue;
        }

        await fetchAndDisplaySchools(lat, lng, schoolCell);
    }

    // Mobile cards
    const cards = document.querySelectorAll('.result-card');

    for (const card of cards) {
        const rowIndex = card.dataset.rowIndex;
        const lat = card.dataset.lat;
        const lng = card.dataset.lng;
        const schoolCell = card.querySelector(`.card-school-catchment-${rowIndex}`);

        if (!lat || !lng || !schoolCell) {
            if (schoolCell) schoolCell.innerHTML = '<span style="color: #999;">No coordinates</span>';
            continue;
        }

        await fetchAndDisplaySchools(lat, lng, schoolCell);
    }
}

// Helper function to fetch and display schools for a given cell
async function fetchAndDisplaySchools(lat, lng, schoolCell) {
    if (!schoolCell) return;

    if (!lat || !lng) {
        schoolCell.innerHTML = '<span style="color: #999;">No coordinates</span>';
        return;
    }

    try {
        const response = await fetch(`/api/address/schools?lat=${lat}&lng=${lng}`);
        const data = await response.json();

        if (data.schools && data.schools.length > 0) {
            const schoolsHtml = data.schools.map(school => {
                const typeColors = {
                    'PRIMARY': '#2196F3',
                    'SECONDARY': '#4CAF50',
                    'HIGH_COED': '#4CAF50',
                    'FUTURE': '#FF9800'
                };
                const color = typeColors[school.school_type] || '#999';

                return `
                    <div style="margin-bottom: 4px;">
                        <a href="/school-search?school_id=${school.school_id}" 
                           style="color: var(--primary-color); text-decoration: none; font-weight: 500;"
                           title="Click to view all addresses in ${school.school_name} catchment">
                            ${school.school_name}
                        </a>
                        <span style="font-size: 0.75rem; color: ${color}; font-weight: 500; margin-left: 4px;">
                            (${school.school_type})
                        </span>
                    </div>
                `;
            }).join('');

            schoolCell.innerHTML = schoolsHtml;
        } else {
            schoolCell.innerHTML = '<span style="color: #999;">No catchment</span>';
        }
    } catch (error) {
        console.error('Error fetching schools:', error);
        schoolCell.innerHTML = '<span style="color: #dc3545;">Error loading</span>';
    }
}

function hideAllSections() {
    schoolInfoSection.style.display = 'none';
    mapSection.style.display = 'none';
    addressSearchSection.style.display = 'none';
    resultsSection.style.display = 'none';
}