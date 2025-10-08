/**
 * Borough Context Service
 * Provides AI agents with borough-specific context for intelligent planning
 */

export interface BoroughContext {
  name: string;
  slug: string;
  demographics: {
    population: number;
    density: number;
    vulnerablePopulation: number;
    touristAreas: string[];
  };
  infrastructure: {
    majorRoads: string[];
    transportHubs: string[];
    hospitals: string[];
    schools: string[];
    emergencyServices: string[];
  };
  riskProfile: {
    floodRisk: 'low' | 'medium' | 'high';
    terroristThreat: 'low' | 'medium' | 'high';
    historicalIncidents: string[];
  };
  evacuationChallenges: string[];
  keyAssets: string[];
  neighboringBoroughs: string[];
}

export class BoroughContextService {
  private static boroughData: Record<string, BoroughContext> = {
    'westminster': {
      name: 'Westminster',
      slug: 'westminster',
      demographics: {
        population: 261000,
        density: 11618, // per km²
        vulnerablePopulation: 15000,
        touristAreas: ['Westminster Abbey', 'Big Ben', 'Buckingham Palace', 'Oxford Street']
      },
      infrastructure: {
        majorRoads: ['A4', 'A40', 'A3212', 'Victoria Embankment'],
        transportHubs: ['Victoria Station', 'Paddington Station', 'Westminster Underground'],
        hospitals: ['St Mary\'s Hospital', 'Westminster Hospital'],
        schools: ['Westminster School', 'Grey Coat Hospital'],
        emergencyServices: ['New Scotland Yard', 'Westminster Fire Station']
      },
      riskProfile: {
        floodRisk: 'medium',
        terroristThreat: 'high',
        historicalIncidents: ['2017 Westminster Bridge Attack', '2005 London Bombings']
      },
      evacuationChallenges: [
        'High tourist density',
        'Complex transport network',
        'Government buildings security',
        'Thames flood risk'
      ],
      keyAssets: [
        'Houses of Parliament',
        'Buckingham Palace',
        'Westminster Abbey',
        'Government offices'
      ],
      neighboringBoroughs: ['Camden', 'Kensington and Chelsea', 'Lambeth', 'Southwark']
    },
    'camden': {
      name: 'Camden',
      slug: 'camden',
      demographics: {
        population: 270000,
        density: 12500,
        vulnerablePopulation: 18000,
        touristAreas: ['Camden Market', 'Regent\'s Park', 'London Zoo']
      },
      infrastructure: {
        majorRoads: ['A5', 'A400', 'A4200'],
        transportHubs: ['King\'s Cross Station', 'Euston Station', 'Camden Town Underground'],
        hospitals: ['Royal Free Hospital', 'University College Hospital'],
        schools: ['Camden School for Girls', 'University College London'],
        emergencyServices: ['Camden Fire Station', 'Kentish Town Police Station']
      },
      riskProfile: {
        floodRisk: 'low',
        terroristThreat: 'medium',
        historicalIncidents: ['King\'s Cross Fire 1987']
      },
      evacuationChallenges: [
        'Major transport hub congestion',
        'High student population',
        'Mixed residential and commercial areas',
        'Canal network constraints'
      ],
      keyAssets: [
        'King\'s Cross Station',
        'Euston Station',
        'British Library',
        'University College London'
      ],
      neighboringBoroughs: ['Westminster', 'Islington', 'Haringey', 'Brent']
    },
    'kensington and chelsea': {
      name: 'Kensington and Chelsea',
      slug: 'kensington and chelsea',
      demographics: {
        population: 156000,
        density: 13000,
        vulnerablePopulation: 8000,
        touristAreas: ['Kensington Palace', 'Natural History Museum', 'Victoria and Albert Museum', 'Hyde Park']
      },
      infrastructure: {
        majorRoads: ['A4', 'A315', 'A3220'],
        transportHubs: ['South Kensington Underground', 'Sloane Square Underground'],
        hospitals: ['Chelsea and Westminster Hospital', 'Royal Brompton Hospital'],
        schools: ['Imperial College London', 'Royal College of Art'],
        emergencyServices: ['Chelsea Fire Station', 'Kensington Police Station']
      },
      riskProfile: {
        floodRisk: 'low',
        terroristThreat: 'medium',
        historicalIncidents: ['Grenfell Tower Fire 2017']
      },
      evacuationChallenges: [
        'High-rise residential buildings',
        'Narrow Victorian streets',
        'Affluent area with limited public transport',
        'Museum district crowds'
      ],
      keyAssets: [
        'Kensington Palace',
        'Natural History Museum',
        'Victoria and Albert Museum',
        'Imperial College London'
      ],
      neighboringBoroughs: ['Westminster', 'Hammersmith and Fulham', 'Wandsworth']
    },
    'tower hamlets': {
      name: 'Tower Hamlets',
      slug: 'tower hamlets',
      demographics: {
        population: 324000,
        density: 15695,
        vulnerablePopulation: 35000,
        touristAreas: ['Tower of London', 'Tower Bridge', 'Canary Wharf', 'Brick Lane']
      },
      infrastructure: {
        majorRoads: ['A11', 'A13', 'A1203'],
        transportHubs: ['Canary Wharf Station', 'Liverpool Street (nearby)', 'Tower Gateway DLR'],
        hospitals: ['Royal London Hospital', 'Mile End Hospital'],
        schools: ['Queen Mary University of London', 'Mulberry School for Girls'],
        emergencyServices: ['Whitechapel Fire Station', 'Bethnal Green Police Station']
      },
      riskProfile: {
        floodRisk: 'high',
        terroristThreat: 'medium',
        historicalIncidents: ['London Bridge Attack 2017', 'Blitz bombing WWII']
      },
      evacuationChallenges: [
        'Thames flood barrier proximity',
        'High-density housing estates',
        'Financial district worker influx',
        'Limited river crossings'
      ],
      keyAssets: [
        'Tower of London',
        'Canary Wharf Financial District',
        'Tower Bridge',
        'Queen Mary University'
      ],
      neighboringBoroughs: ['Hackney', 'Newham', 'Southwark', 'City of London']
    },
    'hackney': {
      name: 'Hackney',
      slug: 'hackney',
      demographics: {
        population: 281000,
        density: 14600,
        vulnerablePopulation: 25000,
        touristAreas: ['Victoria Park', 'Broadway Market', 'Hackney Empire']
      },
      infrastructure: {
        majorRoads: ['A10', 'A107', 'A1199'],
        transportHubs: ['Hackney Central', 'Dalston Junction', 'Old Street (nearby)'],
        hospitals: ['Homerton University Hospital', 'St Leonard\'s Hospital'],
        schools: ['Hackney Community College', 'City and Islington College'],
        emergencyServices: ['Hackney Fire Station', 'Stoke Newington Police Station']
      },
      riskProfile: {
        floodRisk: 'low',
        terroristThreat: 'low',
        historicalIncidents: ['2011 London Riots']
      },
      evacuationChallenges: [
        'Gentrification creating mixed demographics',
        'Limited tube connectivity',
        'Canal network barriers',
        'High cycling population'
      ],
      keyAssets: [
        'Victoria Park',
        'Hackney Empire',
        'Lee Valley Regional Park',
        'Tech City (Old Street)'
      ],
      neighboringBoroughs: ['Islington', 'Tower Hamlets', 'Newham', 'Waltham Forest']
    }
  };

