# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_project_planning_synchro = fields.Boolean("Awesome planning")
    module_project_planning_holidays = fields.Boolean("Leaves")
    project_time_mode_id = fields.Many2one(
        'uom.uom', related='company_id.project_time_mode_id', string='Project Time Unit', readonly=False,
        help="This will set the unit of measure used in projects and tasks.\n"
             "If you use the planning linked to projects, don't "
             "forget to setup the right unit of measure in your employees.")
    planning_encode_uom_id = fields.Many2one('uom.uom', string="Encoding Unit",
        related='company_id.planning_encode_uom_id', readonly=False,
        help="""This will set the unit of measure used to encode planning. This will simply provide tools
        and widgets to help the encoding. All reporting will still be expressed in hours (default value).""")
