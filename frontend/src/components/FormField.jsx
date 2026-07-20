/**
 * FormField
 *
 * A labeled input (or select) with consistent styling and inline error
 * display. Every field in the claim form uses this so validation errors
 * always render the same way.
 */
export default function FormField({
  label,
  name,
  type = "text",
  value,
  onChange,
  error,
  placeholder,
  as = "input",
  options = [],
  required = true,
}) {
  const fieldId = `field-${name}`;

  const baseFieldClasses = `w-full rounded-lg border bg-white px-4 py-3 text-[15px] text-ink placeholder:text-ink/40 focus:outline-none focus:ring-2 focus:ring-forest/40 transition-colors ${
    error ? "border-clay" : "border-line focus:border-forest"
  }`;

  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={fieldId}
        className="text-sm font-medium text-ink/80 tracking-wide"
      >
        {label}
        {required && <span className="text-clay ml-0.5">*</span>}
      </label>

      {as === "select" ? (
        <select
          id={fieldId}
          name={name}
          value={value}
          onChange={onChange}
          className={baseFieldClasses}
        >
          <option value="" disabled>
            Select {label.toLowerCase()}
          </option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={fieldId}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={baseFieldClasses}
        />
      )}

      {error && (
        <p className="text-sm text-clay flex items-start gap-1">
          <span aria-hidden="true">⚠</span>
          <span>{error}</span>
        </p>
      )}
    </div>
  );
}
