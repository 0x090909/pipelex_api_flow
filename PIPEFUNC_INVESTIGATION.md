# PipeFunc Architecture Investigation Report

## Executive Summary

PipeFunc is a Pipelex pipe operator that allows you to integrate custom Python functions into a pipeline. It provides a flexible way to execute synchronous or asynchronous functions with access to the working memory, making it possible to perform arbitrary Python logic within the pipeline execution flow.

---

## 1. PipeFunc Implementation

### 1.1 PipeFunc Class

**File:** `/Users/cristy/Desktop/Programming/pipelex/pipelex/pipe_operators/func/pipe_func.py`

The `PipeFunc` class (lines 29-175) is the core operator that executes custom functions:

```python
class PipeFunc(PipeOperator[PipeFuncOutput]):
    type: Literal["PipeFunc"] = "PipeFunc"
    function_name: str

    @field_validator("function_name", mode="before")
    @classmethod
    def validate_function_name(cls, function_name: str) -> str:
        function = func_registry.get_function(function_name)
        if not function:
            msg = f"Function '{function_name}' not found in registry"
            raise PipeDefinitionError(msg)
        # Validates return type is StuffContent
        ...
```

### 1.2 Execution Flow

**Method:** `_run_operator_pipe()` (lines 64-106)

The PipeFunc execution handles both sync and async functions:

```python
async def _run_operator_pipe(
    self,
    job_metadata: JobMetadata,
    working_memory: WorkingMemory,
    pipe_run_params: PipeRunParams,
    output_name: str | None = None,
) -> PipeFuncOutput:
    log.verbose(f"Applying function '{self.function_name}'")

    function = func_registry.get_required_function(self.function_name)

    # Handle both async and sync functions
    if asyncio.iscoroutinefunction(function):
        func_output_object = await function(working_memory=working_memory)
    else:
        func_output_object = await asyncio.to_thread(function, working_memory=working_memory)

    # Convert output to StuffContent
    the_content: StuffContent
    if isinstance(func_output_object, StuffContent):
        the_content = func_output_object
    elif isinstance(func_output_object, list):
        func_result_list = cast("list[StuffContent]", func_output_object)
        the_content = ListContent(items=func_result_list)
    elif isinstance(func_output_object, str):
        the_content = TextContent(text=func_output_object)
    else:
        msg = f"Function '{self.function_name}' must return a StuffContent or a list, got {type(func_output_object)}"
        raise TypeError(msg)
```

**Key Points:**
- Handles both sync and async functions transparently
- Accepts three return types: `StuffContent`, `list[StuffContent]`, or `str`
- Converts outputs automatically
- Stores result in working memory as the main stuff

### 1.3 Dry Run Support

**Method:** `_dry_run_operator_pipe()` (lines 108-174)

PipeFunc validates all inputs are present and creates mock content for testing.

---

## 2. Function Registry System

### 2.1 FuncRegistry Implementation

**File:** `/Users/cristy/Desktop/Programming/pipelex/pipelex/system/registries/func_registry.py`

The `FuncRegistry` is a singleton that stores and manages registered functions:

```python
class FuncRegistry(RootModel[FuncRegistryDict]):
    root: FuncRegistryDict = Field(default_factory=dict)
    _logger: logging.Logger = PrivateAttr(logging.getLogger(FUNC_REGISTRY_LOGGER_CHANNEL_NAME))
```

**Global Instance:**
```python
func_registry = FuncRegistry()
```

### 2.2 @pipe_func Decorator

**Location:** Lines 25-59 in `func_registry.py`

The `@pipe_func` decorator marks functions for automatic discovery and registration:

```python
def pipe_func(name: str | None = None) -> Callable[[T], T]:
    """Decorator to mark a function for automatic registration in the func_registry.

    Args:
        name: Optional custom name for registration. If not provided, uses function's __name__

    Returns:
        The decorated function unchanged, but marked for registration

    Example:
        @pipe_func()
        async def my_custom_function(working_memory: WorkingMemory) -> TextContent:
            result = working_memory.get_stuff("input")
            return TextContent(text=f"Processed: {result}")

        @pipe_func(name="custom_name")
        async def another_function(working_memory: WorkingMemory) -> MyContent:
            return MyContent(data="example")
    """

    def decorator(func: T) -> T:
        # Mark the function with the attribute
        setattr(func, PIPE_FUNC_MARKER, True)
        # Store custom name if provided
        if name is not None:
            func._pipe_func_name = name  # type: ignore[attr-defined]
        return func

    return decorator
```

