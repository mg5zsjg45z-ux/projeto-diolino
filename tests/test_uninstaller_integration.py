"""Compile/install/uninstall a tiny fixture; never invoke a real Diolino uninstaller."""
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import time
import unittest
import uuid


DEFAULT_COMPILER = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/DiolinoBuildTools/InnoSetup6/ISCC.exe'
COMPILER = Path(os.environ.get('DIOLINO_ISCC', DEFAULT_COMPILER))


@unittest.skipUnless(os.name == 'nt' and COMPILER.is_file(), 'Requer compilador Inno Setup local no Windows.')
class UninstallerIntegrationTests(unittest.TestCase):
    def test_confirmed_cleanup_is_scoped_and_silent_uninstall_requires_opt_in(self):
        with tempfile.TemporaryDirectory(dir=Path('test-output').resolve()) as directory:
            root=Path(directory).resolve()
            profile=root/'profile'; data=profile/'AppData'/'ProjetoDiolino'
            program=root/'program'; startup=root/'startup'; outside=root/'external'
            data.mkdir(parents=True);startup.mkdir();outside.mkdir()
            for relative in ['diolino.sqlite3','backups/old.sqlite3','icloud-connection.bin','appearance.json','offline-ai/model.bin']:
                path=data/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic test data')
            (outside/'export.json').write_text('synthetic external export')
            for relative in ['Desktop/Diolino.lnk','OneDrive/Desktop/Diolino.lnk']:
                path=profile/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic link')
            (startup/'Diolino.lnk').write_text('synthetic link')
            # A base-Python companion must stop too, not just a venv launcher.
            scripts=root/'scripts';scripts.mkdir()
            (scripts/'start_mobile.ps1').write_text('# isolated fixture; never executed')
            companion_script=root/'mobile_server.py'
            companion_script.write_text("import time\nfrom pathlib import Path\nPath(__file__).with_suffix('.ready').write_text('ready')\nwhile True: time.sleep(0.1)\n")
            link_script=root/'create-test-link.ps1'
            link_script.write_text(f'''$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut('{startup / 'Diolino - acesso iPhone.lnk'}')
$link.TargetPath = 'powershell.exe'
$link.Arguments = '-NoProfile -WindowStyle Hidden -File "{scripts / 'start_mobile.ps1'}"'
$link.Save()
''')
            subprocess.run(['powershell','-NoProfile','-File',str(link_script)],capture_output=True,check=True)
            pythonw=Path(sys._base_executable).with_name('pythonw.exe')
            # Native DelTree must unlink junctions rather than deleting their targets.
            junction=data/'linked-external'
            subprocess.run(['cmd','/c','mklink','/J',str(junction),str(outside)],capture_output=True,check=True)
            (root/'fixture.txt').write_text('only a harmless installer fixture')
            include=Path('scripts/uninstall_cleanup.iss').resolve()
            script=root/'fixture.iss'
            script.write_text(f'''#define CleanupDataRoot "{data}"
#define CleanupProgramRoot "{program}"
#define CleanupStartupRoot "{startup}"
#define CleanupUserRoot "{profile}"
[Setup]
AppId=Diolino-Uninstall-Test-{uuid.uuid4().hex}
AppName=Diolino isolated uninstall test
AppVersion=1.0
DefaultDirName={program}
PrivilegesRequired=lowest
OutputDir={root}
OutputBaseFilename=fixture-setup
UninstallDisplayName=Diolino isolated uninstall test
CreateAppDir=yes
[Files]
Source: "{root/'fixture.txt'}"; DestDir: "{{app}}"
#include "{include}"
''',encoding='utf-8-sig')
            compiled=subprocess.run([str(COMPILER),str(script)],capture_output=True,text=True)
            self.assertEqual(compiled.returncode,0,compiled.stdout+compiled.stderr)
            installer=root/'fixture-setup.exe'; uninstaller=program/'unins000.exe'
            self.assertTrue(installer.resolve().is_relative_to(root))
            subprocess.run([str(installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True,timeout=45)
            # Match start_mobile.ps1, which quotes the script path even without spaces.
            companion=subprocess.Popen(f'"{pythonw}" "{companion_script}"',creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                for _ in range(40):
                    if companion_script.with_suffix('.ready').exists():break
                    time.sleep(.05)
                self.assertTrue(companion_script.with_suffix('.ready').exists())
                self.assertTrue((data/'diolino.sqlite3').exists(),'Installation must preserve existing data')
                self.assertTrue(uninstaller.resolve().is_relative_to(root))
                declined=subprocess.run([str(uninstaller),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],timeout=45)
                self.assertNotEqual(declined.returncode,0)
                self.assertTrue((data/'diolino.sqlite3').exists())
                self.assertIsNone(companion.poll(),'Refusing uninstall must not stop the companion')
                accepted=subprocess.run([str(uninstaller),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/PURGEDATA=1'],timeout=45)
                self.assertEqual(accepted.returncode,0)
                self.assertEqual(companion.wait(timeout=5),0,'Uninstaller must wait for the companion shutdown before returning')
                self.assertFalse(data.exists())
                self.assertTrue((outside/'export.json').exists(),'External files must survive, including junction targets')
                self.assertFalse((startup/'Diolino.lnk').exists())
                self.assertFalse((startup/'Diolino - acesso iPhone.lnk').exists())
                self.assertFalse((profile/'Desktop/Diolino.lnk').exists())
                self.assertFalse((profile/'OneDrive/Desktop/Diolino.lnk').exists())
            finally:
                if companion.poll() is None:
                    companion.terminate();companion.wait(timeout=5)
                if uninstaller.exists():
                    subprocess.run([str(uninstaller),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/PURGEDATA=1'],timeout=45)


if __name__=='__main__':unittest.main()
