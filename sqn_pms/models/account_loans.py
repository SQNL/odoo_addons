# -*- coding: utf-8 -*-
# © <2021> <AteneoLab>

from odoo import _, api, fields, models
from odoo.exceptions import UserError
import logging
import datetime

import json

_logger = logging.getLogger(__name__)


# todo: Estructura de datos para intercambiar
class LoanStructureWS:
    n_quota = 0  # numero de cuotas
    total_amount = 0.0  # monto total a diferir
    date_start = False  # fecha de inicio del 1er gasto
    currency = ""  # moneda MNX ó USD ó EUR
    quotas = []  # gastos diferidos, lista de diccionario con la estructura {'date': '30/12/2022', 'amount': 20}

    def __init__(self, n_quota=0, total_amount=0.0, date_start=datetime.date.today(), currency="USD", quotas=[]):
        self.n_quota = n_quota
        self.total_amount = total_amount
        self.date_start = date_start
        self.currency = currency
        self.quotas = quotas


class AccountMove(models.Model):
    _inherit = 'account.loans'

    @api.model
    def create(self, values):
        res = super(AccountMove, self).create(values)
        return res

    def generate_data(self):
        data = {
            "loans_code": self.pms_code,
            "loans_id": self._name
        }
        try:
            token = self.env.user.company_id.pms_token
            integration = self.env['psm.integrator']
            if not token or token == "":
                token = integration.authenticate_credentials()
            if token:
                data_pms_loans = integration.send_loans_data(token=token, data=data)
                if data_pms_loans:
                    # todo: crear el préstamo
                    loan_data = LoanStructureWS()
                    loan_data.n_quota = data_pms_loans.get("n_quota")
                    loan_data.total_amount = data_pms_loans.get("total_amount")
                    loan_data.date_start = data_pms_loans.get("date_start")
                    loan_data.currency = data_pms_loans.get("currency")
                    quotas = []
                    for quota in data_pms_loans.get("quotas"):
                        q = {'date': quota.get("date"), 'amount': quota.get("amount")}
                        if 'interest' in quota:
                            q.update({'interest': quota.get("interest")})
                        else:
                            q.update({'interest': 0.0})
                        if 'amort' in quota:
                            q.update({'amort': quota.get("amort")})
                        else:
                            q.update({'amort': 0.0})
                        quotas.append(q)
                    loan_data.quotas = quotas
                    return loan_data
        except Exception as e:
            _logger.error(e)
            self.pms_message = str(e)
            return e, False
