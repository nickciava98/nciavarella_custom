from odoo import models, fields, api


class LinkInvoiceTimesheet(models.Model):
    _name = "link.invoice.timesheet"
    _description = "Link Invoice Timesheet"

    analytic_line_ids = fields.Many2many(
        "account.analytic.line",
        "link_invoice_analytic_line_rel",
        ondelete="cascade",
        string="Timesheet Entry"
    )
    invoice_ids = fields.Many2many(
        "account.move",
        "link_invoice_account_move_rel"
    )
    invoice_id = fields.Many2one(
        "account.move",
        ondelete="cascade",
        string="Invoice"
    )

    def confirm_action(self):
        self.analytic_line_ids.write({
            "invoice_id": self.invoice_id.id if self.invoice_id else False
        })
