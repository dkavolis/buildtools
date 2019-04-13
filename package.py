#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Author:               Daumantas Kavolis <dkavolis>
Date:                 05-Apr-2019
Filename:             package.py
Last Modified By:     Daumantas Kavolis
Last Modified Time:   13-Apr-2019
------------------
Copyright (c) 2019 Daumantas Kavolis

   buildtools is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   buildtools is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with buildtools.  If not, see <http: //www.gnu.org/licenses/>.

"""


from __future__ import annotations

import argparse
import collections
import glob
import os
import zipfile
from buildtools import common


def run(config, args):
    zipfiles = build_file_list(config)
    package(config, zipfiles)


class ZipFiles(object):
    def __init__(self, config):
        self.files = collections.defaultdict(lambda: set())
        self.config = config

    def __len__(self):
        return len(self.files)

    def __iter__(self):
        for src, files in self.files.items():
            for dst in files:
                yield (src, dst)

    def __getitem__(self, key):
        return self.files[key]

    def __setitem(self, key, value):
        self.files[key] = value

    def _glob(self, pattern):
        pattern = common.resolve_path(pattern, self.config)
        return common.glob(pattern)

    def append(self, name, dst=None):
        if common.isdir(name):
            for _name in glob.glob(name + "**/*", recursive=True):
                self.append(_name, dst)
        if dst is None:
            dst = name
        elif common.isdir(dst):
            dst = os.path.join(dst, os.path.basename(name))
        self.files[name].add(dst)

    def remove(self, name):
        if common.isdir(name):
            for _name in glob.glob(name + "**/*", recursive=True):
                self.remove(_name)
        if name in self.files:
            del self.files[name]

    def include(self, pattern, destination=None):
        for file in self._glob(pattern):
            self.append(file, destination)

    def exclude(self, pattern):
        for file in self._glob(pattern):
            self.remove(file)

    def map(self, src, dst):
        dst = common.resolve_path(dst, self.config)

        for file in self._glob(src):
            self.append(file, dst)


def build_parser(parser):
    pass


def main():
    parser = argparse.ArgumentParser(description="Archive utility")
    common.add_config_option(parser)
    build_parser(parser)

    args = parser.parse_args()

    config = common.load_config(args.config)

    with common.chdir(config["root"]):
        run(config, args)


def package(config, file_list):
    package = config["package"]

    compression = getattr(
        zipfile, f"ZIP_{package.get('compression', 'DEFLATED').upper()}"
    )
    name = common.resolve(package["filename"], config)
    outdir = common.resolve_path(package.get("output_dir", ""), config)
    archive = os.path.join(outdir, name)

    print(f"Packaging {archive!r}")

    with zipfile.ZipFile(archive, "w", compression=compression) as zip:
        for src, dst in file_list:
            print(f"Writing {src!r} -> {dst!r}")
            zip.write(src, dst)


def build_file_list(config):
    package = config["package"]

    zipfiles = ZipFiles(config)

    for pattern in package.get("include", []):
        zipfiles.include(pattern)

    for pattern in package.get("exclude", []):
        zipfiles.exclude(pattern)

    for src, dst in package.get("map", {}).items():
        zipfiles.map(src, dst)

    def process_dependency(name, data):
        src = common.resolve_path(name, config)
        dst = common.resolve_path(data["destination"], config)

        for pattern in data.get("include", []):
            zipfiles.include(os.path.join(src, pattern), dst)

        for pattern in data.get("exclude", []):
            zipfiles.exclude(os.path.join(src, pattern))

        for _src, _dst in data.get("map", {}).items():
            _src = common.resolve_path(_src, config)
            if not os.path.isabs(_src):
                _src = os.path.join(src, _src)
            zipfiles.map(_src, _dst)

    for key, value in package.get("dependencies", {}).items():
        process_dependency(key, value)

    return zipfiles


if __name__ == "__main__":
    main()
