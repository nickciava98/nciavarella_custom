from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    numero_civico = fields.Char(
        compute="_compute_numero_civico",
        inverse="_inverse_numero_civico"
    )

    @api.depends("partner_id", "partner_id.numero_civico")
    def _compute_numero_civico(self):
        for company in self:
            company.numero_civico = company.partner_id.numero_civico \
                if company.partner_id and company.partner_id.numero_civico else False

    def _inverse_numero_civico(self):
        for company in self:
            company.partner_id.numero_civico = company.numero_civico
