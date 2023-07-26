import re

from odoo.exceptions import UserError
from stdnum.it import codicefiscale, iva

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_it_pec_email = fields.Char(
        string="Email PEC"
    )
    l10n_it_codice_fiscale = fields.Char(
        string="Codice Fiscale",
        size=16
    )
    l10n_it_pa_index = fields.Char(
        string="Codice Destinatario",
        size=7
    )

    _sql_constraints = [
        ("l10n_it_codice_fiscale",
         "CHECK(l10n_it_codice_fiscale IS NULL OR l10n_it_codice_fiscale = '' OR LENGTH(l10n_it_codice_fiscale) >= 11)",
         "Il Codice Fiscale deve essere di 11 - 16 caratteri."),
        ("l10n_it_pa_index",
         "CHECK(l10n_it_pa_index IS NULL OR l10n_it_pa_index = '' OR LENGTH(l10n_it_pa_index) >= 6)",
         "Il Codice Destinatario deve essere di 6 - 7 caratteri.")
    ]

    @api.model
    def _l10n_it_normalize_codice_fiscale(self, codice):
        if codice and re.match(r'^IT[0-9]{11}$', codice):
            return codice[2:13]

        return codice

    @api.onchange("vat", "country_id")
    def _l10n_it_onchange_vat(self):
        if not self.l10n_it_codice_fiscale and self.vat and (self.country_id.code == "IT" or self.vat.startswith("IT")):
            self.l10n_it_codice_fiscale = self._l10n_it_normalize_codice_fiscale(self.vat)
        elif self.country_id.code not in [False, "IT"]:
            self.l10n_it_codice_fiscale = ""

    @api.constrains("l10n_it_codice_fiscale")
    def validate_codice_fiscale(self):
        for record in self:
            if record.l10n_it_codice_fiscale and (
                    not codicefiscale.is_valid(record.l10n_it_codice_fiscale) and not iva.is_valid(
                    record.l10n_it_codice_fiscale)):
                raise UserError(
                    _("Invalid Codice Fiscale '%s': should be like 'MRTMTT91D08F205J' for physical person and '12345670546' or 'IT12345670546' for businesses.",
                      record.l10n_it_codice_fiscale)
                )
