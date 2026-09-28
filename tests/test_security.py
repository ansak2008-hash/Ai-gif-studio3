from uuid import uuid4

import pytest

from ai_gif_studio.infrastructure.storage import ArtifactStorage


def test_path_traversal_rejected(tmp_path):
    with pytest.raises(ValueError):
        ArtifactStorage(str(tmp_path)).safe_path(uuid4(), "../evil")
