"""Build and verify Hellpod Drop Hold without launching the game.

python -B scripts/build.py                  release package: releases/Hellpod-Drop-Hold-v<VERSION>.zip
python -B scripts/build.py --test-hold 5    test package: every own drop pod is held 5 s, loading screen
                                            or not, to check the hold in solo play; never publish it
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True

from archive import LUA, sha, EXE_SHA, GAME_DLL_SHA, GAME, ARCHIVE, make_archive, resource_hash
from package import package_release
from module import build_module

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src'
TESTS = ROOT / 'tests'
GAME_LUA = TESTS / 'game_lua.py'
# Local copies that must stay byte-identical to the workspace's canonical ones (checked when present).
CANONICAL = {'tests/frame_budget.lua': 'PerformanceBaseline/frame_budget.lua',
             'tests/game_lua.py': 'PerformanceBaseline/game_lua.py'}
VERSION = '1.2.1'
MODULE = 'mods/cowboybingus/hellpod_drop_hold'
GUID = '6c5b0317-3dc7-4cb6-88d0-0cd3d5c01461'
TEST_GUID = '2ade80d6-1545-47e4-b7a8-ff43db3aff8b'
INSPECTOR = Path(os.environ.get('HD2_PATCH_INSPECT', ROOT.parent / 'tools/bin/hd2-patch-inspect.exe'))
DESCRIPTION = ('Joining a mission in progress, or loading slowly, no longer costs you the drop: '
               'your hellpod waits in the sky until the loading screen is gone.')


def run(args, **kwargs):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def check_game():
    for relative, expected in [('bin/helldivers2.exe', EXE_SHA), ('data/game/game.dll', GAME_DLL_SHA)]:
        if sha((GAME / relative).read_bytes()) != expected:
            raise ValueError('Unsupported game build: ' + relative)


def offline_tests():
    for local, shared in CANONICAL.items():
        canonical = ROOT.parent / shared
        if canonical.exists() and canonical.read_bytes() != (ROOT / local).read_bytes():
            raise ValueError(f'{local} differs from the canonical {shared}')
    env = dict(os.environ, LUA_PATH=str(LUA.parent / '?.lua') + ';;')
    # The same checks in the workspace LuaJIT and in the game's own lua51.dll (tests/game_lua.py, HD2_LUA51_DLL);
    # each run passes its host executable's SHA-256, which the adapter's module hash must return.
    tests = run([LUA, TESTS / 'test_hold.lua', SOURCE, sha(LUA.read_bytes())], env=env)
    host = Path(sys.executable)
    return tests + run([sys.executable, GAME_LUA, TESTS / 'test_hold.lua', SOURCE, sha(host.read_bytes())], env=env)


def archive(build, resources):
    data = build / 'data'
    data.mkdir(exist_ok=True)
    (data / ARCHIVE).write_bytes(make_archive(resources))
    for suffix in ('.stream', '.gpu_resources'):
        (data / (ARCHIVE + suffix)).write_bytes(b'')
    run([INSPECTOR, '--patch', data / ARCHIVE,
         '--out', build / 'archive-inspection.json', '--extract-dir', build / 'archive-resources'])
    inspection = json.loads((build / 'archive-inspection.json').read_text())
    actual = {int(item['name']['hex'], 16) for item in inspection['resources']}
    expected = {resource_hash(MODULE), resource_hash(MODULE + '_impl')}
    if inspection['num_files'] != 2 or actual != expected or any(
            item['type']['hex'] != '0xa14e8dfa2cd117e2' for item in inspection['resources']):
        raise ValueError('Archive must contain only this mod: its declared entry and its implementation')
    folder = build.relative_to(ROOT).as_posix()
    return {f'data/{ARCHIVE}{suffix}': f'{folder}/data/{ARCHIVE}{suffix}' for suffix in ('', '.stream', '.gpu_resources')}


def report_for(files, tests, test_hold):
    name = 'Hellpod Drop Hold' + (' TEST BUILD' if test_hold else '')
    report = {
        'name': name, 'slug': 'HellpodDropHold', 'version': VERSION,
        'guid': TEST_GUID if test_hold else GUID, 'revision': revision(test_hold),
        'description': (f'TEST BUILD, never publish: every own drop pod is held {test_hold:g} s.' if test_hold
                        else DESCRIPTION) + ' Requires Bingus Shared Loader.',
        'game_exe_sha256': EXE_SHA, 'game_dll_sha256': GAME_DLL_SHA,
        'deployment_files': files, 'files': {path: sha((ROOT / path).read_bytes()) for path in files.values()},
        'data_change': {'manager_pointer_rva': '0x3326D58', 'ui_state_pointer_rva': '0x347CE28',
                        'settings_owner_rva': '0x346BF98', 'pod_local_state_field': 32,
                        'writes_per_drop': 2, 'loading_screens': [2, 4], 'grace_seconds': 0,
                        'longest_hold_seconds': 120, 'hold_speed_m_s': 0.5},
        'continuous_update_hook': True, 'shutdown_hook': True, 'executable_code_writes': 0,
        'test_hold_seconds': test_hold, 'offline_tests': tests.strip().splitlines(),
        'requires': [{'name': 'Bingus Shared Loader', 'guid': '612eaf70-d682-43c7-9efd-16dcc695f977', 'api': 1}],
    }
    sources = list(SOURCE.glob('*.lua')) + list(TESTS.glob('*.lua')) + list((ROOT / 'scripts').glob('*.py'))
    report['source_sha256'] = {path.relative_to(ROOT).as_posix(): sha(path.read_bytes()) for path in sources}
    return report


def revision(test_hold):
    return f'data-v{VERSION}' + (f'-testhold{test_hold:g}' if test_hold else '')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test-hold', type=float, help='test package: hold every own drop pod this many seconds')
    options = parser.parse_args()
    test_hold = options.test_hold
    if test_hold is not None and not 0 < test_hold <= 60:
        raise ValueError('--test-hold takes 0 to 60 seconds')
    check_game()
    build = ROOT / ('build-test' if test_hold else 'build')
    resources = build_module(ROOT, build, MODULE, revision(test_hold), test_hold)
    tests = offline_tests()
    (build / 'offline-tests.txt').write_text(tests)
    files = archive(build, resources)
    report = report_for(files, tests, test_hold)
    release = package_release(ROOT, build, report)
    package_tests = run([sys.executable, TESTS / 'test_package.py', release, report['name'], report['revision'], VERSION])
    (build / 'package-tests.txt').write_text(package_tests, encoding='utf-8')
    report['package_tests'] = package_tests.strip().splitlines()
    report['release'] = {'path': Path(os.path.relpath(release, ROOT)).as_posix(), 'sha256': sha(release.read_bytes())}
    (build / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(tests.strip())
    print(package_tests.strip())
    print('Built ' + release.name + '; no installation or game launch performed.')


if __name__ == '__main__':
    main()
