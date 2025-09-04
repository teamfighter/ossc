import os
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from core import env as envmod


class TestEnv(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self.td = tempfile.TemporaryDirectory()
        os.environ['XDG_CONFIG_HOME'] = self.td.name

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self.td.cleanup()

    def test_user_venv_paths(self):
        paths = envmod.user_venv_paths()
        self.assertEqual(len(paths), 1)
        self.assertTrue(str(paths[0]).endswith('ossc/venv'))
        self.assertTrue(str(paths[0]).startswith(self.td.name))

    def test_venv_bin_dir(self):
        p = Path('/tmp/venv')
        self.assertEqual(envmod.venv_bin_dir(p), p / 'bin')

    def test_ensure_openstack_available_prefers_user_venv(self):
        # Prepare fake user venv with openstack exe
        user_venv = envmod.user_venv_paths()[0]
        bin_dir = envmod.venv_bin_dir(user_venv)
        bin_dir.mkdir(parents=True, exist_ok=True)
        exe = bin_dir / 'openstack'
        exe.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
        os.chmod(exe, 0o755)

        with mock.patch('shutil.which', return_value=None):
            # Use a temporary repo root without local .venv
            tmp_repo = Path(self.td.name) / 'repo-root'
            tmp_repo.mkdir(parents=True, exist_ok=True)
            new_env, path = envmod.ensure_openstack_available(tmp_repo, {})
            self.assertIn('PATH', new_env)
            self.assertTrue(path.endswith('openstack'))
            self.assertIn(str(bin_dir), new_env['PATH'])

    def test_ensure_openstack_prefers_repo_venv_over_user(self):
        # Create both user venv and repo local .venv; repo .venv should win
        user_venv = envmod.user_venv_paths()[0]
        user_bin = envmod.venv_bin_dir(user_venv)
        user_bin.mkdir(parents=True, exist_ok=True)
        (user_bin / 'openstack').write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
        os.chmod(user_bin / 'openstack', 0o755)

        tmp_repo = Path(self.td.name) / 'repo-root2'
        local_bin = envmod.venv_bin_dir(tmp_repo / '.venv')
        local_bin.mkdir(parents=True, exist_ok=True)
        (local_bin / 'openstack').write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
        os.chmod(local_bin / 'openstack', 0o755)

        with mock.patch('shutil.which', return_value=None):
            new_env, path = envmod.ensure_openstack_available(tmp_repo, {})
            self.assertEqual(path, str(local_bin / 'openstack'))


if __name__ == '__main__':
    unittest.main()
