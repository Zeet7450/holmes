import { useEffect, useMemo, useRef, useState } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import type { SeriesPoint, TrendRecord, Variable } from "@/lib/types";
import { annualize, deseasonalize, formatP, rollingMean } from "@/lib/trends";

type Mode = "raw" | "deseasonalized" | "annual";

export function EvidenceChart({
  points,
  record,
  variable,
}: {
  points: SeriesPoint[];
  record: TrendRecord | null;
  variable: Variable | undefined;
}) {
  const [mode, setMode] = useState<Mode>("raw");
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const plotRef = useRef<uPlot | null>(null);

  const displayPoints = useMemo(() => {
    if (mode === "annual") return annualize(points);
    if (mode === "deseasonalized") return deseasonalize(points);
    return points;
  }, [points, mode]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || displayPoints.length < 2) return;
    const width = Math.max(260, container.clientWidth);
    const xs = displayPoints.map((point) => point.t);
    const values = displayPoints.map((point) => point.value);
    const rolling = rollingMean(displayPoints, mode === "annual" ? 3 : 12);
    const meanY = values.reduce((sum: number, value) => sum + (value ?? 0), 0) / Math.max(1, values.filter((v) => v !== null).length);
    const slopePerYear = record?.slope ? record.slope / 10 : 0;
    const meanX = xs.reduce((a, b) => a + b, 0) / xs.length;
    const trend = record?.status === "ok" && record.slope !== null ? xs.map((x) => meanY + slopePerYear * (x - meanX)) : xs.map(() => null);
    const ciLow = record?.ci
      ? xs.map((x) => meanY + (record.ci![0] / 10) * (x - meanX))
      : xs.map(() => null);
    const ciHigh = record?.ci
      ? xs.map((x) => meanY + (record.ci![1] / 10) * (x - meanX))
      : xs.map(() => null);

    const data: uPlot.AlignedData = [xs, values, rolling, trend, ciLow, ciHigh];
    const options: uPlot.Options = {
      width,
      height: 178,
      padding: [8, 8, 0, 0],
      legend: { show: false },
      cursor: {
        show: true,
        x: true,
        y: false,
        points: { show: true, size: 4, fill: "#b8d9f5", stroke: "#b8d9f5" },
      },
      scales: { x: { time: false }, y: { range: (_u, _min, max) => [Math.min(_min, 0) === 0 ? _min : _min, max] } },
      axes: [
        {
          stroke: "#587089",
          grid: { stroke: "rgba(77,149,216,0.06)", width: 1 },
          ticks: { stroke: "rgba(77,149,216,0.12)", width: 1, size: 3 },
          font: "9px 'JetBrains Mono', monospace",
          values: (_u, vals) => vals.map((value) => String(Math.round(value))),
          size: 22,
        },
        {
          stroke: "#587089",
          grid: { stroke: "rgba(77,149,216,0.06)", width: 1 },
          ticks: { stroke: "rgba(77,149,216,0.12)", width: 1, size: 3 },
          font: "9px 'JetBrains Mono', monospace",
          size: 52,
          values: (_u, vals) => vals.map((value) => value.toFixed(Math.abs(value) < 1 ? 2 : 1)),
        },
      ],
      series: [
        {},
        { label: "RAW", stroke: "#aac3da", width: 1, spanGaps: false, points: { show: false } },
        { label: "ROLLING", stroke: "#e2eefb", width: 1.7, spanGaps: true },
        { label: "TREND", stroke: "#b8d9f5", width: 1.4, dash: [5, 4], spanGaps: true },
        { label: "CI LOW", stroke: "rgba(77,149,216,0)", width: 0, spanGaps: true },
        { label: "CI HIGH", stroke: "rgba(77,149,216,0)", width: 0, spanGaps: true },
      ],
      bands: [{ series: [5, 4], fill: "rgba(77,149,216,0.16)" }],
      hooks: {
        setCursor: [
          (u) => {
            const idx = u.cursor.idx;
            const tooltip = tooltipRef.current;
            if (!tooltip) return;
            if (idx === null || idx === undefined) {
              tooltip.style.opacity = "0";
              return;
            }
            const x = xs[idx];
            const y = values[idx];
            if (y === null || y === undefined) {
              tooltip.style.opacity = "0";
              return;
            }
            const year = Math.floor(x);
            const month = Math.min(12, Math.max(1, Math.round((x - year) * 12) + 1));
            tooltip.innerHTML = `${String(year)}-${String(month).padStart(2, "0")} · ${y.toFixed(2)} ${variable?.units ?? ""}<br/><span style="color:#aac3da">rolling ${rolling[idx]?.toFixed(2) ?? "—"} · ${mode.toUpperCase()}</span>`;
            tooltip.style.opacity = "1";
            const left = Math.min(width - 150, Math.max(0, u.cursor.left ?? 0));
            tooltip.style.left = `${left + 10}px`;
            tooltip.style.top = "6px";
          },
        ],
      },
    };
    const plot = new uPlot(options, data, container);
    plotRef.current = plot;
    const observer = new ResizeObserver((entries) => {
      const nextWidth = entries[0]?.contentRect.width;
      if (nextWidth && nextWidth > 100) plot.setSize({ width: nextWidth, height: 178 });
    });
    observer.observe(container);
    return () => {
      observer.disconnect();
      plot.destroy();
      plotRef.current = null;
    };
  }, [displayPoints, record, variable, mode]);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex gap-1">
          {(["raw", "deseasonalized", "annual"] as Mode[]).map((item) => (
            <button
              key={item}
              className={`seg-btn ${mode === item ? "seg-btn--on" : ""}`}
              onClick={() => setMode(item)}
            >
              {item === "deseasonalized" ? "DESEASON." : item.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="font-mono text-[8px] text-[var(--text-muted)]">{variable?.units}</div>
      </div>
      <div className="chart-wrap">
        <div ref={containerRef} className="w-full" />
        <div ref={tooltipRef} className="chart-tooltip" />
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 font-mono text-[8px] text-[var(--text-muted)]">
        <span>{record ? `${record.n} months · ${record.nYears} years · ${record.coverage ? `${Math.round(record.coverage * 100)}% complete` : ""}` : "No trend result"}</span>
        <span>{record ? formatP(record.p) : ""} · {record?.methodDependent ? "METHOD-DEPENDENT" : "SEN + MANN–KENDALL"}</span>
      </div>
      {!record || record.status !== "ok" ? (
        <div className="mt-2 rounded border border-[rgba(245,184,75,0.2)] bg-[rgba(245,184,75,0.05)] p-2 text-[10px] leading-relaxed text-[var(--text-dim)]">
          Not enough data for a trend in this window. The series is still shown; gaps are gaps, not zeros.
        </div>
      ) : null}
    </div>
  );
}
