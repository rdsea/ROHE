from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MLServicePerformance(BaseModel):
    model: str
    infrastructure: str
    last_update: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    scale: int | None = None
    base_cost: float | None = None

    def to_dict(self) -> dict[str, Any]:
        self_dict: dict[str, Any] = self.model_dump()
        if self.metrics is not None:
            self_dict.pop("metrics")
            self_dict.update(self.metrics)
        if self.last_update is not None:
            self_dict.pop("last_update")
            self_dict["last_update_ml_metric"] = self.last_update["ml_metric"]
            self_dict["last_update_infrastructure"] = self.last_update["infrastructure"]
        return self_dict
