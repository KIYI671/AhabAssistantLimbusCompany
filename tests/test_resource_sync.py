from __future__ import annotations

from pathlib import Path

from module.resource_sync.manifest import ResourceManifest
from module.resource_sync.service import PROTECTED_CORE_IMAGE_RESOURCES, ResourceSyncService


def test_stale_manifest_cannot_delete_mirror_pathfinding_resources(tmp_path: Path) -> None:
    """A lagging resource repository must not remove templates used by mirror routing."""

    for relative_path in PROTECTED_CORE_IMAGE_RESOURCES:
        image_path = tmp_path / relative_path
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"bundled core image")

    obsolete_path = tmp_path / "default/share/obsolete.png"
    obsolete_path.parent.mkdir(parents=True, exist_ok=True)
    obsolete_path.write_bytes(b"obsolete image")

    service = ResourceSyncService(
        assets_dir=tmp_path,
        state_path=tmp_path / "state.json",
        temp_dir=tmp_path / "update_temp",
    )
    plan = service.build_sync_plan(ResourceManifest(manifest_id="stale", files=[]))

    assert set(plan.files_to_delete) == {"default/share/obsolete.png"}
    assert not PROTECTED_CORE_IMAGE_RESOURCES.intersection(plan.files_to_delete)
