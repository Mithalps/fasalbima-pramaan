# MODULE 2 — Feature 1: Farmer Claim Creation

## What was built

The first complete vertical slice of FasalBima Pramaan: a farmer can open the
app, file a crop-damage claim through a guided multi-step form, get a
generated Claim ID on a success screen, and look that claim up again later.

Every layer of this feature is real — there is no mocked data anywhere:

- **Database:** two normalized SQLite tables (`farmers`, `claims`) with a
  real foreign-key relationship.
- **Backend:** layered into `models/`, `schemas/`, `services/`, `routers/` —
  routers contain no business logic, only HTTP wiring.
- **Frontend:** four real pages, each talking to the live backend, with
  loading states, inline validation errors, and a working submit/view/delete
  path.

## User journey implemented

1. Landing page → **Start New Claim**
2. Step 1 — Farmer details (name, mobile number)
3. Step 2 — Crop details (crop type)
4. Step 3 — Damage details (damage type, date, district, village)
5. Step 4 — Review screen, showing everything entered
6. **Submit** → `POST /api/claims` → saved to SQLite
7. Success screen with the generated Claim ID (stamp-style badge)
8. **View claim details** → fetches and displays the saved claim
9. Landing page also supports jumping straight to any known Claim ID

## Folder changes

```
backend/app/
├── models/
│   ├── __init__.py        # exports Farmer, Claim, DamageType, ClaimStatus
│   ├── farmer.py          # Farmer SQLAlchemy model
│   └── claim.py           # Claim SQLAlchemy model + DamageType/ClaimStatus enums
├── schemas/
│   ├── __init__.py
│   ├── farmer.py          # FarmerCreate, FarmerRead
│   └── claim.py           # ClaimCreate, ClaimUpdate, ClaimRead
├── services/
│   ├── __init__.py
│   └── claim_service.py   # all business logic: farmer dedup, claim CRUD
├── routers/
│   ├── __init__.py
│   └── claims.py          # thin HTTP layer, delegates to claim_service
├── exceptions.py          # ClaimNotFoundError (domain exception)
└── main.py                # updated: logging, table creation, router included

frontend/src/
├── api/
│   ├── client.js          # shared axios instance + error message extraction
│   └── claims.js          # createClaim, getClaim, listClaims, updateClaim, deleteClaim
├── components/
│   ├── FormField.jsx       # labeled input/select with inline error display
│   ├── StepTabs.jsx        # ledger-style step indicator (signature UI element)
│   └── Button.jsx          # primary/secondary/danger button with loading spinner
├── pages/
│   ├── LandingPage.jsx
│   ├── NewClaimPage.jsx    # the 4-step form
│   ├── SuccessPage.jsx
│   └── ViewClaimPage.jsx
└── App.jsx                 # React Router routes (rewritten from Module 1)
```

## Database changes

Two tables, created automatically on backend startup via
`Base.metadata.create_all()`:

**`farmers`**
| Column | Type | Notes |
|---|---|---|
| farmer_id | CHAR(36), PK | UUID |
| farmer_name | VARCHAR(120) | |
| mobile_number | VARCHAR(15), unique, indexed | dedup key |
| created_at | DATETIME | |

**`claims`**
| Column | Type | Notes |
|---|---|---|
| claim_id | CHAR(36), PK | UUID |
| farmer_id | CHAR(36), FK → farmers.farmer_id, indexed | |
| crop_type | VARCHAR(80) | free text, intentionally not an enum |
| damage_type | ENUM | flood / drought / hailstorm / pest_attack / other |
| damage_date | DATE | |
| district | VARCHAR(100) | |
| village | VARCHAR(100) | |
| status | ENUM | submitted / under_review / evidence_ready / closed |
| created_at | DATETIME | |
| updated_at | DATETIME | auto-updates on any change |

A farmer filing a second claim with the same mobile number reuses the
existing farmer row instead of creating a duplicate (`get_or_create_farmer`
in `claim_service.py`).

