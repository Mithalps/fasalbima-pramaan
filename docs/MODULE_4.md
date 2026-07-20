# Module 4 — Voice Assistance (Bhashini ASR)

Extends Module 1 (project setup) and Feature 1/2 (claim workflow, evidence
upload). Nothing in those modules was redesigned — this module only adds
new files and the smallest possible edits to existing ones where a genuine
dependency required it (listed explicitly below).

---

## 1. What was built

A farmer can now tap a microphone button next to four fields on the claim
form — **Farmer's full name**, **Crop type**, **Village**, and **Type of
damage** — speak the answer in Kannada, and have it transcribed and
dropped into the field automatically. They can still edit it by hand
afterwards, same as if they'd typed it.

**Backend**
- New `bhashini_service.py`: implements Bhashini's two-call ULCA pipeline
  (Pipeline Config Call → Pipeline Compute Call), with the resolved
  config (serviceId, inference endpoint, auth key) cached in memory and
  reused across requests instead of re-fetched on every transcription
  request
- New `speech_service.py`: validates the uploaded audio (content-type,
  size, non-empty) before handing it to `bhashini_service`
- New `POST /api/speech/transcribe` endpoint — stateless, not claim-scoped,
  since it's a shared "audio in, text out" utility used by several fields
- Handles: unsupported audio format, empty audio, oversized audio, missing
  Bhashini credentials, Bhashini timeout, and Bhashini failure — each with
  its own exception type and HTTP status (see §4)
- One automatic retry with a freshly-fetched pipeline config if the
  compute call fails with a cached config (guards against a stale
  server-side auth key without needing a backend restart)

**Frontend**
- New `MicButton.jsx`: a self-contained record → stop → upload →
  transcribe control with its own loading/error state, so a failed
  recording or a network error never breaks the rest of the form
- New `audioEncoder.js`: converts whatever the browser's `MediaRecorder`
  produced (webm/opus on Chrome, mp4/aac on Safari) into 16kHz mono WAV
  client-side, since that's the format Bhashini's ASR models are most
  reliably tuned for. Falls back to uploading the raw recording untouched
  if this conversion fails for any reason
- `FormField.jsx` gained one optional prop, `endAdornment`, so a
  `<MicButton />` can sit beside a field without changing the layout of
  any field that doesn't use it
- `damage_type` is a fixed dropdown, not free text, so its mic button
  matches the transcript against a small Kannada/English keyword list per
  option (flood/drought/hailstorm/pest_attack/other) instead of typing
  text into a select. If nothing matches, the transcript is shown as a
  hint under the dropdown so the farmer can pick manually rather than the
  recording silently doing nothing

---

## 2. A discrepancy worth flagging

Before writing any code, `backend/app/config.py` and `.env.example` were
checked, per this module's own instructions. Both already declared a
`whisper_model_size` setting, commented as reserved for a future module —
i.e. the codebase's own prior plan was a local Whisper model for ASR, not
Bhashini.

The brief for this module explicitly asks for **Bhashini Speech-to-Text**,
so that's what was built. `whisper_model_size` was left in place untouched
(not deleted, not repurposed) and re-commented to make clear it isn't used
by this module — deleting a setting that isn't actually in this module's
scope felt like more change than necessary, and repurposing it to mean
something Bhashini-related would have been misleading. If a future module
still intends to add local Whisper transcription alongside Bhashini (e.g.
as an offline fallback), that setting is exactly where it was left.

---

## 3. API endpoint

| Method | Path                     | Description                                    |
|--------|--------------------------|-------------------------------------------------|
| POST   | `/api/speech/transcribe` | Transcribe one short audio clip (multipart)     |

**Request** (multipart/form-data)

| Field           | Required | Notes                                                        |
|-----------------|----------|---------------------------------------------------------------|
| `audio`         | yes      | WAV, WEBM, OGG, or MP3, ≤10MB                                 |
| `language`      | no       | ISO-639 code, defaults to `kn` (Kannada)                      |
| `sampling_rate` | no       | Defaults to `16000`; the frontend sends the real encoded rate |

**Response**

