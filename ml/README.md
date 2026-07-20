# Plant Disease Classifier — MobileNetV2 (PyTorch)

A production-ready training pipeline that fine-tunes a pretrained **MobileNetV2**
to classify leaf images into **Healthy**, **Powdery**, or **Rust**.

Built with PyTorch + torchvision only (no TensorFlow/Keras).

---

## 1. Project structure

Place this project so your dataset sits alongside the scripts, exactly like this:

```
ml/
├── dataset/
│   ├── Train/
│   │   ├── Healthy/
│   │   ├── Powdery/
│   │   └── Rust/
│   ├── Validation/
│   │   ├── Healthy/
│   │   ├── Powdery/
│   │   └── Rust/
│   └── Test/
│       ├── Healthy/
│       ├── Powdery/
│       └── Rust/
│
├── config.py          # all hyperparameters and paths
├── utils.py            # model builder, EarlyStopping, plotting, logging helpers
├── train.py             # training entry point
├── evaluate.py           # test-set evaluation entry point
├── requirements.txt
└── README.md
```

After training and evaluation, an `outputs/` folder is created automatically:

```
outputs/
├── checkpoints/
│   ├── best_model.pth          # weights with the lowest validation loss
│   ├── last_model.pth          # weights from the final epoch
│   ├── class_names.json        # ["Healthy", "Powdery", "Rust"]
│   └── training_history.json   # per-epoch loss/accuracy/lr
├── plots/
│   ├── loss.png
│   ├── accuracy.png
│   └── confusion_matrix.png
└── logs/
    ├── training.log
    ├── evaluation.log
    ├── classification_report.txt
    └── test_results.json
```

---

## 2. Installation

Requires **Python 3.11+**.

```bash
cd ml
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> **GPU users:** the default `torch`/`torchvision` from PyPI installs a CUDA-enabled
> build automatically on most systems. If you need a specific CUDA version, install
> torch first from https://pytorch.org/get-started/locally/ and then run
> `pip install -r requirements.txt` for the remaining packages.

---

## 3. Training

Everything is configured in `config.py` — no command-line arguments needed.

```bash
python train.py
```

What happens:
1. Prints the device being used (`cuda` or `cpu`).
2. Loads `dataset/Train` and `dataset/Validation` with `ImageFolder`, auto-detects
   classes, and prints them (`Healthy`, `Powdery`, `Rust`) before training starts.
3. Builds MobileNetV2 with ImageNet-pretrained weights, freezes the convolutional
   feature extractor, and attaches a new classifier head:
   `Dropout(0.3) → Linear(1280, 512) → ReLU → Dropout(0.3) → Linear(512, 3)`.
4. Trains with `CrossEntropyLoss` + `Adam`, `ReduceLROnPlateau` (watches validation
   loss), and early stopping.
5. Every epoch prints: `Epoch | Train Loss | Train Acc | Val Loss | Val Acc | LR`.
6. Saves `best_model.pth` (whenever validation loss improves) and `last_model.pth`
   (every epoch), plus `class_names.json` and `training_history.json`.
7. At the end, saves `accuracy.png` and `loss.png` to `outputs/plots/`.

### Changing hyperparameters

Edit `config.py`:

```python
BATCH_SIZE = 32
EPOCHS = 30
LEARNING_RATE = 1e-3
NUM_WORKERS = 4
IMAGE_SIZE = 224
```

If your dataset is located somewhere else, update `DATASET_DIR` in `config.py`
(or the individual `TRAIN_DIR` / `VALIDATION_DIR` / `TEST_DIR` paths).

---

## 4. Evaluation

Once training has produced `outputs/checkpoints/best_model.pth`, run:

```bash
python evaluate.py
```

What happens:
1. Loads `class_names.json` and the `best_model.pth` checkpoint.
2. Runs inference over `dataset/Test`.
3. Prints and saves:
   - Overall test loss and accuracy
   - Confusion matrix (console + `outputs/plots/confusion_matrix.png`)
   - Full classification report — precision, recall, f1-score per class
     (console + `outputs/logs/classification_report.txt` + `outputs/logs/test_results.json`)

---

## 5. Re-running

- `train.py` can be re-run at any time; it overwrites `last_model.pth` every
  epoch and `best_model.pth` whenever validation loss improves, and appends to
  `outputs/logs/training.log`.
- `evaluate.py` always evaluates whatever is currently saved at
  `outputs/checkpoints/best_model.pth`.

---

## 6. Troubleshooting

| Issue | Fix |
|---|---|
| `FileNotFoundError` on `dataset/Train` | Confirm the dataset folder is at `ml/dataset/...` exactly as shown above, or update `DATASET_DIR` in `config.py`. |
| Very slow training on CPU | Reduce `IMAGE_SIZE`/`BATCH_SIZE` in `config.py`, or run on a CUDA-enabled machine — the script auto-detects and uses GPU if available. |
| `RuntimeError` about DataLoader workers on Windows | Set `NUM_WORKERS = 0` in `config.py`. |
| Class order looks wrong | `ImageFolder` orders classes alphabetically (`Healthy`, `Powdery`, `Rust`); this is saved in `class_names.json` and used consistently by both scripts. |
