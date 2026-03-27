from __future__ import annotations

import pytest


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    _ = config
    integration: list[pytest.Item] = []
    others: list[pytest.Item] = []
    for item in items:
        if item.get_closest_marker("integration"):
            integration.append(item)
        else:
            others.append(item)
    items[:] = others + integration
