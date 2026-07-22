import argparse
import time
from importlib import import_module

from sqlmodel import Session

from app.core.database import engine
from app.modules.access import get_runtime_manifest
from app.modules.events import configure_event_deliveries
from app.modules.manifest import BuildManifest
from app.modules.outbox import dispatch_pending_events
from app.modules.registry import get_module_definitions


def refresh_module_backlog_metrics(*, manifest: BuildManifest, session: Session) -> None:
    """Let installed modules refresh their own bounded backlog gauges."""

    module_codes = {module.code for module in manifest.modules}
    if "erp" in module_codes:
        import_module("app.modules.erp.observability").refresh_outbox_pending(session)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dispatch transactional outbox events")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    args = parser.parse_args()
    manifest = get_runtime_manifest()
    definitions = get_module_definitions()
    configure_event_deliveries(definitions[module.code] for module in manifest.modules)
    while True:
        with Session(engine) as session:
            # Commit every claimed delivery independently so a retryable target
            # cannot keep the remainder of a batch locked behind its handler.
            delivered, failed = dispatch_pending_events(session=session, max_events=1)
            refresh_module_backlog_metrics(manifest=manifest, session=session)
            session.commit()
        if args.once:
            return
        if delivered == 0 and failed == 0:
            time.sleep(max(0.1, args.poll_seconds))


if __name__ == "__main__":
    main()
