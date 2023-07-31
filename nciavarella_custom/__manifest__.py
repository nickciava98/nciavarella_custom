# -*- coding: utf-8 -*-
{
    "name": "nciavarella Custom",
    "summary": "nciavarella customizations",
    "license": "OPL-1",
    "author": "Niccolò Ciavarella",
    "category": "",
    "version": "16.0.0.3",
    "website": "http://www.nciavarella.me",
    "depends": [
        "l10n_it",
        "hr_timesheet"
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/groups.xml",
        "data/account_menuitem_delete.xml",
        "views/account_analytic_line_tree.xml",
        "views/account_analytic_line_actions.xml",
        "views/account_tax_form.xml",
        "views/account_menuitem.xml",
        "views/account_move_form.xml",
        "views/account_move_tree.xml",
        "views/account_invoice_tree.xml",
        "views/activity_costs_form.xml",
        "views/activity_costs_tree.xml",
        "views/res_partner_form.xml",
        "report/external_layout_standard.xml",
        "report/report_invoice_document.xml",
        "report/hr_timesheet_report.xml",
        "wizards/link_invoice_timesheet_form.xml"
    ],
    "application": False,
    "installable": True
}
