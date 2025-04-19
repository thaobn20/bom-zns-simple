import logging
import json
import requests
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class BomZns(models.Model):
    _name = 'bom.zns'
    _description = 'BOM ZNS API'
    
    def _default_config_id(self):
        return self.env['bom.zns.config'].search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1).id
    
    name = fields.Char('Name', default="ZNS API")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    config_id = fields.Many2one('bom.zns.config', string='ZNS Configuration', default=_default_config_id)
    
    def send_zns_message(self, template_id, phone, params=None, partner_id=False, model=False, res_id=False, is_test=False):
        """Send ZNS message using BOM API
        
        :param template_id: ID of the bom.zns.template to use
        :param phone: Phone number of the recipient
        :param params: Dictionary of parameters to use in the template
        :param partner_id: Optional partner ID for tracking
        :param model: Optional model name for reference
        :param res_id: Optional record ID for reference
        :param is_test: Whether this is a test message
        :return: Dictionary with status and message information
        """
        template = self.env['bom.zns.template'].browse(template_id).exists()
        if not template:
            return {'success': False, 'error': _("Template not found.")}
        
        # Get configuration
        config = template.config_id or self.env['bom.zns.config'].get_bom_zns_config()
        if not config:
            return {'success': False, 'error': _("ZNS Configuration not found.")}
        
        # Prepare parameters
        if params is None:
            params = {}
        
        # Format phone number (remove '+' if present)
        phone = (phone or '').replace('+', '')
        
        # Prepare request data
        request_data = {
            'template_id': template.template_code,
            'phone': phone,
            'params': params
        }
        
        # Add tracking information
        debug_info = {
            'template_id': template.id,
            'template_code': template.template_code,
            'partner_id': partner_id,
            'model': model,
            'res_id': res_id,
            'is_test': is_test,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': config.api_key,
            'X-Api-Secret': config.api_secret,
        }
        
        # Create history record
        history_vals = {
            'template_id': template.id,
            'partner_id': partner_id,
            'company_id': self.env.company.id,
            'config_id': config.id,
            'phone': phone,
            'message_params': json.dumps(params),
            'model': model,
            'res_id': res_id,
            'is_test': is_test,
            'state': 'draft',
            'user_id': self.env.user.id,
            'request_data': json.dumps(request_data),
            'debug_information': json.dumps(debug_info),
        }
        
        history = self.env['bom.zns.history'].create(history_vals)
        
        try:
            # Log request if debug mode is enabled
            if config.debug_mode:
                _logger.info(f"Sending ZNS request: {json.dumps(request_data)}")
            
            # Send request to BOM API
            response = requests.post(
                f"{config.base_url}/send-template",
                headers=headers,
                json=request_data,
                timeout=30
            )
            
            # Always store the response
            history.write({'bom_response': response.text})
            
            # Process response
            response_data = response.json()
            
            # Log response if debug mode is enabled
            if config.debug_mode:
                _logger.info(f"ZNS Response: {response.text}")
            
            if response.status_code == 200 and response_data.get('status') == 'success':
                # Update history record
                history.write({
                    'message_id': response_data.get('message_id', 'Unknown'),
                    'state': 'sent',
                    'message_content': response_data.get('content', ''),
                })
                
                return {
                    'success': True,
                    'message_id': response_data.get('message_id'),
                    'response': response.text,
                    'history_id': history.id,
                    'request_data': json.dumps(request_data),
                }
            else:
                # Handle error
                error_message = response_data.get('message', 'Unknown error')
                history.action_mark_as_failed(error_message)
                
                return {
                    'success': False,
                    'error': error_message,
                    'response': response.text,
                    'history_id': history.id,
                    'debug_info': json.dumps(debug_info),
                    'request_data': json.dumps(request_data),
                }
                
        except Exception as e:
            # Handle exception
            error_message = f"Error sending ZNS message: {str(e)}"
            _logger.exception(error_message)
            
            # Update history record
            history.action_mark_as_failed(error_message)
            
            return {
                'success': False,
                'error': error_message,
                'history_id': history.id,
                'debug_info': json.dumps(debug_info),
                'request_data': json.dumps(request_data),
            }
    
    def check_message_status(self, message_id):
        """Check the status of a sent message
        
        :param message_id: Message ID from BOM API
        :return: Dictionary with status information
        """
        # Get history record
        history = self.env['bom.zns.history'].search([('message_id', '=', message_id)], limit=1)
        if not history:
            return {'success': False, 'error': _("Message not found in history.")}
        
        # Get configuration
        config = history.config_id or self.env['bom.zns.config'].get_bom_zns_config()
        if not config:
            return {'success': False, 'error': _("ZNS Configuration not found.")}
        
        try:
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-Api-Key': config.api_key,
                'X-Api-Secret': config.api_secret,
            }
            
            # Send request to BOM API
            response = requests.get(
                f"{config.base_url}/status/{message_id}",
                headers=headers,
                timeout=30
            )
            
            # Process response
            response_data = response.json()
            
            # Log response if debug mode is enabled
            if config.debug_mode:
                _logger.info(f"Status Check Response: {response.text}")
            
            if response.status_code == 200:
                # Update history record based on status
                status = response_data.get('status', 'unknown')
                history_vals = {'bom_response': response.text}
                
                if status == 'delivered':
                    history_vals.update({
                        'state': 'delivered',
                        'delivery_date': fields.Datetime.now(),
                    })
                elif status == 'read':
                    history_vals.update({
                        'state': 'read',
                        'delivery_date': history.delivery_date or fields.Datetime.now(),
                        'read_date': fields.Datetime.now(),
                    })
                elif status == 'failed':
                    history_vals.update({
                        'state': 'failed',
                        'error_message': response_data.get('message', 'Failed to deliver message'),
                    })
                
                history.write(history_vals)
                
                return {
                    'success': True,
                    'status': status,
                    'response': response.text,
                    'history_id': history.id,
                }
            else:
                # Handle error
                error_message = response_data.get('message', 'Unknown error')
                
                return {
                    'success': False,
                    'error': error_message,
                    'response': response.text,
                    'history_id': history.id,
                }
                
        except Exception as e:
            # Handle exception
            error_message = f"Error checking message status: {str(e)}"
            _logger.exception(error_message)
            
            return {
                'success': False,
                'error': error_message,
                'history_id': history.id,
            }
    
    @api.model
    def cron_check_pending_messages(self):
        """Scheduled action to check status of pending messages"""
        # Get messages that are in 'sent' state and were sent less than 24 hours ago
        pending_messages = self.env['bom.zns.history'].search([
            ('state', '=', 'sent'),
            ('create_date', '>=', fields.Datetime.now() - datetime.timedelta(days=1)),
        ], limit=100)
        
        for message in pending_messages:
            if message.message_id:
                self.check_message_status(message.message_id)
        
        return True