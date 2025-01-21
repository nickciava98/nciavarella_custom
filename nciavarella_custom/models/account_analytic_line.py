import datetime
import xlsxwriter
import locale
import base64
import pytz

from decimal import Decimal
from io import BytesIO

from odoo import modules, models, fields, api, exceptions, _
from odoo.addons.nciavarella_custom.models.project_task import TIPO_ATTIVITA_SELECTION


MESE_COMPETENZA_SELECTION = [
    ("01", "Gennaio"),
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
    ("12", "Dicembre")
]


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    _order = "date desc, time_start desc, id desc"

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
    invoice_value = fields.Monetary(
        currency_field="currency_id",
        related="invoice_id.amount_total",
        store=True
    )
    is_confirmed = fields.Boolean(
        compute="_compute_is_confirmed",
        store=True,
        readonly=False,
        string="Confirmed?"
    )
    doc_cliente = fields.Char(
        string="Doc. Cliente"
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
    tipo_attivita = fields.Selection(
        selection=TIPO_ATTIVITA_SELECTION,
        compute="_compute_tipo_attivita",
        store=True,
        readonly=False,
        string="Tipo Attività"
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
        selection=MESE_COMPETENZA_SELECTION,
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
    competenza = fields.Date(
        compute="_compute_data_competenza",
        store=True,
        string="Competenza"
    )
    trimestre = fields.Integer(
        compute="_compute_trimestre",
        store=True,
        string="Trimestre"
    )
    doc_cliente_required = fields.Boolean(
        compute="_compute_doc_cliente_required"
    )
    netto_presunto = fields.Monetary(
        currency_field="currency_id",
        group_operator="sum",
        compute="_compute_netto_presunto",
        store=True,
        string="Netto Presunto"
    )

    @api.depends("date", "valore")
    def _compute_netto_presunto(self):
        for line in self:
            invoice_down_payment = .0

            if line.date:
                down_payment_ids = self.env["account.move.down.payment"].search(
                    [("date_from", "<=", line.date.strftime("%Y-%m-%d")),
                     ("date_to", ">=", line.date.strftime("%Y-%m-%d"))]
                )

                if down_payment_ids:
                    down_payment_id = down_payment_ids.filtered(
                        lambda d: d.date_from.strftime("%Y") == line.date.strftime("%Y")
                                  or d.date_to.strftime("%Y") == line.date.strftime("%Y")
                    )

                    if down_payment_id:
                        down_payment_id = down_payment_id[0]
                        invoice_down_payment = (
                            not down_payment_id.stamp_duty and down_payment_id.down_payment * line.valore
                            or down_payment_id.down_payment * line.valore + 2
                        )

            line.netto_presunto = line.valore - invoice_down_payment

    @api.depends("is_confirmed", "project_id", "project_id.conferma_automatica", "task_id",
                 "task_id.conferma_automatica")
    def _compute_doc_cliente_required(self):
        for line in self:
            line.doc_cliente_required = not line._get_conferma_automatica() and line.is_confirmed

    @api.depends("date")
    def _compute_trimestre(self):
        for line in self:
            line.trimestre = (line.date.month - 1) // 3 + 1

    @api.depends("task_id", "task_id.default_tipo_attivita")
    def _compute_tipo_attivita(self):
        for line in self:
            line.tipo_attivita = line.task_id and line.task_id.default_tipo_attivita or "consulenza"

    def _get_conferma_automatica(self):
        self.ensure_one()

        conferma_automatica = False

        if self.project_id:
            conferma_automatica = self.project_id.conferma_automatica

        if self.task_id:
            conferma_automatica = self.task_id.conferma_automatica

        return conferma_automatica

    @api.depends("project_id", "project_id.conferma_automatica", "task_id", "task_id.conferma_automatica")
    def _compute_is_confirmed(self):
        for line in self:
            line.is_confirmed = line._get_conferma_automatica()

    def open_invoice_action(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("account.action_move_out_invoice_type")
        action["res_id"] = self.invoice_id.id
        action["view_mode"] = "form"
        action["views"] = [(False, "form")]
        return action

    @api.depends("date")
    def _compute_competenza(self):
        for line in self:
            line.mese_competenza = line.date and line.date.strftime("%m") or False
            line.anno_competenza = line.date and line.date.strftime("%Y") or False

    @api.depends("mese_competenza", "anno_competenza")
    def _compute_data_competenza(self):
        for line in self:
            line.competenza = (line.anno_competenza and line.mese_competenza) and datetime.datetime(
                year=int(line.anno_competenza), month=int(line.mese_competenza), day=1
            ) or fields.Date.today()

    def conferma_action(self):
        for line in self:
            line.is_confirmed = True

    @api.onchange("doc_cliente")
    def _onchange_doc_cliente(self):
        if self._get_conferma_automatica():
            return

        self.is_confirmed = bool(self.doc_cliente)

    def esporta_prospetto_excel_action(self):
        locale.setlocale(locale.LC_ALL, "it_IT.UTF-8")
        file_data = BytesIO()
        periodi = " - ".join(list(set([
            f"{dict(self._fields['mese_competenza']._description_selection(self.env)).get(line.mese_competenza)} "
            f"{line.anno_competenza}"
            for line in self
        ])))

        def _get_workbook():
            workbook = xlsxwriter.Workbook(file_data, {"constant_memory": True})
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
        worksheet = workbook.add_worksheet(name="Progetto > Task")

        worksheet.write(0, 0, "N. Doc.", formats.get("header_format"))
        worksheet.write(0, 1, "Data", formats.get("header_format"))
        worksheet.write(0, 2, "Dalle", formats.get("header_format_center"))
        worksheet.write(0, 3, "Alle", formats.get("header_format_center"))
        worksheet.write(0, 4, "Tipo Attività", formats.get("header_format"))
        worksheet.write(0, 5, "Descrizione", formats.get("header_format"))
        worksheet.write(0, 6, "Ore impiegate", formats.get("header_format_right"))
        worksheet.write(0, 7, "Valore monetario", formats.get("header_format_right"))

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
                row, 0, row, 7, f"{progetto.name} ({Decimal(tot_ore):n} Ore) [{Decimal(tot_valore):n} €]",
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
                    row, 0, row, 7, f"{lavoro.name} ({Decimal(tot_ore):n} Ore) [{Decimal(tot_valore):n} €]",
                    formats.get("header_format")
                )
                row += 1

                for riga in righe.sorted(key=lambda l: l.date, reverse=True)[::-1]:
                    worksheet.write(row, 0, riga.doc_cliente or "/", formats.get("text_format"))
                    worksheet.write(row, 1, riga.date.strftime("%d/%m/%Y"), formats.get("text_format"))
                    worksheet.write(
                        row, 2, "{0:02.0f}:{1:02.0f}".format(*divmod(riga.time_start * 60, 60)),
                        formats.get("text_center")
                    )
                    worksheet.write(
                        row, 3, "{0:02.0f}:{1:02.0f}".format(*divmod(riga.time_end * 60, 60)),
                        formats.get("text_center")
                    )
                    tipo_attivita = dict(TIPO_ATTIVITA_SELECTION).get(riga.tipo_attivita)
                    worksheet.write(row, 4, tipo_attivita, formats.get("text_format"))
                    worksheet.write(row, 5, riga.name, formats.get("text_format"))
                    worksheet.write(row, 6, riga.unit_amount, formats.get("qty_format"))
                    worksheet.write(row, 7, riga.valore, formats.get("currency_format"))

                    row += 1

        worksheet.set_column(0, 7, 30)

        worksheet = workbook.add_worksheet(name="Giorno")

        worksheet.write(0, 0, "N. Doc.", formats.get("header_format"))
        worksheet.write(0, 1, "Data", formats.get("header_format"))
        worksheet.write(0, 2, "Dalle", formats.get("header_format_center"))
        worksheet.write(0, 3, "Alle", formats.get("header_format_center"))
        worksheet.write(0, 4, "Tipo Attività", formats.get("header_format"))
        worksheet.write(0, 5, "Descrizione", formats.get("header_format"))
        worksheet.write(0, 6, "Ore impiegate", formats.get("header_format_right"))
        worksheet.write(0, 7, "Valore monetario", formats.get("header_format_right"))

        tot_ore = str(sum(self.mapped("unit_amount")))

        if len(tot_ore.split(".")[1]) == 1:
            tot_ore += "0"

        tot_valore = str(sum(self.mapped("valore")))

        if len(tot_valore.split(".")[1]) == 1:
            tot_valore += "0"

        worksheet.merge_range(
            1, 0, 1, 7, f"{periodi} ({Decimal(tot_ore):n} Ore) [{Decimal(tot_valore):n} €]",
            formats.get("header_format")
        )

        righe_raggruppate = self.read_group(
            domain=[("id", "in", self.ids)],
            fields=["id"],
            groupby=["date:day"],
            lazy=False
        )
        row = 2

        for riga_raggruppata in righe_raggruppate:
            righe = self.search(riga_raggruppata["__domain"])
            giorno = righe[0].date
            tot_ore = str(sum(righe.mapped("unit_amount")))

            if len(tot_ore.split(".")[1]) == 1:
                tot_ore += "0"

            tot_valore = str(sum(righe.mapped("valore")))

            if len(tot_valore.split(".")[1]) == 1:
                tot_valore += "0"

            worksheet.merge_range(
                row, 0, row, 7, f"{giorno.strftime('%d/%m/%Y')} ({Decimal(tot_ore):n} Ore) [{Decimal(tot_valore):n} €]",
                formats.get("header_format")
            )
            row += 1

            for riga in righe.sorted(key=lambda l: l.time_start, reverse=True)[::-1]:
                worksheet.write(row, 0, riga.doc_cliente or "/", formats.get("text_format"))
                worksheet.write(row, 1, riga.date.strftime("%d/%m/%Y"), formats.get("text_format"))
                worksheet.write(
                    row, 2, "{0:02.0f}:{1:02.0f}".format(*divmod(riga.time_start * 60, 60)),
                    formats.get("text_center")
                )
                worksheet.write(
                    row, 3, "{0:02.0f}:{1:02.0f}".format(*divmod(riga.time_end * 60, 60)),
                    formats.get("text_center")
                )
                tipo_attivita = dict(TIPO_ATTIVITA_SELECTION).get(riga.tipo_attivita)
                worksheet.write(row, 4, tipo_attivita, formats.get("text_format"))
                worksheet.write(row, 5, riga.name, formats.get("text_format"))
                worksheet.write(row, 6, riga.unit_amount, formats.get("qty_format"))
                worksheet.write(row, 7, riga.valore, formats.get("currency_format"))

                row += 1

        worksheet.set_column(0, 7, 30)
        workbook.close()
        file_data.seek(0)

        file_base64 = base64.b64encode(file_data.read())
        attachment_id = self.env["ir.attachment"].create({
            "name": f"Prospetto Ore {periodi}.xlsx",
            "type": "binary",
            "datas": file_base64
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}?download=true",
            "target": "new"
        }

    @api.depends("task_id", "task_id.tariffa_oraria", "unit_amount")
    def _compute_valore(self):
        for line in self:
            line.valore = line.task_id and line.task_id.tariffa_oraria * line.unit_amount or .0

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

        invoice_ids = self.env["account.move"].search([
            ("move_type", "=", "out_invoice"),
            ("partner_id", "=", self[0].project_id.partner_id.id),
            ("invoice_date", ">=", self.sorted(key=lambda line: line.date)[0].date)
        ])

        return {
            "name": _("Link Invoice"),
            "res_model": "link.invoice.timesheet",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "tree,form",
            "views": [(False, "form")],
            "context": {
                "default_analytic_line_ids": self.ids,
                "default_invoice_ids": invoice_ids and invoice_ids.ids or False
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
