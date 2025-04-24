# At the top of each file
import logging
_logger = logging.getLogger(__name__)

# At the beginning of important methods
def action_send_zns(self):
    """Send ZNS notification"""
    _logger.info("Starting action_send_zns for %s (ID: %s)", self._name, self.id)
    
    # Log important parameters
    _logger.info("Parameters: phone=%s, template=%s", self.partner_id.phone, self.template_id.name)
    
    try:
        # Your existing code
        _logger.info("API call successful")
    except Exception as e:
        _logger.error("Failed to send ZNS: %s", str(e), exc_info=True)
        raise
from odoo import api, fields, models, _

class Lead(models.Model):
    _inherit = 'crm.lead'
    
    zns_sent = fields.Boolean('ZNS Sent', default=False, copy=False)
    zns_history_ids = fields.One2many('bom.zns.history', 'res_id', string='ZNS Messages', 
                                     domain=[('model', '=', 'crm.lead')], readonly=True)
    
    def write(self, vals):
        # Store old stage
        old_stage_ids = {lead.id: lead.stage_id.id for lead in self}
        
        # Call original method
        result = super(Lead, self).write(vals)
        
        # Check if stage changed
        if 'stage_id' in vals:
            # Check if auto-send is enabled in config
            IrConfig = self.env['ir.config_parameter'].sudo()
            if IrConfig.get_param('bom_zns_simple.auto_send_crm', 'False').lower() == 'true':
                # Get won stage ids
                won_stage_ids = self.env['crm.stage'].search([('is_won', '=', True)]).ids
                
                # Send ZNS for opportunities that moved to won stage
                for lead in self:
                    if (lead.stage_id.id in won_stage_ids and 
                            old_stage_ids.get(lead.id) not in won_stage_ids and
                            not lead.zns_sent):
                        lead._send_opportunity_won_zns()
        
        return result
    
    def _send_opportunity_won_zns(self):
        self.ensure_one()
        if self.zns_sent:
            return
            
        # Get template from settings
        IrConfig = self.env['ir.config_parameter'].sudo()
        template_id = int(IrConfig.get_param('bom_zns_simple.crm_template_id', '0'))
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
            model='crm.lead',
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
                'default_model': 'crm.lead',
                'default_res_id': self.id,
            },
        }