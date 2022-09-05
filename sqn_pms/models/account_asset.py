# -*- coding: utf-8 -*-
# © <2021> <AteneoLab>

from odoo import _, api, fields, models
import logging
import datetime

import json

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    id_cf = fields.Integer('Cash Flow Id')
    synced = fields.Boolean('Sent to PMS')
    full_synced = fields.Boolean('All payments are sent')
    pms_id = fields.Integer()
    pms_message = fields.Text()

    def action_post(self):
        res = super(AccountMove, self).action_post()
        invoice_loans = True if self.move_type == 'in_invoice' and self.account_loan_invoice_id else False
        if self.move_type == 'out_invoice' or invoice_loans:  # Se envia al pms si es una factura de subs o de loans
            self.send_pms()

        return res

    @api.model
    def send_payment_pms(self):
        """
        Este método envía al PMS los pagos de las facturas. Tiene en cuenta tanto los pagos que se registran
        directamente en la factura como los que se concilian por separado.
        Puede que un pago esté en dos facturas, o que una factura tenga asociado más de un pago. Por esto, es posible
        que un pago se envía dos veces. Por ejemplo, si está asociado con varias facturas.
        Para estos casos es que se envían los datos suficientes para identificar estos escenarios.
        Se envía el id de la factura, el id del pago, el monto total del movimiento de pago y el monto conciliado con la
        factura.
        Con esos datos, en el PMS se debe manejar la información en consecuencia para registrar todo correctamente.
        """
        invoice_list = self.search(
            [('synced', '=', True),
             ('full_synced', '=', False),
             '|',
             ('subscription_id', '!=', None),
             ('manual_subscription_id', '!=', None),
             ('move_type', '=', 'out_invoice')]
        )

        invoice_list_loans = self.search(
            [('synced', '=', True),
             ('full_synced', '=', False),
             ('account_loan_invoice_id', '!=', False),
             ('move_type', '=', 'in_invoice')]
        )

        invoice_list += invoice_list_loans

        for inv in invoice_list:
            try:
                payments_widget = json.loads(inv.invoice_payments_widget)
                if not payments_widget:
                    continue

                content = payments_widget.get('content')
                data = {}
                payments = []

                move_ids = []

                for c in content:
                    move_id = c.get('move_id')
                    # Este movimiento hay que marcarlo para que no lo envíe de nuevo
                    move_payment_id = self.search([('id', '=', move_id)])
                    move_ids.append(move_payment_id)

                    payments.append({
                        # id del moviento del pago asociado, contiene el monto total, no solo el conciliado con la factura
                        "id": move_id,
                        # monto conciliado con la factura. Puede diferir del monto total del pago original.
                        "amount": c.get('amount'),
                        # monto total del pago, puede diferir del monto conciliado con la factura
                        "amount_total": move_payment_id.amount_total,
                        "payment_method_name": move_payment_id.journal_id.name,
                        # nombre con el que aparece el movimiento en los asientos contables
                        "move_name": move_payment_id.name,
                        "currency_id": move_payment_id.currency_id.id,
                        # fecha del pago (no es la fecha de conciliación con la factura, sino del pago)
                        "date": c.get('date')
                    })

                data.update({
                    "move_id": inv.id,  # id de la factura que contiene los pagos
                    "partner_id": inv.partner_id.id,
                    "id_cf": inv.id_cf or -1,
                    "payments": payments
                })

                token = self.env.user.company_id.pms_token
                integration = self.env['psm.integrator']

                if not token or token == "":
                    token = integration.authenticate_credentials()

                if not token:
                    _logger.error("No se ha podido obtener el token al enviar los pagos de la factura: %s" % inv.name)
                    continue
                # Está enviando un listado de pagos_
                _logger.info(data)
                success = integration.send_payment_data(token=token, data=[data])
                _logger.info(data)

                if not success:  # todo: ver qué se puede hacer aquí, que sea más controlado
                    continue

                for move in move_ids:
                    move.synced = True

                if inv.amount_residual == 0:
                    inv.full_synced = True
            except Exception as e:
                _logger.error(e)

    def send_pms(self):
        lines = []
        pms_id = False

        for line in self.invoice_line_ids:
            lines.append({
                "product_id": line.product_id.id,
                "quantity": line.quantity,
                "price_unit": line.price_unit
            })
            if line.subscription_id and not pms_id:
                pms_id = line.subscription_id.pms_id
        invoice_loans = True if self.move_type == 'in_invoice' and self.account_loan_invoice_id else False
        if invoice_loans:
            pms_id = self.account_loan_invoice_id.pms_code  # codigo del loans pms

        if pms_id:
            self.pms_id = pms_id
            data = [{
                "id": self.id,
                "pms_id": pms_id,  # Osmar:Si es una factura de Loans se envia el codigo del prestamo en el PMS
                "partner_id": self.partner_id.id,
                "partner_name": self.partner_id.name,
                "partner_identification": self.partner_id.id,  # todo: change for partner identification
                "amount_residual": self.residual_amount,
                "amount_untaxed": self.amount_untaxed,
                "amount_tax": self.amount_tax,
                "invoice_date": datetime.datetime.strftime(self.invoice_date, '%Y-%m-%d'),
                "invoice_date_due": datetime.datetime.strftime(self.invoice_date_due, '%Y-%m-%d'),
                "invoice_line_ids": lines[0],  # todo: it must be an array
                "id_cf": self.id_cf or -1,  # Osmar que es esto ?
                "currency_id": self.currency_id.id
            }]

            try:
                token = self.env.user.company_id.pms_token
                integration = self.env['psm.integrator']
                if not token or token == "":
                    token = integration.authenticate_credentials()
                if token:
                    _logger.info(data)
                    success = integration.send_invoice_data(token=token, data=data)
                    if success:
                        self.synced = True
            except Exception as e:
                _logger.error(e)
                self.pms_message = str(e)

    def send_cancelled_invoice_pms(self):
        pms_id = False

        for line in self.invoice_line_ids:
            if line.subscription_id and not pms_id:
                pms_id = line.subscription_id.pms_id

        if pms_id:
            data = [{
                "id": self.id,
                "pms_id": pms_id,
                "action": "cancel",
            }]

            try:
                token = self.env.user.company_id.pms_token
                integration = self.env['psm.integrator']
                if not token or token == "":
                    token = integration.authenticate_credentials()
                if token:
                    _logger.info(data)
                    success = integration.send_invoice_data(token=token, data=data)
                    if success:
                        self.synced = True
            except Exception as e:
                _logger.error(e)
                self.pms_message = str(e)
