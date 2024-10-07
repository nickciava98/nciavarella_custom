from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = "project.project"

    tariffa_oraria = fields.Monetary(
        currency_field="currency_id",
        default=.0,
        string="Tariffa Oraria"
    )
    conferma_automatica = fields.Boolean(
        default=False,
        string="Conferma Automatica?"
    )

    def _get_task_domain(self):
        return [("project_id", "=", self.id), ("active", "in", (True, False))]

    @api.depends("task_ids")
    def _compute_task_count(self):
        for project in self:
            project.task_count = self.env["project.task"].search_count(project._get_task_domain())

    def action_view_tasks(self):
        action = super().action_view_tasks()
        action["view_mode"] = "tree,form"
        action["views"] = [
            (self.env.ref("project.view_task_tree2", False).id, "tree"),
            (self.env.ref("project.view_task_form2", False).id, "form")
        ]
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