### 2.3 Registration Methods

**Primary Methods:**

| Method | Purpose |
|--------|---------|
| `register_function(func, name=None)` | Register a single function if it meets eligibility criteria (lines 76-90) |
| `register_functions(functions)` | Register multiple functions from a list (lines 113-116) |
| `register_functions_dict(functions)` | Register multiple functions from a dict (lines 108-111) |
| `get_function(name)` | Retrieve a function, returns None if not found (lines 118-120) |
| `get_required_function(name)` | Retrieve a function, raises error if not found (lines 122-132) |
| `has_function(name)` | Check if function is registered (lines 150-152) |
| `is_marked_pipe_func(func)` | Check if function has @pipe_func decorator (lines 154-164) |

### 2.4 Function Eligibility Criteria

**Method:** `is_eligible_function()` (lines 167-238)

A function must meet ALL these criteria to be registered:

1. **Must be callable**
2. **Exactly one parameter** named `"working_memory"` with type `WorkingMemory`
3. **Return type** must be a subclass of `StuffContent` (or generic like `ListContent[SomeType]`)
4. **All type hints must be present** (function signature must include type annotations)

```python
def is_eligible_function(self, func: Any, require_decorator: bool = False) -> bool:
    """Checks if a function matches the criteria for PipeFunc registration:
    - Must be callable
    - Exactly 1 parameter named "working_memory" with type WorkingMemory
    - Return type that is a subclass of StuffContent
    - Optionally must be marked with @pipe_func decorator if require_decorator=True
    """
    if not callable(func):
        return False

    if require_decorator and not self.is_marked_pipe_func(func):
        return False

    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Check parameter count and name
    if len(params) != 1:
        return False

    param = params[0]
    if param.name != "working_memory":
        return False

    # Get type hints
    type_hints = get_type_hints(func)

    # Check parameter type
    if "working_memory" not in type_hints:
        return False

    param_type = type_hints["working_memory"]
    if param_type != WorkingMemory:
        return False

    # Check return type
    if "return" not in type_hints:
        return False

    return_type = type_hints["return"]

    # Check if return type is a subclass of StuffContent
    try:
        if inspect.isclass(return_type) and issubclass(return_type, StuffContent):
            return True
        # Handle generic types like ListContent[SomeType]
        if hasattr(return_type, "__origin__"):
            origin = return_type.__origin__
            if inspect.isclass(origin) and issubclass(origin, StuffContent):
                return True
    except TypeError:
        pass

    return False
```

---

## 3. Custom Function Definition

### 3.1 Function Signature Requirements

All custom PipeFunc functions MUST follow this signature:

```python
async def my_function(working_memory: WorkingMemory) -> SomeStuffContent:
    ...
```

Or for synchronous functions:

```python
def my_function(working_memory: WorkingMemory) -> SomeStuffContent:
    ...
```

**Critical Requirements:**
- Parameter name MUST be exactly `"working_memory"`
- Parameter type MUST be `WorkingMemory` (imported from `pipelex.core.memory.working_memory`)
- Return type MUST be a subclass of `StuffContent` or `ListContent[StuffContent]`
- Function MUST have return type annotation
- Can be synchronous or asynchronous

### 3.2 Valid Return Types

The function can return:

1. **StuffContent subclass** (e.g., `TextContent`, `ImageContent`, `PDFContent`, `NumberContent`)
   ```python
   def process(working_memory: WorkingMemory) -> TextContent:
       return TextContent(text="result")
   ```

2. **ListContent with typed items**
   ```python
   def process(working_memory: WorkingMemory) -> ListContent[TextContent]:
       items = [TextContent(text="item1"), TextContent(text="item2")]
       return ListContent(items=items)
   ```

