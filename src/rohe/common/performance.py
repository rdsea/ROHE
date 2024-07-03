from pydantic import BaseModel


class MLServicePerformance(BaseModel):
    model: str
    infrastructure: str
    last_update: dict = None
    metrics: dict = None
    scale: int = None
    base_cost: float = None

    def to_dict(self):
        self_dict = dict(self)
        if self.metrics is not None:
            self_dict.pop("metrics")
            self_dict.update(self.metrics)
        if self.last_update is not None:
            self_dict.pop("last_update")
            self_dict["last_update_ml_metric"] = self.last_update["ml_metric"]
            self_dict["last_update_infrastructure"] = self.last_update["infrastructure"]
        return self_dict
