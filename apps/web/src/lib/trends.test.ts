import { describe, expect, it } from "vitest";
import type { SeriesPoint, CityTrends } from "./types";
import {
  annualize,
  compositeForCity,
  deseasonalize,
  findCity,
  formatP,
  getRecord,
  rollingMean,
} from "./trends";

function monthlySeries(yearCount: number, value: (index: number) => number): SeriesPoint[] {
  return Array.from({ length: yearCount * 12 }, (_, index) => {
    const year = 2000 + Math.floor(index / 12);
    const month = (index % 12) + 1;
    return { year, month, t: year + (month - 1) / 12, value: value(index) };
  });
}

describe("trend helpers", () => {
  it("annualizes monthly points and requires ten months", () => {
    const points = monthlySeries(2, () => 1);
    points.push({ year: 2002, month: 1, t: 2002, value: 9 });
    const annual = annualize(points);
    expect(annual).toHaveLength(2);
    expect(annual[0].value).toBeCloseTo(1);
  });

  it("computes a trailing rolling mean and leaves gaps", () => {
    const points = monthlySeries(2, (index) => index);
    const rolling = rollingMean(points, 12);
    expect(rolling[10]).toBeNull();
    expect(rolling[11]).toBeCloseTo(5.5);
    expect(rolling[12]).toBeCloseTo(6.5);
  });

  it("removes the calendar-month mean", () => {
    const points = monthlySeries(3, (index) => (index % 12) + 1);
    const adjusted = deseasonalize(points);
    for (const value of adjusted.map((point) => point.value)) {
      expect(Math.abs(value as number)).toBeLessThan(1e-9);
    }
  });

  it("detects mixed composite signals", () => {
    const trends = {
      methodVersion: "1.0.0",
      generatedAt: "",
      windows: [],
      seasons: [],
      cities: {
        test: {
          T2M: {
            "25y|all": {
              status: "ok", slope: 0.3, ci: null, p: 0.01, pOls: 0.02, olsSlope: 0.3,
              significant: true, methodDependent: false, direction: "increasing", n: 300,
              nYears: 25, coverage: 1, z: 2, effectiveStart: 2001, q: 0.01, qVar: 0.01,
              significantFdr: true, significantVar: true, evidence: "strong", evidenceVar: "strong",
            },
          },
          PRECTOTCORR: {
            "25y|all": {
              status: "ok", slope: -0.2, ci: null, p: 0.02, pOls: 0.03, olsSlope: -0.2,
              significant: true, methodDependent: false, direction: "decreasing", n: 300,
              nYears: 25, coverage: 1, z: -1.5, effectiveStart: 2001, q: 0.02, qVar: 0.02,
              significantFdr: true, significantVar: true, evidence: "strong", evidenceVar: "strong",
            },
          },
        },
      },
    } as unknown as CityTrends;
    const composite = compositeForCity(trends, "test", ["T2M", "PRECTOTCORR"], "25y", "all");
    expect(composite.mixed).toBe(true);
    expect(composite.agreement).toBeLessThan(0.67);
    expect(composite.z).toBeCloseTo(0.25);
  });

  it("finds cities by alias and substring", () => {
    const cities = [
      { id: "jakarta", name: "Jakarta", country: "Indonesia", lat: 0, lon: 0, timezone: "", population: 1, anchorRank: 1, region: "", aliases: ["DKI Jakarta"] },
      { id: "caracas", name: "Caracas", country: "Venezuela", lat: 0, lon: 0, timezone: "", population: 1, anchorRank: 2, region: "", aliases: [] },
    ];
    expect(findCity(cities, "DKI Jakarta")?.id).toBe("jakarta");
    expect(findCity(cities, "carac")?.id).toBe("caracas");
    expect(findCity(cities, "nowhere")).toBeNull();
  });

  it("formats p-values without false precision", () => {
    expect(formatP(0.00001)).toBe("p < 0.001");
    expect(formatP(0.0419)).toBe("p = 0.042");
    expect(formatP(null)).toBe("p unavailable");
  });

  it("returns null for missing records", () => {
    const trends = { cities: {} } as unknown as CityTrends;
    expect(getRecord(trends, "missing", "T2M", "25y", "all")).toBeNull();
  });
});
