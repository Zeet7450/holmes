import { query } from "./_generated/server";
import { v } from "convex/values";

export const getCity = query({
  args: { cityId: v.string() },
  returns: v.any(),
  handler: async (ctx, args) => {
    return await ctx.db
      .query("cityTrends")
      .withIndex("by_city", (q) => q.eq("cityId", args.cityId))
      .unique();
  },
});

export const get = query({
  args: {
    cityId: v.string(),
    variableKey: v.string(),
    windowId: v.string(),
    season: v.string(),
  },
  returns: v.any(),
  handler: async (ctx, args) => {
    const doc = await ctx.db
      .query("cityTrends")
      .withIndex("by_city", (q) => q.eq("cityId", args.cityId))
      .unique();
    const key = `${args.windowId}|${args.season}`;
    return doc?.records?.[args.variableKey]?.[key] ?? null;
  },
});

export const series = query({
  args: { cityId: v.string(), variableKey: v.string() },
  returns: v.any(),
  handler: async (ctx, args) => {
    const doc = await ctx.db
      .query("cityTrends")
      .withIndex("by_city", (q) => q.eq("cityId", args.cityId))
      .unique();
    return doc?.series?.[args.variableKey] ?? null;
  },
});
