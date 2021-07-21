# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """ The widget 'planning_uom' needs to know which UoM conversion factor and which javascript
            widget to apply, depending on th ecurrent company.
        """
        result = super(Http, self).session_info()

        company = self.env.user.company_id
        encoding_uom = company.planning_encode_uom_id

        result['planning_uom'] = encoding_uom.read(['name', 'rounding', 'planning_widget'])[0]
        result['planning_uom_factor'] = company.project_time_mode_id._compute_quantity(1.0, encoding_uom, round=False)  # convert encoding uom into stored uom to get conversion factor
        return result
