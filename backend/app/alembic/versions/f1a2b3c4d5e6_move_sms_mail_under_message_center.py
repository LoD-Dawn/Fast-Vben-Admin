"""move sms and mail management under message center

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-07-11 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE menu AS target
        SET
            parent_id = message_center.id,
            route_path = '/system/message-center/sms',
            component = '#/views/_core/router-view.vue',
            sort = 40,
            updated_at = CURRENT_TIMESTAMP
        FROM menu AS message_center
        WHERE target.route_name = 'Sms'
          AND message_center.route_name = 'MessageCenter'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/system/message-center/sms/channels',
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'SmsChannels'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/system/message-center/sms/templates',
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'SmsTemplates'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/system/message-center/sms/logs',
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'SmsLogs'
        """
    )
    op.execute(
        """
        UPDATE menu AS target
        SET
            parent_id = message_center.id,
            route_path = '/system/message-center/mail',
            component = '#/views/_core/router-view.vue',
            sort = 50,
            updated_at = CURRENT_TIMESTAMP
        FROM menu AS message_center
        WHERE target.route_name = 'Mail'
          AND message_center.route_name = 'MessageCenter'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/system/message-center/mail/accounts',
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'MailAccounts'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/system/message-center/mail/templates',
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'MailTemplates'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/system/message-center/mail/logs',
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'MailLogs'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE menu
        SET
            parent_id = NULL,
            route_path = '/sms',
            component = NULL,
            sort = 30,
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'Sms'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/sms/channels', updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'SmsChannels'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/sms/templates', updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'SmsTemplates'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/sms/logs', updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'SmsLogs'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET
            parent_id = NULL,
            route_path = '/mail',
            component = NULL,
            sort = 40,
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'Mail'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/mail/accounts', updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'MailAccounts'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/mail/templates', updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'MailTemplates'
        """
    )
    op.execute(
        """
        UPDATE menu
        SET route_path = '/mail/logs', updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'MailLogs'
        """
    )
