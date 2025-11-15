# PipeFunc Quick Reference Guide

## TL;DR - Create a Custom PipeFunc

### 1. Import decorator
```python
from pipelex.system.registries.func_registry import pipe_func
from pipelex.core.memory.working_memory import WorkingMemory
from pipelex.core.stuffs.text_content import TextContent
```

### 2. Define and decorate function
```python
@pipe_func()
async def my_function(working_memory: WorkingMemory) -> TextContent:
    """Brief description of what this does."""
    input_data = working_memory.get_stuff_as_str("input_name")
    result = f"Processed: {input_data}"
    return TextContent(text=result)
```

### 3. Use in PLX file
```plx
[pipe.my_pipe]
type = "PipeFunc"
description = "Description of what this pipe does"
inputs = { input_name = "native.Text" }
output = "native.Text"
function_name = "my_function"
```

---

## Function Signature (Non-Negotiable)

```python
@pipe_func()  # Required decorator
async def function_name(working_memory: WorkingMemory) -> ReturnType:
    # Can also be sync (remove async)
    pass
```

### Rules
- Parameter MUST be named `working_memory` (exact spelling)
- Parameter type MUST be `WorkingMemory`
- Return type MUST be annotated (not `-> None`)
- Return type MUST be subclass of `StuffContent`
- Can be sync or async

---

## Common Return Types

| Type | Usage | Example |
|------|-------|---------|
| `TextContent` | Single text output | `return TextContent(text="result")` |
| `ListContent[T]` | Multiple items | `return ListContent(items=[...])` |
| Custom `StructuredContent` | Structured data | `return MyResult(field1=value)` |
| `str` | Auto-converts to TextContent | `return "text"` (converts automatically) |
| `list[StuffContent]` | Auto-converts to ListContent | `return [TextContent(...), ...]` |

---

## Working Memory Access

### Text
```python
text = working_memory.get_stuff_as_str("input_name")  # Returns str
text_content = working_memory.get_stuff_as_text("input_name")  # Returns TextContent
```

### Structured Content
```python
invoice = working_memory.get_stuff_as(name="invoice", content_type=Invoice)
```

### Lists
```python
items = working_memory.get_stuff_as_list("items", item_type=TextContent)
# Access items: items.items (list of items)
for item in items.items:
    process(item)

# Get first item directly
first = working_memory.get_list_stuff_first_item_as("items", item_type=TextContent)
```

### Other Types
```python
image = working_memory.get_stuff_as_image("image")
number = working_memory.get_stuff_as_number("number")
pdf = working_memory.get_stuff_as_pdf("document")
html = working_memory.get_stuff_as_html("page")
```

---

## Common Patterns

### Process List Input
```python
@pipe_func()
async def process_items(working_memory: WorkingMemory) -> ListContent[TextContent]:
    items = working_memory.get_stuff_as_list("items", item_type=TextContent)
    results = []
    for item in items.items:
        result = TextContent(text=f"Processed: {item.text}")
        results.append(result)
    return ListContent(items=results)
```

### Multiple Inputs
```python
@pipe_func()
async def combine(working_memory: WorkingMemory) -> TextContent:
    text = working_memory.get_stuff_as_str("text")
    number = working_memory.get_stuff_as_number("number").number
    return TextContent(text=f"Text: {text}, Number: {number}")
```

### Error Handling
```python
from pipelex.core.memory.exceptions import WorkingMemoryStuffNotFoundError

@pipe_func()
async def safe_process(working_memory: WorkingMemory) -> TextContent:
    try:
        data = working_memory.get_stuff_as_str("input")
    except WorkingMemoryStuffNotFoundError:
        return TextContent(text="Input not found")
    return TextContent(text=f"Processed: {data}")
```

### Async I/O
```python
@pipe_func()
async def fetch_data(working_memory: WorkingMemory) -> TextContent:
    import aiohttp
    url = working_memory.get_stuff_as_str("url")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.text()
    return TextContent(text=content)
```

### Heavy Computation in Async
```python
@pipe_func()
async def compute(working_memory: WorkingMemory) -> TextContent:
    import asyncio
    data = working_memory.get_stuff_as_str("data")
    result = await asyncio.to_thread(heavy_compute, data)
    return TextContent(text=result)

def heavy_compute(data: str) -> str:
    # CPU-intensive work
    return f"Result: {data}"
```

