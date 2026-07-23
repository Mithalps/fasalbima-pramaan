import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Button from "../components/Button";
import { getClaim } from "../api/claims";
import { CheckIcon, InfoIcon } from "../components/Icons";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { useLanguage } from "../context/LanguageContext";

export default function SuccessPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [claim, setClaim] = useState(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function fetchClaim() {
      try {
        const data = await getClaim(claimId);
        if (!cancelled) setClaim(data);
      } catch {
        // The claim was just created by this same flow, so a fetch failure
        // here is almost always a transient network hiccup, not a missing
        // claim — we still have the ID from the URL, so the page stays useful.
        if (!cancelled) {
          setLoadError(t("success.loadError"));
        }
      }
    }

    fetchClaim();
    return () => {
      cancelled = true;
    };
  }, [claimId, t]);

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="max-w-md w-full bg-white border border-line rounded-xl p-8 sm:p-10 shadow-[var(--shadow-card)] text-center">
          <div className="mx-auto mb-6 flex flex-col items-center gap-4">
            <span
              aria-hidden="true"
              className="flex h-11 w-11 items-center justify-center rounded-full bg-forest text-paper shadow-[var(--shadow-pop)]"
            >
              <CheckIcon className="h-5 w-5" />
            </span>

            {/* Signature element: a stamp-styled claim ID badge, evoking the
                physical acknowledgment slip a farmer would receive at a
                real PMFBY filing office. */}
            <div className="inline-flex flex-col items-center gap-1 rounded-full border-2 border-forest px-6 py-4 rotate-[-3deg] shadow-[var(--shadow-pop)]">
              <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-forest/70">
                {t("success.claimIdLabel")}
              </span>
              <span className="font-mono text-sm sm:text-base font-semibold text-forest break-all">
                {claimId}
              </span>
            </div>
          </div>

          <h1 className="font-display text-2xl font-semibold text-ink mb-2">
            {t("success.heading")}
          </h1>
          <p className="text-ink/70 leading-relaxed mb-6">
            {claim
              ? t("success.messageWithClaim", {
                  farmerName: claim.farmer.farmer_name,
                  cropType: claim.crop_type,
                })
              : t("success.messageWithoutClaim")}
          </p>

          <div className="flex items-start gap-2.5 text-left bg-wheat/10 border-l-4 border-wheat rounded-r-lg px-4 py-3 mb-8">
            <InfoIcon className="h-4 w-4 shrink-0 mt-0.5 text-soil" />
            <p className="text-sm text-ink/70">
              <span className="font-semibold text-ink">
                {t("success.importantPrefix")}{" "}
              </span>
              {t("success.importantBody")}
            </p>
          </div>

          {loadError && (
            <p className="text-sm text-clay bg-clay/10 border border-clay/30 rounded-lg px-4 py-3 mb-6">
              {loadError}
            </p>
          )}

          <div className="flex flex-col gap-3">
            <Button fullWidth onClick={() => navigate(`/claims/${claimId}`)}>
              {t("success.viewClaimButton")}
            </Button>
            <Button
              fullWidth
              variant="secondary"
              onClick={() => navigate("/claims/new")}
            >
              {t("success.fileAnotherButton")}
            </Button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
