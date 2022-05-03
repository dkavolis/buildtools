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
import os
import pathlib
import shutil
import subprocess
from typing import Dict, Iterable

from buildtools import common
from buildtools.datatypes import FileCopy, PathLike, Config


def main():
    parser = argparse.ArgumentParser(description="Postbuild utility")
    common.add_config_option(parser)
    build_parser(parser)

    args = parser.parse_args()

    config = common.load_config(args.config)

    with common.chdir(config.root):
        run(config, args)


def run(config: Config, args: argparse.Namespace):
    post_build(config, args.config_name, args.target_path)


def update_config(config: Config, configuration_name: str, target_path: PathLike):
    config.variables["ConfigurationName"] = configuration_name
    config.variables.update(split_target_path(target_path))

    events = config.post_build

    override = f"[{configuration_name}]"
    if override in events:
        events.update(events[override])
    override = f"[{config.variables['TargetName']}]"
    if override in events:
        events.update(events[override])


def post_build(config: Config, configuration_name: str, target_path: PathLike) -> None:
    update_config(config, configuration_name, target_path)
    events = config.post_build

    if events.pdb2mdb is not None:
        pdb2mdb(
            common.resolve_path(events.pdb2mdb, config),
            str(config.variables["TargetPath"]),
        )

    if events.clean:
        clean(events.clean, config)

    if events.install:
        install(events.install, config)


def build_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-c",
        "--configuration",
        help="Name of the configuration",
        dest="config_name",
        default="__NoName__",
    )
    parser.add_argument(
        "-t", "--target", required=True, help="Target path", dest="target_path"
    )


def split_target_path(target: PathLike) -> Dict[str, str]:
    target_path = pathlib.Path(target).absolute()
    target_filename = target_path.name
    target_dir = target_path.parent
    target_name = target_path.stem
    target_ext = target_path.suffix
    return dict(
        TargetPath=str(target_path),
        TargetFileName=target_filename,
        TargetDir=str(target_dir),
        TargetName=target_name,
        TargetExt=target_ext,
    )


def pdb2mdb(path: PathLike, target: PathLike) -> None:
    print(f"Calling '{path} {target}'")
    subprocess.call([path, target])


def clean(paths: Iterable[PathLike], config: Config):
    for path in paths:
        path = common.resolve_path(str(path), config)
        if path.exists():
            if path.is_dir():
                print(f"Removing directory {path!s}")
                shutil.rmtree(path)
            else:
                print(f"Removing file {path!s}")
                os.remove(path)


def install(mapping: Iterable[FileCopy], config: Config):
    for item in mapping:
        src = common.resolve(item.source, config)
        dst = common.resolve_path(item.destination, config)

        for path in config.glob(src):
            if path.is_dir():
                print(f"Copying tree {path!s} -> {dst!s}")
                shutil.copytree(path, dst)
            else:
                print(f"Copying file {path!s} -> {dst!s}")
                shutil.copy(path, dst)


if __name__ == "__main__":
    main()
