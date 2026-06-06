"""LangGraph agent package and shared exceptions."""


class AppError(Exception):
    pass


class AgentError(AppError):
    pass


class NodeExecutionError(AgentError):
    def __init__(self, node: str, cause: Exception):
        self.node = node
        self.cause = cause
        super().__init__(f"Node '{node}' failed: {cause}")


class RetrievalError(AppError):
    pass


class GroundXError(RetrievalError):
    pass


class QdrantError(RetrievalError):
    pass


class ValidationError(AppError):
    pass


class NotFoundError(AppError):
    pass
