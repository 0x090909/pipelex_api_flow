import inspect
import json
from typing import Any, Dict, List, Optional

import requests
from openapiclient import OpenAPIClient
from pipelex.core.memory.working_memory import WorkingMemory
from pipelex.core.stuffs.list_content import ListContent
from pipelex.core.stuffs.structured_content import StructuredContent
from pipelex.core.stuffs.text_content import TextContent
from pipelex.system.registries.func_registry import pipe_func
from pydantic import BaseModel, Field


class FunctionParameter(StructuredContent):
    name: str = Field(description="parameter name")
    value: str = Field(description="parameter value")
    type: str = Field(description="parameter type")


# OpenAPI Specification Models
class OpenAPIParameter(BaseModel):
    name: str
    in_: str = Field(alias="in")
    required: Optional[bool] = False
    description: Optional[str] = None
    schema_: Optional[Dict[str, Any]] = Field(default=None, alias="schema")


class OpenAPIRequestBody(BaseModel):
    description: Optional[str] = None
    required: Optional[bool] = False
    content: Optional[Dict[str, Any]] = None


class OpenAPIResponse(BaseModel):
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None


class OpenAPIOperation(BaseModel):
    operationId: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[List[OpenAPIParameter]] = None
    requestBody: Optional[OpenAPIRequestBody] = None
    responses: Optional[Dict[str, OpenAPIResponse]] = None
    tags: Optional[List[str]] = None


class OpenAPIPathItem(BaseModel):
    get: Optional[OpenAPIOperation] = None
    post: Optional[OpenAPIOperation] = None
    put: Optional[OpenAPIOperation] = None
    delete: Optional[OpenAPIOperation] = None
    patch: Optional[OpenAPIOperation] = None
    options: Optional[OpenAPIOperation] = None
    head: Optional[OpenAPIOperation] = None


class OpenAPIInfo(BaseModel):
    title: str
    version: str
    description: Optional[str] = None


class OpenAPISpec(StructuredContent):
    openapi: str = Field(description="OpenAPI version")
    info: OpenAPIInfo = Field(description="API metadata")
    paths: Dict[str, OpenAPIPathItem] = Field(description="API endpoints")
    components: Optional[Dict[str, Any]] = Field(
        default=None, description="Reusable components"
    )
    servers: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="API servers"
    )


class FunctionInfo(StructuredContent):
    function_name: str = Field(description="The operation ID / function name")
    description: Optional[str] = Field(default=None, description="Function description")


class FunctionChoice(StructuredContent):
    explanation: str = Field(description="Explanation of the choice.")
    function_name: str = Field(description="Name of the function.")


class ParameterDetail(StructuredContent):
    """Detailed parameter information for API calls"""

    name: str = Field(description="Parameter name")
    param_in: str = Field(
        description="Where the parameter goes: path, query, header, cookie"
    )
    required: bool = Field(
        default=False, description="Whether the parameter is required"
    )
    param_type: Optional[str] = Field(default=None, description="Parameter data type")
    description: Optional[str] = Field(
        default=None, description="Parameter description"
    )
    default: Optional[Any] = Field(default=None, description="Default value if any")


class FunctionDetails(StructuredContent):
    """Complete details needed to make an API request"""

    function_name: str = Field(description="The operation ID / function name")
    http_method: str = Field(description="HTTP method (GET, POST, PUT, DELETE, etc.)")
    path: str = Field(description="API endpoint path")
    description: Optional[str] = Field(
        default=None, description="Operation description"
    )
    parameters: List[ParameterDetail] = Field(
        default_factory=list, description="List of parameters"
    )
    request_body_required: bool = Field(
        default=False, description="Whether a request body is required"
    )
    request_body_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Request body schema if applicable"
    )
    tags: Optional[List[str]] = Field(default=None, description="Operation tags")


class RequestDetails(StructuredContent):
    """Holds the actual parameter values needed to make an API request"""

    function_name: str = Field(description="The operation ID / function name")
    http_method: str = Field(description="HTTP method (GET, POST, PUT, DELETE, etc.)")
    path: str = Field(description="API endpoint path")
    query_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Query parameters and their values"
    )
    path_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Path parameters and their values"
    )
    header_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Header parameters and their values"
    )
    cookie_parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Cookie parameters and their values"
    )
    request_body: Optional[Dict[str, Any]] = Field(
        default=None, description="Request body data if applicable"
    )


