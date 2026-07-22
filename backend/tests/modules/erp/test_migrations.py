from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlmodel import Session

from app.core.database import engine
from app.models import ModuleDesiredState, ModuleRegistry
from app.modules.migrations import (
    migrate_edition,
    migration_order,
    module_alembic_config,
)


def test_erp_migration_configuration_is_namespaced() -> None:
    erp_config = module_alembic_config("erp")

    assert migration_order(edition="erp") == ["platform", "erp"]
    assert erp_config.get_main_option("script_location") == "app/modules/erp/migrations"
    assert erp_config.get_main_option("version_table") == "alembic_version_erp"
    assert erp_config.get_main_option("version_table_schema") == "public"


def test_erp_migration_round_trip(db: Session) -> None:
    """ERP revisions must support rollback before they enter shared history."""
    _ = db
    erp_config = module_alembic_config("erp")

    command.downgrade(erp_config, "base")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('erp.product_unit')")).scalar_one() is None
        assert connection.execute(
            text("SELECT to_regclass('erp.finance_receipt')")
        ).scalar_one() is None

    command.upgrade(erp_config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('erp.product_unit')")).scalar_one() == "erp.product_unit"
        assert connection.execute(
            text("SELECT to_regclass('erp.finance_receipt')")
        ).scalar_one() == "erp.finance_receipt"


def test_erp_migration_creates_owned_tables_and_forced_rls(db: Session) -> None:
    erp_config = module_alembic_config("erp")
    expected_head = ScriptDirectory.from_config(erp_config).get_current_head()
    assert expected_head is not None

    assert migrate_edition(edition="erp") == ["platform", "erp"]
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT to_regclass('erp.product_unit'), to_regclass('erp.product_category'), "
                "to_regclass('erp.product'), to_regclass('erp.warehouse'), "
                "to_regclass('erp.erp_setting'), to_regclass('erp.reconciliation_run'), "
                "to_regclass('erp.supplier'), to_regclass('erp.customer'), "
                "to_regclass('erp.document_sequence'), "
                "to_regclass('erp.command_receipt'), "
                "to_regclass('erp.document_attachment'), "
                "to_regclass('erp.document_action_log'), "
                "to_regclass('erp.purchase_in'), to_regclass('erp.purchase_in_item'), "
                "to_regclass('erp.purchase_return'), to_regclass('erp.purchase_return_item'), "
                "to_regclass('erp.sale_out'), to_regclass('erp.sale_out_item'), "
                "to_regclass('erp.sale_return'), to_regclass('erp.sale_return_item'), "
                "to_regclass('erp.settlement_account'), "
                "to_regclass('erp.finance_payment'), to_regclass('erp.finance_payment_item'), "
                "to_regclass('erp.finance_receipt'), to_regclass('erp.finance_receipt_item')"
            )
        ).one() == (
            "erp.product_unit",
            "erp.product_category",
            "erp.product",
            "erp.warehouse",
            "erp.erp_setting",
            "erp.reconciliation_run",
            "erp.supplier",
            "erp.customer",
            "erp.document_sequence",
            "erp.command_receipt",
            "erp.document_attachment",
            "erp.document_action_log",
            "erp.purchase_in",
            "erp.purchase_in_item",
            "erp.purchase_return",
            "erp.purchase_return_item",
            "erp.sale_out",
            "erp.sale_out_item",
            "erp.sale_return",
            "erp.sale_return_item",
            "erp.settlement_account",
            "erp.finance_payment",
            "erp.finance_payment_item",
            "erp.finance_receipt",
            "erp.finance_receipt_item",
        )
        assert connection.execute(
            text("SELECT version_num FROM public.alembic_version_erp")
        ).scalar_one() == expected_head
        assert connection.execute(
            text(
                "SELECT relrowsecurity AND relforcerowsecurity "
                "FROM pg_class WHERE oid = 'erp.product'::regclass"
            )
        ).scalar_one() is True
        assert connection.execute(
            text(
                "SELECT COUNT(*) FROM pg_policies "
                "WHERE schemaname = 'erp' AND policyname = 'erp_product_tenant_isolation'"
            )
        ).scalar_one() == 1
        assert connection.execute(
            text(
                "SELECT COUNT(*) FROM pg_policies "
                "WHERE schemaname = 'erp' "
                "AND policyname IN ('erp_supplier_tenant_isolation', "
                "'erp_customer_tenant_isolation', 'erp_purchase_in_tenant_isolation', "
                "'erp_purchase_in_item_tenant_isolation', "
                "'erp_purchase_return_tenant_isolation', "
                "'erp_purchase_return_item_tenant_isolation', "
                "'erp_sale_out_tenant_isolation', "
                "'erp_sale_out_item_tenant_isolation', "
                "'erp_sale_return_tenant_isolation', "
                "'erp_sale_return_item_tenant_isolation', "
                "'erp_command_receipt_tenant_isolation', "
                "'erp_document_attachment_tenant_isolation', "
                "'erp_settlement_account_tenant_isolation', "
                "'erp_finance_payment_tenant_isolation', "
                "'erp_finance_payment_item_tenant_isolation', "
                "'erp_finance_receipt_tenant_isolation', "
                "'erp_finance_receipt_item_tenant_isolation', "
                "'erp_document_action_log_tenant_isolation', "
                "'erp_erp_setting_tenant_isolation', "
                "'erp_reconciliation_run_tenant_isolation')"
            )
        ).scalar_one() == 20
        assert connection.execute(
            text(
                "SELECT relrowsecurity AND relforcerowsecurity "
                "FROM pg_class WHERE oid = 'erp.document_sequence'::regclass"
            )
        ).scalar_one() is True

    registry = db.get(ModuleRegistry, "erp")
    assert registry is not None
    registry.desired_state = ModuleDesiredState.DISABLED
    db.add(registry)
    db.commit()
