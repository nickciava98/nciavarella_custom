import datetime
import os.path
import shutil
import xlsxwriter
import locale
import base64
import pytz

from decimal import Decimal

from odoo import modules, models, fields, api, exceptions, _


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    def _get_time_start(self, create_date=False):
        def _convert_datetime_to_float(date_time):
            return date_time.hour + (date_time.minute / 60)

        def _get_start_date():
            user_tz = pytz.timezone(self.env.user.tz or "UTC")

            if create_date:
                return user_tz.localize(create_date)

            return datetime.datetime.now(user_tz)

        return _convert_datetime_to_float(_get_start_date())

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
        group_operator="min",
        string="Time Start"
    )
    time_end = fields.Float(
        compute="_compute_time_end",
        store=True,
        readonly=False,
        group_operator="max",
        string="Time End"
    )
    unit_amount = fields.Float(
        compute="_compute_unit_amount",
        store=True,
        readonly=False,
        group_operator="sum",
        string="Ore"
    )
    valore = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_valore",
        store=True,
        group_operator="sum",
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
        compute="_compute_competenza",
        store=True,
        readonly=False,
        string="Mese Competenza"
    )
    anno_competenza = fields.Char(
        compute="_compute_competenza",
        store=True,
        readonly=False,
        string="Anno Competenza"
    )

    @api.depends("date")
    def _compute_competenza(self):
        for line in self:
            line.mese_competenza = line.date and line.date.strftime("%m") or False
            line.anno_competenza = line.date and line.date.strftime("%Y") or False

    def pulizia_xlsx_data_action(self):
        path = modules.module.get_resource_path("nciavarella_custom", "static/xlsx_data")

        for files in os.listdir(path):
            if "temp" in files:
                continue

            p = os.path.join(path, files)

            try:
                shutil.rmtree(p)
            except OSError:
                os.remove(p)

    def esporta_prospetto_excel_action(self):
        locale.setlocale(locale.LC_ALL, "it_IT.UTF-8")
        module_path = modules.module.get_resource_path("nciavarella_custom", "static/xlsx_data")
        periodi = " - ".join(list(dict.fromkeys([
            f"{line.date.strftime('%B').capitalize()} {line.date.strftime('%y')}" for line in self
        ])))
        file_name = f"{module_path}/Prospetto Ore {periodi}.xlsx"

        def _get_workbook():
            workbook = xlsxwriter.Workbook(file_name, {"in_memory": True})
            header_format = workbook.add_format({"bold": True})
            header_format.set_align("vcenter")
            header_format_right = workbook.add_format({
                "bold": True,
                "align": "right"
            })
            header_format_right.set_align("vcenter")
            header_format_center = workbook.add_format({
                "bold": True,
                "align": "center"
            })
            header_format_center.set_align("vcenter")
            currency_format = workbook.add_format({
                "num_format": "_-* #,##0.00 €_-;-* #,##0.00 €_-;_-* -?? €_-;_-@_-",
                "align": "right"
            })
            currency_format.set_align("vcenter")
            qty_format = workbook.add_format({
                "num_format": "#,##0.00",
                "align": "right"
            })
            qty_format.set_align("vcenter")
            text_format = workbook.add_format({
                "text_wrap": True,
                "align": "left"
            })
            text_format.set_align("vcenter")
            text_center = workbook.add_format({
                "align": "center"
            })
            text_center.set_align("vcenter")
            formats = {
                "header_format": header_format,
                "header_format_center": header_format_center,
                "header_format_right": header_format_right,
                "currency_format": currency_format,
                "qty_format": qty_format,
                "text_format": text_format,
                "text_center": text_center
            }

            return workbook, formats

        workbook, formats = _get_workbook()
        worksheet = workbook.add_worksheet()

        worksheet.write(0, 0, "Data", formats.get("header_format"))
        worksheet.write(0, 1, "Dalle", formats.get("header_format_center"))
        worksheet.write(0, 2, "Alle", formats.get("header_format_center"))
        worksheet.write(0, 3, "Descrizione", formats.get("header_format"))
        worksheet.write(0, 4, "Ore impiegate", formats.get("header_format_right"))
        worksheet.write(0, 5, "Valore monetario", formats.get("header_format_right"))

        row = 1

        for progetto in self.mapped("project_id"):
            righe = self.filtered(lambda l: l.project_id.id == progetto.id)
            tot_ore = str(sum(righe.mapped("unit_amount")))

            if len(tot_ore.split(".")[1]) == 1:
                tot_ore += "0"

            tot_valore = str(sum(righe.mapped("valore")))

            if len(tot_valore.split(".")[1]) == 1:
                tot_valore += "0"

            worksheet.merge_range(
                row, 0, row, 5, f"{progetto.name} ({Decimal(tot_ore):n} Ore) [{Decimal(tot_valore):n} €]",
                formats.get("header_format")
            )
            lavori = righe.mapped("task_id")
            row += 1

            for lavoro in lavori:
                righe = self.filtered(lambda l: l.project_id.id == progetto.id and l.task_id.id == lavoro.id)
                tot_ore = str(sum(righe.mapped("unit_amount")))

                if len(tot_ore.split(".")[1]) == 1:
                    tot_ore += "0"

                tot_valore = str(sum(righe.mapped("valore")))

                if len(tot_valore.split(".")[1]) == 1:
                    tot_valore += "0"

                worksheet.merge_range(
                    row, 0, row, 5, f"{lavoro.name} ({Decimal(tot_ore):n} Ore) [{Decimal(tot_valore):n} €]",
                    formats.get("header_format")
                )
                row += 1

                for riga in righe.sorted(key=lambda l: l.date, reverse=True)[::-1]:
                    worksheet.write(row, 0, riga.date.strftime("%d/%m/%Y"), formats.get("text_format"))
                    worksheet.write(
                        row, 1, "{0:02.0f}:{1:02.0f}".format(*divmod(riga.time_start * 60, 60)),
                        formats.get("text_center")
                    )
                    worksheet.write(
                        row, 2, "{0:02.0f}:{1:02.0f}".format(*divmod(riga.time_end * 60, 60)),
                        formats.get("text_center")
                    )
                    worksheet.write(row, 3, riga.name, formats.get("text_format"))
                    worksheet.write(row, 4, riga.unit_amount, formats.get("qty_format"))
                    worksheet.write(row, 5, riga.valore, formats.get("currency_format"))

                    row += 1

        worksheet.set_column(0, 5, 30)
        workbook.close()

        with open(file_name, "rb") as file:
            file_base64 = base64.b64encode(file.read())

        attachment_id = self.env["ir.attachment"].create({
            "name": f"{file_name.split('/')[-1]}",
            "type": "binary",
            "datas": file_base64
        })
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        url = f"{base_url}/web/content/{attachment_id.id}?download=true"

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new"
        }

    @api.depends("project_id", "project_id.tariffa_oraria", "unit_amount")
    def _compute_valore(self):
        for line in self:
            line.valore = line.project_id and line.project_id.tariffa_oraria * line.unit_amount or .0

    @api.depends("create_date")
    def _compute_time_start(self):
        for line in self:
            line.time_start = line._get_time_start(line.create_date)

    @api.depends("time_start", "unit_amount")
    def _compute_time_end(self):
        for line in self:
            if line.time_start > .0 and line.unit_amount > .0:
                time_end = line.time_start + line.unit_amount

                if time_end >= 24.:
                    time_end -= 24.

            else:
                time_end = .0

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

    def unlink(self):
        if self.filtered(lambda l: l.is_confirmed or l.is_invoiced):
            raise exceptions.UserError("Impossibile eliminare delle registrazioni Confermate o Fatturate!")

        return super().unlink()
