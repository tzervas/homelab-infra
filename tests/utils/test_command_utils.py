"""Tests for the command execution utilities."""

import logging
import os
import subprocess
from unittest import mock

import pytest

from homelab_orchestrator.utils.command_utils import execute_command, validate_command


# Test validate_command function
def test_validate_command_empty():
    """Test validation of empty commands."""
    assert not validate_command("")
    assert not validate_command([])


def test_validate_command_unsafe_chars():
    """Test validation of commands with unsafe characters."""
    unsafe_commands = [
        "ls & rm",
        "echo | grep",
        "cat; ls",
        "echo > file",
        "grep < file",
    ]
    for cmd in unsafe_commands:
        assert not validate_command(cmd)


def test_validate_command_allowed_list():
    """Test command validation against allowed list."""
    allowed = ["kubectl", "helm"]
    
    # Valid commands
    assert validate_command("kubectl get pods", allowed)
    assert validate_command(["helm", "list"], allowed)
    
    # Invalid commands
    assert not validate_command("docker ps", allowed)
    assert not validate_command(["rm", "-rf"], allowed)


def test_validate_command_safe():
    """Test validation of safe commands."""
    safe_commands = [
        "ls -la",
        ["git", "status"],
        "kubectl get pods",
        ["python", "-m", "pytest"],
    ]
    for cmd in safe_commands:
        assert validate_command(cmd)


# Test execute_command function
def test_execute_command_success(caplog):
    """Test successful command execution."""
    with caplog.at_level(logging.INFO):
        returncode, stdout, stderr = execute_command(["echo", "test"])
        
    assert returncode == 0
    assert stdout.strip() == "test"
    assert not stderr
    assert "Executing command: echo test" in caplog.text
    assert "Command completed with return code: 0" in caplog.text


def test_execute_command_failure(caplog):
    """Test command execution failure."""
    with pytest.raises(subprocess.CalledProcessError):
        with caplog.at_level(logging.ERROR):
            execute_command(["ls", "nonexistent_file"])
    
    assert "Command failed with return code" in caplog.text


def test_execute_command_timeout():
    """Test command timeout."""
    with pytest.raises(subprocess.TimeoutExpired):
        execute_command(["sleep", "2"], timeout=1)


def test_execute_command_invalid():
    """Test execution of invalid commands."""
    with pytest.raises(ValueError):
        execute_command("rm -rf & ls", allowed_commands=["ls"])


def test_execute_command_with_env():
    """Test command execution with environment variables."""
    env = {"TEST_VAR": "test_value"}
    returncode, stdout, stderr = execute_command(
        ["sh", "-c", "echo $TEST_VAR"],
        env=env
    )
    assert stdout.strip() == "test_value"


def test_execute_command_with_cwd():
    """Test command execution with working directory."""
    temp_dir = "/tmp"
    returncode, stdout, stderr = execute_command(
        ["pwd"],
        cwd=temp_dir
    )
    assert stdout.strip() == temp_dir


@mock.patch('subprocess.run')
def test_execute_command_shell_injection(mock_run):
    """Test prevention of shell injection."""
    mock_run.return_value = mock.Mock(
        returncode=0,
        stdout="",
        stderr=""
    )
    
    # This should be executed as a list, not through shell
    execute_command("echo $(rm -rf)")
    
    # Verify the command was executed safely
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert kwargs.get('shell') is False
    assert isinstance(args[0], list)


def test_execute_command_logging_sensitive_data(caplog):
    """Test that sensitive data is not logged."""
    secret = "super_secret_token"
    env = {"API_TOKEN": secret}
    
    with caplog.at_level(logging.DEBUG):
        execute_command(
            ["sh", "-c", "echo $API_TOKEN"],
            env=env
        )
    
    # Verify secret is not in logs
    assert secret not in caplog.text


@pytest.mark.parametrize("command,allowed,expected", [
    (["ls", "-l"], ["ls"], True),
    (["rm", "-rf"], ["ls"], False),
    ("git status", ["git"], True),
    ("malicious | rm", ["git"], False),
])
def test_validate_command_parametrized(command, allowed, expected):
    """Parametrized test for command validation."""
    assert validate_command(command, allowed) == expected
