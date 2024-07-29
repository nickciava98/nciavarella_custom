from odoo import models, fields, api


class TimesheetAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    valore = fields.Monetary(
        currency_field="currency_id",
        group_operator="sum",
        readonly=True,
        string="Valore"
    )
    mese_competenza = fields.Selection(
        [("01", "Gennaio"),
         ("02", "Febbraio"),
         ("03", "Marzo"),
         ("04", "Aprile"),
         ("05", "Maggio"),
         ("06", "Giugno"),
         ("07", "Luglio"),
         ("08", "Agosto"),
         ("09", "Settembre"),
         ("10", "Ottobre"),
         ("11", "Novembre"),
         ("12", "Dicembre")],
        readonly=True,
        string="Mese Competenza"
    )
    anno_competenza = fields.Char(
        readonly=True,
        string="Anno Competenza"
    )

    @api.model
    def _select(self):
        return super()._select() + """,
            A.valore AS valore,
            A.mese_competenza AS mese_competenza,
            A.anno_competenza AS anno_competenza
        """
