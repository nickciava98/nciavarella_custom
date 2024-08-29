from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    bollo = fields.Boolean(
        default=False,
        string="Bollo?"
    )
