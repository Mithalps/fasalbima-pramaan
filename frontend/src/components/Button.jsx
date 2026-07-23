/**
 * Button
 *
 * Every submit/navigation action in the claim flow uses this so loading
 * and disabled states look and behave consistently.
 */
export default function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  loading = false,
  disabled = false,
  fullWidth = false,
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 min-h-[44px] text-sm font-semibold tracking-wide whitespace-nowrap transition-all duration-150 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 disabled:cursor-not-allowed";

  const variants = {
    primary:
      "bg-forest text-paper shadow-[var(--shadow-pop)] hover:bg-forest-dark hover:shadow-[var(--shadow-card-hover)]",
    secondary:
      "bg-white text-ink border border-line hover:border-forest hover:text-forest hover:shadow-[var(--shadow-pop)]",
    danger:
      "bg-clay text-paper shadow-[var(--shadow-pop)] hover:bg-clay/90 hover:shadow-[var(--shadow-card-hover)]",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${fullWidth ? "w-full" : ""}`}
    >
      {loading && (
        <span
          className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin"
          aria-hidden="true"
        />
      )}
      {children}
    </button>
  );
}
