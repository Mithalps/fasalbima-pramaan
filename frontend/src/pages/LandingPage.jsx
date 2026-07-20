import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";

export default function LandingPage() {
  const navigate = useNavigate();
  const [lookupId, setLookupId] = useState("");
  const [lookupError, setLookupError] = useState("");

  function handleViewClaim(event) {
    event.preventDefault();
    const trimmed = lookupId.trim();
    if (!trimmed) {
      setLookupError("Enter a claim ID first.");
      return;
    }
    setLookupError("");
    navigate(`/claims/${trimmed}`);
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-line bg-white">
        <div className="max-w-3xl mx-auto px-6 py-5 flex items-baseline gap-3">
          <h1 className="font-display text-2xl font-semibold text-forest">
            FasalBima Pramaan
          </h1>
          <span className="text-xs text-ink/50 font-medium tracking-wide uppercase">
            PMFBY Claim Assistant
          </span>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="max-w-lg w-full">
          <div className="bg-white border border-line rounded-2xl p-8 sm:p-10 shadow-sm">
            <p className="text-xs font-semibold tracking-widest text-soil uppercase mb-3">
              Individual crop-damage claim
            </p>
            <h2 className="font-display text-3xl font-semibold text-ink leading-tight mb-4">
              Report crop damage in your own words
            </h2>
            <p className="text-ink/70 leading-relaxed mb-8">
              File your PMFBY individual claim without waiting for the
              village survey. Answer a few guided questions about your
              farmer, crop, and damage details, and we'll assemble the
              evidence in a form your insurer accepts.
            </p>

            <Button fullWidth onClick={() => navigate("/claims/new")}>
              Start New Claim →
            </Button>

            <div className="mt-8 pt-6 border-t border-line">
              <form onSubmit={handleViewClaim} className="flex flex-col gap-2">
                <label
                  htmlFor="lookup-id"
                  className="text-sm font-medium text-ink/70"
                >
                  Already have a claim ID?
                </label>
                <div className="flex gap-2">
                  <input
                    id="lookup-id"
                    type="text"
                    value={lookupId}
                    onChange={(event) => setLookupId(event.target.value)}
                    placeholder="Paste your claim ID"
                    className="flex-1 rounded-lg border border-line bg-white px-4 py-2.5 text-sm font-mono text-ink placeholder:text-ink/40 placeholder:font-body focus:outline-none focus:ring-2 focus:ring-forest/40 focus:border-forest"
                  />
                  <Button type="submit" variant="secondary">
                    View
                  </Button>
                </div>
                {lookupError && (
                  <p className="text-sm text-clay">{lookupError}</p>
                )}
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
