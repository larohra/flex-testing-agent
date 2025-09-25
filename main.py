import json
import os
import subprocess
import asyncio
import random
import string
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from agents import Runner, set_default_openai_client, set_default_openai_api, trace, custom_span, function_span
from testing_agents.creation_agent import CREATION_AGENT, get_creation_prompt
from testing_agents.testing_agent import run_tests
from testing_agents.cleanup_agent import build_cleanup_agent, get_cleanup_prompt
from testing_agents.function_app_creation_agent import (
    FUNCTION_APP_CREATION_AGENT,
    get_function_app_creation_prompt,
)
from testing_agents.azure_function_app_best_practices_agent import (
    build_best_practices_agent,
    build_best_practices_tool,
    create_functionapp_docs_mcp_server,
)

load_dotenv()

deployment = "larohra-gpt-4o"
openai_client = AsyncAzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=deployment,
)
# Set the default OpenAI client for the Agents SDK
set_default_openai_client(openai_client, use_for_tracing=False)
set_default_openai_api('chat_completions')

# set_tracing_disabled(True)

def execute_commands(commands):
    """
    Executes a list of shell commands.
    """
    for command in commands:
        with custom_span(f'execute_command_{command[:5].replace(" ", "_")}'):
            try:
                print(f"Executing: {command}")
                span_data = {"command": command}
                with custom_span("subprocess_run", data=span_data):
                    result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
                    print(result.stdout)
                    span_data["result"] = result.stdout[:1000]
            except subprocess.CalledProcessError as e:
                print(f"Error executing command: {command}")
                print(e.stderr)
                raise

async def main():
    """
    Main orchestrator for the testing agent.
    """
    load_dotenv()

    with open('config.json', 'r') as f:
        config = json.load(f)

    # --- Dynamic random naming overrides ---
    def _rand(suffix_len: int = 6, alphabet: str = string.ascii_lowercase + string.digits):
        return ''.join(random.choice(alphabet) for _ in range(suffix_len))

    # Resource group: keep base or generate new unique
    base_rg = config.get('RESOURCE_GROUP_NAME', 'flex-agent-test-rg')
    config['RESOURCE_GROUP_NAME'] = f"{base_rg}-{_rand()}"

    # Storage account: must be 3-24 chars, lowercase letters & digits, unique globally.
    # Start with base (letters/digits) then append random ensuring max length 24.
    base_storage = ''.join(ch for ch in config.get('STORAGE_ACCOUNT_NAME', 'flexagentstorage').lower() if ch.isalnum())
    rand_part = _rand(12)
    truncated_base = base_storage[: (24 - len(rand_part))]
    config['STORAGE_ACCOUNT_NAME'] = f"{truncated_base}{rand_part}"[:24]

    # Short-circuit for repeatability during testing
    # config['RESOURCE_GROUP_NAME'] = "flex-agent-test-rg-dskmsh"
    # config['STORAGE_ACCOUNT_NAME'] = "flexagentstoxjvv58qghind"

    # Function App: prefix requirement
    rand_fn = _rand(8)
    config['FUNCTION_APP_NAME'] = f"test-flex-agent-{rand_fn}"

    print("Resolved dynamic names:")
    print("  Resource Group:", config['RESOURCE_GROUP_NAME'])
    print("  Storage Account:", config['STORAGE_ACCOUNT_NAME'])
    print("  Function App:", config['FUNCTION_APP_NAME'])

    best_practices_server = create_functionapp_docs_mcp_server()

    # --- Creation Phase ---
    print("--- Starting Creation Phase ---")
    creation_prompt = get_creation_prompt(config)
    with custom_span('creation_agent_run'):
        creation_result = await Runner.run(CREATION_AGENT, creation_prompt)
        creation_commands = creation_result.final_output
        print("Generated Infra Commands: ", creation_commands)
        # Execute only resource group and storage account commands
        execute_commands([
            creation_commands.resource_group_command,
            creation_commands.storage_account_command,
        ])

    print("--- Create Function App Command ---")
    with custom_span('function_app_creation_agent_run'):
        function_app_creation_prompt = get_function_app_creation_prompt(config)
        function_app_creation_result = await Runner.run(FUNCTION_APP_CREATION_AGENT, function_app_creation_prompt)
    function_app_creation_command = function_app_creation_result.final_output.function_app_command
    print("Generated Function App Creation Command (validated): ", function_app_creation_command)
    execute_commands([function_app_creation_command])
    print("--- Creation Phase Complete ---")

    # --- Testing Phase ---
    print("\n--- Starting Testing Phase ---")
    with custom_span('run_tests'):
        results = run_tests(config)
    print("Test Results: ", results)
    print("--- Testing Phase Complete ---")

    # --- Cleanup Phase ---
    print("\n--- Starting Cleanup Phase ---")
    with function_span('cleanup_agent_run'):
        best_practices_agent = build_best_practices_agent(best_practices_server)
        best_practices_tool = build_best_practices_tool(best_practices_agent)
        cleanup_agent = build_cleanup_agent(best_practices_tool)
        cleanup_prompt = get_cleanup_prompt(config)
        cleanup_result = await Runner.run(cleanup_agent, cleanup_prompt)
        print("Generated Cleanup Command: ", cleanup_result.final_output)
        execute_commands([cleanup_result.final_output.cleanup_command])

    print("--- Cleanup Phase Complete ---")

if __name__ == "__main__":
    with trace('Start Testing Flow'):
        asyncio.run(main())
