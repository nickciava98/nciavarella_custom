from odoo import models, fields, api, _
import datetime


class ActivityCosts(models.Model):
    _name = "activity.costs"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Activity Costs"

    name = fields.Char(
        size = 4,
        tracking = True,
        copy = False,
        string = "Periodo d'imposta"
    )
    total_invoiced = fields.Float(
        compute = "_compute_total_invoiced",
        string = "Totale fatturato"
    )
    total_taxable = fields.Float(
        compute = "_compute_total_taxable",
        string = "Imponibile",
        help = "Coefficiente di redditività x Totale fatturato"
    )
    total_down_payments = fields.Float(
        compute = "_compute_total_down_payments",
        string = "Totale acconti",
        help = "Totale degli acconti da fattura"
    )
    remaining_balance = fields.Float(
        compute = "_compute_remaining_balance",
        string = "Saldo rimanente"
    )
    tax_id = fields.Float(
        tracking = True,
        copy = True,
        string = "Imposta sostitutiva",
        help = "Aliquota imposta sostitutiva Regime Forfettario"
    )
    total_taxes_due = fields.Float(
        compute = "_compute_total_taxes_due",
        string = "Imposta sostitutiva (Saldo)"
    )
    total_taxes_down_payment = fields.Float(
        compute = "_compute_total_taxes_down_payment",
        string = "Imposta sostitutiva (Acconto)"
    )
    total_stamp_taxes = fields.Float(
        compute = "_compute_total_stamp_taxes",
        string = "Imposte di bollo"
    )
    welfare_id = fields.Float(
        tracking = True,
        copy = True,
        string = "Gestione Separata INPS"
    )
    total_welfare_due = fields.Float(
        compute = "_compute_total_welfare_due",
        string = "Gestione Separata INPS (Saldo)"
    )
    total_welfare_down_payment = fields.Float(
        compute = "_compute_total_welfare_down_payment",
        string = "Gestione Separata INPS (Acconto)"
    )
    year_cash_flow = fields.Float(
        compute = "_compute_year_cash_flow",
        string = "Netto annuo",
        help = "Importo residuo al netto di imposte e contributi previdenziali"
    )
    currency_id = fields.Many2one(
        "res.currency",
        default = lambda self: self.env.ref("base.main_company").currency_id
    )
    taxes_previous_down_payment = fields.Float(
        string = "Imposta sostitutiva (Acconto precedente)"
    )
    welfare_previous_down_payment = fields.Float(
        string = "Gestione Separata INPS (Acconto precedente)"
    )
    gross_tax = fields.Float(
        compute = "_compute_gross_tax",
        string = "Imposta lorda"
    )
    net_tax = fields.Float(
        compute = "_compute_net_tax",
        string = "Imposta netta"
    )
    profitability_coefficient = fields.Float(
        copy = True,
        string = "Coefficiente di redditività"
    )
    correzione = fields.Float(
        default = 0.0,
        copy = False,
        string = "Correzione [€]"
    )

    @api.depends("total_taxes_due", "total_taxes_down_payment", "total_welfare_due",
                 "total_welfare_down_payment", "total_stamp_taxes")
    def _compute_gross_tax(self):
        for line in self:
            line.gross_tax = sum([
                line.total_taxes_due,
                line.total_taxes_down_payment,
                line.total_welfare_due,
                line.total_welfare_down_payment,
                line.total_stamp_taxes
            ])

    @api.depends("gross_tax", "taxes_previous_down_payment", "welfare_previous_down_payment")
    def _compute_net_tax(self):
        for line in self:
            line.net_tax = line.gross_tax - sum([line.taxes_previous_down_payment, line.welfare_previous_down_payment])

    @api.depends("name", "correzione")
    def _compute_total_invoiced(self):
        for line in self:
            line.total_invoiced = line.correzione
            domain = [
                "&", "&",
                ("invoice_date", ">=", line.name + "-01-01"),
                ("invoice_date", "<=", line.name + "-12-31"),
                ("payment_state", "=", "paid")
            ]
            payment_ids = []

            for invoice in self.env["account.move"].search(domain):
                for payment in invoice.payment_ids:
                    condition = (
                        datetime.date(int(line.name), 1, 1) <= payment.date <= datetime.date(int(line.name), 12, 31)
                        and payment.id not in payment_ids
                    )
                    
                    if condition:
                        line.total_invoiced += payment.amount
                        payment_ids.append(payment.id)

    @api.depends("total_invoiced", "profitability_coefficient")
    def _compute_total_taxable(self):
        for line in self:
            line.total_taxable = line.total_invoiced * line.profitability_coefficient

    @api.depends("name")
    def _compute_total_down_payments(self):
        for line in self:
            line.total_down_payments = .0
            domain = [
                "&", "&", 
                ("invoice_date", ">=", line.name + "-01-01"),
                ("invoice_date", "<=", line.name + "-12-31"), 
                ("payment_state", "=", "paid")
            ]
            
            for invoice in self.env["account.move"].search(domain):
                line.total_down_payments += invoice.invoice_down_payment

    @api.depends("net_tax", "total_stamp_taxes", "total_down_payments")
    def _compute_remaining_balance(self):
        for line in self:
            line.remaining_balance = sum([line.net_tax, line.total_stamp_taxes]) - line.total_down_payments

    @api.depends("tax_id", "total_taxable")
    def _compute_total_taxes_due(self):
        for line in self:
            line.total_taxes_due = line.tax_id * line.total_taxable

    @api.depends("total_taxes_due")
    def _compute_total_taxes_down_payment(self):
        for line in self:
            line.total_taxes_down_payment = line.total_taxes_due

    @api.depends("name")
    def _compute_total_stamp_taxes(self):
        for line in self:
            line.total_stamp_taxes = .0
            domain = [
                "&", "&", 
                ("invoice_date", ">=", line.name + "-01-01"),
                ("invoice_date", "<=", line.name + "-12-31"), 
                ("payment_state", "=", "paid")
            ]
            
            for invoice in self.env["account.move"].search(domain):
                for payment in invoice.payment_ids:
                    if payment.date <= datetime.date(int(line.name), 12, 31):
                        line.total_stamp_taxes += invoice.l10n_it_stamp_duty
                        break

    @api.depends("welfare_id", "total_taxable")
    def _compute_total_welfare_due(self):
        for line in self:
            line.total_welfare_due = line.welfare_id * line.total_taxable

    @api.depends("total_welfare_due")
    def _compute_total_welfare_down_payment(self):
        for line in self:
            line.total_welfare_down_payment = .8 * line.total_welfare_due

    @api.depends("total_invoiced", "net_tax")
    def _compute_year_cash_flow(self):
        for line in self:
            line.year_cash_flow = line.total_invoiced - line.net_tax

    _sql_constraints = [
        ("unique_name", "unique(name)", _("Year must be unique!"))
    ]
