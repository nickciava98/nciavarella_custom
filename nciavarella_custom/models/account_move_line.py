from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_line_height(self):
        self.ensure_one()

        return len(self.name) <= 87 and "30" or "45"

    def _update_sequence(self):
        self.ensure_one()

        if self.product_id and self.product_id.product_tmpl_id and self.product_id.product_tmpl_id.bollo:
            self.sequence = 99

    @api.model
    def update_sequence(self):
        for line in self.search([("product_id", "!=", False), ("product_id.product_tmpl_id.bollo", "=", True)]):
            line.sequence = 99

    def write(self, vals):
        res = super().write(vals)

        if "product_id" in vals:
            for line in self:
                line._update_sequence()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        for line in lines:
            line._update_sequence()

        return lines
