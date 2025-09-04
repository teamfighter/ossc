import io
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from core.commands import config_cmd


class TestConfigCmd(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self.td = tempfile.TemporaryDirectory()
        os.environ['XDG_CONFIG_HOME'] = self.td.name

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self.td.cleanup()

    def test_import_rc_single(self):
        # Prepare RC file
        repo = Path(self.td.name)
        rc_dir = repo / 'dev'
        rc_dir.mkdir(parents=True, exist_ok=True)
        rc_path = rc_dir / 'rc-app.sh'
        rc_path.write_text('export OS_USERNAME=user\nOS_PASSWORD=pass\nOS_AUTH_URL=url\n', encoding='utf-8')

        args = mock.Mock()
        args.cfg_cmd = 'import-rc'
        args.profile = 'dev'
        args.catalog = 'app'
        args.rc_file = None
        args.rc_dir = None

        code = config_cmd.handle(args, repo)
        self.assertEqual(code, 0)
        cfg_file = Path(os.environ['XDG_CONFIG_HOME']) / 'ossc' / 'profiles.json'
        data = json.loads(cfg_file.read_text(encoding='utf-8'))
        self.assertEqual(data['profiles']['dev']['catalogs']['app']['OS_USERNAME'], 'user')

    def test_import_rc_batch(self):
        repo = Path(self.td.name)
        rc_dir = repo / 'rcs'
        rc_dir.mkdir(parents=True, exist_ok=True)
        (rc_dir / 'rc-app.sh').write_text('OS_PROJECT_ID=app\nOS_AUTH_URL=x\n', encoding='utf-8')
        (rc_dir / 'rc-net.sh').write_text('OS_PROJECT_ID=net\nOS_AUTH_URL=x\n', encoding='utf-8')

        args = mock.Mock()
        args.cfg_cmd = 'import-rc'
        args.profile = 'dev'
        args.catalog = None
        args.rc_file = None
        args.rc_dir = str(rc_dir)

        buf = io.StringIO()
        with mock.patch('sys.stdout', new=buf):
            code = config_cmd.handle(args, repo)
        self.assertEqual(code, 0)
        cfg_file = Path(os.environ['XDG_CONFIG_HOME']) / 'ossc' / 'profiles.json'
        data = json.loads(cfg_file.read_text(encoding='utf-8'))
        self.assertIn('app', data['profiles']['dev']['catalogs'])
        self.assertIn('net', data['profiles']['dev']['catalogs'])

    def test_list_and_setcred(self):
        # Seed config
        cfg_file = Path(os.environ['XDG_CONFIG_HOME']) / 'ossc' / 'profiles.json'
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps({'profiles': {'dev': {'catalogs': {'app': {}}}}}), encoding='utf-8')

        args = mock.Mock()
        args.cfg_cmd = 'list'
        buf = io.StringIO()
        with mock.patch('sys.stdout', new=buf):
            code = config_cmd.handle(args, Path('.'))
        self.assertEqual(code, 0)
        self.assertIn('dev', buf.getvalue())

        args = mock.Mock()
        args.cfg_cmd = 'set-cred'
        args.profile = 'dev'
        args.password = 'secret'
        code = config_cmd.handle(args, Path('.'))
        self.assertEqual(code, 0)
        data = json.loads(cfg_file.read_text(encoding='utf-8'))
        self.assertEqual(data['profiles']['dev']['password'], 'secret')

    def test_import_rc_single_requires_catalog(self):
        args = mock.Mock()
        args.cfg_cmd = 'import-rc'
        args.profile = 'dev'
        args.catalog = None
        args.rc_file = None
        args.rc_dir = None
        code = config_cmd.handle(args, Path('.'))
        self.assertEqual(code, 2)

    def test_import_rc_dir_not_directory(self):
        args = mock.Mock()
        args.cfg_cmd = 'import-rc'
        args.profile = 'dev'
        args.catalog = None
        args.rc_file = None
        args.rc_dir = __file__  # a file, not a directory
        code = config_cmd.handle(args, Path('.'))
        self.assertEqual(code, 2)


if __name__ == '__main__':
    unittest.main()
