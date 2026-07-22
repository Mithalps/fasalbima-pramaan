import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getClaim } from "../api/claims";
import { extractErrorMessage } from "../api/client";
import { downloadClaimPdf } from "../api/pdf";
import Button from "../components/Button";

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

// Keyed by String(weather_verified) so the `null` case (weather validation
// not applicable / unavailable) has an explicit, distinct style rather than
// falling through to true/false styling.
const WEATHER_STATUS_CONFIG = {
  true: {
    label: "Verified",
    dotClass: "bg-forest",
    badgeClass: "bg-forest/10 text-forest border-forest/30",
  },
  false: {
    label: "Not Verified",
    dotClass: "bg-soil",
    badgeClass: "bg-wheat/20 text-soil border-wheat/40",
  },
  null: {
    label: "Not Applicable",
    dotClass: "bg-sky",
    badgeClass: "bg-sky/10 text-sky border-sky/30",
  },
};

const WEATHER_METRICS = [
  { key: "precipitation", label: "Rainfall (mm)" },
  { key: "temperature_max", label: "Maximum Temperature (°C)" },
  { key: "temperature_min", label: "Minimum Temperature (°C)" },
  { key: "windspeed", label: "Wind Speed (km/h)" },
];

export default function ViewClaimPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | not_found | error
  const [errorMessage, setErrorMessage] = useState("");
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [pdfError, setPdfError] = useState("");

  async function handleDownloadPdf() {
    setPdfDownloading(true);
    setPdfError("");
    try {
      await downloadClaimPdf(claimId);
    } catch (error) {
      setPdfError(extractErrorMessage(error));
    } finally {
      setPdfDownloading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function fetchClaim() {
      setStatus("loading");
      try {
        const data = await getClaim(claimId);
        if (cancelled) return;
        setClaim(data);
        setStatus("ready");
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
        <div className="max-w-2xl mx-auto flex flex-col gap-6">
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
            <>
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
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs font-semibold uppercase tracking-wide px-3 py-1.5 rounded-full border ${STATUS_STYLES[claim.status] ?? STATUS_STYLES.submitted}`}
                    >
                      {claim.status.replace("_", " ")}
                    </span>
                    <Button
                      variant="secondary"
                      onClick={handleDownloadPdf}
                      disabled={pdfDownloading}
                    >
                      {pdfDownloading ? "Preparing PDF…" : "Download Evidence Report"}
                    </Button>
                  </div>
                </div>

                {pdfError && (
                  <div className="px-6 sm:px-8 pt-4">
                    <p className="text-sm text-clay bg-clay/10 border border-clay/30 rounded-lg px-4 py-3">
                      {pdfError}
                    </p>
                  </div>
                )}

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

                <div className="px-6 sm:px-8 py-4 border-t border-line bg-paper/60 text-xs text-ink/50 flex flex-wrap justify-between gap-2">
                  <span>Filed on {new Date(claim.created_at).toLocaleString()}</span>
                  <span>Last updated {new Date(claim.updated_at).toLocaleString()}</span>
                </div>
              </div>

              <WeatherValidationCard claim={claim} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function WeatherValidationCard({ claim }) {
  const verified = claim.weather_verified ?? null;
  const weatherStatus =
    WEATHER_STATUS_CONFIG[String(verified)] ?? WEATHER_STATUS_CONFIG.null;

  const visibleMetrics = WEATHER_METRICS.filter(
    ({ key }) => claim[key] !== null && claim[key] !== undefined
  );

  return (
    <div className="bg-white border border-line rounded-2xl overflow-hidden shadow-sm">
      <div className="px-6 sm:px-8 py-6 border-b border-line flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-lg font-semibold text-ink">
          Weather Validation
        </h1>
        <span
          className={`inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide px-3 py-1.5 rounded-full border ${weatherStatus.badgeClass}`}
        >
          <span
            aria-hidden="true"
            className={`h-1.5 w-1.5 rounded-full ${weatherStatus.dotClass}`}
          />
          {weatherStatus.label}
        </span>
      </div>

      <div className="px-6 sm:px-8 py-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-6">
        <Section title="Result">
          <Field label="Validation status" value={weatherStatus.label} />
          {claim.weather_reason && (
            <Field label="Reason" value={claim.weather_reason} />
          )}
        </Section>

        {visibleMetrics.length > 0 && (
          <Section title="Recorded weather">
            {visibleMetrics.map(({ key, label }) => (
              <Field key={key} label={label} value={claim[key]} />
            ))}
          </Section>
        )}
      </div>
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