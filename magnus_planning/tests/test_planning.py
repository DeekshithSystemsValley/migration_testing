# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, UserError


class TestCommonplanning(TransactionCase):

    def setUp(self):
        super(TestCommonplanning, self).setUp()

        # customer partner
        self.partner = self.env['res.partner'].create({
            'name': 'Customer Task',
            'email': 'customer@task.com',
            'customer': True,
        })

        self.analytic_account = self.env['account.analytic.account'].create({
            'name': 'Analytic Account for Test Customer',
            'partner_id': self.partner.id,
            'code': 'TEST'
        })

        # project and tasks
        self.project_customer = self.env['project.project'].create({
            'name': 'Project X',
            'allow_planning': True,
            'partner_id': self.partner.id,
            'analytic_account_id': self.analytic_account.id,
        })
        self.task1 = self.env['project.task'].create({
            'name': 'Task One',
            'priority': '0',
            'kanban_state': 'normal',
            'project_id': self.project_customer.id,
            'partner_id': self.partner.id,
        })
        self.task2 = self.env['project.task'].create({
            'name': 'Task Two',
            'priority': '1',
            'kanban_state': 'done',
            'project_id': self.project_customer.id,
        })
        # users
        self.user_employee = self.env['res.users'].create({
            'name': 'User Employee',
            'login': 'user_employee',
            'email': 'useremployee@test.com',
            'groups_id': [(4, self.ref('magnus_planning.group_magnus_planning_user'))],
        })
        self.user_employee2 = self.env['res.users'].create({
            'name': 'User Employee 2',
            'login': 'user_employee2',
            'email': 'useremployee2@test.com',
            'groups_id': [(4, self.ref('magnus_planning.group_magnus_planning_user'))],
        })
        self.user_manager = self.env['res.users'].create({
            'name': 'User Officer',
            'login': 'user_manager',
            'email': 'usermanager@test.com',
            'groups_id': [(4, self.ref('magnus_planning.group_planning_manager'))],
        })
        # employees
        self.empl_employee = self.env['hr.employee'].create({
            'name': 'User Empl Employee',
            'user_id': self.user_employee.id,
        })
        self.empl_employee2 = self.env['hr.employee'].create({
            'name': 'User Empl Employee 2',
            'user_id': self.user_employee2.id,
        })
        self.empl_manager = self.env['hr.employee'].create({
            'name': 'User Empl Officer',
            'user_id': self.user_manager.id,
        })


