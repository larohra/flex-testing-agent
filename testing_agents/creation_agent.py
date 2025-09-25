from agents import Agent
from pydantic import BaseModel

class CreationCommands(BaseModel):
    """Infrastructure creation commands (no function app)."""
    resource_group_command: str
    storage_account_command: str

CREATION_AGENT = Agent(
    name="creation_agent",
    instructions=(
        "You are a helpful assistant that generates Azure CLI commands for ONLY infrastructure prerequisites (resource group and storage account). "
        "Return a JSON object with exactly the keys: resource_group_command, storage_account_command. "
        "Do NOT include any function app creation logic.\n"
        "Requirements:\n"
        "1. Resource group may use plain 'az group create' (already idempotent).\n"
        "2. Storage account creation MUST include '--allow-blob-public-access false'. Never set it to true.\n"
    ),
    output_type=CreationCommands,
)

def get_creation_prompt(config):
    """Prompt for infra prerequisites only (no function app)."""
    return f"""
Generate two Azure CLI commands as JSON (resource_group_command, storage_account_command) for infrastructure prerequisites ONLY.
Inputs:
- Resource Group: {config['RESOURCE_GROUP_NAME']}
- Region: {config['AZURE_REGION']}
- Storage Account: {config['STORAGE_ACCOUNT_NAME']}

Commands:
1. Create the resource group (idempotent).
2. Create the storage account with --allow-blob-public-access false.

Do NOT include any function app creation.
"""