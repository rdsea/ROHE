import click

from .observation import observation as observation_commands
from .orchestration import orchestration as orchestration_commands
from .start import start as start_commands


@click.group()
@click.version_option()
def rohe_cli():
    """CLI group for ROHE commands."""
    pass


rohe_cli.add_command(start_commands)
rohe_cli.add_command(orchestration_commands)
rohe_cli.add_command(observation_commands)

if __name__ == "__main__":
    rohe_cli()
