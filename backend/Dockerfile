# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Dockerfile for aegis-v1-api (baseline single agent)
# For the swarm service, use Dockerfile.swarm instead.

FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

COPY ./pyproject.toml ./README.md ./uv.lock* ./simulator_rules.json ./

COPY ./app ./app
COPY ./eval ./eval
COPY ./playbooks ./playbooks
COPY ./baseline_day_zero ./baseline_day_zero

RUN uv sync --frozen

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

ENV PHOENIX_PROJECT_NAME=default
ENV AEGIS_BACKEND_ROOT=/code
ENV AEGIS_REPO_ROOT=/code

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main_v1:app", "--host", "0.0.0.0", "--port", "8080"]