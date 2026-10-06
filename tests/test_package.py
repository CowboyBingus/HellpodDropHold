"""Verify a release ZIP: contents, manager manifest, provenance hashes, resource identity, privacy, relocation.

python tests/test_package.py <zip> <display name> <revision> <version>
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zipfile


def main():
    release, name, revision, version = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    archive_name = '9ba626afa44a3aa3.patch_0'
    with zipfile.ZipFile(release) as package:
        payloads = {item: package.read(item) for item in package.namelist()}
        expected = {f'data/{archive_name}{suffix}' for suffix in ('', '.stream', '.gpu_resources')}
        expected |= {'manifest.json', 'HellpodDropHold-manifest.json', 'HellpodDropHold-README.txt'}
        assert set(payloads) == expected and len(package.namelist()) == len(expected), sorted(payloads)
        assert not any(item.lower().endswith(('.dll', '.exe', '.lua', '.ps1')) for item in payloads)
        manifest = json.loads(payloads['manifest.json'])
        assert manifest.get('Version') == 1, 'HD2MM requires an explicit V1 manifest'
        assert manifest['Name'] == name + ' - v' + version, manifest['Name']
        assert manifest['Options'] == [{'Name': manifest['Name'], 'Description': manifest['Description'],
                                        'Include': ['data']}]
        provenance = json.loads(payloads['HellpodDropHold-manifest.json'])
        assert provenance['revision'] == revision and provenance['runtime_verified'] is False
        assert provenance['requires'] == [{'name': 'Bingus Shared Loader',
                                           'guid': '612eaf70-d682-43c7-9efd-16dcc695f977', 'api': 1}]
        for item, digest in provenance['files'].items():
            assert hashlib.sha256(payloads[item]).hexdigest().upper() == digest, item
        main_archive = payloads['data/' + archive_name]
        assert struct.unpack_from('<III', main_archive) == (0xF0000011, 1, 2)
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        from archive import resource_hash
        module = 'mods/cowboybingus/hellpod_drop_hold'
        bodies = {}
        for index in range(2):
            entry = struct.unpack_from('<7Q6I', main_archive, 104 + index * 80)
            assert entry[1] == 0xA14E8DFA2CD117E2 and entry[-1] == index
            offset, size = entry[2], entry[7]
            assert offset % 16 == 0 and offset + size <= len(main_archive)
            assert struct.unpack_from('<II', main_archive, offset) == (size - 8, 2)
            bodies[entry[0]] = main_archive[offset + 8:offset + size]
        assert set(bodies) == {resource_hash(module), resource_hash(module + '_impl')}
        # The entry is plaintext and declares itself on its first line, within 256 bytes, so the
        # loader's discovery starts it; the implementation is stripped non-GC64 LuaJIT bytecode.
        declared = bodies[resource_hash(module)]
        first_line = declared.split(b'\n', 1)[0]
        assert first_line == b'-- HD2-Addon: ' + module.encode() and len(first_line) < 256
        assert b"require('" + module.encode() + b"_impl')" in declared
        assert bodies[resource_hash(module + '_impl')][:5] == b'\x1bLJ\x02\x02'
        assert payloads['data/' + archive_name + '.stream'] == b''
        assert payloads['data/' + archive_name + '.gpu_resources'] == b''
        for data in payloads.values():
            lowered = data.lower()
            assert b'users\\' not in lowered and b'users/' not in lowered
            assert b'virtualprotect' not in lowered and b'flushinstructioncache' not in lowered
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'An unrelated install location'
            package.extractall(destination)
            assert all((destination / item).read_bytes() == data for item, data in payloads.items())
    print('PASS: archive contents, V1 manager manifest, hashes, resource identity, privacy and relocation')
    print('1 package check passed; ZIP contains three runtime archive files and no custom DLL.')


if __name__ == '__main__':
    main()
