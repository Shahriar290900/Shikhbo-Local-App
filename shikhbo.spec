# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Shikhbo Local
# Build with:  pyinstaller shikhbo.spec

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

a = Analysis(
    [str(ROOT / 'app.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'raw_data'),   'raw_data'),
        (str(ROOT / 'static'),     'static'),
        (str(ROOT / 'templates'),  'templates'),
        (str(ROOT / 'scripts'),    'scripts'),
    ],
    hiddenimports=[
        'faiss',
        'rank_bm25',
        'langchain_community.vectorstores.faiss',
        'langchain_community.docstore.in_memory',
        'langchain_core.documents',
        'langchain_core.embeddings',
        'langdetect',
        'platformdirs',
        'flask',
        'flask_cors',
        'werkzeug',
        'requests',
        'numpy',
        'sqlite3',
        'webview',
        'webview.platforms.cocoa',
        'webview.platforms.winforms',
        'webview.platforms.gtk',
        'webbrowser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'google.genai', 'huggingface_hub', 'psycopg2', 'bcrypt',
        'sklearn', 'scipy', 'matplotlib', 'pandas', 'cv2', 'onnxruntime',
        'jupyter', 'notebook', 'IPython', 'ipykernel', 'ipywidgets',
        'PIL', 'Pillow', 'skimage', 'altair', 'plotly', 'bokeh',
        'tensorflow', 'torch', 'transformers', 'tokenizers',
        'numba', 'llvmlite', 'sympy', 'statsmodels',
        'grpc', 'google.cloud', 'google.api_core',
        'pytest', 'sphinx', 'docutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Shikhbo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # no terminal window on Windows
    icon=str(ROOT / 'logo.png') if (ROOT / 'logo.png').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Shikhbo',
)

# macOS .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Shikhbo.app',
        icon=str(ROOT / 'logo.png') if (ROOT / 'logo.png').exists() else None,
        bundle_identifier='com.shikhbo.local',
        info_plist={
            'NSMicrophoneUsageDescription': 'Shikhbo uses the microphone for voice input (Bengali STT).',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1',
            'LSMinimumSystemVersion': '12.0',
        },
    )
