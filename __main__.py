#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Author:               Daumantas Kavolis <dkavolis>
Date:                 05-Apr-2019
Filename:             __main__.py
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


import argparse
from buildtools import common, package, postbuild, replace


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

    # args.command always contains None so add defaults
    replace.build_parser(replacer)
    replacer.set_defaults(run=replace.run)

    package.build_parser(packager)
    packager.set_defaults(run=package.run)

    postbuild.build_parser(post)
    post.set_defaults(run=postbuild.run)

    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="Display this help and exit",
        default=argparse.SUPPRESS,
    )

    args = parser.parse_args()

    config = common.load_config(args.config)

    with common.chdir(config["root"]):
        if hasattr(args, "run"):
            args.run(config, args)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
