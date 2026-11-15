import { query } from "./_generated/server";
import { v } from "convex/values";

export const list = query({
  args: {},
  returns: v.any(),
  handler: async (ctx) => {
    return await ctx.db.query("cases").collect();
  },
});

export const get = query({
  args: { slug: v.string() },
  returns: v.any(),
  handler: async (ctx, args) => {
    return await ctx.db.query("cases").withIndex("by_slug", (q) => q.eq("slug", args.slug)).unique();
  },
});
