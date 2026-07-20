Feature: LiteLLM Configuration
  As a developer
  I want litellm to load provider configuration from a YAML file
  So that I can switch between OpenRouter, OpenAI and Ollama without code changes

  Scenario: litellm config file exists
    When I check for "litellm_config.yaml"
    Then the file exists

  Scenario: config contains OpenRouter provider
    Given the litellm config file
    Then the config has model "openrouter"
    And the model "openrouter" uses provider "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"

  Scenario: config contains OpenAI provider
    Given the litellm config file
    Then the config has model "openai"
    And the model "openai" uses provider "gpt-4o"

  Scenario: config contains Ollama provider
    Given the litellm config file
    Then the config has model "ollama"
    And the model "ollama" uses provider "ollama/llama3"

  Scenario: config has fallbacks defined
    Given the litellm config file
    Then the config has fallbacks
    And the fallback for "openrouter" includes "openai"
    And the fallback for "openrouter" includes "ollama"

  Scenario: config drops unsupported parameters
    Given the litellm config file
    Then the config has drop_params enabled

  Scenario: .env.example exists with required variables
    When I check for ".env.example"
    Then the file exists
    And the file contains "AI_MODEL"
    And the file contains "OPENROUTER_API_KEY"
    And the file contains "OPENAI_API_KEY"
    And the file contains "OLLAMA_BASE_URL"

  Scenario: chatbot.py uses litellm config
    Given the chatbot source file
    Then the file imports "litellm"
    And the file loads "litellm_config.yaml"
    And the file calls "litellm.acompletion"
    And the call does not use hardcoded "base_url"
    And the call does not use hardcoded "api_key"

  Scenario: env references are resolved from YAML config
    Given the litellm config file
    Then the model "openrouter" has param "api_key" starting with "os.environ/"

  Scenario: chatbot resolves os.environ references at runtime
    Given the chatbot source file
    Then the chatbot source file resolves "os.environ/" references
