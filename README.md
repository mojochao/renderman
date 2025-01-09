# renderman renders manifests

The `renderman` CLI is an opinionated tool to render Kubernetes resource
manifests for an application stack of one or more workloads used when
managing Kubernetes cluster state in pull-based [GitOps](https://opengitops.dev/)
workflows with the [Rendered Manifests](https://medium.com/@PlanB./rendered-manifests-pattern-the-new-standard-for-gitops-c0b9b020f3b6)
pattern.

It is primarily intended for use by Kubernetes platform engineers and cluster
administrators responsible for the configuration and management of the platform
stack itself.
It is not particularly intended for use by non-platform tenants, whether they
are application developers or operators.

Also note that it is only intended for use and been tested on *macOS*
and *Linux* platforms for 64-bit AMD and ARM architectures.

> *"I don't always do Windows, but when I do, I prefer WSL."*
> -- The Most Interesting Platform Engineer in the World

Despite the sage advice above, who knows?
It might just work for you on Windows anyway, despite being untested and unsupported.
What do you have to lose other than your sanity?

> *"Have fun storming the castle!"*
> -- Miracle Max

With that out of the way, let's get started.

## Installation

The `renderman` package requires Python 3.12 or later, and should be installed
in a Python [virtual environment](https://docs.python.org/3/library/venv.html).

```shell
python3 -m venv .venv
source .venv/bin/activate
```

The `renderman` package can be installed from this Git repository with `pip`:

```shell
pip install pip@git+https://github.com/mojochao/renderman
```

Once installed, the `renderman` CLI will be available in the virtual environment.

The `renderman` CLI uses the following tools to render manifests:

- the [`helmfile`](https://helmfile.readthedocs.io/) and [`helm`](https://helm.sh/docs/helm/)
  CLIs to render manifests from local or remote [Helm charts](https://helm.sh/docs/topics/charts/)
- the [`kustomize`](https://kustomize.io/) CLI to render manifests from local or remote
  [kustomizations](https://kubectl.docs.kubernetes.io/references/kustomize/glossary/#kustomization)

These tools must be installed and available in the `PATH` for the `renderman` CLI
to work correctly, as the `renderman` CLI does not install these tools itself.

These tools are easily installable with [`brew`](https://brew.sh/) :package managers.

```shell
brew install helm helmfile kustomize
```

or alternatively with [`asdf`](https://asdf-vm.com/):

```bash
plugins=("helm" "helmfile" "kustomize")
for plugin in "${plugins[@]}"; do
  asdf plugin add "$plugin" && asdf install "$plugin"
done
```

If you wish to render a chart release directly from its chart source in a git
repository, you will also need to install the [`helm-git`](https://github.com/aslafy-z/helm-git)
plugin.

You do *not* need to install the [`helm-diff`](https://github.com/databus23/helm-diff)
plugin, as `helm` is only used to template chart manifests, and not to manage
chart releases in the cluster.

As the rendered manifests are modified in your locally cloned git repository,
you can examine changes to them, and the source changes responsible for the
changed renders,  with basic `git diff`, `git show`, and `git log` commands.

An additional benefit of pushing these changes will be displayed in the pull request (PR) that is created when
your push commits in a config change branch to their forge origin.

## Configuration

Configuration for a project is defined in a `renderman.yaml` file.
By default, `renderman` looks for this file in the current working directory.
The name and location of the configuration can be overridden with the `--config-file` flag.
Its initial schema as follows, from the top:

```yaml
# Root object
renderman:
  schema_version: string
  apps: [App]
```

Each `App` object is defined as follows:

```yaml
# App object fields
enabled: bool
app_name: string
releases: [Release]
kustomizations: [Kustomization]
bundles: [Bundle]
```

Each `Release` object in `.renderman.apps.*.releases` contains:

```yaml
# Release object fields
release_name: string
namespace: string
chart_name: string
chart_version: string
helmfile: optional[string]
```

Each `Kustomization` object in `.renderman.apps.*.kustomizations` contains:

```yaml
# Kustomization object fields
kustomization_name: string
source: string # Either a local path or a remote URL
```

Each `Bundle` object in `.renderman.apps.*.bundles` contains:

```yaml
# Bundle object fields
bundle_name: string
data: dict[string, any] # Arbitrary data to pass to the bundle renderer for expansion in fields
sources: list[Path | URL]
```

See the [example configuration](examples/demo-stack/renderman.yaml) for a full example.

## Rendered output layout

The rendered manifests are output to a directory structure that mirrors the
configuration structure. The output directory is created in the current working
directory by default, but can be overridden with the `--output-dir` flag.

The output directory structure is as follows:

```text
$OUTPUT_DIR/
$OUTPUT_DIR/<app_name>/
$OUTPUT_DIR/<app_name>/<release_name_a>.release.manifest.yaml
$OUTPUT_DIR/<app_name>/<release_name_b>.release.manifest.yaml
$OUTPUT_DIR/<app_name>/<kustomization_name_a>.kustomization.manifest.yaml
$OUTPUT_DIR/<app_name>/<kustomization_name_b>.kustomization.manifest.yaml
$OUTPUT_DIR/<app_name>/<bundle_name_a>.bundle.manifest.yaml
$OUTPUT_DIR/<app_name>/<bundle_name_b>.bundle.manifest.yaml
```

One common category name for bundles is `crds`.

```text
apps/cert-manager/crds.bundle.manifest.yaml
```

Another useful category name might be `externalsecrets`.

```text
apps/grafana/externalsecrets.bundle.manifest.yaml
```

Note that the `<bundle_name>` is sourced by the category name of the bundle.

## Usage

Once the `renderman` package is installed, the `renderman` CLI is available
in the Python environment it was installed into.

### Getting help

Run `renderman --help` to see the available commands.

Run `renderman <command> --help` to see the available options for a specific
command.

### Listing apps

To list the available apps in the configuration, run:

```shell
renderman apps
```

### Listing output filenames of the rendered manifests

To list the filenames of the available output files in the configuration, run:

```shell
renderman outputs
```

### Diffing rendering manifests

To diff the rendered manifests with the current manifests in the cluster, run:

```shell
renderman diff
```

If no diffs are found, the command will exit with a status code of `0`.
This is useful for CI/CD pipelines to determine if the rendered manifests
are in sync with their manifests sources in `src/<cluster_name>/`.

### Previewing rendered manifests

To preview the manifests that would be updated in the cluster, run:

```shell
renderman preview
```

This is useful for examining the complete manifests for the changes that would
be applied to the cluster before pushing the changes in your work branch to the
origin forge, where the changes 

### Updating rendered manifests

To update the rendered manifests for the cluster, run:

```shell
renderman update
```

After this command is run, the rendered manifests will be updated in the output
directory, and the changes can be examined locally with `git diff` or `git show`
before adding them to a commit in your work branch
## References

- the [Kubernetes workloads management docs](https://kubernetes.io/docs/concepts/workloads/management/)
  provide detailed information on configuring Kubernetes workloads with manifests
- the [Rendered Manifests Pattern blog post](https://medium.com/@PlanB./rendered-manifests-pattern-the-new-standard-for-gitops-c0b9b020f3b6)
  introduces the concept of rendered manifests and how they can be used to manage
  Kubernetes resource state in GitOps workflows
- the [OpenGitOps website](https://opengitops.dev/) provides a comprehensive
  overview of GitOps workflows and practices
- the [Python virtual environments docs](https://docs.python.org/3/library/venv.html)
  provide detailed information on isolating Python dependencies for a package
- the [Helmfile docs](https://helmfile.readthedocs.io/) provide detailed info
  on how to use the `helmfile` CLI to manage Helm releases
- the [Helm docs](https://helm.sh/docs/) provide detailed info on how to use
  the `helm` cli to manage Helm chart releases
- the [Kustomize docs](https://kustomize.io/) provide detailed info on how to
  use the `kustomize` CLI to manage Kubernetes resources
