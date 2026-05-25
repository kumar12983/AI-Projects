// ============================================
// Results & Display Functions — school-results.js
// Depends on: DOM refs and global state from school.js
// ============================================

function showLoading(show) {
    loadingIndicator.style.display = show ? 'flex' : 'none';
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
    document.getElementById('schoolTypeBadge').textContent = info.school_type || 'SCHOOL';
    if (info.school_type) {
        document.getElementById('schoolTypeBadge').className = `badge badge-${info.school_type.toLowerCase()}`;
    }
    
    // Display state badge for VIC schools
    const stateBadge = document.getElementById('stateBadge');
    if (stateBadge && info.state && info.state === 'VIC') {
        stateBadge.textContent = 'VIC';
        stateBadge.style.display = 'inline-block';
    } else if (stateBadge) {
        stateBadge.style.display = 'none';
    }
    
    // Display VIC-specific campus name
    const campusContainer = document.getElementById('campus-container');
    const campusName = document.getElementById('campusName');
    if (campusContainer && campusName && info.campus_name && info.campus_name.trim()) {
        campusName.textContent = info.campus_name;
        campusContainer.style.display = 'flex';
    } else if (campusContainer) {
        campusContainer.style.display = 'none';
    }
    
    // Display VIC-specific year level code (pre-formatted from backend)
    const yearLevelContainer = document.getElementById('year-level-container');
    const yearLevelCode = document.getElementById('yearLevelCode');
    if (yearLevelContainer && yearLevelCode && info.year_level_code && info.year_level_code.trim()) {
        yearLevelCode.textContent = info.year_level_code;
        yearLevelContainer.style.display = 'flex';
    } else if (yearLevelContainer) {
        yearLevelContainer.style.display = 'none';
    }
    
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

function displaySearchResults(data) {
    // Use the same format as address lookup page
    searchResults.innerHTML = `
        <div class="results-header">
            <div class="results-title">Search Results in this School Catchment</div>
            <div class="results-count">${data.count} result(s)</div>
        </div>
        
        <!-- Desktop: Compact table with expandable rows -->
        <div style="width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch;">
        <table class="results-table" style="min-width: 600px;">
            <thead>
                <tr>
                    <th style="width: 50px;"></th>
                    <th>Address</th>
                    <th>Distance</th>
                    <th>Last Sold</th>
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
                                ${addr.last_sold_price
                                    ? `<strong style="color: #166534; font-size: 0.9rem;">${addr.last_sold_price}</strong><br><span style="font-size: 0.75rem; color: #6b7280;">${addr.last_sale_date || ''}</span>`
                                    : '<span style="color: #9ca3af;">—</span>'}
                            </td>
                            <td style="white-space: nowrap;">
                                ${googleMapsUrl ? `<a href="${googleMapsUrl}" target="_blank" class="coords-button" title="View on Google Maps" onclick="event.stopPropagation()">📍 Map</a>` : ''}
                            </td>
                        </tr>
                        <!-- Details row (expandable) -->
                        <tr class="results-row-details" id="details-${index}" data-row-index="${index}">
                            <td colspan="5" style="max-width: 0; width: 100%;">
                                <div class="detail-grid" style="max-width: 100%; overflow: hidden; box-sizing: border-box;">
                                    <div class="detail-item">
                                        <div class="detail-label">Coordinates</div>
                                        <div class="detail-value" style="word-break: break-all; font-size: 0.85rem;">${coords}</div>
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
                                    <div class="detail-item">
                                        <div class="detail-label">Confidence</div>
                                        <div class="detail-value">
                                            <span style="color: ${confidenceColor}; font-weight: 500;">${confidenceText}</span>
                                        </div>
                                    </div>
                                    <div class="detail-item" style="grid-column: 1 / -1;">
                                        <div class="detail-label">Property Links</div>
                                        <div class="detail-value" style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px;">
                                            ${realEstateUrl ? `<a href="${realEstateUrl}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #c41230; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500;">🏠 RealEstate.com.au</a>` : ''}
                                            ${domainUrl ? `<a href="${domainUrl}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #16a34a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500;">🏡 Domain.com.au</a>` : ''}
                                            ${!realEstateUrl && !domainUrl ? '<span style="color: #999;">No property links available</span>' : ''}
                                        </div>
                                    </div>
                                    <div class="detail-item" style="grid-column: 1 / -1;">
                                        <div class="detail-label">Property Hazards</div>
                                        <div class="detail-value">
                                            <button type="button" class="coords-button" style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: none; cursor: pointer; padding: 6px 14px; border-radius: 4px; font-size: 0.85rem; font-weight: 500; margin-bottom: 8px;" onclick="fetchSchoolHazards(${index}, ${addr.latitude || 'null'}, ${addr.longitude || 'null'}, event)" title="View Hazard Info">⚠️ View Hazard</button>
                                            <div id="school-hazard-${index}"></div>
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `;
    }).join('')}
            </tbody>
        </table>
        </div>
        
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
                                    <div class="card-info-label">Last Sold</div>
                                    <div class="card-info-value">
                                        ${addr.last_sold_price
                                            ? `<strong style="color: #166534;">${addr.last_sold_price}</strong>
                                               <span style="font-size: 0.75rem; color: #6b7280; display: block;">${addr.last_sale_date || ''}</span>`
                                            : '<span style="color: #9ca3af;">—</span>'}
                                    </div>
                                </div>
                                <div class="card-info-item">
                                    <div class="card-info-label">Coordinates</div>
                                    <div class="card-info-value" style="font-size: 0.85rem;">${coords}</div>
                                </div>
                                <div class="card-info-item">
                                    <div class="card-info-label">Geocode Type</div>
                                    <div class="card-info-value">${geocodeType}</div>
                                </div>
                                <div class="card-info-item">
                                    <div class="card-info-label">Confidence</div>
                                    <div class="card-info-value" style="color: ${confidenceColor}; font-weight: 500;">${confidenceText}</div>
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
                            <div style="margin-top: 8px;">
                                <div style="font-size: 0.7rem; font-weight: 600; text-transform: uppercase; color: #6b7280; margin-bottom: 4px;">Property Hazards</div>
                                <button type="button" class="card-action-btn" style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: none; cursor: pointer; padding: 6px 14px; border-radius: 4px; font-size: 0.82rem; font-weight: 500;" onclick="fetchSchoolHazards(${index}, ${addr.latitude || 'null'}, ${addr.longitude || 'null'}, event)">⚠️ View Hazard</button>
                                <div id="school-hazard-card-${index}" style="margin-top: 6px;"></div>
                            </div>
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

        if (response.status === 401) {
            schoolCell.innerHTML = `<a href="/login" style="display: inline-block; padding: 4px 10px; background: #1e3a8a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.8rem; font-weight: 500; white-space: nowrap;">Login to see catchment</a>`;
        } else if (data.schools && data.schools.length > 0) {
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
