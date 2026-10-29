/**
 * Authoritative AICTE Approval Process Handbook (APH 2024–2027) Knowledge Chunks.
 *
 * Verbatim text and exact citations matching official Council specifications:
 * - Prototype Specification v2
 * - PS 26261 Idea and Approach Review
 * - Annexure 2.1 Mandatory Documents for Extension of Approval (EoA)
 */

export interface AphChunk {
  id: string;
  requirementCode: string;
  title: string;
  chapter: string;
  clause: string;
  pageNumber: number;
  citation: string;
  summary: string;
  verbatimText: string;
  keywords: string[];
  mandatoryCheckpoints: string[];
}

export const APH_HANDBOOK_CHUNKS: AphChunk[] = [
  {
    id: 'APH-CHUNK-01',
    requirementCode: 'EOA-SD-01',
    title: 'Affidavit 2 (Self-Disclosure Affirmation)',
    chapter: 'Annexure 2.1',
    clause: 'Item (i): Legal Undertakings',
    pageNumber: 142,
    citation: 'AICTE APH 2024–2027, Annexure 2.1, Item (i), p. 142',
    summary:
      'Mandatory notarized affidavit on non-judicial stamp paper of ₹100 affirming non-deviation from AICTE norms.',
    verbatimText:
      'Affidavit 2 shall be executed on a Non-Judicial Stamp Paper or e-Stamp Paper of minimum ₹100, duly notarized by an authorized Notary Public. The affidavit must be affirmed and executed by the Chairman or Secretary of the sponsoring Trust, Society, or Company registered under Section 8 of the Companies Act. The contents of Affidavit 2 certify that the applicant institution complies with all land, building, faculty, instructional facility, and fee norms without deviation.',
    keywords: [
      'affidavit',
      'affidavit 2',
      'stamp paper',
      'notarized',
      'e-stamp',
      '100',
      'chairman',
      'secretary',
      'signatory',
      'trustee',
    ],
    mandatoryCheckpoints: [
      'Non-Judicial / e-Stamp paper value minimum ₹100',
      'Duly sworn before a Competent Notary Public with seal & registration number',
      'Signed by Chairman or Secretary as registered in AICTE portal profile',
    ],
  },
  {
    id: 'APH-CHUNK-02',
    requirementCode: 'EOA-SD-02',
    title: 'Application Processing Fee & Statutory Exemptions',
    chapter: 'Chapter II',
    clause: 'Section 2.4: Processing Fee Scale and Concessions',
    pageNumber: 48,
    citation: 'AICTE APH 2024–2027, Chapter II, Section 2.4, p. 48',
    summary:
      'Non-refundable processing fee requirement and specific statutory exemption criteria for government/special category institutions.',
    verbatimText:
      'The applicant institution shall remit the prescribed non-refundable application processing fee through the designated AICTE payment gateway. Government institutions, Central/State University departments, and institutions located in designated special hilly or remote regions may claim statutory fee exemption subject to production of an authoritative government gazette notification or administrative sanction order. Claiming fee exemption without verifiable government sanction renders the application deficient.',
    keywords: [
      'fee',
      'processing fee',
      'exemption',
      'payment',
      'challan',
      'section 2.4',
      'tuition fee waiver',
      'concession',
      'government gazette',
    ],
    mandatoryCheckpoints: [
      'Online transaction receipt with valid transaction reference ID, or',
      'Official Gazette notification / Government sanction order for statutory exemption',
      'Distinction between application processing fee exemption and student tuition fee waiver',
    ],
  },
  {
    id: 'APH-CHUNK-03',
    requirementCode: 'EOA-SD-03',
    title: 'Land Ownership & Registration Documents',
    chapter: 'Annexure 2.1',
    clause: 'Item (iii): Land Title & Contiguity Standards',
    pageNumber: 143,
    citation: 'AICTE APH 2024–2027, Annexure 2.1, Item (iii), Clause 2.1.2, p. 143',
    summary:
      'Proof of clear, contiguous, and unencumbered land title registered in the name of the Trust/Society/Institution.',
    verbatimText:
      'Registered Sale Deed, Gift Deed, Government Allotment Order, or Registered Lease Deed for a minimum period of 30 years in the name of the applicant Society/Trust/Company. The land must be contiguous as per Chapter IV norms (e.g. minimum 7.5 acres in rural areas, 2.5 acres in urban mega cities). Any variance between the declared parcel acreage and authoritative State Revenue records (7/12 extract / Patta / Khasra) constitutes a major contradiction requiring formal rectification or demarcation survey.',
    keywords: [
      'land',
      'deed',
      'sale deed',
      'revenue',
      'acres',
      'contiguity',
      'state revenue',
      'patta',
      '7/12',
      'khasra',
      'plot',
      'survey',
    ],
    mandatoryCheckpoints: [
      'Registered title deed with Sub-Registrar stamp & registration number',
      'Certified copy of latest Revenue record (7/12 extract / Patta / Khatian)',
      'Contiguity certificate issued by competent revenue authority',
    ],
  },
  {
    id: 'APH-CHUNK-04',
    requirementCode: 'EOA-SD-04',
    title: 'Structural Stability Certificate (> 30 Years Criterion)',
    chapter: 'Annexure 2.1',
    clause: 'Item (iv): Building Safety & Age Threshold',
    pageNumber: 144,
    citation: 'AICTE APH 2024–2027, Annexure 2.1, Item (iv), p. 144',
    summary:
      'Approved municipal building sanction plan and mandatory structural stability certificate if building construction exceeds 30 years.',
    verbatimText:
      'Approved Building Sanction Plan issued by the Competent Municipal Authority / Town Planning Department. In all cases where the institution premises or building structures were constructed thirty (30) or more years prior to the application academic year, a Structural Stability Certificate issued by a registered Structural Engineer / Chartered Engineer (certifying structural safety under NBC 2016) is strictly mandatory. Failure to submit this certificate results in a DEFICIENT regulatory finding.',
    keywords: [
      'structural stability',
      'building plan',
      '30 years',
      'structural engineer',
      'chartered engineer',
      'nbc 2016',
      'completion date',
      '1990',
      'municipal',
    ],
    mandatoryCheckpoints: [
      'Approved building sanction drawing with plinth/completion approval',
      'If construction year is > 30 years prior to AY, Structural Stability Certificate is mandatory',
      'Certificate must bear valid engineer registration license number and inspection validity date',
    ],
  },
  {
    id: 'APH-CHUNK-05',
    requirementCode: 'EOA-SD-05',
    title: 'Fire Safety Certificate / NOC from Competent Authority',
    chapter: 'Annexure 2.1',
    clause: 'Item (v): Life Safety & Fire Clearance',
    pageNumber: 144,
    citation: 'AICTE APH 2024–2027, Annexure 2.1, Item (v), p. 144',
    summary:
      'Valid Fire Safety NOC issued by the State Fire Services Directorate or Municipal Chief Fire Officer.',
    verbatimText:
      'Fire Safety Certificate / No Objection Certificate (NOC) issued by the Chief Fire Officer / Director of Fire Services of the respective State / Union Territory. The certificate must confirm adequate provision of fire suppression equipment, hydrants, automatic detection/sprinklers, emergency staircases, and unobstructed ingress routes. The NOC must be active and valid for the operational academic year.',
    keywords: [
      'fire',
      'fire safety',
      'noc',
      'fire services',
      'cfo',
      'fire clearance',
      'life safety',
      'sprinkler',
    ],
    mandatoryCheckpoints: [
      'Issued by authorized State / Municipal Fire Authority',
      'Active validity covering the target academic year',
      'Physical inspection verification of operational pressure pumps and escape exits',
    ],
  },
  {
    id: 'APH-CHUNK-06',
    requirementCode: 'EOA-SD-06',
    title: 'Demarcated Satellite Map with Geocoordinates',
    chapter: 'Annexure 2.1',
    clause: 'Item (vi): Geospatial Site Demarcation',
    pageNumber: 145,
    citation: 'AICTE APH 2024–2027, Annexure 2.1, Item (vi), p. 145',
    summary:
      'Satellite image overlay demarcating institution boundary polygon with exact GPS/Bhuvan coordinates.',
    verbatimText:
      'A demarcated satellite imagery map generated through ISRO Bhuvan or accredited satellite mapping portals, clearly showing the boundary perimeter coordinates (Latitude and Longitude in WGS84 format) of the campus land. The demarcated polygon must match the parcel boundaries described in the registered land deeds.',
    keywords: [
      'satellite',
      'bhuvan',
      'geocoordinates',
      'latitude',
      'longitude',
      'gis',
      'demarcation',
      'boundary',
      'perimeter',
    ],
    mandatoryCheckpoints: [
      'GPS coordinates of all vertex corners of the institutional perimeter',
      'Clear demarcation polygon overlaid on high-resolution satellite imagery',
      'Match between declared surveyed area and computed polygon surface area',
    ],
  },
  {
    id: 'APH-CHUNK-07',
    requirementCode: 'EOA-SD-07',
    title: 'Audited Financial Statements with ICAI UDIN',
    chapter: 'Annexure 2.1',
    clause: 'Item (vii): Financial Accountability & UDIN',
    pageNumber: 145,
    citation: 'AICTE APH 2024–2027, Annexure 2.1, Item (vii), p. 145',
    summary:
      'Audited balance sheet, income & expenditure account, and audit report bearing a verified ICAI UDIN.',
    verbatimText:
      'Audited Financial Statements for the preceding financial year comprising Balance Sheet, Income and Expenditure Account, and Auditor’s Report duly signed by a qualified Chartered Accountant in active practice. Every certificate and audit report must carry a valid Unique Document Identification Number (UDIN) generated from the official ICAI UDIN portal. Financial submissions with invalid or unregistered UDINs will be flagged as DEFICIENT under regulatory integrity protocols.',
    keywords: [
      'financial',
      'balance sheet',
      'ca',
      'chartered accountant',
      'udin',
      'icai',
      'audit report',
      'expenditure',
    ],
    mandatoryCheckpoints: [
      'Signed and stamped by active Fellow/Associate Chartered Accountant',
      'Valid 18-digit Unique Document Identification Number (UDIN)',
      'Verified status against official ICAI UDIN registry portal',
    ],
  },
];

/**
 * Searches the authoritative AICTE APH chunks using deterministic keyword scoring.
 */
export function searchAphHandbook(query: string): AphChunk[] {
  const clean = query.trim().toLowerCase();
  if (!clean) return APH_HANDBOOK_CHUNKS;

  const terms = clean.split(/\s+/).filter((t) => t.length > 2);

  const scored = APH_HANDBOOK_CHUNKS.map((chunk) => {
    let score = 0;

    // Check requirement code exact match (e.g. EOA-SD-04)
    if (clean.includes(chunk.requirementCode.toLowerCase())) {
      score += 20;
    }

    // Check title matches
    if (chunk.title.toLowerCase().includes(clean)) {
      score += 15;
    }

    // Check keyword matches
    for (const term of terms) {
      if (chunk.keywords.some((k) => k.includes(term))) {
        score += 5;
      }
      if (chunk.verbatimText.toLowerCase().includes(term)) {
        score += 3;
      }
      if (chunk.summary.toLowerCase().includes(term)) {
        score += 2;
      }
    }

    return { chunk, score };
  });

  return scored
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((s) => s.chunk);
}

