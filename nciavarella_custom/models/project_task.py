from odoo import models, fields, api


TIPO_ATTIVITA_SELECTION = [
    ("analisi", "Analisi"),
    ("assistenza", "Assistenza"),
    ("collaudo", "Collaudo"),
    ("consulenza", "Consulenza"),
    ("installazione_parametrizzazione", "Installazione e Parametrizzazione"),
    ("programmazione", "Programmazione")
]


class ProjectTask(models.Model):
    _inherit = "project.task"

    currency_id = fields.Many2one(
        "res.currency",
        related="project_id.currency_id",
        store=True
    )
    tariffa_oraria = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_tariffa_oraria",
        store=True,
        readonly=False,
        string="Tariffa Oraria"
    )
    conferma_automatica = fields.Boolean(
        compute="_compute_conferma_automatica",
        store=True,
        readonly=False,
        string="Conferma Automatica?"
    )
    default_tipo_attivita = fields.Selection(
        selection=TIPO_ATTIVITA_SELECTION,
        default="programmazione",
        string="Tipo Attività"
    )
    active = fields.Boolean(
        copy=False
    )

    @api.depends("project_id", "project_id.tariffa_oraria")
    def _compute_tariffa_oraria(self):
        for task in self:
            task.tariffa_oraria = task.project_id and task.project_id.tariffa_oraria or .0

    @api.depends("project_id", "project_id.conferma_automatica")
    def _compute_conferma_automatica(self):
        for task in self:
            task.conferma_automatica = task.project_id and task.project_id.conferma_automatica or False

    @api.onchange("stage_id")
    def _onchange_stage_id(self):
        for task in self:
            if task.stage_id and task.stage_id.fase_completata:
                task.active = False
