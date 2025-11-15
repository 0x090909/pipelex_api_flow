domain = "openapi_function_builder"
description = "Building function info from OpenAPI JSON spec"
main_pipe = "build_function_info"

[concept]
OpenAPISpec = "Structured OpenAPI specification for the backend."
FunctionInfo = "Information about a function in the OpenAPI spec."
FunctionChoice = "Choice of OpenAPI function to accomplish an operation."

[concept.OpenAPIURL]
description = "The URL of the OpenAPI JSON spec"
refines = "Text"

[concept.OperationToAccomplish]
description = "The specific operation to accomplish."
refines = "Text"

[concept.RelevantOpenapiPaths]
description = """
Relevant information (e.g., paths, methods) from the OpenAPI JSON specification that pertains to the operation to accomplish.
"""

[concept.RelevantOpenapiPaths.structure]
paths = { type = "text", description = "List of relevant paths.", required = true }
methods = { type = "text", description = "List of relevant methods.", required = true }

[concept.FunctionName]
description = "The name of the function."
refines = "Text"

[concept.FunctionParameter]
description = "The necessary function parameters."

[concept.FunctionParameter.structure]
name = { type = "text", description = "Name of a function parameter.", required = true }
type = { type = "text", description = "Data type of a function parameter.", required = true }
value = { type = "text", description = "Values of each function parameter.", required = true }

[concept.ApiResponseResult]
description = "The compiled api response content."

[concept.ApiResponseResult.structure]
response = { type = "text", description = "The response of the api server", required = true }


[pipe.build_function_info]
type = "PipeSequence"
description = """
Main pipeline that builds the function name and function parameters and values necessary for the task based on the OpenAPI JSON spec and the operation to accomplish.
"""
inputs = { openapi_url = "OpenAPIURL", operation_to_accomplish = "OperationToAccomplish" }
# output = "ApiResponseResult"
output = "FunctionDetails"
steps = [
    { pipe = "obtain_api_spec", result = "openapi_spec"},
    { pipe = "extract_available_functions", result = "function_info" },
    { pipe = "choose_function", result = "function_choice" },
    { pipe = "get_function_details", result = "function_details" },
    # { pipe = "execute_api_call", result = "result_api_call" },
]
# [pipe.obtain_api_spec]
# type = "PipeFunc"
# description = "Obtains the OpenAPI spec given a URL."
# inputs = { openapi_url = "OpenAPIURL" }
# output = "OpenapiJsonSpec"
# function_name = "obtain_openapi_spec"

# [pipe.extract_openapi_info]
# type = "PipeLLM"
# description = """
# Extracts relevant information (e.g., paths, methods) from the OpenAPI JSON specification that pertains to the operation to accomplish.
# """
# inputs = { openapi_json_spec = "OpenapiJsonSpec", operation_to_accomplish = "OperationToAccomplish" }
# output = "RelevantOpenapiPaths"
# model = "llm_to_engineer"
# system_prompt = """
# Extract relevant information from the OpenAPI JSON specification that pertains to the operation to accomplish. Provide the information in a structured format.
# """
# prompt = """
# Extract relevant paths and methods from the OpenAPI JSON specification that are related to the operation to accomplish: `$operation_to_accomplish`. Use the OpenAPI JSON specification: `@openapi_json_spec`. Provide the extracted information in a structured format.
# """

# [pipe.determine_function_name]
# type = "PipeLLM"
# description = "Uses the operation to accomplish and relevant OpenAPI paths to determine the function name."
# inputs = { operation_to_accomplish = "OperationToAccomplish", relevant_openapi_info = "RelevantOpenapiPaths" }
# output = "FunctionName"
# model = "llm_to_engineer"
# system_prompt = """
# Determine a function name based on the operation to accomplish and relevant OpenAPI paths. Be concise.
# """
# prompt = """
# Based on the operation `$operation_to_accomplish` and the relevant OpenAPI paths `@relevant_openapi_info`, determine a suitable function name. Provide a single function name.
# """

# [pipe.determine_function_parameters]
# type = "PipeLLM"
# description = "Based on the OpenAPI JSON spec and the operation, identifies the necessary function parameters."
# inputs = { openapi_json_spec = "OpenapiJsonSpec", relevant_openapi_info = "RelevantOpenapiPaths", operation_to_accomplish = "OperationToAccomplish" }
# output = "FunctionParameter[]"
# model = "llm_to_engineer"
# system_prompt = """
# Generate a list of function parameters based on the OpenAPI JSON specification and the operation to accomplish. Be concise and focus on the necessary parameters.
# """
# prompt = """
# Based on the OpenAPI JSON specification `@openapi_json_spec` and the operation `$operation_to_accomplish`, identify the necessary function parameters from the relevant OpenAPI paths `@relevant_openapi_info`. Provide the parameters in a structured format.
# """


# [pipe.compile_function_info]
# type = "PipeLLM"
# description = "Combines the function name and parameters and their values into a usable format."
# inputs = {function_name = "FunctionName", function_parameters = "FunctionParameter[]" }
# output = "CompiledFunctionInfo"
# model = "llm_to_engineer"
# system_prompt = """
# Generate a structured object containing the compiled function information, including the function name and parameters and parameter values."""
# prompt = """
# Create a JSON object with the function name $function_name and parameters "$function_parameters".
# """

[pipe.obtain_api_spec]
type = "PipeFunc"
description = "Obtains the OpenAPI spec given a URL."
inputs = { openapi_url = "OpenAPIURL" }
output = "OpenAPISpec"
function_name = "obtain_openapi_model"

[pipe.extract_available_functions]
type = "PipeFunc"
description = "Extracts the available functions from the OpenAPI spec."
inputs = { openapi_url = "OpenAPIURL" }
output = "FunctionInfo[]"
function_name = "extract_available_functions"


[pipe.choose_function]
type = "PipeLLM"
description = "Uses the operation to accomplish and relevant OpenAPI paths to determine the function name."
inputs = { operation_to_accomplish = "OperationToAccomplish", function_info = "FunctionInfo[]" }
output = "FunctionChoice"
model = "llm_to_engineer"
system_prompt = """
Determine a function name based on the operation to accomplish and relevant OpenAPI paths. Be concise.
"""
prompt = """
Based on the operation to accomplish and the available OpenAPI functions, choose the relevant function name.

@operation_to_accomplish

@function_info
"""

[pipe.get_function_details]
type = "PipeFunc"
description = "Gets the details of a function from the OpenAPI spec."
inputs = { function_choice = "FunctionChoice" }
output = "FunctionDetails"
function_name = "get_function_details"


[pipe.execute_api_call]
type = "PipeFunc"
description = "Execute the API request given a CompiledFunctionInfo."
inputs = { compiled_function_info = "CompiledFunctionInfo" }
output = "ApiResponseResult"
function_name = "invoke_function_api_backend"


