import math

from odoo import models, fields, api, _
import datetime
import pytz


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _get_time_start(self):
        if "tz" in self.env.context:
            timezone = pytz.timezone(self.env.context.get("tz"))
            float_time_start = datetime.datetime.now().hour + (datetime.datetime.now().minute / 60)
            date_time_start = datetime.datetime(1970, 1, 1, int(float_time_start // 1), int(float_time_start % 1))
            offset = str(timezone.utcoffset(date_time_start))

            return float_time_start + int(offset[ : offset.find(":")]) + 1

        return datetime.datetime.now().hour + (datetime.datetime.now().minute / 60) + 2

    is_invoiced = fields.Boolean(
        compute = "_compute_is_invoiced",
        store = True,
        string = "Invoiced?"
    )
    invoice_id = fields.Many2one(
        "account.move",
        ondelete = "restrict",
        string = "Invoice"
    )
    is_confirmed = fields.Boolean(
        default = False,
        string = "Confirmed?"
    )
    time_start = fields.Float(
        default = _get_time_start,
        compute = "_compute_time_start",
        store = True,
        readonly = False,
        string = "Time Start"
    )
    time_end = fields.Float(
        compute = "_compute_time_end",
        store = True,
        readonly = False,
        string = "Time End"
    )

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
                line.time_start = float_time_start + int(offset[ : offset.find(":")]) + 1

    @api.depends("time_start", "unit_amount")
    def _compute_time_end(self):
        for line in self:
            time_end = line.time_start + line.unit_amount if line.time_start > 0 and line.unit_amount > 0 else .0
            time_end -= 24. if time_end >= 24 else .0
            line.time_end = time_end

    @api.depends("invoice_id")
    def _compute_is_invoiced(self):
        for line in self:
            line.is_invoiced = True if line.invoice_id else False

    def link_invoice_timesheet_action(self):
        return {
            "name": _("Link Invoice"),
            "res_model": "link.invoice.timesheet",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "tree,form",
            "views": [(False, "form")],
            "context": {
                "default_analytic_line_ids": self.ids
            },
            "target": "new"
        }

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if "time_start" in val and "time_end" in val and "unit_amount" in val:
                time_start = val.get("time_start")
                time_end = val.get("time_end")
                unit_amount = val.get("unit_amount")
                val["unit_amount"] = time_end - time_start \
                    if math.isclose(unit_amount, .0) and time_start > 0 and time_end > 0 else .0

        return super().create(vals)
