#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Author:               Daumantas Kavolis <dkavolis>
Date:                 05-Apr-2019
Filename:             replace.py
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
import glob
import re
from buildtools import common


def run(config, args):
    replace(config)


def build_parser(parser):
    pass


def replace(config):
    for patterns in config.get("replace", {}).get("regex", []):
        files = common.glob(common.resolve_path(patterns["pattern"], config))

        for filename in files:
            replace_in_file(filename, patterns["substitutions"], config)

    for files in config.get("replace", {}).get("template_files", []):
        src = common.resolve_path(files["source"], config)
        dst = common.resolve_path(files["destination"], config)

        replace_in_file_all(src, dst, config)


def replace_in_file_all(src, dst, config):
    print(f"Updating {src!r} -> {dst!r}")
    with open(src, "r", newline="") as file:
        contents = file.read()

    contents = common.resolve(contents, config)

    with open(dst, "w", newline="") as file:
        file.write(contents)


def replace_in_file(filename, replacements, config):
    print(f"Updating {filename!r}")
    with open(filename, "r", newline="") as file:
        contents = file.read()
    for replacement in replacements:
        pattern = common.resolve(replacement["search"], config)
        replacement = common.resolve(replacement["replace"], config)
        contents = re.sub(pattern, replacement, contents)
    with open(filename, "w", newline="") as file:
        file.write(contents)


def main():
    parser = argparse.ArgumentParser(description="Regex replacement utility")
    common.add_config_option(parser)
    build_parser(parser)

    args = parser.parse_args()

    config = common.load_config(args.config)
    with common.chdir(config["root"]):
        replace(config)


GROUP = re.compile(r"(?:\\g<(\d+)>|\\(\d+))")


def sub_groups(string, groups):
    def _replace_group(matchobj):
        index = int(matchobj[1])
        if index < len(groups):
            return str(groups[index])
        return matchobj[0]

    return re.sub(GROUP, _replace_group, string)


if __name__ == "__main__":
    main()
