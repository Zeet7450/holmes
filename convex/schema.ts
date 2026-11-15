import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  cities: defineTable({
    id: v.string(),
    name: v.string(),
    country: v.string(),
    lat: v.number(),
    lon: v.number(),
    timezone: v.string(),
    population: v.number(),
    anchorRank: v.number(),
    region: v.string(),
    aliases: v.array(v.string()),
  }).index("by_slug", ["id"]),

  variables: defineTable({
    key: v.string(),
    sourceKey: v.string(),
    label: v.string(),
    code: v.string(),
    definition: v.string(),
    units: v.string(),
    nativeFrequency: v.union(v.literal("daily"), v.literal("monthly")),
    aggregation: v.union(v.literal("mean"), v.literal("sum")),
    coverageStart: v.string(),
    coverageEnd: v.string(),
    theme: v.string(),
    caveats: v.array(v.string()),
    resourcesTab: v.boolean(),
    sourceDetail: v.string(),
  }).index("by_key", ["key"]),

  cityTrends: defineTable({
    cityId: v.string(),
    records: v.any(),
    series: v.any(),
  }).index("by_city", ["cityId"]),

  cases: defineTable({
    slug: v.string(),
    title: v.string(),
    question: v.string(),
    placeId: v.string(),
    variableKeys: v.array(v.string()),
    windowId: v.string(),
    season: v.string(),
    narrative: v.string(),
    source: v.string(),
    sourcesTab: v.boolean(),
  }).index("by_slug", ["slug"]),

  fires: defineTable({
    snapshot: v.any(),
    pointChunks: v.array(v.any()),
    clusters: v.any(),
  }),

  analyses: defineTable({
    cacheKey: v.string(),
    cityId: v.string(),
    variableKey: v.string(),
    windowId: v.string(),
    season: v.string(),
    methodVersion: v.string(),
    result: v.any(),
    createdAt: v.number(),
  }).index("by_cache_key", ["cacheKey"]),

  jobs: defineTable({
    cacheKey: v.string(),
    status: v.union(
      v.literal("queued"),
      v.literal("running"),
      v.literal("succeeded"),
      v.literal("failed"),
      v.literal("cancelled"),
    ),
    stage: v.string(),
    done: v.number(),
    total: v.number(),
    error: v.optional(v.string()),
    createdAt: v.number(),
    updatedAt: v.number(),
  }).index("by_cache_key", ["cacheKey"]).index("by_status", ["status"]),

  threads: defineTable({
    sessionId: v.string(),
    question: v.string(),
    cityId: v.optional(v.string()),
    answer: v.any(),
    createdAt: v.number(),
  }).index("by_session", ["sessionId"]),
});
