import { useState } from "react";
import { useNavigate } from "react-router-dom";
import StepTabs from "../components/StepTabs";
import FormField from "../components/FormField";
import Button from "../components/Button";
import EvidenceUploader from "../components/EvidenceUploader";
import { createClaim } from "../api/claims";
import { extractErrorMessage } from "../api/client";
import MicButton from "../components/MicButton";
import { extractClaimFields } from "../utils/extractClaimFields";
import { CheckIcon } from "../components/Icons";

const STEPS = [
  { key: "farmer", label: "Farmer" },
  { key: "crop", label: "Crop" },
  { key: "damage", label: "Damage" },
  { key: "evidence", label: "Evidence" },
  { key: "review", label: "Review" },
];

const DAMAGE_TYPE_OPTIONS = [
  { value: "flood", label: "Flood" },
  { value: "drought", label: "Drought" },
  { value: "hailstorm", label: "Hailstorm" },
  { value: "pest_attack", label: "Pest Attack" },
  { value: "other", label: "Other" },
];

const MOBILE_PATTERN = /^[6-9]\d{9}$/;
const TODAY = new Date().toISOString().split("T")[0];

const INITIAL_FORM = {
  farmer_name: "",
  mobile_number: "",
  crop_type: "",
  damage_type: "",
  damage_date: "",
  district: "",
  village: "",
};

// Field key -> human label, in the fixed display order for the
// "Recognized details" checklist after a voice pass.
const FIELD_LABELS = [
  { key: "farmer_name", label: "Farmer Name" },
  { key: "mobile_number", label: "Mobile Number" },
  { key: "district", label: "District" },
  { key: "village", label: "Village" },
  { key: "crop_type", label: "Crop" },
  { key: "damage_type", label: "Damage Type" },
  { key: "damage_date", label: "Damage Date" },
];

const SPEECH_LANGUAGE_OPTIONS = [
  { value: "kn", label: "Kannada" },
  { value: "en", label: "English" },
];

