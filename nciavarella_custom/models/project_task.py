from odoo import models, api


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.onchange("stage_id")
    def _onchange_stage_id(self):
        for task in self:
            if task.stage_id and task.stage_id.fase_completata:
                task.active = False
