# FasalBima Pramaan — Crop Damage Classifier (EfficientNetB0 + TensorFlow/Keras)

Classifies crop photos into **Healthy**, **Flood Damage**, **Drought Stress**,
or **Pest Attack**, to be used as supplementary AI evidence in PMFBY crop
insurance claims.

This replaces the previous PyTorch/MobileNetV2 PlantVillage classifier
(Healthy / Powdery / Rust), which was not relevant to crop-insurance claims.

---

## 1. Project structure

```
ml/
├── dataset/
│   ├── train/
│   │   ├── healthy/    (30)
│   │   ├── flood/      (26)
│   │   ├── drought/    (23)
│   │   └── pest/       (33)
│   └── val/
│       ├── healthy/    (7)
│       ├── flood/      (7)
│       ├── drought/    (6)
│       └── pest/       (8)
│
├── config.py             # all hyperparameters, paths, class label mapping
├── utils.py               # model builder, fine-tuning helpers, class weights, plotting, export
├── evaluation.py            # confusion matrix + classification report (also runnable standalone)
├── train.py                   # training entry point (two-phase: warmup -> fine-tune)
├── inference.py                 # single-image prediction, importable by FastAPI
├── requirements.txt
├── README.md
│
└── backend_integration/     # reference files for wiring into your FastAPI backend
    ├── classifier_service.py     # service-layer wrapper -> copy into your backend
    ├── example_router_usage.py    # example FastAPI route using the service
    └── pdf_section.py              # "AI Crop Damage Assessment" PDF section
```

After training, an `outputs/` folder is created automatically:

```
outputs/
├── checkpoints/
│   ├── best_model.keras         # best model across BOTH phases by val_loss -- USE THIS ONE
│   ├── last_model.keras          # weights from the final fine-tuning epoch
│   ├── class_names.json           # ["drought", "flood", "healthy", "pest"] (folder names, index order)
│   ├── labels.json                 # {"0": "Drought Stress", "1": "Flood Damage", ...} -- what inference.py reads
│   └── training_history.json       # per-epoch loss/accuracy/lr, phase 1 + phase 2 merged
├── plots/
│   ├── loss.png                  # dashed line marks where fine-tuning starts
│   └── accuracy.png
├── evaluation/
│   ├── confusion_matrix.png
│   ├── classification_report.txt    # precision / recall / F1 per class, human-readable
│   └── classification_report.json    # same, machine-readable
├── saved_model/                # TensorFlow SavedModel export, for deployment/serving
└── logs/
    └── training.log
```

---

## 2. Installation

```bash
cd ml
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## 3. Training

```bash
python train.py
```

What happens:

1. Loads `dataset/train` and `dataset/val` with `ImageDataGenerator.flow_from_directory`.
2. **Online augmentation only** on the training split (rotation, zoom,
   horizontal flip, brightness, width shift, height shift) — no new
   image files are ever written to disk.
3. Computes **class weights** (`sklearn.utils.class_weight.compute_class_weight`,
   `"balanced"`) from the train split's class counts and passes them into
   every `model.fit()` call, so "drought" (23 images) isn't drowned out by
   "pest" (33 images).
4. Builds **EfficientNetB0** (ImageNet weights) with a
   `GlobalAveragePooling2D -> Dropout -> Dense(256, relu) -> Dropout ->
   Dense(4, softmax)` head.
5. **Phase 1 — frozen-backbone warmup**: trains with `Adam(lr=1e-4)` +
   `categorical_crossentropy`, `EarlyStopping`, `ReduceLROnPlateau`, and
   `ModelCheckpoint` (saves the best epoch by `val_loss`).
6. **Phase 2 — fine-tuning**: reloads the best phase-1 checkpoint,
   unfreezes the **top 25 layers** of the EfficientNetB0 backbone
   (BatchNormalization layers are always kept frozen), recompiles at
   `Adam(lr=1e-5)`, and continues training for **5 epochs**. The
   checkpoint callback is seeded with phase 1's best `val_loss`, so
   `best_model.keras` only gets overwritten if fine-tuning genuinely
   improves on phase 1 — whichever phase actually produced the better
   checkpoint is what you end up with.
7. Reloads the true best checkpoint and runs **evaluation**: confusion
   matrix + classification report (precision/recall/F1 per class) on the
   validation split.
8. Saves `labels.json`, exports a **TensorFlow SavedModel** to
   `outputs/saved_model/`, and writes merged loss/accuracy plots (phase 1
   + phase 2, with a dashed marker at the fine-tuning boundary).

Image size is 224×224 and batch size is 8, per project requirements — both
configurable in `config.py`, along with `FT_UNFREEZE_LAYERS`, `FT_EPOCHS`,
and `FT_LEARNING_RATE` for the fine-tuning phase.

### If ImageNet weights can't be downloaded

`utils.build_model` tries to download ImageNet weights for EfficientNetB0
first. If that fails (e.g. no internet access in the training environment),
it **keeps the EfficientNetB0 architecture** and falls back to random
weight initialization instead, logging a clear warning both to the console
and to `outputs/logs/training.log`. This is a deliberate change from the
previous version, which silently switched to a completely different
architecture (MobileNetV2) on failure — that could quietly break the
"use EfficientNetB0" requirement and make the fine-tuning step
(unfreezing "the last 20-30 EfficientNet layers") meaningless if the
network happened to be down on a given run. With this fallback, the
architecture is always EfficientNetB0; only the starting weights differ,
and you'll know immediately (from the log) if that happened, since accuracy
without ImageNet transfer learning will be noticeably lower — especially
on a dataset this small.

## 4. Evaluation (standalone)

```bash
python evaluation.py
```

Re-runs evaluation against whatever is currently saved at
`outputs/checkpoints/best_model.keras` without retraining — useful if you
want to regenerate the confusion matrix / report after changing something
downstream (e.g. class display names) without a full retrain.

## 5. Inference

```bash
python inference.py path/to/photo.jpg
```

```
Prediction: Flood Damage
Confidence: 94.2%
All class probabilities:
  Flood Damage: 94.2%
  Healthy: 2.1%
  Drought Stress: 2.0%
  Pest Attack: 1.7%
