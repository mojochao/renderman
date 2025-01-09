"""Renderman app core."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from os import makedirs, path
from subprocess import run
from shutil import which, rmtree
from sys import stderr, version_info
from tempfile import TemporaryDirectory
from typing import Optional

import requests
import yaml

# -----------------------------------------------------------------------------
# Define global constants
# -----------------------------------------------------------------------------

CONFIGFILE_NAME = "renderman.yaml"
HELMFILE_NAME = "helmfile.yaml"
EXTERNAL_TOOLS = ["git", "helm", "helmfile", "kustomize"]
SOURCE_TYPES = ["bundle", "kustomization", "release"]
TEXT_ENCODING = "utf-8"
YAML_SEPARATOR = "---"


# -----------------------------------------------------------------------------
# Define types to make the code more readable and self-documenting
# -----------------------------------------------------------------------------

type AppName = str
"""The name of an application in the stack."""

"""The version of a Helm chart for a chart release."""

type Document = str
"""A YAML document containing one or more Kubernetes resource manifests."""

type ExitCode = int
"""The exit code of a command-line program."""

type Path = str
"""A file path for a local resource manifest document."""

type URL = str
"""An HTTP URL for a remote resource manifest document."""

type Source = Path | URL
"""The source of a resource manifest document."""

type RenderType = str
"""The type of the renderer of a resource manifest document."""

type ChartVersion = str
"""The version of a Helm chart for a chart release."""


# -----------------------------------------------------------------------------
# Define config file schema and loading support
# -----------------------------------------------------------------------------

@dataclass
class Bundle:
    app_name: AppName
    bundle_name: str
    data: Optional[dict[str, str]] = field(default_factory=dict)
    sources: list[Source] = field(default_factory=list)

    @property
    def paths(self) -> list[Path]:
        data = {k: v.format(self.data) for k, v in self.data.items()}
        return [source.format(data) for source in self.sources if not source.startswith("http")]

    @property
    def source_type(self) -> RenderType:
        return "bundle"

    @property
    def urls(self) -> list[URL]:
        data = {k: v.format(self.data) for k, v in self.data.items()}
        return [source.format(data) for source in self.sources if source.startswith("http")]


@dataclass
class Kustomization:
    app_name: AppName
    kustomization_name: str
    source: Source

    @property
    def source_type(self) -> RenderType:
        return "kustomization"


@dataclass
class Release:
    app_name: AppName
    release_name: str
    chart_name: str
    chart_version: ChartVersion
    helmfile: Optional[Path] = None

    @property
    def source_type(self) -> RenderType:
        return "release"


@dataclass
class App:
    enabled: bool = True
    releases: Optional[list[Release]] = field(default_factory=list)
    bundles: list[Bundle] = field(default_factory=list)
    kustomizations: list[Kustomization] = field(default_factory=list)


@dataclass
class Renderman:
    schema_version: str = "1"
    apps: dict[str, App] = field(default_factory=dict)


@dataclass
class Config:
    renderman: Renderman


# -----------------------------------------------------------------------------
# Define global flags initialized in CLI commands from options
# -----------------------------------------------------------------------------

DEBUG = False
QUIET = False
SKIP_HELM_REPO_UPDATE = False
SOURCE_DIR = ""


def initialize(config_file: str, quiet: bool, debug: bool = False, skip_helm_repo_update: bool = False) -> Config:
    """Initialize renderman."""
    # Ensure minimum Python version and required tools are available.
    if version_info < (3, 12):
        raise RuntimeError("Python 3.12 or higher is required.")

    missing_tools = [tool for tool in EXTERNAL_TOOLS if not which(tool)]
    if missing_tools:
        raise RuntimeError(f"required tools not found: {', '.join(missing_tools)}")

    # Set global flags.
    global SOURCE_DIR, DEBUG, QUIET, SKIP_HELM_REPO_UPDATE
    SOURCE_DIR = path.dirname(config_file)
    DEBUG = debug
    QUIET = quiet
    SKIP_HELM_REPO_UPDATE = skip_helm_repo_update

    # Return loaded config.
    try:
        with open(config_file, "r") as file:
            data = yaml.safe_load(file)
        return Config(**data)
    except Exception as e:
        raise RuntimeError(f"Error loading config file {config_file}: {e}")


# -----------------------------------------------------------------------------
# Define enhanced user messaging support
# -----------------------------------------------------------------------------

def message(msg: str) -> None:
    """Print messages to stderr if 'quiet' option not provided.

    Keep stdout reserved for "real" output, such as that produced by the 'apps' and 'preview' commands.
    """
    if not QUIET:
        print(msg, file=stderr)


# -----------------------------------------------------------------------------
# Define rendering support
# -----------------------------------------------------------------------------

@dataclass
class Render:
    """An app Kubernetes manifest render with enough metadata to create a meaningful output file name."""

    app_name: AppName
    """The name of the app for the rendered manifest."""

    source_type: RenderType
    """The type of the source of the rendered manifest, such as 'release', 'bundle', or 'kustomization'."""

    source: Source
    """The source of the rendered manifest, such as a file path or URL."""

    document: Optional[Document] = None
    """The rendered manifest document, if no error occurred."""

    error: Optional[Exception] = None
    """The error that occurred during rendering, if any."""


class Renderer(ABC):
    """App manifests renderer interface."""

    config: Config
    """Loaded renderman config."""

    source_type: RenderType
    """The type of the source of the rendered manifest."""

    def __init__(self, config: Config, source_type: RenderType):
        """Initialize a new Renderer with loaded renderman config data."""
        self.config = config
        self.source_type = source_type

    @property
    def apps(self) -> list[AppName]:
        """Get the app names capable of being rendered."""
        return [app_name for app_name, app_config in self.config.renderman.apps.items() if app_config.enabled]

    @abstractmethod
    def render(self, app_names: list[AppName], source_types: list[RenderType]) -> list[Render]:
        """Render app manifests for the given app names and source types."""


class BundleRenderer(Renderer):
    """Renderer implementation for bundles of local and/or remote static Kubernetes resources."""

    def __init__(self, config: Config):
        super().__init__(config, "bundle")

    def render(self, app_names: list[AppName], source_types: list[RenderType]) -> list[Render]:
        # Collect bundles to render.
        bundles: list[Bundle] = []
        for loaded_app_name, loaded_app_data in self.config.renderman.apps.items():
            if loaded_app_name not in app_names:
                continue
            for release in loaded_app_data.bundles:
                release.app_name = loaded_app_name
                bundles.append(release)

        # Return renders of bundles.
        renders: list[Render] = []
        for bundle in bundles:
            renders.extend(render_bundle(bundle))
        return renders


def render_bundle(bundle: Bundle) -> list[Render]:
    """Render manifest for a resource bundle."""
    renders = []
    # Process local resources.
    for file_path in bundle.paths:
        document = None
        error = None
        try:
            with open(file_path, "r", encoding=TEXT_ENCODING) as infile:
                document = infile.read()
        except Exception as e:
            error = e
        renders.append(
            Render(
                app_name=bundle.app_name,
                source_type=bundle.source_type,
                source=file_path,
                document=document,
                error=error,
            )
        )
    # Process remote resources.
    for url in bundle.urls:
        document = None
        error = None
        message(f"Fetching {bundle.app_name} resource manifest from {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for HTTP error codes
            document = response.text.strip()  # Remove leading/trailing whitespace
            document = document.lstrip(f"{YAML_SEPARATOR}\n")  # Remove leading YAML separator
            document = document.rstrip(f"\n{YAML_SEPARATOR}")  # Remove trailing YAML separator
        except Exception as e:
            error = e
        renders.append(
            Render(
                app_name=bundle.app_name,
                source_type=bundle.source_type,
                source=url,
                document=document,
                error=error,
            )
        )
    return renders


class KustomizationRenderer(Renderer):
    """Renderer implementation for Kustomize bases and/or overlays."""

    def __init__(self, config: Config):
        super().__init__(config, "kustomization")

    def render(self, app_names: list[AppName], source_types: list[RenderType]) -> list[Render]:
        # Collect kustomizations to render.
        kustomizations: list[Kustomization] = []
        for app_name, app_data in self.config.renderman.apps.items():
            if app_name not in app_names:
                continue
            for kustomization in app_data.kustomizations:
                kustomization.app_name = app_name
                kustomizations.append(kustomization)
        # Return renders of kustomizations.
        renders: list[Render] = []
        for kustomization in kustomizations:
            renders.extend(render_kustomization(kustomization))
        return renders


def render_kustomization(kustomization: Kustomization) -> list[Render]:
    """Render manifest for a Kustomize base and/or overlay."""
    document = None
    error = None
    try:
        document = run_kustomize_build_cmd(kustomization)
    except Exception as e:
        error = e
    return [
        Render(
            app_name=kustomization.app_name,
            source_type=kustomization.source_type,
            source=kustomization.source,
            document=document,
            error=error
        )
    ]


def run_kustomize_build_cmd(kustomization: Kustomization) -> str:
    """Run the kustomize build command for a given app name and source."""
    cmd = f"kustomize build {kustomization.source}"
    return run(cmd, shell=True, check=True, text=True, capture_output=True).stdout


class ReleaseRenderer(Renderer):
    """Helmfile releases Renderer implementation for Kubernetes manifests."""

    def __init__(self, config: Config):
        super().__init__(config, "release")

    def render(self, app_names: list[AppName], source_types: list[RenderType]) -> list[Render]:
        # Collect releases to render.
        releases: list[Release] = []
        for app_name, app_config in self.config.renderman.apps.items():
            if app_name not in app_names:
                continue
            for release in app_config.releases:
                release.app_name = app_name
                releases.append(release)
        # Return renders of releases.
        renders = []
        for release in releases:
            renders.extend(render_release(release))
        return renders


def render_release(release: Release) -> list[Render]:
    """Render manifest for a Helmfile release."""
    # Set the helmfile path to that configured in the release if it exists,
    # otherwise use the helmfile.yaml in the same directory as the config file.
    default_helmfile_path = path.join(SOURCE_DIR, HELMFILE_NAME)
    helmfile_path = release.helmfile or default_helmfile_path
    # Render the release manifest using the 'helmfile template' command.
    error = None
    document = None
    try:
        document = run_helmfile_template_cmd(helmfile_path=helmfile_path, release_name=release.app_name)
    except Exception as e:
        error = e
    return [
        Render(
            app_name=release.app_name,
            source_type=release.source_type,
            source=helmfile_path,
            document=document,
            error=error
        )
    ]


def run_helmfile_template_cmd(helmfile_path: Path, release_name: str) -> str:
    """Run the helmfile template command for a given app name."""
    debug_option = "--debug" if DEBUG else ""
    skip_deps_option = "--skip-deps" if SKIP_HELM_REPO_UPDATE else ""
    cmd = f"helmfile template --file={helmfile_path} --selector name={release_name} {debug_option} {skip_deps_option}"
    return run(cmd, shell=True, check=True, text=True, capture_output=True).stdout


def get_outputs(config: Config, app_names: list[AppName], category_names: list[RenderType]) -> list[Path]:
    """Get the renders for the given apps and categories."""
    outputs = []
    for app_name, app_config in config.renderman.apps.items():
        if app_name in app_names and app_config.enabled:
            continue
        if "bundle" in category_names and app_config.bundles:
            file_names = [f"{b.bundle_name}.bundle.manifest.yaml" for b in app_config.bundles]
            outputs.extend([path.join(app_name, f) for f in file_names])
        if "kustomization" in category_names and app_config.kustomizations:
            file_names = [f"{k.kustomization_name}.kustomize.manifest.yaml" for k in app_config.kustomizations]
            outputs.extend([path.join(app_name, f) for f in file_names])
        if "release" in category_names and app_config.releases:
            file_names = [f"{r.name}.release.manifest.yaml" for r in app_config.releases]
            outputs.extend([path.join(app_name, f) for f in file_names])
    return outputs


def get_renders(config: Config, app_names: list[AppName], source_types: list[RenderType]) -> list[Render]:
    """Get the renders for the given apps and categories."""
    renders = []
    renders.extend(BundleRenderer(config).render(app_names, source_types))
    renders.extend(KustomizationRenderer(config).render(app_names, source_types))
    renders.extend(ReleaseRenderer(config).render(app_names, source_types))
    return renders


# -----------------------------------------------------------------------------
# Manifests support
# -----------------------------------------------------------------------------

class Manifest:
    """A rendered manifest for an app and source type with multiple sections."""
    def __init__(self, app_name: AppName, source_type: RenderType, renders: list[Render]):
        self.app_name = app_name
        self.source_type = source_type
        self.renders = renders

    @property
    def document(self) -> str:
        """Get the rendered manifest text document."""
        return "\n---\n".join([r.document for r in self.renders if r.document])

    def file_path(self, output_dir: Path) -> Path:
        """Get the file path for the rendered manifest."""
        return path.join(output_dir, self.app_name, f"{self.source_type}.manifest.yaml")

    def save(self, output_dir: Path) -> Path:
        """Save the rendered manifest to the output directory."""
        manifest_path = self.file_path(output_dir)
        makedirs(path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, "w", encoding=TEXT_ENCODING) as outfile:
            sections = [r.document for r in self.renders if r.document]
            outfile.write("\n---\n".join(sections))
        return manifest_path


def get_manifests(renders: list[Render]) -> list[Manifest]:
    """Get the rendered manifests for the given apps and source types."""
    grouped = {}
    for render in renders:
        key = (render.app_name, render.source_type)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(render.document)
    return [Manifest(app_name, source_type, renders) for (app_name, source_type), renders in grouped.items()]


def diff_manifests(manifests: list[Manifest], output_dir: Path) -> ExitCode:
    """Diff the rendered manifests in the output directory and return 0 if no differences were found, return 1 if found."""
    # Write the manifests to a staging directory.
    with TemporaryDirectory() as staging_dir:
        save_manifests(manifests, staging_dir)
    # Diff the manifests in the output directory.
    diff_cmd = f"diff -r -u {staging_dir} {output_dir}"
    diff_output = run(diff_cmd, shell=True, check=False, text=True, capture_output=True)
    print(diff_output.stdout)
    # Clean up after ourselves.
    rmtree(staging_dir, ignore_errors=True)
    # Return 0 if no differences were found, 1 if differences were found.
    return diff_output.returncode


def update_manifests(manifests: list[Manifest], output_dir: Path) -> list[Path]:
    """Update the rendered manifests in the output directory."""
    # Write the manifests to a staging directory.
    with TemporaryDirectory() as staging_dir:
        save_manifests(manifests, staging_dir)
    # Remove the existing manifests output directory.
    rmtree(output_dir, ignore_errors=True)
    # Populate new output directory from the staging directory
    makedirs(output_dir)
    paths = save_manifests(manifests, output_dir)
    # Clean up after ourselves.
    rmtree(staging_dir, ignore_errors=True)
    # Return the paths of the written manifests.
    return sorted(paths)


def save_manifests(manifests: list[Manifest], output_dir: Path) -> list[Path]:
    """Write the rendered manifests to the output directory and return their output paths."""
    return [manifest.save(output_dir) for manifest in manifests]
