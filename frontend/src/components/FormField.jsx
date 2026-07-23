import { WarningIcon } from "./Icons";
import { useLanguage } from "../context/LanguageContext";

/**
 * FormField
 *
 * A labeled input (or select) with consistent styling and inline error
 * display. Every field in the claim form uses this so validation errors
 * always render the same way.
 *
 * `label`, `placeholder`, and `error` are expected to already be
 * translated strings (the caller resolves them via t()) — this component
 * only needs t() itself for the generic "Select {label}" placeholder
 * option text.
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
  const { t } = useLanguage();
  const fieldId = `field-${name}`;

  const baseFieldClasses = `w-full min-h-[44px] rounded-xl border bg-white px-4 py-3 text-[15px] text-ink placeholder:text-ink/70 shadow-[inset_0_1px_2px_rgba(34,48,31,0.04)] focus:ring-2 focus:ring-forest/30 transition-colors ${
    error
      ? "border-clay"
      : "border-line hover:border-ink/25 focus:border-forest"
  }`;

  return (
    <div className="flex flex-col gap-2">
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
            {t("formField.selectPrefix")} {label}
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
        <p className="text-sm text-clay flex items-start gap-1.5">
          <WarningIcon className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </p>
      )}
    </div>
  );
}
