from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    company_informations = fields.Text(
        compute="_compute_company_informations_override"
    )
    invoice_down_payment_settings_ids = fields.Many2many(
        "account.move.down.payment",
        string="Invoice Down Payment Settings"
    )

    @api.depends("company_id")
    def _compute_company_informations_override(self):
        for setting in self:
            company = setting.company_id
            setting.company_informations = False

            if not company:
                continue

            row1 = (
                (company.partner_id.street or "/") if not company.partner_id.numero_civico
                else f"{company.partner_id.street or '/'}, {company.partner_id.numero_civico or '/'}"
            )
            row2 = company.partner_id.street2
            state_id = (
                company.partner_id.state_id.code or company.partner_id.state_id.name or "/"
                if company.partner_id.country_id and company.partner_id.country_id.code == "IT"
                else company.partner_id.state_id.name or company.partner_id.state_id.code or "/"
            )
            row3 = (
                f"{company.partner_id.zip or '00000'}, {company.partner_id.city or '/'} "
                f"({state_id}), {company.partner_id.country_id.name or '/'}"
            )
            setting.company_informations = "\n".join([row for row in [row1, row2, row3] if row])

    def set_values(self):
        res = super().set_values()

        if self.invoice_down_payment_settings_ids:
            self.env["ir.config_parameter"].set_param(
                "nciavarella_custom.invoice_down_payment_settings_ids", self.invoice_down_payment_settings_ids.ids
            )

        return res

    @api.model
    def get_values(self):
        res = super().get_values()
        invoice_down_payment_settings_ids = self.env["ir.config_parameter"].sudo().get_param(
            "nciavarella_custom.invoice_down_payment_settings_ids"
        )

        if invoice_down_payment_settings_ids:
            res.update(
                invoice_down_payment_settings_ids=self.env["account.move.down.payment"].search(
                    [("id", "in", invoice_down_payment_settings_ids.strip("][").split(", "))]
                )
            )

        return res
