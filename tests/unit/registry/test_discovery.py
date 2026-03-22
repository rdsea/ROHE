from __future__ import annotations

from rohe.registry.discovery import HttpRegistryDiscovery, K8sServiceDiscovery, create_service_discovery


class TestHttpRegistryDiscovery:
    def test_register_and_discover(self):
        disc = HttpRegistryDiscovery()
        iid = disc.register("yolov8n", "10.0.0.1", 8080, {"model": "yolov8n"})

        instances = disc.discover("yolov8n")
        assert len(instances) == 1
        assert instances[0]["service_name"] == "yolov8n"
        assert instances[0]["host"] == "10.0.0.1"
        assert instances[0]["port"] == 8080
        assert instances[0]["metadata"]["model"] == "yolov8n"
        assert instances[0]["instance_id"] == iid

    def test_discover_empty(self):
        disc = HttpRegistryDiscovery()
        assert disc.discover("nonexistent") == []

    def test_deregister(self):
        disc = HttpRegistryDiscovery()
        iid = disc.register("svc", "localhost", 9090)
        assert disc.deregister(iid)
        assert disc.discover("svc") == []

    def test_deregister_nonexistent(self):
        disc = HttpRegistryDiscovery()
        assert not disc.deregister("fake-id")

    def test_multiple_services(self):
        disc = HttpRegistryDiscovery()
        disc.register("yolov8n", "10.0.0.1", 8080)
        disc.register("yolov8n", "10.0.0.2", 8080)
        disc.register("resnet50", "10.0.0.3", 8081)

        yolo_instances = disc.discover("yolov8n")
        assert len(yolo_instances) == 2

        resnet_instances = disc.discover("resnet50")
        assert len(resnet_instances) == 1

    def test_health_check(self):
        disc = HttpRegistryDiscovery()
        assert disc.health_check()


class TestK8sServiceDiscovery:
    def test_discover_dns(self):
        disc = K8sServiceDiscovery(namespace="ml-services")
        instances = disc.discover("yolov8n")
        assert len(instances) == 1
        assert instances[0]["dns"] == "yolov8n.ml-services.svc.cluster.local"

    def test_register_noop(self):
        disc = K8sServiceDiscovery()
        iid = disc.register("svc", "localhost", 8080)
        assert "svc" in iid

    def test_deregister_noop(self):
        disc = K8sServiceDiscovery()
        assert disc.deregister("any-id")


class TestCreateServiceDiscovery:
    def test_auto_detect_non_k8s(self, monkeypatch):
        monkeypatch.delenv("ROHE_DISCOVERY_MODE", raising=False)
        disc = create_service_discovery()
        assert isinstance(disc, HttpRegistryDiscovery)

    def test_force_http(self, monkeypatch):
        monkeypatch.setenv("ROHE_DISCOVERY_MODE", "http")
        disc = create_service_discovery()
        assert isinstance(disc, HttpRegistryDiscovery)

    def test_force_k8s(self, monkeypatch):
        monkeypatch.setenv("ROHE_DISCOVERY_MODE", "k8s")
        disc = create_service_discovery()
        assert isinstance(disc, K8sServiceDiscovery)
