import { mutation } from "./_generated/server";
import { v } from "convex/values";


export const clear = mutation({
  args: {},
  returns: v.any(),
  handler: async (ctx) => {
    for (const table of ["cities", "variables", "cityTrends", "cases", "fires", "analyses", "jobs", "threads"] as const) {
      const rows = await ctx.db.query(table).collect();
      for (const row of rows) await ctx.db.delete(row._id);
    }
    return { ok: true };
  },
});

export const insertCityBatch = mutation({
  args: { cities: v.array(v.any()) },
  returns: v.any(),
  handler: async (ctx, args) => {
    for (const city of args.cities) await ctx.db.insert("cities", city);
    return { inserted: args.cities.length };
  },
});

export const insertVariables = mutation({
  args: { variables: v.array(v.any()) },
  returns: v.any(),
  handler: async (ctx, args) => {
    for (const variable of args.variables) await ctx.db.insert("variables", variable);
    return { inserted: args.variables.length };
  },
});

export const insertCases = mutation({
  args: { cases: v.array(v.any()) },
  returns: v.any(),
  handler: async (ctx, args) => {
    for (const entry of args.cases) await ctx.db.insert("cases", entry);
    return { inserted: args.cases.length };
  },
});

export const insertFires = mutation({
  args: { snapshot: v.any(), pointChunks: v.array(v.any()), clusters: v.any() },
  returns: v.any(),
  handler: async (ctx, args) => {
    await ctx.db.insert("fires", args);
    return { ok: true };
  },
});

export const insertCityTrend = mutation({
  args: { cityId: v.string(), records: v.any(), series: v.any() },
  returns: v.any(),
  handler: async (ctx, args) => {
    await ctx.db.insert("cityTrends", args);
    return { ok: true };
  },
});
