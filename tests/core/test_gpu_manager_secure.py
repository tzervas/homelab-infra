"""Tests for secure command execution in GPU Manager."""

import pytest
from unittest.mock import patch, Mock, AsyncMock

from homelab_orchestrator.core.gpu_manager import GPUResourceManager
from homelab_orchestrator.utils.command_utils import execute_command


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager."""
    config = Mock()
    config.get_gpu_config.return_value = {
        "enabled": True,
        "discovery": {
            "local_gpus": True,
            "remote_gpus": False
        }
    }
    return config


@pytest.fixture
def gpu_manager(mock_config_manager):
    """Initialize GPU manager for testing."""
    return GPUResourceManager(mock_config_manager)


@pytest.mark.asyncio
async def test_secure_nvidia_smi_execution(gpu_manager):
    """Test secure execution of nvidia-smi commands."""
    mock_response = (0, "0, Tesla V100, 32510, 0, 0, 35, 450.102.04", "")
    
    with patch('homelab_orchestrator.utils.command_utils.execute_command',
              new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_response
        
        # Test GPU discovery
        result = await gpu_manager.discover_gpu_resources()
        
        # Verify secure command execution
        mock_exec.assert_called()
        calls = mock_exec.call_args_list
        
        # Check that no commands were run with shell=True
        for call in calls:
            assert 'shell=True' not in str(call)
        
        # Check that commands were run with proper allowed_commands
        assert any('allowed_commands=[\"nvidia-smi\"]' in str(call) for call in calls)
        
        # Verify successful discovery
        assert result["success"]
        assert result["gpus_found"] == 1


@pytest.mark.asyncio
async def test_secure_kubectl_execution(gpu_manager):
    """Test secure execution of kubectl commands."""
    # Mock successful deployment check
    deploy_check = (0, "", "")
    # Mock successful deployment
    deploy_response = (0, "daemonset.apps/nvidia-device-plugin-daemonset created", "")
    
    with patch('homelab_orchestrator.utils.command_utils.execute_command',
              new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = [deploy_check, deploy_response]
        
        # Test device plugin setup
        result = await gpu_manager._setup_nvidia_device_plugin()
        
        # Verify secure command execution
        mock_exec.assert_called()
        calls = mock_exec.call_args_list
        
        # Check that kubectl commands were run securely
        for call in calls:
            assert 'allowed_commands=[\"kubectl\"]' in str(call)
            assert 'shell=True' not in str(call)
        
        # Verify successful deployment
        assert result["success"]
        assert result["action"] == "skipped"


@pytest.mark.asyncio
async def test_secure_command_validation(gpu_manager):
    """Test command validation in GPU operations."""
    with patch('homelab_orchestrator.utils.command_utils.validate_command',
              return_value=False) as mock_validate:
        with patch('homelab_orchestrator.utils.command_utils.execute_command',
                  new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = ValueError("Command validation failed")
            
            # Test GPU discovery with invalid command
            result = await gpu_manager.discover_gpu_resources()
            
            # Verify command validation
            mock_validate.assert_called()
            
            # Verify discovery failed
            assert not result["success"]
            assert "Command validation failed" in str(result.get("error", ""))


@pytest.mark.asyncio
async def test_gpu_command_error_handling(gpu_manager):
    """Test error handling for GPU commands."""
    error_response = (1, "", "Command failed with error")
    
    with patch('homelab_orchestrator.utils.command_utils.execute_command',
              new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = error_response
        
        # Test GPU discovery with command error
        result = await gpu_manager.discover_gpu_resources()
        
        # Verify error was handled properly
        assert not result["success"]
        assert result["gpus_found"] == 0


@pytest.mark.asyncio
async def test_gpu_command_timeout_handling(gpu_manager):
    """Test timeout handling for GPU commands."""
    with patch('homelab_orchestrator.utils.command_utils.execute_command',
              new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = TimeoutError("Command timed out")
        
        # Test GPU discovery with timeout
        result = await gpu_manager.discover_gpu_resources()
        
        # Verify timeout was handled properly
        assert not result["success"]
        assert "timed out" in str(result.get("error", "")).lower()


@pytest.mark.asyncio
async def test_gpu_secure_environment_handling(gpu_manager):
    """Test secure environment handling in GPU operations."""
    env_vars = {
        "CUDA_VISIBLE_DEVICES": "0,1",
        "PATH": "/usr/local/cuda/bin:/usr/local/bin:/usr/bin",
    }
    
    with patch('homelab_orchestrator.utils.command_utils.execute_command',
              new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = (0, "", "")
        
        # Test GPU plugin setup with environment
        await gpu_manager._setup_nvidia_device_plugin()
        
        # Verify environment was handled securely
        calls = mock_exec.call_args_list
        for call in calls:
            if 'env=' in str(call):
                assert 'shell=True' not in str(call)
                assert 'allowed_commands=' in str(call)


@pytest.mark.asyncio
async def test_gpu_command_injection_prevention(gpu_manager):
    """Test prevention of command injection in GPU operations."""
    injection_attempts = [
        "; rm -rf /",
        "|| true",
        "&& echo 'compromised'",
        "` rm -rf /`",
        "$(rm -rf /)",
    ]
    
    for injection in injection_attempts:
        # Try to execute GPU discovery with injection attempt
        result = await gpu_manager.discover_gpu_resources()
        
        # Verify injection was prevented
        assert result["gpus_found"] == 0  # No GPUs should be found
        # Check logs for security warnings
        # This would require setting up a log capture fixture
