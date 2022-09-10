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

import contextlib
import logging
import json
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Mapping, Optional, TypeVar
import pathlib
from buildtools.datatypes import PathLike, Config

VAR_PATTERN = re.compile(r"\$\(([\w\_\-\:\d]+)\)")
SILENT_VARS = {
    "Configuration",
}

K = TypeVar("K")
V = TypeVar("V")

logger = logging.getLogger(__name__)


def recursive_update(left: Dict[K, V], right: Dict[K, V]) -> None:
    for k, v in right.items():
        lv = left.get(k, None)  # type: ignore
        if isinstance(lv, dict):
            recursive_update(lv, v)  # type: ignore
        else:
            left[k] = v


def load_config(filename: PathLike) -> Config:
    filename = pathlib.Path(filename).absolute()
    with open(filename) as file:
        data: Dict[str, Any] = json.load(file)

    user_file = filename.with_suffix(filename.suffix + ".user")
    if user_file.exists():
        with open(user_file) as file:
            user_data = json.load(file)

        recursive_update(data, user_data)

    file_dir = filename.parent
    if "root" in data:
        root = data["root"]
        if not os.path.isabs(root):
            root = file_dir / root
    else:
        root = file_dir
    data["root"] = root

    if "build_props" in data:
        data["build_props"] = root / data["build_props"]

    data.setdefault("variables", {}).update(
        load_variables(root, data.get("build_props", None))
    )

    for name, value in data["variables"].items():
        if not isinstance(value, str):
            continue

        data["variables"][name] = replace_variables(value, data["variables"])

    return Config(**data)


def find_solution_dir(root: Optional[PathLike] = None) -> pathlib.Path:
    if root is None:
        root = pathlib.Path.cwd()
    else:
        root = pathlib.Path(root)

    counter = 0
    while not root.glob("*.sln"):
        root = root.parent
        if counter > 20:
            raise FileNotFoundError("Could not find .sln file")
        else:
            counter += 1
    return root


def get_solution_vars(
    root: Optional[PathLike] = None,
) -> Dict[str, str]:
    sol_dir = find_solution_dir(root)
    data: Dict[str, str] = {"SolutionDir": str(sol_dir)}
    sol_files = list(sol_dir.glob("*.sln"))
    if sol_files:
        sol_file = sol_files[0]
        data["SolutionFileName"] = sol_file.name
        data["SolutionName"] = sol_file.stem
    return data


def load_build_props(filename: PathLike) -> Dict[str, str]:
    filename = pathlib.Path(filename)
    tree = ET.parse(filename)
    root = tree.getroot()
    data: Dict[str, str] = {}

    for section in root:
        if section.tag == "Import" and "Project" in section.attrib:
            project = pathlib.Path(section.attrib["Project"])
            if not project.is_absolute():
                project = filename.parent / project
            if project.exists():
                data.update(load_build_props(project))
        elif section.tag == "PropertyGroup":
            for item in section:
                if item.text is None:
                    continue
                data[item.tag] = item.text

    return data


def load_variables(
    root: Optional[PathLike] = None, filename: Optional[PathLike] = None
) -> Dict[str, str]:
    data = get_solution_vars(root)
    if filename is not None:
        data.update(load_build_props(filename))
    for key, value in data.items():
        data[key] = replace_variables(value, data)
    return data


def replace_variables(string: str, var_map: Mapping[str, Any]) -> str:
    def _re_sub(matchobj: re.Match[str]):
        identifier = matchobj.group(1)
        value: Any = None
        if identifier.startswith("env:"):
            value = os.environ.get(identifier[4:], None)
        else:
            value = var_map.get(identifier, None)

        if value is None:
            if identifier not in SILENT_VARS:
                logger.warn("Variable %s not found!", identifier)
            return ""

        return str(value)

    newstr, subs = re.subn(VAR_PATTERN, _re_sub, string)
    while subs > 0:
        newstr, subs = re.subn(VAR_PATTERN, _re_sub, newstr)
    return newstr


def resolve(string: str, config: Config) -> str:
    return replace_variables(string, config.variables)


def resolve_path(string: PathLike, config: Config) -> pathlib.Path:
    return pathlib.Path(resolve(str(string), config))


@contextlib.contextmanager
def chdir(dirname: PathLike):
    old = os.getcwd()
    try:
        os.chdir(dirname)
        yield
    finally:
        os.chdir(old)


def add_config_option(parser: argparse.ArgumentParser):
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
