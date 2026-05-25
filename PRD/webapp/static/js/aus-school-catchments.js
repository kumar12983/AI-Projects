/**
 * aus-school-catchments.js
 * Loads and displays school catchment zones for a given address coordinate.
 * Requires australia_school.js (orchestrator) to be loaded first.
 */

async function loadSchoolCatchments(index, lat, lng) {
    const detailsRow = document.getElementById(`details-${index}`);
    const catchmentDetail = detailsRow.querySelector('.school-catchment-detail .detail-value');
    
    // Check if already loaded
    if (catchmentDetail.dataset.loaded === 'true') {
        return;
    }
    
    const mainRow = document.querySelector(`tr.results-row-main[data-row-index="${index}"]`);
    const state = mainRow ? (mainRow.dataset.state || 'NSW') : 'NSW';
    
    try {
        const response = await fetch(`/api/address/schools?lat=${lat}&lng=${lng}&state=${state}`);
        const data = await response.json();
        
        if (response.status === 401) {
            catchmentDetail.innerHTML = `<a href="/login" style="display: inline-block; padding: 4px 10px; background: #1e3a8a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.8rem; font-weight: 500; white-space: nowrap;">Login to see catchment</a>`;
            return;
        }
        
        if (data.schools && data.schools.length > 0) {
            const schoolMap = new Map();
            data.schools.forEach(school => {
                if (!schoolMap.has(school.school_id)) {
                    schoolMap.set(school.school_id, { ...school, yearLevels: [] });
                }
                if (school.year_level_code && school.year_level_code.trim()) {
                    schoolMap.get(school.school_id).yearLevels.push(school.year_level_code.trim());
                }
            });
            catchmentDetail.innerHTML = Array.from(schoolMap.values()).map(school => {
                const schoolLink = `/school-search?school_id=${school.school_id}`;
                let yearText = '';
                if (school.yearLevels.length > 0) {
                    const hasP6 = school.yearLevels.includes('P6');
                    const numericLevels = school.yearLevels.filter(y => y !== 'P6' && !isNaN(y)).map(Number).sort((a, b) => a - b);
                    const parts = [];
                    if (hasP6) parts.push('Prep-Yr 6');
                    if (numericLevels.length > 0) parts.push(`Yr ${numericLevels.join(', ')}`);
                    yearText = parts.length > 0 ? `, ${parts.join(', ')}` : '';
                }
                return `<a href="${schoolLink}" style="color: #2563eb; text-decoration: none; display: block; margin-bottom: 4px;">${school.school_name} <span style="color: #666; font-size: 0.85rem;">(${school.school_type}${yearText})</span></a>`;
            }).join('');
        } else {
            catchmentDetail.innerHTML = '<span style="color: #999;">No school catchments</span>';
        }
        
        catchmentDetail.dataset.loaded = 'true';
    } catch (error) {
        console.error('Error loading school catchments:', error);
        catchmentDetail.innerHTML = '<span style="color: #dc3545;">Error loading catchments</span>';
    }
}
