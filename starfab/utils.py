import os
import io
import sys
import typing
import shutil
import tempfile
import importlib
import subprocess
from scdatatools.engine.textures.converter import (
    convert_buffer,
    ConverterUtility,
    ConversionError,
)

from starfab import get_starfab
from starfab.gui import qtw, qtc
from starfab.settings import get_texconv, get_compressonatorcli


def reload_starfab_modules(module=""):
    # build up the list of modules first, otherwise sys.modules will change while you iterate through it
    loaded_modules = [
        m
        for n, m in sys.modules.items()
        if (n.startswith(module) if module else n.startswith("starfab.gui"))
    ]
    for module in loaded_modules:
        importlib.reload(module)


def show_file_in_filemanager(path):
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class ImageConverter:
    def __init__(self):
        self.compressonatorcli = get_compressonatorcli()
        self.texconv = get_texconv()
        self.converter = (
            ConverterUtility.texconv
            if self.texconv
            else ConverterUtility.compressonator
        )

    @property
    def converter_bin(self):
        return (
            self.texconv
            if self.converter == ConverterUtility.texconv
            else self.compressonatorcli
        )

    def _check_bin(self):
        if not self.converter:
            qtw.QMessageBox.information(
                None,
                "Image Converter",
                f"Missing a DDS converter. If you're on Mac/Linux use compressonatorcli. You can install it from "
                f"<a href='https://gpuopen.com/compressonator/'>https://www.steamgriddb.com/manager</a>. If you're on"
                f"windows you can use texconv, download it from "
                f"<a href='https://github.com/microsoft/DirectXTex/releases'>"
                f"https://github.com/microsoft/DirectXTex/releases</a>. Ensure whichever tool is in your system PATH.",
            )
            raise RuntimeError(f"Cannot find compressonatorcli")

    def convert_buffer(self, inbuf, in_format, out_format="tif") -> bytes:
        """Converts a buffer `inbuf` to the output format `out_format`"""
        self._check_bin()

        try:
            buf, msg = convert_buffer(
                inbuf,
                in_format=in_format,
                out_format=out_format,
                converter=self.converter,
                converter_bin=self.converter_bin,
            )
        except ConversionError as e:
            raise RuntimeError(f"Failed to convert buffer: {e}")

        return buf


image_converter = ImageConverter()
