// ============================================
// Property Hazards — school-hazards.js
// ============================================

async function fetchSchoolHazards(index, lat, lng, event) {
    if (event) { event.stopPropagation(); event.preventDefault(); }
    if (!lat || !lng) return;

    // Ensure the details row is open
    const detailsRow = document.getElementById(`details-${index}`);
    const mainRow = document.querySelector(`.results-row-main[data-row-index="${index}"]`);
    if (detailsRow && !detailsRow.classList.contains('show')) {
        detailsRow.classList.add('show');
        if (mainRow) {
            mainRow.classList.add('expanded');
            const icon = mainRow.querySelector('.expand-icon');
            if (icon) icon.textContent = '▾';
        }
    }

    // Target the desktop detail div; also update mobile card div if present
    const hazardDiv = document.getElementById(`school-hazard-${index}`);
    const hazardCardDiv = document.getElementById(`school-hazard-card-${index}`);

    const targets = [hazardDiv, hazardCardDiv].filter(Boolean);
    if (targets.length === 0) return;

    // Skip re-fetch
    if (hazardDiv && hazardDiv.dataset.loaded === 'true') {
        hazardDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        return;
    }

    targets.forEach(t => { t.innerHTML = '<span style="color: #6b7280; font-size: 0.85rem;">Loading hazards... ⏳</span>'; });

    try {
        const response = await fetch(`/api/hazards?lat=${lat}&lng=${lng}`);
        const data = await response.json();
        if (response.status === 401) {
            targets.forEach(t => { t.innerHTML = `<a href="/login" style="display: inline-block; padding: 4px 10px; background: #1e3a8a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.8rem; font-weight: 500;">Login to view hazards</a>`; });
            return;
        }
        if (!response.ok) throw new Error(data.error || 'Failed to fetch hazards');

        const hazards = data.hazards || {};
        let html = '<div style="display: flex; flex-direction: column; gap: 8px; margin-top: 4px;">';

        ['Bushfire', 'Flood', 'Landslide'].forEach(type => {
            const h = hazards[type] || {};
            const icon = h.detected ? '⚠️' : '✅';
            const color = h.detected ? '#dc2626' : '#16a34a';
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

        targets.forEach(t => { t.innerHTML = html; t.dataset.loaded = 'true'; });
    } catch (err) {
        console.error(err);
        targets.forEach(t => { t.innerHTML = `<span style="color: #dc2626; font-size: 0.85rem;">⚠️ Error: ${err.message}</span>`; });
    }
}

window.fetchSchoolHazards = fetchSchoolHazards;
