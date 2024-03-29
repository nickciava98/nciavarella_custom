import datetime
import math
import html2text

from odoo import models, fields, api, exceptions
from odoo.tools import format_date, float_repr
from textwrap import shorten


class AccountMove(models.Model):
    _order = "invoice_date desc, invoice_date_due desc, name desc"
    _inherit = "account.move"

    ref = fields.Char(
        copy=True,
        tracking=True,
        string="Riferimento"
    )
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
                [("id", "!=", self.id), ("progressivo_invio", "=", vals.get("progressivo_invio"))]
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
        if not self.narration:
            return ""

        return html2text.html2text(self.narration).replace("\n", " ").replace("  ", "\n")

    @api.depends("state")
    def _compute_show_reset_to_draft_button(self):
        for line in self:
            line.show_reset_to_draft_button = True if line.state != "draft" else False

    def _post(self, soft=True):
        posted = super()._post(soft=soft)

        for invoice in posted.filtered(lambda i: i.move_type in ("out_invoice", "out_refund")):
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
            body = (
                f"Fattura elettronica generata il {now.strftime('%d/%m/%Y')} "
                f"alle {now.strftime('%H:%M')} "
                f"da {self.env.user.display_name}"
            )
            invoice.message_post(body=body)

        return posted

    @api.depends("invoice_line_ids", "invoice_line_ids.tax_ids")
    def _compute_tax_ids(self):
        for line in self:
            line.tax_ids = line.invoice_line_ids.tax_ids.ids \
                if line.invoice_line_ids and line.invoice_line_ids.mapped("tax_ids") \
                else False

    @api.depends("invoice_date")
    def _compute_down_payment_id(self):
        for line in self:
            line.down_payment_id = False

            if line.invoice_date:
                down_payment_ids = self.env["account.move.down.payment"].search(
                    [("date_from", "<=", line.invoice_date.strftime("%Y-%m-%d")),
                     ("date_to", ">=", line.invoice_date.strftime("%Y-%m-%d"))]
                )

                if down_payment_ids:
                    down_payment_id = down_payment_ids.filtered(
                        lambda d: d.date_from.strftime("%Y") == line.invoice_date.strftime("%Y")
                                  or d.date_to.strftime("%Y") == line.invoice_date.strftime("%Y")
                    )

                    if down_payment_id:
                        line.down_payment_id = down_payment_id[0]

    def update_invoice_down_payment_action(self):
        self.with_context(no_create_write=True)._compute_invoice_down_payment()

    @api.depends("move_type", "invoice_date", "amount_total", "down_payment_id", "down_payment_id.stamp_duty",
                 "l10n_it_stamp_duty", "invoice_line_ids", "invoice_line_ids.quantity", "invoice_line_ids.price_unit",
                 "invoice_line_ids.tax_ids")
    def _compute_invoice_down_payment(self):
        for line in self:
            line.invoice_down_payment = .0

            if line.move_type in ("out_invoice", "out_receipt") and line.invoice_date and line.down_payment_id:
                line.invoice_down_payment = line.down_payment_id.down_payment * line.amount_total \
                    if not line.down_payment_id.stamp_duty \
                    else line.down_payment_id.down_payment * line.amount_total + line.l10n_it_stamp_duty

    @api.depends("amount_total", "invoice_down_payment")
    def _compute_cash_flow(self):
        for line in self:
            line.cash_flow = line.amount_total - line.invoice_down_payment

    def name_get(self):
        result = []

        for move in self:
            if move.move_type in ("entry", "in_receipt", "out_receipt"):
                result.append((move.id, move._get_move_display_name(show_ref=True)))

            else:
                name = [f"Fatt. n. {move.name}"]

                if move.ref:
                    name.append(f"(Rif. {move.ref})")

                if move.invoice_date:
                    name.append(f"del {move.invoice_date.strftime('%d/%m/%Y')}")

                if move.partner_id:
                    name.append(f"- {move.partner_id.name}")

                result.append((move.id, " ".join(name)))

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

    @api.model
    def _update_account_move_report_name(self):
        account_invoices_id = self.env.ref(xml_id="account.account_invoices", raise_if_not_found=False)

        if account_invoices_id:
            attachment = "(object.state == 'posted') and ((object._get_move_display_name()).replace('/','.')+'.pdf')"

            account_invoices_id.write({
                "attachment": attachment
            })

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id, view_type, **options)
        invoice_report_nopayment_id = self.env.ref(
            xml_id="account.account_invoices_without_payment", raise_if_not_found=False
        )

        if invoice_report_nopayment_id and invoice_report_nopayment_id.binding_model_id:
            invoice_report_nopayment_id.write({
                "binding_model_id": False
            })

        return res


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

    def remove_record(self):
        def format_numbers(number):
            number_splited = str(number).split(".")

            if len(number_splited) == 1:
                return "%.02f" % number

            cents = number_splited[1]

            if len(cents) > 8:
                return "%.08f" % number

            return float_repr(number, max(2, len(cents)))

        move_ids = self.env["account.move"].search([("down_payment_id", "=", self.id)])

        if not move_ids:
            self.env.cr.execute(
                "DELETE FROM account_move_down_payment_res_config_settings_rel "
                f"WHERE account_move_down_payment_id = {self.id}"
            )
            self.env.cr.commit()
            self.unlink()
            self.env.cr.commit()
            return

        config = (f"{self.date_from} > {self.date_to}: {format_numbers(self.down_payment * 100).replace('.', ',')}% "
                  f"({'con' if self.stamp_duty else 'senza'} Bollo)")
        fatture = '\n- '.join(move_ids.mapped("name"))

        raise exceptions.ValidationError(
            f"Impossibile eliminare la configurazione {config} perché associata a:\n- {fatture}"
        )


