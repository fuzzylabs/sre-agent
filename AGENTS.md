# AGENTS.md

## Do
- Always use Context7 MCP when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask.
- Keep code simple, with a strong focus on readability and maintainability.
- Use UK English.

## Docstrings
- Keep module-level and script top-level docstrings to a single line.
- Use Google-style docstrings.
- Do not include types for arguments.
- Keep docstrings concise and only include what is necessary to help readers understand the function or class.

### Docstrings Example
```
def function_with_pep484_type_annotations(param1: int, param2: str) -> bool:
    """Example function with PEP 484 type annotations.

    Important note.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        The return value. True for success, False otherwise.

    """
```
