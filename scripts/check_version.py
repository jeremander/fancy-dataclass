#!/usr/bin/env python3

from pathlib import Path
import re
import subprocess
import sys


CHANGELOG = 'docs/CHANGELOG.md'
VERSION_REGEX = re.compile(r'\d+\.\d+\.\d+')

def error(msg):
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)

def parse_version_str(version):
    return tuple(map(int, version.split('.')))

def get_latest_built_version():
    dist_dir = Path('dist')
    if not dist_dir.exists():
        return None
    max_version = None
    for path in dist_dir.glob('fancy_dataclass-*.whl'):
        if (match := VERSION_REGEX.search(path.name)):
            version = parse_version_str(match.group())
            max_version = version if (max_version is None) else max(version, max_version)
    return '.'.join(map(str, max_version)) if max_version else max_version


if __name__ == '__main__':

    # check latest tag is a valid version (for now, other tags are not allowed)
    latest_tag = subprocess.check_output(['git', 'describe', '--tags', '--abbrev=0'], text=True).strip()
    print(f'Latest tag:           {latest_tag}')
    tag_version = latest_tag.lstrip('v')
    if not VERSION_REGEX.match(tag_version):
        error(f'tag {latest_tag!r} is not a valid version')
    print(f'Latest version:       {tag_version}')

    # check that the package version matches the tag version
    pkg_version = subprocess.check_output(['hatch', 'version'], text=True).strip()
    if not VERSION_REGEX.match(pkg_version):
        error(f'package version string {pkg_version_str!r} is not a valid version')
    if pkg_version != tag_version:
        print(f'WARNING: mismatch between tag version ({tag_version}) and package version ({pkg_version}) -- remember to update tag')
        # error(f'mismatch between tag version ({tag_version}) and package version ({pkg_version})')

    # check the latest built version
    built_version = get_latest_built_version()
    if built_version:
        print(f'Latest built version: {built_version}')
    if (not built_version) or (built_version != pkg_version):
        print(f'WARNING: latest version has not been built -- remember to build & publish v{pkg_version}')

    # check the CHANGELOG has an URL for the latest version
    url_regex = re.compile(r'\[' + str(tag_version) + r'\]:\s*\w+')
    has_url = False
    with open(CHANGELOG) as f:
        for line in f:
            if url_regex.search(line):
                has_url = True
                break
    if has_url:
        print('Changelog:            OK')
    else:
        error(f'{CHANGELOG} may not be up-to-date, does not contain a line like:\n\t[{tag_version}]: https://...')
