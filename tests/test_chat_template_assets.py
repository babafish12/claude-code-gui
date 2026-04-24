"""Tests for chat template glass tokens and behavior hooks."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from claude_code_gui.assets.chat_template import CHAT_WEBVIEW_HTML

pytestmark = pytest.mark.unit


def _extract_css(html: str) -> str:
    return "\n".join(re.findall(r"<style>(.*?)</style>", html, flags=re.DOTALL))


def _extract_rules(css: str, selector: str) -> list[str]:
    rules: list[str] = []
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css, flags=re.DOTALL):
        if selector in selectors:
            rules.append(body)
    return rules


def test_glass_classes_have_backdrop_filter_and_tint() -> None:
    css = _extract_css(CHAT_WEBVIEW_HTML)
    classes = [
        "folder-path-btn",
        "plus-btn",
        "voice-btn",
        "selector-btn",
        "permission-btn",
        "permission-selector",
        "assistant-action",
        "chip",
        "artifact-action-btn",
        "action-btn",
        "code-copy-btn",
        "quick-chip",
        "stop-process-btn",
        "example-prompt",
        "popup-menu",
    ]
    for cls in classes:
        selector = f".{cls}"
        rules = _extract_rules(css, selector)
        assert rules, selector
        assert any(
            "backdrop-filter: blur(" in rule and "-webkit-backdrop-filter: blur(" in rule
            for rule in rules
        ), selector
        assert any("var(--glass-tint-interactive" in rule for rule in rules), selector


def test_voice_button_disables_when_runtime_unavailable() -> None:
    assert re.search(
        r'if \(!isSupported\) \{\s*button\.disabled = true;\s*button\.setAttribute\("title", "Speech input runtime unavailable in this environment\."\);',
        CHAT_WEBVIEW_HTML,
    )
    assert "Voice input is unavailable in this runtime." not in CHAT_WEBVIEW_HTML


def test_voice_send_is_deferred_until_voice_pipeline_finishes() -> None:
    assert "let voiceSendQueued = false;" in CHAT_WEBVIEW_HTML
    assert "let voiceQueuedInput = null;" in CHAT_WEBVIEW_HTML
    assert re.search(
        r"if \(speechRecognitionActive \|\| mediaRecorderActive \|\| voiceTranscribeInFlight\) \{\s*queueSendAfterVoice\(inputEl\);\s*stopVoiceInput\(\);\s*return;\s*\}",
        CHAT_WEBVIEW_HTML,
    )
    assert "flushQueuedSendAfterVoice();" in CHAT_WEBVIEW_HTML


def test_voice_media_recorder_uses_host_user_media_bridge() -> None:
    assert 'window.pybridge.armUserMedia = function () {' in CHAT_WEBVIEW_HTML
    assert 'window.pybridge.disarmUserMedia = function () {' in CHAT_WEBVIEW_HTML
    assert re.search(
        r'window\.pybridge && typeof window\.pybridge\.armUserMedia === "function"\) \{\s*window\.pybridge\.armUserMedia\(\);',
        CHAT_WEBVIEW_HTML,
    )
    assert re.search(
        r'window\.pybridge && typeof window\.pybridge\.disarmUserMedia === "function"\) \{\s*window\.pybridge\.disarmUserMedia\(\);',
        CHAT_WEBVIEW_HTML,
    )


def test_popup_option_no_backdrop_filter() -> None:
    rules = _extract_rules(_extract_css(CHAT_WEBVIEW_HTML), ".popup-option")
    assert rules, ".popup-option"
    assert all("backdrop-filter" not in rule for rule in rules)
    assert any("background: transparent" in rule for rule in rules)


def test_composer_focus_and_permission_accessibility_hooks_exist() -> None:
    css = _extract_css(CHAT_WEBVIEW_HTML)
    focus_visible_rules = _extract_rules(css, ".composer-input:focus-visible")
    assert focus_visible_rules
    assert any("outline:" in rule and "var(--accent)" in rule for rule in focus_visible_rules)
    assert CHAT_WEBVIEW_HTML.count('aria-label="Permissions"') == 2


def test_reduced_motion_media_query_exists() -> None:
    assert "@media (prefers-reduced-motion: reduce)" in CHAT_WEBVIEW_HTML
    assert "body.reduced-motion" in CHAT_WEBVIEW_HTML
    assert "window.setReducedMotion" in CHAT_WEBVIEW_HTML


def test_reduced_transparency_media_query_exists() -> None:
    assert "@media (prefers-reduced-transparency: reduce)" in CHAT_WEBVIEW_HTML


def test_motion_one_injected() -> None:
    assert "window.Motion" in CHAT_WEBVIEW_HTML
    assert "window.Motion.animate" in CHAT_WEBVIEW_HTML
    assert "__INLINE_MOTION_ONE_JS__" not in CHAT_WEBVIEW_HTML


def test_spring_press_signature_present() -> None:
    assert "duration: 0.28" in CHAT_WEBVIEW_HTML
    assert "[1, 0.96, 1]" in CHAT_WEBVIEW_HTML
    assert "window.Motion.spring" in CHAT_WEBVIEW_HTML


def test_glass_hover_will_change_clear_on_leave() -> None:
    assert "GLASS_ACTIVE_ANIMATIONS" in CHAT_WEBVIEW_HTML


def test_motion_one_vendor_integrity() -> None:
    motion_content = Path("claude_code_gui/assets/vendor/motion.min.js").read_text(encoding="utf-8")
    digest = hashlib.sha256(motion_content.encode("utf-8")).hexdigest()
    versions = Path("claude_code_gui/assets/vendor/VERSIONS.md").read_text(encoding="utf-8")
    assert digest in versions


def test_agent_prompt_styles_and_renderer_are_present() -> None:
    assert ".agent-prompt-bubble" in CHAT_WEBVIEW_HTML
    assert ".agent-prompt-label" in CHAT_WEBVIEW_HTML
    assert "function addAgentPromptMessage(text)" in CHAT_WEBVIEW_HTML
    assert 'window.addAgentPromptMessage = addAgentPromptMessage;' in CHAT_WEBVIEW_HTML
    assert re.search(
        r'role === "agent_prompt"\) \{\s*addAgentPromptMessage\(content\);',
        CHAT_WEBVIEW_HTML,
    )


def test_permission_request_seen_state_is_tracked_per_session() -> None:
    assert "let currentSessionId = \"\";" in CHAT_WEBVIEW_HTML
    assert "function ensureSeenPermissionRequests(sessionId)" in CHAT_WEBVIEW_HTML
    assert "clearSeenPermissionRequests(targetSessionId);" in CHAT_WEBVIEW_HTML
    assert 'const requestSessionId = String(data.sessionId || currentSessionId || "").trim();' in CHAT_WEBVIEW_HTML


def test_markdown_renderer_avoids_double_escaping_links_and_images() -> None:
    assert (
        '.replace(/&(?!(?:[a-zA-Z][a-zA-Z0-9]+|#\\d+|#x[a-fA-F0-9]+);)/g, "&amp;")'
        in CHAT_WEBVIEW_HTML
    )
    assert "const safeSrc = escapeHtml(src);" not in CHAT_WEBVIEW_HTML
    assert "const safeAlt = escapeHtml(alt);" not in CHAT_WEBVIEW_HTML