3. **Custom StructuredContent class**
   ```python
   from pipelex.core.stuffs.structured_content import StructuredContent
   
   class MyResult(StructuredContent):
       field1: str
       field2: int
   
   def process(working_memory: WorkingMemory) -> MyResult:
       return MyResult(field1="value", field2=42)
   ```

4. **List of StuffContent** (converted to ListContent automatically)
   ```python
   def process(working_memory: WorkingMemory) -> list[TextContent]:
       return [TextContent(text="item1"), TextContent(text="item2")]
   ```

5. **String** (converted to TextContent automatically)
   ```python
   def process(working_memory: WorkingMemory) -> str:
       return "result text"
   ```

### 3.3 Registration Pattern

**Step 1: Import decorator**
```python
from pipelex.system.registries.func_registry import pipe_func
```

**Step 2: Decorate function**
```python
@pipe_func()
async def my_function(working_memory: WorkingMemory) -> TextContent:
    # Implementation
    pass
```

**Step 3: Optional - provide custom name**
```python
@pipe_func(name="my_custom_name")
async def my_function(working_memory: WorkingMemory) -> TextContent:
    # Implementation
    pass
```

### 3.4 Real-World Example from Test Suite

**File:** `/Users/cristy/Desktop/Programming/pipelex/tests/unit/pipe_operators/pipe_func/data.py`

```python
@pipe_func(name="process_text")
async def process_text(working_memory: WorkingMemory) -> TextContent:
    """Test function with single text input."""
    input_data = working_memory.get_stuff_as_str("input_data")
    return TextContent(text=f"processed: {input_data}")


@pipe_func(name="combine_data")
async def combine_data(working_memory: WorkingMemory) -> TextContent:
    """Test function with multiple inputs."""
    text_input = working_memory.get_stuff_as_str("text_input")
    number_input = working_memory.get_stuff_as_number("number_input")
    return TextContent(text=f"combined: {text_input} and {number_input}")
```

### 3.5 File Reading Example

**File:** `/Users/cristy/Desktop/Programming/pipelex/tests/test_pipelines/test_file_func_registry.py` (lines 22-46)

```python
@pipe_func()
def read_file_content(working_memory: WorkingMemory) -> ListContent[CodebaseFileContent]:
    """Read the content of related codebase files.

    Args:
        working_memory: Working memory containing related_file_paths

    Returns:
        ListContent of CodebaseFileContent objects
    """
    file_paths_list = working_memory.get_stuff_as_list("related_file_paths", item_type=FilePath)

    codebase_files: list[CodebaseFileContent] = []
    for file_path in file_paths_list.items:
        try:
            with open(file_path.path, encoding="utf-8") as file:
                content = file.read()
                codebase_files.append(CodebaseFileContent(file_path=file_path.path, file_content=content))
        except Exception as e:
            codebase_files.append(
                CodebaseFileContent(file_path=file_path.path, file_content=f"# File not found or unreadable: {file_path.path}\n# Error: {e!s}"),
            )

    return ListContent[CodebaseFileContent](items=codebase_files)
```

---

## 4. Working Memory Access

### 4.1 WorkingMemory Class Overview

**File:** `/Users/cristy/Desktop/Programming/pipelex/pipelex/core/memory/working_memory.py`

The `WorkingMemory` class provides access to pipeline inputs and intermediate results:

```python
class WorkingMemory(BaseModel, ContextProviderAbstract):
    root: StuffDict = Field(default_factory=dict)
    aliases: dict[str, str] = Field(default_factory=dict)
```

### 4.2 Core Accessor Methods

#### Get Stuff (Generic)

```python
def get_stuff(self, name: str) -> Stuff:
    """Get a stuff by name. Raises WorkingMemoryStuffNotFoundError if not found."""
    
def get_optional_stuff(self, name: str) -> Stuff | None:
    """Get a stuff by name. Returns None if not found."""
```

#### Typed Content Accessors