from odoo.addons.account_edi.models.account_move import AccountMove as AccountMoveEdi
from odoo.addons.account.models.account_move import AccountMove as AccountMoveOdoo

def _post(self, soft=True):
    posted = AccountMoveOdoo._post(self=self, soft=soft)
    today = datetime.datetime.today().strftime("%Y-%m-%d")
    invoices_d = posted.filtered(
        lambda i: i.move_type in ("out_invoice", "out_refund")
                  and (i.invoice_date.strftime("%Y-%m-%d") != today or not i.invoice_date)
    )

    if invoices_d:
        for invoice_d in invoices_d:
            invoice_d.write({
                "invoice_date": today
            })

    invoices_pi = posted.filtered(
        lambda i: not i.progressivo_invio and i.move_type in ("out_invoice", "out_refund")
    )

    if invoices_pi:
        message = "Progressivo invio mancante per "

        if len(invoices_pi) == 1:
            message += "la fattura "
        else:
            message += "le fatture:\n"

        message += "\n".join(invoices_pi.mapped("name"))
        raise exceptions.ValidationError(message)

    invoices_b = posted.filtered(
        lambda i: i.amount_total >= 77.47
                  and math.isclose(i.l10n_it_stamp_duty, .0)
                  and i.move_type in ("out_invoice", "out_refund")
    )

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

def _get_report_base_filename(self):
    return _get_move_display_name(self=self, show_ref=False)

def _get_mail_template(self):
    if all(move.move_type == "out_refund" for move in self):
        template = "account.email_template_edi_credit_note"
    else:
        today = fields.Date.today()
        template = "nciavarella_custom.modello_notifica_emissione_fattura"

        if all(move.move_type == "out_invoice" and move.payment_state == "not_paid" and move.invoice_date_due == today
               for move in self):
            template = "nciavarella_custom.modello_notifica_scadenza_pagamento"
        elif all(move.move_type == "out_invoice" and move.payment_state == "not_paid" and move.invoice_date_due < today
               for move in self):
            template = "nciavarella_custom.modello_stato_fattura_emessa"

    return template

def action_invoice_print(self):
    if any(not move.is_invoice(include_receipts=True) for move in self):
        raise exceptions.UserError("Possono essere stampate solo le fatture")

    self.filtered(lambda inv: not inv.is_move_sent).write({"is_move_sent": True})

    return self.env.ref(xml_id="nciavarella_custom.report_fatture", raise_if_not_found=False).report_action(self)

AccountMoveEdi._post = _post
AccountMoveEdi.button_draft = button_draft
AccountMoveOdoo._get_move_display_name = _get_move_display_name
AccountMoveOdoo._get_report_base_filename = _get_report_base_filename
AccountMoveOdoo._get_mail_template = _get_mail_template
AccountMoveOdoo.action_invoice_print = action_invoice_print
