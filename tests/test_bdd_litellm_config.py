from pathlib import Path

import pytest
import yaml
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("features/litellm_config.feature")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def project_root():
    return PROJECT_ROOT


@given("the litellm config file", target_fixture="litellm_config")
def litellm_config(project_root):
    config_path = project_root / "litellm_config.yaml"
    assert config_path.exists(), f"litellm_config.yaml not found at {config_path}"
    with open(config_path) as f:
        return yaml.safe_load(f)


@given("the chatbot source file", target_fixture="chatbot_source")
def chatbot_source(project_root):
    chatbot_path = project_root / "chatbot.py"
    assert chatbot_path.exists(), "chatbot.py not found"
    return chatbot_path.read_text()


@when(parsers.parse('I check for "{filename}"'))
def check_file(project_root, filename):
    assert (project_root / filename).exists(), f"{filename} not found"


@then("the file exists")
def file_exists(project_root):
    pass


@then(parsers.parse('the config has model "{model_name}"'))
def config_has_model(litellm_config, model_name):
    model_list = litellm_config.get("model_list", [])
    names = [m.get("model_name") for m in model_list]
    assert model_name in names, f"Model '{model_name}' not found. Available: {names}"


@then(parsers.parse('the model "{model_name}" uses provider "{provider}"'))
def model_uses_provider(litellm_config, model_name, provider):
    for m in litellm_config.get("model_list", []):
        if m.get("model_name") == model_name:
            assert m.get("litellm_params", {}).get("model") == provider
            return
    pytest.fail(f"Model '{model_name}' not found")


@then("the config has fallbacks defined")
def config_has_fallbacks_defined(litellm_config):
    assert "fallbacks" in litellm_config.get("litellm_settings", {})


@then("the config has fallbacks")
def config_has_fallbacks(litellm_config):
    assert "fallbacks" in litellm_config.get("litellm_settings", {})


@then(parsers.parse('the fallback for "{primary}" includes "{fallback}"'))
def fallback_includes(litellm_config, primary, fallback):
    for fb in litellm_config.get("litellm_settings", {}).get("fallbacks", []):
        if isinstance(fb, dict) and primary in fb:
            assert fallback in fb[primary]
            return
    pytest.fail(f"No fallback entry for '{primary}'")


@then("the config has drop_params enabled")
def config_drop_params(litellm_config):
    assert litellm_config.get("litellm_settings", {}).get("drop_params") is True


@then(parsers.parse('the file contains "{variable}"'))
def file_contains_variable(project_root, variable):
    content = (project_root / ".env.example").read_text()
    assert variable in content


@then(parsers.parse('the file imports "{module}"'))
def file_imports(chatbot_source, module):
    assert f"import {module}" in chatbot_source or f"from {module}" in chatbot_source


@then(parsers.parse('the file loads "{filename}"'))
def file_loads(chatbot_source, filename):
    assert f'open({filename}' in chatbot_source or f'yaml.safe_load' in chatbot_source


@then(parsers.parse('the model "{model_name}" has param "{param}" starting with "{prefix}"'))
def model_param_starts_with(litellm_config, model_name, param, prefix):
    for m in litellm_config.get("model_list", []):
        if m.get("model_name") == model_name:
            value = m.get("litellm_params", {}).get(param, "")
            assert value.startswith(prefix), f"Expected '{param}' to start with '{prefix}', got '{value}'"
            return
    pytest.fail(f"Model '{model_name}' not found")


@then('the chatbot source file resolves "os.environ/" references')
def chatbot_resolves_env_refs(chatbot_source):
    assert "_resolve_env_refs" in chatbot_source, "_resolve_env_refs function not found"
    assert "os.environ/" in chatbot_source, "os.environ/ reference resolution not found"


@then(parsers.parse('the file calls "{func}"'))
def file_calls_func(chatbot_source, func):
    assert func in chatbot_source


@then('the call does not use hardcoded "base_url"')
def no_hardcoded_base_url(chatbot_source):
    for line in chatbot_source.split("\n"):
        if "acompletion" in line:
            assert "base_url=" not in line


@then('the call does not use hardcoded "api_key"')
def no_hardcoded_api_key(chatbot_source):
    for line in chatbot_source.split("\n"):
        if "acompletion" in line:
            assert "api_key=" not in line