---

## PLX File Definition

```plx
# Minimal
[pipe.my_pipe]
type = "PipeFunc"
description = "What this does"
inputs = { input1 = "native.Text" }
output = "native.Text"
function_name = "my_function"

# With multiple inputs
[pipe.combine_data]
type = "PipeFunc"
description = "Combine text and number"
inputs = { text = "native.Text", number = "native.Number" }
output = "native.Text"
function_name = "combine_inputs"

# With structured content
[pipe.process_invoice]
type = "PipeFunc"
description = "Process invoice"
inputs = { invoice = "billing.Invoice" }
output = "billing.ProcessedInvoice"
function_name = "process_invoice"

# With list output
[pipe.split_text]
type = "PipeFunc"
description = "Split text into words"
inputs = { text = "native.Text" }
output = "native.Text[]"
function_name = "split_words"
```

---

## Troubleshooting

### Error: "Function 'X' not found in registry"
**Cause:** Function not decorated with `@pipe_func()`
**Fix:** Add `@pipe_func()` above your function definition

### Error: "has no return type annotation"
**Cause:** Missing return type hint
**Fix:** Add `-> ReturnType` to function signature

### Error: "return type ... is not a subclass of StuffContent"
**Cause:** Return type doesn't inherit from StuffContent
**Fix:** Return `TextContent`, `ListContent`, or custom `StructuredContent`

### Error: "Exactly 1 parameter named 'working_memory'" expected
**Cause:** Wrong parameter name or count
**Fix:** Use exactly `working_memory: WorkingMemory` as parameter

### Function not discovered during init
**Cause:** File not scanned or import failed
**Fix:** Ensure:
1. Function has `@pipe_func()` decorator
2. File is in project directory (scanned by `register_funcs_in_folder`)
3. No syntax errors in file
4. All imports work

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `pipelex/pipe_operators/func/pipe_func.py` | Core PipeFunc executor |
| `pipelex/system/registries/func_registry.py` | Function registry and decorator |
| `pipelex/core/memory/working_memory.py` | Access pipeline inputs |
| Your `.plx` files | Define pipes that use your functions |

---

## Validation Checklist

Before using your function:

- [ ] Function has `@pipe_func()` decorator
- [ ] Parameter is exactly `working_memory: WorkingMemory`
- [ ] Return type is annotated (e.g., `-> TextContent`)
- [ ] Return type is `StuffContent` subclass or `ListContent`
- [ ] Function is in a scanned directory (your project root)
- [ ] No syntax errors in your Python file
- [ ] All imports in your function work
- [ ] PLX file references correct `function_name`
- [ ] PLX file inputs match what you access in `working_memory`

---

## Real-World Example

**my_functions.py:**
```python
from pipelex.system.registries.func_registry import pipe_func
from pipelex.core.memory.working_memory import WorkingMemory
from pipelex.core.stuffs.text_content import TextContent
from pipelex.core.stuffs.list_content import ListContent

@pipe_func()
async def extract_keywords(working_memory: WorkingMemory) -> ListContent[TextContent]:
    """Extract keywords from text using simple splitting."""
    text = working_memory.get_stuff_as_str("article")
    words = text.split()[:5]  # First 5 words as keywords
    keywords = [TextContent(text=word) for word in words]
    return ListContent(items=keywords)

@pipe_func()
async def format_keywords(working_memory: WorkingMemory) -> TextContent:
    """Format keyword list into CSV."""
    keywords = working_memory.get_stuff_as_list("keywords", item_type=TextContent)
    csv = ", ".join(k.text for k in keywords.items)
    return TextContent(text=csv)
```

**my_pipeline.plx:**
```plx
domain = "text_processing"
description = "Process articles and extract keywords"

[pipe.extract]
type = "PipeFunc"
description = "Extract keywords from article"
inputs = { article = "native.Text" }
output = "native.Text[]"
function_name = "extract_keywords"

[pipe.format]
type = "PipeFunc"
description = "Format keywords as CSV"
inputs = { keywords = "native.Text[]" }
output = "native.Text"
function_name = "format_keywords"

[pipe.main_pipeline]
type = "PipeSequence"
description = "Extract and format keywords"
inputs = { article = "native.Text" }
output = "native.Text"
steps = [
    { pipe = "extract", result = "keywords" },
    { pipe = "format", result = "csv_keywords" }
]
```

