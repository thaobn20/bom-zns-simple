import logging
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class BomZnsSendWizard(models.TransientModel):
    _name = 'bom_zns_simple.zns.send.wizard'
    _description = 'Send ZNS Message Wizard'
    
    template_id = fields.Many2one('bom_zns_simple.zns.template', string='Template', required=True,
                                 domain=[('active', '=', True)])
    partner_id = fields.Many2one('res.partner', string='Recipient')
    phone = fields.Char('Phone Number', required=True)
    
    # For reference
    model = fields.Char('Related Document Model')
    res_id = fields.Integer('Related Document ID')
    
    # For testing
    is_test = fields.Boolean('Test Message', default=False)
    
    # Dynamic fields for variants
    variant_ids = fields.One2many('bom_zns_simple.zns.send.wizard.line', 'wizard_id', string='Variants')
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Load template variants when template changes"""
        self.variant_ids = [(5, 0, 0)]  # Clear existing lines
        
        if self.template_id:
            # Get variants from template
            lines = []
            for variant in self.template_id.variant_ids.filtered(lambda v: v.active):
                # Get default value
                default_value = variant.default_value
                
                # If we have a record, try to get the value from it
                if self.model and self.res_id and variant.field_model == self.model:
                    try:
                        record = self.env[self.model].browse(self.res_id).exists()
                        if record:
                            default_value = variant.get_formatted_value(record=record)
                    except Exception as e:
                        _logger.error(f"Error getting field value: {str(e)}")
                
                # If we have a partner, try to get value if the model is res.partner
                elif self.partner_id and variant.field_model == 'res.partner':
                    try:
                        default_value = variant.get_formatted_value(record=self.partner_id)
                    except Exception as e:
                        _logger.error(f"Error getting partner field value: {str(e)}")
                
                lines.append((0, 0, {
                    'variant_id': variant.id,
                    'param_name': variant.param_name,
                    'required': variant.required,
                    'param_type': variant.param_type,
                    'value': default_value,
                }))
            
            self.variant_ids = lines
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update phone when partner changes"""
        if self.partner_id:
            self.phone = self.partner_id.zalo_phone or self.partner_id.mobile or self.partner_id.phone
    
    def action_send(self):
        """Send ZNS message"""
        self.ensure_one()
        
        # Validate required fields
        if not self.template_id:
            raise UserError(_("Please select a template."))
        
        if not self.phone:
            raise UserError(_("Please provide a phone number."))
        
        # Check required variants
        for variant_line in self.variant_ids.filtered(lambda l: l.required):
            if not variant_line.value:
                raise UserError(_("Please provide a value for required parameter: %s") % variant_line.param_name)
        
        # Prepare parameters
        params = {}
        for variant_line in self.variant_ids:
            params[variant_line.param_name] = variant_line.value
        
        # Initialize ZNS API
        zns_api = self.env['bom_zns_simple.zns'].create({})
        
        # Send message
        result = zns_api.send_zns_message(
            template_id=self.template_id.id,
            phone=self.phone,
            params=params,
            partner_id=self.partner_id.id if self.partner_id else False,
            model=self.model,
            res_id=self.res_id,
            is_test=self.is_test,
        )
        
        if result.get('success'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('ZNS message sent successfully!'),
                    'sticky': False,
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': result.get('error', _('Failed to send ZNS message.')),
                    'sticky': False,
                    'type': 'danger',
                }
            }


class BomZnsSendWizardLine(models.TransientModel):
    _name = 'bom_zns_simple.zns.send.wizard.line'
    _description = 'Send ZNS Message Wizard Line'
    
    wizard_id = fields.Many2one('bom_zns_simple.zns.send.wizard', string='Wizard')
    variant_id = fields.Many2one('bom_zns_simple.zns.variant', string='Variant')
    param_name = fields.Char('Parameter Name', required=True)
    param_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('currency', 'Currency'),
        ('url', 'URL'),
    ], string='Parameter Type', required=True, default='text')
    required = fields.Boolean('Required', default=False)
    value = fields.Char('Value')