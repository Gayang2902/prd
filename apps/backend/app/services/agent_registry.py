from importlib.metadata import entry_points

from securescope_schemas.agent_interface import AgentMetadata, BaseAgent

_registry: dict[str, type[BaseAgent]] = {}


def discover_agents() -> dict[str, type[BaseAgent]]:
    eps = entry_points(group="securescope.agents")
    for ep in eps:
        agent_cls = ep.load()
        if isinstance(agent_cls, type) and issubclass(agent_cls, BaseAgent):
            _registry[ep.name] = agent_cls
    return _registry


def get_registry() -> dict[str, type[BaseAgent]]:
    if not _registry:
        discover_agents()
    return _registry


def get_agent_metadata() -> list[AgentMetadata]:
    return [cls.describe() for cls in get_registry().values()]
