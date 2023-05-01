# -*- coding: utf-8 -*-
{
    'name': "nciavarella Custom",
    'summary': "nciavarella customizations",
    'license': 'OPL-1',
    'author': "Niccolò Ciavarella",
    'category': '',
    'version': '15.0.3',
    'website': "http://www.nciavarella.me",
    'depends': ['sale_management', 'account'],
    'data': [
        'data/account_menuitem_delete.xml',
        'data/template_fatturapa.xml',
        'security/ir.model.access.csv',
        'security/groups.xml',
        'views/sale_order_form.xml',
        'views/account_tax_form.xml',
        'views/account_menuitem.xml',
        'views/account_move_form.xml',
        'views/account_move_tree.xml',
        'views/account_invoice_tree.xml',
        'views/activity_costs_form.xml',
        'views/activity_costs_tree.xml',
        'views/res_company_form.xml',
        'views/res_partner_form.xml',
        'report/external_layout_standard.xml',
        'report/report_saleorder_document.xml',
        'report/report_invoice_document.xml'
    ],
    'application': False,
    'installable': True
}
