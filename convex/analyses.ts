import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const WINDOW_START: Record<string, number> = { full: 1981, "35y": 1991, "25y": 2001, "15y": 2011 };

export const get = query({
  args: { cacheKey: v.string() },
  returns: v.any(),
  handler: async (ctx, args) => {
    const doc = await ctx.db
      .query("analyses")
      .withIndex("by_cache_key", (q) => q.eq("cacheKey", args.cacheKey))
      .unique();
    return doc ?? null;
  },
});

export const request = mutation({
  args: {
    cityId: v.string(),
    variableKey: v.string(),
    windowId: v.string(),
    season: v.string(),
  },
  returns: v.any(),
  handler: async (ctx, args) => {
    const cacheKey = `analysis:${args.cityId}:${args.variableKey}:${args.windowId}:${args.season}:1.0.0`;
    const existing = await ctx.db
      .query("analyses")
      .withIndex("by_cache_key", (q) => q.eq("cacheKey", cacheKey))
      .unique();
    if (existing) return { cacheKey, cached: true, analysis: existing };

    const city = await ctx.db
      .query("cityTrends")
      .withIndex("by_city", (q) => q.eq("cityId", args.cityId))
      .unique();
    const key = `${args.windowId}|${args.season}`;
    const result = city?.records?.[args.variableKey]?.[key];
    if (!result) {
      throw new Error(`NO_DATA: ${args.cityId}/${args.variableKey}/${args.windowId}/${args.season}`);
    }
    const id = await ctx.db.insert("analyses", {
      cacheKey,
      cityId: args.cityId,
      variableKey: args.variableKey,
      windowId: args.windowId,
      season: args.season,
      methodVersion: "1.0.0",
      result,
      createdAt: Date.now(),
    });
    return { cacheKey, cached: false, analysis: { _id: id, result } };
  },
});

export const ranking = mutation({
  args: { variableKey: v.string(), windowId: v.string(), season: v.string(), direction: v.string() },
  returns: v.any(),
  handler: async (ctx, args) => {
    const cities = await ctx.db.query("cityTrends").collect();
    const key = `${args.windowId}|${args.season}`;
    const rows = cities
      .map((city) => ({ cityId: city.cityId, result: city.records?.[args.variableKey]?.[key] }))
      .filter((row) => row.result && row.result.status === "ok")
      .filter((row) => args.direction === "all" || (args.direction === "increasing" ? row.result.slope > 0 : row.result.slope < 0))
      .sort((a, b) => Math.abs(b.result.z ?? b.result.slope ?? 0) - Math.abs(a.result.z ?? a.result.slope ?? 0))
      .slice(0, 20);
    return rows;
  },
});

export const windowStart = query({
  args: { windowId: v.string() },
  returns: v.any(),
  handler: (ctx, args) => WINDOW_START[args.windowId] ?? 1981,
});
