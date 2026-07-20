# Module 3 / Feature 2 — Crop Damage Evidence Upload

Extends Module 1 (project setup) and Feature 1 (claim workflow). Nothing in
those modules was redesigned — this module only adds new files and makes
the smallest possible edits to existing ones where a genuine dependency
required it (listed explicitly below).

---

## 1. What was built

A farmer can now attach up to 5 photos of crop damage to a claim, as part
of the same guided flow used in Feature 1.

**Backend**
- New `Evidence` model, schema, service, and router
- File validation: JPEG/PNG/WEBP only, ≤10MB each, ≤5 images per claim,
  and the file content itself is verified to be a genuine, decodable image
  (not just a renamed file with a matching extension)
- Files are stored on disk under `backend/uploads/{claim_id}/{uuid}.ext`;
  only metadata lives in SQLite
- Uploaded photos are served back as static files at `/uploads/...`
- Deleting a single evidence photo removes both the DB row and the file
- Deleting a claim removes its evidence rows (via cascade) and their files

**Frontend**
- New "Evidence" step in the claim form, between Damage and Review
- Drag-and-drop zone + click-to-browse, multi-select
- Per-file thumbnail with an upload progress bar
- Per-file validation errors (wrong type / too large / limit reached),
  dismissible without affecting other files
- Delete button on each uploaded thumbnail
- Review step shows a photo count and thumbnail grid
- Claim view page (`/claims/{id}`) now also shows the claim's evidence
  photos, in an appended section

---

## 2. A design decision worth calling out

The required API is claim-scoped (`POST /api/claims/{id}/evidence`), which
means evidence can only be uploaded against a claim that already exists.
But the required UI flow places the Evidence step *before* Review/Submit —
and Feature 1's original design only ever created the claim at the very
end, when the Review step's "Submit" button was pressed.

To satisfy both requirements without changing the API contract, the claim
is now created as soon as the farmer finishes the **Damage** step (i.e.
the moment "Continue" is pressed going into Evidence). The Evidence step
then uploads against that real `claim_id`. The Review step's "Submit"
button no longer creates the claim — it already exists — it just confirms
and navigates to the success page.

**Trade-off this introduces:** if a farmer closes the tab or abandons the
flow after the Damage step but before finishing Review, a claim record
already exists in the database (with `status = submitted`, no evidence,
and no explicit "I'm done" confirmation from the farmer). The existing
`ClaimStatus` enum has no "draft" value, and adding one felt like scope
creep for an evidence-upload feature — it's called out here instead so
it's a known, deliberate limitation rather than a silent one. The `Cancel`
button (shown on the first step, Farmer) deletes the claim if one was
already created, but there's no equivalent explicit "leave the flow"
control on the later steps in this version of the UI, since Feature 1's
design didn't have one either.

---

## 3. Database changes

New table: `evidence`

| Column        | Type              | Notes                                  |
|---------------|-------------------|-----------------------------------------|
| `id`          | String(36), PK    | UUID                                    |
| `claim_id`    | String(36), FK    | References `claims.claim_id`            |
| `file_name`   | String(255)       | Original filename from the upload       |
| `file_path`   | String(500)       | Path relative to `UPLOAD_DIR`           |
| `uploaded_at` | DateTime (tz-aware) | Set on insert                         |

`claims.evidence_items` — a new relationship on the existing `Claim` model
(`cascade="all, delete-orphan"`), so deleting a claim deletes its evidence
rows. This was the one necessary addition to `models/claim.py`.

Tables are created via the existing `Base.metadata.create_all()` in
`main.py`'s startup event — no migration step needed, consistent with how
Feature 1 handles schema changes (see MODULE_2.md's own Known Limitations
re: no Alembic).

---

## 4. API endpoints

| Method | Path                          | Description                          |
|--------|-------------------------------|---------------------------------------|
| POST   | `/api/claims/{claim_id}/evidence` | Upload one evidence photo (multipart `file` field) |
| GET    | `/api/claims/{claim_id}/evidence` | List all evidence photos for a claim |
| DELETE | `/api/evidence/{evidence_id}`     | Delete one evidence photo            |

Upload is **one file per request** by design — the frontend calls it once
per selected file so each photo gets its own progress bar and a failure on
one file doesn't affect the others already uploading.

**Error responses**

| Status | Cause                                      |
|--------|---------------------------------------------|
| 404    | Claim (or evidence) not found               |
| 415    | Unsupported file type                        |
| 413    | File exceeds 10MB                            |
| 400    | File extension/type is accepted but content isn't a decodable image |
| 409    | Claim already has 5 evidence images          |

All are documented and testable via Swagger at `/docs`.

---

## 5. Folder changes

```
backend/
  app/
    models/evidence.py          (new)
    schemas/evidence.py         (new)
    services/evidence_service.py (new)
    routers/evidence.py         (new)
  uploads/                      (new — gitignored except .gitkeep)
    {claim_id}/
      {uuid}.jpg / .png / .webp

frontend/
  src/
    api/evidence.js             (new)
    components/EvidenceUploader.jsx (new)
```

