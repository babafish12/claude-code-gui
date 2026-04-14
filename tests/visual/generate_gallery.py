from pathlib import Path

from claude_code_gui.assets.chat_template import CHAT_WEBVIEW_HTML


def main() -> None:
    out = Path("tests/visual/generated_gallery.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(CHAT_WEBVIEW_HTML, encoding="utf-8")


if __name__ == "__main__":
    main()
