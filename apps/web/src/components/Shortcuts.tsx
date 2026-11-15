import { X } from "lucide-react";

const SHORTCUTS = [
  ["/", "Focus city search"],
  ["↑ / ↓", "Move through city results"],
  ["Enter", "Open the highlighted city"],
  ["Esc", "Close search or overlays"],
  ["?", "Open this shortcut sheet"],
  ["F", "Toggle the fire watch layer"],
  ["E", "Switch to the Evidence Lens"],
  ["1 / 2 / 3 / 4", "Effect / Evidence / Agreement / Coverage"],
  ["M", "Open methods and limitations"],
];

export function Shortcuts({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card glass-panel p-5 !w-[min(520px,92vw)]" onClick={(event) => event.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <div className="hud-title text-base">KEYBOARD SHORTCUTS</div>
            <div className="hud-label mt-1">THE BOARD IS KEYBOARD REACHABLE</div>
          </div>
          <button className="btn-hud" onClick={onClose}><X size={13} /></button>
        </div>
        <div className="grid gap-2">
          {SHORTCUTS.map(([key, label]) => (
            <div key={key} className="flex items-center justify-between gap-4 border-b border-[rgba(77,149,216,0.06)] pb-1.5">
              <span className="text-[12px] text-[var(--text-dim)]">{label}</span>
              <span className="kbd">{key}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
