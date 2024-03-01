from odoo import models

class ProjectTask(models.Model):
    _inherit = "project.task"

    def write(self, vals):
        res = super().write(vals)

        if "stage_id" in vals:
            for project in self.filtered(lambda p: p.stage_id.fase_completata):
                project.active = False

        return res