Edited (not rewritten) existing files:
- `backend/app/models/claim.py` — added `evidence_items` relationship
- `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py` — registered new model/schema
- `backend/app/main.py` — mounted `/uploads` static files, registered evidence routers, ensured `uploads/` exists at startup
- `backend/app/config.py` — added upload settings (`upload_dir`, size/count limits)
- `backend/app/exceptions.py` — added evidence-related exception types
- `backend/app/services/claim_service.py` — `delete_claim` now also removes evidence files from disk (DB rows are handled by the cascade)
- `backend/requirements.txt` — added `python-multipart`, `Pillow`
- `.env`, `.env.example`, `.gitignore` — new upload settings / ignore rules
- `frontend/vite.config.js` — proxy `/uploads` alongside the existing `/api` proxy
- `frontend/src/pages/NewClaimPage.jsx` — added Evidence step, claim-creation timing (see §2), Review step evidence summary
- `frontend/src/pages/ViewClaimPage.jsx` — appended an Evidence section

---

## 6. Testing instructions

**Backend, standalone**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open `http://localhost:8000/docs` and exercise the three evidence endpoints
directly — create a claim via `/api/claims` first to get a `claim_id`.

**Full stack**
```bash
# terminal 1
cd backend && uvicorn app.main:app --reload

# terminal 2
cd frontend && npm install && npm run dev
```
Visit `http://localhost:5173`.

**What was actually verified during this build** (via `curl` against a live
`uvicorn` instance, and again through the real Vite dev proxy):
- Valid JPEG, PNG, and WEBP uploads → 201, file saved, correct `file_url`
- Unsupported type (e.g. `.txt`) → 415
- File over 10MB → 413
- A file with an image extension/content-type but non-image bytes → 400
- 6th upload attempt on a claim that already has 5 → 409
- Upload to a nonexistent `claim_id` → 404
- `DELETE /api/evidence/{id}` removes both the DB row and the file on disk
- `DELETE /api/claims/{id}` removes the claim's evidence files too
- Deleting a nonexistent evidence id → 404
- Fetching an uploaded file back through `/uploads/...` (and through the
  Vite dev proxy) → 200, correct `Content-Type`
- Frontend build (`vite build`) and lint (`oxlint`) both pass clean

---

## 7. Manual testing checklist

**Happy path**
- [ ] Fill Farmer → Crop → Damage steps, click Continue
- [ ] Confirm the Evidence step appears and no page error is shown
- [ ] Drag-and-drop 2–3 JPEG/PNG/WEBP photos onto the drop zone
- [ ] Confirm each shows a thumbnail and a progress bar that completes
- [ ] Click "browse" and select 1–2 more photos via the file picker
- [ ] Delete one uploaded photo using the ✕ button; confirm it disappears
- [ ] Click Continue to Review; confirm the photo count and thumbnails match
- [ ] Click "Submit claim"; confirm it navigates to the success page
- [ ] Open "View claim details"; confirm the Evidence section shows the
      same photos

**Validation**
- [ ] Try uploading a `.gif` or `.pdf` — should show a per-file error, not
      block the other files
- [ ] Try uploading a file larger than 10MB — should show a per-file
      "too large" error
- [ ] Upload 5 valid photos, then try a 6th — the drop zone should show
      "Photo limit reached" and further files should show a limit error
- [ ] With the drop zone visibly at 5/5, confirm it's disabled for further
      drag-and-drop

**Navigation**
- [ ] From Evidence, click "← Back" to Damage, edit a field, click
      Continue again — confirm it does **not** create a second claim (no
      duplicate appears if you check `/api/claims` in Swagger)
- [ ] From Evidence, click "← Back" twice to Crop — confirm previously
      uploaded photos are still shown when you return to Evidence
- [ ] On the Farmer step, click "Cancel" before ever reaching Evidence —
      confirm it returns to the landing page (no claim was created, so
      there's nothing to clean up)

**Backend direct (via `/docs`)**
- [ ] `POST /api/claims/{id}/evidence` with a valid image → 201
- [ ] Same endpoint with a `.txt` file → 415
- [ ] Same endpoint on a claim_id that doesn't exist → 404
- [ ] `GET /api/claims/{id}/evidence` → lists uploaded photos
- [ ] `DELETE /api/evidence/{id}` → 204, and the file is gone from
      `backend/uploads/{claim_id}/`

---

## 8. Known limitations

- **Orphaned draft claims**: as explained in §2, a claim is created before
  the farmer reaches Review. If they abandon the flow after that point,
  the claim persists with no evidence and no final confirmation. There's
  no scheduled cleanup job for this yet.
- **No image compression/resizing**: photos are stored as uploaded. A
  farmer on a low-end phone with large camera photos will use more of the
  10MB budget per image than necessary; client-side resizing before
  upload would help but wasn't in scope here.
- **No malware/EXIF scanning**: files are verified to be genuine, decodable
  images (via Pillow) but are not scanned for embedded malicious content
  or stripped of EXIF metadata (e.g. GPS coordinates in photo metadata are
  preserved as-is).
- **Local disk storage only**: `backend/uploads/` is local to wherever the
  backend runs. This is fine for the hackathon demo but won't survive a
  redeploy or scale past a single instance — a real deployment would need
  object storage (S3-compatible or similar).
- **No retry/resume on failed uploads**: a failed upload can be dismissed
  and re-selected, but there's no automatic retry or resumable upload
  support for flaky rural connectivity, which is exactly the kind of
  environment this project targets. Left for a later module.
- **Evidence step has no "skip explicitly" affordance beyond just clicking
  Continue with zero photos** — zero photos is allowed, but there's no
  distinct "I have no photos" confirmation versus "I forgot to upload."
