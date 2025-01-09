"""Renderman app command-line interface."""
import click

from .core import CONFIGFILE_NAME, SOURCE_TYPES, AppName, RenderType, diff_manifests, get_outputs, get_renders, get_manifests, initialize, update_manifests


@click.group(name="renderman")
def app():
    """renderman renders kubernetes resource manifests from multiple sources."""


@app.command("apps")
@click.option("-f", "--config-file", "config_file", default=CONFIGFILE_NAME, help="Config file.", metavar="PATH", show_default=True, type=str)
@click.option("-q", "--quiet", "quiet", is_flag=True, help="Suppress message output.")
def apps_cmd(config_file: str, quiet: bool):
    """List the apps with manifests to render."""
    try:
        config = initialize(config_file=config_file, quiet=quiet)
        app_names = [app_name for app_name, app_config in config.renderman.apps.items() if app_config.enabled]
        print("\n".join(app_names))
    except Exception as e:
        raise click.ClickException(f"Error listing apps: {e}")


@app.command("outputs")
@click.option("-f", "--config-file", "config_file", default=CONFIGFILE_NAME, help="Config file.", metavar="PATH", show_default=True, type=str)
@click.option("-a", "--app", "app_names", help="App names.  [multiple]", metavar="NAME", multiple=True, type=str)
@click.option("-t", "--type", "source_types", help="Source types.", multiple=True, type=click.Choice(SOURCE_TYPES))
@click.option("-q", "--quiet", "quiet", is_flag=True, help="Suppress message output.")
def outputs_cmd(config_file: str, app_names: list[AppName], source_types: list[RenderType], quiet: bool):
    """List the rendered manifests outputs."""
    try:
        config = initialize(config_file=config_file, quiet=quiet)
        outputs = get_outputs(config, app_names, source_types)
        print("\n".join(sorted(outputs)))
    except Exception as e:
        raise click.ClickException(f"Error listing outputs: {e}")


@app.command("preview")
@click.option("-f", "--config-file", "config_file", default=CONFIGFILE_NAME, help="Config file.", metavar="PATH", show_default=True, type=str)
@click.option("-a", "--app", "app_names", help="App names.  [multiple]", metavar="NAME", multiple=True, type=str)
@click.option("-t", "--type", "source_types", help="Source types.", multiple=True, type=click.Choice(SOURCE_TYPES))
@click.option("-q", "--quiet", "quiet", is_flag=True, help="Suppress message output.")
@click.option("--debug", "debug", is_flag=True, help="Enable debug output.")
@click.option("--no-helm-repo-update", "skip_helm_repo_update", is_flag=True, help="Skip updating Helm repositories.")
def preview_cmd(config_file: str, app_names: list[AppName], source_types: list[RenderType], quiet: bool, debug: bool, skip_helm_repo_update: bool):
    """Preview the rendered manifests text."""
    try:
        config = initialize(config_file=config_file, quiet=quiet, debug=debug, skip_helm_repo_update=skip_helm_repo_update)
        renders = get_renders(config, app_names, source_types)
        manifests = get_manifests(renders)
        print("\n".join([manifest.document for manifest in manifests]))
    except Exception as e:
        raise click.ClickException(f"Error previewing manifests: {e}")


@app.command("diff")
@click.option("-f", "--config-file", "config_file", default=CONFIGFILE_NAME, help="Config file.", metavar="PATH", show_default=True, type=str)
@click.option("-a", "--app", "app_names", help="App names.  [multiple]", metavar="NAME", multiple=True, type=str)
@click.option("-t", "--type", "source_types", help="Source types.", multiple=True, type=click.Choice(SOURCE_TYPES))
@click.option("-o", "--output-dir", "output_dir", help="Output directory.", metavar="PATH", required=True, type=str)
@click.option("-q", "--quiet", "quiet", is_flag=True, help="Suppress message output.")
@click.option("--debug", "debug", is_flag=True, help="Enable debug output.")
@click.option("--no-helm-repo-update", "skip_helm_repo_update", is_flag=True, help="Skip updating Helm chart repositories.")
def diff(config_file: str, app_names: list[AppName], source_types: list[RenderType], output_dir: str, quiet: bool, debug: bool, skip_helm_repo_update: bool):
    """Write the rendered manifests to their outputs."""
    try:
        config = initialize(config_file=config_file, quiet=quiet, debug=debug, skip_helm_repo_update=skip_helm_repo_update)
        renders = get_renders(config, app_names, source_types)
        manifests = get_manifests(renders)
        diff_manifests(manifests, output_dir)
    except Exception as e:
        raise click.ClickException(f"Error updating manifests: {e}")


@app.command("update")
@click.option("-f", "--config-file", "config_file", default=CONFIGFILE_NAME, help="Config file.", metavar="PATH", show_default=True, type=str)
@click.option("-a", "--app", "app_names", help="App names.  [multiple]", metavar="NAME", multiple=True, type=str)
@click.option("-t", "--type", "source_types", help="Source types.", multiple=True, type=click.Choice(SOURCE_TYPES))
@click.option("-o", "--output-dir", "output_dir", help="Output directory.", metavar="PATH", required=True, type=str)
@click.option("-q", "--quiet", "quiet", is_flag=True, help="Suppress message output.")
@click.option("--debug", "debug", is_flag=True, help="Enable debug output.")
@click.option("--no-helm-repo-update", "skip_helm_repo_update", is_flag=True, help="Skip updating Helm chart repositories.")
def update_cmd(config_file: str, app_names: list[AppName], source_types: list[RenderType], output_dir: str, quiet: bool, debug: bool, skip_helm_repo_update: bool):
    """Write the rendered manifests to their outputs."""
    try:
        config = initialize(config_file=config_file, quiet=quiet, debug=debug, skip_helm_repo_update=skip_helm_repo_update)
        renders = get_renders(config, app_names, source_types)
        manifests = get_manifests(renders)
        update_manifests(manifests, output_dir)
    except Exception as e:
        raise click.ClickException(f"Error updating manifests: {e}")


if __name__ == "__main__":
    app()
