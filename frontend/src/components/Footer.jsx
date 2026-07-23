/**
 * Footer
 *
 * Shared bottom bar for every screen. Static, presentational only — no
 * routing or backend behind the reference links, consistent with the
 * rest of this pass being visual-only.
 */
export default function Footer() {
  return (
    <footer className="border-t border-line mt-auto">
      <div className="max-w-6xl mx-auto px-6 py-6 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <p className="font-display text-sm font-semibold text-forest">
              FasalBima Pramaan
            </p>
            <p className="text-xs text-ink/70 mt-0.5">
              A guided assistant for filing individual PMFBY crop-damage
              claims in Kannada or English.
            </p>
          </div>

          <nav
            aria-label="Footer"
            className="flex items-center gap-5 text-xs font-medium text-ink/70"
          >
            <span className="hover:text-forest transition-colors cursor-default">
              About PMFBY
            </span>
            <span className="hover:text-forest transition-colors cursor-default">
              Help &amp; Support
            </span>
            <span className="hover:text-forest transition-colors cursor-default">
              EN / ಕನ್ನಡ
            </span>
          </nav>
        </div>

        <p className="text-[11px] text-ink/70 border-t border-line/70 pt-3">
          FasalBima Pramaan is an independent assistant tool built to help
          farmers prepare individual crop-damage claims under the Pradhan
          Mantri Fasal Bima Yojana. Your responses are used only to prepare
          your claim evidence.
        </p>
      </div>
    </footer>
  );
}
