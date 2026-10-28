import pytest
from PIL import features


def pytest_configure(config):
    # The renderer re-launches itself to find Homebrew's FriBiDi on a Mac, but
    # under pytest that would lose the output, so say what to run instead.
    if not features.check("raqm"):
        pytest.exit(
            "Pillow has no Raqm text layout here. On a Mac run: "
            "DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run pytest",
            returncode=2,
        )
