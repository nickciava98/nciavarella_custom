from odoo import models, api


class ProjectProject(models.Model):
    _inherit = "project.project"

    def _get_task_domain(self):
        return [("project_id", "=", self.id), ("active", "in", (True, False))]

    @api.depends("task_ids")
    def _compute_task_count(self):
        for project in self:
            project.task_count = self.env["project.task"].search_count(project._get_task_domain())

    def action_view_tasks(self):
        action = super().action_view_tasks()
        action["domain"] = self._get_task_domain()

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
