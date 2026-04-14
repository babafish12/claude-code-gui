from __future__ import annotations

import pytest

from claude_code_gui.assets.gtk_css import CSS_STYLES, build_gtk_css
from claude_code_gui.domain.provider import PROVIDERS

pytestmark = pytest.mark.gtk_css


def test_claude_css_is_byte_identical() -> None:
    generated = build_gtk_css(
        PROVIDERS["claude"].colors,
        PROVIDERS["claude"].accent_rgb,
        PROVIDERS["claude"].accent_soft_rgb,
    )

    assert CSS_STYLES.encode("utf-8") == generated.encode("utf-8")