class Testplanning(TestCommonplanning):

    def test_log_planning(self):
        """ Test when log planning : check analytic account, user and employee are correctly set. """
        planning = self.env['account.analytic.line']
        planning_uom = self.project_customer.analytic_account_id.company_id.project_time_mode_id
        # employee 1 log some planning on task 1
        planning1 = planning.sudo(self.user_employee.id).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my first planning',
            'unit_amount': 4,
        })
        self.assertEquals(planning1.account_id, self.project_customer.analytic_account_id, 'Analytic account should be the same as the project')
        self.assertEquals(planning1.employee_id, self.empl_employee, 'Employee should be the one of the current user')
        self.assertEquals(planning1.partner_id, self.task1.partner_id, 'Customer of task should be the same of the one set on new planning')
        self.assertEquals(planning1.product_uom_id, planning_uom, "The UoM of the planning should be the one set on the company of the analytic account.")

        # employee 1 cannot log planning for employee 2
        with self.assertRaises(AccessError):
            planning2 = planning.sudo(self.user_employee.id).create({
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'name': 'a second planning but for employee 2',
                'unit_amount': 3,
                'employee_id': self.empl_employee2.id,
            })

        # manager log planning for employee 2
        planning3 = planning.sudo(self.user_manager.id).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'a second planning but for employee 2',
            'unit_amount': 7,
            'employee_id': self.empl_employee2.id,
        })
        planning3._onchange_employee_id()
        self.assertEquals(planning3.user_id, self.user_employee2, 'planning user should be the one linked to the given employee')
        self.assertEquals(planning3.product_uom_id, planning_uom, "The UoM of the planning 3 should be the one set on the company of the analytic account.")

        # employee 1 log some planning on project (no task)
        planning4 = planning.sudo(self.user_employee.id).create({
            'project_id': self.project_customer.id,
            'name': 'my first planning',
            'unit_amount': 4,
        })
        self.assertEquals(planning4.partner_id, self.project_customer.partner_id, 'Customer of new planning should be the same of the one set project (since no task on planning)')

    def test_log_access_rights(self):
        """ Test access rights : user can update its own plannings only, and manager can change all """
        # employee 1 log some planning on task 1
        planning = self.env['account.analytic.line']
        planning1 = planning.sudo(self.user_employee.id).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my first planning',
            'unit_amount': 4,
        })
        # then employee 2 try to modify it
        with self.assertRaises(AccessError):
            planning1.sudo(self.user_employee2.id).write({
                'name': 'i try to update this planning',
                'unit_amount': 2,
            })
        # manager can modify all planning
        planning1.sudo(self.user_manager.id).write({
            'unit_amount': 8,
            'employee_id': self.empl_employee2.id,
        })
        self.assertEquals(planning1.user_id, self.user_employee2, 'Changing planning employee should change the related user')

    def test_create_unlink_project(self):
        """ Check project creation, and if necessary the analytic account generated when project should track time. """
        # create project wihtout tracking time, nor provide AA
        non_tracked_project = self.env['project.project'].create({
            'name': 'Project without planning',
            'allow_planning': False,
            'partner_id': self.partner.id,
        })
        self.assertFalse(non_tracked_project.analytic_account_id, "A non time-tracked project shouldn't generate an analytic account")

        # create a project tracking time
        tracked_project = self.env['project.project'].create({
            'name': 'Project with planning',
            'allow_planning': True,
            'partner_id': self.partner.id,
        })
        self.assertTrue(tracked_project.analytic_account_id, "A time-tracked project should generate an analytic account")
        self.assertTrue(tracked_project.analytic_account_id.active, "A time-tracked project should generate an active analytic account")
        self.assertEquals(tracked_project.partner_id, tracked_project.analytic_account_id.partner_id, "The generated AA should have the same partner as the project")
        self.assertEquals(tracked_project.name, tracked_project.analytic_account_id.name, "The generated AA should have the same name as the project")
        self.assertEquals(tracked_project.analytic_account_id.project_count, 1, "The generated AA should be linked to the project")

        # create a project without tracking time, but with analytic account
        analytic_project = self.env['project.project'].create({
            'name': 'Project without planning but with AA',
            'allow_planning': True,
            'partner_id': self.partner.id,
            'analytic_account_id': tracked_project.analytic_account_id.id,
        })
        self.assertNotEquals(analytic_project.name, tracked_project.analytic_account_id.name, "The name of the associated AA can be different from the project")
        self.assertEquals(tracked_project.analytic_account_id.project_count, 2, "The AA should be linked to 2 project")

        # analytic linked to projects containing tasks can not be removed
        task = self.env['project.task'].create({
            'name': 'task in tracked project',
            'project_id': tracked_project.id,
        })
        with self.assertRaises(UserError):
            tracked_project.analytic_account_id.unlink()

        # task can be removed, as there is no planning
        task.unlink()

        # since both projects linked to the same analytic account are empty (no task), it can be removed
        tracked_project.analytic_account_id.unlink()

    def test_transfert_project(self):
        """ Transfert task with planning to another project should not modified past plannings (they are still linked to old project. """
        planning = self.env['account.analytic.line']
        # create a second project
        self.project_customer2 = self.env['project.project'].create({
            'name': 'Project NUMBER DEUX',
            'allow_planning': True,
        })
        # employee 1 log some planning on task 1
        planning.create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my first planning',
            'unit_amount': 4,
        })

        planning_count1 = planning.search_count([('project_id', '=', self.project_customer.id)])
        planning_count2 = planning.search_count([('project_id', '=', self.project_customer2.id)])
        self.assertEquals(planning_count1, 1, "One planning in project 1")
        self.assertEquals(planning_count2, 0, "No planning in project 2")
        self.assertEquals(len(self.task1.planning_ids), 1, "The planning should be linked to task 1")

        # change project of task 1
        self.task1.write({
            'project_id': self.project_customer2.id
        })

        planning_count1 = planning.search_count([('project_id', '=', self.project_customer.id)])
        planning_count2 = planning.search_count([('project_id', '=', self.project_customer2.id)])
        self.assertEquals(planning_count1, 1, "Still one planning in project 1")
        self.assertEquals(planning_count2, 0, "No planning in project 2")
        self.assertEquals(len(self.task1.planning_ids), 1, "The planning still should be linked to task 1")

        # it is forbidden to set a task with planning without project
        with self.assertRaises(UserError):
            self.task1.write({
                'project_id': False
            })

    def test_recompute_amount_for_multiple_planning(self):
        """ Check that amount is recomputed correctly when setting unit_amount for multiple plannings at once. """
        planning = self.env['account.analytic.line']
        self.empl_employee.planning_cost = 5.0
        self.empl_employee2.planning_cost = 6.0
        # create a planning for each employee
        planning_1 = planning.sudo(self.user_employee).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': '/',
            'unit_amount': 1,
        })
        planning_2 = planning.sudo(self.user_employee2).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': '/',
            'unit_amount': 1,
        })
        plannings = planning_1 + planning_2

        # increase unit_amount to trigger amount recomputation
        plannings.sudo().write({
            'unit_amount': 2,
        })

        # since planning costs are different for both employees, we should get different amounts
        self.assertRecordValues(plannings, [{
            'amount': -10.0,
        }, {
            'amount': -12.0,
        }])
