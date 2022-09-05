# -*- coding: utf-8 -*-

{
    'name': 'PMS Amortization Table Id',
    'category': 'Subscription',
    'summary': 'PMS Amortization Table Id is related to Subscription',
    'version': '0.5',
    'description': """Account Deferred Assets""",
    'depends': ['base', 'account_deferred_asset', 'account_loans_src'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/cron.xml',
        'views/res_company_view.xml',
    ],
    # 'images': ['static/description/icon.png'],
    'installable': True,
    # 'post_init_hook': 'create_missing_journal_for_acquirers',
}
