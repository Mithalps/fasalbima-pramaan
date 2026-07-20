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
    "inline-flex items-center justify-center gap-2 rounded-lg px-5 py-3 text-sm font-semibold tracking-wide transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";

  const variants = {
    primary:
      "bg-forest text-paper hover:bg-forest-dark focus:ring-forest",
    secondary:
      "bg-white text-ink border border-line hover:border-forest hover:text-forest focus:ring-forest",
    danger: "bg-clay text-paper hover:bg-clay/90 focus:ring-clay",
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
