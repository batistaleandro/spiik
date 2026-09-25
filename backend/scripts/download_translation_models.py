"""Pre-download the Marian translation models for offline translation.

The Docker image runs this at build time; run it manually for local
development so the local provider activates without a first-use stall:

    cd backend && .venv/bin/python -m scripts.download_translation_models
"""

from __future__ import annotations

from huggingface_hub import snapshot_download

from app.translate_local import MODEL_IDS


def main() -> None:
    for model_id in MODEL_IDS:
        print(f"downloading {model_id} ...")
        snapshot_download(model_id)
    print(f"done: {len(MODEL_IDS)} models cached")


if __name__ == "__main__":
    main()
