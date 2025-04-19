import logging
import json
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class BomZnsHistory(models.Model):
    _name = 'bom_zns_simple.zns.history'
    _description = 'BOM ZNS Message History'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'message_id'
    _order = 'create_date desc'
    
    message_id = fields.Char('Message ID', readonly=True, track_visibility='onchange',
                            help='Unique message ID from BOM ZNS')
    
    # Relation fields
    template_id = fields.Many2one('bom_zns_simple.zns.template', string='Template', ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Recipient', ondelete='set null')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    config_id = fields.Many2one('bom_zns_simple.zns.config', string='ZNS Configuration')
    user_id = fields.Many2one('res.users', string='Sent By', default=lambda self: self.env.user,
                             help='User who sent the message')
    
    # Reference to Odoo documents
    model = fields.Char('Related Document Model')
    res_id = fields.Integer('Related Document ID')
    
    # Message information
    phone = fields.Char('Phone Number', help='Recipient phone number')
    template_code = fields.Char('Template Code', related='template_id.template_code', store=True, readonly=True)
    template_type = fields.Selection(related='template_id.template_type', store=True, readonly=True)
    
    # Content and parameters
    message_params = fields.Text('Message Parameters', 
                                help='JSON representation of parameters sent with the message')
    message_content = fields.Text('Message Content',
                                 help='Final content of the message after parameter substitution')
    
    # Status tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', tracking=True, readonly=True,
       help='Current status of the message')
    
    error_message = fields.Text('Error Message', readonly=True,
                               help='Error message if the message failed')
    delivery_date = fields.Datetime('Delivery Date', readonly=True)
    read_date = fields.Datetime('Read Date', readonly=True)
    
    # Additional information
    is_test = fields.Boolean('Test Message', default=False, readonly=True,
                            help='Whether this was a test message')
    bom_response = fields.Text('BOM API Response', readonly=True,
                              help='Complete response from BOM API')
    
    # Debugging information
    request_data = fields.Text('Request Data', readonly=True,
                              help='Data sent to BOM API')
    debug_information = fields.Text('Debug Information', readonly=True,
                                   help='Additional debug information')
    
    def name_get(self):
        """Override name_get to show template name and recipient"""
        result = []
        for record in self:
            name = record.message_id or _('New Message')
            if record.template_id:
                name = f"{name} ({record.template_id.name})"
            if record.partner_id:
                name = f"{name} - {record.partner_id.name}"
            result.append((record.id, name))
        return result
    
    def action_mark_as_sent(self):
        """Manually mark message as sent"""
        for record in self:
            record.write({'state': 'sent'})
    
    def action_mark_as_delivered(self):
        """Manually mark message as delivered"""
        for record in self:
            record.write({
                'state': 'delivered',
                'delivery_date': fields.Datetime.now(),
            })
    
    def action_mark_as_read(self):
        """Manually mark message as read"""
        for record in self:
            record.write({
                'state': 'read',
                'read_date': fields.Datetime.now(),
            })
    
    def action_mark_as_failed(self, error_message=None):
        """Manually mark message as failed"""
        for record in self:
            vals = {'state': 'failed'}
            if error_message:
                vals['error_message'] = error_message
            record.write(vals)
    
    def action_retry_sending(self):
        """Retry sending failed messages"""
        for record in self:
            if record.state == 'failed' and record.template_id and record.message_params:
                # Initialize ZNS API handler
                zns_api = self.env['bom_zns_simple.zns'].create({})
                
                # Parse message parameters
                try:
                    params = json.loads(record.message_params)
                except Exception as e:
                    record.write({
                        'error_message': f"Failed to parse message parameters: {str(e)}",
                    })
                    continue
                
                # Retry sending message
                result = zns_api.send_zns_message(
                    template_id=record.template_id.id,
                    phone=record.phone,
                    params=params,
                    partner_id=record.partner_id.id if record.partner_id else False,
                    model=record.model,
                    res_id=record.res_id,
                    is_test=record.is_test,
                )
                
                if result.get('success'):
                    # Update existing record with new information
                    record.write({
                        'message_id': result.get('message_id'),
                        'state': 'sent',
                        'error_message': False,
                        'bom_response': result.get('response'),
                        'request_data': result.get('request_data'),
                    })
                else:
                    # Update error message
                    record.write({
                        'error_message': result.get('error'),
                        'debug_information': result.get('debug_info'),
                    })
    
    def action_view_related_record(self):
        """Open the related record if it exists"""
        self.ensure_one()
        if not self.model or not self.res_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _('No related document found.'),
                    'sticky': False,
                    'type': 'info',
                }
            }
        
        # Try to get record
        try:
            record = self.env[self.model].browse(self.res_id).exists()
            if not record:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Warning'),
                        'message': _('The related document no longer exists.'),
                        'sticky': False,
                        'type': 'warning',
                    }
                }
            
            # Open the record
            return {
                'name': _('Related Document'),
                'type': 'ir.actions.act_window',
                'res_model': self.model,
                'res_id': self.res_id,
                'view_mode': 'form',
                'target': 'current',
            }
        except Exception as e:
            _logger.error(f"Error opening related record: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Could not open related document: %s') % str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }