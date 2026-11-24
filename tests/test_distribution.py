"""Distribution boundaries: never package personal records or launch scripts."""
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from scripts.package_portable import package


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='test-output')
        self.root=Path(self.temp.name)
        self.source=self.root/'releases/1.0.1/Diolino'
        self.source.mkdir(parents=True)
        (self.source/'Diolino.exe').write_bytes(b'isolated fixture')

    def tearDown(self):
        self.temp.cleanup()

    def test_packages_only_release_and_rejects_personal_database(self):
        (self.root/'releases/1.0.1/private.sqlite3').write_bytes(b'outside release')
        with ZipFile(package('1.0.1',self.root)) as archive:
            self.assertEqual(archive.namelist(),['Diolino/Diolino.exe'])
        (self.source/'private.sqlite3').write_bytes(b'personal database')
        with self.assertRaises(ValueError):package('1.0.1',self.root)
        with self.assertRaises(ValueError):package('../1.0.0',self.root)

    def test_native_installer_scopes_data_cleanup_and_has_no_automatic_execution(self):
        script=Path('scripts/diolino.iss').read_text(encoding='utf-8')
        self.assertNotIn('[Run]',script)
        self.assertNotIn('[Code]',script)
        self.assertNotIn('powershell',script.lower())
        self.assertIn('#include "uninstall_cleanup.iss"',script)
        cleanup=Path('scripts/uninstall_cleanup.iss').read_text(encoding='utf-8')
        self.assertIn('"{localappdata}\\ProjetoDiolino"',cleanup)
        self.assertIn('DelTree(Root, True, True, True)',cleanup)
        self.assertNotIn("DelTree(ExpandConstant('{app}'),",cleanup)
        self.assertIn('MB_YESNO or MB_DEFBUTTON2',cleanup)
        self.assertIn('PURGEDATA|0',cleanup)
        self.assertIn('DiolinoProcessRunning',cleanup)
        self.assertIn('PrivilegesRequired=lowest',script)
        self.assertIn('Tasks: startup',script)
        build=Path('scripts/build_distribution.ps1').read_text(encoding='utf-8-sig')
        self.assertNotIn('installer.py',build)
        self.assertNotIn('--onefile',build)

if __name__=='__main__':unittest.main()
