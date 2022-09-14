# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import UserError
from functools import reduce


# Todo: Decorador para generar un asiento contable
def generatemove(function):
    """Decorador para generar el asiento contable, el modelo desde donde se llama debe tener un campo journal_id"""

    def wrap(*args, **kwargs):
        self = args[0]
        try:
            journal = self.journal_id
            currency = self.currency.id or self.env.company.currency_id.id
        except Exception as e:
            raise UserError(_("El modelo, no tiene un campo jounal_id" + "--" + e.args))
        move_data = {
            "journal_id": journal.id,
            "ref": self.name,
            "date": date.today(),
            "state": "draft",
            "currency_id": currency
        }
        lines = function(*args, **kwargs)
        move_data.update({"line_ids": lines})
        move = self.env["account.move"].create(move_data)
        move.write({"state": "posted"})
        return move

    return wrap


# todo: Estructura de datos para intercambiar
class LoanStructureWS:
    n_quota = 0  # numero de cuotas
    total_amount = 0.0  # monto total a diferir
    date_start = False  # fecha de inicio del 1er gasto
    currency = ""  # moneda MNX ó USD ó EUR
    quotas = []  # gastos diferidos, lista de diccionario con la estructura {'date': '30/12/2022', 'amount': 20}

    def __init__(self, n_quota=0, total_amount=0.0, date_start=date.today(), currency="USD", quotas=False):
        if not quotas:
            quotas = []
        self.n_quota = n_quota
        self.total_amount = total_amount
        self.date_start = date_start
        self.currency = currency
        self.quotas = quotas


