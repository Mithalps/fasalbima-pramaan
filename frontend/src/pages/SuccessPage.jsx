import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import Button from "../components/Button";
import { getClaim } from "../api/claims";

export default function SuccessPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();
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
          setLoadError("Claim saved, but we couldn't reload its details.");
        }
      }
    }

    fetchClaim();
    return () => {
      cancelled = true;
    };
  }, [claimId]);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-line bg-white">
        <div className="max-w-3xl mx-auto px-6 py-5">
          <Link
            to="/"
            className="font-display text-xl font-semibold text-forest"
          >
            FasalBima Pramaan
          </Link>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="max-w-md w-full bg-white border border-line rounded-2xl p-8 sm:p-10 shadow-sm text-center">
          <div className="mx-auto mb-6 flex flex-col items-center">
            {/* Signature element: a stamp-styled claim ID badge, evoking the
                physical acknowledgment slip a farmer would receive at a
                real PMFBY filing office. */}
            <div className="inline-flex flex-col items-center gap-1 rounded-full border-2 border-forest px-6 py-4 rotate-[-3deg]">
              <span className="text-[10px] font-semibold tracking-[0.2em] uppercase text-forest/70">
                Claim ID
              </span>
              <span className="font-mono text-sm sm:text-base font-semibold text-forest break-all">
                {claimId}
              </span>
            </div>
          </div>

          <h1 className="font-display text-2xl font-semibold text-ink mb-2">
            Claim submitted
          </h1>
          <p className="text-ink/70 leading-relaxed mb-2">
            {claim
              ? `Your claim for ${claim.farmer.farmer_name}'s ${claim.crop_type} crop has been recorded.`
              : "Your claim has been recorded."}
          </p>
          <p className="text-sm text-ink/50 mb-8">
            Save this Claim ID — you'll need it to check your claim later.
          </p>

          {loadError && (
            <p className="text-sm text-clay bg-clay/10 border border-clay/30 rounded-lg px-4 py-3 mb-6">
              {loadError}
            </p>
          )}

          <div className="flex flex-col gap-3">
            <Button fullWidth onClick={() => navigate(`/claims/${claimId}`)}>
              View claim details
            </Button>
            <Button
              fullWidth
              variant="secondary"
              onClick={() => navigate("/claims/new")}
            >
              File another claim
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