| Method | Returns | Notes |
|--------|---------|-------|
| `get_stuff_as_str(name)` | `str` | Extracts text from TextContent |
| `get_stuff_as_text(name)` | `TextContent` | Raw TextContent |
| `get_stuff_as_image(name)` | `ImageContent` | Raw ImageContent |
| `get_stuff_as_pdf(name)` | `PDFContent` | Raw PDFContent |
| `get_stuff_as_number(name)` | `NumberContent` | Raw NumberContent |
| `get_stuff_as_html(name)` | `HtmlContent` | Raw HtmlContent |
| `get_stuff_as_mermaid(name)` | `MermaidContent` | Raw MermaidContent |
| `get_stuff_as_text_and_image(name)` | `TextAndImagesContent` | Text and images together |

#### List Accessors

```python
def get_stuff_as_list(self, name: str, item_type: type[StuffContentType]) -> ListContent[StuffContentType]:
    """Get stuff content as ListContent with items of specific type.
    
    Args:
        name: Name of the stuff
        item_type: Type of items in the list (e.g., TextContent, MyStructuredContent)
    
    Returns:
        ListContent with items of specified type
    """

def get_list_stuff_first_item_as(self, name: str, item_type: type[StuffContentType]) -> StuffContentType:
    """Get the first item from a list."""
```

#### Generic Type Accessor

```python
def get_stuff_as(self, name: str, content_type: type[StuffContentType]) -> StuffContentType:
    """Get stuff content as a specific type (useful for StructuredContent)."""
```

### 4.3 Practical Usage Examples

**Get simple text input:**
```python
@pipe_func()
async def process(working_memory: WorkingMemory) -> TextContent:
    text = working_memory.get_stuff_as_str("input_text")
    return TextContent(text=f"Processed: {text}")
```

**Get structured content:**
```python
@pipe_func()
async def process(working_memory: WorkingMemory) -> TextContent:
    invoice = working_memory.get_stuff_as(name="invoice", content_type=Invoice)
    return TextContent(text=f"Invoice total: {invoice.total_amount}")
```

**Get list of items:**
```python
@pipe_func()
async def process(working_memory: WorkingMemory) -> ListContent[ProcessedItem]:
    items = working_memory.get_stuff_as_list("items", item_type=Item)
    
    processed = []
    for item in items.items:
        processed.append(ProcessedItem(value=item.value * 2))
    
    return ListContent(items=processed)
```

**Get first item from list:**
```python
@pipe_func()
async def process(working_memory: WorkingMemory) -> TextContent:
    first_item = working_memory.get_list_stuff_first_item_as("items", item_type=TextContent)
    return TextContent(text=f"First: {first_item.text}")
```

### 4.4 Error Handling

Working memory operations can raise exceptions:

```python
from pipelex.core.memory.exceptions import (
    WorkingMemoryStuffNotFoundError,
    WorkingMemoryTypeError,
    WorkingMemoryStuffAttributeNotFoundError,
)

@pipe_func()
async def safe_process(working_memory: WorkingMemory) -> TextContent:
    try:
        data = working_memory.get_stuff_as_str("input")
    except WorkingMemoryStuffNotFoundError as e:
        return TextContent(text=f"Input not found: {e}")
    except WorkingMemoryTypeError as e:
        return TextContent(text=f"Type mismatch: {e}")
    
    return TextContent(text=f"Processed: {data}")
```

---

## 5. Function Discovery and Auto-Registration

### 5.1 FuncRegistryUtils

**File:** `/Users/cristy/Desktop/Programming/pipelex/pipelex/system/registries/func_registry_utils.py`

#### Package-Based Discovery

```python
@classmethod
def register_pipe_funcs_from_package(cls, package_name: str, package: Any) -> int:
    """Register all @pipe_func decorated functions from a package.

    Args:
        package_name: Full name of the package (e.g. "pipelex.builder")
        package: The imported package object

    Returns:
        Number of functions registered
    """
```

**Usage:**
```python
from pipelex.system.registries.func_registry_utils import FuncRegistryUtils
import pipelex.builder

functions_count = FuncRegistryUtils.register_pipe_funcs_from_package(
    "pipelex.builder", 
    pipelex.builder
)
```

#### Folder-Based Discovery

```python
@classmethod
def register_funcs_in_folder(
    cls,
    folder_path: str,
    is_recursive: bool = True,
) -> None:
    """Discovers and attempts to register all functions in Python files within a folder.
    
    Only functions marked with @pipe_func decorator are registered.
    Uses AST parsing to avoid importing files that don't contain @pipe_func functions.
    
    Args:
        folder_path: Path to folder containing Python files
        is_recursive: Whether to search recursively in subdirectories
    """
```

