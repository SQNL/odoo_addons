# -*- coding: utf-8 -*-

import json
import requests
from requests.adapters import HTTPAdapter

from odoo import _, api, fields, models
from datetime import datetime, date
from ..models.account_loans import LoanStructureWS

import logging

_logger = logging.getLogger(__name__)


class PMSIntegrator(models.Model):
    _name = 'psm.integrator'

    @api.model
    def get_base_url(self):
        return self.env.user.company_id.pms_host

    @api.model
    def get_host(self):
        host = self.env.user.company_id.pms_host

        schema_index = host.index("//")
        host = host[schema_index + 2: len(host)]

        slash_index = host.index("/")
        host = host[:slash_index]

        return host

    @api.model
    def make_request(self, action, params, data={}, type_request='get', headers_custom={}):
        from urllib.parse import urlencode, quote_plus
        url = "%s?%s" % (self.get_base_url() + action, urlencode(params))

        session = requests.Session()
        adapter = HTTPAdapter(max_retries=3)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        r = None
        try:
            if type_request == "get":
                headers = {'user-agent': 'Odoo14:sqn_pms_integration/0.0.1', 'Connection': 'keep-alive',
                           'Host': self.get_host()}
                r = session.get(url, timeout=None, verify=False, stream=False, headers=headers)
                _logger.info(r.text)
                return r
            else:
                headers = {}
                headers.update(headers_custom)

                if type(data) == list:
                    data = json.dumps(data)
                r = requests.post(self.get_base_url() + action, data=data, json=data,
                                  headers=headers)  # working to auth
                _logger.info(r.text)
                return r
        except requests.exceptions.ConnectionError as m:
            _logger.error(u'Problemas en la conexion con SQN. Verifique que su conexion funciona adecuadamente.')
            raise requests.exceptions.ConnectionError(
                u'Problemas en el servidor con la conexion a SQN. Verifique que el servidor esta conectado adecuadamente.')
        except Exception as e:
            _logger.error(str(e))
            raise requests.exceptions.RequestException(str(e))

    def get_basic_params(self):
        return {

        }

    # Authenticate Credentials
    @api.model
    def authenticate_credentials(self):
        action = "authentication"
        params = self.get_basic_params()
        data = {
            "email": self.env.user.company_id.pms_user,
            "strategy": "local",
            "password": self.env.user.company_id.pms_pass
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        # data = "{'email':'pms@sqnlatina.com', 'strategy':'local', 'password':'supersecret'}"
        response = self.make_request(action, params, data, type_request="post", headers_custom=headers)
        data = json.loads(response.text)
        token = data.get('accessToken')
        return token

    # Send invoice data
    @api.model
    def send_invoice_data(self, token=False, data={}):
        action = "odoo-invoices"
        headers = {
            'Authorization': 'Bearer %s' % token,
            'Content-Type': 'application/json'
        }

        response = self.make_request(action, {}, data, type_request="post", headers_custom=headers)
        code = response.status_code
        return True if code in [200, 201] else False

    # Send payment data
    @api.model
    def send_payment_data(self, token=False, data={}):
        action = "odoo-payments"
        headers = {
            'Authorization': 'Bearer %s' % token,
            'Content-Type': 'application/json'
        }

        response = self.make_request(action, {}, data, type_request="post", headers_custom=headers)
        code = response.status_code
        return True if code in [200, 201] else False

    @api.model
    def send_loans_data(self, token=False, data={}):
        action = "account-loans/%s" % data.get("loans_code")
        headers = {
            'Authorization': 'Bearer %s' % token,
            'Content-Type': 'application/json'
        }

        response = self.make_request(action, {}, data, headers_custom=headers)
        data = json.loads(response.text)
        return data


    # todo:  mock de la funcion generate_data hasta que la misma se conecte con el PMS
    def mock_generate_date(self):
        loan_data = LoanStructureWS()
        loan_data.n_quota  = 3
        loan_data.total_amount = 3000
        loan_data.date_start = date.today()
        loan_data.currency = "USD"
        q1 ={ 'date': '15/12/2021', 'amount': 2000 }
        q2 = {'date': '15/01/2022', 'amount': 600}
        q3 = {'date': '15/02/2022', 'amount': 400}
        loan_data.quotas = [q1,q2,q3]
        return loan_data
