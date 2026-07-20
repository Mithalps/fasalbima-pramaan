import { useState } from "react";
import { useNavigate } from "react-router-dom";
import StepTabs from "../components/StepTabs";
import FormField from "../components/FormField";
import Button from "../components/Button";
import { createClaim } from "../api/claims";
import { extractErrorMessage } from "../api/client";

const STEPS = [
  { key: "farmer", label: "Farmer" },
  { key: "crop", label: "Crop" },
  { key: "damage", label: "Damage" },
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

export default function NewClaimPage() {
  const navigate = useNavigate();
  const [stepIndex, setStepIndex] = useState(0);
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);

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

  function goNext() {
    if (!validateCurrentStep()) return;
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
      const payload = {
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
      const claim = await createClaim(payload);
      navigate(`/claims/${claim.claim_id}/success`);
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
                  </dl>

                  {submitError && (
                    <p className="text-sm text-clay bg-clay/10 border border-clay/30 rounded-lg px-4 py-3">
                      {submitError}
                    </p>
                  )}
                </div>
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
                  <Button onClick={goNext}>Continue →</Button>
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
