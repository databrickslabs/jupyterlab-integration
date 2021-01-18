import pytest

from databrickslabs_jupyterlab.local import _build_config_content


@pytest.fixture
def default_config():
    return {
        "c.KernelManager.autorestart": False,
        "c.MappingKernelManager.kernel_info_timeout": 20,
    }


@pytest.fixture
def overwritten_config(default_config):
    default_config['c.NotebookApp.tornado_settings'] = {}
    return default_config


def test_build_config_content(default_config):
    config_lines = [
        "c.NotebookApp.token=''",
        "c.NotebookApp.tornado_settings={"
        "    'headers': {",
        "        'Content-Security-Policy': \"frame-ancestors 'self' http://localhost/\"",
        "    }}"
    ]
    result_config = _build_config_content(lines=config_lines, config=default_config)
    expected_config = [line + '\n' for line in config_lines]
    expected_config = expected_config + [
        'c.KernelManager.autorestart=False\n',
        'c.MappingKernelManager.kernel_info_timeout=20\n',
    ]
    assert result_config == expected_config


def test_build_config_content_with_config_overwrite(overwritten_config):
    config_lines = [
        "c.NotebookApp.token=''",
        "c.NotebookApp.tornado_settings={"
        "    'headers': {",
        "        'Content-Security-Policy': \"frame-ancestors 'self' http://localhost/\"",
        "    }}"
    ]
    result_config = _build_config_content(lines=config_lines, config=overwritten_config)
    expected_config = [
        'c.NotebookApp.token=\'\'\n',
        'c.NotebookApp.tornado_settings={}\n',
        'c.KernelManager.autorestart=False\n',
        'c.MappingKernelManager.kernel_info_timeout=20\n',
    ]
    assert result_config == expected_config
