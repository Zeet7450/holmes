import { query } from "./_generated/server";
import { v } from "convex/values";

export const listVariables = query({
  args: {},
  returns: v.any(),
  handler: async (ctx) => {
    const variables = await ctx.db.query("variables").collect();
    return variables.sort((a, b) => a.label.localeCompare(b.label));
  },
});

export const getVariable = query({
  args: { key: v.string() },
  returns: v.any(),
  handler: async (ctx, args) => {
    return await ctx.db.query("variables").withIndex("by_key", (q) => q.eq("key", args.key)).unique();
  },
});

export const listCities = query({
  args: {},
  returns: v.any(),
  handler: async (ctx) => {
    const cities = await ctx.db.query("cities").collect();
    return cities.sort((a, b) => a.anchorRank - b.anchorRank);
  },
});

export const searchCities = query({
  args: { query: v.string(), limit: v.optional(v.number()) },
  returns: v.any(),
  handler: async (ctx, args) => {
    const needle = args.query.trim().toLowerCase();
    const limit = args.limit ?? 8;
    if (!needle) return [];
    const cities = await ctx.db.query("cities").collect();
    return cities
      .filter((city) =>
        [city.name, city.country, city.id, ...city.aliases].some((name) =>
          name.toLowerCase().includes(needle),
        ),
      )
      .slice(0, limit);
  },
});
