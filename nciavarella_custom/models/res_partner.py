from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    codice_fiscale = fields.Char(
        size = 16,
        string = "Codice Fiscale"
    )
    codice_destinatario = fields.Char(
        size = 7,
        string = "Codice Destinatario SDI"
    )
    pec_mail = fields.Char(
        string = "PEC"
    )