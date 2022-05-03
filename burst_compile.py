#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from __future__ import annotations

import argparse
import copy
import logging
import os
import pathlib
import subprocess
import sys
from typing import Dict, List, Optional
from buildtools import common
from buildtools.datatypes import BurstCompileAction, BurstTarget, PathLike, Config

logger = logging.getLogger(__name__)


def run(config: Config, args: argparse.Namespace):
    burst_compile_all(config, args.print_help)


def build_parser(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--print-help",
        help="Print burst compiler help and exit",
        dest="print_help",
        action="store_true",
        default=False,
    )


def get_targets(config: BurstCompileAction):
    targets: Dict[str, BurstTarget] = {}
    for t in config.targets:
        target = copy.deepcopy(t)
        platform = target.platform
        if platform is None:
            raise ValueError("Target does not contain platform")
        targets[platform] = target

    # sort out includes
    final: Dict[str, BurstTarget] = {}
    for platform, target in targets.items():
        include = target.include
        if include is None:
            final[platform] = target
            continue

        target.include = None
        parent = targets.get(include, None)

        if parent is None:
            logger.warning(
                "Target '%s' includes non-existent target '%s'", platform, include
            )
            final[platform] = target
            continue

        new_target = copy.deepcopy(parent)
        new_target.update(target)
        final[platform] = new_target

    return final


def add_option(
    args: List[str],
    target: BurstTarget,
    name: str,
    config: Config,
    if_false: Optional[str] = None,
) -> None:
    option = getattr(target, name, None)
    if option is None:
        return

    option = common.resolve(option, config)

    if option:
        args.append(f"--{name.replace('_', '-')}")
    elif if_false is not None:
        args.append(if_false)


def add_value_option(
    args: List[str],
    target: BurstTarget,
    name: str,
    config: Config,
    is_path: bool = False,
) -> None:
    option = getattr(target, name, None)
    if option is None:
        return

    if is_path:
        option = common.resolve_path(option, config)
    else:
        option = common.resolve(option, config)

    args.append(f"--{name.replace('_', '-')}={option}")


def add_path_list_option(
    args: List[str], target: BurstTarget, name: str, option_name: str, config: Config
) -> None:
    paths: Optional[List[pathlib.Path]] = getattr(target, name, None)
    if paths is None:
        return

    path: pathlib.Path
    for path in paths:
        path = common.resolve_path(path, config)
        if "*" in str(path):
            for p in config.glob(path):
                args.append(f"--{option_name}={p}")
        else:
            args.append(f"--{option_name}={path}")


def burst_compile(
    bcl: PathLike, target: BurstTarget, config: Config, debug: bool = False
) -> None:
    args: List[str] = [str(bcl)]

    add_value_option(args, target, "platform", config)
    add_option(args, target, "safety_checks", config, "--disable-safety-checks")
    add_option(args, target, "fast_math", config)
    add_option(args, target, "enable_guard", config)
    add_value_option(args, target, "float_precision", config)
    add_value_option(args, target, "float_mode", config)
    add_value_option(args, target, "debug", config)
    add_option(args, target, "debug_mode", config)
    add_value_option(args, target, "output", config, is_path=True)
    add_option(args, target, "verbose", config)
    add_option(args, target, "log_timings", config)
    add_value_option(args, target, "key_folder", config, is_path=True)
    add_value_option(args, target, "include_root_assembly_references", config)

    if target.targets:
        for t in target.targets:
            args.append(f"--target={common.resolve(t, config)}")

    add_path_list_option(args, target, "root_assemblies", "root-assembly", config)
    add_path_list_option(args, target, "assembly_folders", "assembly-folder", config)

    logger.debug("Running burst with args: %s", args)

    if debug:
        env = os.environ.copy()
        env["UNITY_BURST_DEBUG"] = ""
    else:
        env = os.environ  # type: ignore

    try:
        subprocess.check_call(args, env=env)
    except Exception:
        logger.exception("Burst compile failed. Command line: %s", args)
        raise


def burst_compile_all(config: Config, print_help: bool = False) -> None:
    compile_config = config.burst_compile
    bcl = compile_config.bcl
    bcl = common.resolve_path(bcl, config)

    if print_help:
        subprocess.call([bcl, "--help"])
        sys.exit(0)

    debug = compile_config.debug

    targets = get_targets(compile_config)
    for platform, target in targets.items():
        try:
            burst_compile(bcl, target, config, debug)
        except Exception:
            logger.exception("Exception compiling target '%s'", platform)


def main():
    parser = argparse.ArgumentParser(description="Burst compile utility")
    common.add_config_option(parser)
    build_parser(parser)

    args = parser.parse_args()

    config = common.load_config(args.config)

    with common.chdir(config.root):
        run(config, args)


if __name__ == "__main__":
    main()
