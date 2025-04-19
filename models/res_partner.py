import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    zalo_phone = fields.Char('Zalo Phone', help='Phone number associated with Zalo account')
    zalo_id = fields.Char('Zalo ID', help='Zalo User ID if available')
    zalo_opt_in = fields.Boolean('Zalo Opt-in', default=False, 
                                help='Customer has opted in to receive Zalo ZNS messages')
    zalo_opt_in_date = fields.Datetime('Opt-in Date', readonly=True,
                                      help='Date when customer opted in to Zalo messaging')
    
    zns_history_count = fields.Integer('ZNS Message Count', compute='_compute_zns_history_count')
    
    @api.depends('zalo_phone', 'phone', 'mobile')
    def _compute_zns_history_count(self):
        """Compute the number of ZNS messages sent to this partner"""
        for partner in self:
            domain = [('partner_id', '=', partner.id)]
            partner.zns_history_count = self.env['bom.zns.history'].search_count(domain)
    
    def write(self, vals):
        """Override write to track opt-in changes"""
        # Set opt-in date when opt-in status changes
        if 'zalo_opt_in' in vals and vals['zalo_opt_in'] and not vals.get('zalo_opt_in_date'):
            vals['zalo_opt_in_date'] = fields.Datetime.now()
        
        return super(ResPartner, self).write(vals)
    
    def action_view_zns_history(self):
        """Open ZNS history for this partner"""
        self.ensure_one()
        return {
            'name': _('ZNS Messages'),
            'type': 'ir.actions.act_window',
            'res_model': 'bom.zns.history',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
    
    def action_send_zns(self):
        """Open wizard to send ZNS message to this partner"""
        self.ensure_one()
        
        # Check if partner has a phone number for Zalo
        phone = self.zalo_phone or self.mobile or self.phone
        if not phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Partner has no phone number for Zalo messaging.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        return {
            'name': _('Send ZNS Message'),
            'type': 'ir.actions.act_window',
            'res_model': 'bom.zns.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_phone': phone,
            },
        }