@pipe_func()
async def invoke_function_api_backend(working_memory: WorkingMemory) -> TextContent:
    openapi_url = working_memory.get_stuff_as_text("openapi_url").text.strip()
    function_name_text = working_memory.get_stuff_as_text("function_name").text
    function_name = function_name_text.strip("`")
    function_parameters = working_memory.get_stuff_as(
        "function_parameters", ListContent
    )

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
        print(f"Invoking desired function: {function_name}")
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
        if "paths" in spec_data:
            for path, methods in spec_data["paths"].items():
                for method, operation in methods.items():
                    if method.lower() not in [
                        "get",
                        "post",
                        "put",
                        "delete",
                        "patch",
                        "options",
                        "head",
                    ]:
                        continue

                    operation_id = operation.get("operationId")
                    if not operation_id:
                        continue

                    params = []

                    # Extract parameters
                    if "parameters" in operation:
                        for param in operation["parameters"]:
                            param_name = param.get("name", "unknown")
                            param_required = param.get("required", False)

                            if param_required:
                                params.append(f"{param_name}")
                            else:
                                params.append(f"{param_name}=None")

                    # Check for request body
                    if "requestBody" in operation:
                        params.append("body=" + json.dumps(operation["requestBody"]))

                    params_str = ", ".join(params) if params else ""
                    functions_detail.append(f"{operation_id}({params_str})")

        # Fallback: just list function names
        if not functions_detail:
            for func_name in client.functions.keys():
                functions_detail.append(f"{func_name}(**kwargs)")

        functions_text = "\n".join(functions_detail)
        spec = f"\n\nAvailable functions:\n{functions_text}"

    return TextContent(text=spec)


@pipe_func()
async def obtain_openapi_model(working_memory: WorkingMemory) -> OpenAPISpec:
    """
    Fetch and parse OpenAPI specification into a structured Pydantic model.

    Returns:
        OpenAPISpec: Structured representation of the OpenAPI specification
    """
    openapi_url = working_memory.get_stuff_as_text("openapi_url").text.strip()
    response = requests.get(url=openapi_url)
    spec_data = response.json()

    # Parse the raw JSON into our Pydantic model
    # The model will validate and structure the data
    openapi_spec = OpenAPISpec(**spec_data)

    return openapi_spec


@pipe_func()
async def extract_available_functions(
    working_memory: WorkingMemory,
) -> ListContent[FunctionInfo]:
    """
    Extract available functions from OpenAPI spec as a list of FunctionInfo objects.

    Returns:
        ListContent: List of FunctionInfo objects with function_name and description
    """
    openapi_url = working_memory.get_stuff_as_text("openapi_url").text.strip()
    response = requests.get(url=openapi_url)
    spec_data = response.json()

    functions: List[FunctionInfo] = []

    # Parse the OpenAPI spec to extract function names and descriptions
    if "paths" in spec_data:
        for path, methods in spec_data["paths"].items():
            for method, operation in methods.items():
                if method.lower() not in [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "options",
                    "head",
                ]:
                    continue

                operation_id = operation.get("operationId")
                if not operation_id:
                    continue

                # Get description from summary or description field
                description = operation.get("summary") or operation.get("description")

                functions.append(
                    FunctionInfo(function_name=operation_id, description=description)
                )

    # Convert to ListContent with FunctionInfo items
    return ListContent(items=functions)


@pipe_func()
async def get_function_details(working_memory: WorkingMemory) -> FunctionDetails:
    """
    Get detailed information about a specific function from the OpenAPI spec.
    This includes HTTP method, path, parameters, and request body schema.

    Returns:
        FunctionDetails: Complete details needed to make the API request
    """
    # Get the structured OpenAPISpec from working memory
    openapi_spec = working_memory.get_stuff_as("openapi_spec", OpenAPISpec)
    function_choice = working_memory.get_stuff_as("function_choice", FunctionChoice)
    function_name = function_choice.function_name

    # Search for the function in the OpenAPI spec
    for path, path_item in openapi_spec.paths.items():
        # Check each HTTP method
        for method_name in ["get", "post", "put", "delete", "patch", "options", "head"]:
            operation = getattr(path_item, method_name, None)

            if operation and operation.operationId == function_name:
                # Found the function! Extract all details
                parameters: List[ParameterDetail] = []

                # Extract parameters from the structured model
                if operation.parameters:
                    for param in operation.parameters:
                        param_type = None
                        param_default = None
                        if param.schema_:
                            param_type = param.schema_.get("type")
                            param_default = param.schema_.get("default")

                        parameters.append(
                            ParameterDetail(
                                name=param.name,
                                param_in=param.in_,
                                required=param.required or False,
                                param_type=param_type,
                                description=param.description,
                                default=param_default,
                            )
                        )

                # Extract request body information
                request_body_required = False
                request_body_schema = None
                if operation.requestBody:
                    request_body_required = operation.requestBody.required or False
                    request_body_schema = operation.requestBody.content

                # Get description (prefer summary over description)
                description = operation.summary or operation.description

                # Get tags
                tags = operation.tags

                return FunctionDetails(
                    function_name=function_name,
                    http_method=method_name.upper(),
                    path=path,
                    description=description,
                    parameters=parameters,
                    request_body_required=request_body_required,
                    request_body_schema=request_body_schema,
                    tags=tags,
                )

    # Function not found
    raise ValueError(f"Function '{function_name}' not found in OpenAPI specification")
