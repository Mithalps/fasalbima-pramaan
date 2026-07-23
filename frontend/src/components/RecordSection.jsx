/**
 * RecordSection / RecordField
 *
 * The small building blocks used to lay out a claim's details as labeled
 * groups (Farmer, Crop, Damage, Location, Evidence...). Used on both the
 * Review step of the claim form and the View Claim page so a claim looks
 * identical wherever it's shown.
 */
export function RecordSection({ title, icon, children }) {
  return (
    <div>
      <h2 className="flex items-center gap-1.5 text-xs font-semibold tracking-widest text-soil uppercase mb-3">
        {icon}
        {title}
      </h2>
      <div className="flex flex-col gap-2">{children}</div>
    </div>
  );
}

export function RecordField({ label, value }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-sm text-ink/70">{label}</span>
      <span className="text-sm font-medium text-ink text-right">
        {value || "—"}
      </span>
    </div>
  );
}
