import os
import tempfile
from pathlib import Path
import unittest

from core import rc


class TestRC(unittest.TestCase):
    def test_build_rc_path_with_override_absolute(self):
        # Use an absolute path valid for the current OS
        abs_p = (Path.cwd() / 'rc.sh').resolve()
        p = rc.build_rc_path(Path('/repo'), 'dev', 'app', str(abs_p))
        self.assertTrue(p.is_absolute())
        self.assertEqual(p, abs_p)

    def test_build_rc_path_with_override_relative(self):
        repo = Path('/repo')
        p = rc.build_rc_path(repo, 'dev', 'app', 'rel/rc.sh')
        self.assertEqual(p, repo / 'rel' / 'rc.sh')

    def test_build_rc_path_default(self):
        repo = Path('/repo')
        p = rc.build_rc_path(repo, 'dev', 'app', None)
        self.assertEqual(p, repo / 'dev' / 'rc-app.sh')

    def test_parse_rc_file_basic_and_quotes(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'rc.sh'
            f.write_text(
                """
                # comment\n
                export OS_USERNAME='user'\n
                OS_PASSWORD=pass\n
                OS_AUTH_URL="https://example"\n
                echo ignored\n
                [[ ignored ]]\n
                INVALID LINE\n
                """,
                encoding='utf-8',
            )
            env = rc.parse_rc_file(f)
            self.assertEqual(env['OS_USERNAME'], 'user')
            self.assertEqual(env['OS_PASSWORD'], 'pass')
            self.assertEqual(env['OS_AUTH_URL'], 'https://example')
            self.assertNotIn('INVALID', ''.join(env.keys()))

    def test_parse_rc_file_missing(self):
        with self.assertRaises(FileNotFoundError):
            rc.parse_rc_file(Path('no_such_file.sh'))


if __name__ == '__main__':
    unittest.main()
