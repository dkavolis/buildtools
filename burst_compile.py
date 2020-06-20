#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 20-Jun-2020
@Filename:             burst_compile.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   20-Jun-2020
"""

import argparse
import copy
import logging
import os
import subprocess
import sys
from buildtools import common

logger = logging.getLogger(__name__)


def run(config, args):
    burst_compile_all(config, args.print_help)


def build_parser(parser):
    parser.add_argument(
        "--print-help",
        help="Print burst compiler help and exit",
        dest="print_help",
        action="store_true",
        default=False,
    )


def get_targets(config):
    targets = {}
    for t in config.get("targets", []):
        target = copy.deepcopy(t)
        platform = target.get("platform", None)
        if platform is None:
            raise ValueError("Target does not contain platform")
        targets[platform] = target

    # sort out includes
    final = {}
    for platform, target in targets.items():
        include = target.pop("include", None)
        if include is None:
            final[platform] = target
            continue

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


def add_option(args, target, name, config, if_false=None):
    option = target.get(name, None)
    if option is None:
        return

    option = common.resolve(option, config)

    if option:
        args.append(f"--{name.replace('_', '-')}")
    elif if_false is not None:
        args.append(if_false)


def add_value_option(args, target, name, config, is_path=False):
    option = target.get(name, None)
    if option is None:
        return

    if is_path:
        option = common.resolve_path(option, config)
    else:
        option = common.resolve(option, config)

    args.append(f"--{name.replace('_', '-')}={option}")


def burst_compile(bcl, target, config, debug=False):
    args = [bcl]

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

    for t in target.get("targets", []):
        args.append(f"--target={common.resolve_path(t, config)}")

    for asm in target.get("root_assemblies", []):
        args.append(f"--root-assembly={common.resolve_path(asm, config)}")

    logger.debug("Running burst with args: %s", args)

    if debug:
        env = os.environ.copy()
        env["UNITY_BURST_DEBUG"] = ""
    else:
        env = os.environ

    try:
        subprocess.check_call(args, env=env)
    except Exception:
        logger.exception("Burst compile failed. Command line: %s", args)
        raise


def burst_compile_all(config, print_help=False):
    compile_config = config["burst_compile"]
    bcl = compile_config.get("bcl", None)
    if bcl is None:
        raise ValueError("config must contain 'bcl' entry")

    bcl = common.resolve_path(bcl, config)

    if print_help:
        subprocess.call([bcl, "--help"])
        sys.exit(0)

    debug = compile_config.get("debug", False)

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

    with common.chdir(config["root"]):
        run(config, args)


if __name__ == "__main__":
    main()
