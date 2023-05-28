from odoo import models, fields, api
import datetime
import itertools


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
        store = True,
        string = "Taxes"
    )
    payment_ids = fields.Many2many(
        "account.payment",
        "account_payment_invoice_rel",
        compute = "_compute_payment_ids",
        string = "Payments"
    )
    send_sequence = fields.Char(
        copy = False,
        string = "Send Sequence FE"
    )
    is_move_sent = fields.Boolean(
        readonly = True,
        default = True,
        copy = False,
        tracking = True,
        help = "It indicates that the invoice/payment has been sent."
    )
    analytic_line_ids = fields.One2many(
        "account.analytic.line",
        "invoice_id",
        string = "Timesheet Entries"
    )

    @api.depends("payment_state")
    def _compute_payment_ids(self):
        for line in self:
            line.payment_ids = False

            if line.payment_state == "paid":
                payment_ids = self.env["account.payment"].search([]).filtered(
                    lambda payment: line.id in payment.reconciled_invoice_ids.ids
                ).ids
                payment_ids = list(dict.fromkeys(payment_ids)) if len(payment_ids) > 0 else []
                line.payment_ids = [(6, 0, payment_ids)] if len(payment_ids) > 0 else False

    @api.depends("invoice_line_ids")
    def _compute_tax_ids(self):
        for line in self:
            line.tax_ids = False

            if len(line.invoice_line_ids) > 0:
                tax_ids = []

                for inv_line in line.invoice_line_ids:
                    tax_ids.append(inv_line.tax_ids)

                tax_ids = list(itertools.chain.from_iterable(tax_ids))
                tax_ids = list(dict.fromkeys(tax_ids)) if len(tax_ids) > 0 else []
                line.tax_ids = [(6, 0, tax_ids)] if len(tax_ids) > 0 else False

    @api.depends("move_type", "invoice_date", "name", "amount_total", "l10n_it_stamp_duty")
    def _compute_invoice_down_payment(self):
        for line in self:
            line.invoice_down_payment = 0.00

            if ("in_" in line.move_type or "out_" in line.move_type) and line.invoice_date:
                if line.name == "29":
                    line.invoice_down_payment = 56.00
                elif line.invoice_date <= datetime.date(2023, 3, 1):
                    line.invoice_down_payment = 0.4 * line.amount_total + line.l10n_it_stamp_duty
                elif datetime.date(2023, 3, 1) < line.invoice_date <= datetime.date(2023, 4, 1):
                    line.invoice_down_payment = 0.35 * line.amount_total + line.l10n_it_stamp_duty
                elif line.invoice_date > datetime.date(2023, 4, 1):
                    line.invoice_down_payment = 0.345 * line.amount_total + line.l10n_it_stamp_duty

    @api.depends("amount_total", "invoice_down_payment")
    def _compute_cash_flow(self):
        for line in self:
            line.cash_flow = line.amount_total - line.invoice_down_payment

    def send_pec_mail(self):
        pass

    _sql_constraints = [
        ("unique_send_sequence", "unique(send_sequence)", "Il progressivo invio deve essere univoco!")
    ]
