/**
 * Australia School Search JavaScript
 * Handles Australian school autocomplete with state filter and 5km zone visualization
 */

// Global state
let map = null;
let selectedSchool = null;

// DOM Elements
const schoolInput = document.getElementById('schoolInput');
const schoolSuggestions = document.getElementById('schoolSuggestions');
const stateFilter = document.getElementById('stateFilter');
const australiaSchoolSearchForm = document.getElementById('australiaSchoolSearchForm');
const schoolInfoSection = document.getElementById('schoolInfoSection');
const mapSection = document.getElementById('mapSection');
const loadingIndicator = document.getElementById('loadingIndicator');

// ============================================
// School Autocomplete with State Filter
// ============================================

schoolInput.addEventListener('input', async (e) => {
    const query = e.target.value.trim();

    if (query.length < 3) {
        schoolSuggestions.innerHTML = '';
        schoolSuggestions.style.display = 'none';
        return;
    }

    try {
        const state = stateFilter.value;
        const url = `/api/autocomplete/australia-schools?q=${encodeURIComponent(query)}${state ? '&state=' + state : ''}`;
        const response = await fetch(url);
        const schools = await response.json();

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

    showLoading();

    try {
        const response = await fetch(`/api/australia-school/${selectedSchool}/info`);
        const data = await response.json();

        if (data.error) {
            alert(data.error);
            hideLoading();
            return;
        }

        displaySchoolInfo(data);
        displayMap(data);

        hideLoading();
    } catch (error) {
        console.error('Error loading school data:', error);
        alert('Error loading school information');
        hideLoading();
    }
});

// ============================================
// Display Functions
// ============================================

function displaySchoolInfo(data) {
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

    schoolInfoSection.style.display = 'block';
}

function displayMap(data) {
    mapSection.style.display = 'block';

    // Initialize map if not already done
    if (!map) {
        map = L.map('schoolMap');
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);
    }

    // Clear existing layers
    map.eachLayer(layer => {
        if (layer instanceof L.GeoJSON || layer instanceof L.Marker) {
            map.removeLayer(layer);
        }
    });

    // Add school marker
    if (data.latitude && data.longitude) {
        const schoolMarker = L.marker([data.latitude, data.longitude]).addTo(map);
        schoolMarker.bindPopup(`<strong>${data.school_name}</strong><br>${data.school_sector}`);
    }

    // Add 5km buffer if available
    if (data.geom_5km_buffer) {
        const bufferLayer = L.geoJSON(data.geom_5km_buffer, {
            style: {
                color: '#3b82f6',
                weight: 2,
                opacity: 0.8,
                fillColor: '#3b82f6',
                fillOpacity: 0.1
            }
        }).addTo(map);

        map.fitBounds(bufferLayer.getBounds(), { padding: [20, 20] });
    } else if (data.latitude && data.longitude) {
        map.setView([data.latitude, data.longitude], 13);
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
