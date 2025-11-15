import requests
import inspect
from openapiclient import OpenAPIClient
from pipelex.core.memory.working_memory import WorkingMemory
from pipelex.core.stuffs.list_content import ListContent
from pipelex.core.stuffs.text_content import TextContent
from pipelex.system.registries.func_registry import pipe_func
from pydantic import Field
from pipelex.core.stuffs.structured_content import StructuredContent

class FunctionParameter(StructuredContent):
    name : str = Field(description="parameter name")
    value : str = Field(description="parameter value")
    type : str = Field(description="parameter type")


@pipe_func()
async def invoke_function_api_backend(working_memory: WorkingMemory) -> TextContent:
    openapi_url = working_memory.get_stuff_as_text("openapi_url").text.strip()
    function_name_text = working_memory.get_stuff_as_text("function_name").text
    function_name = function_name_text.strip('`')
    function_parameters = working_memory.get_stuff_as("function_parameters", ListContent)

    # Initialize the API factory with the OpenAPI definition
    print(type(function_name))
    print("About to call: " + function_name)
    print(type(function_parameters))
    param_dict = {}
    for parameter in function_parameters.items:
        p = FunctionParameter(**parameter.__dict__)
        param_dict[p.name] = p.value
        print(f"name: {p.name} val: {p.value} type: {p.type}")


    # Initialize the API factory with the OpenAPI definition
    api = OpenAPIClient(definition=openapi_url)

    # Use the async client with context manager
    async with api.AsyncClient() as client:
        # Show available operations
        print("Operations:", client.operations)
        print("Available functions:", client.functions)
        print(f"Invoking desired function: {function_name}" )
        result = await client(method_name=function_name, parameters=param_dict)
    return TextContent(text=str(result))

@pipe_func()
async def obtain_openapi_spec(working_memory: WorkingMemory) -> TextContent:
    openapi_url = working_memory.get_stuff_as_text("openapi_url").text.strip()
    response = requests.get(url=openapi_url)
    spec_data = response.json()

    api = OpenAPIClient(definition=openapi_url)

    # Use the async client with context manager
    async with api.AsyncClient() as client:
        # Build detailed function signatures from OpenAPI spec
        functions_detail = []

        # Parse the OpenAPI spec to extract function signatures
        if 'paths' in spec_data:
            for path, methods in spec_data['paths'].items():
                for method, operation in methods.items():
                    if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                        continue

                    operation_id = operation.get('operationId')
                    if not operation_id:
                        continue

                    params = []

                    # Extract parameters
                    if 'parameters' in operation:
                        for param in operation['parameters']:
                            param_name = param.get('name', 'unknown')
                            param_required = param.get('required', False)
                            param_in = param.get('in', '')

                            if param_required:
                                params.append(f"{param_name}")
                            else:
                                params.append(f"{param_name}=None")

                    # Check for request body
                    if 'requestBody' in operation:
                        body_required = operation['requestBody'].get('required', False)
                        if body_required:
                            params.append("body")
                        else:
                            params.append("body=None")

                    params_str = ", ".join(params) if params else ""
                    functions_detail.append(f"{operation_id}({params_str})")

        # Fallback: just list function names
        if not functions_detail:
            for func_name in client.functions.keys():
                functions_detail.append(f"{func_name}(**kwargs)")

        functions_text = "\n".join(functions_detail)
        spec = f"\n\nAvailable functions:\n{functions_text}"
        print(spec)
    return TextContent(text=spec)