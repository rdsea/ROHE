from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.server_api import ServerApi

from .base import (
    ContractRepository,
    ExperimentRepository,
    MetricRepository,
    NodeRepository,
    PipelineRepository,
    ServiceRepository,
)

logger = logging.getLogger(__name__)


def create_mongo_client(uri: str) -> MongoClient[dict[str, Any]]:
    """Create a MongoDB client from a connection URI."""
    client: MongoClient[dict[str, Any]] = MongoClient(uri, server_api=ServerApi("1"))
    client.admin.command("ping")
    logger.info("Connected to MongoDB successfully")
    return client


class MongoNodeRepository(NodeRepository):
    """MongoDB implementation of NodeRepository."""

    def __init__(
        self, db: Database[dict[str, Any]], collection_name: str = "nodes"
    ) -> None:
        self._collection: Collection[dict[str, Any]] = db[collection_name]

    def get_node(self, node_name: str) -> dict[str, Any] | None:
        result = self._collection.find_one({"node_name": node_name})
        if result is not None:
            result.pop("_id", None)
        return result

    def get_all_nodes(self) -> list[dict[str, Any]]:
        results = list(self._collection.find({}))
        for r in results:
            r.pop("_id", None)
        return results

    def upsert_node(self, node_name: str, node_data: dict[str, Any]) -> None:
        self._collection.update_one(
            {"node_name": node_name},
            {"$set": node_data},
            upsert=True,
        )

    def delete_node(self, node_name: str) -> bool:
        result = self._collection.delete_one({"node_name": node_name})
        return result.deleted_count > 0


class MongoServiceRepository(ServiceRepository):
    """MongoDB implementation of ServiceRepository."""

    def __init__(
        self, db: Database[dict[str, Any]], collection_name: str = "services"
    ) -> None:
        self._collection: Collection[dict[str, Any]] = db[collection_name]

    def get_service(self, service_name: str) -> dict[str, Any] | None:
        result = self._collection.find_one({"service_name": service_name})
        if result is not None:
            result.pop("_id", None)
        return result

    def get_all_services(self) -> list[dict[str, Any]]:
        results = list(self._collection.find({}))
        for r in results:
            r.pop("_id", None)
        return results

    def upsert_service(self, service_name: str, service_data: dict[str, Any]) -> None:
        self._collection.update_one(
            {"service_name": service_name},
            {"$set": service_data},
            upsert=True,
        )

    def delete_service(self, service_name: str) -> bool:
        result = self._collection.delete_one({"service_name": service_name})
        return result.deleted_count > 0


