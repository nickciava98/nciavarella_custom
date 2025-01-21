from odoo import models, fields, api
from odoo.addons.nciavarella_custom.models.account_analytic_line import MESE_COMPETENZA_SELECTION


class TimesheetAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    valore = fields.Monetary(
        currency_field="currency_id",
        group_operator="sum",
        readonly=True,
        string="Valore"
    )
    netto_presunto = fields.Monetary(
        currency_field="currency_id",
        group_operator="sum",
        readonly=True,
        string="Netto Presunto"
    )
    mese_competenza = fields.Selection(
        selection=MESE_COMPETENZA_SELECTION,
        readonly=True,
        string="Mese Competenza"
    )
    anno_competenza = fields.Char(
        readonly=True,
        string="Anno Competenza"
    )
    competenza = fields.Date(
        readonly=True,
        string="Competenza"
    )
    trimestre = fields.Integer(
        readonly=True,
        string="Trimestre"
    )

    @api.model
    def _select(self):
        return super()._select() + """,
            A.valore AS valore,
            A.netto_presunto AS netto_presunto,
            A.mese_competenza AS mese_competenza,
            A.anno_competenza AS anno_competenza,
            A.competenza AS competenza,
            A.trimestre AS trimestre
        """
