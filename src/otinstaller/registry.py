"""Registry management: loading, searching, and validating tool entries."""

from __future__ import annotations

import importlib.resources
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from otinstaller.config import get_home


class RegistryError(Exception):
    """Raised when registry validation fails."""

    pass


@dataclass(frozen=True)
class Install:
    method: str
    package: str | None = None
    version: str | None = None
    url: str | None = None
    ref: str | None = None
    requirements: str | None = None
    as_package: bool = False
    extra_packages: tuple[str, ...] = ()


@dataclass(frozen=True)
class Entrypoint:
    command: str | None = None
    script: str | None = None


@dataclass(frozen=True)
class ApiKeys:
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()


@dataclass(frozen=True)
class Verification:
    date: str
    version: str
    os: str
    python: str


_ACCEPTS_VALUES = (
    "username",
    "email",
    "domain",
    "ip",
    "phone",
    "url",
    "name",
)

_INPUT_TYPE_PREFIXES = (
    "u",
    "e",
    "p",
    "d",
    "url",
    "q",
    "geo",
    "tg",
    "lat",
    "lng",
)


@dataclass(frozen=True)
class Tool:
    name: str
    display_name: str
    description: str
    repo: str | None = None
    license: str | None = None
    stars: int | None = None
    tier: str = "community"
    install: Install = Install(method="pip")
    entrypoint: Entrypoint = Entrypoint()
    smoke_args: tuple[str, ...] = ("--help",)
    capabilities: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    api_keys: ApiKeys = ApiKeys()
    needs_config: bool = False
    resume_flag: str | None = None
    example: str | None = None
    verified: Verification | None = None
    accepts: tuple[str, ...] = ()
    input_types: dict[str, str] = None


_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
_PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_VERSION_RE = re.compile(r"^[0-9A-Za-z.!+-]+$")
_GIT_URL_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$")
_REF_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
_COMMAND_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_CAPABILITY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_API_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _validate_name(name: str, tool_name: str) -> None:
    if not _NAME_RE.match(name):
        raise RegistryError(f"tool '{tool_name}': name must match ^[a-z0-9][a-z0-9_-]{{0,39}}$")


def _validate_display_name(display_name: str, tool_name: str) -> None:
    if not display_name or not display_name.strip():
        raise RegistryError(f"tool '{tool_name}': display_name is required and non-empty")


def _validate_description(description: str, tool_name: str) -> None:
    if not description or not description.strip():
        raise RegistryError(f"tool '{tool_name}': description is required and non-empty")
    if "\n" in description:
        raise RegistryError(f"tool '{tool_name}': description must be one line")


def _validate_tier(tier: str, tool_name: str) -> None:
    if tier not in ("verified", "community"):
        raise RegistryError(f"tool '{tool_name}': tier must be 'verified' or 'community'")


def _validate_install(install: Install, tool_name: str) -> None:
    if install.method not in ("pip", "git"):
        raise RegistryError(f"tool '{tool_name}': install.method must be 'pip' or 'git'")

    if install.method == "pip":
        if not install.package:
            raise RegistryError(f"tool '{tool_name}': install.package is required for pip method")
        if not _PACKAGE_RE.match(install.package):
            raise RegistryError(
                f"tool '{tool_name}': install.package must match ^[A-Za-z0-9][A-Za-z0-9._-]*$"
            )
        if install.version and not _VERSION_RE.match(install.version):
            raise RegistryError(
                f"tool '{tool_name}': install.version must match ^[0-9A-Za-z.!+-]+$"
            )
        if install.url is not None:
            raise RegistryError(f"tool '{tool_name}': install.url must not be set for pip method")
        if install.ref is not None:
            raise RegistryError(f"tool '{tool_name}': install.ref must not be set for pip method")
        if install.requirements is not None:
            raise RegistryError(
                f"tool '{tool_name}': install.requirements must not be set for pip method"
            )
        if install.as_package:
            raise RegistryError(
                f"tool '{tool_name}': install.as_package must be false for pip method"
            )
        if install.extra_packages:
            for pkg in install.extra_packages:
                if not _PACKAGE_RE.match(pkg):
                    msg = (
                        f"tool '{tool_name}': install.extra_packages entry '{pkg}' "
                        f"must match ^[A-Za-z0-9][A-Za-z0-9._-]*$"
                    )
                    raise RegistryError(msg)
    else:
        if not install.url:
            raise RegistryError(f"tool '{tool_name}': install.url is required for git method")
        if not _GIT_URL_RE.match(install.url):
            raise RegistryError(f"tool '{tool_name}': install.url must be an https github.com URL")
        if install.ref and not _REF_RE.match(install.ref):
            raise RegistryError(
                f"tool '{tool_name}': install.ref must match ^[A-Za-z0-9._/-]+$ "
                "and not start with '-'"
            )
        if install.ref and install.ref.startswith("-"):
            raise RegistryError(f"tool '{tool_name}': install.ref must not start with '-'")
        has_requirements = install.requirements is not None
        has_as_package = install.as_package
        if has_requirements == has_as_package:
            raise RegistryError(
                f"tool '{tool_name}': exactly one of install.requirements "
                "or install.as_package must be given"
            )
        if install.requirements:
            if install.requirements.startswith("/") or ".." in install.requirements:
                raise RegistryError(
                    f"tool '{tool_name}': install.requirements must be a relative path with no '..'"
                )
        if install.package is not None:
            raise RegistryError(
                f"tool '{tool_name}': install.package must not be set for git method"
            )
        if install.version is not None:
            raise RegistryError(
                f"tool '{tool_name}': install.version must not be set for git method"
            )


