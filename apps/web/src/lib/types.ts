export type Lens = "effect" | "evidence" | "agreement" | "coverage";
export type Season = "all" | "DJF" | "MAM" | "JJA" | "SON";
export type WindowId = "full" | "35y" | "25y" | "15y";
export type PanelTab = "file" | "fire";
export type Direction = "increasing" | "decreasing" | "none";
export type EvidenceLevel = "strong" | "moderate" | "weak" | "insufficient";

export interface City {
  id: string;
  name: string;
  country: string;
  lat: number;
  lon: number;
  timezone: string;
  population: number;
  anchorRank: number;
  region: string;
  aliases: string[];
}

export interface Variable {
  key: string;
  sourceKey: string;
  label: string;
  code: string;
  definition: string;
  units: string;
  nativeFrequency: "daily" | "monthly";
  aggregation: "mean" | "sum";
  coverageStart: string;
  coverageEnd: string;
  theme: "HEAT" | "WATER" | "AIR" | "ENERGY";
  caveats: string[];
  resourcesTab: boolean;
  sourceDetail: string;
}

export interface WindowDef {
  id: WindowId;
  start: number;
  end: number;
  label: string;
  short: string;
}

export interface TrendRecord {
  status: "ok" | "insufficient_data";
  slope: number | null;
  ci: [number, number] | null;
  p: number | null;
  pOls: number | null;
  olsSlope: number | null;
  significant: boolean;
  methodDependent: boolean;
  direction: Direction;
  n: number;
  nYears: number;
  coverage: number;
  z: number | null;
  effectiveStart: number;
  q: number;
  qVar: number;
  significantFdr: boolean;
  significantVar: boolean;
  evidence: EvidenceLevel;
  evidenceVar: EvidenceLevel;
}

export type CityTrends = {
  methodVersion: string;
  generatedAt: string;
  windows: WindowDef[];
  seasons: Season[];
  cities: Record<string, Record<string, Record<string, TrendRecord>>>;
};

export type SeriesData = {
  startYear: number;
  months: number;
  cities: Record<string, Record<string, (number | null)[]>>;
};

export interface SeriesPoint {
  year: number;
  month: number;
  t: number;
  value: number | null;
}

export interface FireCluster {
  id: string;
  label: string;
  province: string;
  lat: number;
  lon: number;
  count: number;
  sumFrp: number;
  maxFrp: number;
  start: string;
  end: string;
}

export interface FireData {
  snapshot: { start: string; end: string; source: string; caveat: string };
  points: [number, number, number, string][];
  clusters: FireCluster[];
}

export interface ThenNowEntry {
  cityId: string;
  label: string;
  startDate: string;
  endDate: string;
  sensor: string;
  resolution: string;
  trueImage: string;
  falseImage: string;
  startTrueImage?: string;
  startFalseImage?: string;
  endTrueImage?: string;
  endFalseImage?: string;
  images?: {
    start?: { true?: string; false?: string };
    end?: { true?: string; false?: string };
  };
  caveat: string;
  fallback?: boolean;
}

export type ThenNowData = Record<string, ThenNowEntry>;

export interface CaseEntry {
  slug: string;
  title: string;
  question: string;
  placeId: string;
  variableKeys: string[];
  windowId: WindowId;
  season: Season;
  narrative: string;
  source: string;
  sourcesTab: boolean;
}

export interface CompositeResult {
  z: number | null;
  agreement: number;
  significantCount: number;
  selectedCount: number;
  mixed: boolean;
  methodDependent: boolean;
  evidence: EvidenceLevel;
  direction: "increasing" | "decreasing" | "none";
}

export interface ViewState {
  variableKeys: string[];
  lens: Lens;
  windowId: WindowId;
  season: Season;
  cityId: string | null;
  panelTab: PanelTab;
  areasOn: boolean;
  fireOn: boolean;
  night: boolean;
  labels: boolean;
  methodsOpen: boolean;
}

export interface CityNote {
  variableKey: string;
  text: string;
  tone: "rising" | "falling" | "mixed" | "weak" | "insufficient";
  evidence: EvidenceLevel;
}

