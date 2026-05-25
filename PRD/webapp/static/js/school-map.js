// ============================================
// Catchment Map — school-map.js
// Depends on: catchmentMap, catchmentLayer (globals from school.js)
// ============================================

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
