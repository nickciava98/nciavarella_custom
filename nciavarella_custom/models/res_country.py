from odoo import models, api, exceptions, _


class ResCountry(models.Model):
    _inherit = "res.country"

    @api.model
    def update_it_address_format(self):
        country_id = self.env.ref("base.it", False)

        if not country_id:
            return

        address_format = (
            "%(street)s, %(numero_civico)s\n%(street2)s\n%(zip)s, %(city)s (%(state_code)s), %(country_name)s"
        )
        country_id.write({"address_format": address_format})

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
