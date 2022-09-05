# -*- coding: utf-8 -*-
{
    'name': "account_loans_src",

    'summary': """
       Management of money loans and payments
       """,

    'description': """
        Management of money loans and payments
    """,

    'author': "Ateneolab <oleyet@ateneolab.com>",
    'website': "http://www.ateneolab.com",

    'category': 'account',
    'version': '14.1.0.4',

    'depends': ['base', 'account', 'account_asset'],

    'data': [
        'data/ir_sequence_data.xml',
        'data/journal.xml',
        'security/ir.model.access.csv',
        'views/loans_views.xml',
        'views/menu.views.xml',
        'security/loans_security.xml',
    ],
}
