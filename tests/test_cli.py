import os
import unittest
from unittest import mock
from types import SimpleNamespace
import io

from core import cli


class TestCLI(unittest.TestCase):
    def test_first_positional(self):
        self.assertEqual(cli._first_positional(['config', '--help']), 'config')
        self.assertEqual(cli._first_positional(['--profile', 'dev', 'server', 'list']), 'server')
        self.assertEqual(cli._first_positional(['--dry-run', '--', 'server', 'list']), 'server')
        self.assertIsNone(cli._first_positional(['--dry-run']))

    @mock.patch('core.cli.ensure_openstack_available')
    @mock.patch('core.cli.subprocess.run')
    @mock.patch('core.cli.get_catalog_env')
    @mock.patch('core.cli.ensure_profiles_structure')
    @mock.patch('core.cli.load_profiles_config')
    def test_handle_default_minimal_happy_path(
        self,
        m_load,
        m_struct,
        m_getenv,
        m_run,
        m_ensure_os,
    ):
        # Profiles and env
        m_load.return_value = ({'profiles': {'dev': {'password': 'p'}}}, None, False)
        m_struct.side_effect = lambda x: x
        m_getenv.return_value = {'OS_AUTH_URL': 'u', 'OS_USERNAME': 'user'}
        m_ensure_os.return_value = ({}, '/bin/openstack')
        m_run.return_value = SimpleNamespace(returncode=0)

        parser = cli.build_default_parser()
        args = parser.parse_args(['--profile', 'dev', '--catalog', 'app', 'server', 'list'])
        rc = cli.handle_default(args, cli.Path('.'))
        self.assertEqual(rc, 0)

    def test_top_level_help_includes_subcommands(self):
        buf = io.StringIO()
        with mock.patch('sys.stdout', new=buf):
            with self.assertRaises(SystemExit):
                cli.main(['-h'])
        out = buf.getvalue()
        self.assertIn('config', out)
        self.assertIn('report', out)

    @mock.patch('core.cli.ensure_openstack_available')
    @mock.patch('core.cli.get_catalog_env')
    @mock.patch('core.cli.ensure_profiles_structure')
    @mock.patch('core.cli.load_profiles_config')
    def test_handle_default_dry_run_masks_password(self, m_load, m_struct, m_getenv, m_ensure):
        m_load.return_value = ({'profiles': {'dev': {'password': 'secret'}}}, None, False)
        m_struct.side_effect = lambda x: x
        m_getenv.return_value = {'OS_AUTH_URL': 'u', 'OS_USERNAME': 'user'}
        m_ensure.return_value = ({}, '/bin/openstack')

        parser = cli.build_default_parser()
        args = parser.parse_args(['--profile', 'dev', '--catalog', 'app', '--dry-run', 'server', 'list'])
        buf = io.StringIO()
        with mock.patch('sys.stdout', new=buf):
            rc = cli.handle_default(args, cli.Path('.'))
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn('Resolved OS_* env:', out)
        self.assertIn('OS_PASSWORD=***', out)
        self.assertNotIn('secret', out)

    @mock.patch('core.cli.parse_rc_file', return_value={})
    @mock.patch('core.cli.get_catalog_env', return_value={})
    @mock.patch('core.cli.ensure_profiles_structure', side_effect=lambda x: x)
    @mock.patch('core.cli.load_profiles_config', return_value=({'profiles': {}}, None, False))
    def test_handle_default_missing_vars(self, *_):
        parser = cli.build_default_parser()
        # No OS_* values provided anywhere
        args = parser.parse_args(['--profile', 'dev', '--catalog', 'app', 'server', 'list'])
        with mock.patch('sys.stdin.isatty', return_value=False):
            rc = cli.handle_default(args, cli.Path('.'))
        self.assertEqual(rc, 2)

    @mock.patch('core.cli.get_catalog_env')
    @mock.patch('core.cli.ensure_profiles_structure', side_effect=lambda x: x)
    @mock.patch('core.cli.load_profiles_config')
    def test_double_dash_passthrough(self, m_load, m_struct, m_getenv):
        m_load.return_value = ({'profiles': {'dev': {'password': 'p'}}}, None, False)
        m_getenv.return_value = {'OS_AUTH_URL': 'u', 'OS_USERNAME': 'user'}
        parser = cli.build_default_parser()
        args = parser.parse_args(['--profile', 'dev', '--catalog', 'app', '--dry-run', '--', 'server', 'list'])
        buf = io.StringIO()
        with mock.patch('sys.stdout', new=buf):
            with mock.patch('sys.stdin.isatty', return_value=False):
                rc = cli.handle_default(args, cli.Path('.'))
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn('Command: openstack server list', out)


if __name__ == '__main__':
    unittest.main()