  static getBoroughContext(boroughSlug: string): BoroughContext | null {
    return this.boroughData[boroughSlug] || null;
  }

  static getAllBoroughs(): BoroughContext[] {
    return Object.values(this.boroughData);
  }

  static generateAIPromptContext(borough: BoroughContext): string {
    return `
Borough: ${borough.name}
Population: ${borough.demographics.population.toLocaleString()} (density: ${borough.demographics.density}/km²)
Vulnerable population: ${borough.demographics.vulnerablePopulation.toLocaleString()}

Key Infrastructure:
- Transport hubs: ${borough.infrastructure.transportHubs.join(', ')}
- Major roads: ${borough.infrastructure.majorRoads.join(', ')}
- Hospitals: ${borough.infrastructure.hospitals.join(', ')}
- Emergency services: ${borough.infrastructure.emergencyServices.join(', ')}

Risk Profile:
- Flood risk: ${borough.riskProfile.floodRisk}
- Terrorist threat: ${borough.riskProfile.terroristThreat}
- Historical incidents: ${borough.riskProfile.historicalIncidents.join(', ')}

Evacuation Challenges:
${borough.evacuationChallenges.map(challenge => `- ${challenge}`).join('\n')}

Key Assets to Protect:
${borough.keyAssets.map(asset => `- ${asset}`).join('\n')}

Tourist Areas: ${borough.demographics.touristAreas.join(', ')}
Neighboring Boroughs: ${borough.neighboringBoroughs.join(', ')}
    `;
  }

  static generateBoroughSpecificSuggestions(context: BoroughContext): string[] {
    const suggestions = [];
    
    // Risk-based suggestions
    if (context.riskProfile.floodRisk === 'high') {
      suggestions.push(`Test flood evacuation for ${context.name} during high tide`);
    }
    if (context.riskProfile.terroristThreat === 'high') {
      suggestions.push(`Analyse security incident evacuation around ${context.keyAssets[0]}`);
    }
    
    // Infrastructure-based suggestions
    if (context.infrastructure.transportHubs.length > 2) {
      suggestions.push(`Evaluate transport hub closure impact on ${context.name} evacuation`);
    }
    
    // Tourism-based suggestions
    if (context.demographics.touristAreas.length > 0) {
      suggestions.push(`Plan evacuation during peak tourist season in ${context.name}`);
    }

    // Population density suggestions
    if (context.demographics.density > 12000) {
      suggestions.push(`Test high-density evacuation efficiency in ${context.name}`);
    }

    // Vulnerable population suggestions
    if (context.demographics.vulnerablePopulation > 20000) {
      suggestions.push(`Focus on vulnerable population protection during ${context.name} evacuation`);
    }

    return suggestions;
  }

  static formatBoroughName(slug: string): string {
    return slug
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  static getBoroughSlug(name: string): string {
    return name.toLowerCase().replace(/\s+/g, ' ').trim();
  }
}
