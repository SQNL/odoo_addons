# -*- coding: utf-8 -*-
import json
from integration import integration as pms

res = pms.authenticate_credentials()
data = json.loads(res.text)
token = data.get('accessToken')

invoice_data = pms.send_invoice_data(token=token)
print(invoice_data.text)

payment_data = pms.send_payment_data(token=token)
print(payment_data.text)
