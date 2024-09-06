# -*- coding: utf-8 -*-
{
    "name": "nciavarella Custom",
    "summary": "nciavarella customizations",
    "license": "OPL-1",
    "author": "Niccolò Ciavarella",
    "category": "",
    "version": "16.0.0.34",
    "website": "http://www.nciavarella.me",
    "depends": [
        "l10n_it_edi",
        "partner_firstname",
        "hr_timesheet",
        "project",
        "onlyoffice_odoo"
    ],
    "assets": {
        "web.assets_backend": [
            "nciavarella_custom/static/src/css/backend.scss"
        ]
    },
    "data": [
        "security/ir.model.access.csv",
        "security/groups.xml",
        "data/account_report.xml",
        "data/invoice_it_template.xml",
        "data/ir_cron.xml",
        "data/mail_template.xml",
        "data/update_data.xml",
        "views/account_analytic_line_views.xml",
        "views/account_move_views.xml",
        "views/account_tax_views.xml",
        "views/activity_costs_views.xml",
        "views/product_template_views.xml",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
        "views/res_bank_views.xml",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "reports/external_layout_standard.xml",
        "reports/hr_timesheet_report.xml",
        "reports/report_bilancio.xml",
        "reports/report_fattura.xml",
        "reports/report_invoice_document.xml",
        "reports/report_contabile.xml",
        "wizards/link_invoice_timesheet_form.xml"
    ],
    "application": False,
    "installable": True
}
