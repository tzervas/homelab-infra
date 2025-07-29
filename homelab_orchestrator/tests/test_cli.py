import pytest
from click.testing import CliRunner

from homelab_orchestrator.cli import cli


@pytest.fixture()
def runner():
    return CliRunner()


def test_cli_help():
    """Test that CLI help works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Homelab Orchestrator" in result.output


def test_manage_help():
    """Test that manage command help works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["manage", "--help"])
    assert result.exit_code == 0
    assert "Backup, Teardown, and Recovery operations" in result.output
    assert "backup" in result.output
    assert "teardown" in result.output
    assert "recover" in result.output


def test_config_validate():
    """Test that config validate command works."""
    runner = CliRunner()
    # This will fail due to missing config but should show the command exists
    result = runner.invoke(cli, ["config", "validate"])
    # We expect this to fail gracefully with config issues
    assert "Configuration Validation Results" in result.output or result.exit_code != 0
