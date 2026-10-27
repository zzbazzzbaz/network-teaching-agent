from deepagents.backends import (
    CompositeBackend,
    FilesystemBackend,
    StateBackend,
    StoreBackend,
)

from agent.infra.ags_backend import AgsBackend
from agent.runtime.memory import memory_namespace
from agent.runtime.paths import RESOURCE_DIR


def build_exp_backend() -> CompositeBackend:
    return CompositeBackend(
        default=AgsBackend(),
        routes={
            **_resource_routes(),
            "/memory/": StoreBackend(namespace=memory_namespace),
        },
    )


def build_teaching_backend() -> CompositeBackend:
    return CompositeBackend(
        default=StateBackend(),
        routes={
            **_resource_routes(),
            "/memory/": StoreBackend(namespace=memory_namespace),
        },
    )


def _resource_routes() -> dict[str, FilesystemBackend]:
    return {
        "/skills/": FilesystemBackend(
            root_dir=RESOURCE_DIR / "skills",
            virtual_mode=True,
        ),
        "/materials/": FilesystemBackend(
            root_dir=RESOURCE_DIR / "materials",
            virtual_mode=True,
        ),
    }
