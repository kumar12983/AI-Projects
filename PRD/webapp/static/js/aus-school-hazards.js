/**
 * aus-school-hazards.js
 * Fetches and displays property hazard data (bushfire, flood, landslide, cyclone).
 * Requires australia_school.js (orchestrator) and aus-school-catchments.js to be loaded first.
 */

async function fetchHazards(index, lat, lng, event) {
    // CRITICAL: stop the click from bubbling up to the <tr>'s onclick (toggleRowDetails)
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    if (!lat || !lng) {
        alert("Coordinates not available for this address.");
        return;
    }

    // Force the details row OPEN without toggling — fixes the collapse problem.
    // toggleRowDetails flips state, but we always want the row open here.
    function forceExpand(idx) {
        const detailsRow = document.getElementById(`details-${idx}`);
        const mainRow = document.querySelector(`tr.results-row-main[data-row-index="${idx}"]`);
        if (!detailsRow || !mainRow) return;

        if (!detailsRow.classList.contains('show')) {
            detailsRow.classList.add('show');
            mainRow.classList.add('expanded');
            const icon = mainRow.querySelector('.expand-icon');
            if (icon) icon.textContent = '▾';

            // Also trigger school catchments load (same as toggleRowDetails does)
            const rowLat = mainRow.dataset.lat;
            const rowLng = mainRow.dataset.lng;
            if (rowLat && rowLng) loadSchoolCatchments(idx, rowLat, rowLng);
        }
    }

    forceExpand(index);

    const hazardValueDiv = document.getElementById(`hazard-${index}`);
    if (!hazardValueDiv) return;

    // Skip re-fetch if already loaded — just scroll into view
    if (hazardValueDiv.dataset.loaded === 'true') {
        hazardValueDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        return;
    }

    hazardValueDiv.innerHTML = '<span style="color: #6b7280; font-size: 0.85rem;">Loading hazards... ⏳</span>';

    try {
        const response = await fetch(`/api/hazards?lat=${lat}&lng=${lng}`);
        const data = await response.json();
        if (response.status === 401) {
            hazardValueDiv.innerHTML = `<a href="/login" style="display: inline-block; padding: 4px 10px; background: #1e3a8a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.8rem; font-weight: 500;">Login to view hazards</a>`;
            return;
        }
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch hazards');
        }

        const hazards = data.hazards || {};

        let html = '<div style="display: flex; flex-direction: column; gap: 8px; margin-top: 4px;">';

        ['Bushfire', 'Flood', 'Landslide'].forEach(type => {
            const h = hazards[type] || {};
            const isDetected = h.detected;
            const icon = isDetected ? '⚠️' : '✅';
            const color = isDetected ? '#dc2626' : '#16a34a';
            html += `
                <div style="padding: 8px 12px; background: #f9fafb; border-radius: 6px; border-left: 3px solid ${color};">
                    <div style="font-weight: 600; font-size: 0.85rem; color: #374151;">${icon} ${type.toUpperCase()}: ${h.label || 'N/A'}</div>
                    <div style="font-size: 0.8rem; color: #6b7280; margin-top: 2px;">${h.detail || 'No data'}</div>
                </div>`;
        });

        const cyc = hazards.Cyclone || {};
        const cycColor = cyc.cyclone_direct_risk ? '#dc2626' : (cyc.elevated_wind_risk ? '#f59e0b' : '#3b82f6');
        html += `
            <div style="padding: 8px 12px; background: #f9fafb; border-radius: 6px; border-left: 3px solid ${cycColor};">
                <div style="font-weight: 600; font-size: 0.85rem; color: #374151;">🌀 CYCLONE / WIND REGION: ${cyc.wind_region || 'N/A'}</div>
                <div style="font-size: 0.8rem; color: #6b7280; margin-top: 2px;">
                    Direct Risk: <strong style="color: ${cyc.cyclone_direct_risk ? '#dc2626' : '#374151'}">${cyc.cyclone_direct_risk ? 'YES' : 'No'}</strong> &nbsp;|&nbsp;
                    Elevated Wind: <strong style="color: ${cyc.elevated_wind_risk ? '#f59e0b' : '#374151'}">${cyc.elevated_wind_risk ? 'YES' : 'No'}</strong><br>
                    <span style="color: #9ca3af;">${cyc.description || ''}</span>
                </div>
            </div>`;

        if (data.errors && data.errors.length > 0) {
            html += `<div style="font-size: 0.75rem; color: #d97706; margin-top: 2px;">⚠️ ${data.errors.join('<br>')}</div>`;
        }

        html += '</div>';
        hazardValueDiv.innerHTML = html;
        hazardValueDiv.dataset.loaded = 'true';

        // Ensure the row is still open after the async gap (in case user clicked it during load)
        forceExpand(index);

    } catch (err) {
        console.error(err);
        hazardValueDiv.innerHTML = `<span style="color: #dc2626; font-size: 0.85rem;">⚠️ Error: ${err.message}</span>`;
        forceExpand(index);
    }
}

// Make available globally (called from inline onclick= in dynamically generated HTML rows)
window.fetchHazards = fetchHazards;