export default function NewClaimPage() {
  const navigate = useNavigate();
  const [stepIndex, setStepIndex] = useState(0);
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [voiceResult, setVoiceResult] = useState(null); // { recognizedKeys: string[] } | null
  const [speechLanguage, setSpeechLanguage] = useState("kn");

  // The claim is created once (right after the Damage step) so that the
  // Evidence step has a real claim_id to upload photos against. Review's
  // "Submit claim" button then just takes the farmer to the success page.
  const [claimId, setClaimId] = useState(null);
  const [creatingClaim, setCreatingClaim] = useState(false);
  const [evidenceItems, setEvidenceItems] = useState([]);

  function updateField(event) {
    const { name, value } = event.target;
    setFormData((previous) => ({ ...previous, [name]: value }));
    // Clear the field's error as soon as the person starts correcting it
    if (errors[name]) {
      setErrors((previous) => {
        const next = { ...previous };
        delete next[name];
        return next;
      });
    }
  }

  // Single big-mic flow: one 30-60s recording -> one transcription call ->
  // rule-based extraction -> auto-fill whatever fields were detected.
  // Anything not detected is left as-is so the farmer can fill/correct it
  // by typing, same as before. The raw transcript is intentionally never
  // shown - only a checklist of which fields were recognized.
  function handleBulkTranscript(transcript) {
    const extracted = extractClaimFields(transcript);
    const recognizedKeys = FIELD_LABELS.map((f) => f.key).filter(
      (key) => extracted[key]
    );

    setVoiceResult({ recognizedKeys });

    if (recognizedKeys.length === 0) return;

    setFormData((previous) => ({ ...previous, ...extracted }));

    setErrors((previous) => {
      const next = { ...previous };
      recognizedKeys.forEach((key) => delete next[key]);
      return next;
    });
  }

  function validateCurrentStep() {
    const stepKey = STEPS[stepIndex].key;
    const nextErrors = {};

    if (stepKey === "farmer") {
      if (formData.farmer_name.trim().length < 2) {
        nextErrors.farmer_name = "Enter the farmer's full name.";
      }
      if (!MOBILE_PATTERN.test(formData.mobile_number.trim())) {
        nextErrors.mobile_number =
          "Enter a valid 10-digit mobile number starting with 6-9.";
      }
    }

    if (stepKey === "crop") {
      if (formData.crop_type.trim().length < 2) {
        nextErrors.crop_type = "Enter the crop type.";
      }
    }

    if (stepKey === "damage") {
      if (!formData.damage_type) {
        nextErrors.damage_type = "Select the type of damage.";
      }
      if (!formData.damage_date) {
        nextErrors.damage_date = "Select the date the damage occurred.";
      } else if (formData.damage_date > TODAY) {
        nextErrors.damage_date = "Damage date cannot be in the future.";
      }
      if (formData.district.trim().length < 2) {
        nextErrors.district = "Enter the district.";
      }
      if (formData.village.trim().length < 2) {
        nextErrors.village = "Enter the village.";
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  function buildClaimPayload() {
    return {
      farmer: {
        farmer_name: formData.farmer_name.trim(),
        mobile_number: formData.mobile_number.trim(),
      },
      crop_type: formData.crop_type.trim(),
      damage_type: formData.damage_type,
      damage_date: formData.damage_date,
      district: formData.district.trim(),
      village: formData.village.trim(),
    };
  }

  async function goNext() {
    if (!validateCurrentStep()) return;

    const stepKey = STEPS[stepIndex].key;

    // Create the claim right as the farmer leaves the Damage step, so the
    // Evidence step has a real claim_id to upload photos against.
    if (stepKey === "damage" && !claimId) {
      setSubmitError("");
      setCreatingClaim(true);
      try {
        const claim = await createClaim(buildClaimPayload());
        setClaimId(claim.claim_id);
        setStepIndex((index) => Math.min(index + 1, STEPS.length - 1));
      } catch (error) {
        setSubmitError(extractErrorMessage(error));
      } finally {
        setCreatingClaim(false);
      }
      return;
    }

    setStepIndex((index) => Math.min(index + 1, STEPS.length - 1));
  }

  function goBack() {
    setSubmitError("");
    setStepIndex((index) => Math.max(index - 1, 0));
  }

  async function handleSubmit() {
    setSubmitError("");
    setSubmitting(true);
    try {
      // Normally the claim already exists by this point (created after the
      // Damage step). This is just a safety fallback in case that step was
      // somehow skipped.
      let id = claimId;
      if (!id) {
        const claim = await createClaim(buildClaimPayload());
        id = claim.claim_id;
      }
      navigate(`/claims/${id}/success`);
    } catch (error) {
      setSubmitError(extractErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  const stepKey = STEPS[stepIndex].key;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-line bg-white">
        <div className="max-w-3xl mx-auto px-6 py-5">
          <h1 className="font-display text-xl font-semibold text-forest">
            FasalBima Pramaan
          </h1>
        </div>
      </header>

      <main className="flex-1 px-6 py-10">
        <div className="max-w-2xl mx-auto mb-6">
          <div className="bg-white border border-line rounded-2xl p-6 sm:p-8 shadow-sm flex flex-col items-center gap-3 text-center">
            <h2 className="font-display text-lg font-semibold text-ink">
              Speak your claim details
            </h2>
            <p className="text-sm text-ink/60 max-w-md">
              Tap the mic and describe your name, mobile number, crop, what
              happened, and your village and district - in Kannada or
              English. We'll fill in the form below; just review and
              correct anything before you continue.
            </p>

            <fieldset className="flex items-center gap-5">
              <legend className="sr-only">Speech language</legend>
              {SPEECH_LANGUAGE_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className="flex items-center gap-1.5 text-sm text-ink/80 cursor-pointer"
                >
                  <input
                    type="radio"
                    name="speech_language"
                    value={option.value}
                    checked={speechLanguage === option.value}
                    onChange={() => setSpeechLanguage(option.value)}
                    className="accent-forest"
                  />
                  {option.label}
                </label>
              ))}
            </fieldset>

            <MicButton
              size="lg"
              label="claim details"
              language={speechLanguage}
              onTranscript={handleBulkTranscript}
            />

            {voiceResult && (
              <div className="w-full max-w-sm text-left bg-forest/5 border border-forest/20 rounded-lg px-4 py-3 mt-1">
                {voiceResult.recognizedKeys.length > 0 ? (
                  <>
                    <p className="text-sm font-medium text-forest flex items-center gap-1.5">
                      <CheckIcon className="h-4 w-4" />
                      Voice processed successfully
                    </p>
                    <p className="text-xs text-ink/60 mt-1 mb-1.5">
                      Recognized details:
                    </p>
                    <ul className="text-sm text-ink/80 flex flex-col gap-0.5">
                      {FIELD_LABELS.filter((f) =>
                        voiceResult.recognizedKeys.includes(f.key)
                      ).map((f) => (
                        <li key={f.key} className="flex items-center gap-1.5">
                          <span aria-hidden="true" className="text-forest">
                            •
                          </span>
                          {f.label}
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p className="text-sm text-clay">
                    Couldn't recognize any details from that recording.
                    Please try again, or fill in the form below manually.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="max-w-2xl mx-auto">
          <div className="bg-white border border-line rounded-2xl overflow-hidden shadow-sm">
            <StepTabs steps={STEPS} currentIndex={stepIndex} />

            <div className="p-6 sm:p-8">
              {stepKey === "farmer" && (
                <div className="flex flex-col gap-5">
                  <div>
                    <h2 className="font-display text-xl font-semibold text-ink">
                      Farmer details
                    </h2>
                    <p className="text-sm text-ink/60 mt-1">
                      Who is this claim being filed for?
                    </p>
                  </div>

                  <FormField
                    label="Farmer's full name"
                    name="farmer_name"
                    value={formData.farmer_name}
                    onChange={updateField}
                    error={errors.farmer_name}
                    placeholder="e.g. Basavaraj Patil"
                  />

                  <FormField
                    label="Mobile number"
                    name="mobile_number"
                    type="tel"
                    value={formData.mobile_number}
                    onChange={updateField}
                    error={errors.mobile_number}
                    placeholder="10-digit mobile number"
                  />
                </div>
              )}

              {stepKey === "crop" && (
                <div className="flex flex-col gap-5">
                  <div>
                    <h2 className="font-display text-xl font-semibold text-ink">
                      Crop details
                    </h2>
                    <p className="text-sm text-ink/60 mt-1">
                      What crop was affected?
                    </p>
                  </div>
                  <FormField
                    label="Crop type"
                    name="crop_type"
                    value={formData.crop_type}
                    onChange={updateField}
                    error={errors.crop_type}
                    placeholder="e.g. Ragi, Paddy, Cotton"
                  />
                </div>
              )}

              {stepKey === "damage" && (
                <div className="flex flex-col gap-5">
                  <div>
                    <h2 className="font-display text-xl font-semibold text-ink">
                      Damage details
                    </h2>
                    <p className="text-sm text-ink/60 mt-1">
                      Tell us what happened, where, and when.
                    </p>
                  </div>
                  <FormField
                    label="Type of damage"
                    name="damage_type"
                    as="select"
                    options={DAMAGE_TYPE_OPTIONS}
                    value={formData.damage_type}
                    onChange={updateField}
                    error={errors.damage_type}
                  />
                  <FormField
                    label="Date of damage"
                    name="damage_date"
                    type="date"
                    value={formData.damage_date}
                    onChange={updateField}
                    error={errors.damage_date}
                  />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <FormField
                      label="District"
                      name="district"
                      value={formData.district}
                      onChange={updateField}
                      error={errors.district}
                      placeholder="e.g. Bengaluru Rural"
                    />
                    <FormField
                      label="Village"
                      name="village"
                      value={formData.village}
                      onChange={updateField}
                      error={errors.village}
                      placeholder="e.g. Hesaraghatta"
                    />
                  </div>
                </div>
              )}

              {stepKey === "evidence" && (
                <div className="flex flex-col gap-5">
                  <EvidenceUploader
                    claimId={claimId}
                    evidenceItems={evidenceItems}
                    setEvidenceItems={setEvidenceItems}
                  />
                </div>
              )}

              {stepKey === "review" && (
                <div className="flex flex-col gap-5">
                  <div>
                    <h2 className="font-display text-xl font-semibold text-ink">
                      Review your claim
                    </h2>
                    <p className="text-sm text-ink/60 mt-1">
                      Check the details before submitting.
                    </p>
                  </div>

                  <dl className="divide-y divide-line rounded-lg border border-line overflow-hidden">
                    <ReviewRow label="Farmer name" value={formData.farmer_name} />
                    <ReviewRow label="Mobile number" value={formData.mobile_number} />
                    <ReviewRow label="Crop type" value={formData.crop_type} />
                    <ReviewRow
                      label="Damage type"
                      value={
                        DAMAGE_TYPE_OPTIONS.find(
                          (option) => option.value === formData.damage_type
                        )?.label
                      }
                    />
                    <ReviewRow label="Damage date" value={formData.damage_date} />
                    <ReviewRow label="District" value={formData.district} />
                    <ReviewRow label="Village" value={formData.village} />
                    <ReviewRow
                      label="Evidence photos"
                      value={
                        evidenceItems.length > 0
                          ? `${evidenceItems.length} uploaded`
                          : "None uploaded"
                      }
                    />
                  </dl>
                </div>
              )}

              {submitError && (
                <p className="text-sm text-clay bg-clay/10 border border-clay/30 rounded-lg px-4 py-3 mt-6">
                  {submitError}
                </p>
              )}

              <div className="flex items-center justify-between mt-8 pt-6 border-t border-line">
                <Button
                  variant="secondary"
                  onClick={stepIndex === 0 ? () => navigate("/") : goBack}
                >
                  {stepIndex === 0 ? "Cancel" : "← Back"}
                </Button>

                {stepKey === "review" ? (
                  <Button onClick={handleSubmit} loading={submitting}>
                    Submit claim
                  </Button>
                ) : (
                  <Button onClick={goNext} loading={creatingClaim}>
                    Continue →
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function ReviewRow({ label, value }) {
  return (
    <div className="flex justify-between gap-4 px-4 py-3 bg-white">
      <dt className="text-sm text-ink/60">{label}</dt>
      <dd className="text-sm font-medium text-ink text-right">
        {value || "—"}
      </dd>
    </div>
  );
}