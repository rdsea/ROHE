"""ResNet-50 inference service."""
from __future__ import annotations

import io
import logging
import time

import torch
import torchvision.models as models
import torchvision.transforms as transforms
from fastapi import FastAPI, File, Form, UploadFile
from PIL import Image

logger = logging.getLogger(__name__)

MODEL_NAME = "resnet50"
app = FastAPI(title=f"{MODEL_NAME} Inference Service")

# Load model at startup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1).to(device)
model.eval()

# ImageNet class labels (top-level import for speed)
weights = models.ResNet50_Weights.IMAGENET1K_V1
categories = weights.meta["categories"]

preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Optional rohe-sdk monitoring
try:
    from rohe.monitoring.sdk import RoheMonitor
    monitor = RoheMonitor.from_env()
except Exception:
    monitor = None  # type: ignore[assignment]


@app.post("/predict")
async def predict(
    image: UploadFile = File(...),
    query_id: str = Form("unknown"),
) -> dict:
    """Run ResNet-50 inference on uploaded image."""
    start = time.perf_counter()

    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    input_tensor = preprocess(img).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(input_tensor)
        probabilities = torch.nn.functional.softmax(output[0], dim=0)

    top_k = 10
    top_probs, top_indices = torch.topk(probabilities, top_k)
    predictions = {
        categories[idx.item()]: round(prob.item(), 4)
        for prob, idx in zip(top_probs, top_indices)
    }
    confidence = top_probs[0].item()
    elapsed_ms = (time.perf_counter() - start) * 1000

    if monitor:
        monitor.report_inference(
            query_id=query_id,
            predictions=predictions,
            confidence=confidence,
            response_time_ms=elapsed_ms,
            labels={"model": MODEL_NAME, "device": str(device)},
        )

    return {
        "query_id": query_id,
        "predictions": predictions,
        "confidence": round(confidence, 4),
        "model": MODEL_NAME,
        "response_time_ms": round(elapsed_ms, 2),
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME, "device": str(device)}
