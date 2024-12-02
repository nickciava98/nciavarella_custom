from odoo import models, fields


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _partner_ids_domain(self):
        return [("id", "in", self.env.context.get("allowed_partner_ids", []))]

    partner_ids = fields.Many2many(
        domain=_partner_ids_domain
    )
