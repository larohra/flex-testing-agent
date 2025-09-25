"""Agent package exports for testing agents."""

from .creation_agent import CREATION_AGENT, CreationCommands
from .function_app_creation_agent import (
	FUNCTION_APP_CREATION_AGENT,
	FunctionAppCreationCommands,
	get_function_app_creation_prompt,
)
from .cleanup_agent import (
	CleanupCommands,
	build_cleanup_agent,
	get_cleanup_prompt,
)
from .azure_function_app_best_practices_agent import (
	CleanupCommandReview,
	create_functionapp_docs_mcp_server,
	build_best_practices_agent,
	build_best_practices_tool,
	DEFAULT_TOOL_NAME as AZURE_FUNCTIONAPP_BEST_PRACTICES_TOOL_NAME,
)

__all__ = [
	"CREATION_AGENT",
	"CreationCommands",
	"FUNCTION_APP_CREATION_AGENT",
	"FunctionAppCreationCommands",
	"get_function_app_creation_prompt",
	"CleanupCommands",
	"build_cleanup_agent",
	"get_cleanup_prompt",
	"CleanupCommandReview",
	"create_functionapp_docs_mcp_server",
	"build_best_practices_agent",
	"build_best_practices_tool",
	"AZURE_FUNCTIONAPP_BEST_PRACTICES_TOOL_NAME",
]
