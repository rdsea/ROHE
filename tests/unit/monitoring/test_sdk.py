from __future__ import annotations

import time

from rohe.monitoring.sdk import RoheMonitor
from rohe.monitoring.transport import NoopTransport


class TestRoheMonitor:
    def _make_monitor(self, batch_size: int = 100) -> tuple[RoheMonitor, NoopTransport]:
        transport = NoopTransport()
        monitor = RoheMonitor(
            endpoint="http://test:5010/metrics",
            service_name="test-service",
            experiment_id="exp-001",
            transport=transport,
            batch_size=batch_size,
            flush_interval_seconds=999,  # disable auto-flush for tests
        )
        return monitor, transport

    def test_report_metric(self):
        monitor, transport = self._make_monitor()
        monitor.report_metric("accuracy", 0.95, labels={"model": "yolov8n"})
        monitor.flush()
        monitor.close()

        assert len(transport.sent) == 1
        batch = transport.sent[0]
        assert len(batch) == 1
        assert batch[0].name == "accuracy"
        assert batch[0].value == 0.95
        assert batch[0].labels["model"] == "yolov8n"
        assert batch[0].service_name == "test-service"
        assert batch[0].experiment_id == "exp-001"

    def test_report_inference(self):
        monitor, transport = self._make_monitor()
        monitor.report_inference(
            query_id="q-001",
            predictions={"car": 0.92, "truck": 0.05},
            confidence=0.92,
            response_time_ms=45.2,
            labels={"model": "yolov8n", "device": "jetson"},
        )
        monitor.flush()
        monitor.close()

        batch = transport.sent[0]
        assert batch[0].query_id == "q-001"
        assert batch[0].predictions == {"car": 0.92, "truck": 0.05}
        assert batch[0].confidence == 0.92
        assert batch[0].response_time_ms == 45.2
        assert batch[0].metric_type == "inference"

    def test_report_request_with_ground_truth(self):
        monitor, transport = self._make_monitor()
        monitor.report_request(
            query_id="q-001",
            pipeline_id="cctvs-detection",
            response_time_ms=52.3,
            ground_truth="car",
            prediction={"car": 0.92},
        )
        monitor.flush()
        monitor.close()

        batch = transport.sent[0]
        assert batch[0].ground_truth == "car"
        assert batch[0].metric_type == "request"
        assert batch[0].labels["pipeline_id"] == "cctvs-detection"

    def test_batch_auto_flush(self):
        monitor, transport = self._make_monitor(batch_size=3)
        monitor.report_metric("m1", 1.0)
        monitor.report_metric("m2", 2.0)
        assert len(transport.sent) == 0  # not yet flushed

        monitor.report_metric("m3", 3.0)  # triggers batch flush
        assert len(transport.sent) == 1
        assert len(transport.sent[0]) == 3
        monitor.close()

    def test_flush_empty_buffer(self):
        monitor, transport = self._make_monitor()
        monitor.flush()  # should not crash
        monitor.close()
        assert len(transport.sent) == 0

    def test_multiple_flushes(self):
        monitor, transport = self._make_monitor()
        monitor.report_metric("m1", 1.0)
        monitor.flush()
        monitor.report_metric("m2", 2.0)
        monitor.flush()
        monitor.close()

        assert len(transport.sent) == 2
        assert transport.sent[0][0].name == "m1"
        assert transport.sent[1][0].name == "m2"

    def test_track_inference_decorator(self):
        monitor, transport = self._make_monitor()

        @monitor.track_inference
        def predict(data):
            time.sleep(0.01)
            return {
                "query_id": "q-auto",
                "predictions": {"car": 0.88},
                "confidence": 0.88,
            }

        result = predict("image_data")
        monitor.flush()
        monitor.close()

        assert result["query_id"] == "q-auto"
        assert len(transport.sent) == 1
        batch = transport.sent[0]
        assert batch[0].query_id == "q-auto"
        assert batch[0].response_time_ms > 0

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("ROHE_ENDPOINT", "http://custom:9999/metrics")
        monkeypatch.setenv("ROHE_SERVICE_NAME", "my-service")
        monkeypatch.setenv("ROHE_EXPERIMENT_ID", "exp-42")

        monitor = RoheMonitor.from_env()
        assert monitor._service_name == "my-service"
        assert monitor._experiment_id == "exp-42"
        monitor.close()

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("ROHE_ENDPOINT", raising=False)
        monkeypatch.delenv("ROHE_SERVICE_NAME", raising=False)
        monkeypatch.delenv("ROHE_EXPERIMENT_ID", raising=False)

        monitor = RoheMonitor.from_env()
        assert monitor._service_name == "unknown"
        assert monitor._experiment_id is None
        monitor.close()
