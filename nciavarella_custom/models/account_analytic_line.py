import datetime
import math
import pytz

from odoo import models, fields, api, exceptions, _


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _get_time_start(self):
        if "tz" in self.env.context:
            timezone = pytz.timezone(self.env.context.get("tz"))
            float_time_start = datetime.datetime.now().hour + (datetime.datetime.now().minute / 60)
            date_time_start = datetime.datetime(
                1970, 1, 1, int(float_time_start // 1),
                int(float_time_start % 1)
            )
            offset = str(timezone.utcoffset(date_time_start))

            return float_time_start + int(offset[: offset.find(":")])

        return datetime.datetime.now().hour + (datetime.datetime.now().minute / 60) + 1

    is_invoiced = fields.Boolean(
        compute="_compute_is_invoiced",
        store=True,
        string="Invoiced?"
    )
    invoice_id = fields.Many2one(
        "account.move",
        ondelete="restrict",
        string="Invoice"
    )
    is_confirmed = fields.Boolean(
        default=False,
        string="Confirmed?"
    )
    time_start = fields.Float(
        default=_get_time_start,
        compute="_compute_time_start",
        store=True,
        readonly=False,
        string="Time Start"
    )
    time_end = fields.Float(
        compute="_compute_time_end",
        store=True,
        readonly=False,
        string="Time End"
    )
    dalle = fields.Char(
        compute="_compute_dalle",
        store=True
    )
    alle = fields.Char(
        compute="_compute_alle",
        store=True
    )
    unit_amount = fields.Float(
        compute="_compute_unit_amount",
        store=True,
        readonly=False,
        string="Ore"
    )
    valore = fields.Monetary(
        compute="_compute_valore",
        store=True,
        string="Valore"
    )

    @api.depends("time_start")
    def _compute_dalle(self):
        for line in self:
            line.dalle = "{0:02.0f}:{1:02.0f}".format(*divmod(line.time_start * 60, 60))

    @api.depends("time_start")
    def _compute_alle(self):
        for line in self:
            line.alle = "{0:02.0f}:{1:02.0f}".format(*divmod(line.time_end * 60, 60))

    @api.depends("employee_id", "employee_id.hourly_cost", "unit_amount")
    def _compute_valore(self):
        for line in self:
            line.valore = line.employee_id.hourly_cost * line.unit_amount \
                if line.employee_id and line.employee_id.hourly_cost else .0

    @api.depends("create_date")
    def _compute_time_start(self):
        for line in self:
            float_time_start = sum([
                float(line.create_date.strftime("%H")), float(float(line.create_date.strftime("%M")) / 60)
            ])
            line.time_start = float_time_start + 2

            if "tz" in self.env.context:
                timezone = pytz.timezone(self.env.context.get("tz"))
                date_time_start = datetime.datetime(1970, 1, 1, int(float_time_start // 1), int(float_time_start % 1))
                offset = str(timezone.utcoffset(date_time_start))
                line.time_start = float_time_start + int(offset[: offset.find(":")]) + 1

    @api.depends("time_start", "unit_amount")
    def _compute_time_end(self):
        for line in self:
            time_end = line.time_start + line.unit_amount if line.time_start > .0 and line.unit_amount > .0 else .0
            time_end -= 24. if time_end >= 24. else .0
            line.time_end = time_end

    @api.depends("invoice_id")
    def _compute_is_invoiced(self):
        for line in self:
            line.is_invoiced = True if line.invoice_id else False

    def link_invoice_timesheet_action(self):
        if len(self.ids) > 1 and len(list(dict.fromkeys(self.project_id.partner_id.ids))) > 1:
            raise exceptions.UserError("Non è possibile selezionare ore con clienti differenti!")

        return {
            "name": _("Link Invoice"),
            "res_model": "link.invoice.timesheet",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "tree,form",
            "views": [(False, "form")],
            "context": {
                "default_analytic_line_ids": self.ids,
                "default_invoice_ids": self.env["account.move"].search(
                    [("move_type", "=", "out_invoice"),
                     ("partner_id", "=", self[0].project_id.partner_id.id),
                     ("invoice_date", ">=", self.sorted(key=lambda line: line.date)[0].date)]
                ).ids
            },
            "target": "new"
        }

    @api.depends("time_start", "time_end")
    def _compute_unit_amount(self):
        for line in self:
            if line.time_start >= .0 and line.time_end >= .0:
                line.unit_amount = line.time_end - line.time_start
