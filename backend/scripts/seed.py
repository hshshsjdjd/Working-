"""Idempotent seed for model catalog + singleton rows.

Model IDs below are real NVIDIA NIM catalog identifiers served by the
OpenAI-compatible endpoint at https://integrate.api.nvidia.com/v1. Update this
list (or use the admin API) to add/remove models.
"""
from __future__ import annotations

from app.db import SessionLocal
from app.models import MaintenanceState, ModelConfig

MODELS = [
    {
        "id": "meta/llama-3.1-8b-instruct",
        "display_name": "Llama 3.1 8B Instruct",
        "description": "Fast, lightweight general-purpose chat model.",
        "capabilities": ["chat", "code"],
        "context_window": 128000,
        "supports_vision": False,
        "sort_order": 10,
    },
    {
        "id": "meta/llama-3.1-70b-instruct",
        "display_name": "Llama 3.1 70B Instruct",
        "description": "High-quality general-purpose reasoning and code.",
        "capabilities": ["chat", "code", "reasoning"],
        "context_window": 128000,
        "supports_vision": False,
        "sort_order": 20,
    },
    {
        "id": "nvidia/llama-3.1-nemotron-70b-instruct",
        "display_name": "Llama 3.1 Nemotron 70B",
        "description": "NVIDIA-tuned Nemotron model optimized for helpfulness.",
        "capabilities": ["chat", "code", "reasoning"],
        "context_window": 128000,
        "supports_vision": False,
        "sort_order": 30,
    },
    {
        "id": "mistralai/mixtral-8x7b-instruct-v0.1",
        "display_name": "Mixtral 8x7B Instruct",
        "description": "Mixture-of-experts model with strong efficiency.",
        "capabilities": ["chat", "code"],
        "context_window": 32768,
        "supports_vision": False,
        "sort_order": 40,
    },
    {
        "id": "meta/llama-3.2-11b-vision-instruct",
        "display_name": "Llama 3.2 11B Vision",
        "description": "Multimodal model that accepts text and images.",
        "capabilities": ["chat", "vision"],
        "context_window": 128000,
        "supports_vision": True,
        "sort_order": 50,
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        for entry in MODELS:
            existing = db.get(ModelConfig, entry["id"])
            if existing is None:
                db.add(ModelConfig(**entry))
            else:
                # Refresh descriptive fields but preserve admin toggles.
                existing.display_name = entry["display_name"]
                existing.description = entry["description"]
                existing.capabilities = entry["capabilities"]
                existing.context_window = entry["context_window"]
                existing.supports_vision = entry["supports_vision"]
        if db.get(MaintenanceState, 1) is None:
            db.add(MaintenanceState(id=1, maintenance_mode=False))
        db.commit()
        print(f"Seeded {len(MODELS)} models.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
