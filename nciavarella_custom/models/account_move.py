import itertools

from odoo import models, fields, api


class AccountMove(models.Model):
    _order = "invoice_date desc, invoice_date_due desc, name desc"
    _inherit = "account.move"

    l10n_it_stamp_duty = fields.Float(
        default=.0,
        readonly=True,
        states={"draft": [("readonly", False)]},
        string="Bollo",
    )
    down_payment_id = fields.Many2one(
        "account.move.down.payment",
        compute="_compute_down_payment_id",
        store=True
    )
    invoice_down_payment = fields.Monetary(
        compute="_compute_invoice_down_payment",
        store=True,
        readonly=False
    )
    cash_flow = fields.Monetary(
        compute="_compute_cash_flow",
        store=True
    )
    tax_ids = fields.Many2many(
        "account.tax",
        "tax_present_rel",
        compute="_compute_tax_ids",
        store=True,
        string="Taxes"
    )
    payment_ids = fields.Many2many(
        "account.payment",
        "account_payment_invoice_rel",
        compute="_compute_payment_ids",
        store=True,
        string="Payments"
    )
    is_move_sent = fields.Boolean(
        readonly=True,
        default=True,
        copy=False,
        tracking=True,
        help="It indicates that the invoice/payment has been sent."
    )
    analytic_line_ids = fields.One2many(
        "account.analytic.line",
        "invoice_id",
        string="Timesheet Entries"
    )

    @api.depends("payment_state")
    def _compute_payment_ids(self):
        for line in self:
            payment_ids = self.env["account.payment"].search([]).filtered(
                lambda payment: line.id in payment.reconciled_invoice_ids.ids
            ).ids if line.payment_state == "paid" else []
            line.payment_ids = [(6, 0, list(dict.fromkeys(payment_ids)))] if payment_ids else False

    @api.depends("invoice_line_ids")
    def _compute_tax_ids(self):
        for line in self:
            line.tax_ids = False

            if line.invoice_line_ids:
                tax_ids = list(itertools.chain.from_iterable(
                    [inv_line.tax_ids.ids for inv_line in line.invoice_line_ids]
                ))
                line.tax_ids = [(6, 0, list(dict.fromkeys(tax_ids)))] if tax_ids else False

    @api.depends("invoice_date")
    def _compute_down_payment_id(self):
        for line in self:
            line.down_payment_id = self.env["account.move.down.payment"].search(
                ["&", ("date_from", "<=", line.invoice_date.strftime("%Y-%m-%d")),
                 ("date_to", ">=", line.invoice_date.strftime("%Y-%m-%d"))], limit=1
            ) if line.invoice_date else False

    def update_invoice_down_payment_action(self):
        self.with_context(no_create_write=True)._compute_invoice_down_payment()

    @api.depends("move_type", "invoice_date", "amount_total", "down_payment_id", "down_payment_id.stamp_duty",
                 "l10n_it_stamp_duty")
    def _compute_invoice_down_payment(self):
        for line in self:
            line.invoice_down_payment = .0

            if line.move_type in ("out_invoice", "out_receipt") and line.invoice_date and line.down_payment_id:
                line.invoice_down_payment = line.down_payment_id.down_payment * line.amount_total \
                    if not line.down_payment_id.stamp_duty \
                    else line.down_payment_id.down_payment * line.amount_total + line.l10n_it_stamp_duty

                # if line.name == "29":
                #     line.invoice_down_payment = 56.
                # elif line.name == "2023/39":
                #     line.invoice_down_payment = .34 * line.amount_total + line.l10n_it_stamp_duty
                # elif line.invoice_date <= datetime.date(2023, 3, 1):
                #     line.invoice_down_payment = .4 * line.amount_total + line.l10n_it_stamp_duty
                # elif datetime.date(2023, 3, 1) < line.invoice_date <= datetime.date(2023, 4, 1):
                #     line.invoice_down_payment = .35 * line.amount_total + line.l10n_it_stamp_duty
                # elif datetime.date(2023, 4, 1) < line.invoice_date <= datetime.date(2023, 5, 29):
                #     line.invoice_down_payment = .345 * line.amount_total + line.l10n_it_stamp_duty
                # elif datetime.date(2023, 5, 29) < line.invoice_date < datetime.date(2023, 6, 30):
                #     line.invoice_down_payment = .34 * line.amount_total
                # elif datetime.date(2023, 6, 30) <= line.invoice_date < datetime.date(2023, 8, 31):
                #     line.invoice_down_payment = .3 * line.amount_total
                # elif datetime.date(2023, 8, 31) <= line.invoice_date <= datetime.date(2023, 9, 30):
                #     line.invoice_down_payment = .15 * line.amount_total
                # elif datetime.date(2023, 10, 31) < line.invoice_date <= datetime.date(2023, 12, 31):
                #     line.invoice_down_payment = .2 * line.amount_total
                # elif line.invoice_date >= datetime.date(2024, 1, 1):
                #     line.invoice_down_payment = .3 * line.amount_total

    @api.depends("amount_total", "invoice_down_payment")
    def _compute_cash_flow(self):
        for line in self:
            line.cash_flow = line.amount_total - line.invoice_down_payment

    def name_get(self):
        result = []

        for line in self:
            name = [line.name]

            if line.invoice_date:
                name.append(f"({line.invoice_date.strftime('%d/%m/%Y')})")

            if line.partner_id:
                name.append(f"[{line.partner_id.name}]")

            result.append((line.id, " ".join(name)))

        return result

    @api.model
    def _name_search(self, name, args=None, operator="ilike", limit=100, name_get_uid=None):
        args = args or []
        domain = ["|", ("name", operator, name), ("partner_id", "ilike", name)] if name else []

        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)


class AccountMoveDownPayment(models.Model):
    _name = "account.move.down.payment"
    _description = "Invoice Down Payment"

    date_from = fields.Date(
        string="Date From"
    )
    date_to = fields.Date(
        string="Date To"
    )
    down_payment = fields.Float(
        string="Down Payment"
    )
    stamp_duty = fields.Boolean(
        string="Stamp Duty"
    )

    _sql_constraints = [
        ("unique_dates", "UNIQUE(date_from, date_to)", "Date From and Date To must be unique!")
    ]
