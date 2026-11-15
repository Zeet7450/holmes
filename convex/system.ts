import { v } from "convex/values";
import { query } from "./_generated/server";

export const health = query({
  args: {},
  returns: v.any(),
  handler: async (ctx) => {
    const [cities, variables, cases, fires, analyses] = await Promise.all([
      ctx.db.query("cities").take(1000),
      ctx.db.query("variables").take(100),
      ctx.db.query("cases").take(100),
      ctx.db.query("fires").take(10),
      ctx.db.query("analyses").take(100),
    ]);
    return {
      status: "ok",
      mode: "cached",
      cities: cities.length,
      variables: variables.length,
      citySeries: cities.length,
      cases: cases.length,
      fireSnapshots: fires.length,
      analyses: analyses.length,
      methodVersion: "1.0.0",
    };
  },
});
