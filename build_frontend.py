"""Minify frontend JS/CSS files for production."""
import re
import shutil
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent / "frontend"
BUILD = Path(__file__).resolve().parent / "build"


def minify_js(code: str) -> str:
    code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'\n\s*\n', '\n', code)
    lines = []
    for line in code.split('\n'):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return '\n'.join(lines)


def minify_css(code: str) -> str:
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'\s+', ' ', code)
    code = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', code)
    code = re.sub(r';}', '}', code)
    return code.strip()


def build():
    BUILD.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True, parents=True)

    for js_file in FRONTEND.glob("*.js"):
        original = js_file.read_text(encoding="utf-8")
        minified = minify_js(original)
        out = BUILD / js_file.name
        out.write_text(minified, encoding="utf-8")
        ratio = (1 - len(minified) / len(original)) * 100 if original else 0
        print(f"  JS: {js_file.name} {len(original)} -> {len(minified)} bytes ({ratio:.0f}% menor)")

    for css_file in FRONTEND.glob("*.css"):
        original = css_file.read_text(encoding="utf-8")
        minified = minify_css(original)
        out = BUILD / css_file.name
        out.write_text(minified, encoding="utf-8")
        ratio = (1 - len(minified) / len(original)) * 100 if original else 0
        print(f"  CSS: {css_file.name} {len(original)} -> {len(minified)} bytes ({ratio:.0f}% menor)")

    for html_file in FRONTEND.glob("*.html"):
        original = html_file.read_text(encoding="utf-8")
        content = original

        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = re.sub(r'\n\s*\n', '\n', content)
        lines = []
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
        content = '\n'.join(lines)

        out = BUILD / html_file.name
        out.write_text(content, encoding="utf-8")
        ratio = (1 - len(content) / len(original)) * 100 if original else 0
        print(f"  HTML: {html_file.name} {len(original)} -> {len(content)} bytes ({ratio:.0f}% menor)")

    print(f"\nBuild completo em: {BUILD}")


if __name__ == "__main__":
    print("=== AI Market Analyzer - Build ===\n")
    build()
