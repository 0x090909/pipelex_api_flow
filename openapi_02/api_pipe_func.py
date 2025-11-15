import json

from openapiclient import OpenAPIClient
from pipelex.core.memory.working_memory import WorkingMemory
from pipelex.core.stuffs.text_content import TextContent
from pipelex.system.registries.func_registry import pipe_func
from pipelex.tools.misc.json_utils import JsonContent
from posthog import api_key


@pipe_func()
async def get_api_backend_capabilities(working_memory: WorkingMemory) -> TextContent:
    """Given in input a openapi_schema_def_link this can list all the capabilities an OpenAPI defined backend can do."""
    openapi_schema_def_link = working_memory.get_stuff_as_str("openapi_schema_def_link")

    # Initialize the API factory with the OpenAPI definition
    apiClient = OpenAPIClient(definition=openapi_schema_def_link)
    with apiClient.Client() as client:
        print("client.paths", client.paths)
        print("client.functions", client.functions)
        print("client.tools", client.tools)

        return TextContent(text=str(client.operations))

@pipe_func()
async def invoke_function_api_backend(working_memory: WorkingMemory) -> JsonContent:
    """This function can call, given in input a openapi_schema_def_link, function_name, function_parameters and get the result of a specific function listed in the capabilities list of the backend."""
    openapi_schema_def_link = working_memory.get_stuff_as_str("openapi_schema_def_link")
    function_name = working_memory.get_stuff_as_str("function_name")
    function_parameters = json.loads(working_memory.get_stuff_as_str("function_parameters"))

    # Initialize the API factory with the OpenAPI definition
    api = OpenAPIClient(definition=openapi_schema_def_link)
    api.get_operations()

    callable_client = api.AsyncClient()
    api_response = await callable_client(function_name, **function_parameters)
    return JsonContent(api_response['data'])

