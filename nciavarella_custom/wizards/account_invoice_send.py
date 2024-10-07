from odoo import models, fields


class AccountInvoiceSend(models.TransientModel):
    _inherit = "account.invoice.send"

    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="account_invoice_send_res_partner_rel",
        domain=lambda self: [("id", "in", self.env.context.get("allowed_partner_ids", []))],
        string="Additional Contacts"
    )
