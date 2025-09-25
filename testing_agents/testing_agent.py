import subprocess
import json
from agents import trace, custom_span

def run_tests(config):
    """
    Executes a series of Azure CLI commands based on the test matrix.
    """
    test_matrix = config['TEST_MATRIX']
    app_name = config['FUNCTION_APP_NAME']
    resource_group = config['RESOURCE_GROUP_NAME']
    results = []

    for test in test_matrix:
        with custom_span(f'test_{test["TestCaseId"]}'):
            command = test['Command'].format(AppName=app_name, ResourceGroup=resource_group)
            
            print(f"--- Running Test: {test['TestCaseId']} ---")
            print(f"Description: {test['Description']}")
            print(f"Command: {command}")

            span_data = {"command": command}
            with custom_span("subprocess_run", data=span_data):
                try:
                    result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
                    print("Status: PASS")
                    print("Output:")
                    print(result.stdout)
                    span_data["result"] = result.stdout[:1000]  # Store only the first 1000 chars
                    results.append({"test": test, "status": "PASS", "output": result.stdout})
                except subprocess.CalledProcessError as e:
                    print("Status: FAIL")
                    print("Error:")
                    print(e.stderr)
                    span_data["error"] = e.stderr[:1000]  # Store only the first 1000 chars
                    results.append({"test": test, "status": "FAIL", "output": e.stderr})
            
            print("-" * (len(test['TestCaseId']) + 16))
            print()

    return results
