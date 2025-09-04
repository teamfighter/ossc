import json
import os
import tempfile
from pathlib import Path
import unittest

from types import SimpleNamespace

from core import config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self.td = tempfile.TemporaryDirectory()
        os.environ['XDG_CONFIG_HOME'] = self.td.name

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self.td.cleanup()

    def test_config_path_respects_xdg(self):
        p = config.config_path()
        self.assertTrue(str(p).startswith(self.td.name))
        self.assertTrue(str(p).endswith('ossc/profiles.json'))

    def test_load_profiles_config_empty(self):
        data, path, _ = config.load_profiles_config(Path('.'))
        self.assertEqual(data, {})
        self.assertTrue(str(path).endswith('profiles.json'))

    def test_save_and_merge_profiles_config(self):
        cfg_path = config.config_path()
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps({'profiles': {'dev': {'catalogs': {'app': {'OS_X': '1'}}}}}), encoding='utf-8')
        # Save new profile and new field into existing dev
        config.save_profiles_config(cfg_path, {
            'profiles': {
                'dev': {'catalogs': {'app': {'OS_Y': '2'}}},
                'prod': {'catalogs': {'net': {'OS_Z': '3'}}},
            }
        })
        merged = json.loads(cfg_path.read_text(encoding='utf-8'))
        self.assertEqual(merged['profiles']['dev']['catalogs']['app']['OS_X'], '1')
        self.assertEqual(merged['profiles']['dev']['catalogs']['app']['OS_Y'], '2')
        self.assertIn('prod', merged['profiles'])

    def test_ensure_profiles_structure_migration(self):
        old = {
            'dev': {'username': 'u', 'catalogs': {'app': {'OS_A': 'a'}}},
            'misc': {'k': 'v'},
        }
        migrated = config.ensure_profiles_structure(old)
        self.assertIn('profiles', migrated)
        self.assertIn('dev', migrated['profiles'])
        self.assertIn('catalogs', migrated['profiles']['dev'])

    def test_get_catalog_env(self):
        cfg = {'profiles': {'dev': {'catalogs': {'app': {'OS_A': '1'}}}}}
        self.assertEqual(config.get_catalog_env(cfg, 'dev', 'app'), {'OS_A': '1'})
        self.assertIsNone(config.get_catalog_env(cfg, 'prod', 'app'))
        self.assertIsNone(config.get_catalog_env(cfg, 'dev', 'net'))

    def test_resolve_password_precedence(self):
        args = SimpleNamespace(password='flag')
        self.assertEqual(config.resolve_password(args, {'password': 'p'}), 'flag')
        args = SimpleNamespace(password=None)
        os.environ['OSS_PASSWORD'] = 'envpw'
        self.assertEqual(config.resolve_password(args, {'password': 'p'}), 'envpw')
        del os.environ['OSS_PASSWORD']
        self.assertEqual(config.resolve_password(args, {'password': 'p'}), 'p')

    def test_resolve_username_precedence(self):
        rc_env = {'OS_USERNAME': 'rcuser'}
        args = SimpleNamespace(username='flag')
        self.assertEqual(config.resolve_username(args, {'username': 'p'}, rc_env), 'flag')
        args = SimpleNamespace(username=None)
        os.environ['OSS_USERNAME'] = 'envuser'
        self.assertEqual(config.resolve_username(args, {'username': 'p'}, rc_env), 'envuser')
        del os.environ['OSS_USERNAME']
        self.assertEqual(config.resolve_username(args, {'username': 'p'}, rc_env), 'p')
        self.assertEqual(config.resolve_username(args, {}, rc_env), 'rcuser')


if __name__ == '__main__':
    unittest.main()

