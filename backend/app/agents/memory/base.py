from abc import ABC, abstractmethod


class AgentMemory(ABC):
    @abstractmethod
    async def retrieve(
        self,
        namespace: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    async def remember(self, namespace: str, key: str, value: dict[str, object]) -> None:
        raise NotImplementedError
