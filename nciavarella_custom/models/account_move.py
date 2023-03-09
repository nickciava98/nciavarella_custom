import datetime

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_down_payment = fields.Monetary(
        compute = "_compute_invoice_down_payment",
        store = True
    )
    cash_flow = fields.Monetary(
        compute = "_compute_cash_flow",
        store = True
    )
    tax_ids = fields.Many2many(
        "account.tax",
        "tax_present_rel",
        compute = "_compute_tax_ids",
        store = True
    )
    send_sequence = fields.Char(
        copy = False,
        string = "Send Sequence FE"
    )

    @api.depends("invoice_line_ids")
    def _compute_tax_ids(self):
        for line in self:
            line.tax_ids = False

            if len(line.invoice_line_ids) > 0:
                tax_ids = []

                for inv_line in line.invoice_line_ids:
                    for tax in inv_line.tax_ids:
                        if tax.id not in tax_ids:
                            tax_ids.append(tax.id)

                if len(tax_ids) > 0:
                    line.tax_ids = [(6, 0, tax_ids)]

    @api.depends("amount_total")
    def _compute_invoice_down_payment(self):
        for line in self:
            line.invoice_down_payment = 0.00

            if ("in_" in line.move_type or "out_" in line.move_type) and line.invoice_date:
                if line.name == "29":
                    line.invoice_down_payment = 56.00
                elif line.invoice_date <= datetime.date(2023, 3, 1):
                    line.invoice_down_payment = 0.4 * line.amount_total + line.l10n_it_stamp_duty
                elif line.invoice_date > datetime.date(2023, 3, 1):
                    line.invoice_down_payment = 0.35 * line.amount_total + line.l10n_it_stamp_duty

    @api.depends("invoice_down_payment")
    def _compute_cash_flow(self):
        for line in self:
            line.cash_flow = line.amount_total - line.invoice_down_payment

    def send_pec_mail(self):
        pass

    _sql_constraints = [
        ("unique_send_sequence", "unique(send_sequence)", "Il progressivo invio deve essere univoco!")
    ]
