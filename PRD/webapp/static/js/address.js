// ============================================
// Address Lookup Page JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const streetNumberInput = document.getElementById('street-number-input');
    const streetInput = document.getElementById('street-input');
    const suburbInput = document.getElementById('suburb-input-addr');
    const postcodeInput = document.getElementById('postcode-input-addr');
    const stateInput = document.getElementById('state-input');
    const limitInput = document.getElementById('limit-input');
    const searchBtn = document.getElementById('address-search-btn');
    const resultsDiv = document.getElementById('address-results');

    // Check for URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const suburbParam = urlParams.get('suburb');
    const postcodeParam = urlParams.get('postcode');
    const autoSearch = urlParams.get('auto');

    const streetSuggestions = document.getElementById('street-suggestions');
    const suburbSuggestions = document.getElementById('suburb-suggestions');

    // Auto-populate and search if URL parameters exist
    if (suburbParam || postcodeParam) {
        if (suburbParam) suburbInput.value = suburbParam;
        if (postcodeParam) postcodeInput.value = postcodeParam;

        // Auto-execute search if auto=true
        if (autoSearch === 'true') {
            setTimeout(() => {
                searchBtn.click();
            }, 100);
        }
    }

    // Autocomplete for Street
    let streetDebounce;
    streetInput.addEventListener('input', (e) => {
        clearTimeout(streetDebounce);
        const query = e.target.value.trim();

        if (query.length < 2) {
            streetSuggestions.innerHTML = '';
            streetSuggestions.style.display = 'none';
            return;
        }

        streetDebounce = setTimeout(async () => {
            try {
                const response = await fetch(`/api/autocomplete/streets?q=${encodeURIComponent(query)}`);
                const data = await response.json();

                if (data.length > 0) {
                    streetSuggestions.innerHTML = data.map(item => {
                        const streetFull = item.street_type ? `${item.street_name} ${item.street_type}` : item.street_name;
                        return `<div class="suggestion-item" data-value="${item.street_name}">${streetFull}</div>`;
                    }).join('');
                    streetSuggestions.style.display = 'block';

                    // Add click handlers
                    streetSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            streetInput.value = item.dataset.value;
                            streetSuggestions.style.display = 'none';
                        });
                    });
                } else {
                    streetSuggestions.style.display = 'none';
                }
            } catch (error) {
                console.error('Error fetching street suggestions:', error);
            }
        }, 300);
    });

    // Autocomplete for Suburb
    let suburbDebounce;
    suburbInput.addEventListener('input', (e) => {
        clearTimeout(suburbDebounce);
        const query = e.target.value.trim();

        if (query.length < 2) {
            suburbSuggestions.innerHTML = '';
            suburbSuggestions.style.display = 'none';
            return;
        }

        suburbDebounce = setTimeout(async () => {
            try {
                const response = await fetch(`/api/autocomplete/suburbs?q=${encodeURIComponent(query)}`);
                const data = await response.json();

                if (data.length > 0) {
                    suburbSuggestions.innerHTML = data.map(item =>
                        `<div class="suggestion-item" data-value="${item.suburb}">
                                    ${item.suburb} <span class="suggestion-meta">${item.state} ${item.postcode}</span>
                                </div>`
                    ).join('');
                    suburbSuggestions.style.display = 'block';

                    // Add click handlers
                    suburbSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            suburbInput.value = item.dataset.value;
                            suburbSuggestions.style.display = 'none';
                        });
                    });
                } else {
                    suburbSuggestions.style.display = 'none';
                }
            } catch (error) {
                console.error('Error fetching suburb suggestions:', error);
            }
        }, 300);
    });

    // Hide suggestions when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.autocomplete-wrapper')) {
            streetSuggestions.style.display = 'none';
            suburbSuggestions.style.display = 'none';
        }
    });

    async function searchAddress() {
        const streetNumber = streetNumberInput.value.trim();
        const street = streetInput.value.trim();
        const suburb = suburbInput.value.trim();
        const postcode = postcodeInput.value.trim();
        const state = stateInput.value.trim();
        const limit = limitInput.value;

        if (!street && !suburb && !postcode && !state) {
            resultsDiv.innerHTML = '<div class="error">Please enter at least one search criteria</div>';
            return;
        }

        showLoading('address-results');

        try {
            const params = new URLSearchParams();
            if (streetNumber) params.append('street_number', streetNumber);
            if (street) params.append('street', street);
            if (suburb) params.append('suburb', suburb);
            if (postcode) params.append('postcode', postcode);
            if (state) params.append('state', state);
            params.append('limit', limit);

            const response = await fetch(`/api/address/search?${params}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch data');
            }

            if (data.addresses.length === 0) {
                resultsDiv.innerHTML = `
                    <div class="no-results">
                        No addresses found matching your search criteria
                    </div>
                `;
                return;
            }

            resultsDiv.innerHTML = `
                <div class="results-header">
                    <div class="results-title">Address Search Results</div>
                    <div class="results-count">${data.count} result(s)</div>
                </div>
                <div class="results-table-wrapper">
                    <table class="results-table">
                        <thead>
                            <tr>
                                <th>Unit/Flat</th>
                                <th>Street Number</th>
                                <th>Street Name</th>
                                <th>Suburb</th>
                                <th>State</th>
                                <th>Postcode</th>
                                <th>GNAF ID</th>
                                <th>Coordinates</th>
                                <th>School Catchments</th>
                                <th>Useful Links</th>
                                <th>Confidence</th>
                            </tr>
                        </thead>
                        <tbody id="addressResultsTableBody">
                            ${data.addresses.map((addr, index) => {
                const streetName = [addr.street_name, addr.street_type].filter(Boolean).join(' ').trim();
                const streetNumber = addr.number_last
                    ? `${addr.number_first}${addr.number_first_suffix || ''}-${addr.number_last}${addr.number_last_suffix || ''}`
                    : `${addr.number_first || 'N/A'}${addr.number_first_suffix || ''}`;

                const unit = addr.flat_number
                    ? (addr.flat_type ? `${addr.flat_type} ${addr.flat_number}` : addr.flat_number)
                    : '-';

                const coords = addr.latitude && addr.longitude
                    ? `${parseFloat(addr.latitude).toFixed(6)}, ${parseFloat(addr.longitude).toFixed(6)}`
                    : 'N/A';

                // Calculate distance from state CBD using Haversine formula
                let distanceFromCBD = '';
                if (addr.latitude && addr.longitude) {
                    // Define CBD coordinates for each state (using abbreviations)
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

                        distanceFromCBD = `Distance from ${stateCBD.city} CBD: ${distance.toFixed(2)} km&#10;(Haversine formula used to calculate as-the-crow-flies distance, driving distance can be calculated from Google Maps)`;
                    }
                }

                // Google Maps link with pin dropped at coordinates
                const googleMapsUrl = addr.latitude && addr.longitude
                    ? `https://www.google.com/maps?q=${parseFloat(addr.latitude).toFixed(6)},${parseFloat(addr.longitude).toFixed(6)}`
                    : '';

                const geocodeType = addr.geocode_type_code || 'N/A';

                // Geocode type tooltip mapping
                const geocodeTypeTooltips = {
                    'PC': 'Property Centroid - Geocoded to the center of the property parcel. Most accurate.',
                    'BC': 'Building Centroid - Geocoded to the center of the building footprint.',
                    'FC': 'Frontage Centre - Geocoded to the center of the street frontage of the property.',
                    'FP': 'Frontage Point - Geocoded to a specific point on the street frontage.',
                    'SC': 'Street Locality Centroid - Geocoded to the center of the street segment.',
                    'SL': 'Street Locality - Geocoded to the street.',
                    'LC': 'Locality Centroid - Geocoded to the center of the suburb/locality.',
                    'L': 'Locality - Geocoded to the suburb/locality.',
                    'UC': 'Unit Centroid - Geocoded to the center of the unit/apartment.',
                    'EM': 'Emergency Management - Emergency services geocode.',
                    'PAR': 'Parcel - Geocoded to land parcel.',
                    'STL': 'Street Locality - Street level geocode.',
                    'GAP': 'Gap Geocode - Interpolated between known points.'
                };

                const geocodeTypeTooltip = geocodeTypeTooltips[geocodeType] || 'Geocode type information not available';

                // Convert confidence to user-friendly text
                let confidenceText = 'Unknown';
                let confidenceTooltip = 'Confidence level not available';
                let confidenceColor = '#999';

                if (addr.confidence !== null && addr.confidence !== undefined) {
                    const confValue = parseInt(addr.confidence);
                    if (confValue === 3) {
                        confidenceText = 'Very High';
                        confidenceTooltip = 'Precise location - accurate to property/building level. Suitable for navigation and mapping.';
                        confidenceColor = '#28a745';
                    } else if (confValue === 2) {
                        confidenceText = 'High';
                        confidenceTooltip = 'Accurate location - geocoded to street segment or locality. Good for most purposes.';
                        confidenceColor = '#5cb85c';
                    } else if (confValue === 1) {
                        confidenceText = 'Medium';
                        confidenceTooltip = 'Approximate location - may be off by hundreds of meters. Use with caution.';
                        confidenceColor = '#ffc107';
                    } else if (confValue === 0) {
                        confidenceText = 'Low';
                        confidenceTooltip = 'General area only - coordinates may be inaccurate. Not recommended for navigation.';
                        confidenceColor = '#ff9800';
                    } else if (confValue === -1) {
                        confidenceText = 'None';
                        confidenceTooltip = 'No reliable geocoding available. Do not use coordinates for navigation.';
                        confidenceColor = '#dc3545';
                    }
                }
                const gnafId = addr.address_detail_pid || 'N/A';

                // Construct property URLs
                const formatForUrl = (str) => {
                    if (!str) return '';
                    return str.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
                };

                // Expand street type abbreviations for RealEstate
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
                    const lowerType = type.toLowerCase();
                    return abbreviations[lowerType] || lowerType;
                };

                // Expand street type abbreviations for Domain
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
                    const lowerType = type.toLowerCase();
                    return abbreviations[lowerType] || lowerType;
                };

                // Build street number with range if applicable
                const urlStreetNumber = streetNumber.replace('N/A', '').trim();

                // Get unit number (just the number, not the type)
                const urlUnitNumber = addr.flat_number ? addr.flat_number.toString() : '';

                const urlStreetNameRealEstate = formatForUrl([addr.street_name, expandStreetTypeRealEstate(addr.street_type)].filter(Boolean).join(' '));
                const urlStreetNameDomain = formatForUrl([addr.street_name, expandStreetTypeDomain(addr.street_type)].filter(Boolean).join(' '));
                const urlSuburb = formatForUrl(addr.suburb);
                const urlState = (addr.state || '').toLowerCase();
                const urlPostcode = addr.postcode || '';

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

                return `
                                <tr data-row-index="${index}" data-lat="${addr.latitude || ''}" data-lng="${addr.longitude || ''}">
                                    <td>${unit}</td>
                                    <td><strong>${streetNumber}</strong></td>
                                    <td>${streetName || 'N/A'}</td>
                                    <td>${addr.suburb || 'N/A'}</td>
                                    <td>${addr.state || 'N/A'}</td>
                                    <td>${addr.postcode || 'N/A'}</td>
                                    <td style="font-size: 0.75rem; font-family: monospace; color: var(--text-muted);">${gnafId}</td>
                                    <td style="font-size: 0.85rem;">
                                        ${googleMapsUrl
                        ? `<a href="${googleMapsUrl}" target="_blank" class="coords-button" title="View on Google Maps${distanceFromCBD ? '&#10;' + distanceFromCBD : ''}">📍 ${coords}</a>`
                        : '<span style="color: var(--text-muted);">N/A</span>'}
                                    </td>
                                    <td class="school-catchment-cell" style="font-size: 0.85rem;">
                                        <span style="color: #999;">Loading...</span>
                                    </td>
                                    <td style="font-size: 0.85rem;">
                                        <div style="display: flex; flex-direction: column; gap: 6px;">
                                            ${realEstateUrl ? `<a href="${realEstateUrl}" target="_blank" style="display: block; text-align: center; padding: 4px 8px; background: #c41230; color: white; text-decoration: none; border-radius: 3px; font-size: 0.85rem; font-weight: 500; white-space: nowrap;" title="View on RealEstate.com.au">RealEstate</a>` : ''}
                                            ${domainUrl ? `<a href="${domainUrl}" target="_blank" style="display: block; text-align: center; padding: 4px 8px; background: #16a34a; color: white; text-decoration: none; border-radius: 3px; font-size: 0.85rem; font-weight: 500; white-space: nowrap;" title="View on Domain.com.au">Domain</a>` : ''}
                                            ${!realEstateUrl && !domainUrl ? '<span style="color: #999;">-</span>' : ''}
                                        </div>
                                    </td>
                                    <td style="font-size: 0.85rem;">
                                        <span style="color: ${confidenceColor}; font-weight: 500; cursor: help;" 
                                              title="${confidenceTooltip}">
                                            ${confidenceText}
                                        </span>
                                    </td>
                                </tr>
                            `;
            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            // Fetch school catchments for each address
            fetchSchoolCatchments();

        } catch (error) {
            resultsDiv.innerHTML = handleAPIError(error);
        }
    }

    // Function to fetch school catchments for all addresses
    async function fetchSchoolCatchments() {
        const rows = document.querySelectorAll('#addressResultsTableBody tr');

        for (const row of rows) {
            const lat = row.dataset.lat;
            const lng = row.dataset.lng;
            const schoolCell = row.querySelector('.school-catchment-cell');

            if (!lat || !lng) {
                schoolCell.innerHTML = '<span style="color: #999;">No coordinates</span>';
                continue;
            }

            try {
                const response = await fetch(`/api/address/schools?lat=${lat}&lng=${lng}`);
                const data = await response.json();

                if (response.status === 401 || response.status === 403) {
                    schoolCell.innerHTML = `
                        <a href="/login" style="display: inline-block; padding: 6px 12px; background: #1e3a8a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500; white-space: nowrap;">
                            Login to see catchment
                        </a>
                    `;
                } else if (data.schools && data.schools.length > 0) {
                    const schoolsHtml = data.schools.map(school => {
                        const typeColors = {
                            'PRIMARY': '#2196F3',
                            'SECONDARY': '#4CAF50',
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
                schoolCell.innerHTML = `
                    <a href="/login" style="display: inline-block; padding: 6px 12px; background: #1e3a8a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500; white-space: nowrap;">
                        Login to see catchment
                    </a>
                `;
            }
        }
    }

    searchBtn.addEventListener('click', searchAddress);

    // Allow Enter key on any input field
    [streetNumberInput, streetInput, suburbInput, postcodeInput].forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchAddress();
        });
    });
});