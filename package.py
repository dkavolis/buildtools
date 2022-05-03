#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Copyright (c) 2022 Daumantas Kavolis

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
import pathlib
from typing import Dict, Iterable, Optional, Set, Tuple
import zipfile
from buildtools import common
from buildtools.datatypes import Config, Dependency, PathLike


def run(config: Config, args: argparse.Namespace):
    zipfiles = build_file_list(config)
    package(config, zipfiles, args.verbose > 0)


class ZipFiles(object):
    def __init__(self, config: Config):
        self.files: Dict[pathlib.Path, Set[pathlib.Path]] = collections.defaultdict(
            lambda: set()
        )
        self.config = config

    def __len__(self) -> int:
        return len(self.files)

    def items(self) -> Iterable[Tuple[pathlib.Path, pathlib.Path]]:
        for src, files in self.files.items():
            for dst in files:
                yield (src, dst)

    def __getitem__(self, key: PathLike) -> Set[pathlib.Path]:
        return self.files[pathlib.Path(key)]

    def __setitem__(self, key: PathLike, value: Set[PathLike]) -> None:
        self.files[pathlib.Path(key)] = {pathlib.Path(v) for v in value}

    def _glob(self, pattern: PathLike) -> Iterable[pathlib.Path]:
        pattern = common.resolve_path(pattern, self.config)
        return self.config.glob(pattern)

    def append(
        self,
        name: PathLike,
        dst: Optional[PathLike] = None,
        is_dir: bool = False,
    ) -> None:
        name = pathlib.Path(name)
        if name.is_dir():
            for _name in name.glob("**/*"):
                self.append(_name, dst)
        if dst is None:
            dst = name.relative_to(self.config.root)
        else:
            dst = pathlib.Path(dst)
            if dst.is_dir() or is_dir:
                dst = dst / name.name
        self.files[name].add(dst)

    def remove(self, name: PathLike) -> None:
        name = pathlib.Path(name)
        if name.is_dir():
            for _name in name.glob("**/*"):
                self.remove(_name)
        if name in self.files:
            del self.files[name]

    def include(
        self,
        pattern: PathLike,
        destination: Optional[PathLike] = None,
        is_dir: bool = False,
    ) -> None:
        for file in self._glob(pattern):
            self.append(file, destination, is_dir)

    def exclude(self, pattern: PathLike) -> None:
        for file in self._glob(pattern):
            self.remove(file)

    def map(self, src: PathLike, dst: PathLike) -> None:
        dst = common.resolve_path(dst, self.config)

        for file in self._glob(src):
            self.append(file, dst)


def build_parser(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-v", "--verbose", action="count", help="Increase output verbosity", default=0
    )


def main():
    parser = argparse.ArgumentParser(description="Archive utility")
    common.add_config_option(parser)
    build_parser(parser)

    args = parser.parse_args()

    config = common.load_config(args.config)

    with common.chdir(config.root):
        run(config, args)


def package(config: Config, file_list: ZipFiles, verbose: bool) -> None:
    package = config.package

    compression = package.compression_value
    name = common.resolve(package.filename, config)
    outdir = common.resolve_path(package.output_dir, config)
    archive = outdir / name

    if verbose:
        print(f"Packaging {archive!s}")

    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=compression) as zip:
        for src, dst in file_list.items():
            if verbose:
                print(f"Writing {src!s} -> {dst!s}")
            zip.write(src, dst)

    print(archive)


def build_file_list(config: Config) -> ZipFiles:
    package = config.package

    zipfiles = ZipFiles(config)

    for pattern in package.include:
        zipfiles.include(pattern)

    for pattern in package.exclude:
        zipfiles.exclude(pattern)

    for file_map in package.map:
        zipfiles.map(file_map.source, file_map.destination)

    def process_dependency(dep: Dependency):
        src = common.resolve_path(dep.path, config)
        dst = common.resolve_path(dep.destination, config)

        for pattern in dep.include:
            zipfiles.include(src / pattern, dst, True)

        for pattern in dep.exclude:
            zipfiles.exclude(src / pattern)

        for file_map in dep.map:
            _src = common.resolve_path(file_map.source, config)
            if not _src.is_absolute():
                _src = src / _src
            zipfiles.map(_src, file_map.destination)

    for dependency in package.dependencies:
        process_dependency(dependency)

    return zipfiles


if __name__ == "__main__":
    main()
