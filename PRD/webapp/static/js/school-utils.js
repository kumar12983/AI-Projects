// ============================================
// Utility Functions — school-utils.js
// ============================================

function calculateDistance(lat1, lon1, lat2, lon2) {
    // Haversine formula
    const R = 6371; // Earth's radius in km
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);

    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;

    if (distance < 1) {
        return `${Math.round(distance * 1000)} m`;
    } else {
        return `${distance.toFixed(2)} km`;
    }
}

function toRad(degrees) {
    return degrees * Math.PI / 180;
}

function generatePropertyLinks(address) {
    if (!address.street_name || !address.suburb || !address.street_number) {
        return '-';
    }

    // Helper function to format text for URLs
    const formatForUrl = (text) => {
        if (!text) return '';
        return text.toLowerCase()
            .replace(/\s+/g, '-')
            .replace(/[^a-z0-9-]/g, '');
    };

    // Build street number
    const urlStreetNumber = address.street_number.replace('N/A', '').trim();

    // Get unit number (just the number, not the type)
    const urlUnitNumber = address.unit_number ? address.unit_number.toString().trim() : '';

    const expandedTypeRE = expandStreetTypeRealEstate(address.street_type);
    const expandedTypeDomain = expandStreetTypeDomain(address.street_type);

    const urlStreetNameRealEstate = formatForUrl([address.street_name, expandedTypeRE].filter(Boolean).join(' '));
    const urlStreetNameDomain = formatForUrl([address.street_name, expandedTypeDomain].filter(Boolean).join(' '));
    const urlSuburb = formatForUrl(address.suburb);
    const urlState = (address.state || 'nsw').toLowerCase();
    const urlPostcode = address.postcode || '';

    // Build RealEstate URL with unit prefix if unit exists
    let realEstateUrl = '';
    if (urlStreetNumber && urlStreetNameRealEstate && urlSuburb && urlState && urlPostcode) {
        if (urlUnitNumber) {
            // Format: unit-4-53-57-burdett-cres-hornsby-nsw-2077
            realEstateUrl = `https://www.realestate.com.au/property/unit-${urlUnitNumber}-${urlStreetNumber}-${urlStreetNameRealEstate}-${urlSuburb}-${urlState}-${urlPostcode}/`;
        } else {
            realEstateUrl = `https://www.realestate.com.au/property/${urlStreetNumber}-${urlStreetNameRealEstate}-${urlSuburb}-${urlState}-${urlPostcode}/`;
        }
    }

    // Build Domain URL with unit number (no prefix) if unit exists
    let domainUrl = '';
    if (urlStreetNumber && urlStreetNameDomain && urlSuburb && urlState && urlPostcode) {
        if (urlUnitNumber) {
            // Format: 4-53-57-burdett-crescent-hornsby-nsw-2077
            domainUrl = `https://www.domain.com.au/property-profile/${urlUnitNumber}-${urlStreetNumber}-${urlStreetNameDomain}-${urlSuburb}-${urlState}-${urlPostcode}`;
        } else {
            domainUrl = `https://www.domain.com.au/property-profile/${urlStreetNumber}-${urlStreetNameDomain}-${urlSuburb}-${urlState}-${urlPostcode}`;
        }
    }

    if (!realEstateUrl && !domainUrl) {
        return '-';
    }

    return `
        <div style="display: flex; flex-direction: column; gap: 8px;">
            ${realEstateUrl ? `<a href="${realEstateUrl}" target="_blank" class="property-link" style="display: block; text-align: center; padding: 6px 12px; background: #c41230; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500; white-space: nowrap; min-width: 85px;" title="View on RealEstate.com.au">RealEstate</a>` : ''}
            ${domainUrl ? `<a href="${domainUrl}" target="_blank" class="property-link" style="display: block; text-align: center; padding: 6px 12px; background: #16a34a; color: white; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500; white-space: nowrap; min-width: 85px;" title="View on Domain.com.au">Domain</a>` : ''}
        </div>
    `;
}

function expandStreetTypeRealEstate(streetType) {
    if (!streetType) return '';
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
    const lowerType = streetType.toLowerCase();
    return abbreviations[lowerType] || lowerType;
}

function expandStreetTypeDomain(streetType) {
    if (!streetType) return '';
    const expansions = {
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
    const lowerType = streetType.toLowerCase();
    return expansions[lowerType] || lowerType;
}

function getGeocodeTypeDescription(code) {
    const descriptions = {
        'BAP': 'Building Access Point - Point of access to the building',
        'BC': 'Building Centroid - Centre of building footprint',
        'BCP': 'Building Centroid Point - Centre of building',
        'CDF': 'Cadastral Frontage - Property boundary on street',
        'EC': 'Emergency Access - Emergency service access point',
        'ECP': 'Emergency Centroid Point - Emergency centroid',
        'FC': 'Frontage Centre - Centre of property frontage',
        'FCP': 'Frontage Centre Point - Centre point of frontage',
        'GAP': 'Gazetted Address Point - Official gazetted location',
        'LCP': 'Locality Centre Point - Centre of locality',
        'PAP': 'Property Access Point - Main property access',
        'PC': 'Property Centroid - Centre of property',
        'UC': 'Unit Centroid - Centre of unit'
    };
    return descriptions[code] || 'Unknown geocode type';
}

function getConfidenceDescription(confidence) {
    const descriptions = {
        'HIGH': 'High confidence in coordinate accuracy',
        'MEDIUM': 'Medium confidence in coordinate accuracy',
        'LOW': 'Low confidence in coordinate accuracy',
        'VERY LOW': 'Very low confidence in coordinate accuracy',
        'UNKNOWN': 'Confidence level unknown'
    };
    return descriptions[confidence] || 'Unknown confidence level';
}

function openGoogleMaps(lat, lng) {
    window.open(`https://www.google.com/maps?q=${lat},${lng}`, '_blank');
}
