from odoo import api, SUPERUSER_ID
from odoo.addons.nciavarella_custom.models.project_task import TIPO_ATTIVITA_SELECTION


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    timesheets = env["account.analytic.line"].search([
        ("project_id", "!=", False),
        ("task_id", "!=", False),
        ("name", "not in", (False, "/")),
        ("tipo_attivita", "=", False)
    ])

    if timesheets:
        for timesheet in timesheets:
            tipo_attivita = []

            for selection in TIPO_ATTIVITA_SELECTION:
                descr = selection[1].upper()
                name = timesheet.name.upper()
                cond = descr in name

                if descr == "PROGRAMMAZIONE":
                    cond = cond or "SVILUPP" in name or "IMPLEMENTAZION" in name

                if descr == "INSTALLAZIONE E PARAMETRIZZAZIONE":
                    cond = cond or "INSTALLAZION" in name

                if cond:
                    tipo_attivita.append(selection)

            if tipo_attivita:
                timesheet.tipo_attivita = tipo_attivita[0][0]

            else:
                timesheet.tipo_attivita = "consulenza"
