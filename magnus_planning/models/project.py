# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class Project(models.Model):
    _inherit = "project.project"

    allow_planning = fields.Boolean("Allow plannings", default=True)
    


    @api.onchange('analytic_account_id')
    def _onchange_analytic_account(self):
        if not self.analytic_account_id and self._origin:
            self.allow_planning = False

    @api.constrains('allow_planning', 'analytic_account_id')
    def _check_allow_planning(self):
        for project in self:
            if project.allow_planning and not project.analytic_account_id:
                raise ValidationError(_('To allow planning, your project %s should have an analytic account set.' % (project.name,)))

    @api.model
    def name_create(self, name):
        """ Create a project with name_create should generate analytic account creation """
        values = {
            'name': name,
            'allow_planning': True,
            'allow_timesheet':True,
        }
        return self.create(values).name_get()[0]

    @api.model
    def create(self, values):
        """ Create an analytic account if project allow planning and don't provide one
            Note: create it before calling super() to avoid raising the ValidationError from _check_allow_planning
        """
        allow_planning = values['allow_planning'] if 'allow_planning' in values else self.default_get(['allow_planning'])['allow_planning']
        if allow_planning and not values.get('analytic_account_id'):
            analytic_account = self.env['account.analytic.account'].create({
                'name': values.get('name', _('Unknown Analytic Account')),
                'company_id': values.get('company_id', self.env.user.company_id.id),
                'partner_id': values.get('partner_id'),
                'active': True,
            })
            values['analytic_account_id'] = analytic_account.id
        return super(Project, self).create(values)

    @api.multi
    def write(self, values):
        # create the AA for project still allowing planning
        if values.get('allow_planning'):
            for project in self:
                if not project.analytic_account_id and not values.get('analytic_account_id'):
                    project._create_analytic_account()
        result = super(Project, self).write(values)
        return result


    @api.model
    def _init_data_analytic_account(self):
        self.search([('analytic_account_id', '=', False), ('allow_planning', '=', True)])._create_analytic_account()

 

class Task(models.Model):
    _inherit = "project.task"

    allow_planning = fields.Boolean("Allow plannings", related='project_id.allow_planning', help="plannings can be logged on this task.", readonly=True)

    planning_effective_hours = fields.Float("Hours Spent", compute='_compute_effective_hours', compute_sudo=True, store=True, help="Computed using the sum of the task work done.")
    

    planning_ids = fields.One2many('account.analytic.line', 'task_id', 'plannings')

    @api.depends('planning_ids.unit_amount')
    def _compute_effective_hours(self):
        for task in self:
            task.effective_hours = round(sum(task.planning_ids.mapped('unit_amount')), 2)



    # ---------------------------------------------------------
    # ORM
    # ---------------------------------------------------------



    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Set the correct label for `unit_amount`, depending on company UoM """
        result = super(Task, self)._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        result['arch'] = self.env['account.analytic.line']._apply_planning_label(result['arch'])
        return result
