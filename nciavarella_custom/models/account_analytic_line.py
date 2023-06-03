from odoo import models, fields, api, _
import datetime
import pytz


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _get_time_start(self):
        timezone = pytz.timezone(self.env.context.get("tz"))
        float_time_start = datetime.datetime.now().hour + (datetime.datetime.now().minute / 60)
        date_time_start = datetime.datetime(1970, 1, 1, int(float_time_start // 1), int(float_time_start % 1))
        offset = str(timezone.utcoffset(date_time_start))

        return float_time_start + int(offset[ : offset.find(":")]) + 1

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
            timezone = pytz.timezone(self.env.context.get("tz"))
            float_time_start = sum([
                float(line.create_date.strftime("%H")), float(float(line.create_date.strftime("%M")) / 60)
            ])
            float_time_start -= 24. if float_time_start >= 24 else .0
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
