#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from __future__ import annotations
import copy
from dataclasses import Field, dataclass, field, fields
import dataclasses
from functools import reduce
import json

import pathlib
import sys
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)
import zipfile

PathLike = Union[str, pathlib.Path]

T = TypeVar("T")

JsonClassTag = "_IsJsonClass"


_TYPE_MAP: Dict[str, Optional[Type[Any]]] = {}


def get_class(name: str) -> Optional[Type[Any]]:
    try:
        return _TYPE_MAP[name]
    except KeyError:
        pass

    parts = name.partition(".")

    try:
        m = sys.modules[__name__]
        cls = _TYPE_MAP[name] = cast(Type[Any], getattr(m, name))
        return cls
    except AttributeError:
        pass

    try:
        if parts[1] and "[" not in parts[0]:
            cls = _TYPE_MAP[name] = cast(
                Type[Any],
                reduce(getattr, name.split(".")[1:], __import__(parts[0])),
            )
    except AttributeError:
        pass

    _TYPE_MAP[name] = None
    return None


def parse_list(
    items: Union[List[T], List[Union[T, Dict[Any, Any]]]], type: Type[T]
) -> List[T]:
    return [type(**v) if isinstance(v, dict) else v for v in items]  # type: ignore


def parse_dict(
    items: Union[Dict[str, T], Dict[str, Union[T, Dict[Any, Any]]]], type: Type[T]
) -> Dict[str, T]:
    return {k: type(**v) if isinstance(v, dict) else v for k, v in items.items()}


def post_init(self: Any) -> None:
    for f in fields(self):
        value = getattr(self, f.name)

        init = f.metadata.get("__post_init__", None)
        if init is not None:
            setattr(self, f.name, init(getattr(self, f.name)))
            continue

        type = get_class(str(f.type))
        if type is None:
            continue

        if getattr(type, JsonClassTag, False):
            if isinstance(value, dict):
                setattr(self, f.name, type(**value))
            continue

        if type is pathlib.Path:
            setattr(self, f.name, pathlib.Path(value))
            continue


def jsonclass(cls: Type[T]) -> Type[T]:
    old_init: Optional[Callable[[T], None]] = getattr(cls, "__post_init__", None)

    new_init: Callable[[T], None]

    if old_init is None:
        new_init = post_init
    else:

        def init(self: T) -> None:
            post_init(self)
            old_init(self)  # type: ignore

        new_init = init

    setattr(cls, "__post_init__", new_init)
    setattr(cls, JsonClassTag, True)
    return cls


def listfield(type: Type[T], optional: bool = False) -> List[T]:
    def parse(items: Optional[List[T]]) -> Optional[List[T]]:
        if items is None:
            return None
        return parse_list(items, type)

    kwargs: Dict[str, Any] = {}
    if optional:
        kwargs["default"] = None
    else:
        kwargs["default_factory"] = lambda: list  # type: ignore

    return field(
        **kwargs,
        metadata=dict(__post_init__=parse),
    )


@dataclass
class Substitution:
    search: str
    replace: str


@dataclass
@jsonclass
class Pattern:
    pattern: str
    substitutions: List[Substitution] = listfield(Substitution)


@dataclass
class FileCopy:
    source: str
    destination: str


@dataclass
@jsonclass
class ReplaceAction:
    regex: List[Pattern] = listfield(Pattern)
    template_files: List[FileCopy] = listfield(FileCopy)


@dataclass
@jsonclass
class PostBuildActionList:
    clean: List[str] = field(default_factory=list)
    install: List[FileCopy] = listfield(FileCopy)


