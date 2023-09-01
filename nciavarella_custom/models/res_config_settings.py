from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    invoice_down_payment_settings_ids = fields.Many2many(
        "account.move.down.payment",
        string="Invoice Down Payment Settings"
    )

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
