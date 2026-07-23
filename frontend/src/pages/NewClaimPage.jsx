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
import { CheckIcon, UserIcon, LeafIcon, WarningIcon, PinIcon } from "../components/Icons";
import { RecordSection, RecordField } from "../components/RecordSection";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { useLanguage } from "../context/LanguageContext";

const MOBILE_PATTERN = /^[6-9]\d{9}$/;
const AADHAAR_PATTERN = /^\d{12}$/;
const TODAY = new Date().toISOString().split("T")[0];

const INITIAL_FORM = {
  farmer_name: "",
  mobile_number: "",
  aadhaar_number: "",
  crop_type: "",
  damage_type: "",
  damage_date: "",
  district: "",
  village: "",
};

// Masks all but the last 4 digits, e.g. "123456789012" -> "XXXX XXXX 9012".
// Used for read-back display only (Review step here, and ViewClaimPage) —
// the raw value is still what's sent to the API/stored.
function maskAadhaar(value) {
  const digits = (value || "").replace(/\s/g, "");
  if (digits.length < 4) return "XXXX XXXX XXXX";
  return `XXXX XXXX ${digits.slice(-4)}`;
}

export default function NewClaimPage() {
  const navigate = useNavigate();
  const { t } = useLanguage();
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

  // Translated lookup data. Rebuilt on every render so switching languages
  // immediately re-labels steps, dropdown options, and the voice-recognized
  // fields checklist without losing any of the state above.
  const STEPS = [
    { key: "farmer", label: t("newClaim.stepFarmer") },
    { key: "crop", label: t("newClaim.stepCrop") },
    { key: "damage", label: t("newClaim.stepDamage") },
    { key: "evidence", label: t("newClaim.stepEvidence") },
    { key: "review", label: t("newClaim.stepReview") },
  ];

  const DAMAGE_TYPE_OPTIONS = [
    { value: "flood", label: t("damageTypes.flood") },
    { value: "drought", label: t("damageTypes.drought") },
    { value: "hailstorm", label: t("damageTypes.hailstorm") },
    { value: "pest_attack", label: t("damageTypes.pest_attack") },
    { value: "other", label: t("damageTypes.other") },
  ];

  // Field key -> human label, in the fixed display order for the
  // "Recognized details" checklist after a voice pass.
  const FIELD_LABELS = [
    { key: "farmer_name", label: t("newClaim.fieldFarmerName") },
    { key: "mobile_number", label: t("newClaim.fieldMobileNumber") },
    { key: "district", label: t("newClaim.fieldDistrict") },
    { key: "village", label: t("newClaim.fieldVillage") },
    { key: "crop_type", label: t("newClaim.fieldCrop") },
    { key: "damage_type", label: t("newClaim.fieldDamageType") },
    { key: "damage_date", label: t("newClaim.fieldDamageDate") },
  ];

  const SPEECH_LANGUAGE_OPTIONS = [
    { value: "kn", label: t("newClaim.speechLanguageKannada") },
    { value: "en", label: t("newClaim.speechLanguageEnglish") },
  ];

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
        nextErrors.farmer_name = t("newClaim.errorFarmerName");
      }
      if (!MOBILE_PATTERN.test(formData.mobile_number.trim())) {
        nextErrors.mobile_number = t("newClaim.errorMobileNumber");
      }
      const aadhaarDigits = formData.aadhaar_number.replace(/\s/g, "");
      if (!aadhaarDigits) {
        nextErrors.aadhaar_number = t("newClaim.errorAadhaarNumberRequired");
      } else if (!/^\d+$/.test(aadhaarDigits)) {
        nextErrors.aadhaar_number = t("newClaim.errorAadhaarNumberNonNumeric");
      } else if (!AADHAAR_PATTERN.test(aadhaarDigits)) {
        nextErrors.aadhaar_number = t("newClaim.errorAadhaarNumberLength");
      }
    }

    if (stepKey === "crop") {
      if (formData.crop_type.trim().length < 2) {
        nextErrors.crop_type = t("newClaim.errorCropType");
      }
    }

    if (stepKey === "damage") {
      if (!formData.damage_type) {
        nextErrors.damage_type = t("newClaim.errorDamageType");
      }
      if (!formData.damage_date) {
        nextErrors.damage_date = t("newClaim.errorDamageDate");
      } else if (formData.damage_date > TODAY) {
        nextErrors.damage_date = t("newClaim.errorDamageDateFuture");
      }
      if (formData.district.trim().length < 2) {
        nextErrors.district = t("newClaim.errorDistrict");
      }
      if (formData.village.trim().length < 2) {
        nextErrors.village = t("newClaim.errorVillage");
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
        aadhaar_number: formData.aadhaar_number.replace(/\s/g, ""),
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
      <Header
        contextLabel={t("header.contextNewClaim")}
        stepInfo={t("common.stepOf", { current: stepIndex + 1, total: STEPS.length })}
      />

      <main className="flex-1 px-6 py-10">
        <div className="max-w-3xl mx-auto mb-6">
          <div className="bg-white border border-line rounded-xl p-6 sm:p-8 shadow-[var(--shadow-card)] flex flex-col items-center gap-3 text-center">
            <h2 className="font-display text-lg font-semibold text-ink">
              {t("newClaim.speakHeading")}
            </h2>
            <p className="text-sm text-ink/70 max-w-md">
              {t("newClaim.speakBody")}
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
              label={t("newClaim.micLabel")}
              language={speechLanguage}
              onTranscript={handleBulkTranscript}
            />

            {voiceResult && (
              <div className="w-full max-w-sm text-left bg-forest/5 border border-forest/20 rounded-lg px-4 py-3 mt-1">
                {voiceResult.recognizedKeys.length > 0 ? (
                  <>
                    <p className="text-sm font-medium text-forest flex items-center gap-1.5">
                      <CheckIcon className="h-4 w-4" />
                      {t("newClaim.voiceProcessed")}
                    </p>
                    <p className="text-xs text-ink/70 mt-1 mb-1.5">
                      {t("newClaim.recognizedDetails")}
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
                    {t("newClaim.voiceNoResults")}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="max-w-3xl mx-auto">
          <div className="bg-white border border-line rounded-xl overflow-hidden shadow-[var(--shadow-card)]">
            <StepTabs steps={STEPS} currentIndex={stepIndex} />

            <div className="p-6 sm:p-8">
              {stepKey === "farmer" && (
                <div className="flex flex-col gap-5">
                  <div>
                    <h2 className="font-display text-xl font-semibold text-ink">
                      {t("newClaim.farmerStepHeading")}
                    </h2>
                    <p className="text-sm text-ink/70 mt-1">
                      {t("newClaim.farmerStepBody")}
                    </p>
                  </div>

                  <FormField
                    label={t("newClaim.farmerNameLabel")}
                    name="farmer_name"
                    value={formData.farmer_name}
                    onChange={updateField}
                    error={errors.farmer_name}
                    placeholder={t("newClaim.farmerNamePlaceholder")}
                  />

                  <FormField
                    label={t("newClaim.aadhaarNumberLabel")}
                    name="aadhaar_number"
                    value={formData.aadhaar_number}
                    onChange={updateField}
                    error={errors.aadhaar_number}
                    placeholder={t("newClaim.aadhaarNumberPlaceholder")}
                  />

                  <FormField
                    label={t("newClaim.mobileNumberLabel")}
                    name="mobile_number"
                    type="tel"
                    value={formData.mobile_number}
                    onChange={updateField}
                    error={errors.mobile_number}
                    placeholder={t("newClaim.mobileNumberPlaceholder")}
                  />
                </div>
              )}

              {stepKey === "crop" && (
                <div className="flex flex-col gap-5">
                  <div>
                    <h2 className="font-display text-xl font-semibold text-ink">
                      {t("newClaim.cropStepHeading")}
                    </h2>
                    <p className="text-sm text-ink/70 mt-1">
                      {t("newClaim.cropStepBody")}
                    </p>
                  </div>
                  <FormField
                    label={t("newClaim.cropTypeLabel")}
                    name="crop_type"
                    value={formData.crop_type}
                    onChange={updateField}
                    error={errors.crop_type}
                    placeholder={t("newClaim.cropTypePlaceholder")}
                  />
                </div>
              )}

              {stepKey === "damage" && (
                <div className="flex flex-col gap-5">
                  <div>
                    <h2 className="font-display text-xl font-semibold text-ink">
                      {t("newClaim.damageStepHeading")}
                    </h2>
                    <p className="text-sm text-ink/70 mt-1">
                      {t("newClaim.damageStepBody")}
                    </p>
                  </div>
                  <FormField
                    label={t("newClaim.damageTypeLabel")}
                    name="damage_type"
                    as="select"
                    options={DAMAGE_TYPE_OPTIONS}
                    value={formData.damage_type}
                    onChange={updateField}
                    error={errors.damage_type}
                  />
                  <FormField
                    label={t("newClaim.damageDateLabel")}
                    name="damage_date"
                    type="date"
                    value={formData.damage_date}
                    onChange={updateField}
                    error={errors.damage_date}
                  />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <FormField
                      label={t("newClaim.districtLabel")}
                      name="district"
                      value={formData.district}
                      onChange={updateField}
                      error={errors.district}
                      placeholder={t("newClaim.districtPlaceholder")}
                    />
                    <FormField
                      label={t("newClaim.villageLabel")}
                      name="village"
                      value={formData.village}
                      onChange={updateField}
                      error={errors.village}
                      placeholder={t("newClaim.villagePlaceholder")}
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
                      {t("newClaim.reviewHeading")}
                    </h2>
                    <p className="text-sm text-ink/70 mt-1">
                      {t("newClaim.reviewBody")}
                    </p>
                  </div>

                  <div className="rounded-lg border border-line bg-paper-raised/40 px-5 py-5 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-6">
                    <RecordSection title={t("sections.farmer")} icon={<UserIcon className="h-3.5 w-3.5" />}>
                      <RecordField label={t("recordLabels.name")} value={formData.farmer_name} />
                      <RecordField label={t("recordLabels.mobileNumber")} value={formData.mobile_number} />
                      <RecordField label={t("recordLabels.aadhaarNumber")} value={maskAadhaar(formData.aadhaar_number)} />
                    </RecordSection>

                    <RecordSection title={t("sections.crop")} icon={<LeafIcon className="h-3.5 w-3.5" />}>
                      <RecordField label={t("recordLabels.cropType")} value={formData.crop_type} />
                    </RecordSection>

                    <RecordSection title={t("sections.damage")} icon={<WarningIcon className="h-3.5 w-3.5" />}>
                      <RecordField
                        label={t("recordLabels.type")}
                        value={
                          DAMAGE_TYPE_OPTIONS.find(
                            (option) => option.value === formData.damage_type
                          )?.label
                        }
                      />
                      <RecordField label={t("recordLabels.date")} value={formData.damage_date} />
                    </RecordSection>

                    <RecordSection title={t("sections.location")} icon={<PinIcon className="h-3.5 w-3.5" />}>
                      <RecordField label={t("recordLabels.district")} value={formData.district} />
                      <RecordField label={t("recordLabels.village")} value={formData.village} />
                    </RecordSection>

                    <RecordSection title={t("sections.evidence")}>
                      <RecordField
                        label={t("recordLabels.photos")}
                        value={
                          evidenceItems.length > 0
                            ? t("newClaim.photosUploaded", { count: evidenceItems.length })
                            : t("newClaim.photosNone")
                        }
                      />
                    </RecordSection>
                  </div>
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
                  {stepIndex === 0 ? t("common.cancel") : t("common.back")}
                </Button>

                {stepKey === "review" ? (
                  <Button onClick={handleSubmit} loading={submitting}>
                    {t("common.submitClaim")}
                  </Button>
                ) : (
                  <Button onClick={goNext} loading={creatingClaim}>
                    {t("common.continueButton")}
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
