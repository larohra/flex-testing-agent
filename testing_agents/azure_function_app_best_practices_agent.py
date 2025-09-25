"""Azure Function App CLI best-practices reviewer agent."""

from __future__ import annotations

import json
import os
from typing import Literal, Optional

from pydantic import BaseModel

from agents import Agent
from agents.mcp import MCPServer, MCPServerStreamableHttp, MCPServerStreamableHttpParams

AZURE_FUNCTIONAPP_MCP_URL_ENV = "AZURE_FUNCTIONAPP_MCP_URL"
AZURE_FUNCTIONAPP_MCP_HEADERS_ENV = "AZURE_FUNCTIONAPP_MCP_HEADERS_JSON"
AZURE_FUNCTIONAPP_MCP_API_KEY_ENV = "AZURE_FUNCTIONAPP_MCP_API_KEY"
DEFAULT_TOOL_NAME = "azure_functionapp_best_practices_review"
DEFAULT_SERVER_NAME = "azure-functionapp-docs"


class CleanupCommandReview(BaseModel):
    """Review verdict for any Azure Function App CLI command."""

    status: Literal["approved", "rejected"]
    feedback: str
    corrected_command: Optional[str] = None


class ReviewInput(BaseModel):
    """Input payload for handing off a candidate creation command to the reviewer."""

    command: str
    resource_group: str
    region: str
    storage_account: str
    function_app_name: str
    runtime: str


def create_functionapp_docs_mcp_server() -> MCPServer:
    """Instantiate the MCP server that exposes Azure Function App documentation tools."""

    url = "https://learn.microsoft.com/api/mcp" # os.getenv(AZURE_FUNCTIONAPP_MCP_URL_ENV)
    if not url:
        raise RuntimeError(
            f"Environment variable {AZURE_FUNCTIONAPP_MCP_URL_ENV} must be set to the Azure MCP functionapp endpoint."
        )

    headers: dict[str, str] = {}
    api_key = os.getenv(AZURE_FUNCTIONAPP_MCP_API_KEY_ENV)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    header_blob = os.getenv(AZURE_FUNCTIONAPP_MCP_HEADERS_ENV)
    if header_blob:
        try:
            parsed_headers = json.loads(header_blob)
            if not isinstance(parsed_headers, dict):
                raise ValueError("Header JSON must decode to an object")
            headers.update({str(k): str(v) for k, v in parsed_headers.items()})
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Failed to parse {AZURE_FUNCTIONAPP_MCP_HEADERS_ENV} as JSON object"
            ) from exc

    params: MCPServerStreamableHttpParams = {"url": url}
    if headers:
        params["headers"] = headers

    return MCPServerStreamableHttp(params, name=DEFAULT_SERVER_NAME, cache_tools_list=True)


def build_best_practices_agent(server: Optional[MCPServer] = None) -> Agent:
    """Create the agent responsible for validating Azure Function App CLI commands."""

    instructions = (
        "You are the Azure Function App CLI best-practices reviewer. "
        "Whenever any agent supplies an Azure CLI command for creating, configuring, or cleaning up "
        "Function App resources, exhaustively consult the MCP tools on this server to retrieve the "
        "official best-practices guidance. "
        "Verify the command follows all required flags, safety confirmations, and scope expectations "
        "for both provisioning and deletion scenarios. "
        "If the command is compliant, respond with status=approved and a concise justification. "
        "If not, respond with status=rejected, detailed remediation feedback, and provide an updated "
        "corrected_command that aligns with the guidance."
        "The command must:\n"
        "- Use --flexconsumption-location {config['AZURE_REGION']} and the provided runtime."
        "- Reference the existing storage account with --storage-account."
        "- Do NOT include --consumption-plan-location or --function-version."
    )

    if server:
        return Agent(
            name="azure_function_app_best_practices_agent",
            instructions=instructions,
            handoff_description=(
                "Validates Azure Function App cleanup commands against Azure MCP documentation and "
                "returns an approval verdict with optional corrections."
            ),
            mcp_servers= [server],
            output_type=CleanupCommandReview,
        )
    else:
        return Agent(
            name="azure_function_app_best_practices_agent",
            instructions=instructions,
            output_type=CleanupCommandReview,
        )


def build_best_practices_tool(agent: Agent, *, tool_name: str = DEFAULT_TOOL_NAME):
    """Expose the best-practices agent as a reusable tool."""

    description = (
        "Reviews an Azure CLI command for Azure Function Apps. Returns approval status, "
        "feedback, and an optional corrected command based on Azure documentation."
    )

    return agent.as_tool(tool_name, description)


def get_function_app_command_review_prompt(config: dict[str, str], command: str) -> str:
    """Construct a prompt asking the best-practices agent to validate a creation command."""

    return (
        "You are validating an Azure CLI command that creates a Flex Consumption Azure Function App. "
        "Confirm the command is safe, idempotent, and aligned with Azure guidance. "
        "If the command passes review respond with status=approved and concise justification. "
        "If it fails, respond with status=rejected, detailed feedback, and provide a corrected_command "
        "illustrating the compliant form.\n\n"
        f"Context:\n"
        f"- Resource Group: {config['RESOURCE_GROUP_NAME']}\n"
        f"- Region: {config['AZURE_REGION']}\n"
        f"- Storage Account: {config['STORAGE_ACCOUNT_NAME']}\n"
        f"- Function App Name: {config['FUNCTION_APP_NAME']}\n"
        f"- Runtime: {config.get('FUNCTION_RUNTIME', 'python')}\n\n"
        "Command to review (do not execute, only evaluate):\n"
        f"{command}\n"
        "Return your decision strictly following the structured schema with keys status, feedback, "
        "and optional corrected_command."
        "The command must:\n"
        "- Use --flexconsumption-location {config['AZURE_REGION']} and the provided runtime."
        "- Reference the existing storage account with --storage-account."
        "- Do NOT include --consumption-plan-location or --function-version."
    )


__all__ = [
    "CleanupCommandReview",
    "ReviewInput",
    "create_functionapp_docs_mcp_server",
    "build_best_practices_agent",
    "build_best_practices_tool",
    "get_function_app_command_review_prompt",
    "DEFAULT_TOOL_NAME",
]
