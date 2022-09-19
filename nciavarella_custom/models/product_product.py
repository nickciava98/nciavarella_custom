from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = "product.product"

    is_hourly_cost = fields.Boolean(
        store = True
    )