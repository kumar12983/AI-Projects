/**
 * Australia School Search JavaScript
 * Handles Australian school autocomplete with state filter and 5km zone visualization
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
// School Autocomplete with State Filter
// ============================================

schoolInput.addEventListener('input', async (e) => {
    const query = e.target.value.trim();
    console.log('School input changed, query:', query, 'length:', query.length);

    if (query.length < 3) {
        schoolSuggestions.innerHTML = '';
        schoolSuggestions.style.display = 'none';
        return;
    }

    try {
        const state = stateFilter.value;
        const url = `/api/autocomplete/australia-schools?q=${encodeURIComponent(query)}${state ? '&state=' + state : ''}`;
        console.log('Fetching schools from:', url);
        const response = await fetch(url);
        const schools = await response.json();
        console.log('Schools received:', schools.length, schools);

        if (schools.length > 0) {
            schoolSuggestions.innerHTML = schools.map(school => `
                <div class="autocomplete-item" data-acara-id="${school.acara_sml_id}">
                    <strong>${school.school_name}</strong>
                    <div style="font-size: 0.85rem; color: #666;">
                        ${school.state} - ${school.school_sector}
                    </div>
                </div>
            `).join('');
            schoolSuggestions.style.display = 'block';

            // Add click handlers
            document.querySelectorAll('.autocomplete-item').forEach(item => {
                item.addEventListener('click', () => {
                    const acaraId = item.dataset.acaraId;
                    const schoolName = item.querySelector('strong').textContent;
                    schoolInput.value = schoolName;
                    schoolSuggestions.style.display = 'none';
                    selectedSchool = acaraId;
                });
            });
        } else {
            schoolSuggestions.innerHTML = '<div class="autocomplete-item">No schools found</div>';
            schoolSuggestions.style.display = 'block';
        }
    } catch (error) {
        console.error('Error fetching schools:', error);
    }
});

// Close suggestions when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.autocomplete-wrapper')) {
        schoolSuggestions.style.display = 'none';
    }
});

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

        // Load initial 200 addresses after school info is displayed
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
// Display Functions
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

function displayMap(data) {
    console.log('displayMap called with data:', data);
    console.log('geom_5km_buffer exists:', !!data.geom_5km_buffer);
    
    mapSection.removeAttribute('style');
    mapSection.style.display = 'block';
    console.log('mapSection display set to block');
    console.log('mapSection computed style:', window.getComputedStyle(mapSection).display);

    // Initialize map if not already done
    if (!map) {
        map = L.map('schoolMap');
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);
    }

    // Clear existing layers
    let clearedCount = 0;
    map.eachLayer(layer => {
        if (layer instanceof L.GeoJSON || layer instanceof L.Marker) {
            map.removeLayer(layer);
            clearedCount++;
        }
    });
    console.log('Cleared', clearedCount, 'existing layers from map');

    // Add school marker
    if (data.latitude && data.longitude) {
        const schoolMarker = L.marker([data.latitude, data.longitude]).addTo(map);
        schoolMarker.bindPopup(`<strong>${data.school_name}</strong><br>${data.school_sector}`);
        console.log('School marker added at:', data.latitude, data.longitude);
    }

    // Add 5km buffer if available
    if (data.geom_5km_buffer) {
        console.log('GeoJSON buffer data:', data.geom_5km_buffer);
        try {
            const bufferLayer = L.geoJSON(data.geom_5km_buffer, {
                style: {
                    color: '#3b82f6',
                    weight: 2,
                    opacity: 0.8,
                    fillColor: '#3b82f6',
                    fillOpacity: 0.1
                }
            }).addTo(map);

            const bounds = bufferLayer.getBounds();
            console.log('Buffer bounds:', bounds);
            console.log('Buffer bounds center:', bounds.getCenter());
            
            map.fitBounds(bounds, { padding: [20, 20] });
            console.log('Map fitted to bounds, current zoom:', map.getZoom());
            console.log('Map center:', map.getCenter());
            console.log('Buffer layer added successfully');
        } catch (error) {
            console.error('Error adding buffer layer:', error);
            // Fallback to center view if buffer fails
            if (data.latitude && data.longitude) {
                map.setView([data.latitude, data.longitude], 13);
            }
        }
    } else {
        console.log('No geom_5km_buffer data available');
        if (data.latitude && data.longitude) {
            map.setView([data.latitude, data.longitude], 13);
        }
    }

    // Scroll to map
    mapSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showLoading() {
    loadingIndicator.style.display = 'flex';
    schoolInfoSection.style.display = 'none';
    mapSection.style.display = 'none';
}

function hideLoading() {
    loadingIndicator.style.display = 'none';
}

// ============================================
// Address Search Autocomplete
// ============================================

// Autocomplete for Street Name
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

        if (!currentAcaraId) {
            searchStreetSuggestions.innerHTML = '<div class="suggestion-item no-results">Please select a school first</div>';
            searchStreetSuggestions.style.display = 'block';
            return;
        }

        streetSearchDebounce = setTimeout(async () => {
            try {
                const response = await fetch(`/api/australia-school/${currentAcaraId}/autocomplete/streets?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                if (data.length > 0) {
                    searchStreetSuggestions.innerHTML = data.map(item => {
                        const streetFull = item.street_type ? `${item.street_name} ${item.street_type}` : item.street_name;
                        return `<div class="suggestion-item" data-value="${item.street_name}">${streetFull}</div>`;
                    }).join('');
                    searchStreetSuggestions.style.display = 'block';

                    searchStreetSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            searchStreet.value = item.dataset.value;
                            searchStreetSuggestions.style.display = 'none';
                        });
                    });
                } else {
                    searchStreetSuggestions.innerHTML = '<div class="suggestion-item no-results">No streets found</div>';
                    searchStreetSuggestions.style.display = 'block';
                }
            } catch (error) {
                console.error('Error fetching street suggestions:', error);
            }
        }, 300);
    });
}

// Autocomplete for Suburb
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

        if (!currentAcaraId) {
            searchSuburbSuggestions.innerHTML = '<div class="suggestion-item no-results">Please select a school first</div>';
            searchSuburbSuggestions.style.display = 'block';
            return;
        }

        suburbSearchDebounce = setTimeout(async () => {
            try {
                const response = await fetch(`/api/australia-school/${currentAcaraId}/autocomplete/suburbs?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                if (data.length > 0) {
                    searchSuburbSuggestions.innerHTML = data.map(item => 
                        `<div class="suggestion-item" data-value="${item.locality_name}">
                            ${item.locality_name} <span class="suggestion-meta">${item.postcode} ${item.state_abbreviation}</span>
                        </div>`
                    ).join('');
                    searchSuburbSuggestions.style.display = 'block';

                    searchSuburbSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            searchSuburb.value = item.dataset.value;
                            searchSuburbSuggestions.style.display = 'none';
                        });
                    });
                } else {
                    searchSuburbSuggestions.innerHTML = '<div class="suggestion-item no-results">No suburbs found</div>';
                    searchSuburbSuggestions.style.display = 'block';
                }
            } catch (error) {
                console.error('Error fetching suburb suggestions:', error);
            }
        }, 300);
    });
}

// Autocomplete for Postcode
let postcodeSearchDebounce;
if (searchPostcode && searchPostcodeSuggestions) {
    searchPostcode.addEventListener('input', (e) => {
        clearTimeout(postcodeSearchDebounce);
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            searchPostcodeSuggestions.innerHTML = '';
            searchPostcodeSuggestions.style.display = 'none';
            return;
        }

        if (!currentAcaraId) {
            searchPostcodeSuggestions.innerHTML = '<div class="suggestion-item no-results">Please select a school first</div>';
            searchPostcodeSuggestions.style.display = 'block';
            return;
        }

        postcodeSearchDebounce = setTimeout(async () => {
            try {
                const response = await fetch(`/api/australia-school/${currentAcaraId}/autocomplete/postcodes?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                if (data.length > 0) {
                    searchPostcodeSuggestions.innerHTML = data.map(item => 
                        `<div class="suggestion-item" data-value="${item.postcode}">
                            ${item.postcode} <span class="suggestion-meta">${item.suburb}</span>
                        </div>`
                    ).join('');
                    searchPostcodeSuggestions.style.display = 'block';

                    searchPostcodeSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            searchPostcode.value = item.dataset.value;
                            searchPostcodeSuggestions.style.display = 'none';
                        });
                    });
                } else {
                    searchPostcodeSuggestions.innerHTML = '<div class="suggestion-item no-results">No postcodes found</div>';
                    searchPostcodeSuggestions.style.display = 'block';
                }
            } catch (error) {
                console.error('Error fetching postcode suggestions:', error);
            }
        }, 300);
    });
}

// Hide autocomplete dropdowns when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.autocomplete-wrapper')) {
        if (searchStreetSuggestions) searchStreetSuggestions.style.display = 'none';
        if (searchSuburbSuggestions) searchSuburbSuggestions.style.display = 'none';
        if (searchPostcodeSuggestions) searchPostcodeSuggestions.style.display = 'none';
    }
});

// ============================================
// Address Search Functions
// ============================================

async function loadAddresses(isInitialLoad = false) {
    console.log('loadAddresses called, currentAcaraId:', currentAcaraId, 'isInitialLoad:', isInitialLoad);
    
    if (!currentAcaraId) {
        console.log('No currentAcaraId, returning early');
        return;
    }

    // Only show loading indicator, don't hide school info/map sections
    loadingIndicator.style.display = 'flex';

    try {
        const params = new URLSearchParams();
        
        // Load 100 addresses at a time for better performance
        params.append('limit', PAGE_SIZE.toString());
        params.append('offset', '0');
        
        // Reset pagination for new searches
        currentOffset = 0;

        if (!isInitialLoad) {
            if (searchStreetNumber && searchStreetNumber.value) params.append('street_number', searchStreetNumber.value);
            if (searchStreet && searchStreet.value) params.append('street', searchStreet.value);
            if (searchSuburb && searchSuburb.value) params.append('suburb', searchSuburb.value);
            if (searchPostcode && searchPostcode.value) params.append('postcode', searchPostcode.value);
            if (searchState && searchState.value) params.append('state', searchState.value);
        }

        const url = `/api/australia-school/${currentAcaraId}/addresses?${params.toString()}`;
        console.log('Fetching addresses from:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('Addresses response:', data);

        if (data.error) {
            alert(data.error);
            hideLoading();
            return;
        }

        allAddresses = data.addresses;
        totalAddresses = data.total;
        currentOffset = PAGE_SIZE;
        displayAddresses(allAddresses, totalAddresses, false);

        // Show address search section and results
        addressSearchSection.style.display = 'block';
        resultsSection.style.display = 'block';

        hideLoading();

        // Scroll to results if not initial load
        if (!isInitialLoad) {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    } catch (error) {
        console.error('Error loading addresses:', error);
        alert('Error loading addresses');
        hideLoading();
    }
}

function displayAddresses(addresses, total, append = false) {
    if (!addresses || addresses.length === 0) {
        if (!append) {
            searchResults.innerHTML = `
                <div class="no-results">
                    <h3>No addresses found</h3>
                    <p>Try adjusting your search filters</p>
                </div>
            `;
        }
        return;
    }

    const addressRowsHtml = addresses.map((addr, index) => {
        // Adjust index for pagination
        const globalIndex = append ? allAddresses.length - addresses.length + index : index;
                    const streetName = [addr.street_name, addr.street_type].filter(Boolean).join(' ').trim();
                    
                    // Build street number
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
                            'espl': 'esplanade', 'esp': 'esplanade', 'esplanade': 'esplanade',
                            'gr': 'grove', 'grove': 'grove',
                            'cir': 'circuit', 'circuit': 'circuit',
                            'cl': 'close', 'close': 'close'
                        };
                        return abbreviations[type.toLowerCase()] || type.toLowerCase();
                    };

                    // Build property URLs
                    const urlStreetNumber = streetNumber.trim();
                    const urlUnitNumber = addr.flat_number ? addr.flat_number.toString() : '';
                    const urlStreetNameRealEstate = formatForUrl([addr.street_name, expandStreetTypeRealEstate(addr.street_type)].filter(Boolean).join(' '));
                    const urlStreetNameDomain = formatForUrl([addr.street_name, expandStreetTypeDomain(addr.street_type)].filter(Boolean).join(' '));
                    const urlSuburb = formatForUrl(addr.locality_name);
                    const urlState = (addr.state_abbreviation || '').toLowerCase();
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

                    return `
                        <!-- Main row (always visible) -->
                        <tr class="results-row-main" data-row-index="${globalIndex}" data-lat="${addr.latitude || ''}" data-lng="${addr.longitude || ''}" onclick="toggleRowDetails(${globalIndex})">
                            <td><span class="expand-icon">▸</span></td>
                            <td>
                                <strong>${fullAddress}</strong><br>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">${addr.locality_name || 'N/A'}, ${addr.state_abbreviation || 'N/A'} ${addr.postcode || ''}</span>
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
                        <tr class="results-row-details" id="details-${globalIndex}" data-row-index="${globalIndex}">
                            <td colspan="5">
                                <div class="detail-grid">
                                    <div class="detail-item">
                                        <div class="detail-label">COORDINATES</div>
                                        <div class="detail-value">${coords}</div>
                                    </div>
                                    <div class="detail-item">
                                        <div class="detail-label">GEOCODE TYPE</div>
                                        <div class="detail-value">${geocodeType}</div>
                                    </div>
                                    <div class="detail-item school-catchment-detail">
                                        <div class="detail-label">SCHOOL CATCHMENTS</div>
                                        <div class="detail-value"><span style="color: #999;">Loading...</span></div>
                                    </div>
                                    <div class="detail-item" style="grid-column: 1 / -1;">
                                        <div class="detail-label">PROPERTY LINKS</div>
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
                }).join('');
    
    if (!append) {
        // Initial load - create full table structure
        const resultsHtml = `
            <div class="results-header">
                <div class="results-title">Address Results within 5km</div>
                <div class="results-count" id="resultsCount">${allAddresses.length} of ${total} result(s)</div>
            </div>
            
            <!-- Desktop: Compact table with expandable rows -->
            <table class="results-table">
                <thead>
                    <tr>
                        <th style="width: 50px;"></th>
                        <th>ADDRESS</th>
                        <th>DISTANCE</th>
                        <th>CONFIDENCE</th>
                        <th>ACTIONS</th>
                    </tr>
                </thead>
                <tbody id="addressResultsTableBody">
                    ${addressRowsHtml}
                </tbody>
            </table>
            
            ${allAddresses.length < total ? `
                <div style="text-align: center; margin: 20px 0;">
                    <button id="loadMoreBtn" class="btn btn-primary" style="padding: 12px 32px; font-size: 1rem;">
                        Load More (${allAddresses.length} of ${total})
                    </button>
                </div>
            ` : ''}
        `;
        searchResults.innerHTML = resultsHtml;
        
        // Attach load more event listener
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', loadMoreAddresses);
        }
    } else {
        // Append mode - add new rows to existing table
        const tbody = document.getElementById('addressResultsTableBody');
        if (tbody) {
            tbody.insertAdjacentHTML('beforeend', addressRowsHtml);
        }
        
        // Update count
        const resultsCount = document.getElementById('resultsCount');
        if (resultsCount) {
            resultsCount.textContent = `${allAddresses.length} of ${total} result(s)`;
        }
        
        // Update or remove Load More button
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (allAddresses.length >= total) {
            if (loadMoreBtn) {
                loadMoreBtn.parentElement.remove();
            }
        } else if (loadMoreBtn) {
            loadMoreBtn.textContent = `Load More (${allAddresses.length} of ${total})`;
        }
    }
}

// Load more addresses with pagination
async function loadMoreAddresses() {
    if (!currentAcaraId) {
        console.log('No currentAcaraId, returning early');
        return;
    }

    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (loadMoreBtn) {
        loadMoreBtn.disabled = true;
        loadMoreBtn.textContent = 'Loading...';
    }

    try {
        const params = new URLSearchParams();
        params.append('limit', PAGE_SIZE.toString());
        params.append('offset', currentOffset.toString());

        // Add search filters if present
        const searchStreetNumber = document.getElementById('searchStreetNumber');
        const searchStreet = document.getElementById('searchStreet');
        const searchSuburb = document.getElementById('searchSuburb');
        const searchPostcode = document.getElementById('searchPostcode');
        const searchState = document.getElementById('searchState');

        if (searchStreetNumber && searchStreetNumber.value) params.append('street_number', searchStreetNumber.value);
        if (searchStreet && searchStreet.value) params.append('street', searchStreet.value);
        if (searchSuburb && searchSuburb.value) params.append('suburb', searchSuburb.value);
        if (searchPostcode && searchPostcode.value) params.append('postcode', searchPostcode.value);
        if (searchState && searchState.value) params.append('state', searchState.value);

        const url = `/api/australia-school/${currentAcaraId}/addresses?${params.toString()}`;
        console.log('Loading more addresses from:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            if (loadMoreBtn) {
                loadMoreBtn.disabled = false;
                loadMoreBtn.textContent = `Load More (${allAddresses.length} of ${totalAddresses})`;
            }
            return;
        }

        // Append new addresses to existing array
        allAddresses = allAddresses.concat(data.addresses);
        currentOffset += PAGE_SIZE;
        
        // Display with append mode
        displayAddresses(data.addresses, totalAddresses, true);

        if (loadMoreBtn) {
            loadMoreBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error loading more addresses:', error);
        alert('Error loading more addresses');
        if (loadMoreBtn) {
            loadMoreBtn.disabled = false;
            loadMoreBtn.textContent = `Load More (${allAddresses.length} of ${totalAddresses})`;
        }
    }
}

// Toggle row details expansion
function toggleRowDetails(index) {
    const detailsRow = document.getElementById(`details-${index}`);
    const mainRow = document.querySelector(`[data-row-index="${index}"].results-row-main`);
    const expandIcon = mainRow.querySelector('.expand-icon');
    
    if (detailsRow.classList.contains('show')) {
        detailsRow.classList.remove('show');
        mainRow.classList.remove('expanded');
        expandIcon.textContent = '▸';
    } else {
        detailsRow.classList.add('show');
        mainRow.classList.add('expanded');
        expandIcon.textContent = '▾';
        
        // Load school catchments if not already loaded
        const lat = mainRow.dataset.lat;
        const lng = mainRow.dataset.lng;
        
        if (lat && lng) {
            loadSchoolCatchments(index, lat, lng);
        }
    }
}

// Load school catchments for an address
async function loadSchoolCatchments(index, lat, lng) {
    const detailsRow = document.getElementById(`details-${index}`);
    const catchmentDetail = detailsRow.querySelector('.school-catchment-detail .detail-value');
    
    // Check if already loaded
    if (catchmentDetail.dataset.loaded === 'true') {
        return;
    }
    
    try {
        const response = await fetch(`/api/address/schools?lat=${lat}&lng=${lng}`);
        const data = await response.json();
        
        if (data.schools && data.schools.length > 0) {
            catchmentDetail.innerHTML = data.schools.map(school => {
                const schoolLink = `/school-search?school_id=${school.school_id}`;
                return `<a href="${schoolLink}" style="color: #2563eb; text-decoration: none; display: block; margin-bottom: 4px;">${school.school_name} <span style="color: #666; font-size: 0.85rem;">(${school.school_type})</span></a>`;
            }).join('');
        } else {
            catchmentDetail.innerHTML = '<span style="color: #999;">No school catchments</span>';
        }
        
        catchmentDetail.dataset.loaded = 'true';
    } catch (error) {
        console.error('Error loading school catchments:', error);
        catchmentDetail.innerHTML = '<span style="color: #dc3545;">Error loading catchments</span>';
    }
}

// Address search button click handler
if (searchAddressBtn) {
    searchAddressBtn.addEventListener('click', () => {
        loadAddresses(false);
    });
}

// Make toggleRowDetails available globally
window.toggleRowDetails = toggleRowDetails;
