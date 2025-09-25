from agents import Agent
from agents.tool import Tool
from pydantic import BaseModel

from .azure_function_app_best_practices_agent import (
    DEFAULT_TOOL_NAME as AZURE_FUNCTIONAPP_BEST_PRACTICES_TOOL_NAME,
)


class CleanupCommands(BaseModel):
    """Single command for deleting the target resource group."""

    cleanup_command: str


_INSTRUCTIONS = (
    "You generate exactly ONE Azure CLI command in JSON with key cleanup_command. "
    "Goal: delete a specified resource group and all its resources. Requirements: "
    "1) Use: az group delete --name <RG> --yes --no-wait --only-show-errors. "
    "2) MUST include --yes to suppress confirmation. "
    "3) MUST include --only-show-errors (reduce noise). "
    "4) MAY include --no-wait so the pipeline can continue. "
    "5) BEFORE emitting final output, you MUST call the tool "
    f"{AZURE_FUNCTIONAPP_BEST_PRACTICES_TOOL_NAME} with the candidate command. "
    "Only emit the JSON once the tool returns status=approved. If it is rejected, "
    "refine the command and re-run the tool. "
    "6) Output strictly JSON, no explanation."
)


def get_cleanup_prompt(config):
    """Prompt focusing the model on emitting a single RG deletion command."""

    return (
        "Provide JSON with cleanup_command only. Delete the resource group idempotently.\n"
        f"Resource Group: {config['RESOURCE_GROUP_NAME']}\n"
        f"You must call {AZURE_FUNCTIONAPP_BEST_PRACTICES_TOOL_NAME} to verify the command.\n"
        "Command form: az group delete --name <RG> --yes --no-wait --only-show-errors\n"
        "No extra commentary."
    )


def build_cleanup_agent(best_practices_tool: Tool) -> Agent:
    """Create a cleanup agent with the best-practices tool attached."""

    return Agent(
        name="cleanup_agent",
        instructions=_INSTRUCTIONS,
        tools=[best_practices_tool],
        output_type=CleanupCommands,
    )
