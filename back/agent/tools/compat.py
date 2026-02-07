"""Compatibility helpers for optional tool frameworks."""

from typing import Any, Callable, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])

try:
    from agents import function_tool as _function_tool
except Exception:
    _function_tool = None


@overload
def function_tool(func: F) -> F:
    ...


@overload
def function_tool(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    ...


def function_tool(*args: Any, **kwargs: Any):
    """Fallback to a no-op decorator when `agents` is unavailable."""
    if _function_tool is None:
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def _decorator(func: F) -> F:
            return func

        return _decorator

    return _function_tool(*args, **kwargs)
