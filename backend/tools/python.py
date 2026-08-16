def calculate(expression: str) -> str:
    allowed = {"__builtins__": {}}
    try:
        return str(eval(expression, allowed, {}))
    except Exception as exc:
        return f"Calculation failed: {exc}"
