# -*- coding: utf-8 -*-
{
    'name': "nciavarella Custom Report",
    'summary': "nciavarella customization for reports",
    'license': 'OPL-1',
    'author': "Niccolò Ciavarella",
    'category': '',
    'version': '15.0.1',
    'website': "http://www.nciavarella.me",
    'depends': ['hr_timesheet', 'account', 'nciavarella_custom'],
    'data': [
        'reports/external_layout_standard.xml',
        'reports/report_timesheet.xml',
        'reports/report_invoice_document.xml'
    ],
    'application': False,
    'installable': True,
}