```json
{ "transcript": "ಬಸವರಾಜ ಪಾಟೀಲ", "language": "kn" }
```

**Error responses**

| Status | Cause                                                          |
|--------|------------------------------------------------------------------|
| 400    | Audio file is empty                                              |
| 415    | Audio content-type isn't WAV/WEBM/OGG/MP3                        |
| 413    | Audio exceeds 10MB                                                |
| 503    | `BHASHINI_ULCA_USER_ID` / `BHASHINI_ULCA_API_KEY` / `BHASHINI_PIPELINE_ID` not configured |
| 504    | Bhashini's config or compute call didn't respond in time         |
| 502    | Bhashini's config or compute call failed or returned an unexpected shape |

All are documented and testable via Swagger at `/docs`.

---

## 4. Configuration

**Obtaining Bhashini credentials**

1. Register/log in at the ULCA web portal (https://bhashini.gitbook.io/bhashini-apis
   documents the full process; Bhashini's own onboarding form is linked
   from https://bhashini.gov.in/).
2. Once approved as an integrator, you receive a `userID` and `ulcaApiKey`
   — these map to `BHASHINI_ULCA_USER_ID` and `BHASHINI_ULCA_API_KEY`.
3. Use the Pipeline Search API (or the ULCA web UI) to find a pipeline
   that supports the `asr` task for Kannada (`kn`), and note its
   `pipelineId` — this maps to `BHASHINI_PIPELINE_ID`.
4. `BHASHINI_CONFIG_URL` defaults to Bhashini's standard Config Call
   endpoint (`https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline`)
   — only override this if Bhashini's docs specify a different one for
   your account.

**New environment variables** (added to `.env.example`)

```bash
BHASHINI_ULCA_USER_ID=
BHASHINI_ULCA_API_KEY=
BHASHINI_PIPELINE_ID=
BHASHINI_CONFIG_URL=https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline
BHASHINI_DEFAULT_SOURCE_LANGUAGE=kn
BHASHINI_REQUEST_TIMEOUT_SECONDS=20
BHASHINI_CONFIG_CACHE_SECONDS=3600
MAX_AUDIO_FILE_SIZE_MB=10
```

Without real values for the first three, the app still starts normally —
`POST /api/speech/transcribe` returns a clean 503 instead of failing at
import time or crashing the process.

**New Python package**

```
httpx==0.28.1
```
(added to `backend/requirements.txt` — used to call Bhashini's two API
endpoints asynchronously, consistent with FastAPI's async route handlers)

**New npm packages:** none. `MicButton.jsx` and `audioEncoder.js` use only
browser-native `MediaRecorder`, `AudioContext`/`OfflineAudioContext`, and
`Blob` APIs — no new dependency was needed.

---

## 5. Folder changes

```
backend/
  app/
    services/bhashini_service.py   (new)
    services/speech_service.py     (new)
    schemas/speech.py              (new)
    routers/speech.py              (new)

frontend/
  src/
    api/speech.js                  (new)
    components/MicButton.jsx       (new)
    utils/audioEncoder.js          (new)
```

Edited (not rewritten) existing files:
- `backend/app/config.py` — added Bhashini settings; re-commented
  `whisper_model_size` as unused by this module (see §2)
- `backend/app/exceptions.py` — added speech/Bhashini exception types
- `backend/app/schemas/__init__.py` — registered `TranscriptionRead`
- `backend/app/main.py` — registered the speech router
- `backend/requirements.txt` — added `httpx`
- `.env.example` — added Bhashini configuration block
- `frontend/src/components/FormField.jsx` — added the optional
  `endAdornment` prop
- `frontend/src/pages/NewClaimPage.jsx` — added `MicButton`s to Farmer's
  full name, Crop type, and Village; added the damage-type keyword matcher
  and voice hint text under the Type of damage dropdown

---

## 6. Testing instructions

**Backend, standalone**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open `http://localhost:8000/docs` and try `POST /api/speech/transcribe`
directly with a short WAV file attached.

**Full stack**
```bash
# terminal 1
cd backend && uvicorn app.main:app --reload

# terminal 2
cd frontend && npm install && npm run dev
```
Visit `http://localhost:5173`, start a new claim, and tap a microphone
button on the Farmer, Crop, or Damage step.

**What was actually verified during this build** (via FastAPI's
`TestClient` against the real app, and `vite build`/`oxlint` against the
real frontend):
- App imports cleanly and `/api/speech/transcribe` registers correctly
  alongside the existing claim/evidence routes
- Empty audio file → 400
- Unsupported content-type (e.g. `text/plain`) → 415
- No Bhashini credentials configured → clean 503 with the exact message
  shown above, not a crash or an unhandled 500
- `vite build` and `oxlint` both pass clean on the whole `frontend/src`
  tree after these changes

**Not yet verified against a live Bhashini account** (no real credentials
were available in this environment): the actual Config Call → Compute
Call round trip, real Kannada transcription accuracy, and the 504/502
paths under real network conditions. These should be the first things
tested once `BHASHINI_ULCA_USER_ID` / `BHASHINI_ULCA_API_KEY` /
`BHASHINI_PIPELINE_ID` are filled in — see the manual checklist below.

---

## 7. Manual testing checklist

**Happy path (needs real Bhashini credentials in `.env`)**
- [ ] Start a new claim, tap the mic next to "Farmer's full name," speak a
      name in Kannada, confirm the field fills in and is still editable
- [ ] Repeat for Crop type and Village
- [ ] On the Damage step, tap the mic next to "Type of damage" and say a
      damage type in Kannada (e.g. "ಪ್ರವಾಹ" for flood) — confirm the
      dropdown auto-selects the matching option
- [ ] Say something that doesn't match any keyword — confirm the hint text
      appears under the dropdown instead of silently doing nothing
- [ ] Complete the rest of the flow normally; confirm voice-filled fields
      show up correctly on Review and in the final claim

**Error handling**
- [ ] Deny microphone permission when prompted — confirm a friendly inline
      message appears and the rest of the page still works
- [ ] Start a recording, then immediately navigate away/cancel — confirm
      no stray error and the mic track is released (check the browser's
      mic-in-use indicator turns off)
- [ ] Temporarily stop the backend mid-recording and tap stop — confirm
      "Could not reach the server" appears next to the mic button, not a
      page crash
- [ ] With `BHASHINI_ULCA_USER_ID` etc. unset, tap any mic button, record,
      and stop — confirm the 503 message surfaces inline

**Backend direct (via `/docs`)**
- [ ] `POST /api/speech/transcribe` with a valid short WAV → 200 with a
      transcript (once real credentials are configured)
- [ ] Same endpoint with a `.txt` file → 415
- [ ] Same endpoint with an empty file → 400
- [ ] Same endpoint with credentials unset → 503

---

## 8. Known limitations

- **Real Bhashini credentials weren't available in this build
  environment** — the two-call ULCA flow was implemented against
  Bhashini's own documented request/response shapes and unit-tested for
  every failure path (missing credentials, bad format, empty audio), but
  hasn't been exercised against a live pipeline yet. Test this first once
  credentials are added.
- **`damage_type` voice matching is keyword-based, not NLU** — consistent
  with the proposal's own reasoning for slot extraction generally (a fixed
  small vocabulary is more predictable with rules than a model), but it
  means unusual phrasing won't match even when a human would understand
  it. The hint text is the safety net for that case.
- **No audio format conversion fallback beyond raw upload** — if a
  browser's `AudioContext` can't decode the recorded audio (rare, but
  possible on older browsers), the original webm/ogg is uploaded as-is.
  The backend accepts it, but transcription accuracy on non-WAV input from
  Bhashini's models is unverified here.
- **No retry/resume on a failed transcription** — a failed recording can
  be re-recorded from scratch by tapping the mic again, but there's no
  automatic retry, which matters for the same flaky rural connectivity
  this project already flags as a concern for evidence uploads (see
  MODULE_3.md, Known Limitations).
- **Mobile number, District, and Damage date have no mic button** — mobile
  number and dates are awkward to dictate reliably by voice and weren't
  included in the brief's field list; District was left out to match the
  brief precisely ("Farmer Name, Village, Crop Type, Damage Type") even
  though it's a similar free-text field to Village.
