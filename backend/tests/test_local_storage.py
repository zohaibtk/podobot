from pathlib import Path

import pytest

from app.files.storage import LocalStorage


def test_local_storage_resolves_paths_inside_root(tmp_path: Path) -> None:
    storage = LocalStorage(str(tmp_path))

    resolved = storage.resolve("workspace/series/file.txt")

    assert resolved == tmp_path / "workspace" / "series" / "file.txt"


def test_local_storage_resolves_existing_fallback_paths(tmp_path: Path) -> None:
    primary_root = tmp_path / "primary"
    fallback_root = tmp_path / "fallback"
    fallback_file = fallback_root / "workspace" / "series" / "legacy.txt"
    fallback_file.parent.mkdir(parents=True)
    fallback_file.write_text("legacy")
    storage = LocalStorage(str(primary_root), fallback_roots=[str(fallback_root)])

    assert storage.resolve("workspace/series/legacy.txt") == fallback_file
    assert storage.resolve("workspace/series/new.txt") == (
        primary_root / "workspace" / "series" / "new.txt"
    )


@pytest.mark.parametrize(
    "unsafe_path",
    ["", "   ", "../secret.txt", "workspace/../secret.txt", "/tmp/secret.txt"],
)
def test_local_storage_rejects_unsafe_paths(tmp_path: Path, unsafe_path: str) -> None:
    storage = LocalStorage(str(tmp_path))

    with pytest.raises(ValueError):
        storage.resolve(unsafe_path)