```

`inference.predict_image()` returns:

```json
{
  "prediction": "Flood Damage",
  "confidence": 94.2,
  "probabilities": {
    "Flood Damage": 94.2,
    "Healthy": 2.1,
    "Drought Stress": 2.0,
    "Pest Attack": 1.7
  },
  "prediction_key": "flood",
  "all_probabilities": { "...": "same as probabilities, kept for backend_integration/ compatibility" }
}
```

Class labels are loaded from `outputs/checkpoints/labels.json` at runtime —
**nothing is hardcoded in `inference.py`**. If you retrain with a different
class set, this file needs no edits.

## 6. Backend integration

See `backend_integration/` — copy `classifier_service.py` into your FastAPI
backend's services folder, wire it into your claims router as shown in
`example_router_usage.py`, and use `pdf_section.py` to render the "AI Crop
Damage Assessment" block in the evidence PDF. These files read `result["prediction"]`,
`result["confidence"]`, and `result["all_probabilities"]` — all still present,
so no changes are needed there. Full instructions are in the docstring at
the top of each file.

## 7. Re-running

- `train.py` can be re-run anytime; it overwrites `last_model.keras` every
  fine-tuning epoch and `best_model.keras` whenever validation loss improves
  in either phase.
- `inference.py`, `evaluation.py`, and the FastAPI service always load
  whatever is currently saved at `outputs/checkpoints/best_model.keras`
  and `labels.json`.

## 8. A note on dataset size

The current dataset is small — **112 train / 28 validation images**, with
the smallest class ("drought") at 23 train / 6 validation images. Class
weighting and augmentation help, but with this few validation images per
class, precision/recall/F1 numbers will swing a lot between runs and
shouldn't be read as statistically robust — they're indicative for a
hackathon demo, not a production accuracy claim. Growing the dataset is the
highest-leverage next step for real-world accuracy.

## 9. Troubleshooting

| Issue | Fix |
|---|---|
| `FileNotFoundError` on `dataset/train` | Confirm the dataset folder is at `ml/dataset/...` exactly as shown above, or update `DATASET_DIR` in `config.py`. |
| ImageNet weights fail to download | Training continues with EfficientNetB0 (random init) instead of silently switching architectures — check `outputs/logs/training.log` for the warning, and expect lower accuracy on that run. |
| `FileNotFoundError` on `labels.json` in `inference.py` | Run `python train.py` at least once — it's generated automatically. Older checkpoints without it fall back to `class_names.json` + `config.CLASS_DISPLAY_NAMES` and regenerate it on first load. |
| SavedModel export warning in the log | Non-fatal — `best_model.keras` is still valid and is what `inference.py`/`evaluation.py` use either way. |
| Very slow training on CPU | Reduce `EPOCHS` in `config.py`, or train on a GPU-enabled machine. Phase 2 (fine-tuning) is slower per-epoch than phase 1 since more layers are trainable. |
| Class order looks wrong | `flow_from_directory` uses the explicit `classes=config.CLASS_FOLDER_NAMES` order (alphabetical: drought, flood, healthy, pest) — this is saved in `class_names.json` / `labels.json` and used consistently everywhere. |
