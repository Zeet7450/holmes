import type {
  CaseEntry,
  City,
  CityTrends,
  FireData,
  SeriesData,
  ThenNowData,
  Variable,
} from "./types";

const base = import.meta.env.BASE_URL;

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(`${base}data/${path}`);
  if (!response.ok) throw new Error(`Failed to load ${path}: ${response.status}`);
  return (await response.json()) as T;
}

export interface ModisTrend {
  series: { month: string; jakarta: number | null; wisconsin: number | null }[];
  trends: Record<
    string,
    {
      nYears: number;
      mean: number;
      slopePerDecade: number;
      p: number;
      ci: [number, number] | null;
      verdict: string;
    }
  >;
}

export interface BackendInfo {
  mode: "convex" | "static";
  health?: Record<string, unknown>;
}

export interface CoreData {
  cities: City[];
  variables: Variable[];
  trends: CityTrends;
  series: SeriesData;
  fires: FireData;
  thenNow: ThenNowData;
  cases: CaseEntry[];
  modis: ModisTrend | null;
  backend: BackendInfo;
}

export const emptyFires: FireData = {
  snapshot: {
    start: "2026-11-10",
    end: "2026-11-14",
    source: "NASA FIRMS NRT",
    caveat:
      "FIRMS detects hot pixels. They can be wildfires, peat burning, land clearing, agricultural burns, or industrial flares. This is not a confirmed incident.",
  },
  points: [],
  clusters: [],
};

let corePromise: Promise<CoreData> | null = null;

export function loadCoreData(): Promise<CoreData> {
  if (corePromise) return corePromise;
  corePromise = Promise.all([
    loadJson<City[]>("cities.json"),
    loadJson<Variable[]>("variables.json"),
    loadJson<CityTrends>("city-trends.json"),
    loadJson<SeriesData>("series.json"),
    loadJson<FireData>("fires.json").catch(() => emptyFires),
    loadJson<ThenNowData>("thenNow.json").catch(() => ({})),
    loadJson<CaseEntry[]>("cases.json").catch(() => []),
    loadJson<ModisTrend>("modis-case.json").catch(() => null),
  ]).then(async ([cities, variables, trends, series, staticFires, thenNow, staticCases, modis]) => {
    let fires = staticFires;
    let cases = staticCases;
    let backend: BackendInfo = { mode: "static" };
    const convexUrl = import.meta.env.VITE_CONVEX_URL as string | undefined;
    if (convexUrl) {
      try {
        const query = async (path: string, args: Record<string, unknown> = {}) => {
          const response = await fetch(`${convexUrl}/api/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path, args, format: "json" }),
            signal: AbortSignal.timeout(2500),
          });
          if (!response.ok) throw new Error(`Convex query ${path} failed: ${response.status}`);
          const payload = await response.json();
          if (payload.status !== "success") throw new Error(payload.errorMessage ?? "Convex query failed");
          return payload.value;
        };
        const [remoteFires, remoteCases, health] = await Promise.all([
          query("fires:latest"),
          query("cases:list"),
          query("system:health"),
        ]);
        if (remoteFires?.clusters?.length) {
          const points = Array.isArray(remoteFires.pointChunks)
            ? remoteFires.pointChunks.flat()
            : remoteFires.points ?? [];
          fires = { snapshot: remoteFires.snapshot, points, clusters: remoteFires.clusters } as FireData;
        }
        if (Array.isArray(remoteCases) && remoteCases.length) {
          const order = ["jakarta-warming", "jakarta-scan", "wisconsin-aod", "jakarta-rainfall", "jakarta-air", "wisconsin-temperature"];
          cases = [...(remoteCases as CaseEntry[])].sort((a, b) => order.indexOf(a.slug) - order.indexOf(b.slug));
        }
        backend = { mode: "convex", health };
      } catch (cause) {
        console.info("Convex backend unavailable; using the local cached dataset.", cause);
      }
    }
    return {
      cities: [...cities].sort((a, b) => a.anchorRank - b.anchorRank),
      variables,
      trends,
      series,
      fires,
      thenNow,
      cases,
      modis,
      backend,
    };
  });
  return corePromise;
}

export function resetDataCache() {
  corePromise = null;
}