def _validate_entrypoint(entrypoint: Entrypoint, install_method: str, tool_name: str) -> None:
    has_command = entrypoint.command is not None
    has_script = entrypoint.script is not None
    if has_command == has_script:
        raise RegistryError(
            f"tool '{tool_name}': exactly one of entrypoint.command "
            "or entrypoint.script must be given"
        )
    if entrypoint.command and not _COMMAND_RE.match(entrypoint.command):
        raise RegistryError(
            f"tool '{tool_name}': entrypoint.command must match ^[A-Za-z0-9][A-Za-z0-9._-]*$"
        )
    if entrypoint.script:
        if entrypoint.script.startswith("/") or ".." in entrypoint.script:
            raise RegistryError(
                f"tool '{tool_name}': entrypoint.script must be a relative path with no '..'"
            )
        if install_method != "git":
            raise RegistryError(
                f"tool '{tool_name}': entrypoint.script only allowed for git method"
            )


def _validate_smoke_args(smoke_args: tuple[str, ...], tool_name: str) -> None:
    for arg in smoke_args:
        if not isinstance(arg, str):
            raise RegistryError(f"tool '{tool_name}': smoke_args must be a list of strings")


def _validate_capabilities_topics(values: tuple[str, ...], field: str, tool_name: str) -> None:
    for v in values:
        if not _CAPABILITY_RE.match(v):
            raise RegistryError(
                f"tool '{tool_name}': {field} entries must be lowercase "
                "matching ^[a-z0-9][a-z0-9-]*$"
            )


def _validate_accepts(values: tuple[str, ...], tool_name: str) -> None:
    for v in values:
        if v not in _ACCEPTS_VALUES:
            raise RegistryError(
                f"tool '{tool_name}': accepts value '{v}' must be one of "
                f"{', '.join(_ACCEPTS_VALUES)}"
            )


def _validate_api_keys(api_keys: ApiKeys, tool_name: str) -> None:
    for key in api_keys.required:
        if not _API_KEY_RE.match(key):
            raise RegistryError(f"tool '{tool_name}': api key '{key}' must match ^[A-Z][A-Z0-9_]*$")
    for key in api_keys.optional:
        if not _API_KEY_RE.match(key):
            raise RegistryError(f"tool '{tool_name}': api key '{key}' must match ^[A-Z][A-Z0-9_]*$")


def _validate_stars(stars: int | None, tool_name: str) -> None:
    if stars is not None and stars < 0:
        raise RegistryError(f"tool '{tool_name}': stars must be a non-negative integer")


def _validate_input_types(input_types: dict[str, str] | None, tool_name: str) -> None:
    if input_types is None:
        return
    if not isinstance(input_types, dict):
        raise RegistryError(f"tool '{tool_name}': input_types must be a mapping")
    for prefix, flag in input_types.items():
        if prefix not in _INPUT_TYPE_PREFIXES:
            raise RegistryError(
                f"tool '{tool_name}': input_types prefix '{prefix}' must be one of "
                f"{', '.join(_INPUT_TYPE_PREFIXES)}"
            )
        if not isinstance(flag, str):
            raise RegistryError(f"tool '{tool_name}': input_types['{prefix}'] must be a string")


def _validate_unknown_keys(data: dict, tool_name: str) -> None:
    known_keys = {
        "name",
        "display_name",
        "description",
        "repo",
        "license",
        "stars",
        "tier",
        "install",
        "entrypoint",
        "smoke_args",
        "capabilities",
        "topics",
        "api_keys",
        "needs_config",
        "resume_flag",
        "example",
        "verified",
        "accepts",
        "input_types",
    }
    for key in data:
        if key not in known_keys:
            raise RegistryError(f"tool '{tool_name}': unknown key '{key}'")