**Usage:**
```python
FuncRegistryUtils.register_funcs_in_folder(folder_path="/path/to/project", is_recursive=True)
```

### 5.2 Automatic Initialization in Pipelex

**File:** `/Users/cristy/Desktop/Programming/pipelex/pipelex/libraries/library_manager.py` (lines 242-331)

When Pipelex initializes:

1. **Direct imports** of pipelex.builder for critical functions:
   ```python
   def _import_pipelex_modules_directly(self) -> None:
       import pipelex.builder
       functions_count = FuncRegistryUtils.register_pipe_funcs_from_package("pipelex.builder", pipelex.builder)
   ```

2. **Folder scanning** for user-defined functions:
   ```python
   # Only import files that contain @pipe_func decorated functions (uses AST pre-check)
   FuncRegistryUtils.register_funcs_in_folder(folder_path=str(library_dir))
   ```

3. **Verification** of critical functions:
   ```python
   critical_functions = ["create_concept_spec", "assemble_pipelex_bundle_spec"]
   for func_name in critical_functions:
       if func_registry.has_function(func_name):
           log.verbose(f"✓ Function '{func_name}' successfully registered")
       else:
           log.error(f"✗ Function '{func_name}' NOT registered - this will cause errors!")
   ```

### 5.3 Smart AST-Based Pre-Checking

The discovery process uses AST (Abstract Syntax Tree) parsing to:

1. **Avoid unnecessary imports** - Only imports files that contain `@pipe_func` decorators
2. **Handle import errors gracefully** - Skips files with missing dependencies or circular imports
3. **Detect syntax errors early** - Warns about invalid Python code

---

## 6. PipeFunc Definition in PLX Files

### 6.1 PLX Syntax

**File:** CLAUDE.md (PipeFunc Operator section)

PipeFunc is defined in `.plx` files using TOML syntax:

```plx
[pipe.process_data]
type = "PipeFunc"
description = "Process data using custom function"
inputs = { input_data = "DataType" }
output = "ProcessedData"
function_name = "process_data_function"
```

### 6.2 Blueprint Definition

**File:** `/Users/cristy/Desktop/Programming/pipelex/pipelex/pipe_operators/func/pipe_func_blueprint.py`

```python
class PipeFuncBlueprint(PipeBlueprint):
    type: Literal["PipeFunc"] = "PipeFunc"
    pipe_category: Literal["PipeOperator"] = "PipeOperator"
    function_name: str = Field(description="The name of the function to call.")
```

### 6.3 Factory

**File:** `/Users/cristy/Desktop/Programming/pipelex/pipelex/pipe_operators/func/pipe_func_factory.py`

```python
class PipeFuncFactory(PipeFactoryProtocol[PipeFuncBlueprint, PipeFunc]):
    @classmethod
    def make_from_blueprint(
        cls,
        domain: str,
        pipe_code: str,
        blueprint: PipeFuncBlueprint,
        concept_codes_from_the_same_domain: list[str] | None = None,
    ) -> PipeFunc:
        # Validates function_name exists in registry during instantiation
```

---

## 7. Existing Examples

### 7.1 Test Function Examples

**File:** `/Users/cristy/Desktop/Programming/pipelex/tests/unit/pipe_operators/pipe_func/data.py`

```python
# No inputs
@pipe_func(name="my_function")
async def my_function(working_memory: WorkingMemory) -> TextContent:
    return TextContent(text="test output")

# Single input
@pipe_func(name="process_text")
async def process_text(working_memory: WorkingMemory) -> TextContent:
    input_data = working_memory.get_stuff_as_str("input_data")
    return TextContent(text=f"processed: {input_data}")

# Multiple inputs
@pipe_func(name="combine_data")
async def combine_data(working_memory: WorkingMemory) -> TextContent:
    text_input = working_memory.get_stuff_as_str("text_input")
    number_input = working_memory.get_stuff_as_number("number_input")
    return TextContent(text=f"combined: {text_input} and {number_input}")

# Image input
@pipe_func(name="process_image")
async def process_image(working_memory: WorkingMemory) -> TextContent:
    image = working_memory.get_stuff_as_image("image")
    return TextContent(text=f"processed image: {image.url}")
```

