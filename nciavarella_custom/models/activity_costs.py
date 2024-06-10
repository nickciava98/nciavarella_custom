import math
import datetime

from odoo import models, fields, api, exceptions, _


class ActivityCosts(models.Model):
    _name = "activity.costs"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Activity Costs"

    name = fields.Char(
        default=str(datetime.datetime.now().year),
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
        compute="_compute_taxes_previous_down_payment",
        store=True,
        readonly=False,
        string="Imposta sostitutiva (Acconto precedente)"
    )
    welfare_previous_down_payment = fields.Float(
        compute="_compute_welfare_previous_down_payment",
        store=True,
        readonly=False,
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
    payment_ids = fields.Many2many(
        "account.payment",
        "activity_costs_account_payment_rel",
        compute="_compute_payment_ids",
        store=True
    )
    line_ids = fields.One2many(
        "activity.costs.line",
        "activity_cost_id",
        string="Riepilogo"
    )

    @api.model
    def update_data(self):
        for cost in self.search([]):
            cost._compute_taxes_previous_down_payment()
            cost._compute_welfare_previous_down_payment()

    def _get_previous_id(self):
        self.ensure_one()

        return self.search([("name", "=", str(int(self.name) - 1))], limit=1)

    @api.depends("name")
    def _compute_taxes_previous_down_payment(self):
        for cost in self:
            previous_id = cost._get_previous_id()
            cost.taxes_previous_down_payment = previous_id and previous_id.total_taxes_down_payment or .0

    @api.depends("name")
    def _compute_welfare_previous_down_payment(self):
        for cost in self:
            previous_id = cost._get_previous_id()
            cost.welfare_previous_down_payment = previous_id and previous_id.total_welfare_down_payment or .0

    def update_line_ids(self):
        self._update_line_ids()

    def _update_line_ids(self):
        self.ensure_one()

        if not self.payment_ids:
            return

        invoices = self.payment_ids.mapped("reconciled_invoice_ids")

        if not invoices:
            return

        partner_ids = self.env["res.partner"].with_context(active_test=False).browse()

        for invoice in invoices:
            if not invoice.partner_id:
                continue

            if partner_ids and invoice.partner_id.id in partner_ids.ids:
                continue

            partner_ids |= invoice.partner_id

        if not partner_ids:
            return

        self.with_context(force_update=True).line_ids = [(5, 0)] + [(0, 0, {
            "partner_id": partner_id.id
        }) for partner_id in partner_ids]

    def write(self, values):
        res = super().write(values)

        if self.env.context.get("force_update", False) or "line_ids" in values:
            return res

        for cost in self:
            cost._update_line_ids()

        return res

    @api.depends("name")
    def _compute_payment_ids(self):
        for cost in self:
            cost.payment_ids = self.env["account.payment"].search([
                ("date", ">=", f"{cost.name}-01-01"),
                ("date", "<=", f"{cost.name}-12-31"),
                ("partner_type", "=", "customer")
            ])

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
        for cost in self:
            cost.deduction = (1 - cost.profitability_coefficient) * cost.total_invoiced

    @api.depends("profitability_coefficient", "total_invoiced")
    def _compute_gross_income(self):
        for cost in self:
            cost.gross_income = math.ceil(cost.profitability_coefficient * cost.total_invoiced)

    @api.depends("total_taxes_due", "total_taxes_down_payment", "total_welfare_due",
                 "total_welfare_down_payment", "total_stamp_taxes")
    def _compute_total_due(self):
        for cost in self:
            cost.total_due = sum([
                cost.total_taxes_due,
                cost.total_taxes_down_payment,
                cost.total_welfare_due,
                cost.total_welfare_down_payment,
                cost.total_stamp_taxes
            ])

    @api.depends("name", "correzione", "payment_ids")
    def _compute_total_invoiced(self):
        for cost in self:
            cost.total_invoiced = cost.correzione

            if cost.name and cost._check_name_is_year() and cost.payment_ids:
                cost.total_invoiced += sum(cost.payment_ids.mapped("amount"))

    @api.depends("name", "gross_income", "welfare_previous_down_payment")
    def _compute_total_taxable(self):
        for cost in self:
            previous_id = cost._get_previous_id()
            welfare_previous_due = previous_id and previous_id.total_welfare_due or .0
            cost.total_taxable = math.ceil(
                cost.gross_income - (cost.welfare_previous_down_payment + welfare_previous_due)
            )

    @api.depends("name", "payment_ids")
    def _compute_total_down_payments(self):
        for cost in self:
            cost.total_down_payments = .0

            if cost.name and cost._check_name_is_year() and cost.payment_ids:
                invoice_ids = cost.payment_ids.mapped("reconciled_invoice_ids")

                if invoice_ids:
                    cost.total_down_payments += sum([
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

    @api.depends("name", "payment_ids")
    def _compute_total_stamp_taxes(self):
        for cost in self:
            cost.total_stamp_taxes = .0

            if cost.name and cost._check_name_is_year() and cost.payment_ids:
                invoice_ids = cost.payment_ids.mapped("reconciled_invoice_ids")

                if invoice_ids:
                    cost.total_stamp_taxes += sum(cost.payment_ids.mapped("l10n_it_stamp_duty"))

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


class ActivityCostsLine(models.Model):
    _name = "activity.costs.line"
    _description = "Riepilogo attività"
    _order = "partner_id asc"

    activity_cost_id = fields.Many2one(
        "activity.costs",
        ondelete="cascade"
    )
    partner_id = fields.Many2one(
        "res.partner",
        ondelete="restrict",
        string="Cliente"
    )
    total = fields.Float(
        compute="_compute_total",
        store=True,
        string="Totale"
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="activity_cost_id.currency_id",
        store=True
    )
    cert_unica = fields.Boolean(
        default=False,
        string="Cert. Unica?"
    )

    @api.depends("partner_id", "activity_cost_id", "activity_cost_id.payment_ids")
    def _compute_total(self):
        for line in self:
            line.total = .0

            if not line.partner_id:
                continue

            invoices = line.activity_cost_id.payment_ids.mapped("reconciled_invoice_ids").filtered(
                lambda i: i.partner_id.id == line.partner_id.id
            )

            if not invoices:
                continue

            line.total = sum(invoices.mapped("amount_total"))
