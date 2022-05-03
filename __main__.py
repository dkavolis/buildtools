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


import argparse
import json
import pprint
from buildtools import common, package, postbuild, replace, burst_compile
from buildtools.datatypes import JSONEncoder


def main():
    parser = argparse.ArgumentParser("C# build helpers", add_help=False)

    common.add_config_option(parser)
    subparsers = parser.add_subparsers(description="Available helpers", dest="command")

    replacer = subparsers.add_parser(
        "replace", description="Regex replacement utility", parents=[parser]
    )
    packager = subparsers.add_parser(
        "package", description="Archive utility", parents=[parser]
    )
    post = subparsers.add_parser(
        "postbuild", description="Post build utility", parents=[parser]
    )
    burst_compiler = subparsers.add_parser(
        "burst_compile", description="Burst compiler utility", parents=[parser]
    )

    # args.command always contains None so add defaults
    replace.build_parser(replacer)
    replacer.set_defaults(run=replace.run)

    package.build_parser(packager)
    packager.set_defaults(run=package.run)

    postbuild.build_parser(post)
    post.set_defaults(run=postbuild.run)

    burst_compile.build_parser(burst_compiler)
    burst_compiler.set_defaults(run=burst_compile.run)

    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="Display this help and exit",
        default=argparse.SUPPRESS,
    )
    parser.add_argument("--dump-config", action="store", default=0, nargs="?")

    args = parser.parse_args()

    config = common.load_config(args.config)

    if args.dump_config != 0:
        if args.dump_config:
            with open(args.dump_config, "w") as file:
                json.dump(config, file, cls=JSONEncoder, indent=4)
        else:
            pprint.pprint(config)
        return

    with common.chdir(config.root):
        if hasattr(args, "run"):
            args.run(config, args)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
