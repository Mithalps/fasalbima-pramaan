import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getClaim } from "../api/claims";
import { extractErrorMessage } from "../api/client";
import { downloadClaimPdf } from "../api/pdf";
import Button from "../components/Button";
import { RecordSection, RecordField } from "../components/RecordSection";
import { UserIcon, LeafIcon, WarningIcon, PinIcon, CloudIcon } from "../components/Icons";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { useLanguage } from "../context/LanguageContext";

// Masks all but the last 4 digits, e.g. "123456789012" -> "XXXX XXXX 9012".
// The API returns the full value (masking is a presentation-layer concern),
// so every screen that displays it masks it locally before rendering.
function maskAadhaar(value) {
  const digits = (value || "").replace(/\s/g, "");
  if (digits.length < 4) return "XXXX XXXX XXXX";
  return `XXXX XXXX ${digits.slice(-4)}`;
}

const STATUS_STYLES = {
  submitted: "bg-wheat/20 text-soil border-wheat/40",
  under_review: "bg-olive/10 text-olive-dark border-olive/30",
  evidence_ready: "bg-forest/10 text-forest border-forest/30",
  closed: "bg-line text-ink/70 border-line",
};

// Keyed by String(weather_verified) so the `null` case (weather validation
// not applicable / unavailable) has an explicit, distinct style rather than
// falling through to true/false styling. Labels come from t() at render
// time since they're translated UI copy, not fixed style tokens.
const WEATHER_STATUS_STYLE = {
  true: { dotClass: "bg-forest", badgeClass: "bg-forest/10 text-forest border-forest/30" },
  false: { dotClass: "bg-soil", badgeClass: "bg-wheat/20 text-soil border-wheat/40" },
  null: { dotClass: "bg-sky", badgeClass: "bg-sky/10 text-sky border-sky/30" },
};

