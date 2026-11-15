import { sparklinePath } from "@/lib/trends";

export function Sparkline({
  values,
  color = "#b8d9f5",
  width = 64,
  height = 18,
}: {
  values: number[];
  color?: string;
  width?: number;
  height?: number;
}) {
  if (values.length < 2) {
    return (
      <svg width={width} height={height} className="sparkline">
        <line x1="0" y1={height / 2} x2={width} y2={height / 2} stroke="#587089" strokeDasharray="2 3" />
      </svg>
    );
  }
  const path = sparklinePath(values, width, height);
  const last = values[values.length - 1];
  const first = values[0];
  const rising = last >= first;
  const stroke = color === "auto" ? ((rising ? "#f5b84b" : "#5aa9ff") as string) : color;
  const clean = values.filter((value) => Number.isFinite(value));
  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const span = max - min || 1;
  const lastY = height - ((last - min) / span) * height;
  return (
    <svg width={width} height={height} className="sparkline" aria-hidden="true">
      <path d={path} fill="none" stroke={stroke} strokeWidth="1.3" opacity="0.9" />
      <circle cx={width} cy={lastY} r="1.8" fill={stroke} />
    </svg>
  );
}
