from odoo import models, fields


class ResBank(models.Model):
    _inherit = "res.bank"

    abi = fields.Char(
        string="ABI"
    )
    cab = fields.Char(
        string="CAB"
    )
