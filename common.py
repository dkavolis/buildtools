#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Author:               Daumantas Kavolis <dkavolis>
Date:                 05-Apr-2019
Filename:             common.py
Last Modified By:     Daumantas Kavolis
Last Modified Time:   24-Nov-2019
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

import contextlib
import glob as _glob
import json
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Mapping

VAR_PATTERN = re.compile(r"\$\(([\w\_\-\d]+)\)")


def load_config(filename: str) -> Dict[str, Any]:
    with open(filename) as file:
        data = json.load(file)
    file_dir = os.path.abspath(os.path.dirname(filename))
    if "root" in data:
        root = data["root"]
        if not os.path.isabs(root):
            root = os.path.abspath(os.path.join(file_dir, root))
    else:
        root = file_dir
    data["root"] = root

    if "build_props" in data:
        data["build_props"] = os.path.join(root, data["build_props"])

    data.setdefault("variables", {}).update(
        load_variables(root, data.get("build_props", None))
    )

    for name, value in data["variables"].items():
        data["variables"][name] = replace_variables(value, data["variables"])

    return data


def find_solution_dir(root: str = None) -> str:
    if root is None:
        root = os.getcwd()
    os.chdir(root)
    counter = 0
    try:
        while not _glob.glob("*.sln"):
            os.chdir(os.getcwd() + "/..")
            if counter > 20:
                raise FileNotFoundError("Could not find .sln file")
            else:
                counter += 1
        return os.getcwd() + os.path.sep
    finally:
        os.chdir(root)


def get_solution_vars(root: str = None) -> Dict[str, str]:
    sol_dir = find_solution_dir(root)
    data = {"SolutionDir": sol_dir}
    sol_files = _glob.glob(os.path.join(sol_dir, "*.sln"))
    if sol_files:
        sol_file = os.path.basename(sol_files[0])
        data["SolutionFileName"] = sol_file
        data["SolutionName"] = os.path.splitext(sol_file)[0]
    return data


def load_build_props(filename: str) -> Dict[str, str]:
    tree = ET.parse(filename)
    root = tree.getroot()
    data = {}
    for item in root[0]:
        if item.text is None:
            continue
        data[item.tag] = item.text
    return data


def load_variables(root: str = None, filename: str = None) -> Dict[str, str]:
    data = get_solution_vars(root)
    if filename is not None:
        data.update(load_build_props(filename))
    for key, value in data.items():
        data[key] = replace_variables(value, data)
    return data


def replace_variables(string: str, var_map: Mapping[str, str]) -> str:
    if not isinstance(string, str):
        return string

    def _re_sub(matchobj):
        if matchobj.group(1) in var_map:
            return str(var_map[matchobj.group(1)])
        return ""

    newstr, subs = re.subn(VAR_PATTERN, _re_sub, string)
    while subs > 0:
        newstr, subs = re.subn(VAR_PATTERN, _re_sub, newstr)
    return newstr


def resolve(string: str, config: Dict[str, Any]) -> str:
    return replace_variables(string, config["variables"])


def resolve_path(string: str, config: Dict[str, Any]) -> str:
    path = os.path.normpath(resolve(string, config))
    if isdir(string) or isdir(path):
        return os.path.join(path, "")
    return path


def isdir(path: str) -> bool:
    return os.path.isdir(path) or any(path.endswith(char) for char in "\\/")


@contextlib.contextmanager
def chdir(dirname):
    old = os.getcwd()
    try:
        os.chdir(dirname)
        yield
    finally:
        os.chdir(old)


def glob(pattern):
    return _glob.glob(pattern, recursive=True)


def add_config_option(parser):
    parser.add_argument(
        "-f",
        "--file",
        help="Path to configuration file",
        dest="config",
        default="config.json",
    )


def main():
    config = load_config("config.json")
    print("config: ", config)


if __name__ == "__main__":
    main()
