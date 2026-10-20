from __future__ import annotations

from pathlib import Path

from module.resource_sync.manifest import ResourceFileEntry, ResourceManifest
from module.resource_sync.service import (
    PROTECTED_CORE_IMAGE_RESOURCES,
    ResourceCheckResult,
    ResourceCheckStatus,
    ResourceSyncPlan,
    ResourceSyncService,
)
from module.resource_sync.source import ResourceSource


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



def test_precomputed_sync_plan_cannot_remove_core_templates(monkeypatch, tmp_path):
    protected = sorted(PROTECTED_CORE_IMAGE_RESOURCES)[0]
    for relative_path in (protected, "obsolete.png"):
        path = tmp_path / "images" / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"image")
    service = ResourceSyncService(assets_dir=tmp_path / "images", state_path=tmp_path / "state.json")
    monkeypatch.setattr(service, "_refresh_runtime_image_cache", lambda: None)
    check = ResourceCheckResult(
        ResourceCheckStatus.UPDATE_AVAILABLE,
        source=ResourceSource("test", "https://example.invalid/manifest.json"),
        remote_manifest=ResourceManifest(manifest_id="stale", files=[]),
    )
    result = service.apply_sync_plan(check_result=check, sync_plan=ResourceSyncPlan(files_to_delete=[protected, "obsolete.png"]))
    assert result.deleted_count == 1
    assert (tmp_path / "images" / protected).read_bytes() == b"image"
    assert not (tmp_path / "images" / "obsolete.png").exists()
    assert service.load_state().last_applied_manifest_id == "stale"


def test_core_template_still_accepts_remote_content_updates(tmp_path):
    protected = sorted(PROTECTED_CORE_IMAGE_RESOURCES)[0]
    path = tmp_path / protected
    path.parent.mkdir(parents=True)
    path.write_bytes(b"old image")
    replacement = ResourceFileEntry(path=protected, sha256="0" * 64, size=9)
    service = ResourceSyncService(assets_dir=tmp_path)
    plan = service.build_sync_plan(ResourceManifest(manifest_id="updated", files=[replacement]))
    assert plan.files_to_update == [replacement]
    assert not plan.files_to_delete
