from dataclasses import dataclass


@dataclass(frozen=True)
class MCPRetryPolicy:
    max_attempts: int = 2
    backoff_ms: int = 250

    @classmethod
    def from_payload(cls, payload: dict[str, object] | None) -> "MCPRetryPolicy":
        payload = payload or {}
        return cls(
            max_attempts=max(1, int(payload.get("max_attempts", 2))),
            backoff_ms=max(0, int(payload.get("backoff_ms", 250))),
        )
