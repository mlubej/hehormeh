"""Implements the command line interface for `hehormeh`."""

import subprocess

import click

variables_option = click.option(
    "-v",
    "--variable",
    "cli_variables",
    multiple=True,
    type=str,
    help='Specify variables to use in config (overriding present config values). Must be of form `"name:value"`',
)


@click.command()
@click.option("-p", "--port", type=int, default=5001, help="Port to run the server on")
@click.option("-d", "--debug", type=bool, is_flag=True, help="Enable debug mode")
def start_server(port: int, debug: bool) -> None:
    """Start the server."""
    app = __name__.replace("cli", "app")
    cmd = f"flask --app {app} run --host=0.0.0.0"
    cmd += f" --port={port}" if port else ""
    cmd += " --debug" if debug else ""

    subprocess.run(cmd, shell=True)
