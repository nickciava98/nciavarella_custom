import datetime
import itertools
import math
import html2text

from odoo import models, fields, api, exceptions


class AccountMove(models.Model):
    _order = "invoice_date desc, invoice_date_due desc, name desc"
    _inherit = "account.move"

    l10n_it_stamp_duty = fields.Float(
        default=.0,
        readonly=True,
        states={"draft": [("readonly", False)]},
        string="Bollo",
    )
    l10n_it_edi_attachment_id = fields.Many2one(
        "ir.attachment",
        copy=False,
        string="XML Fattura elettronica",
        ondelete="set null"
    )
    progressivo_invio = fields.Char(
        size=5,
        copy=False
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

    def write(self, vals):
        if "progressivo_invio" in vals:
            invoices = self.search(
                ["&", ("id", "!=", self.id), ("progressivo_invio", "=", vals.get("progressivo_invio"))]
            )

            if invoices:
                invoice_names = "\n".join(invoices.mapped("name"))

                raise exceptions.ValidationError(
                    f"Il Progressivo invio deve essere univoco!\n"
                    f"Lo stesso progressivo è stato trovato nelle seguenti fatture:\n"
                    f"{invoice_names}"
                )

        return super().write(vals)

    def button_draft(self):
        res = super().button_draft()

        for invoice in self:
            invoice.attachment_ids = [(5, 0, 0)]

        return res

    def _compute_edi_error_count(self):
        for line in self:
            line.edi_error_count = 0

    def _get_causale(self):
        causale = ""

        if self.narration:
            causale = html2text.html2text(self.narration).replace("\n", " ").replace("  ", "\n")

        return causale

    @api.depends("state")
    def _compute_show_reset_to_draft_button(self):
        for line in self:
            line.show_reset_to_draft_button = True if line.state != "draft" else False

    def _post(self, soft=True):
        posted = super()._post(soft=soft)

        for invoice in posted:
            codice_nazione = invoice.company_id.country_id.code
            codice_fiscale = self.env["res.partner"]._l10n_it_normalize_codice_fiscale(
                invoice.company_id.l10n_it_codice_fiscale
            )
            report_name = f"{codice_nazione}{codice_fiscale}_{invoice.progressivo_invio}.xml"
            data = (
                "<?xml version='1.0' encoding='UTF-8'?>%s"
                % str(self.env["account.edi.format"]._l10n_it_edi_export_invoice_as_xml(invoice))
            )
            description = f"Fattura elettronica: {invoice.move_type}"
            self.env["ir.attachment"].create({
                "name": report_name,
                "res_id": invoice.id,
                "res_model": invoice._name,
                "raw": data.encode(),
                "description": description,
                "type": "binary"
            })
            now = datetime.datetime.now()
            body = (f"Fattura elettronica generata il {now.strftime('%d/%m/%Y')} "
                    f"alle {now.strftime('%H:%M')} "
                    f"da {self.env.user.display_name}")
            invoice.message_post(body=body)

        return posted

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
                 "l10n_it_stamp_duty", "invoice_line_ids", "invoice_line_ids.quantity", "invoice_line_ids.price_unit")
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

    def _l10n_it_edi_prepare_fatturapa_line_details(
            self, reverse_charge_refund=False, is_downpayment=False, convert_to_euros=True):
        invoice_lines = super()._l10n_it_edi_prepare_fatturapa_line_details(
            reverse_charge_refund=reverse_charge_refund,
            is_downpayment=is_downpayment,
            convert_to_euros=convert_to_euros
        )

        if invoice_lines:
            inv_line_ids = [invoice_line["line"].id for invoice_line in invoice_lines]
            invoice_line_ids = self.env["account.move.line"].browse(inv_line_ids).sorted(key=lambda l: l.sequence)

            for invoice_line in invoice_lines:
                invoice_line["line_number"] = invoice_line_ids.ids.index(invoice_line["line"].id) + 1

        return sorted(invoice_lines, key=lambda l: l["line_number"])


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


from odoo.addons.account_edi.models.account_move import AccountMove as AccountMoveEdi
from odoo.addons.account.models.account_move import AccountMove as AccountMoveOdoo

def _post(self, soft=True):
    posted = AccountMoveOdoo._post(self=self, soft=soft)
    invoices_pi = posted.filtered(lambda i: not i.progressivo_invio)

    if invoices_pi:
        message = "Progressivo invio mancante per "

        if len(invoices_pi) == 1:
            message += "la fattura "
        else:
            message += "le fatture:\n"

        message += "\n".join(invoices_pi.mapped("name"))
        raise exceptions.ValidationError(message)

    invoices_b = posted.filtered(lambda i: i.amount_total >= 77.47 and math.isclose(i.l10n_it_stamp_duty, .0))

    if invoices_b:
        message = "Bollo mancante per "

        if len(invoices_b) == 1:
            message += "la fattura "
        else:
            message += "le fatture:\n"

        message += "\n".join(invoices_b.mapped("name"))
        raise exceptions.ValidationError(message)

    return posted

def button_draft(self):
    res = AccountMoveOdoo.button_draft(self=self)
    return res

def _get_move_display_name(self, show_ref=False):
    self.ensure_one()
    name = {
        "out_invoice": "Fattura",
        "out_refund": "Nota di credito",
        "in_invoice": "Fattura fornitore",
        "in_refund": "Nota di credito fornitore",
        "out_receipt": "Ricevuta",
        "in_receipt": "Ricevuta fornitore",
        "entry": "Bozza"
    }[self.move_type]
    name += " "

    if not self.name or self.name == "/":
        name += "in bozza"

    else:
        name += f"n. {self.name}"

        if self.env.context.get("input_full_display_name"):
            if self.partner_id:
                name += f", {self.partner_id.name}"

            if self.date:
                name += f", {format_date(self.env, self.date)}"

    return name + (f" ({shorten(self.ref, width=50)})" if show_ref and self.ref else "")

AccountMoveEdi._post = _post
AccountMoveEdi.button_draft = button_draft
AccountMoveOdoo._get_move_display_name = _get_move_display_name
