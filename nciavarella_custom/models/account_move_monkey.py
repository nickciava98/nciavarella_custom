from textwrap import shorten

from odoo import fields, exceptions
from odoo.tools import float_compare, float_is_zero, format_date
from odoo.addons.account_edi.models.account_move import AccountMove as AccountMoveEdi
from odoo.addons.account.models.account_move import AccountMove as AccountMoveOdoo


def _post(self, soft=True):
    posted = AccountMoveOdoo._post(self=self, soft=soft)
    today = fields.Date.context_today(self).strftime("%Y-%m-%d")
    invoices_d = posted.filtered(
        lambda i: i.move_type in ("out_invoice", "out_refund")
                  and (i.invoice_date.strftime("%Y-%m-%d") != today or not i.invoice_date)
    )

    if invoices_d:
        invoices_d.write({"invoice_date": today})

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
        lambda i: float_compare(i.amount_total, 77.47, precision_digits=2) >= 0
                  and float_is_zero(i.l10n_it_stamp_duty, precision_digits=2)
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

    return self.env.ref("account.account_invoices", False).report_action(self)


AccountMoveEdi._post = _post
AccountMoveEdi.button_draft = button_draft
AccountMoveOdoo._get_move_display_name = _get_move_display_name
AccountMoveOdoo._get_report_base_filename = _get_report_base_filename
AccountMoveOdoo._get_mail_template = _get_mail_template
AccountMoveOdoo.action_invoice_print = action_invoice_print