## APIs added

| Method | Path | Purpose | Success | Failure |
|---|---|---|---|---|
| POST | `/api/claims` | Create farmer (or reuse) + claim | 201 | 422 validation |
| GET | `/api/claims` | List claims, newest first, `skip`/`limit` params | 200 | — |
| GET | `/api/claims/{id}` | Fetch one claim | 200 | 404 |
| PUT | `/api/claims/{id}` | Partial update (any subset of fields) | 200 | 404, 422 |
| DELETE | `/api/claims/{id}` | Delete a claim | 204 | 404 |

All five were tested directly against the running server (not just written
and assumed correct) — see "How to test" below for the exact commands used.

## How to run

**Backend:**
```bash
cd backend
./venv/bin/pip install -r requirements.txt   # only needed if requirements.txt changed
./venv/bin/uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install                                   # only needed if package.json changed
npm run dev
```

Open `http://localhost:5173`.

## How to test

### Through the UI
1. Go to `http://localhost:5173` → click **Start New Claim**.
2. Step 1: leave the mobile number blank or type `123` → click Continue →
   see a red inline error, cannot proceed.
3. Fix it (e.g. `9845012345`) and a name → Continue.
4. Step 2: enter a crop type (e.g. `Ragi`) → Continue.
5. Step 3: pick a damage type, pick **today's date or earlier** (the date
   picker won't stop you from picking the future — server-side validation
   will if you try), enter district and village → Continue.
6. Step 4: review the summary table → click **Submit claim**.
7. You land on the success page with a stamped Claim ID. Copy it.
8. Click **View claim details** → confirms every field you entered.
9. Go back to the landing page, paste the Claim ID into "Already have a
   claim ID?" → View → same claim loads.
10. Try a made-up Claim ID → you should see "No claim found for this ID",
    not a crash.

### Through Swagger (`http://localhost:8000/docs`)
1. Expand `POST /api/claims` → **Try it out** → paste:
   ```json
   {
     "farmer": { "farmer_name": "Test Farmer", "mobile_number": "9876543210" },
     "crop_type": "Ragi",
     "damage_type": "flood",
     "damage_date": "2026-07-15",
     "district": "Bengaluru Rural",
     "village": "Hesaraghatta"
   }
   ```
   → Execute → expect **201** with a `claim_id` in the response.
2. Copy that `claim_id` into `GET /api/claims/{claim_id}` → Execute →
   expect **200** with the same data.
3. Try `GET /api/claims/does-not-exist` → expect **404**.
4. Try the POST again with `"mobile_number": "123"` → expect **422** with a
   readable validation message.
5. Try `PUT /api/claims/{claim_id}` with `{"status": "under_review"}` →
   expect **200** and an updated `updated_at`.
6. Try `DELETE /api/claims/{claim_id}` → expect **204**, then `GET` the same
   ID again → expect **404**.

All of the above were run against the live server while building this
feature — not just designed on paper — including the farmer-dedup case
(filing a second claim with the same mobile number reuses the same
`farmer_id`).

## Known limitations

- **No Alembic migrations** — schema changes rely on `create_all()`, which
  only adds new tables, never alters existing ones. Fine for this project's
  timeline; a real production system would use Alembic.
- **No authentication** — anyone with a Claim ID can view it. Acceptable for
  a hackathon MVP filing flow; would need farmer-auth (e.g. OTP on the
  mobile number) before this handles real claims.
- **No edit/delete UI** — `PUT` and `DELETE` are fully implemented and
  tested on the backend, but Feature 1's frontend only exposes create and
  view, since that's the journey specified for this feature. Editing a
  claim through the UI is a natural fit for Feature 7 (Dashboard & Claim
  History).
- **Pagination is basic** — `GET /api/claims` supports `skip`/`limit` but
  there's no UI for it yet (no list page exists until Feature 7).
- **SQLite, single-writer** — fine for a hackathon demo; would need
  PostgreSQL for concurrent multi-user production use.
