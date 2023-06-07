from odoo import models, api


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    @api.model
    def _l10n_it_edi_generate_electronic_invoice_filename(self, invoice):
        return "%(country_code)s%(codice)s_%(progressive_number)s.xml" % {
            "country_code": invoice.company_id.country_id.code,
            "codice": self.env["res.partner"]._l10n_it_normalize_codice_fiscale(
                invoice.company_id.l10n_it_codice_fiscale
            ),
            "progressive_number": invoice.send_sequence,
        }
