# Change Log

## CLI Best Practices Agent (2025-09-24)
- Added `azure_function_app_best_practices_agent` which connects to the Azure MCP Function App documentation server to review Function App-related CLI commands (creation and cleanup).
- Cleanup agent now requires the `azure_functionapp_best_practices_review` tool to approve generated `az group delete` commands before emitting the final JSON, and the same tool can be reused by other agents such as the creation workflow.
- Introduced new environment variables to configure the MCP server connection:
	- `AZURE_FUNCTIONAPP_MCP_URL` (required)
	- `AZURE_FUNCTIONAPP_MCP_API_KEY` (optional bearer token)
	- `AZURE_FUNCTIONAPP_MCP_HEADERS_JSON` (optional custom headers JSON)

## Infra Creation Agent Refactor (2025-09-14)
- `CreationCommands` now only includes: `resource_group_command`, `storage_account_command`.
- Removed responsibility for function app creation from `creation_agent`.
- Updated `main.py` to execute only the two infra commands.
- A separate agent (`FUNCTION_APP_CREATION_AGENT`) should be used for function app provisioning.

## Dynamic Naming Enhancement (2025-09-14)
- Added runtime randomization of `RESOURCE_GROUP_NAME`, `STORAGE_ACCOUNT_NAME`, and `FUNCTION_APP_NAME` in `main.py`.
- Function app names now always prefixed with `test-flex-agent-` followed by random 8-char alphanumeric suffix.
- Storage account name randomized while preserving compliance (<=24 chars, lowercase, alphanumeric).
- Resource group name now includes a 6-char suffix for uniqueness per run.

## Agent Swarm Validation (2026-04-08)
- This repository was used for an agent swarm validation run.
