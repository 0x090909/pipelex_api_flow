import asyncio

from pipelex.pipelex import Pipelex
from pipelex.pipeline.execute import execute_pipeline

spec_url = '''
https://developer.keap.com/docs/rest/2025-11-05-v1.json
'''

async def run_build_function_info():
    return await execute_pipeline(
        pipe_code="build_function_info",
        inputs={
            "openapi_url": {
                "concept": "openapi_function_builder.OpenAPIURL",
                "content": spec_url,
            },
            "operation_to_accomplish": {
                "concept": "openapi_function_builder.OperationToAccomplish",
                "content": "extract all the contacts with email pincopalla@gmail.com",
            },
        },
    )


if __name__ == "__main__":
    # Initialize Pipelex
    Pipelex.make()

    # Run the pipeline
    result = asyncio.run(run_build_function_info())