class MongoMetricRepository(MetricRepository):
    """MongoDB implementation of MetricRepository.

    Stores per-request and per-period metrics with timestamp-based queries.
    """

    def __init__(
        self, db: Database[dict[str, Any]], collection_name: str = "metrics"
    ) -> None:
        self._collection: Collection[dict[str, Any]] = db[collection_name]
        self._collection.create_index([("timestamp", DESCENDING)])
        self._collection.create_index("experiment_id")
        self._collection.create_index("pipeline_id")

    def insert_metric(self, metric: dict[str, Any]) -> str:
        if "timestamp" not in metric:
            metric["timestamp"] = datetime.now()
        result = self._collection.insert_one(metric)
        return str(result.inserted_id)

    def insert_metrics_batch(self, metrics: list[dict[str, Any]]) -> int:
        if not metrics:
            return 0
        now = datetime.now()
        for m in metrics:
            if "timestamp" not in m:
                m["timestamp"] = now
        result = self._collection.insert_many(metrics)
        return len(result.inserted_ids)

    def query_metrics(
        self,
        filters: dict[str, Any] | None = None,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = filters.copy() if filters else {}
        if time_from or time_to:
            time_filter: dict[str, Any] = {}
            if time_from:
                time_filter["$gte"] = time_from
            if time_to:
                time_filter["$lte"] = time_to
            query["timestamp"] = time_filter

        results = list(
            self._collection.find(query).sort("timestamp", DESCENDING).limit(limit)
        )
        for r in results:
            r.pop("_id", None)
        return results

    def aggregate_metrics(
        self,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return list(self._collection.aggregate(pipeline))

    def delete_metrics(
        self,
        filters: dict[str, Any],
    ) -> int:
        result = self._collection.delete_many(filters)
        return result.deleted_count


class MongoContractRepository(ContractRepository):
    """MongoDB implementation of ContractRepository."""

    def __init__(
        self, db: Database[dict[str, Any]], collection_name: str = "contracts"
    ) -> None:
        self._contracts: Collection[dict[str, Any]] = db[collection_name]
        self._cdms: Collection[dict[str, Any]] = db["cdm_definitions"]
        self._contracts.create_index("contract_id", unique=True)
        self._cdms.create_index("name", unique=True)

    def get_contract(self, contract_id: str) -> dict[str, Any] | None:
        result = self._contracts.find_one({"contract_id": contract_id})
        if result is not None:
            result.pop("_id", None)
        return result

    def list_contracts(
        self,
        tenant_id: str | None = None,
        pipeline_id: str | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if tenant_id:
            query["tenant_id"] = tenant_id
        if pipeline_id:
            query["pipeline_id"] = pipeline_id
        if is_active is not None:
            now = datetime.now().isoformat()
            if is_active:
                query["effective_from"] = {"$lte": now}
                query["$or"] = [
                    {"effective_until": None},
                    {"effective_until": {"$gte": now}},
                ]
            else:
                query["effective_until"] = {"$lt": now}

        results = list(self._contracts.find(query))
        for r in results:
            r.pop("_id", None)
        return results

    def create_contract(self, contract: dict[str, Any]) -> str:
        self._contracts.insert_one(contract)
        return str(contract["contract_id"])

    def update_contract(self, contract_id: str, updates: dict[str, Any]) -> bool:
        result = self._contracts.update_one(
            {"contract_id": contract_id},
            {"$set": updates},
        )
        return result.modified_count > 0

    def deactivate_contract(self, contract_id: str) -> bool:
        return self.update_contract(
            contract_id, {"deactivated_at": datetime.now().isoformat()}
        )

    def get_cdm(self, cdm_name: str) -> dict[str, Any] | None:
        result = self._cdms.find_one({"name": cdm_name})
        if result is not None:
            result.pop("_id", None)
        return result

    def list_cdms(self) -> list[dict[str, Any]]:
        results = list(self._cdms.find({}))
        for r in results:
            r.pop("_id", None)
        return results

    def upsert_cdm(self, cdm: dict[str, Any]) -> None:
        self._cdms.update_one(
            {"name": cdm["name"]},
            {"$set": cdm},
            upsert=True,
        )


class MongoPipelineRepository(PipelineRepository):
    """MongoDB implementation of PipelineRepository."""

    def __init__(
        self, db: Database[dict[str, Any]], collection_name: str = "applications"
    ) -> None:
        self._collection: Collection[dict[str, Any]] = db[collection_name]
        self._collection.create_index("application_name", unique=True)

    def get_application(self, application_name: str) -> dict[str, Any] | None:
        result = self._collection.find_one({"application_name": application_name})
        if result is not None:
            result.pop("_id", None)
        return result

    def register_application(self, app_data: dict[str, Any]) -> str:
        self._collection.insert_one(app_data)
        return str(app_data.get("application_name", ""))

    def update_application(
        self, application_name: str, updates: dict[str, Any]
    ) -> bool:
        result = self._collection.update_one(
            {"application_name": application_name},
            {"$set": updates},
        )
        return result.modified_count > 0

    def delete_application(self, application_name: str) -> bool:
        result = self._collection.delete_one({"application_name": application_name})
        return result.deleted_count > 0

    def list_applications(self) -> list[dict[str, Any]]:
        results = list(self._collection.find({}))
        for r in results:
            r.pop("_id", None)
        return results


class MongoExperimentRepository(ExperimentRepository):
    """MongoDB implementation of ExperimentRepository."""

    def __init__(
        self, db: Database[dict[str, Any]], collection_name: str = "experiments"
    ) -> None:
        self._collection: Collection[dict[str, Any]] = db[collection_name]
        self._collection.create_index("experiment_id", unique=True)
        self._collection.create_index("name")

    def create_experiment(self, experiment: dict[str, Any]) -> str:
        self._collection.insert_one(experiment)
        return str(experiment["experiment_id"])

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        result = self._collection.find_one({"experiment_id": experiment_id})
        if result is not None:
            result.pop("_id", None)
        return result

    def get_experiment_by_name(self, name: str) -> dict[str, Any] | None:
        result = self._collection.find_one({"name": name})
        if result is not None:
            result.pop("_id", None)
        return result

    def update_experiment(self, experiment_id: str, updates: dict[str, Any]) -> bool:
        result = self._collection.update_one(
            {"experiment_id": experiment_id},
            {"$set": updates},
        )
        return result.modified_count > 0

    def list_experiments(
        self,
        status: str | None = None,
        pipeline_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        if pipeline_id:
            query["pipeline_id"] = pipeline_id
        results = list(self._collection.find(query).sort("created_at", DESCENDING))
        for r in results:
            r.pop("_id", None)
        return results

    def delete_experiment(self, experiment_id: str) -> bool:
        result = self._collection.delete_one({"experiment_id": experiment_id})
        return result.deleted_count > 0
