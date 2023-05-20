from odoo import models, fields, api, _


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    is_invoiced = fields.Boolean(
        compute = "_compute_is_invoiced",
        store = True,
        string = "Invoiced?"
    )
    invoice_id = fields.Many2one(
        "account.move",
        ondelete = "restrict",
        string = "Invoice"
    )

    @api.depends("invoice_id")
    def _compute_is_invoiced(self):
        for line in self:
            line.is_invoiced = True if line.invoice_id else False

    def link_invoice_timesheet_action(self):
        return {
            "name": _("Link Invoice"),
            "res_model": "link.invoice.timesheet",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "tree,form",
            "views": [(False, "form")],
            "context": {
                "default_analytic_line_ids": self.ids
            },
            "target": "new"
        }
