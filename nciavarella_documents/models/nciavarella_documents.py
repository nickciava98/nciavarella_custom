from odoo import models, fields, api
from datetime import datetime

class NciavarellaDocuments(models.Model):
    _name = "nciavarella.documents"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "nciavarella Documents Model"

    name = fields.Char(
        required = True,
        tracking = True
    )
    subject = fields.Char(
        required = True,
        tracking = True
    )
    partner_id = fields.Many2one(
        "res.partner",
        tracking = True
    )
    date = fields.Date(
        default = datetime.today()
    )
    message = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        default = lambda self: self.env.company.id
    )