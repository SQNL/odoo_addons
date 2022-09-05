# -*- coding: utf-8 -*-
# © <2021> <AteneoLab>

from odoo import _, fields, models, api
import logging

_logger = logging.getLogger(__name__)


class Subscription(models.Model):
    _inherit = 'sale.subscription'
    _inherits = {'account.asset': 'account_asset_id'}

    pms_id = fields.Integer(string=_(u"PMS Identifier"))

