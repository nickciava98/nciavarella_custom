from odoo import models, fields


class AccountInvoiceSend(models.TransientModel):
    _inherit = "account.invoice.send"

    def _partner_ids_domain(self):
        return [("id", "in", self.env.context.get("allowed_partner_ids", []))]
