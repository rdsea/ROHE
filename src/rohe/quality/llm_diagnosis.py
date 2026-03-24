"""Tier 3 quality evaluation: LLM-assisted diagnosis and recommendations.

Uses an LLM (via OpenAI-compatible API, e.g., NVIDIA NIM) to analyze
SLA violations, metric patterns, and anomaly detection results, then
produce human-readable diagnoses and actionable remediation recommendations.

Configuration via environment variables:
  LLM_API_KEY: API key (or NVIDIA_API_KEY)
  LLM_BASE_URL: API base URL (default: https://integrate.api.nvidia.com/v1)
  LLM_MODEL: Model ID (default: nvidia/llama-3.1-nemotron-70b-instruct)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class DiagnosisResult(BaseModel):
    """Structured output from LLM diagnosis."""

    model_config = ConfigDict(frozen=True)

    pipeline_id: str
    timestamp: datetime
    summary: str  # one-paragraph diagnosis
    root_cause: str  # identified root cause
    severity: str  # "low", "medium", "high", "critical"
    recommendations: list[str]  # ordered list of actionable steps
    affected_modalities: list[str]
    affected_models: list[str]
    confidence: float  # LLM's self-assessed confidence in diagnosis (0-1)
    raw_response: str  # full LLM response for audit


class LLMDiagnosisEngine:
    """LLM-powered quality diagnosis engine.

    Analyzes violation events, metric trends, and anomaly detection results
    to produce structured diagnoses with remediation recommendations.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> None:
        self._api_key = api_key or os.environ.get(
            "LLM_API_KEY", os.environ.get("NVIDIA_API_KEY", "")
        )
        self._base_url = base_url or os.environ.get(
            "LLM_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        self._model = model or os.environ.get(
            "LLM_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1.5"
        )
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client: Any = None

    def _ensure_client(self) -> Any:
        """Lazy-initialize the OpenAI-compatible client."""
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise ValueError(
                "LLM API key required. Set LLM_API_KEY or NVIDIA_API_KEY env var."
            )
        try:
            import openai

            self._client = openai.OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=120.0,
            )
            logger.info(
                f"LLM client initialized: model={self._model}, base_url={self._base_url}"
            )
            return self._client
        except ImportError:
            raise ImportError("openai package required: pip install openai")

    def diagnose(
        self,
        pipeline_id: str,
        violations: list[dict[str, Any]],
        metric_summary: dict[str, Any] | None = None,
        anomaly_results: dict[str, Any] | None = None,
        plan_snapshot: dict[str, Any] | None = None,
    ) -> DiagnosisResult:
        """Run LLM diagnosis on quality violations.

        Args:
            pipeline_id: Pipeline that experienced violations
            violations: List of ViolationEvent dicts
            metric_summary: Summary statistics for recent metrics
            anomaly_results: Tier 2 anomaly detection results
            plan_snapshot: Current ExecutionPlan for context

        Returns:
            Structured DiagnosisResult with recommendations
        """
        client = self._ensure_client()

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            pipeline_id, violations, metric_summary, anomaly_results, plan_snapshot
        )

        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )

            message = response.choices[0].message
            raw_response = message.content or ""
            # Some reasoning models put the answer in content after <think> tags,
            # or return empty content with reasoning_content
            if not raw_response and hasattr(message, "reasoning_content"):
                raw_response = getattr(message, "reasoning_content", "") or ""
            return self._parse_response(pipeline_id, raw_response, violations)

        except Exception as e:
            logger.error(f"LLM diagnosis failed: {e}")
            return DiagnosisResult(
                pipeline_id=pipeline_id,
                timestamp=datetime.now(timezone.utc),
                summary=f"LLM diagnosis unavailable: {e}",
                root_cause="unknown",
                severity="medium",
                recommendations=["Manual investigation required"],
                affected_modalities=[],
                affected_models=[],
                confidence=0.0,
                raw_response=str(e),
            )

    def _build_system_prompt(self) -> str:
        return """You are an expert ML infrastructure diagnostician for the ROHE platform.
ROHE orchestrates multi-model inference pipelines on heterogeneous edge clusters.

Your job is to analyze SLA violations and metric anomalies, identify root causes,
and recommend specific remediation actions.

You must respond in valid JSON with this exact structure:
{
  "summary": "One paragraph diagnosis",
  "root_cause": "Identified root cause",
  "severity": "low|medium|high|critical",
  "recommendations": ["Step 1", "Step 2", ...],
  "affected_modalities": ["video", "timeseries", ...],
  "affected_models": ["model_name", ...],
  "confidence": 0.85
}

Focus on:
- Whether the issue is model quality degradation, hardware contention, or data drift
- Whether the issue is transient (spike) or sustained (trend)
- Specific actions: which models to add/remove, ensemble size changes, time budget reallocation
- Impact assessment: which modalities and models are affected"""

    def _build_user_prompt(
        self,
        pipeline_id: str,
        violations: list[dict[str, Any]],
        metric_summary: dict[str, Any] | None,
        anomaly_results: dict[str, Any] | None,
        plan_snapshot: dict[str, Any] | None,
    ) -> str:
        parts = [f"Pipeline: {pipeline_id}\n"]

        parts.append("## SLA Violations\n")
        for v in violations:
            parts.append(
                f"- {v.get('metric_name', '?')}: actual={v.get('actual_value', '?')} "
                f"threshold={v.get('threshold_operator', '?')}{v.get('threshold_value', '?')} "
                f"severity={v.get('severity', '?')} action={v.get('recommended_action', '?')}"
            )

        if metric_summary:
            parts.append("\n## Recent Metric Summary\n")
            parts.append(json.dumps(metric_summary, indent=2, default=str))

        if anomaly_results:
            parts.append("\n## Anomaly Detection Results (Tier 2)\n")
            parts.append(json.dumps(anomaly_results, indent=2, default=str))

        if plan_snapshot:
            parts.append("\n## Current ExecutionPlan\n")
            # Include only relevant fields
            plan_brief = {
                "modalities": {},
                "phases": len(plan_snapshot.get("execution_phases", [])),
            }
            for mod, ens in plan_snapshot.get("modality_ensembles", {}).items():
                members = ens.get("ensemble_members", [])
                plan_brief["modalities"][mod] = {
                    "active_models": [
                        m["service_id"] for m in members if m.get("is_active", True)
                    ],
                    "ensemble_size": ens.get("ensemble_size", 0),
                    "strategy": ens.get("selection_strategy", "?"),
                }
            parts.append(json.dumps(plan_brief, indent=2))

        parts.append("\nDiagnose the issue and provide recommendations in JSON format.")
        return "\n".join(parts)

    def _parse_response(
        self,
        pipeline_id: str,
        raw_response: str,
        violations: list[dict[str, Any]],
    ) -> DiagnosisResult:
        """Parse the LLM response into a structured DiagnosisResult."""
        try:
            # Try to extract JSON from the response
            json_str = raw_response

            # Handle reasoning models that wrap response in <think>...</think>
            if "</think>" in json_str:
                json_str = json_str.split("</think>")[-1].strip()

            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            return DiagnosisResult(
                pipeline_id=pipeline_id,
                timestamp=datetime.now(timezone.utc),
                summary=data.get("summary", "No summary provided"),
                root_cause=data.get("root_cause", "unknown"),
                severity=data.get("severity", "medium"),
                recommendations=data.get("recommendations", []),
                affected_modalities=data.get("affected_modalities", []),
                affected_models=data.get("affected_models", []),
                confidence=float(data.get("confidence", 0.5)),
                raw_response=raw_response,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return DiagnosisResult(
                pipeline_id=pipeline_id,
                timestamp=datetime.now(timezone.utc),
                summary=raw_response[:500] if raw_response else "Empty response",
                root_cause="parse_error",
                severity="medium",
                recommendations=[
                    f"LLM response could not be parsed: {e}",
                    "Manual investigation recommended",
                ],
                affected_modalities=[v.get("metric_name", "") for v in violations],
                affected_models=[],
                confidence=0.0,
                raw_response=raw_response,
            )
