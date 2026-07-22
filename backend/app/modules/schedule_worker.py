"""Run module-owned tenant schedules outside HTTP processes."""

import argparse
import logging
import time

from sqlmodel import Session

from app.core.database import engine
from app.modules.access import get_runtime_manifest
from app.modules.registry import get_module_definitions
from app.platform.infra.module_tenant_directory import SqlEnabledModuleTenantDirectory

logger = logging.getLogger(__name__)


def run_due_schedules(*, last_run: dict[str, float], now: float) -> int:
    """Run due handlers for tenants entitled to their owning module."""

    manifest_codes = {module.code for module in get_runtime_manifest().modules}
    completed = 0
    with Session(engine) as session:
        directory = SqlEnabledModuleTenantDirectory(session)
        definitions = get_module_definitions()
        for module_code in sorted(manifest_codes):
            definition = definitions[module_code]
            for schedule in definition.schedule_handlers:
                previous = last_run.get(schedule.code)
                if previous is not None and now - previous < schedule.interval_seconds:
                    continue
                for tenant_id in directory.list_enabled_tenant_ids(module_code=module_code):
                    schedule.handler(session, tenant_id)
                    completed += 1
                last_run[schedule.code] = now
    return completed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run module-owned tenant schedules")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    args = parser.parse_args()
    last_run: dict[str, float] = {}
    while True:
        completed = run_due_schedules(last_run=last_run, now=time.monotonic())
        if args.once:
            return
        if completed == 0:
            time.sleep(max(1.0, args.poll_seconds))


if __name__ == "__main__":
    main()
