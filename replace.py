#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Author:               Daumantas Kavolis <dkavolis>
Date:                 05-Apr-2019
Filename:             replace.py
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
import glob
import re
from buildtools import common


def run(config, args):
    replace(config)


def build_parser(parser):
    pass


def replace(config):
    for glob_pattern, subs in config.get("replace", {}).get("regex", {}).items():
        files = common.glob(common.resolve_path(glob_pattern, config))

        for filename in files:
            replace_in_file(filename, subs, config)

    for src, dst in config.get("replace", {}).get("template_files", {}).items():
        src = common.resolve_path(src, config)
        dst = common.resolve_path(dst, config)

        replace_in_file_all(src, dst, config)


def replace_in_file_all(src, dst, config):
    print(f"Updating {src!r} -> {dst!r}")
    with open(src, "r") as file:
        contents = file.read()

    contents = common.resolve(contents, config)

    with open(dst, "w") as file:
        file.write(contents)


def replace_in_file(filename, replacements, config):
    print(f"Updating {filename!r}")
    with open(filename, "r") as file:
        contents = file.read()
    for pattern, replacement in replacements.items():
        pattern = common.resolve(pattern, config)
        replacement = common.resolve(replacement, config)

        def replace(matchobj):
            if (len(matchobj.groups())) > 0:
                string = matchobj[0]
                start_, end_ = matchobj.start(), matchobj.end()
                start, end = matchobj.start(1), matchobj.end(1)
                new = string[: start - start_] + replacement
                if end != end_:
                    new = new + string[end - end_ :]
                return sub_groups(new, (matchobj[0],) + matchobj.groups())
            return sub_groups(replacement, (matchobj[0],) + matchobj.groups())

        contents = re.sub(pattern, replace, contents)
    with open(filename, "w") as file:
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
