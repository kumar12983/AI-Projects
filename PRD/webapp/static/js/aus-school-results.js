/**
 * aus-school-results.js
 * Address loading, display, pagination, and row expansion for Australia school search.
 * Requires australia_school.js (orchestrator) to be loaded first.
 */

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
            // Display error message near the map instead of alert popup
            const mapErrorMessage = document.getElementById('mapErrorMessage');
            const mapErrorText = document.getElementById('mapErrorText');
            if (mapErrorMessage && mapErrorText) {
                mapErrorText.textContent = data.error;
                mapErrorMessage.style.display = 'block';
                // Scroll to the error message
                mapErrorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            hideLoading();
            return;
        }
        
        // Hide error message if addresses loaded successfully
        const mapErrorMessage = document.getElementById('mapErrorMessage');
        if (mapErrorMessage) {
            mapErrorMessage.style.display = 'none';
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
        // Display error message near the map instead of alert popup
        const mapErrorMessage = document.getElementById('mapErrorMessage');
        const mapErrorText = document.getElementById('mapErrorText');
        if (mapErrorMessage && mapErrorText) {
            mapErrorText.textContent = 'Error loading addresses. Please try again.';
            mapErrorMessage.style.display = 'block';
            mapErrorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
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
                        <tr class="results-row-main" data-row-index="${globalIndex}" data-lat="${addr.latitude || ''}" data-lng="${addr.longitude || ''}" data-state="${addr.state_abbreviation || 'NSW'}" onclick="toggleRowDetails(${globalIndex})">
                            <td><span class="expand-icon">▸</span></td>
                            <td>
                                <strong>${fullAddress}</strong><br>
                                <span style="color: var(--text-muted); font-size: 0.85rem;">${addr.locality_name || 'N/A'}, ${addr.state_abbreviation || 'N/A'} ${addr.postcode || ''}</span>
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
                                    <div class="detail-item">
                                        <div class="detail-label">CONFIDENCE</div>
                                        <div class="detail-value">
                                            <span style="color: ${confidenceColor}; font-weight: 500;">${confidenceText}</span>
                                        </div>
                                    </div>
                                    <div class="detail-item" style="grid-column: 1 / -1;">
                                        <div class="detail-label">PROPERTY HAZARDS</div>
                                        <div class="detail-value">
                                            <button type="button" class="coords-button" style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: none; cursor: pointer; padding: 6px 14px; border-radius: 4px; font-size: 0.85rem; font-weight: 500; margin-bottom: 8px;" onclick="fetchHazards(${globalIndex}, ${addr.latitude || 'null'}, ${addr.longitude || 'null'}, event)" title="View Hazard Info">⚠️ View Hazard</button>
                                            <div id="hazard-${globalIndex}"></div>
                                        </div>
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
                        <th>LAST SOLD</th>
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

// Make toggleRowDetails available globally (called from inline onclick= in generated HTML)
window.toggleRowDetails = toggleRowDetails;
