# -*- coding: utf-8 -*-
# © <2021> <AteneoLab>

from odoo import _, api, fields, models
import logging
import datetime

from ..integration import integration

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = 'res.company'

    pms_token = fields.Text()
    pms_host = fields.Char()
    pms_user = fields.Char()
    pms_pass = fields.Char()

    def renew_token(self):
        integration = self.env['psm.integrator']
        token = integration.authenticate_credentials()
        self.env.user.company_id.write({
            "pms_token": token,
        })

    def sync_pms_invoices(self):
        invoices = self.env['account.move'].search(
            [('pms_id', 'not in', [False, None]), ('state', 'in', ['open', 'posted']),
             ('move_type', '=', 'out_invoice'), ('synced', '=', False)])

        for inv in invoices:
            inv.send_pms()

    def sync_pms_payments(self):
        # payment_ids = self.env['account.move'].search(
        #     [('payment_id', 'not in', [False]), ('synced', '=', False), ('state', 'in', ['open', 'posted'])])

        # for item in payment_ids:
            #item.send_paymet_pms()
        self.env['account.move'].send_payment_pms()