### 7.2 Builder Functions

**File:** `/Users/cristy/Desktop/Programming/pipelex/pipelex/builder/builder.py`

```python
@pipe_func()
async def assemble_pipelex_bundle_spec(working_memory: WorkingMemory) -> PipelexBundleSpec:
    """Construct a PipelexBundleSpec from working memory containing concept and pipe blueprints."""
    try:
        concept_specs = working_memory.get_stuff_as_list(
            name="concept_specs",
            item_type=ConceptSpec,
        )
    except StuffContentTypeError as exc:
        msg = f"assemble_pipelex_bundle_spec: Failed to get concept specs: {exc}."
        raise PipeBuilderError(message=msg, working_memory=working_memory) from exc

    try:
        pipe_specs_list: ListContent[StuffContent] = working_memory.get_stuff_as_list(
            name="pipe_specs", 
            item_type=StructuredContent
        )
    except StuffContentTypeError as exc:
        msg = f"assemble_pipelex_bundle_spec: Failed to get pipe specs: {exc}."
        raise PipeBuilderError(message=msg, working_memory=working_memory) from exc
    
    # Process and return result
    ...
```

### 7.3 List Processing Example

**File:** `/Users/cristy/Desktop/Programming/pipelex/tests/integration/pipelex/pipes/test_bracket_notation_operators.py` (lines 20-28)

```python
@pipe_func(name="process_function")
async def process_function(working_memory: WorkingMemory) -> ListContent[TextContent]:
    """Test function that processes items and returns a list."""
    items = working_memory.get_stuff_as_list(name="two_texts", item_type=TextContent).items
    processed_items = [TextContent(text=f"processed: {item.text}") for item in items]
    return ListContent(items=processed_items)
```

---

## 8. Best Practices and Patterns

### 8.1 Error Handling

**Pattern 1: Try/Except with WorkingMemory exceptions**
```python
from pipelex.core.memory.exceptions import WorkingMemoryStuffNotFoundError, WorkingMemoryTypeError

@pipe_func()
async def robust_process(working_memory: WorkingMemory) -> TextContent:
    try:
        data = working_memory.get_stuff_as_str("required_input")
    except WorkingMemoryStuffNotFoundError:
        return TextContent(text="Error: required_input not found")
    except WorkingMemoryTypeError:
        return TextContent(text="Error: required_input is not text")
    
    return TextContent(text=f"Processed: {data}")
```

**Pattern 2: Custom exceptions with context**
```python
@pipe_func()
async def safe_compute(working_memory: WorkingMemory) -> TextContent:
    try:
        values = working_memory.get_stuff_as_list("numbers", item_type=NumberContent)
        total = sum(v.number for v in values.items)
        return TextContent(text=f"Sum: {total}")
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Computation failed: {e}", exc_info=True)
        return TextContent(text=f"Computation error: {str(e)}")
```

### 8.2 Type Hints and Validation

**Good Practice:**
```python
from typing import cast
from pipelex.core.stuffs.list_content import ListContent

@pipe_func()
async def typed_process(working_memory: WorkingMemory) -> ListContent[TextContent]:
    # Explicit type hints for clarity
    items_list: ListContent[TextContent] = working_memory.get_stuff_as_list(
        name="texts",
        item_type=TextContent
    )
    
    processed: list[TextContent] = [
        TextContent(text=f"Item: {item.text}")
        for item in items_list.items
    ]
    
    return ListContent(items=processed)
```

### 8.3 Function Naming

**Best Practice:**
- Use descriptive names that indicate what the function does
- Use snake_case for Python functions
- Optionally provide a custom registration name for PLX compatibility

```python
@pipe_func(name="extract_keywords")  # Custom name for PLX
async def extract_keywords_from_text(working_memory: WorkingMemory) -> ListContent[TextContent]:
    """Extract keywords from input text using NLP."""
    ...
```

### 8.4 Documentation

