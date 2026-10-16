import importlib.util
import shlex
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("agent_guard", Path(__file__).resolve().parents[1] / "scripts/agent-guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

PROVEN = """## Summary

Fix.

## Evidence

- **Before:** Swap quote failed.
  **After:** Swap settles on the preview.

**Checks:** typecheck, 12 tests.

**Browser:** verified https://example.com/run/1

## Merge Danger
"""

# Body of #784, merged-ready while swaps were broken in the preview.
UNPROVEN = """Stacked on #768.

On success, the status card collapses its steps into "Swap complete".

- Adds `summarizeOnSuccess` to `ProgressSteps`.
"""


class AgentGuardTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.e2e = self.repo("e2e", "git@github.com:silent-shipper/metamask-e2e.git")
        self.app = self.repo("app", "https://github.com/defuse-protocol/defuse-frontend-monorepos.git")

    def repo(self, name, url):
        path = self.root / name
        path.mkdir()
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "remote", "add", "origin", url], check=True)
        return path

    def decide(self, command, project):
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(project)}):
            return guard.decide({"tool_name": "Bash", "cwd": str(project), "tool_input": {"command": command}})

    def test_push_to_another_repo_asks(self):
        result = self.decide(f"cd {self.app} && git push origin HEAD", self.e2e)
        self.assertEqual(result[0], "ask")
        self.assertIn("defuse-protocol/defuse-frontend-monorepos", result[1])
        self.assertEqual(self.decide(f"git -C {self.app} push", self.e2e)[0], "ask")
        self.assertEqual(self.decide("gh pr merge 5 --repo defuse-protocol/defuse-frontend-monorepos", self.e2e)[0], "ask")

    def test_push_to_session_repo_is_allowed(self):
        self.assertIsNone(self.decide("git push origin main", self.e2e))

    def test_pr_without_evidence_is_denied(self):
        body = self.root / "body.md"
        body.write_text(UNPROVEN)
        result = self.decide(f"gh pr edit 784 --body-file {body}", self.app)
        self.assertEqual(result[0], "deny")
        self.assertIn("## Evidence", result[1])

    def test_unfilled_template_is_denied(self):
        body = PROVEN.replace("verified https://example.com/run/1", "verified <link>")
        self.assertIn("placeholder", self.decide("gh pr create --body " + shlex.quote(body), self.app)[1])

    def test_proven_pr_is_allowed(self):
        body = self.root / "body.md"
        body.write_text(PROVEN)
        self.assertIsNone(self.decide(f"gh pr create --body-file {body}", self.app))
        self.assertIsNone(self.decide("gh pr edit 5 --add-label bug", self.app))


if __name__ == "__main__":
    unittest.main()
