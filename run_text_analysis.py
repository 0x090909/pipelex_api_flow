import asyncio
from pipelex import pretty_print
from pipelex.pipelex import Pipelex
from pipelex.pipeline.execute import execute_pipeline


async def analyze_text():
  pipe_output = await execute_pipeline(
      pipe_code="analyze_text",
      inputs={
          "text": "Hello world! This is a test of PipeFunc."
      },
  )
  return pipe_output.main_stuff_as_str


# Start Pipelex
Pipelex.make()

# Run
result = asyncio.run(analyze_text())
pretty_print(result, title="Text Analysis")
