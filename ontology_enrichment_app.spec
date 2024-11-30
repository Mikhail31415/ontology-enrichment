# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ontology_enrichment_app.py'],
    pathex=[],
    binaries=[],
    datas=[('resources/application.yaml', 'resources'), ('.venv/Lib/site-packages/owlready2/pellet', 'owlready2/pellet'), ('.venv/Lib/site-packages/tiktoken_ext/openai_public.py', 'tiktoken_ext')],
    hiddenimports=['tiktoken.load'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ontology_enrichment_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ontology_enrichment_app',
)
