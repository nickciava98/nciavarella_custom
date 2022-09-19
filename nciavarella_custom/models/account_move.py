from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move"

    is_hourly_cost = fields.Boolean(
        compute = "_compute_is_hourly_cost"
    )
    invoice_down_payment = fields.Monetary(
        compute = "_compute_invoice_down_payment",
        store = True
    )
    cash_flow = fields.Monetary(
        compute = "_compute_cash_flow",
        store = True
    )

    @api.onchange("invoice_line_ids")
    def _compute_is_hourly_cost(self):
        for line in self:
            line.is_hourly_cost = False

            for invoice_line in line.invoice_line_ids:
                if invoice_line.product_id.is_hourly_cost:
                    line.is_hourly_cost = True
                    break

    @api.depends("amount_total")
    def _compute_invoice_down_payment(self):
        for line in self:
            line.invoice_down_payment = 0

            if line.amount_total >= 79.47:
                line.invoice_down_payment = 0.4 * line.amount_total + 2
            else:
                line.invoice_down_payment = 0.4 * line.amount_total

    @api.depends("invoice_down_payment")
    def _compute_cash_flow(self):
        for line in self:
            line.cash_flow = line.amount_total - line.invoice_down_payment
