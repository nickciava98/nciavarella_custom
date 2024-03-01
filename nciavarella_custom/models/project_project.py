from odoo import models


class ProjectProject(models.Model):
    _inherit = "project.project"

    def action_view_tasks(self):
        action = super().action_view_tasks()
        action["domain"] = [("project_id", "=", self.id), ("active", "in", (True, False))]

        return action

    def view_project_form(self):
        return {
            "name": self.name,
            "view_type": "form",
            "view_mode": "form",
            "view_id": self.env.ref("project.edit_project").id,
            "res_model": self._name,
            "res_id": self.id,
            "type": "ir.actions.act_window",
            "context": {
                "active_id": self.id,
                "create": self.active,
                "active_test": self.active
            },
            "target": "current"
        }
