from pydantic import BaseModel
from agents import Agent, handoff
from .azure_function_app_best_practices_agent import (
    build_best_practices_agent,
    ReviewInput
)
from .azure_function_app_best_practices_agent import CleanupCommandReview

class FunctionAppCreationCommands(BaseModel):
    function_app_command: str

# Build reviewer agent for handoff
_base_reviewer = build_best_practices_agent(None)

# Helper: persist data across handoff via context and craft next agent input
def _store_in_context(ctx, key: str, value):
    if ctx.context is None:
        ctx.context = {}
    try:
        ctx.context[key] = value
    except Exception:
        # if context isn't a dict, replace with one
        ctx.context = {key: value}

def _to_reviewer_input(handoff_input_data):
    ctx = handoff_input_data.run_context
    payload = None if ctx is None else getattr(ctx, "context", None)
    payload = payload.get("review_request") if isinstance(payload, dict) else None
    if not payload:
        text = (
            "Validate the following Azure CLI command for creating a Flex Consumption Function App. "
            "Return a JSON matching the CleanupCommandReview schema."
        )
    else:
        text = (
            "Please review this candidate Function App creation command against Azure best practices.\n"
            f"Command: {payload['command']}\n"
            f"Resource Group: {payload['resource_group']}\n"
            f"Region: {payload['region']}\n"
            f"Storage Account: {payload['storage_account']}\n"
            f"Function App Name: {payload['function_app_name']}\n"
            f"Runtime: {payload['runtime']}\n\n"
            "Respond with status=approved or rejected, feedback, and optional corrected_command. "
            "Then handoff back to the creation agent using the transfer tool."
        )
    return handoff_input_data.clone(input_history=text)

def _to_creation_input(handoff_input_data):
    ctx = handoff_input_data.run_context
    verdict = None if ctx is None else getattr(ctx, "context", None)
    verdict = verdict.get("review_result") if isinstance(verdict, dict) else None
    if not verdict:
        text = "Reviewer returned no structured verdict. Please regenerate a compliant command."
    else:
        text = (
            "Best-practices review verdict received.\n"
            f"Status: {verdict['status']}\n"
            f"Feedback: {verdict['feedback']}\n"
        )
        if verdict.get("corrected_command"):
            text += f"Suggested corrected_command: {verdict['corrected_command']}\n"
        text += (
            "If rejected, revise your candidate command accordingly and re-submit for review. "
            "If approved, emit final JSON with function_app_command (use corrected_command if provided)."
        )
    return handoff_input_data.clone(input_history=text)

# Create a specialized reviewer instance for the creation flow with a back-handoff stubbed in later
_reviewer_for_creation = _base_reviewer

FUNCTION_APP_CREATION_AGENT = Agent(
    name="function_app_creation_agent",
    instructions=(
        "You are a helpful assistant that generates ONLY the Azure CLI command to create (if absent) an Azure Functions Flex Consumption Function App. "
        "Return a JSON object with the single key: function_app_command. "
        "Requirements:\n"
        "1. Create a Flex Consumption function app using az functionapp create with --runtime (python or node supplied via prompt), and region.\n"
        "2. Do NOT include storage account creation – storage account already exists and name will be provided. Use --storage-account <STORAGE>.\n"
        "3. MUST NOT enable public blob access anywhere.\n"
        "4. Do NOT include --consumption-plan-location and only include --flexconsumption-location.\n"
        "Before returning your final JSON, you MUST handoff to the azure_function_app_best_practices_agent "
        "to validate the candidate command. Use the transfer tool for that agent, passing a JSON payload "
        "with keys: command, resource_group, region, storage_account, function_app_name, runtime. "
        "If the review returns status=rejected, use the feedback (and any corrected_command) to revise the command, "
        "then handoff again. Only emit the final JSON after an approved review."
    ),
    output_type=FunctionAppCreationCommands,
    handoffs=[
        # _reviewer_for_creation
        handoff(
            _reviewer_for_creation,
            on_handoff=lambda ctx, data: _store_in_context(ctx, "review_request", data.model_dump()),
            input_type=ReviewInput,
            input_filter=_to_reviewer_input,
        )
    ],
)

# Now add a back-handoff from the reviewer to the creation agent, so the flow returns with feedback
_reviewer_for_creation.handoffs = [
    handoff(
        FUNCTION_APP_CREATION_AGENT,
        on_handoff=lambda ctx, data: _store_in_context(ctx, "review_result", data.model_dump()),
        input_type=CleanupCommandReview,
        input_filter=_to_creation_input,
    )
]

def get_function_app_creation_prompt(config):
    """Builds the prompt asking for the idempotent function app creation command only."""
    return f"""
Generate only the single Azure CLI command (wrapped in JSON per instructions) to create a Flex Consumption Function App if it does not already exist.
Inputs:
- Resource Group: {config['RESOURCE_GROUP_NAME']}
- Region: {config['AZURE_REGION']}
- Storage Account: {config['STORAGE_ACCOUNT_NAME']}
- Function App Name: {config['FUNCTION_APP_NAME']}
- Runtime: {config.get('FUNCTION_RUNTIME', 'python')}

The command must:
- Use --flexconsumption-location {config['AZURE_REGION']} and the provided runtime.
- Reference the existing storage account with --storage-account.
- Do NOT include --consumption-plan-location or --function-version.

Before you return the JSON, handoff to the reviewer using the transfer tool named transfer_to_azure_function_app_best_practices_agent. 
Pass the following JSON payload to the transfer tool:
{{
    "command": "<your candidate command>",
    "resource_group": "{config['RESOURCE_GROUP_NAME']}",
    "region": "{config['AZURE_REGION']}",
    "storage_account": "{config['STORAGE_ACCOUNT_NAME']}",
    "function_app_name": "{config['FUNCTION_APP_NAME']}",
    "runtime": "{config.get('FUNCTION_RUNTIME', 'python')}"
}}
Iterate until the reviewer returns status=approved, then emit the final JSON with function_app_command.
"""
