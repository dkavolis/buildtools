#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Author:               Daumantas Kavolis <dkavolis>
Date:                 05-Apr-2019
Filename:             postbuild.py
Last Modified By:     Daumantas Kavolis
Last Modified Time:   25-Apr-2019
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
import os
import shutil
import subprocess
from buildtools import common
from typing import Dict


def main():
    parser = argparse.ArgumentParser(description="Postbuild utility")
    common.add_config_option(parser)
    build_parser(parser)

    args = parser.parse_args()

    config = common.load_config(args.config)

    with common.chdir(config["root"]):
        run(config, args)


def run(config, args):
    post_build(config, args.config_name, args.target_path)


def update_config(config, configuration_name, target_path):
    config["variables"]["ConfigurationName"] = configuration_name
    config["variables"].update(
        split_target_path(config["variables"]["SolutionDir"], target_path)
    )

    events = config["post_build"]

    override = f"[{configuration_name}]"
    if override in events:
        events.update(events[override])
    override = f"[{config['variables']['TargetName']}]"
    if override in events:
        events.update(events[override])


def post_build(config, configuration_name, target_path):
    update_config(config, configuration_name, target_path)
    events = config["post_build"]

    if "pdb2mdb" in events:
        pdb2mdb(
            common.resolve_path(events["pdb2mdb"], config),
            config["variables"]["TargetPath"],
        )

    if "clean" in events:
        clean(events["clean"], config)

    if "install" in events:
        install(events["install"], config)


def build_parser(parser):
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


def split_target_path(solution_dir: str, target: str) -> Dict[str, str]:
    target_path = os.path.abspath(target)
    target_filename = os.path.basename(target_path)
    target_dir = os.path.dirname(target_path) + os.path.sep
    target_name, target_ext = os.path.splitext(target_filename)
    return dict(
        TargetPath=target_path,
        TargetFileName=target_filename,
        TargetDir=target_dir,
        TargetName=target_name,
        TargetExt=target_ext,
    )


def pdb2mdb(path, target):
    print(f"Calling '{path} {target}'")
    subprocess.call([path, target])


def clean(paths, config):
    for path in paths:
        path = common.resolve_path(path, config)
        if os.path.exists(path):
            if os.path.isdir(path):
                print(f"Removing directory {path!r}")
                shutil.rmtree(path)
            else:
                print(f"Removing file {path!r}")
                os.remove(path)


def install(mapping, config):
    for item in mapping:
        src = common.resolve_path(item["source"], config)
        dst = common.resolve_path(item["destination"], config)

        src = common.glob(src)

        for path in src:
            if os.path.isdir(path):
                print(f"Copying tree {path!r} -> {dst!r}")
                shutil.copytree(path, dst)
            else:
                print(f"Copying file {path!r} -> {dst!r}")
                shutil.copy(path, dst)


if __name__ == "__main__":
    main()
