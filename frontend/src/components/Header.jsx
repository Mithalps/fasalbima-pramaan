import { Link } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";

const UI_LANGUAGES = [
  { value: "en", label: "EN" },
  { value: "kn", label: "ಕನ್ನಡ" },
];

/**
 * Header
 *
 * Shared top bar for every screen in the app. Keeps the brand mark,
 * product tag, and interface-language toggle identical everywhere so the
 * claim flow reads as one product rather than four different screens.
 *
 * `contextLabel` is the small uppercase tag next to the wordmark (e.g.
 * "New Claim", "Claim Record"). `stepInfo` is optional right-aligned text
 * (used by the claim form for "Step X of Y").
 *
 * The language toggle drives the app-wide LanguageContext: selecting
 * ಕನ್ನಡ / EN re-renders every page and component that reads t() with the
 * new language's copy, without a page reload.
 */
export default function Header({ contextLabel, stepInfo }) {
  const { language, setLanguage, t } = useLanguage();

  return (
    <header className="border-b border-line bg-white">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-baseline gap-3 min-w-0">
          <span
            aria-hidden="true"
            className="hidden sm:flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-forest text-forest font-display text-sm font-semibold"
          >
            फ
          </span>
          <span className="font-display text-xl font-semibold text-forest whitespace-nowrap">
            FasalBima Pramaan
          </span>
          {contextLabel && (
            <span className="hidden md:inline text-xs text-ink/70 font-semibold tracking-wide uppercase whitespace-nowrap">
              {contextLabel}
            </span>
          )}
        </Link>

        <div className="flex items-center gap-4 shrink-0">
          {stepInfo && (
            <span className="hidden sm:inline text-xs font-medium text-ink/70 font-mono tabular-nums whitespace-nowrap">
              {stepInfo}
            </span>
          )}

          <div
            role="group"
            aria-label="Interface language"
            className="inline-flex items-center rounded-xl border border-line bg-paper-raised/60 p-0.5"
          >
            {UI_LANGUAGES.map((lang) => (
              <button
                key={lang.value}
                type="button"
                onClick={() => setLanguage(lang.value)}
                aria-pressed={language === lang.value}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-colors duration-150 ${
                  language === lang.value
                    ? "bg-forest text-paper"
                    : "text-ink/70 hover:text-ink"
                }`}
              >
                {lang.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="border-t border-line/70 bg-paper-raised/50">
        <div className="max-w-6xl mx-auto px-6 py-1.5">
          <p className="text-[11px] font-semibold tracking-widest text-ink/70 uppercase">
            {t("common.claimAssistantTag")}
          </p>
        </div>
      </div>
    </header>
  );
}
