import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const get = query({
  args: { jobId: v.id("jobs") },
  returns: v.any(),
  handler: async (ctx, args) => await ctx.db.get(args.jobId),
});

export const cancel = mutation({
  args: { jobId: v.id("jobs") },
  returns: v.any(),
  handler: async (ctx, args) => {
    await ctx.db.patch(args.jobId, { status: "cancelled", updatedAt: Date.now() });
    return { ok: true };
  },
});
