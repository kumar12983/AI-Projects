/**
 * aus-school-autocomplete.js
 * School name autocomplete and address field autocomplete event listeners.
 * Requires australia_school.js (orchestrator) to be loaded first.
 */

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

// Close school suggestions when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.autocomplete-wrapper')) {
        schoolSuggestions.style.display = 'none';
    }
});

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

// ============================================
// Full-Address Single-Field Autocomplete (School Address Search)
// ============================================
const schoolFullAddressInput       = document.getElementById('school-full-address-input');
const schoolFullAddressSuggestions = document.getElementById('school-full-address-suggestions');

if (schoolFullAddressInput && schoolFullAddressSuggestions) {
    let schoolFullAddressDebounce;

    schoolFullAddressInput.addEventListener('input', (e) => {
        clearTimeout(schoolFullAddressDebounce);
        const query = e.target.value.trim();

        if (query.length < 4) {
            schoolFullAddressSuggestions.innerHTML = '';
            schoolFullAddressSuggestions.style.display = 'none';
            return;
        }

        schoolFullAddressDebounce = setTimeout(async () => {
            try {
                const url = `/api/autocomplete/full-address?q=${encodeURIComponent(query)}`;
                const response = await fetch(url);
                const addresses = await response.json();

                if (addresses.length > 0) {
                    schoolFullAddressSuggestions.innerHTML = addresses.map(addr =>
                        `<div class="suggestion-item"
                             data-number="${addr.number_first || ''}"
                             data-suffix="${addr.number_first_suffix || ''}"
                             data-street="${addr.street_name || ''}"
                             data-suburb="${addr.suburb || ''}"
                             data-state="${addr.state || ''}"
                             data-postcode="${addr.postcode || ''}">
                            ${addr.full_address}
                        </div>`
                    ).join('');
                    schoolFullAddressSuggestions.style.display = 'block';

                    schoolFullAddressSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            schoolFullAddressInput.value = item.textContent.trim();
                            schoolFullAddressSuggestions.style.display = 'none';

                            // Back-fill individual fields
                            if (searchStreetNumber) searchStreetNumber.value = item.dataset.number + (item.dataset.suffix || '');
                            if (searchStreet)       searchStreet.value       = item.dataset.street;
                            if (searchSuburb)       searchSuburb.value       = item.dataset.suburb;
                            if (searchPostcode)     searchPostcode.value     = item.dataset.postcode;
                            if (searchState)        searchState.value        = item.dataset.state;

                            // Auto-trigger address search
                            if (searchAddressBtn) searchAddressBtn.click();
                        });
                    });
                } else {
                    schoolFullAddressSuggestions.innerHTML = '<div class="suggestion-item" style="color:#999;">No addresses found</div>';
                    schoolFullAddressSuggestions.style.display = 'block';
                }
            } catch (error) {
                console.error('Error fetching full-address suggestions:', error);
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
        if (schoolFullAddressSuggestions) schoolFullAddressSuggestions.style.display = 'none';
    }
});
