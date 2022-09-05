# -*- coding: utf-8 -*-

from integration import integration as pms

pms.send_invoice_data()

# import requests
#
# r = requests.post('http://ec2-54-160-91-63.compute-1.amazonaws.com:3030/authentication',
#               {'email': 'pms@sqnlatina.com', 'strategy': 'local', 'password': 'supersecret'},
#               {'email': 'pms@sqnlatina.com', 'strategy': 'local', 'password': 'supersecret'},
#               headers={'Content-Type': 'application/x-www-form-urlencoded'})
# print(r.text)