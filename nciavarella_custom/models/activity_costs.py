import math

from odoo import models, fields, api, exceptions, _


class ActivityCosts(models.Model):
    _name = "activity.costs"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Activity Costs"

    name = fields.Char(
        size=4,
        tracking=True,
        copy=False,
        string="Periodo d'imposta"
    )
    total_invoiced = fields.Float(
        compute="_compute_total_invoiced",
        string="Totale fatturato"
    )
    deduction = fields.Float(
        compute="_compute_deduction",
        string="Deduzione"
    )
    total_taxable = fields.Float(
        compute="_compute_total_taxable",
        string="Imponibile",
        help="Coefficiente di redditività x Totale fatturato"
    )
    gross_income = fields.Float(
        compute="_compute_gross_income",
        string="Reddito Lordo"
    )
    total_down_payments = fields.Float(
        compute="_compute_total_down_payments",
        string="Totale acconti",
        help="Totale degli acconti da fattura"
    )
    remaining_balance = fields.Float(
        compute="_compute_remaining_balance",
        string="Saldo rimanente"
    )
    tax_id = fields.Float(
        tracking=True,
        copy=True,
        string="Imposta sostitutiva",
        help="Aliquota imposta sostitutiva Regime Forfettario"
    )
    total_taxes_due = fields.Float(
        compute="_compute_total_taxes_due",
        string="Imposta sostitutiva (Saldo)"
    )
    total_taxes_down_payment = fields.Float(
        compute="_compute_total_taxes_down_payment",
        string="Imposta sostitutiva (Acconto)"
    )
    total_stamp_taxes = fields.Float(
        compute="_compute_total_stamp_taxes",
        string="Imposte di bollo"
    )
    welfare_id = fields.Float(
        tracking=True,
        copy=True,
        string="Gestione Separata INPS"
    )
    total_welfare_due = fields.Float(
        compute="_compute_total_welfare_due",
        string="Gestione Separata INPS (Saldo)"
    )
    total_welfare_down_payment = fields.Float(
        compute="_compute_total_welfare_down_payment",
        string="Gestione Separata INPS (Acconto)"
    )
    year_cash_flow = fields.Float(
        compute="_compute_year_cash_flow",
        string="Netto annuo",
        help="Importo residuo al netto di imposte e contributi previdenziali"
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.ref("base.main_company").currency_id
    )
    taxes_previous_down_payment = fields.Float(
        string="Imposta sostitutiva (Acconto precedente)"
    )
    welfare_previous_down_payment = fields.Float(
        string="Gestione Separata INPS (Acconto precedente)"
    )
    total_due = fields.Float(
        compute="_compute_total_due",
        string="Totale da versare"
    )
    profitability_coefficient = fields.Float(
        copy=True,
        string="Redditività"
    )
    correzione = fields.Float(
        default=.0,
        copy=False,
        string="Correzione [€]"
    )

    def _check_name_is_year(self):
        if self.name:
            is_year = True

            try:
                int(self.name)
            except:
                is_year = False

            if not is_year:
                raise exceptions.UserError(f"Il periodo d'imposta inserito ({self.name}) non è corretto!")

            return True

    @api.constrains("name")
    def _constrains_name(self):
        for cost in self:
            cost._check_name_is_year()

    @api.depends("profitability_coefficient", "total_invoiced")
    def _compute_deduction(self):
        for line in self:
            line.deduction = (1 - line.profitability_coefficient) * line.total_invoiced

    @api.depends("profitability_coefficient", "total_invoiced")
    def _compute_gross_income(self):
        for line in self:
            line.gross_income = math.ceil(line.profitability_coefficient * line.total_invoiced)

    @api.depends("total_taxes_due", "total_taxes_down_payment", "total_welfare_due",
                 "total_welfare_down_payment", "total_stamp_taxes")
    def _compute_total_due(self):
        for line in self:
            line.total_due = sum([
                line.total_taxes_due,
                line.total_taxes_down_payment,
                line.total_welfare_due,
                line.total_welfare_down_payment,
                line.total_stamp_taxes
            ])

    @api.depends("name", "correzione")
    def _compute_total_invoiced(self):
        for line in self:
            line.total_invoiced = line.correzione

            if line.name and line._check_name_is_year():
                payment_ids = self.env["account.payment"].search(
                    [("date", ">=", f"{line.name}-01-01"),
                     ("date", "<=", f"{line.name}-12-31"),
                     ("partner_type", "=", "customer")]
                )

                if payment_ids:
                    line.total_invoiced += sum([
                        payment_id.amount for payment_id in payment_ids
                    ])

    @api.depends("gross_income", "welfare_previous_down_payment")
    def _compute_total_taxable(self):
        for line in self:
            line.total_taxable = math.ceil(line.gross_income - (2.25 * line.welfare_previous_down_payment))

    @api.depends("name")
    def _compute_total_down_payments(self):
        for line in self:
            line.total_down_payments = .0

            if line.name and line._check_name_is_year():
                payment_ids = self.env["account.payment"].search(
                    [("date", ">=", f"{line.name}-01-01"),
                     ("date", "<=", f"{line.name}-12-31"),
                     ("partner_type", "=", "customer")]
                )

                if payment_ids:
                    invoice_ids = payment_ids.mapped("reconciled_invoice_ids")

                    if invoice_ids:
                        line.total_down_payments += sum([
                            invoice_id.invoice_down_payment for invoice_id in invoice_ids
                        ])

    @api.depends("total_due", "total_stamp_taxes", "total_down_payments")
    def _compute_remaining_balance(self):
        for line in self:
            line.remaining_balance = sum([line.total_due, line.total_stamp_taxes]) - line.total_down_payments

    @api.depends("tax_id", "total_taxable", "taxes_previous_down_payment")
    def _compute_total_taxes_due(self):
        for line in self:
            line.total_taxes_due = math.ceil(line.tax_id * line.total_taxable - line.taxes_previous_down_payment)

    @api.depends("tax_id", "total_taxable")
    def _compute_total_taxes_down_payment(self):
        for line in self:
            line.total_taxes_down_payment = math.ceil(line.tax_id * line.total_taxable)

    @api.depends("name")
    def _compute_total_stamp_taxes(self):
        for line in self:
            line.total_stamp_taxes = .0

            if line.name and line._check_name_is_year():
                payment_ids = self.env["account.payment"].search(
                    [("date", ">=", f"{line.name}-01-01"),
                     ("date", "<=", f"{line.name}-12-31"),
                     ("partner_type", "=", "customer")]
                )

                if payment_ids:
                    invoice_ids = payment_ids.mapped("reconciled_invoice_ids")

                    if invoice_ids:
                        line.total_stamp_taxes += sum([
                            invoice_id.l10n_it_stamp_duty for invoice_id in invoice_ids
                        ])

    @api.depends("welfare_id", "gross_income", "welfare_previous_down_payment")
    def _compute_total_welfare_due(self):
        for line in self:
            line.total_welfare_due = math.ceil(line.welfare_id * line.gross_income - line.welfare_previous_down_payment)

    @api.depends("welfare_id", "gross_income")
    def _compute_total_welfare_down_payment(self):
        for line in self:
            line.total_welfare_down_payment = math.ceil(.8 * line.welfare_id * line.gross_income)

    @api.depends("total_invoiced", "total_due")
    def _compute_year_cash_flow(self):
        for line in self:
            line.year_cash_flow = line.total_invoiced - line.total_due

    _sql_constraints = [
        ("unique_name", "unique(name)", "Il periodo d'imposta deve essere univoco!")
    ]
