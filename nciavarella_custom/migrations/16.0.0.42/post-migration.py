import logging

from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    timesheets = env["account.analytic.line"].search([("project_id", "!=", False), ("task_id", "!=", False)])

    if timesheets:
        for timesheet in timesheets:
            _logger.info(
                f"Aggiornamento Valore: ({timesheet.id}, {timesheet.task_id.name} - {timesheet.project_id.name})"
            )
            timesheet._compute_valore()
