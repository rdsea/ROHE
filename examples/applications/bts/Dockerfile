# Built with context = repo root (ROHE/)
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi "uvicorn[standard]" numpy httpx pydantic pyyaml python-multipart redis

# Copy rohe core packages (needed by simulation, inference, and orchestrator)
COPY src/rohe/__init__.py /app/rohe/__init__.py
COPY src/rohe/common/ /app/rohe/common/
COPY src/rohe/models/ /app/rohe/models/
COPY src/rohe/repositories/ /app/rohe/repositories/

# Copy shared application utilities
COPY examples/applications/common/ /app/common/

# Copy the target service
ARG APP_NAME=bts
ARG SERVICE_NAME=gateway
COPY examples/applications/${APP_NAME}/services/${SERVICE_NAME}/ /app/service/

# Optional: include simulation framework and config for testing
ARG INCLUDE_SIM=false
ARG SIM_CONFIG=
COPY examples/applications/${APP_NAME}/simulation/ /tmp/sim/simulation/
COPY examples/applications/${APP_NAME}/sim_config/ /tmp/sim/sim_config/
RUN if [ "$INCLUDE_SIM" = "true" ]; then \
      cp -r /tmp/sim/simulation/ /app/simulation/ && \
      mkdir -p /config && \
      if [ -n "$SIM_CONFIG" ] && [ -f "/tmp/sim/sim_config/$SIM_CONFIG" ]; then \
        cp "/tmp/sim/sim_config/$SIM_CONFIG" /config/model.yaml; \
      fi && \
      if [ -f /tmp/sim/sim_config/samples.yaml ]; then \
        cp /tmp/sim/sim_config/samples.yaml /config/samples.yaml; \
      fi && \
      if [ -f /tmp/sim/sim_config/preprocessor.yaml ]; then \
        cp /tmp/sim/sim_config/preprocessor.yaml /config/preprocessor.yaml; \
      fi && \
      if [ -f /tmp/sim/sim_config/execution_plan.yaml ]; then \
        mkdir -p /config/plans && \
        cp /tmp/sim/sim_config/execution_plan.yaml /config/plans/execution_plan.yaml; \
      fi; \
    fi && \
    rm -rf /tmp/sim/

ENV PYTHONPATH=/app
ENV MODEL_CONFIG=/config/model.yaml
EXPOSE 8000

CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000"]
