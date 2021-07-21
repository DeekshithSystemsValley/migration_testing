# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# Copyright 2018-2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    # plan boolean to indicate that the analytic account is for planning or timesheet

    @api.constrains('company_id')
    def _check_timesheet_sheet_company_id(self):
        for rec in self.sudo():
            sheets = rec.line_ids.mapped('planning_sheet_id').filtered(
                lambda s: s.company_id and s.company_id != rec.company_id)
            if sheets:
                raise ValidationError(_(
                    'You cannot change the company, as this %s (%s) '
                    'is assigned to %s (%s).'
                ) % (rec._name, rec.display_name,
                     sheets[0]._name, sheets[0].display_name))


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    planning_sheet_id = fields.Many2one(
        comodel_name='magnus.planning',
        string='Sheet',
    )
    planning_sheet_state = fields.Selection(
        string='Sheet State',
        related='planning_sheet_id.state',
    )

    employee_id = fields.Many2one('hr.employee',string="Employee")

    week_id = fields.Many2one('date.range',string="Week")

    @api.multi
    def _get_sheet_domain(self):
        """ Hook for extensions """
        self.ensure_one()
        return [
            ('date_end', '>=', self.date),
            ('date_start', '<=', self.date),
            ('employee_id', '=', self.employee_id.id),
            ('company_id', 'in', [self.company_id.id, False]),
            ('state', 'in', ['new', 'draft']),
        ]

    @api.multi
    def _determine_sheet(self):
        """ Hook for extensions """
        self.ensure_one()
        return self.env['magnus.planning'].search(
            self._get_sheet_domain(),
            limit=1,
        )

    def _compute_sheet(self):
        """Links the timesheet line to the corresponding sheet"""
        for timesheet in self.filtered('project_id'):
            sheet = timesheet._determine_sheet()
            if timesheet.planning_sheet_id != sheet:
                timesheet.planning_sheet_id = sheet

    @api.multi
    @api.constrains('company_id', 'planning_sheet_id')
    def _check_company_id_planning_sheet_id(self):
        for aal in self.sudo():
            if aal.company_id and aal.planning_sheet_id.company_id and \
                    aal.company_id != aal.planning_sheet_id.company_id:
                raise ValidationError(_(
                    'You cannot create a timesheet of a different company '
                    'than the one of the timesheet sheet:'
                    '\n - %s of %s'
                    '\n - %s of %s' % (
                        aal.planning_sheet_id.complete_name,
                        aal.planning_sheet_id.company_id.name,
                        aal.name,
                        aal.company_id.name,
                    )
                ))

    @api.model
    def create(self, values):
        if not self.env.context.get('sheet_create') and 'planning_sheet_id' in values:
            del values['planning_sheet_id']
        res = super().create(values)
        res._compute_sheet()
        return res

    @api.model
    def _sheet_create(self, values):
        return self.with_context(sheet_create=True).create(values)

    @api.multi
    def write(self, values):
        self._check_state_on_write(values)
        res = super().write(values)
        if self._timesheet_should_compute_sheet(values):
            self._compute_sheet()
        return res

    @api.multi
    def unlink(self):
        self._check_state()
        return super().unlink()

    @api.multi
    def _check_state_on_write(self, values):
        """ Hook for extensions """
        if self._timesheet_should_check_write(values):
            self._check_state()

    @api.model
    def _timesheet_should_check_write(self, values):
        """ Hook for extensions """
        return bool(set(self._get_timesheet_protected_fields()) &
                    set(values.keys()))

    @api.model
    def _timesheet_should_compute_sheet(self, values):
        """ Hook for extensions """
        return any(f in self._get_sheet_affecting_fields() for f in values)

    @api.model
    def _get_timesheet_protected_fields(self):
        """ Hook for extensions """
        return [
            'name',
            'date',
            'unit_amount',
            'user_id',
            'employee_id',
            'department_id',
            'company_id',
            'task_id',
            'project_id',
            'planning_sheet_id',
        ]

    @api.model
    def _get_sheet_affecting_fields(self):
        """ Hook for extensions """
        return ['date', 'employee_id', 'project_id', 'company_id']

    @api.multi
    def _check_state(self):
        if self.env.context.get('skip_check_state'):
            return
        for line in self.filtered('planning_sheet_id'):
            if line.planning_sheet_id.state not in ['new', 'draft']:
                raise UserError(_(
                    'You cannot modify an entry in a confirmed timesheet sheet'
                    ': %s'
                ) % (
                    line.planning_sheet_id.complete_name,
                ))

    @api.multi
    def merge_timesheets(self):
        unit_amount = sum(
            [t.unit_amount for t in self])
        amount = sum([t.amount for t in self])
        self[0].write({
            'unit_amount': unit_amount,
            'amount': amount,
        })
        self[1:].unlink()
        return self[0]
