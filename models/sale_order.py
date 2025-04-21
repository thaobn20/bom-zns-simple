from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    zns_sent = fields.Boolean('ZNS Sent', default=False, copy=False)
    zns_history_ids = fields.One2many('bom.zns.history', 'res_id', string='ZNS Messages', 
                                     domain=[('model', '=', 'sale.order')], readonly=True)
    
    def action_confirm(self):
        # First call the original method
        result = super(SaleOrder, self).action_confirm()
        
        # Check if auto-send is enabled in config
        IrConfig = self.env['ir.config_parameter'].sudo()
        if IrConfig.get_param('bom_zns_simple.auto_send_so', 'False').lower() == 'true':
            self._send_confirmation_zns()
        
        return result
    
    def _send_confirmation_zns(self):
        self.ensure_one()
        if self.zns_sent:
            return
            
        # Get template from settings
        IrConfig = self.env['ir.config_parameter'].sudo()
        template_id = int(IrConfig.get_param('bom_zns_simple.so_template_id', '0'))
        if not template_id:
            return
            
        template = self.env['bom.zns.template'].browse(template_id).exists()
        if not template or not self.partner_id or not self.partner_id.zalo_opt_in:
            return
            
        # Get phone number
        phone = self.partner_id.zalo_phone or self.partner_id.mobile or self.partner_id.phone
        if not phone:
            return
            
        # Prepare parameters
        params = {}
        for variant in template.variant_ids.filtered(lambda v: v.active):
            params[variant.param_name] = variant.get_formatted_value(record=self)
        
        # Send ZNS
        zns_api = self.env['bom.zns'].create({})
        result = zns_api.send_zns_message(
            template_id=template.id,
            phone=phone,
            params=params,
            partner_id=self.partner_id.id,
            model='sale.order',
            res_id=self.id,
            is_test=False
        )
        
        if result.get('success'):
            self.zns_sent = True
    
    def action_send_zns(self):
        """Manual ZNS sending action"""
        self.ensure_one()
        
        return {
            'name': _('Send ZNS Message'),
            'type': 'ir.actions.act_window',
            'res_model': 'bom.zns.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_model': 'sale.order',
                'default_res_id': self.id,
            },
        }