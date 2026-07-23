/**
 * StepTabs
 *
 * The claim form's signature visual: tab dividers styled like a physical
 * filing ledger, one tab per step. This encodes real information — the
 * fixed order of the actual PMFBY claim form — rather than decorating
 * an otherwise plain multi-step form.
 */
import { CheckIcon } from "./Icons";

export default function StepTabs({ steps, currentIndex }) {
  return (
    <div className="flex border-b border-line">
      {steps.map((step, index) => {
        const isActive = index === currentIndex;
        const isComplete = index < currentIndex;

        return (
          <div
            key={step.key}
            className={`relative flex-1 px-3 py-3 sm:px-5 sm:py-4 border-r border-line last:border-r-0 transition-colors duration-200 ${
              isActive ? "bg-white" : "bg-paper-raised/60"
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`flex h-5 w-5 sm:h-6 sm:w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold font-mono transition-colors duration-200 ${
                  isComplete
                    ? "bg-forest text-paper"
                    : isActive
                    ? "bg-wheat text-ink"
                    : "bg-line text-ink/70"
                }`}
              >
                {isComplete ? <CheckIcon className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> : index + 1}
              </span>
              <span
                className={`text-xs sm:text-sm font-medium truncate transition-colors duration-200 ${
                  isActive ? "text-ink" : "text-ink/70"
                }`}
              >
                {step.label}
              </span>
            </div>

            {isActive && (
              <span className="absolute inset-x-0 -bottom-px h-[3px] bg-forest" />
            )}
          </div>
        );
      })}
    </div>
  );
}
