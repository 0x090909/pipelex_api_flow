# PipeFunc Documentation

This directory contains comprehensive documentation for understanding and implementing PipeFunc in Pipelex.

## Documents Included

### 1. PIPEFUNC_QUICK_REFERENCE.md (309 lines, 8.6 KB)
**For:** Developers who want to quickly implement a PipeFunc
- TL;DR - Get started in 3 steps
- Function signature rules (non-negotiable requirements)
- Common return types with examples
- Working memory access patterns
- Common code patterns (error handling, async, lists, etc.)
- PLX file syntax examples
- Troubleshooting guide
- Validation checklist

**Start here if:** You just need to write a function and get it working

---

### 2. PIPEFUNC_INVESTIGATION.md (1053 lines, 33 KB)
**For:** Developers who want to deeply understand PipeFunc architecture
- PipeFunc class implementation (execution flow, dry-run support)
- Function Registry System (registration methods, eligibility criteria)
- Custom function definition requirements and patterns
- Working memory access (all accessor methods, error handling)
- Function discovery and auto-registration mechanism
- PipeFunc definition in PLX files
- Existing real-world examples
- Best practices and design patterns
- Gotchas and important considerations
- Complete file location reference

**Start here if:** You want to understand how PipeFunc works internally, or solve complex integration issues

---

## Quick Navigation

### I want to...
- **Create a simple PipeFunc** → Read PIPEFUNC_QUICK_REFERENCE.md (TL;DR section)
- **Process a list of items** → PIPEFUNC_QUICK_REFERENCE.md (Common Patterns section)
- **Handle errors gracefully** → PIPEFUNC_QUICK_REFERENCE.md (Error Handling pattern)
- **Understand the architecture** → PIPEFUNC_INVESTIGATION.md (Sections 1-2)
- **See examples** → PIPEFUNC_INVESTIGATION.md (Section 7)
- **Debug registration issues** → PIPEFUNC_INVESTIGATION.md (Sections 5, 9)
- **Learn best practices** → PIPEFUNC_INVESTIGATION.md (Section 8)
- **Check file locations** → PIPEFUNC_INVESTIGATION.md (Section 11)

---

## The Essence of PipeFunc

**PipeFunc allows you to execute custom Python functions within Pipelex pipelines.**

```python
# 1. Create function with @pipe_func() decorator
@pipe_func()
async def my_function(working_memory: WorkingMemory) -> TextContent:
    text = working_memory.get_stuff_as_str("input")
    return TextContent(text=f"Processed: {text}")

# 2. Use in PLX file
[pipe.my_pipe]
type = "PipeFunc"
inputs = { input = "native.Text" }
output = "native.Text"
function_name = "my_function"
```

---

## Function Signature (Critical Rules)

```python
@pipe_func()  # ← Required decorator
async def name(working_memory: WorkingMemory) -> StuffContent:
    # ↑ Exactly this parameter name
    # ↑ Must be WorkingMemory
    # ↑ Async OR sync (both supported)
    # ↑ MUST have return type annotation
    # ↑ MUST inherit from StuffContent
```

---

## Key Concepts

| Concept | Explanation |
|---------|-------------|
| **@pipe_func decorator** | Marks function for automatic discovery and registration |
| **Function Registry** | Global singleton that stores all registered functions |
| **WorkingMemory** | Object containing pipeline inputs and intermediate results |
| **StuffContent** | Base class for all data types that flow through pipelines |
| **Auto-registration** | Pipelex automatically discovers functions on initialization |
| **PLX file** | TOML-based pipeline definition that references functions |

---

## File Locations (Quick Reference)

| Component | Location |
|-----------|----------|
| PipeFunc Executor | `pipelex/pipe_operators/func/pipe_func.py` |
| Function Registry | `pipelex/system/registries/func_registry.py` |
| Registry Utils | `pipelex/system/registries/func_registry_utils.py` |
| Working Memory | `pipelex/core/memory/working_memory.py` |
| Tests | `tests/unit/pipe_operators/pipe_func/` |

---

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Function 'X' not found in registry" | Missing `@pipe_func()` | Add decorator before function |
| "has no return type annotation" | Missing `->` return type | Add return type hint |
| "is not a subclass of StuffContent" | Wrong return type | Return StuffContent or ListContent |
| "Exactly 1 parameter named 'working_memory'" | Wrong parameter | Use exactly `working_memory: WorkingMemory` |
| Function not discovered | Scan failure | Check syntax, imports, decorator present |

---

## Next Steps

1. **Beginner?** Start with PIPEFUNC_QUICK_REFERENCE.md TL;DR section
2. **Intermediate?** Read the entire PIPEFUNC_QUICK_REFERENCE.md
3. **Advanced?** Deep-dive into PIPEFUNC_INVESTIGATION.md
4. **Stuck?** Check Troubleshooting in PIPEFUNC_QUICK_REFERENCE.md first, then Gotchas in PIPEFUNC_INVESTIGATION.md

---

## Documentation Statistics

- **Total documentation**: 1,362 lines, 41.6 KB
- **Code examples**: 50+
- **Patterns documented**: 10+
- **Real-world examples**: 6
- **Error scenarios covered**: 15+

---

## Version Information

- **Investigation Date**: 2025-11-14
- **Pipelex Branch**: feature/groq
- **Architecture Version**: Post v0.12.0 (with @pipe_func decorator requirement)

---

Generated by comprehensive codebase analysis of Pipelex architecture.
