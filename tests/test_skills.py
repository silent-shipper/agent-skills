import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import skills


class SkillInstallationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name) / "home"
        self.home.mkdir()
        self.patch = patch.object(skills, "HOME_DIR", self.home)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_install_is_repeatable_and_backs_up_original_sources(self):
        original = self.home / ".claude/skills/architect"
        original.mkdir(parents=True)
        (original / "SKILL.md").write_text("Original personal skill\n")
        skills.install()
        self.assertEqual(original.resolve(), skills.REPO / "skills/architect")
        backups = list((self.home / ".agents/skill-backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / ".claude/skills/architect/SKILL.md").read_text(), "Original personal skill\n")
        config = (self.home / ".codex/config.toml").read_bytes()
        links = {p: p.readlink() for p in skills.managed_paths(skills.manifest())}
        skills.install()
        self.assertEqual((self.home / ".codex/config.toml").read_bytes(), config)
        self.assertEqual(list((self.home / ".agents/skill-backups").iterdir()), backups)
        self.assertEqual({p: p.readlink() for p in links}, links)
        result = subprocess.run([sys.executable, str(self.home / ".agents/check-skills.py")],
                                env={"HOME": str(self.home)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_config_preserves_unrelated_tables_and_replaces_only_managed_entries(self):
        old = 'model = "keep-this-model"\n\n[features]\nfoo = true\n\n'
        old += '[[skills.config]]\npath = "/unmanaged/plugin/SKILL.md"\nenabled = false\n\n'
        old += '[[skills.config]]\npath = "' + str(self.home / '.claude/skills/architect/SKILL.md') + '"\nenabled = false\n\n'
        old += '[mcp_servers.example]\ncommand = "keep-this-command"\n'
        config = self.home / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text(old)
        skills.install()
        result = config.read_text()
        self.assertIn('model = "keep-this-model"', result)
        self.assertIn('[features]\nfoo = true', result)
        self.assertIn('[mcp_servers.example]\ncommand = "keep-this-command"', result)
        self.assertIn('path = "/unmanaged/plugin/SKILL.md"\nenabled = false', result)
        self.assertNotIn(str(self.home / '.claude/skills/architect/SKILL.md'), result)
        skills.check()

    def test_checker_rejects_a_disabled_discovery_alias(self):
        skills.install()
        config = self.home / ".codex/config.toml"
        with config.open("a") as file:
            file.write('\n[[skills.config]]\npath = "' + str(self.home / '.claude/skills/architect/SKILL.md') + '"\nenabled = false\n')
        with self.assertRaises(SystemExit):
            skills.check()

    def test_sync_refuses_uncommitted_edits_without_overwriting(self):
        repo = Path(self.directory.name) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "local-edit").write_text("Keep my edit\n")
        with patch.object(skills, "REPO", repo):
            with self.assertRaisesRegex(SystemExit, "Local edits exist"):
                skills.sync()
        self.assertEqual((repo / "local-edit").read_text(), "Keep my edit\n")

    def test_removed_skills_are_unlinked_and_unmanaged_skills_are_preserved(self):
        skills.install()
        retired = []
        for root in skills.ROOTS:
            path = self.home / root / "removed-skill"
            path.symlink_to(skills.REPO / "skills/removed-skill")
            retired.append(path)
        unmanaged = self.home / ".claude/skills/local-only"
        unmanaged.mkdir()
        (unmanaged / "SKILL.md").write_text("Keep this local skill\n")
        external = self.home / ".codex/skills/external"
        external.symlink_to(unmanaged)
        config = self.home / ".codex/config.toml"
        with config.open("a") as file:
            file.write('\n[[skills.config]]\npath = "' + str(self.home / '.codex/skills/removed-skill/SKILL.md') + '"\nenabled = false\n')
        with self.assertRaises(SystemExit):
            skills.check()
        skills.install()
        for path in retired:
            self.assertFalse(path.is_symlink())
        self.assertNotIn("removed-skill", config.read_text())
        self.assertEqual((unmanaged / "SKILL.md").read_text(), "Keep this local skill\n")
        self.assertEqual(external.resolve(), unmanaged.resolve())
        backups = [directory / '.claude/skills/removed-skill'
                   for directory in (self.home / ".agents/skill-backups").iterdir()
                   if (directory / '.claude/skills/removed-skill').is_symlink()]
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].is_symlink())
        skills.install()

    def test_sync_runs_the_installer_from_the_pulled_revision(self):
        origin = Path(self.directory.name) / 'origin'
        checkout = self.home / '.agents/skill-config'
        origin.mkdir()
        (origin / 'scripts').mkdir()
        shutil.copy2(skills.REPO / 'scripts/skills.py', origin / 'scripts/skills.py')
        shutil.copy2(skills.REPO / 'scripts/check-skills.py', origin / 'scripts/check-skills.py')
        shutil.copytree(skills.REPO / 'skills/architect', origin / 'skills/architect')
        (origin / 'manifest.json').write_text(json.dumps({'version': 1, 'skills': [{'name': 'architect', 'codex_enabled': True}]}))
        (origin / 'surge-defaults.md').write_text('Shared defaults\n')
        (origin / '.gitignore').write_text('__pycache__/\n')
        def git(*args):
            subprocess.run(['git', '-C', str(origin), *args], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        git('init', '-b', 'main')
        git('config', 'user.name', 'Skill config tests')
        git('config', 'user.email', 'tests@example.invalid')
        git('add', '.')
        git('commit', '-m', 'Initial installer')
        subprocess.run(['git', 'clone', '-q', str(origin), str(checkout)], check=True)
        script = origin / 'scripts/skills.py'
        script.write_text(script.read_text().replace('def install():\n',
            'def install():\n    (HOME_DIR / "pulled-installer-ran").write_text("new revision")\n'))
        git('add', '.')
        git('commit', '-m', 'Update installer')
        result = subprocess.run([sys.executable, str(checkout / 'scripts/skills.py'), 'sync'],
                                env={'HOME': str(self.home), 'PATH': os.environ['PATH']},
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.home / 'pulled-installer-ran').read_text(), 'new revision')


if __name__ == "__main__":
    unittest.main()
