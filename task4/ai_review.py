"""
AI-powered PR review script.

Reads a git diff, sends it to Claude for analysis, and posts the result
as a comment on the GitHub Pull Request.

Required environment variables:
  ANTHROPIC_API_KEY  — Claude API key (stored as a GitHub secret)
  GITHUB_TOKEN       — provided automatically by GitHub Actions
  REPO               — owner/repo, e.g. "octocat/my-project"
  PR_NUMBER          — pull request number
  DIFF_FILE          — path to the file containing git diff output
"""

from __future__ import annotations

import os
import sys

import anthropic
import httpx

# Claude will only see this many characters of diff to stay within context limits.
_MAX_DIFF_CHARS = 60_000

_REVIEW_PROMPT_PREFIX = """\
You are a senior Python developer conducting a thorough code review.
Analyze the git diff below and respond **in Russian** using exactly these sections:

## 📝 Краткое описание изменений
2–3 sentences: what does this PR do and why?

## 🔍 Основные изменения
Bullet list of the key changes with file names.

## ⚠️ Найденные проблемы
For each problem use the format:
- **[Категория]** `file:line` — описание проблемы и рекомендация

Categories: Безопасность | Производительность | Логика | Стиль/PEP8 | Обработка ошибок

If no problems are found, write: "Критических проблем не обнаружено."

## 🧪 Покрытие тестами
Are new code paths covered by tests? What should be tested?

## ✅ Итог
One line: **Готово к мерджу** or **Требует доработки** — and a one-sentence reason.

---
Git diff:
```diff
"""

_REVIEW_PROMPT_SUFFIX = "\n```\n"


def _build_prompt(diff: str) -> str:
    # Build prompt via concatenation — NOT .format() — because diffs routinely
    # contain curly braces (f-strings, Rust format macros, JS template literals)
    # that would cause KeyError with str.format().
    return _REVIEW_PROMPT_PREFIX + diff + _REVIEW_PROMPT_SUFFIX


def _load_diff() -> str:
    diff_file = os.environ.get("DIFF_FILE", "/tmp/pr_diff.txt")
    try:
        with open(diff_file, encoding="utf-8") as fh:
            content = fh.read()
    except FileNotFoundError:
        print(f"[ai_review] Diff file not found: {diff_file}", file=sys.stderr)
        sys.exit(1)

    if len(content) > _MAX_DIFF_CHARS:
        content = content[:_MAX_DIFF_CHARS] + "\n\n[...diff обрезан по длине...]"
    return content


def _analyze(diff: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ai_review] ANTHROPIC_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        messages=[{"role": "user", "content": _build_prompt(diff)}],
    )
    block = message.content[0]
    return block.text  # type: ignore[union-attr]


def _post_comment(review_text: str) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("REPO")
    pr_number = os.environ.get("PR_NUMBER")

    if not all([token, repo, pr_number]):
        missing = [k for k, v in {"GITHUB_TOKEN": token, "REPO": repo, "PR_NUMBER": pr_number}.items() if not v]
        print(f"[ai_review] Missing env vars: {missing}", file=sys.stderr)
        sys.exit(1)

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = (
        "## 🤖 AI Code Review (Claude)\n\n"
        + review_text
        + "\n\n---\n*Сгенерировано автоматически · [Claude AI](https://anthropic.com)*"
    )

    resp = httpx.post(url, json={"body": body}, headers=headers, timeout=30)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(f"[ai_review] GitHub API error {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        sys.exit(1)

    print(f"[ai_review] Comment posted: {resp.json()['html_url']}")


def main() -> None:
    print("[ai_review] Loading diff...")
    diff = _load_diff()

    if not diff.strip():
        print("[ai_review] Empty diff — nothing to review.")
        return

    print(f"[ai_review] Diff size: {len(diff)} chars. Sending to Claude...")
    review = _analyze(diff)

    print("[ai_review] Posting review comment to PR...")
    _post_comment(review)
    print("[ai_review] Done.")


if __name__ == "__main__":
    main()
