# Build with: python -m PyInstaller --clean --noconfirm ETS2AcademyTracker.spec
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['main.py'], pathex=[], binaries=[],
    datas=[('database/schema.sql','database')] + collect_data_files('tzdata'),
    hiddenimports=['watchdog.observers.read_directory_changes'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtQml','PySide6.QtQuick'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,a.binaries,a.datas,[],name='ETS2AcademyTracker',
          debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False)