**Best Practice:**
```python
@pipe_func()
async def my_function(working_memory: WorkingMemory) -> MyResult:
    """Brief description of what the function does.
    
    Longer description if needed, explaining:
    - What inputs it expects from working memory
    - What it returns
    - Any side effects or special behavior
    
    Args:
        working_memory: Working memory containing:
            - input_name: Description of input
    
    Returns:
        MyResult: Description of output
    
    Raises:
        SomeException: When something specific happens
    """
    ...
```

### 8.5 Working with StructuredContent

**Pattern:**
```python
from pipelex.core.stuffs.structured_content import StructuredContent
from pydantic import Field

class Invoice(StructuredContent):
    """An invoice with validation."""
    invoice_number: str = Field(description="Invoice ID")
    total_amount: float = Field(ge=0, description="Total amount")

class ProcessedInvoice(StructuredContent):
    """Result of invoice processing."""
    original_invoice_number: str
    status: str
    processed_at: str

@pipe_func()
async def process_invoice(working_memory: WorkingMemory) -> ProcessedInvoice:
    """Process an invoice."""
    invoice = working_memory.get_stuff_as(name="invoice", content_type=Invoice)
    
    # Process
    result = ProcessedInvoice(
        original_invoice_number=invoice.invoice_number,
        status="processed",
        processed_at="2024-01-01"
    )
    
    return result
```

### 8.6 Async Best Practices

**Pattern 1: Pure async operations**
```python
@pipe_func()
async def async_operation(working_memory: WorkingMemory) -> TextContent:
    """Perform async I/O operation."""
    import aiohttp
    
    url = working_memory.get_stuff_as_str("url")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.text()
    
    return TextContent(text=content)
```

**Pattern 2: Mixed sync/async (avoid blocking)**
```python
@pipe_func()
async def mixed_operation(working_memory: WorkingMemory) -> TextContent:
    """Use asyncio to run sync operations without blocking."""
    import asyncio
    
    data = working_memory.get_stuff_as_str("data")
    
    # Run CPU-intensive operation in thread pool
    result = await asyncio.to_thread(expensive_computation, data)
    
    return TextContent(text=result)

def expensive_computation(data: str) -> str:
    """Sync function doing heavy computation."""
    # CPU-intensive work
    return f"Computed: {data}"
```

---

## 9. Gotchas and Important Considerations

### 9.1 Critical Issues

**Issue 1: Missing @pipe_func Decorator**
```python
# WRONG - Will not be registered
async def my_function(working_memory: WorkingMemory) -> TextContent:
    return TextContent(text="test")

# RIGHT - Will be discovered and registered
@pipe_func()
async def my_function(working_memory: WorkingMemory) -> TextContent:
    return TextContent(text="test")
```

Error Message:
```
Function 'my_function' not found in registry. Since v0.12.0, custom functions 
require the @pipe_func() decorator for auto-discovery. Add @pipe_func() above 
your function definition.
```

**Issue 2: Wrong Parameter Name**
```python
# WRONG - Parameter must be named "working_memory"
@pipe_func()
async def my_function(wm: WorkingMemory) -> TextContent:
    return TextContent(text="test")

# RIGHT
@pipe_func()
async def my_function(working_memory: WorkingMemory) -> TextContent:
    return TextContent(text="test")
```

**Issue 3: Missing Type Annotations**
```python
# WRONG - Missing type hints
@pipe_func()
async def my_function(working_memory):
    return TextContent(text="test")

# WRONG - Missing return type
@pipe_func()
async def my_function(working_memory: WorkingMemory):
    return TextContent(text="test")

# RIGHT - All type hints present
@pipe_func()
async def my_function(working_memory: WorkingMemory) -> TextContent:
    return TextContent(text="test")
```

**Issue 4: Wrong Return Type**
```python
# WRONG - Returns str instead of StuffContent
@pipe_func()
async def my_function(working_memory: WorkingMemory) -> str:
    return "test"

# RIGHT - Returns StuffContent
@pipe_func()
async def my_function(working_memory: WorkingMemory) -> TextContent:
    return TextContent(text="test")
```

### 9.2 Performance Considerations