class AccountLoans(models.Model):
    _name = 'account.loans'
    _description = 'account_loans_src.account_loans_src'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'

    # Calculo del monto total pendiente a pagar (Capital + Interes) - Total Pagado: amount_pending
    def _compute_amount_pending(self):
        for record in self:
            if record.account_payment_ids:
                sum = reduce(lambda a, b: a + b, record.account_payment_ids.mapped('amount'))
                record.amount_pending = record.amount_total - sum
            else:
                record.amount_pending = record.amount_total
            record.amount_pending_pivot = record.amount_pending
            if record.amount_pending == 0:
                record.state_paid = "paid"
            else:
                record.state_paid = "pending"

    # Calculo del monto total a pagar Capital + Interes: amount_total
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = record.amount_loan + record.amount_interest
            record.amount_total_pivot = record.amount_total

    # Calculo del monto pendiente del Capital: amount_capital_pending
    def _compute_capital_pending(self):
        for record in self:
            record.amount_capital_pending = record.amount_loan - (
                    record.amount_payment - record.amount_payment_interest)
            record.amount_capital_pending_pivot = record.amount_capital_pending

    # Calculo del monto total del Interes: amount_interest
    def _compute_amount_interest(self):
        for record in self:
            if record.account_asset_id:
                record.amount_interest = sum(
                    record.account_asset_id.depreciation_move_ids.mapped("amount_total"))
            else:
                record.amount_interest = 0.0

    # Calculo del monto total pagado: amount_payment
    def _compute_amount_payment(self):
        for record in self:
            if record.account_payment_ids:
                record.amount_payment = sum(
                    record.account_payment_ids.filtered(lambda a: a.state == "posted").mapped("amount"))
            else:
                record.amount_payment = 0.0

    # Calculo del monto pagado de interes: amount_payment_interest
    def _compute_amount_payment_interest(self):
        for record in self:
            if record.account_asset_id:
                record.amount_payment_interest = sum(
                    record.account_asset_id.depreciation_move_ids.filtered(lambda a: a.state == "posted").mapped(
                        "amount_total"))
                record.amount_payment_interest_pivot = record.amount_payment_interest
            else:
                record.amount_payment_interest = 0.0
                record.amount_payment_interest_pivot = record.amount_payment_interest

    # Calculo del monto pendiente del interes: amount_pending_interest
    def _compute_amount_pending_interest(self):
        for record in self:
            record.amount_pending_interest = record.amount_interest - record.amount_payment_interest
            record.amount_pending_interest_pivot = record.amount_pending_interest

    name = fields.Char(string="Code", default=lambda self: _("New"), copy=False)
    pms_code = fields.Char(string="PMS Code")
    description = fields.Char(string="Description")
    partner_id = fields.Many2one("res.partner", string="Customer")
    journal_id = fields.Many2one("account.journal", string="Bank")

    # Planificacion de los montos del Prestamo
    amount_loan = fields.Float(string="Capital amount")  # Monto Capital
    interest_loan = fields.Float(string="Interest rate")  # Tasa de Interes
    amount_interest = fields.Float(string="Interest amount",
                                   compute="_compute_amount_interest")  # Monto total de Interes
    amount_total = fields.Float(string="Total amount", compute="_compute_amount_total")  # Monto total Capital + Interes

    # Ejecucion de los montos del Prestamos
    amount_capital_pending = fields.Float(string="Capital pending",
                                          compute="_compute_capital_pending")  # Pendiente por pagar del capital
    amount_payment = fields.Float(string="Payment amount", compute="_compute_amount_payment")  # Monto total Pagado
    amount_payment_interest = fields.Float(string="Interest payment",
                                           compute="_compute_amount_payment_interest")  # Monto pagado del Interes
    amount_pending_interest = fields.Float(string="Interes pending",
                                           compute="_compute_amount_pending_interest")  # Pendiente por pagar del Interes
    amount_pending = fields.Float(string="Pending amount", compute="_compute_amount_pending") # Pendiente por pagar Total

    # Campos auxiliares para las pivot y filtros
    amount_interest_pivot = fields.Float(string="Interest amount")
    amount_total_pivot = fields.Float(string="Total amount")
    amount_pending_pivot = fields.Float(string="Pending amount")
    amount_capital_pending_pivot = fields.Float(string="Capital pending")
    amount_payment_interest_pivot = fields.Float(string="Interest payment")
    amount_pending_interest_pivot = fields.Float(string="Interes pending")




    description = fields.Char(string="Description")
    note = fields.Text(string="note")
    main_liability_account_id = fields.Many2one('account.account', string="Main liability account")
    interest_expense_account_id = fields.Many2one('account.account', string="Interest expense account")
    product_id = fields.Many2one('product.template', string="Product")
    start_date = fields.Date(string="Start date")
    end_date = fields.Date(string="End date")
    account_invoice_ids = fields.One2many("account.move", "account_loan_invoice_id", string="Invoice")
    account_payment_ids = fields.One2many("account.payment", "account_loan_id", string="Payment")
    deferred_interest_expense_ids = fields.One2many("account.move", "account_loan_expense_id",
                                                    string="Expense deferred")
    account_asset_id = fields.Many2one("account.asset", string="Deferred expense")
    account_move_id = fields.Many2one("account.move", string="Account move loan")
    currency = fields.Many2one("res.currency", string="Moneda", default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company.id)
    state = fields.Selection([('draft', 'Draft'),
                              ('in_progress', 'In action'),
                              ('closed', 'Closed')],
                             string='State', default='draft')
    state_paid = fields.Selection([('pending', 'Pending'), ('paid', 'Paid')], string="Paid State", default="pending")
    pms_message = fields.Text()

    @api.model
    def create(self, vals_list):
        if vals_list.get("name", _("New")) == _("New"):
            name = self.env["ir.sequence"].next_by_code("account.loan.seq") or _(
                "New"
            )
            vals_list["name"] = name
        if 'state_create' in vals_list:
            del vals_list["state_create"]
        result = super(AccountLoans, self).create(vals_list)
        return result

    def action_in_progress(self):
        move = self.generate_move_liability_main()
        self.write({"account_move_id": move.id})
        self.generate_deferred_expense_interest()
        self.write({'state': 'in_progress'})

    def action_closed(self):
        self.write({'state': 'closed'})

    @generatemove
    def generate_move_liability_main(self):
        """Generando movimiento contable del Pasivo principal vs Banco"""
        lines = []
        if self.currency.id != self.env.company.currency_id.id:
            lines.append(
                (0, 0, {
                    "account_id": self.journal_id.payment_debit_account_id.id,
                    "amount_currency": self.amount_loan,
                    "debit": round(
                        self.currency._convert(self.amount_loan, self.env.company.currency_id, self.env.company,
                                               date.today()), 2),
                    "credit": 0.0,
                    "currency_id": self.currency.id
                },))
            lines.append(
                (0, 0, {
                    "account_id": self.main_liability_account_id.id,
                    "amount_currency": self.amount_loan * -1,
                    "credit": round(
                        self.currency._convert(self.amount_loan, self.env.company.currency_id, self.env.company,
                                               date.today()), 2),
                    "debit": 0.0,
                    "currency_id": self.currency.id
                },))
        else:
            lines.append(
                (0, 0, {
                    "account_id": self.journal_id.payment_debit_account_id.id,
                    "debit": self.amount_loan,
                    "credit": 0.00,
                },))
            lines.append(
                (0, 0, {
                    "account_id": self.main_liability_account_id.id,
                    "debit": 0.00,
                    "credit": self.amount_loan,
                },))
        return lines

    def generate_deferred_expense_interest(self):
        """Generando el Gasto diferido para el interes"""

        def date_convert(date_str):
            result_date = datetime.strptime(date_str, '%Y/%m/%d')
            return result_date.date()

        loan_data = LoanStructureWS()
        loan_data = self.generate_data()
        if not loan_data:
            raise UserError(_("Error getting dats for loans: {0} from PMS.".format(self.pms_code)))
        obj_journal = self.env['account.journal'].search([('code', '=', 'DEI')], limit=1)
        x = loan_data.total_amount
        if obj_journal:
            asset = {
                'name': "Deferred expense interest for {}".format(self.name),
                'asset_type': 'expense',
                'journal_id': obj_journal.id,
                'account_loan_id': self.id,
                'account_depreciation_expense_id': self.interest_expense_account_id.id,
                'account_depreciation_id': self.product_id.property_account_expense_id.id if self.product_id.property_account_expense_id.id else self.product_id.categ_id.property_account_expense_categ_id.id,
                'original_value': loan_data.total_amount,
                'method_number': loan_data.n_quota,
                'method_period': '1',
                'currency_id': loan_data.currency
            }
            move = self.env["account.asset"].create(asset)
            self.write({'account_asset_id': move.id})
            self.account_asset_id.compute_depreciation_board()

            for index, quota in enumerate(loan_data.quotas):
                self.account_asset_id.depreciation_move_ids[index].date = quota.get('date')
                self.account_asset_id.depreciation_move_ids[index].amount_total = quota.get('amount')
                self.account_asset_id.depreciation_move_ids[index].interest_loan = quota.get('interest')
                self.account_asset_id.depreciation_move_ids[index].amort_loan = quota.get('amort')

            self.account_asset_id.validate()


class AccountMove(models.Model):
    _inherit = "account.move"

    account_loan_invoice_id = fields.Many2one("account.loans", string="Loan")
    account_loan_expense_id = fields.Many2one("account.loans", string="Loan")
    interest_loan = fields.Float(string="Interest")
    amort_loan = fields.Float(string="Amort")


class AccountAsset(models.Model):
    _inherit = "account.asset"

    account_loan_id = fields.Many2one("account.loans", string="Loan")

    def validate(self):
        result = super(AccountAsset, self).validate()
        loan = self.env["account.loans"].search([('account_asset_id', '=', self.id)], limit=1)
        if loan:
            for move in self.depreciation_move_ids:
                move.write({'account_loan_expense_id': loan.id})
        return result


class AccountPayment(models.Model):
    _inherit = "account.payment"

    account_loan_id = fields.Many2one("account.loans", string="Loan")


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    account_loan_id = fields.Many2one("account.loans", string="Loans")

    def _create_payment_vals_from_wizard(self):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
        if self.account_loan_id:
            payment_vals['account_loan_id'] = self.account_loan_id.id
        return payment_vals
