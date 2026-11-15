import { v } from "convex/values";
import { query } from "./_generated/server";

export const latest = query({
  args: {},
  returns: v.any(),
  handler: async (ctx) => {
    const doc = await ctx.db.query("fires").first();
    if (!doc) return null;
    return {
      snapshot: doc.snapshot,
      pointChunks: doc.pointChunks,
      clusters: doc.clusters,
    };
  },
});