export default function ViewClaimPage() {
  const { claimId } = useParams();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [claim, setClaim] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | not_found | error
  const [errorMessage, setErrorMessage] = useState("");
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [pdfError, setPdfError] = useState("");

  const DAMAGE_TYPE_LABELS = {
    flood: t("damageTypes.flood"),
    drought: t("damageTypes.drought"),
    hailstorm: t("damageTypes.hailstorm"),
    pest_attack: t("damageTypes.pest_attack"),
    other: t("damageTypes.other"),
  };

  const STATUS_LABELS = {
    submitted: t("claimStatuses.submitted"),
    under_review: t("claimStatuses.under_review"),
    evidence_ready: t("claimStatuses.evidence_ready"),
    closed: t("claimStatuses.closed"),
  };

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
      <Header contextLabel={t("header.contextClaimRecord")} />

      <main className="flex-1 px-6 py-10">
        <div className="max-w-4xl mx-auto flex flex-col gap-6">
          {status === "loading" && (
            <div className="bg-white border border-line rounded-xl p-10 flex items-center justify-center gap-3 text-ink/70 shadow-[var(--shadow-card)]">
              <span className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
              {t("viewClaim.loading")}
            </div>
          )}

          {status === "not_found" && (
            <div className="bg-white border border-line rounded-xl p-10 text-center shadow-[var(--shadow-card)]">
              <h1 className="font-display text-xl font-semibold text-ink mb-2">
                {t("viewClaim.notFoundHeading")}
              </h1>
              <p className="text-ink/70 mb-6">
                {t("viewClaim.notFoundBody")}
              </p>
              <button
                onClick={() => navigate("/")}
                className="text-forest font-medium hover:underline"
              >
                {t("viewClaim.backHome")}
              </button>
            </div>
          )}

          {status === "error" && (
            <div className="bg-white border border-line rounded-xl p-10 text-center shadow-[var(--shadow-card)]">
              <h1 className="font-display text-xl font-semibold text-ink mb-2">
                {t("viewClaim.errorHeading")}
              </h1>
              <p className="text-clay mb-6">{errorMessage}</p>
              <button
                onClick={() => window.location.reload()}
                className="text-forest font-medium hover:underline"
              >
                {t("viewClaim.tryAgain")}
              </button>
            </div>
          )}

          {status === "ready" && claim && (
            <>
              <div className="bg-white border border-line rounded-xl overflow-hidden shadow-[var(--shadow-card)]">
                <div className="px-6 sm:px-8 py-6 border-b border-line flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold tracking-widest text-soil uppercase mb-1">
                      {t("viewClaim.claimIdLabel")}
                    </p>
                    <p className="font-mono text-sm text-ink break-all">
                      {claim.claim_id}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs font-semibold uppercase tracking-wide px-3 py-1.5 rounded-full border ${STATUS_STYLES[claim.status] ?? STATUS_STYLES.submitted}`}
                    >
                      {STATUS_LABELS[claim.status] ?? claim.status.replace("_", " ")}
                    </span>
                    <Button
                      variant="secondary"
                      onClick={handleDownloadPdf}
                      disabled={pdfDownloading}
                    >
                      {pdfDownloading ? t("viewClaim.preparingPdf") : t("viewClaim.downloadPdf")}
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
                  <RecordSection title={t("sections.farmer")} icon={<UserIcon className="h-3.5 w-3.5" />}>
                    <RecordField label={t("recordLabels.name")} value={claim.farmer.farmer_name} />
                    <RecordField label={t("recordLabels.mobileNumber")} value={claim.farmer.mobile_number} />
                    {claim.farmer.aadhaar_number && (
                      <RecordField
                        label={t("recordLabels.aadhaarNumber")}
                        value={maskAadhaar(claim.farmer.aadhaar_number)}
                      />
                    )}
                  </RecordSection>

                  <RecordSection title={t("sections.crop")} icon={<LeafIcon className="h-3.5 w-3.5" />}>
                    <RecordField label={t("recordLabels.cropType")} value={claim.crop_type} />
                  </RecordSection>

                  <RecordSection title={t("sections.damage")} icon={<WarningIcon className="h-3.5 w-3.5" />}>
                    <RecordField
                      label={t("recordLabels.type")}
                      value={DAMAGE_TYPE_LABELS[claim.damage_type] ?? claim.damage_type}
                    />
                    <RecordField label={t("recordLabels.date")} value={claim.damage_date} />
                  </RecordSection>

                  <RecordSection title={t("sections.location")} icon={<PinIcon className="h-3.5 w-3.5" />}>
                    <RecordField label={t("recordLabels.district")} value={claim.district} />
                    <RecordField label={t("recordLabels.village")} value={claim.village} />
                  </RecordSection>
                </div>

                <div className="px-6 sm:px-8 py-4 border-t border-line bg-paper/60 text-xs text-ink/70 flex flex-wrap justify-between gap-2">
                  <span>{t("viewClaim.filedOn", { date: new Date(claim.created_at).toLocaleString() })}</span>
                  <span>{t("viewClaim.lastUpdated", { date: new Date(claim.updated_at).toLocaleString() })}</span>
                </div>
              </div>

              <WeatherValidationCard claim={claim} />
            </>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}

function WeatherValidationCard({ claim }) {
  const { t } = useLanguage();

  const WEATHER_STATUS_LABEL = {
    true: t("viewClaim.weatherVerified"),
    false: t("viewClaim.weatherNotVerified"),
    null: t("viewClaim.weatherNotApplicable"),
  };

  const WEATHER_METRICS = [
    { key: "precipitation", label: t("viewClaim.rainfall") },
    { key: "temperature_max", label: t("viewClaim.tempMax") },
    { key: "temperature_min", label: t("viewClaim.tempMin") },
    { key: "windspeed", label: t("viewClaim.windSpeed") },
  ];

  const verified = claim.weather_verified ?? null;
  const key = String(verified);
  const style = WEATHER_STATUS_STYLE[key] ?? WEATHER_STATUS_STYLE.null;
  const label = WEATHER_STATUS_LABEL[key] ?? WEATHER_STATUS_LABEL.null;

  const visibleMetrics = WEATHER_METRICS.filter(
    ({ key }) => claim[key] !== null && claim[key] !== undefined
  );

  return (
    <div className="bg-white border border-line rounded-xl overflow-hidden shadow-[var(--shadow-card)]">
      <div className="px-6 sm:px-8 py-6 border-b border-line flex flex-wrap items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 font-display text-lg font-semibold text-ink">
          <CloudIcon className="h-4 w-4 text-sky" />
          {t("viewClaim.weatherValidationHeading")}
        </h1>
        <span
          className={`inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide px-3 py-1.5 rounded-full border ${style.badgeClass}`}
        >
          <span
            aria-hidden="true"
            className={`h-1.5 w-1.5 rounded-full ${style.dotClass}`}
          />
          {label}
        </span>
      </div>

      <div className="px-6 sm:px-8 py-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-6">
        <RecordSection title={t("sections.result")}>
          <RecordField label={t("recordLabels.validationStatus")} value={label} />
          {claim.weather_reason && (
            <RecordField label={t("recordLabels.reason")} value={claim.weather_reason} />
          )}
        </RecordSection>

        {visibleMetrics.length > 0 && (
          <RecordSection title={t("sections.recordedWeather")}>
            {visibleMetrics.map(({ key, label }) => (
              <RecordField key={key} label={label} value={claim[key]} />
            ))}
          </RecordSection>
        )}
      </div>
    </div>
  );
}
