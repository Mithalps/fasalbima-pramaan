import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { ClockIcon, MicIcon, DocumentIcon } from "../components/Icons";
import { useLanguage } from "../context/LanguageContext";

export default function LandingPage() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [lookupId, setLookupId] = useState("");
  const [lookupError, setLookupError] = useState("");

  const TRUST_POINTS = [
    {
      title: t("landing.trustPoint1Title"),
      body: t("landing.trustPoint1Body"),
      icon: ClockIcon,
    },
    {
      title: t("landing.trustPoint2Title"),
      body: t("landing.trustPoint2Body"),
      icon: MicIcon,
    },
    {
      title: t("landing.trustPoint3Title"),
      body: t("landing.trustPoint3Body"),
      icon: DocumentIcon,
    },
  ];

  const HOW_IT_WORKS = [
    { step: "1", title: t("landing.step1Title"), body: t("landing.step1Body") },
    { step: "2", title: t("landing.step2Title"), body: t("landing.step2Body") },
    { step: "3", title: t("landing.step3Title"), body: t("landing.step3Body") },
  ];

  function handleViewClaim(event) {
    event.preventDefault();
    const trimmed = lookupId.trim();
    if (!trimmed) {
      setLookupError(t("landing.lookupErrorEmpty"));
      return;
    }
    setLookupError("");
    navigate(`/claims/${trimmed}`);
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 px-6 py-14 sm:py-20">
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] gap-12 lg:gap-16 items-center">
          <div>
            <p className="text-xs font-semibold tracking-widest text-soil uppercase mb-3">
              {t("landing.eyebrow")}
            </p>
            <h2 className="font-display text-4xl sm:text-[2.75rem] leading-[1.1] font-semibold text-ink mb-5">
              {t("landing.heroTitle")}
            </h2>
            <p className="text-ink/70 text-lg leading-relaxed max-w-md mb-8">
              {t("landing.heroBody")}
            </p>

            <ul className="flex flex-col gap-4 max-w-md">
              {TRUST_POINTS.map((point) => (
                <li key={point.title} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-forest/10 text-forest">
                    <point.icon className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-ink">
                      {point.title}
                    </p>
                    <p className="text-sm text-ink/70 leading-snug">
                      {point.body}
                    </p>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-8 pt-6 border-t border-line max-w-md">
              <p className="text-xs text-ink/70 leading-relaxed">
                {t("landing.pmfbyNote")}
              </p>
            </div>
          </div>

          <div className="bg-white border border-line rounded-xl p-8 sm:p-10 shadow-[var(--shadow-card)]">
            <h3 className="font-display text-xl font-semibold text-ink mb-1">
              {t("landing.startCardTitle")}
            </h3>
            <p className="text-sm text-ink/70 mb-6">
              {t("landing.startCardBody")}
            </p>

            <Button fullWidth onClick={() => navigate("/claims/new")}>
              {t("landing.startButton")}
            </Button>

            <div className="mt-8 pt-6 border-t border-line">
              <form onSubmit={handleViewClaim} className="flex flex-col gap-2">
                <label
                  htmlFor="lookup-id"
                  className="text-sm font-medium text-ink/70"
                >
                  {t("landing.lookupLabel")}
                </label>
                <div className="flex gap-2">
                  <input
                    id="lookup-id"
                    type="text"
                    value={lookupId}
                    onChange={(event) => setLookupId(event.target.value)}
                    placeholder={t("landing.lookupPlaceholder")}
                    className="flex-1 min-w-0 min-h-[44px] rounded-xl border border-line bg-white px-4 py-2.5 text-sm font-mono text-ink placeholder:text-ink/60 placeholder:font-body shadow-[inset_0_1px_2px_rgba(34,48,31,0.04)] hover:border-ink/25 focus:border-forest focus:ring-2 focus:ring-forest/30 transition-colors"
                  />
                  <Button type="submit" variant="secondary">
                    {t("landing.lookupButton")}
                  </Button>
                </div>
                {lookupError && (
                  <p className="text-sm text-clay">{lookupError}</p>
                )}
              </form>
            </div>
          </div>
        </div>

        <div className="max-w-6xl mx-auto mt-16 sm:mt-24">
          <p className="text-xs font-semibold tracking-widest text-soil uppercase mb-6">
            {t("landing.howItWorksEyebrow")}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {HOW_IT_WORKS.map((item) => (
              <div
                key={item.step}
                className="bg-white border border-line rounded-xl p-6 shadow-[var(--shadow-card)]"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-forest text-paper text-xs font-semibold font-mono mb-4">
                  {item.step}
                </span>
                <p className="text-sm font-semibold text-ink mb-1">
                  {item.title}
                </p>
                <p className="text-sm text-ink/70 leading-snug">
                  {item.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
