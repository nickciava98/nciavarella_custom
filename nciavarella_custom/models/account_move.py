import html2text

from odoo import models, fields, api, exceptions, SUPERUSER_ID


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

    def action_invoice_sent(self):
        action = super().action_invoice_sent()
        default_partner_ids = [self.partner_id.id]
        allowed_partner_ids = [self.partner_id.id] + self.partner_id.child_ids.ids

        action["context"].update({
            "default_partner_ids": default_partner_ids,
            "allowed_partner_ids": allowed_partner_ids
        })

        return action

    @api.constrains("progressivo_invio")
    def _constrains_progressivo_invio(self):
        invoice_names = ""

        for move in self.filtered("progressivo_invio"):
            invoices = self.search(
                [("id", "!=", move.id), ("progressivo_invio", "=", move.progressivo_invio)]
            )

            if invoices:
                invoice_names += "\n".join(invoices.mapped("name"))

        raise exceptions.ValidationError(
            f"Il Progressivo invio deve essere univoco!\n"
            f"Lo stesso progressivo è stato trovato nelle seguenti fatture:\n"
            f"{invoice_names}"
        )

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
        for move in self:
            move.show_reset_to_draft_button = move.state != "draft"

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
            now = fields.Datetime.now()
            body = (
                f"Fattura elettronica generata il {now.strftime('%d/%m/%Y')} "
                f"alle {now.strftime('%H:%M')} "
                f"da {self.env.user.display_name}"
            )
            invoice.message_post(body=body)

        return posted

    @api.depends("invoice_line_ids", "invoice_line_ids.tax_ids")
    def _compute_tax_ids(self):
        for move in self:
            move.tax_ids = (
                (move.invoice_line_ids and move.invoice_line_ids.mapped("tax_ids"))
                and move.invoice_line_ids.tax_ids.ids or False
            )

    @api.depends("invoice_date")
    def _compute_down_payment_id(self):
        for move in self:
            move.down_payment_id = False

            if not move.invoice_date:
                continue

            down_payment_ids = self.env["account.move.down.payment"].search(
                [("date_from", "<=", move.invoice_date.strftime("%Y-%m-%d")),
                 ("date_to", ">=", move.invoice_date.strftime("%Y-%m-%d"))]
            )

            if not down_payment_ids:
                continue

            down_payment_id = down_payment_ids.filtered(
                lambda d: d.date_from.strftime("%Y") == move.invoice_date.strftime("%Y")
                          or d.date_to.strftime("%Y") == move.invoice_date.strftime("%Y")
            )

            if not down_payment_id:
                continue

            move.down_payment_id = down_payment_id[0]

    def update_invoice_down_payment_action(self):
        self.with_context(no_create_write=True)._compute_invoice_down_payment()

    @api.depends("move_type", "invoice_date", "amount_total", "down_payment_id", "down_payment_id.stamp_duty",
                 "l10n_it_stamp_duty", "invoice_line_ids", "invoice_line_ids.quantity", "invoice_line_ids.price_unit",
                 "invoice_line_ids.tax_ids")
    def _compute_invoice_down_payment(self):
        for move in self:
            move.invoice_down_payment = .0

            if move.move_type in ("out_invoice", "out_receipt") and move.invoice_date and move.down_payment_id:
                move.invoice_down_payment = (
                    not move.down_payment_id.stamp_duty and move.down_payment_id.down_payment * move.amount_total
                    or move.down_payment_id.down_payment * move.amount_total + move.l10n_it_stamp_duty
                )

    @api.depends("amount_total", "invoice_down_payment")
    def _compute_cash_flow(self):
        for move in self:
            move.cash_flow = move.amount_total - move.invoice_down_payment

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

    def _l10n_it_edi_prepare_fatturapa_line_details(self, reverse_charge_refund=False, is_downpayment=False,
                                                    convert_to_euros=True):
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
    def update_account_move_report_name(self):
        self = self.with_user(SUPERUSER_ID)
        account_invoices_id = self.env.ref(xml_id="account.account_invoices", raise_if_not_found=False)

        if account_invoices_id:
            account_invoices_id = account_invoices_id.sudo()
            data = {
                "attachment": (
                    "(object.state == 'posted') and ((object._get_move_display_name()).replace('/','.')+'.pdf')"
                )
            }
            report = "nciavarella_custom.report_fattura"

            if account_invoices_id.report_name != report:
                data["report_name"] = report

            if account_invoices_id.report_file != report:
                data["report_file"] = report

            account_invoices_id.write(data)

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id, view_type, **options)
        invoice_report_nopayment_id = self.env.ref("account.account_invoices_without_payment", False)

        if invoice_report_nopayment_id and invoice_report_nopayment_id.binding_model_id:
            invoice_report_nopayment_id.write({"binding_model_id": False})

        return res

    def _prepare_fatturapa_export_values(self):
        def get_vat_values(partner):
            europe = self.env.ref("base.europe", raise_if_not_found=False)
            in_eu = europe and partner.country_id and partner.country_id in europe.country_ids
            is_sm = partner.country_code == "SM"
            is_gb = partner.country_code == "GB"
            normalized_vat = partner.vat
            normalized_country = partner.country_code
            has_vat = partner.vat and not partner.vat in ["/", "NA"]

            if has_vat:
                normalized_vat = partner.vat.replace(" ", "")

                if in_eu or is_gb:
                    if not normalized_vat[:2].isdecimal():
                        normalized_vat = normalized_vat[2:]

                elif is_sm:
                    normalized_vat = normalized_vat[:2].isdecimal() and normalized_vat or normalized_vat[2:]

            if not normalized_country and partner.l10n_it_codice_fiscale:
                normalized_country = "IT"

            elif not has_vat and partner.country_id and partner.country_id.code != "IT":
                normalized_vat = "0000000"

            return {
                "vat": normalized_vat,
                "country_code": normalized_country
            }

        self.ensure_one()

        template_values = super()._prepare_fatturapa_export_values()
        is_self_invoice = self.env["account.edi.format"]._l10n_it_edi_is_self_invoice(self)
        company = self.company_id
        partner = self.commercial_partner_id
        buyer = partner if not is_self_invoice else company
        template_values["buyer_info"] = get_vat_values(buyer)

        return template_values
