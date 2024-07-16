from odoo import models, api, exceptions, _


class ResCountry(models.Model):
    _inherit = "res.country"

    @api.constrains("address_format")
    def _check_address_format(self):
        for country in self:
            if not country.address_format:
                continue

            address_fields = (
                self.env["res.partner"]._formatting_address_fields()
                + ["state_code", "state_name", "country_code", "country_name", "company_name", "numero_civico"]
            )

            try:
                country.address_format % {i: 1 for i in address_fields}

            except (ValueError, KeyError):
                raise exceptions.UserError(_("The layout contains an invalid format key"))
