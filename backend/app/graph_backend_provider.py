from __future__ import annotations

import os
from enum import StrEnum


class GraphBackendConfigError(ValueError):
    pass


class GraphBackendProvider(StrEnum):
    ZEP_CLOUD = 'zep_cloud'
    GRAPHITI = 'graphiti'


GRAPHITI_REQUIRED_ENV_VARS = ('NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD')


def get_graph_backend_provider(*, validate_env: bool = False) -> GraphBackendProvider:
    raw = (os.environ.get('GRAPH_BACKEND_PROVIDER') or GraphBackendProvider.ZEP_CLOUD).strip().lower()
    try:
        provider = GraphBackendProvider(raw)
    except ValueError as exc:
        valid = ', '.join(provider.value for provider in GraphBackendProvider)
        raise GraphBackendConfigError(
            f'Unsupported GRAPH_BACKEND_PROVIDER={raw!r}. Valid values: {valid}'
        ) from exc

    if validate_env and provider == GraphBackendProvider.GRAPHITI:
        missing = [key for key in GRAPHITI_REQUIRED_ENV_VARS if not (os.environ.get(key) or '').strip()]
        if missing:
            raise GraphBackendConfigError(
                'GRAPHITI backend requires: ' + ', '.join(missing)
            )

    return provider