@dataclass
class PostBuildAction(PostBuildActionList):
    pdb2mdb: Optional[pathlib.Path] = None

    def __init__(
        self,
        clean: List[str] = dataclasses.MISSING,  # type: ignore
        install: List[FileCopy] = dataclasses.MISSING,  # type: ignore
        pdb2mdb: Optional[PathLike] = None,
        **kwargs: PostBuildActionList,
    ) -> None:
        super().__init__(clean, install)
        self.pdb2mdb = None
        if pdb2mdb is not None:
            self.pdb2mdb = pathlib.Path(pdb2mdb)
        self.per_target = parse_dict(kwargs, PostBuildActionList)

        # emulate dynamic fields
        fs: Dict[str, Field[Any]] = getattr(self, "__dataclass_fields__")
        default_field = fs["pdb2mdb"]
        for name in self.per_target:
            f = copy.copy(default_field)
            f.name = name
            f.type = "PostBuildActionList"  # type: ignore
            fs[name] = f

        try:
            self.__post_init__()  # type: ignore
        except AttributeError:
            pass

    def __getitem__(self, key: str) -> PostBuildActionList:
        return self.per_target[key]

    def __getattr__(self, name: str) -> PostBuildActionList:
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __contains__(self, key: str) -> bool:
        return key in self.per_target

    def update(self, other: PostBuildActionList) -> None:
        self.clean = other.clean
        self.install = other.install


@dataclass
@jsonclass
class Dependency:
    path: pathlib.Path
    destination: str
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    map: List[FileCopy] = listfield(FileCopy)


@dataclass
@jsonclass
class PackageAction:
    filename: str
    output_dir: pathlib.Path = field(default_factory=lambda: pathlib.Path(""))
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    map: List[FileCopy] = listfield(FileCopy)
    dependencies: List[Dependency] = listfield(Dependency)
    compression: Optional[str] = "DEFLATED"

    @property
    def compression_value(self) -> Optional[int]:
        if self.compression is None:
            return None
        return getattr(zipfile, f"ZIP_{self.compression.upper()}")


@dataclass
@jsonclass
class BurstTarget:
    platform: str
    output: pathlib.Path
    include: Optional[str] = None
    safety_checks: Optional[bool] = None
    fastmath: Optional[bool] = None
    targets: Optional[List[str]] = None
    enable_guard: Optional[bool] = None
    float_precision: Optional[str] = None
    float_mode: Optional[str] = None
    debug: Optional[str] = None
    debugMode: Optional[bool] = None
    verbose: Optional[bool] = None
    log_timings: Optional[bool] = None
    root_assemblies: Optional[List[pathlib.Path]] = listfield(
        pathlib.Path, optional=True
    )
    assembly_folders: Optional[List[pathlib.Path]] = listfield(
        pathlib.Path, optional=True
    )
    include_root_assembly_references: Optional[bool] = None

    def update(self, other: BurstTarget) -> None:
        for f in fields(other):
            value = getattr(other, f.name)
            if value is None:
                continue
            setattr(self, f.name, value)


@dataclass
@jsonclass
class BurstCompileAction:
    bcl: pathlib.Path
    debug: bool = False
    targets: List[BurstTarget] = listfield(BurstTarget)


@dataclass
@jsonclass
class Config:
    root: pathlib.Path
    build_props: pathlib.Path
    post_build: PostBuildAction
    replace: ReplaceAction
    package: PackageAction
    burst_compile: BurstCompileAction
    variables: Dict[str, Union[str, int]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.build_props.is_absolute():
            self.build_props = self.root / self.build_props

    def glob(
        self, pattern: PathLike, root: Optional[PathLike] = None
    ) -> Generator[pathlib.Path, None, None]:
        if root is None:
            root = self.root
        else:
            root = pathlib.Path(root)

        pattern = pathlib.Path(pattern).expanduser()
        if pattern.is_absolute():
            parts = pattern.parts
            root = pathlib.Path(parts[0])
            p = str(pathlib.Path(*parts[1:]))
        else:
            p = str(pattern)

        return root.glob(p)


class JSONEncoder(json.JSONEncoder):
    def default(self, o: Any):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, pathlib.Path):
            return str(o)
        return super().default(o)
