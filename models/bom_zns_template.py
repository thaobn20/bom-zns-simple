import logging
import requests
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class BomZnsTemplate(models.Model):
    _name = 'bom.zns.template'
    _description = 'BOM ZNS Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'
    
    name = fields.Char('Template Name', required=True, track_visibility='onchange')
    template_code = fields.Char('Template Code', required=True, track_visibility='onchange',
                               help='Template code provided by BOM/Zalo')
    description = fields.Text('Description', help='Template description')
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    config_id = fields.Many2one('bom.zns.config', string='ZNS Configuration',
                               domain="[('company_id', '=', company_id)]")
    template_content = fields.Text('Template Content', help='Content of the ZNS template')
    template_json = fields.Text('Template JSON', help='JSON representation of the template structure')
    
    # ZNS Template properties according to BOM API
    template_type = fields.Selection([
        ('transaction', 'Transaction'),
        ('otp', 'OTP'),
        ('promotion', 'Promotion'),
    ], string='Template Type', required=True, default='transaction', 
       help='Type of the ZNS template')
    
    # Related information
    variant_ids = fields.One2many('bom.zns.variant', 'template_id', string='Variants')
    variant_count = fields.Integer(compute='_compute_variant_count', string='Number of Variants')
    history_ids = fields.One2many('bom.zns.history', 'template_id', string='Message History')
    history_count = fields.Integer(compute='_compute_history_count', string='Number of Messages Sent')
    
    # Creation Info
    create_date = fields.Datetime('Created Date', readonly=True)
    create_uid = fields.Many2one('res.users', string='Created By', readonly=True)
    
    _sql_constraints = [
        ('template_code_company_uniq', 'unique(template_code, company_id)', 
         'Template code must be unique per company!')
    ]
    
    @api.depends('variant_ids')
    def _compute_variant_count(self):
        for template in self:
            template.variant_count = len(template.variant_ids)
    
    @api.depends('history_ids')
    def _compute_history_count(self):
        for template in self:
            template.history_count = len(template.history_ids)
    
    @api.model
    def create(self, vals):
        """Override create to automatically set config_id if not provided"""
        if not vals.get('config_id'):
            company_id = vals.get('company_id', self.env.company.id)
            config = self.env['bom.zns.config'].search([
                ('company_id', '=', company_id),
                ('active', '=', True)
            ], limit=1)
            if config:
                vals['config_id'] = config.id
        
        return super(BomZnsTemplate, self).create(vals)
    
    def sync_from_bom(self):
        """Sync template information from BOM API"""
        self.ensure_one()
        if not self.config_id:
            raise UserError(_("Please set a ZNS Configuration for this template first."))
        
        if not self.template_code:
            raise UserError(_("Template code is required to sync from bom."))
        
        try:
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-Api-Key': self.config_id.api_key,
                'X-Api-Secret': self.config_id.api_secret,
            }
            
            # Make request to get template information
            # Using the get-template endpoint (adjust according to actual BOM API)
            response = requests.get(
                f"{self.config_id.base_url}/template/{self.template_code}",
                headers=headers
            )
            
            # Log the response if debug mode is enabled
            if self.config_id.debug_mode:
                _logger.info(f"Sync Template Response: {response.text}")
            
            # Process response
            if response.status_code == 200:
                data = response.json()
                
                # Update template information
                self.write({
                    'name': data.get('name', self.name),
                    'description': data.get('description', self.description),
                    'template_type': data.get('type', self.template_type),
                    'template_content': data.get('content', self.template_content),
                    'template_json': json.dumps(data),
                })
                
                # Sync template parameters/variants if available
                if 'parameters' in data:
                    self._sync_template_parameters(data['parameters'])
                
                self.message_post(body=_("Template synced successfully from BOM!"))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Template synced successfully from BOM!'),
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                error_msg = f"Failed to sync template. Status code: {response.status_code}. Response: {response.text}"
                _logger.error(error_msg)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': error_msg,
                        'sticky': False,
                        'type': 'danger',
                    }
                }
        except Exception as e:
            error_msg = f"Failed to sync template: {str(e)}"
            _logger.exception(error_msg)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': error_msg,
                    'sticky': False,
                    'type': 'danger',
                }
            }
    
    def _sync_template_parameters(self, parameters):
        """Sync template parameters as variants"""
        Variant = self.env['bom.zns.variant']
        
        # Get existing variants for this template
        existing_variants = Variant.search([('template_id', '=', self.id)])
        existing_param_names = existing_variants.mapped('param_name')
        
        # Create or update variants based on parameters
        for param in parameters:
            param_name = param.get('name')
            param_type = param.get('type', 'text')
            param_required = param.get('required', False)
            param_description = param.get('description', '')
            
            if param_name in existing_param_names:
                # Update existing variant
                variant = existing_variants.filtered(lambda v: v.param_name == param_name)
                variant.write({
                    'param_type': param_type,
                    'required': param_required,
                    'description': param_description,
                })
            else:
                # Create new variant
                Variant.create({
                    'template_id': self.id,
                    'name': param_name,  # Use parameter name as variant name
                    'param_name': param_name,
                    'param_type': param_type,
                    'required': param_required,
                    'description': param_description,
                })
    
    def action_view_variants(self):
        """Open the variants related to this template"""
        self.ensure_one()
        return {
            'name': _('Template Variants'),
            'type': 'ir.actions.act_window',
            'res_model': 'bom.zns.variant',
            'view_mode': 'tree,form',
            'domain': [('template_id', '=', self.id)],
            'context': {'default_template_id': self.id},
        }
    
    def action_view_history(self):
        """Open the message history related to this template"""
        self.ensure_one()
        return {
            'name': _('Message History'),
            'type': 'ir.actions.act_window',
            'res_model': 'bom.zns.history',
            'view_mode': 'tree,form',
            'domain': [('template_id', '=', self.id)],
            'context': {'default_template_id': self.id},
        }
    
    def action_send_test_message(self):
        """Open wizard to send a test message using this template"""
        self.ensure_one()
        return {
            'name': _('Send Test ZNS Message'),
            'type': 'ir.actions.act_window',
            'res_model': 'bom.zns.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
                'default_is_test': True,
            },
        }