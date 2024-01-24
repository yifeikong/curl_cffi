import sys
import os
import platform
import shutil
import struct
from pathlib import Path
from setuptools import setup
from urllib.request import urlretrieve
from wheel.bdist_wheel import bdist_wheel
from distutils.command.build import build


__version__ = "0.6.0b8"


class bdist_wheel_abi3(bdist_wheel):
    def run(self):
        super().run()

        impl_tag, abi_tag, plat_tag = self.get_tag()
        archive_basename = f"{self.wheel_dist_name}-{impl_tag}-{abi_tag}-{plat_tag}"

        wheel_path = os.path.join(self.dist_dir, archive_basename + ".whl")

        os.system(f'python3 -m auditwheel repair -w "{self.dist_dir}" "{wheel_path}"')
        os.remove(wheel_path)

    def get_tag(self):
        python, abi, plat = super().get_tag()

        if python.startswith("cp"):
            # on CPython, our wheels are abi3 and compatible back to 3.7
            return "cp37", "abi3", plat

        return python, abi, plat


def abs_machine():
    machine = platform.machine()

    pointer_bits = struct.calcsize("P") * 8
    if pointer_bits not in (32, 64):
        raise Exception("Unsupported pointer size")

    is_64 = pointer_bits == 64

    # x86 based archs
    if machine in ('AMD64', 'x86_64', 'i686'):
        return "x86_64" if is_64 else "i686"
    # arm based archs
    elif machine in ('aarch64', 'arm64', 'armv6l', 'armv7l'):
        return "aarch64" if is_64 else "arm"
    else:
        raise Exception("Unsupported processor")


def download_so():
    system = platform.system()
    machine = abs_machine()

    if system == "Windows":
        sysname = "win32"
        so_name = "libcurl.dll"

        if machine == "x86_64":
            libdir = "./lib32"
        elif machine == "i686":
            libdir = "./lib64"
        else:
            so_name = "SKIP"

    elif system == "Darwin":
        sysname = "macos"
        so_name = "libcurl-impersonate-chrome.4.dylib"

        if machine == "x86_64":
            libdir = "/Users/runner/work/_temp/install/lib"
        else:
            so_name = "SKIP"

    else:
        sysname = "linux-gnu"
        so_name = "libcurl-impersonate-chrome.so"

        if machine in ("x86_64", "arm", "aarch64"):
            libdir = f"./libcurl_{machine}"
        else:
            so_name = "SKIP"

    if so_name == "SKIP":
        print(".so file for platform is not available on github.")
        return

    if (Path(libdir) / so_name).exists():
        print(".so files alreay downloaded.")
        return

    file = "libcurl-impersonate.tar.gz"
    url = (
        f"https://github.com/yifeikong/curl-impersonate/releases/download/"
        f"v{__version__}/libcurl-impersonate-v{__version__}"
        f".{machine}-{sysname}.tar.gz"
    )

    print(f"Downloading libcurl-impersonate-chrome from {url}...")
    urlretrieve(url, file)

    print("Unpacking downloaded files...")
    os.makedirs(libdir, exist_ok=True)
    shutil.unpack_archive(file, libdir)
    print(f"Unpacked downloaded files into {libdir}.")

    if system == "Windows":
        shutil.copy2(f"{libdir}/libcurl.dll", "curl_cffi")


class my_build(build):
    def run(self):
        download_so()
        super().run()


# this option is only valid in setup.py
kwargs = {"cffi_modules": ["scripts/build.py:ffibuilder"]}
if len(sys.argv) > 1 and sys.argv[1] != 'bdist_wheel':
    kwargs = {}

setup(
    cmdclass={
        "bdist_wheel": bdist_wheel_abi3,  # type: ignore
        "build": my_build,  # type: ignore
    },
    **kwargs,
)
