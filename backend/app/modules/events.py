"""Event composition and contract validation at the application boundary."""

from collections.abc import Iterable

from app.modules.contracts import ModuleDefinition
from app.modules.outbox import EVENT_HANDLERS


def configure_event_deliveries(definitions: Iterable[ModuleDefinition]) -> None:
    """Build the in-process delivery registry from enabled module definitions."""
    definitions = tuple(definitions)
    EVENT_HANDLERS.clear()
    for definition in definitions:
        if definition.lifecycle.register_event_handlers is not None:
            definition.lifecycle.register_event_handlers()
    validate_event_contracts(definitions)


def validate_event_contracts(definitions: Iterable[ModuleDefinition]) -> None:
    """Reject duplicate or incompatible publisher/subscriber declarations."""
    publishers: dict[tuple[str, int], str] = {}
    for definition in definitions:
        for contract in definition.event_publishers:
            key = (contract.event_type, contract.version)
            existing = publishers.setdefault(key, definition.code)
            if existing != definition.code:
                raise ValueError(
                    f"Event {contract.event_type}@{contract.version} has multiple publishers: "
                    f"{existing}, {definition.code}"
                )
    for definition in definitions:
        for contract in definition.event_subscribers:
            key = (contract.event_type, contract.version)
            if key not in publishers:
                raise ValueError(
                    f"Module {definition.code} subscribes to undeclared event "
                    f"{contract.event_type}@{contract.version}"
                )
