import asyncio

from pipelex.pipelex import Pipelex
from pipelex.pipeline.execute import execute_pipeline


async def run_get_capabilities():
    return await execute_pipeline(
        pipe_code="retrieve_backend_capabilities",
        inputs={
            "openapi_schema_def_link": "https://developer.keap.com/docs/rest/2025-11-05-v1.json"
        },
    )


if __name__ == "__main__":
    # Initialize Pipelex
    Pipelex.make()

    # Run the pipeline
    result = asyncio.run(run_get_capabilities())
