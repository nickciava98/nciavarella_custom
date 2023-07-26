from odoo import models, fields


class LinkInvoiceTimesheet(models.Model):
    _name = "link.invoice.timesheet"
    _description = "Link Invoice Timesheet"

    analytic_line_ids = fields.Many2many(
        "account.analytic.line",
        "link_invoice_analytic_line_rel",
        ondelete="cascade",
        string="Timesheet Entry"
    )
    invoice_id = fields.Many2one(
        "account.move",
        ondelete="cascade",
        domain="[('move_type', '=', 'out_invoice')]",
        string="Invoice"
    )

    def confirm_action(self):
        if len(self.analytic_line_ids) > 0:
            for analytic_line in self.analytic_line_ids:
                analytic_line.invoice_id = self.invoice_id if self.invoice_id else False
