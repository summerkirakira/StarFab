import urllib.request
from sys import platform
from pathlib import Path
from subprocess import check_output


DIST_DIR = (Path(__file__).parent.parent / 'dist').absolute()
DIST_DIR.mkdir(exist_ok=True)

INCLUDED_PLUGINS = [
]


PLAT_EXCLUDES = {
    'win32': ['pyobjc']
}


def run():
    reqs = check_output('poetry export --without-hashes', shell=True, encoding='utf-8').split('\n')
    if 'Warning' in reqs[0]:
        reqs = reqs[1:]  # skip the warning
    reqs.extend(INCLUDED_PLUGINS)
    reqs = '\n'.join(r for r in reqs if not any(e in r for e in PLAT_EXCLUDES.get(platform, [])))

    with open(DIST_DIR / 'requirements.txt', 'w') as r:
        r.write(reqs)

    if platform == 'win32':
        print('Fetching latest texconv')
        CONTRIB_DIR = (DIST_DIR.parent / 'scdv' / 'contrib')
        urllib.request.urlretrieve('https://github.com/Microsoft/DirectXTex/releases/latest/download/texconv.exe',
                                   str(CONTRIB_DIR / 'texconv.exe'))


if __name__ == "__main__":
    run()
