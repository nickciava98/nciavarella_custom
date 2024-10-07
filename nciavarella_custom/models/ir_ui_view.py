import logging

from odoo import models, api, SUPERUSER_ID


_logger = logging.getLogger(__name__)


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def update_views(self):
        self = self.with_user(SUPERUSER_ID)
        views_to_unlink = [
            "contacts.action_contacts_view_kanban",
            "hr_timesheet.act_hr_timesheet_line_view_kanban",
            "hr_timesheet.act_hr_timesheet_line_view_pivot",
            "hr_timesheet.act_hr_timesheet_line_view_graph"
        ]

        for view in views_to_unlink:
            view_id = self.env.ref(view, False)

            if not view_id:
                continue

            _logger.info(f"Unlinking view: {view}")
            view_id.unlink()
