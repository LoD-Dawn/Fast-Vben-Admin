import argparse

from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine
from app.modules.access import reconcile_module_runtime
from app.modules.manifest import build_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize module runtime records for an Edition"
    )
    parser.add_argument("--edition", default=settings.APP_EDITION)
    args = parser.parse_args()
    manifest = build_manifest(edition=args.edition)
    with Session(engine) as session:
        reconcile_module_runtime(session, manifest=manifest)
        session.commit()


if __name__ == "__main__":
    main()
