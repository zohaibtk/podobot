from dataclasses import dataclass

from app.db.types import AgentOutputValidationStatus


@dataclass(frozen=True)
class OutputValidation:
    status: AgentOutputValidationStatus
    checks: list[dict[str, object]]
    errors: list[str]


def validate_agent_output(output: dict[str, object]) -> OutputValidation:
    errors: list[str] = []
    checks = [
        {
            "name": "structured_output",
            "passed": isinstance(output, dict),
            "message": "Output must be a JSON object.",
        },
        {
            "name": "summary_present",
            "passed": bool(output.get("summary")),
            "message": "Output includes a summary.",
        },
        {
            "name": "approval_gate_flag",
            "passed": output.get("needs_approval") is True,
            "message": "Output explicitly preserves human approval gates.",
        },
    ]
    for check in checks:
        if not check["passed"]:
            errors.append(str(check["message"]))
    return OutputValidation(
        status=AgentOutputValidationStatus.FAILED if errors else AgentOutputValidationStatus.PASSED,
        checks=checks,
        errors=errors,
    )
