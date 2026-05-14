"""
Unit tests for task4/ai_review.py.

All external I/O (Anthropic API, httpx, filesystem) is mocked — no real
network calls or API keys are required to run the suite.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import httpx
import pytest

# Make sure the task4 package root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

import ai_review  # noqa: E402  (import after sys.path manipulation)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_claude_message(text: str = "Всё хорошо") -> MagicMock:
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


def _mock_github_response(url: str = "https://github.com/owner/repo/issues/1#issuecomment-1") -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"html_url": url}
    resp.raise_for_status = MagicMock()
    return resp


_BASE_GH_ENV = {"GITHUB_TOKEN": "ghp_test", "REPO": "owner/repo", "PR_NUMBER": "42"}


# ══════════════════════════════════════════════════════════════════════════════
# _build_prompt
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildPrompt:

    def test_diff_appears_in_prompt(self) -> None:
        diff = "diff --git a/foo.py b/foo.py\n+print('hello')"
        result = ai_review._build_prompt(diff)
        assert diff in result

    def test_prompt_wrapped_in_diff_code_fence(self) -> None:
        result = ai_review._build_prompt("x")
        assert "```diff" in result
        assert "```" in result

    def test_prompt_contains_required_sections(self) -> None:
        result = ai_review._build_prompt("x")
        assert "## 📝 Краткое описание изменений" in result
        assert "## 🔍 Основные изменения" in result
        assert "## ⚠️ Найденные проблемы" in result
        assert "## 🧪 Покрытие тестами" in result
        assert "## ✅ Итог" in result

    def test_curly_braces_do_not_raise(self) -> None:
        """Regression: old .format(diff=diff) crashed on diffs with {var}."""
        tricky = "+x = f'{value}'\n+d = {key: val}\n+fmt = '{}'\n+tpl = '{name}'"
        result = ai_review._build_prompt(tricky)   # must not raise KeyError
        assert tricky in result

    def test_empty_curly_braces_do_not_raise(self) -> None:
        result = ai_review._build_prompt("+print('{}'.format(x))")
        assert "{}" in result

    def test_rust_format_macro_does_not_raise(self) -> None:
        result = ai_review._build_prompt('+println!("value={}", x);')
        assert "value=" in result


# ══════════════════════════════════════════════════════════════════════════════
# _load_diff
# ══════════════════════════════════════════════════════════════════════════════

class TestLoadDiff:

    def test_returns_file_content(self, tmp_path: Path) -> None:
        f = tmp_path / "diff.txt"
        f.write_text("some diff content", encoding="utf-8")
        with patch.dict(os.environ, {"DIFF_FILE": str(f)}):
            assert ai_review._load_diff() == "some diff content"

    def test_missing_file_exits_with_code_1(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"DIFF_FILE": str(tmp_path / "no_such.txt")}):
            with pytest.raises(SystemExit) as exc:
                ai_review._load_diff()
        assert exc.value.code == 1

    def test_file_at_exact_limit_not_truncated(self, tmp_path: Path) -> None:
        content = "a" * ai_review._MAX_DIFF_CHARS
        f = tmp_path / "diff.txt"
        f.write_text(content, encoding="utf-8")
        with patch.dict(os.environ, {"DIFF_FILE": str(f)}):
            result = ai_review._load_diff()
        assert result == content

    def test_file_over_limit_is_truncated(self, tmp_path: Path) -> None:
        content = "b" * (ai_review._MAX_DIFF_CHARS + 500)
        f = tmp_path / "diff.txt"
        f.write_text(content, encoding="utf-8")
        with patch.dict(os.environ, {"DIFF_FILE": str(f)}):
            result = ai_review._load_diff()
        assert len(result) < len(content)
        assert "[...diff обрезан по длине...]" in result
        assert result.startswith("b" * ai_review._MAX_DIFF_CHARS)

    def test_empty_file_returns_empty_string(self, tmp_path: Path) -> None:
        f = tmp_path / "diff.txt"
        f.write_text("", encoding="utf-8")
        with patch.dict(os.environ, {"DIFF_FILE": str(f)}):
            assert ai_review._load_diff() == ""

    def test_default_path_used_when_env_not_set(self, tmp_path: Path) -> None:
        """DIFF_FILE defaults to /tmp/pr_diff.txt when not set."""
        env = {k: v for k, v in os.environ.items() if k != "DIFF_FILE"}
        with patch.dict(os.environ, env, clear=True):
            with patch("builtins.open", side_effect=FileNotFoundError):
                with pytest.raises(SystemExit):
                    ai_review._load_diff()


# ══════════════════════════════════════════════════════════════════════════════
# _analyze
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalyze:

    def test_returns_text_block(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("ai_review.anthropic.Anthropic") as mock_cls:
                mock_cls.return_value.messages.create.return_value = _mock_claude_message("Отличный PR!")
                result = ai_review._analyze("diff text")
        assert result == "Отличный PR!"

    def test_missing_api_key_exits(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as exc:
                ai_review._analyze("diff")
        assert exc.value.code == 1

    def test_uses_correct_model(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("ai_review.anthropic.Anthropic") as mock_cls:
                mock_cls.return_value.messages.create.return_value = _mock_claude_message()
                ai_review._analyze("diff")
        kwargs = mock_cls.return_value.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-opus-4-7"

    def test_uses_correct_max_tokens(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("ai_review.anthropic.Anthropic") as mock_cls:
                mock_cls.return_value.messages.create.return_value = _mock_claude_message()
                ai_review._analyze("diff")
        kwargs = mock_cls.return_value.messages.create.call_args.kwargs
        assert kwargs["max_tokens"] == 2048

    def test_diff_with_braces_reaches_claude_unmangled(self) -> None:
        """Curly braces in the diff must not be altered before being sent."""
        tricky = "+x = f'{val}' + '{literal}'"
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            with patch("ai_review.anthropic.Anthropic") as mock_cls:
                mock_cls.return_value.messages.create.return_value = _mock_claude_message()
                ai_review._analyze(tricky)
        content_sent = mock_cls.return_value.messages.create.call_args.kwargs["messages"][0]["content"]
        assert tricky in content_sent

    def test_anthropic_client_initialised_with_api_key(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-my-key"}):
            with patch("ai_review.anthropic.Anthropic") as mock_cls:
                mock_cls.return_value.messages.create.return_value = _mock_claude_message()
                ai_review._analyze("diff")
        mock_cls.assert_called_once_with(api_key="sk-my-key")


# ══════════════════════════════════════════════════════════════════════════════
# _post_comment
# ══════════════════════════════════════════════════════════════════════════════

class TestPostComment:

    def test_calls_correct_github_url(self) -> None:
        with patch.dict(os.environ, _BASE_GH_ENV):
            with patch("ai_review.httpx.post", return_value=_mock_github_response()) as mock_post:
                ai_review._post_comment("review")
        assert mock_post.call_args.args[0] == (
            "https://api.github.com/repos/owner/repo/issues/42/comments"
        )

    def test_body_contains_review_text(self) -> None:
        with patch.dict(os.environ, _BASE_GH_ENV):
            with patch("ai_review.httpx.post", return_value=_mock_github_response()) as mock_post:
                ai_review._post_comment("Needs work!")
        body = mock_post.call_args.kwargs["json"]["body"]
        assert "Needs work!" in body

    def test_authorization_header_sent(self) -> None:
        with patch.dict(os.environ, _BASE_GH_ENV):
            with patch("ai_review.httpx.post", return_value=_mock_github_response()) as mock_post:
                ai_review._post_comment("ok")
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer ghp_test"
        assert headers["Accept"] == "application/vnd.github+json"

    def test_missing_github_token_exits(self) -> None:
        env = {"REPO": "owner/repo", "PR_NUMBER": "42"}   # no GITHUB_TOKEN
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc:
                ai_review._post_comment("review")
        assert exc.value.code == 1

    def test_missing_repo_exits(self) -> None:
        env = {"GITHUB_TOKEN": "ghp_test", "PR_NUMBER": "42"}  # no REPO
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc:
                ai_review._post_comment("review")
        assert exc.value.code == 1

    def test_missing_pr_number_exits(self) -> None:
        env = {"GITHUB_TOKEN": "ghp_test", "REPO": "owner/repo"}  # no PR_NUMBER
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit) as exc:
                ai_review._post_comment("review")
        assert exc.value.code == 1

    def test_github_4xx_error_exits(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=MagicMock(status_code=403, text="Forbidden"),
        )
        with patch.dict(os.environ, _BASE_GH_ENV):
            with patch("ai_review.httpx.post", return_value=mock_resp):
                with pytest.raises(SystemExit) as exc:
                    ai_review._post_comment("review")
        assert exc.value.code == 1

    def test_timeout_passed_to_httpx(self) -> None:
        with patch.dict(os.environ, _BASE_GH_ENV):
            with patch("ai_review.httpx.post", return_value=_mock_github_response()) as mock_post:
                ai_review._post_comment("ok")
        assert mock_post.call_args.kwargs["timeout"] == 30


# ══════════════════════════════════════════════════════════════════════════════
# main()
# ══════════════════════════════════════════════════════════════════════════════

class TestMain:

    def _full_env(self, diff_file: str) -> dict[str, str]:
        return {
            "DIFF_FILE": diff_file,
            "ANTHROPIC_API_KEY": "sk-test",
            **_BASE_GH_ENV,
        }

    def test_happy_path_calls_claude_and_github(self, tmp_path: Path) -> None:
        f = tmp_path / "diff.txt"
        f.write_text("real changes here", encoding="utf-8")

        with patch.dict(os.environ, self._full_env(str(f))):
            with patch("ai_review.anthropic.Anthropic") as mock_cls:
                mock_cls.return_value.messages.create.return_value = _mock_claude_message("LGTM")
                with patch("ai_review.httpx.post", return_value=_mock_github_response()) as mock_post:
                    ai_review.main()

        mock_cls.return_value.messages.create.assert_called_once()
        mock_post.assert_called_once()

    def test_empty_diff_skips_claude_and_github(self, tmp_path: Path) -> None:
        f = tmp_path / "diff.txt"
        f.write_text("   \n\n  \t  ", encoding="utf-8")

        with patch.dict(os.environ, self._full_env(str(f))):
            with patch("ai_review.anthropic.Anthropic") as mock_cls:
                with patch("ai_review.httpx.post") as mock_post:
                    ai_review.main()

        mock_cls.assert_not_called()
        mock_post.assert_not_called()

    def test_review_text_ends_up_in_github_comment(self, tmp_path: Path) -> None:
        f = tmp_path / "diff.txt"
        f.write_text("some changes", encoding="utf-8")
        expected_review = "Требует доработки: нет тестов"

        with patch.dict(os.environ, self._full_env(str(f))):
            with patch("ai_review.anthropic.Anthropic") as mock_cls:
                mock_cls.return_value.messages.create.return_value = _mock_claude_message(expected_review)
                with patch("ai_review.httpx.post", return_value=_mock_github_response()) as mock_post:
                    ai_review.main()

        body = mock_post.call_args.kwargs["json"]["body"]
        assert expected_review in body

    def test_diff_with_curly_braces_completes_without_error(self, tmp_path: Path) -> None:
        """End-to-end regression for the .format() KeyError bug."""
        f = tmp_path / "diff.txt"
        f.write_text("+x = f'{value}'\n+d = {key: val}", encoding="utf-8")

        with patch.dict(os.environ, self._full_env(str(f))):
            with patch("ai_review.anthropic.Anthropic") as mock_cls:
                mock_cls.return_value.messages.create.return_value = _mock_claude_message()
                with patch("ai_review.httpx.post", return_value=_mock_github_response()):
                    ai_review.main()   # must not raise

        mock_cls.return_value.messages.create.assert_called_once()
