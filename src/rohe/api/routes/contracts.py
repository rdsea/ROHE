from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from rohe.repositories.base import ContractRepository

logger = logging.getLogger(__name__)


class ContractCreateRequest(BaseModel):
    contract_id: str
    tenant_id: str
    pipeline_id: str
    effective_from: str
    effective_until: str | None = None
    performance_slo: dict[str, Any]
    quality_slo: dict[str, Any]


class CDMCreateRequest(BaseModel):
    name: str
    metric_type: str
    expression: dict[str, Any]
    window: str | None = None
    description: str | None = None


class StatusResponse(BaseModel):
    status: str
    data: dict[str, Any] = {}


def create_contracts_router(repo: ContractRepository) -> APIRouter:
    """Create contracts CRUD router with injected repository."""
    router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])

    @router.post("/")
    async def create_contract(req: ContractCreateRequest) -> StatusResponse:
        existing = repo.get_contract(req.contract_id)
        if existing is not None:
            raise HTTPException(
                status_code=409, detail=f"Contract '{req.contract_id}' already exists"
            )
        contract_id = repo.create_contract(req.model_dump())
        return StatusResponse(status="created", data={"contract_id": contract_id})

    @router.get("/{contract_id}")
    async def get_contract(contract_id: str) -> StatusResponse:
        contract = repo.get_contract(contract_id)
        if contract is None:
            raise HTTPException(
                status_code=404, detail=f"Contract '{contract_id}' not found"
            )
        return StatusResponse(status="ok", data=contract)

    @router.get("/")
    async def list_contracts(
        tenant_id: str | None = None,
        pipeline_id: str | None = None,
    ) -> StatusResponse:
        contracts = repo.list_contracts(tenant_id=tenant_id, pipeline_id=pipeline_id)
        return StatusResponse(status="ok", data={"contracts": contracts})

    @router.put("/{contract_id}")
    async def update_contract(
        contract_id: str, updates: dict[str, Any]
    ) -> StatusResponse:
        updated = repo.update_contract(contract_id, updates)
        if not updated:
            raise HTTPException(
                status_code=404, detail=f"Contract '{contract_id}' not found"
            )
        return StatusResponse(status="updated", data={"contract_id": contract_id})

    @router.delete("/{contract_id}")
    async def deactivate_contract(contract_id: str) -> StatusResponse:
        deactivated = repo.deactivate_contract(contract_id)
        if not deactivated:
            raise HTTPException(
                status_code=404, detail=f"Contract '{contract_id}' not found"
            )
        return StatusResponse(status="deactivated", data={"contract_id": contract_id})

    # --- CDM definitions ---

    @router.post("/cdms")
    async def create_cdm(req: CDMCreateRequest) -> StatusResponse:
        repo.upsert_cdm(req.model_dump())
        return StatusResponse(status="created", data={"name": req.name})

    @router.get("/cdms")
    async def list_cdms() -> StatusResponse:
        cdms = repo.list_cdms()
        return StatusResponse(status="ok", data={"cdms": cdms})

    @router.get("/cdms/{cdm_name}")
    async def get_cdm(cdm_name: str) -> StatusResponse:
        cdm = repo.get_cdm(cdm_name)
        if cdm is None:
            raise HTTPException(status_code=404, detail=f"CDM '{cdm_name}' not found")
        return StatusResponse(status="ok", data=cdm)

    return router
