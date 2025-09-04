import io
import os
import shutil
import tempfile
from pathlib import Path
import unittest
from unittest import mock
from types import SimpleNamespace

from core.commands import report_cmd


class TestReportCmd(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()
        self.td = tempfile.TemporaryDirectory()
        os.environ['XDG_CONFIG_HOME'] = self.td.name

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self.td.cleanup()

    @mock.patch('core.commands.report_cmd.resolve_username', return_value='user')
    @mock.patch('core.commands.report_cmd.resolve_password', return_value='pass')
    @mock.patch('core.commands.report_cmd.ensure_openstack_available', return_value=({}, '/bin/openstack'))
    @mock.patch('core.commands.report_cmd.subprocess.run')
    def test_report_writes_files(self, m_run, m_ensure, m_pw, m_user):
        # Seed profiles in memory via load_profiles_config monkeypatch
        profiles = {
            'profiles': {
                'dev': {
                    'catalogs': {
                        'app': {'OS_AUTH_URL': 'url', 'OS_USERNAME': 'u'},
                    }
                }
            }
        }

        def fake_load(_):
            return profiles, Path('ignored'), False

        with mock.patch('core.commands.report_cmd.load_profiles_config', side_effect=fake_load):
            m_run.return_value = SimpleNamespace(returncode=0, stdout='OK\n', stderr='')
            args = SimpleNamespace(out=str(Path(self.td.name) / 'out'), format='table', profile=None, catalog=None)
            code = report_cmd.handle(args, Path('.'))
            self.assertEqual(code, 0)
            report_file = Path(args.out) / 'dev' / 'app' / 'report.txt'
            self.assertTrue(report_file.exists())
            content = report_file.read_text(encoding='utf-8')
            self.assertIn('OK', content)

    @mock.patch('core.commands.report_cmd.resolve_username', return_value=None)
    @mock.patch('core.commands.report_cmd.resolve_password', return_value=None)
    def test_report_missing_vars_writes_notice(self, m_pw, m_user):
        profiles = {
            'profiles': {
                'dev': {'catalogs': {'app': {'OS_USERNAME': '', 'OS_AUTH_URL': ''}}}
            }
        }

        def fake_load(_):
            return profiles, Path('ignored'), False

        args = SimpleNamespace(out=str(Path(self.td.name) / 'out2'), format='table', profile=None, catalog=None)
        with mock.patch('core.commands.report_cmd.load_profiles_config', side_effect=fake_load):
            code = report_cmd.handle(args, Path('.'))
        self.assertEqual(code, 2)
        report_file = Path(args.out) / 'dev' / 'app' / 'report.txt'
        self.assertTrue(report_file.exists())
        content = report_file.read_text(encoding='utf-8')
        self.assertIn('Missing variables:', content)

    @mock.patch('core.commands.report_cmd.resolve_username', return_value='user')
    @mock.patch('core.commands.report_cmd.resolve_password', return_value='pass')
    @mock.patch('core.commands.report_cmd.ensure_openstack_available', return_value=({}, '/bin/openstack'))
    @mock.patch('core.commands.report_cmd.subprocess.run')
    def test_report_filters(self, m_run, *_):
        profiles = {
            'profiles': {
                'dev': {'catalogs': {'app': {'OS_AUTH_URL': 'u', 'OS_USERNAME': 'u'}}},
                'prod': {'catalogs': {'app': {'OS_AUTH_URL': 'u', 'OS_USERNAME': 'u'}, 'net': {'OS_AUTH_URL': 'u', 'OS_USERNAME': 'u'}}},
            }
        }

        def fake_load(_):
            return profiles, Path('ignored'), False

        m_run.return_value = SimpleNamespace(returncode=0, stdout='OK\n', stderr='')

        # profile+catalog
        with mock.patch('core.commands.report_cmd.load_profiles_config', side_effect=fake_load):
            args = SimpleNamespace(out=str(Path(self.td.name) / 'outf'), format='table', profile='prod', catalog='app')
            code = report_cmd.handle(args, Path('.'))
            self.assertEqual(code, 0)
            self.assertTrue((Path(args.out) / 'prod' / 'app' / 'report.txt').exists())

        # profile only
        with mock.patch('core.commands.report_cmd.load_profiles_config', side_effect=fake_load):
            args = SimpleNamespace(out=str(Path(self.td.name) / 'outf2'), format='table', profile='prod', catalog=None)
            code = report_cmd.handle(args, Path('.'))
            self.assertEqual(code, 0)
            self.assertTrue((Path(args.out) / 'prod' / 'app' / 'report.txt').exists())
            self.assertTrue((Path(args.out) / 'prod' / 'net' / 'report.txt').exists())

        # catalog only across profiles
        with mock.patch('core.commands.report_cmd.load_profiles_config', side_effect=fake_load):
            args = SimpleNamespace(out=str(Path(self.td.name) / 'outf3'), format='table', profile=None, catalog='app')
            code = report_cmd.handle(args, Path('.'))
            self.assertEqual(code, 0)
            self.assertTrue((Path(args.out) / 'dev' / 'app' / 'report.txt').exists())
            self.assertTrue((Path(args.out) / 'prod' / 'app' / 'report.txt').exists())

    def test_report_filter_errors(self):
        profiles = {'profiles': {'dev': {'catalogs': {}}}}

        def fake_load(_):
            return profiles, Path('ignored'), False

        # Profile not found
        with mock.patch('core.commands.report_cmd.load_profiles_config', side_effect=fake_load):
            args = SimpleNamespace(out=str(Path(self.td.name) / 'o1'), format='table', profile='prod', catalog=None)
            code = report_cmd.handle(args, Path('.'))
            self.assertEqual(code, 2)

        # Catalog not found
        profiles2 = {'profiles': {'dev': {'catalogs': {'app': {'OS_AUTH_URL': 'u'}}}}}

        def fake_load2(_):
            return profiles2, Path('ignored'), False

        with mock.patch('core.commands.report_cmd.load_profiles_config', side_effect=fake_load2):
            args = SimpleNamespace(out=str(Path(self.td.name) / 'o2'), format='table', profile='dev', catalog='net')
            code = report_cmd.handle(args, Path('.'))
            self.assertEqual(code, 2)


if __name__ == '__main__':
    unittest.main()
