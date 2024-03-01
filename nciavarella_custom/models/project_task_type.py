from odoo import models, fields


class ProjectTaskType(models.Model):
    _inherit = "project.task.type"

    fase_completata = fields.Boolean(
        default=False,
        string="Fase completata?"
    )
