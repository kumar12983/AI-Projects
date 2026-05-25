// ============================================
// Autocomplete & Event Listeners — school-autocomplete.js
// Depends on: DOM refs and global state from school.js (loaded first)
// ============================================

// State filter change handler - clear school input for better UX
if (stateFilter) {
    stateFilter.addEventListener('change', function() {
        schoolInput.value = '';
        currentSchoolId = null;
        schoolSuggestions.style.display = 'none';
        hideAllSections();
        console.log('State changed to:', this.value, '- school input cleared');
    });
}

// ============================================
// Address Search Autocomplete (School-Specific)
// ============================================

// Autocomplete for Street Name in address filter (filtered by school catchment)
let streetSearchDebounce;
if (searchStreet && searchStreetSuggestions) {
    searchStreet.addEventListener('input', (e) => {
        clearTimeout(streetSearchDebounce);
        const query = e.target.value.trim();
        
        console.log('Street input event - query:', query, 'currentSchoolId:', currentSchoolId);

        if (query.length < 2) {
            searchStreetSuggestions.innerHTML = '';
            searchStreetSuggestions.style.display = 'none';
            return;
        }

        // Require a school to be selected first
        if (!currentSchoolId) {
            searchStreetSuggestions.innerHTML = '<div class="suggestion-item no-results">Please select a school first</div>';
            searchStreetSuggestions.style.display = 'block';
            return;
        }

        streetSearchDebounce = setTimeout(async () => {
            try {
                console.log('Fetching streets for school:', currentSchoolId);
                const response = await fetch(`/api/school/${currentSchoolId}/autocomplete/streets?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                
                console.log('Street autocomplete response:', data);

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
                    searchStreetSuggestions.innerHTML = '<div class="suggestion-item no-results">No streets found in this catchment</div>';
                    searchStreetSuggestions.style.display = 'block';
                }
            } catch (error) {
                console.error('Error fetching street suggestions:', error);
            }
        }, 300);
    });
}

// Autocomplete for Suburb in address filter (filtered by school catchment)
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

        // Require a school to be selected first
        if (!currentSchoolId) {
            searchSuburbSuggestions.innerHTML = '<div class="suggestion-item no-results">Please select a school first</div>';
            searchSuburbSuggestions.style.display = 'block';
            return;
        }

        suburbSearchDebounce = setTimeout(async () => {
            try {
                const response = await fetch(`/api/school/${currentSchoolId}/autocomplete/suburbs?q=${encodeURIComponent(query)}`);
                const data = await response.json();

                if (data.length > 0) {
                    searchSuburbSuggestions.innerHTML = data.map(item =>
                        `<div class="suggestion-item" data-value="${item.suburb}">
                            ${item.suburb} <span class="suggestion-meta">${item.postcode}</span>
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
                    searchSuburbSuggestions.innerHTML = '<div class="suggestion-item no-results">No suburbs found in this catchment</div>';
                    searchSuburbSuggestions.style.display = 'block';
                }
            } catch (error) {
                console.error('Error fetching suburb suggestions:', error);
            }
        }, 300);
    });
}

// Autocomplete for Postcode in address filter (filtered by school catchment)
let postcodeSearchDebounce;
if (searchPostcode && searchPostcodeSuggestions) {
    searchPostcode.addEventListener('input', (e) => {
        clearTimeout(postcodeSearchDebounce);
        const query = e.target.value.trim();

        if (query.length < 1) {
            searchPostcodeSuggestions.innerHTML = '';
            searchPostcodeSuggestions.style.display = 'none';
            return;
        }

        // Require a school to be selected first
        if (!currentSchoolId) {
            searchPostcodeSuggestions.innerHTML = '<div class="suggestion-item no-results">Please select a school first</div>';
            searchPostcodeSuggestions.style.display = 'block';
            return;
        }

        postcodeSearchDebounce = setTimeout(async () => {
            try {
                const response = await fetch(`/api/school/${currentSchoolId}/autocomplete/postcodes?q=${encodeURIComponent(query)}`);
                const data = await response.json();

                if (data.length > 0) {
                    searchPostcodeSuggestions.innerHTML = data.map(item =>
                        `<div class="suggestion-item" data-value="${item.postcode}">
                            ${item.postcode} <span class="suggestion-meta">${item.suburb}</span>
                        </div>`
                    ).join('');
                    searchPostcodeSuggestions.style.display = 'block';

                    // Add click handlers
                    searchPostcodeSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            searchPostcode.value = item.dataset.value;
                            searchPostcodeSuggestions.style.display = 'none';
                        });
                    });
                } else {
                    searchPostcodeSuggestions.innerHTML = '<div class="suggestion-item no-results">No postcodes found in this catchment</div>';
                    searchPostcodeSuggestions.style.display = 'block';
                }
            } catch (error) {
                console.error('Error fetching postcode suggestions:', error);
            }
        }, 300);
    });
}

// Hide suggestions when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.autocomplete-wrapper')) {
        if (searchStreetSuggestions) searchStreetSuggestions.style.display = 'none';
        if (searchSuburbSuggestions) searchSuburbSuggestions.style.display = 'none';
        if (searchPostcodeSuggestions) searchPostcodeSuggestions.style.display = 'none';
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
        const state = stateFilter ? stateFilter.value : 'NSW';
        fetchSchoolSuggestions(query, state);
    }, 300);
});

async function fetchSchoolSuggestions(query, state = 'NSW') {
    try {
        const url = `/api/autocomplete/schools?q=${encodeURIComponent(query)}&state=${state}`;
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
        <div class="autocomplete-item" data-school-id="${school.school_id}" data-school-name="${school.school_name}" data-state="${school.state || 'NSW'}">
            <div class="school-suggestion">
                <span class="school-name">${school.school_name}</span>
                <span class="school-meta">
                    <span class="badge badge-${school.school_type.toLowerCase()}">${school.school_type}</span>
                    ${school.state ? `<span class="badge" style="background: #10b981; margin-left: 4px;">${school.state}</span>` : ''}
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
            
            console.log('School selected - ID:', currentSchoolId, 'Name:', schoolName);

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
