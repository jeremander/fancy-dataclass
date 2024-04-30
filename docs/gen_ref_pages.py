"""Generate the code reference pages.

See: https://mkdocstrings.github.io/recipes/"""


from pathlib import Path

import mkdocs_gen_files


nav = mkdocs_gen_files.Nav()

PKG_NAME = 'fancy_dataclass'
PKG_DIR = Path(PKG_NAME)
REF_DIR = Path('reference')

REF_MODULES = ['cli', 'config', 'func', 'dict', 'json', 'mixin', 'serialize', 'sql', 'subprocess', 'toml', 'utils']

for mod_name in REF_MODULES:
    path = PKG_DIR / f'{mod_name}.py'
    module_path = path.relative_to(PKG_DIR).with_suffix('')
    doc_path = path.relative_to(PKG_DIR).with_suffix('.md')
    full_doc_path = REF_DIR / doc_path
    parts = tuple(module_path.parts)
    if parts[-1] == '__init__':
        # parts = parts[:-1]
        continue
    elif parts[-1] == '__main__':
        continue
    nav[parts] = doc_path.as_posix()
    with mkdocs_gen_files.open(full_doc_path, 'w') as f:
        identifier = '.'.join(parts)
        print(f'::: {PKG_NAME}.{identifier}', file = f)
    mkdocs_gen_files.set_edit_path(full_doc_path, path)

with mkdocs_gen_files.open(REF_DIR / 'SUMMARY.md', 'w') as nav_file:
    nav_file.writelines(nav.build_literate_nav())