**Issue 1: Blocking Operations in Async Functions**
```python
# INEFFICIENT - Blocking in async context
@pipe_func()
async def bad_async(working_memory: WorkingMemory) -> TextContent:
    # This blocks the event loop!
    import time
    time.sleep(5)
    return TextContent(text="done")

# BETTER - Use asyncio.to_thread for sync work
@pipe_func()
async def good_async(working_memory: WorkingMemory) -> TextContent:
    import asyncio
    result = await asyncio.to_thread(blocking_work)
    return TextContent(text=result)

def blocking_work() -> str:
    import time
    time.sleep(5)
    return "done"
```

**Issue 2: Memory Management with Large Lists**
```python
# INEFFICIENT - Loading entire list into memory
@pipe_func()
async def inefficient(working_memory: WorkingMemory) -> ListContent[TextContent]:
    items = working_memory.get_stuff_as_list("huge_list", item_type=TextContent)
    # Process all at once
    result = [process(item) for item in items.items]
    return ListContent(items=result)

# BETTER - Stream or batch process
@pipe_func()
async def efficient(working_memory: WorkingMemory) -> ListContent[TextContent]:
    items = working_memory.get_stuff_as_list("huge_list", item_type=TextContent)
    result = []
    for item in items.items:
        result.append(process(item))
        # Could add batching logic here
    return ListContent(items=result)
```

### 9.3 Registration Timing

**Issue:** Functions must be registered before they're referenced in PLX files.

**Solution:** Ensure Pipelex initialization includes your functions:

```python
from pipelex.pipelex import Pipelex
from pipelex.system.registries.func_registry_utils import FuncRegistryUtils

# Initialize Pipelex
Pipelex.make()

# OR manually register functions if needed
FuncRegistryUtils.register_funcs_in_folder("/path/to/your/functions")

# Then execute pipelines
```

---

## 10. Summary Table

| Aspect | Details |
|--------|---------|
| **Class** | `PipeFunc` in `pipelex/pipe_operators/func/pipe_func.py` |
| **Registry** | `func_registry` in `pipelex/system/registries/func_registry.py` |
| **Decorator** | `@pipe_func()` - Required for auto-discovery |
| **Parameter** | Exactly one: `working_memory: WorkingMemory` |
| **Return Types** | `StuffContent`, `ListContent[StuffContent]`, `list[StuffContent]`, `str` |
| **Async Support** | Yes - Both sync and async functions supported |
| **Execution** | Sync functions run in thread pool, async functions awaited directly |
| **Discovery** | Auto-discovered via AST scanning in `load_libraries()` |
| **Error Handling** | Validation at registration time and pipe instantiation time |
| **Testing** | Test fixtures in `tests/unit/pipe_operators/pipe_func/` |

---

## 11. File Locations Quick Reference

| Component | File Path |
|-----------|-----------|
| PipeFunc Implementation | `/Users/cristy/Desktop/Programming/pipelex/pipelex/pipe_operators/func/pipe_func.py` |
| Function Registry | `/Users/cristy/Desktop/Programming/pipelex/pipelex/system/registries/func_registry.py` |
| Registry Utils | `/Users/cristy/Desktop/Programming/pipelex/pipelex/system/registries/func_registry_utils.py` |
| PipeFunc Blueprint | `/Users/cristy/Desktop/Programming/pipelex/pipelex/pipe_operators/func/pipe_func_blueprint.py` |
| PipeFunc Factory | `/Users/cristy/Desktop/Programming/pipelex/pipelex/pipe_operators/func/pipe_func_factory.py` |
| WorkingMemory | `/Users/cristy/Desktop/Programming/pipelex/pipelex/core/memory/working_memory.py` |
| Test Data | `/Users/cristy/Desktop/Programming/pipelex/tests/unit/pipe_operators/pipe_func/data.py` |
| Test Suite | `/Users/cristy/Desktop/Programming/pipelex/tests/unit/pipe_operators/pipe_func/test_pipe_func_input.py` |
| Test Registry | `/Users/cristy/Desktop/Programming/pipelex/tests/unit/tools/test_func_registry.py` |
| Library Manager | `/Users/cristy/Desktop/Programming/pipelex/pipelex/libraries/library_manager.py` |

