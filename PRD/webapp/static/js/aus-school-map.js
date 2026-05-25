/**
 * aus-school-map.js
 * Map display for the Australia school 5km buffer zone.
 * Requires australia_school.js (orchestrator) to be loaded first.
 */

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
