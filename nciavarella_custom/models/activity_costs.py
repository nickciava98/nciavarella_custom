from odoo import models, fields, api
from datetime import datetime

class ActivityCosts(models.Model):
    _name = "activity.costs"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Activity Costs"

    name = fields.Char(
        required = True,
        tracking = True
    )
    total_invoiced = fields.Float(
        compute = "_compute_total_invoiced"
    )
    total_taxable = fields.Float(
        compute = "_compute_total_taxable"
    )
    total_down_payments = fields.Float(
        compute = "_compute_total_down_payments",
    )
    remaining_balance = fields.Float(
        compute = "_compute_remaining_balance"
    )
    tax_id = fields.Float(
        required = True,
        tracking = True
    )
    total_taxes_due = fields.Float(
        compute = "_compute_total_taxes_due"
    )
    total_stamp_taxes = fields.Float(
        compute = "_compute_total_stamp_taxes"
    )
    welfare_id = fields.Float(
        required = True,
        tracking = True
    )
    total_welfare_due = fields.Float(
        compute = "_compute_total_welfare_due"
    )
    year_cash_flow = fields.Float(
        compute = "_compute_year_cash_flow"
    )
    currency_id = fields.Many2one(
        "res.currency",
        compute = "_compute_currency_id"
    )
    taxes_previous_down_payment = fields.Float()
    welfare_previous_down_payment = fields.Float()
    gross_tax = fields.Float(
        compute = "_compute_gross_tax"
    )
    net_tax = fields.Float(
        compute = "_compute_net_tax"
    )

    @api.depends("total_down_payments", "remaining_balance")
    def _compute_gross_tax(self):
        for line in self:
            line.gross_tax = 0.3833338 * line.total_invoiced

    @api.depends("gross_tax", "taxes_previous_down_payment",
                 "welfare_previous_down_payment")
    def _compute_net_tax(self):
        for line in self:
            line.net_tax = line.gross_tax - \
                           line.taxes_previous_down_payment - line.welfare_previous_down_payment

    def _compute_currency_id(self):
        for line in self:
            line.currency_id = self.env.ref('base.main_company').currency_id

    def _compute_total_invoiced(self):
        for line in self:
            line.total_invoiced = 0

            for invoice in self.env["account.move"].search(
                    ["&",
                     ("invoice_date", ">=", str(line.name) + "-01-01"),
                     ("invoice_date", "<=", str(line.name) + "-12-31")]
            ):
                line.total_invoiced += invoice.amount_total

    @api.depends("total_invoiced")
    def _compute_total_taxable(self):
        for line in self:
            line.total_taxable = line.total_invoiced * 0.67

    def _compute_total_down_payments(self):
        for line in self:
            line.total_down_payments = 0

            for invoice in self.env["account.move"].search(
                    ["&", "&",
                     ("payment_state", "=", "paid"),
                     ("invoice_date", ">=", str(line.name) + "-01-01"),
                     ("invoice_date", "<=", str(line.name) + "-12-31")]
            ):
                line.total_down_payments += invoice.invoice_down_payment

    @api.depends("total_down_payments", "total_taxes_due",
                 "total_stamp_taxes", "total_welfare_due")
    def _compute_remaining_balance(self):
        for line in self:
            line.remaining_balance = \
                (line.total_taxes_due + line.total_stamp_taxes + line.total_welfare_due) \
                - line.total_down_payments

    @api.depends("tax_id", "total_invoiced")
    def _compute_total_taxes_due(self):
        for line in self:
            line.total_taxes_due = line.tax_id * 1.34 * line.total_invoiced

    def _compute_total_stamp_taxes(self):
        for line in self:
            line.total_stamp_taxes = 0

            for invoice in self.env["account.move"].search(
                    ["&", "&",
                     ("payment_state", "=", "paid"),
                     ("invoice_date", ">=", str(line.name) + "-01-01"),
                     ("invoice_date", "<=", str(line.name) + "-12-31")]
            ):
                if invoice.amount_total > 79.47:
                    line.total_stamp_taxes += 2

    @api.depends("welfare_id", "total_invoiced")
    def _compute_total_welfare_due(self):
        for line in self:
            line.total_welfare_due = 1.206 * line.welfare_id * line.total_invoiced

    @api.depends("total_invoiced")
    def _compute_year_cash_flow(self):
        for line in self:
            line.year_cash_flow = line.total_invoiced - line.total_down_payments + line.remaining_balance