def parse_tool(data: dict) -> Tool:
    tool_name = data.get("name", "unknown")
    _validate_unknown_keys(data, tool_name)
    _validate_name(data.get("name", ""), tool_name)
    _validate_display_name(data.get("display_name", ""), tool_name)
    _validate_description(data.get("description", ""), tool_name)

    tier = data.get("tier", "community")
    _validate_tier(tier, tool_name)

    install_data = data.get("install", {})
    install = Install(
        method=install_data.get("method", "pip"),
        package=install_data.get("package"),
        version=install_data.get("version"),
        url=install_data.get("url"),
        ref=install_data.get("ref"),
        requirements=install_data.get("requirements"),
        as_package=install_data.get("as_package", False),
        extra_packages=tuple(install_data.get("extra_packages", [])),
    )
    _validate_install(install, tool_name)

    entrypoint_data = data.get("entrypoint", {})
    entrypoint = Entrypoint(
        command=entrypoint_data.get("command"),
        script=entrypoint_data.get("script"),
    )
    _validate_entrypoint(entrypoint, install.method, tool_name)

    smoke_args = tuple(data.get("smoke_args", ["--help"]))
    _validate_smoke_args(smoke_args, tool_name)

    capabilities = tuple(data.get("capabilities", []))
    _validate_capabilities_topics(capabilities, "capabilities", tool_name)

    topics = tuple(data.get("topics", []))
    _validate_capabilities_topics(topics, "topics", tool_name)

    accepts = tuple(data.get("accepts", []))
    _validate_accepts(accepts, tool_name)

    api_keys_data = data.get("api_keys", {})
    api_keys = ApiKeys(
        required=tuple(api_keys_data.get("required", [])),
        optional=tuple(api_keys_data.get("optional", [])),
    )
    _validate_api_keys(api_keys, tool_name)

    stars = data.get("stars")
    _validate_stars(stars, tool_name)

    input_types = data.get("input_types")
    _validate_input_types(input_types, tool_name)

    verified = None
    if "verified" in data and data["verified"]:
        v = data["verified"]
        verified = Verification(
            date=v.get("date", ""),
            version=v.get("version", ""),
            os=v.get("os", ""),
            python=v.get("python", ""),
        )

    return Tool(
        name=data["name"],
        display_name=data["display_name"],
        description=data["description"],
        repo=data.get("repo"),
        license=data.get("license"),
        stars=stars,
        tier=tier,
        install=install,
        entrypoint=entrypoint,
        smoke_args=smoke_args,
        capabilities=capabilities,
        topics=topics,
        api_keys=api_keys,
        needs_config=data.get("needs_config", False),
        resume_flag=data.get("resume_flag"),
        example=data.get("example"),
        verified=verified,
        accepts=accepts,
        input_types=input_types or {},
    )


def load_registry(path: Path) -> list[Tool]:
    if not path.exists():
        raise RegistryError(f"registry file not found: {path}")
    try:
        with path.open() as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise RegistryError(f"invalid YAML in registry: {e}") from e

    if content is None:
        return []

    tools_list = content.get("tools", [])
    if not isinstance(tools_list, list):
        raise RegistryError("registry must have a 'tools' list")

    tools = []
    seen_names = set()
    for i, tool_data in enumerate(tools_list):
        if not isinstance(tool_data, dict):
            raise RegistryError(f"tool at index {i} must be a mapping")
        tool = parse_tool(tool_data)
        if tool.name in seen_names:
            raise RegistryError(f"duplicate tool name: {tool.name}")
        seen_names.add(tool.name)
        tools.append(tool)

    tools.sort(key=lambda t: t.name)
    return tools


def default_registry_path() -> Path:
    import os

    env_path = os.environ.get("OTINSTALLER_REGISTRY")
    if env_path:
        return Path(env_path).expanduser()

    home_path = get_home() / "registry.yaml"
    if home_path.exists():
        return home_path

    return importlib.resources.files("otinstaller.data").joinpath("registry.yaml")


def find_tool(tools: list[Tool], name: str) -> Tool | None:
    name_lower = name.lower()
    for tool in tools:
        if tool.name.lower() == name_lower:
            return tool
    return None


def search_tools(tools: list[Tool], query: str) -> list[Tool]:
    words = query.strip().split()
    if not words:
        return []

    words_lower = [w.lower() for w in words]

    def matches(tool: Tool) -> bool:
        haystack = (
            f"{tool.name} {tool.display_name} {tool.description} {' '.join(tool.capabilities)}"
        ).lower()
        return all(w in haystack for w in words_lower)

    matched = [t for t in tools if matches(t)]

    name_matches = [t for t in matched if any(w in t.name.lower() for w in words_lower)]
    other_matches = [t for t in matched if t not in name_matches]

    name_matches.sort(key=lambda t: t.name)
    other_matches.sort(key=lambda t: t.name)

    return name_matches + other_matches


def suggest_names(tools: list[Tool], name: str, limit: int = 3) -> list[str]:
    import difflib

    tool_names = [t.name for t in tools]
    return difflib.get_close_matches(name, tool_names, n=limit, cutoff=0.6)
