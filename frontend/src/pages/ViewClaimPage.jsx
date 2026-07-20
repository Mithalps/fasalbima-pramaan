import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getClaim } from "../api/claims";
import { listEvidence } from "../api/evidence";
import { extractErrorMessage } from "../api/client";

const DAMAGE_TYPE_LABELS = {
  flood: "Flood",
  drought: "Drought",
  hailstorm: "Hailstorm",
  pest_attack: "Pest Attack",
  other: "Other",
};

const STATUS_STYLES = {
  submitted: "bg-wheat/20 text-soil border-wheat/40",
  under_review: "bg-forest/10 text-forest border-forest/30",
  evidence_ready: "bg-forest/10 text-forest border-forest/30",
  closed: "bg-line text-ink/50 border-line",
};

export default function ViewClaimPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | not_found | error
  const [errorMessage, setErrorMessage] = useState("");
  const [evidenceItems, setEvidenceItems] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function fetchClaim() {
      setStatus("loading");
      try {
        const data = await getClaim(claimId);
        if (cancelled) return;
        setClaim(data);
        setStatus("ready");

        // Evidence is fetched separately and best-effort: a farmer should
        // still see their claim details even if this call fails.
        try {
          const evidence = await listEvidence(claimId);
          if (!cancelled) setEvidenceItems(evidence);
        } catch {
          // Silently ignored — the Evidence section just shows as empty.
        }
      } catch (error) {
        if (cancelled) return;
        if (error.response?.status === 404) {
          setStatus("not_found");
        } else {
          setErrorMessage(extractErrorMessage(error));
          setStatus("error");
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

      <main className="flex-1 px-6 py-10">
        <div className="max-w-2xl mx-auto">
          {status === "loading" && (
            <div className="bg-white border border-line rounded-2xl p-10 flex items-center justify-center gap-3 text-ink/60">
              <span className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
              Loading claim…
            </div>
          )}

          {status === "not_found" && (
            <div className="bg-white border border-line rounded-2xl p-10 text-center">
              <h1 className="font-display text-xl font-semibold text-ink mb-2">
                No claim found for this ID
              </h1>
              <p className="text-ink/60 mb-6">
                Double-check the Claim ID and try again.
              </p>
              <button
                onClick={() => navigate("/")}
                className="text-forest font-medium hover:underline"
              >
                ← Back to home
              </button>
            </div>
          )}

          {status === "error" && (
            <div className="bg-white border border-line rounded-2xl p-10 text-center">
              <h1 className="font-display text-xl font-semibold text-ink mb-2">
                Couldn't load this claim
              </h1>
              <p className="text-clay mb-6">{errorMessage}</p>
              <button
                onClick={() => window.location.reload()}
                className="text-forest font-medium hover:underline"
              >
                Try again
              </button>
            </div>
          )}

          {status === "ready" && claim && (
            <div className="bg-white border border-line rounded-2xl overflow-hidden shadow-sm">
              <div className="px-6 sm:px-8 py-6 border-b border-line flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold tracking-widest text-soil uppercase mb-1">
                    Claim ID
                  </p>
                  <p className="font-mono text-sm text-ink break-all">
                    {claim.claim_id}
                  </p>
                </div>
                <span
                  className={`text-xs font-semibold uppercase tracking-wide px-3 py-1.5 rounded-full border ${STATUS_STYLES[claim.status] ?? STATUS_STYLES.submitted}`}
                >
                  {claim.status.replace("_", " ")}
                </span>
              </div>

              <div className="px-6 sm:px-8 py-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-6">
                <Section title="Farmer">
                  <Field label="Name" value={claim.farmer.farmer_name} />
                  <Field label="Mobile number" value={claim.farmer.mobile_number} />
                </Section>

                <Section title="Crop">
                  <Field label="Crop type" value={claim.crop_type} />
                </Section>

                <Section title="Damage">
                  <Field
                    label="Type"
                    value={DAMAGE_TYPE_LABELS[claim.damage_type] ?? claim.damage_type}
                  />
                  <Field label="Date" value={claim.damage_date} />
                </Section>

                <Section title="Location">
                  <Field label="District" value={claim.district} />
                  <Field label="Village" value={claim.village} />
                </Section>
              </div>

              {evidenceItems.length > 0 && (
                <div className="px-6 sm:px-8 pb-6">
                  <h2 className="text-xs font-semibold tracking-widest text-soil uppercase mb-3">
                    Evidence ({evidenceItems.length})
                  </h2>
                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
                    {evidenceItems.map((item) => (
                      <a
                        key={item.id}
                        href={item.file_url}
                        target="_blank"
                        rel="noreferrer"
                        className="aspect-square rounded-lg overflow-hidden border border-line bg-white block"
                      >
                        <img
                          src={item.file_url}
                          alt={item.file_name}
                          className="w-full h-full object-cover"
                        />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              <div className="px-6 sm:px-8 py-4 border-t border-line bg-paper/60 text-xs text-ink/50 flex flex-wrap justify-between gap-2">
                <span>Filed on {new Date(claim.created_at).toLocaleString()}</span>
                <span>Last updated {new Date(claim.updated_at).toLocaleString()}</span>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <h2 className="text-xs font-semibold tracking-widest text-soil uppercase mb-3">
        {title}
      </h2>
      <div className="flex flex-col gap-2">{children}</div>
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-sm text-ink/60">{label}</span>
      <span className="text-sm font-medium text-ink text-right">{value}</span>
    </div>
  );
}
