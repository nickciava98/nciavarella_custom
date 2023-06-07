from odoo import models, fields


class AccountTax(models.Model):
    _inherit = "account.tax"

    tax_description = fields.Text(
        string = "Tax Description"
    )
