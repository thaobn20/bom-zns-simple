import logging
import requests
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class BomZnsConfig(models.Model):
    _name = 'bom.zns.config'
    _description = 'BOM ZNS Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Add this line
    _rec_name = 'name'
    
    name = fields.Char('Name', required=True, default='BOM ZNS Configuration')
    api_key = fields.Char('API Key', required=True, help='API Key provided by BOM')
    api_secret = fields.Char('API Secret', required=True, help='API Secret provided by BOM')
    base_url = fields.Char('API Base URL', default='https://zns.bom.asia/api', required=True, 
                          help='Base URL for BOM ZNS API')
    active = fields.Boolean('Active', default=True)
    debug_mode = fields.Boolean('Debug Mode', default=False, 
                               help='Enable debug mode for detailed logging')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    zalo_oa_id = fields.Char('Zalo OA ID', help='Zalo Official Account ID')
    zalo_oa_name = fields.Char('Zalo OA Name', help='Zalo Official Account Name')
    last_sync_date = fields.Datetime('Last Sync Date', help='Last time OA information was synced')
    
    _sql_constraints = [
        ('unique_company_config', 'unique(company_id)', 'Only one configuration per company is allowed.')
    ]
    
    def test_connection(self):
        """Test the connection to BOM ZNS API"""
        self.ensure_one()
        try:
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-Api-Key': self.api_key,
                'X-Api-Secret': self.api_secret,
            }
            
            # Make a simple request to test connection
            response = requests.get(
                f"{self.base_url}/status",
                headers=headers
            )
            
            # Log the response if debug mode is enabled
            if self.debug_mode:
                _logger.info(f"BOM ZNS API Status Response: {response.text}")
            
            # Process response
            if response.status_code == 200:
                self.message_post(body=_("Connection test successful!"))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Connection to BOM ZNS API successful!'),
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                error_msg = f"Connection test failed. Status code: {response.status_code}. Response: {response.text}"
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
            error_msg = f"Connection test failed: {str(e)}"
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
    
    def sync_zalo_oa_info(self):
        """Sync Zalo OA information from BOM ZNS API"""
        self.ensure_one()
        try:
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-Api-Key': self.api_key,
                'X-Api-Secret': self.api_secret,
            }
            
            # Make request to get OA information
            # Note: This is a placeholder endpoint - adjust according to actual BOM API
            response = requests.get(
                f"{self.base_url}/zalo-oa-info",
                headers=headers
            )
            
            # Log the response if debug mode is enabled
            if self.debug_mode:
                _logger.info(f"Zalo OA Info Response: {response.text}")
            
            # Process response
            if response.status_code == 200:
                data = response.json()
                # Update OA information
                self.write({
                    'zalo_oa_id': data.get('oa_id'),
                    'zalo_oa_name': data.get('oa_name'),
                    'last_sync_date': fields.Datetime.now(),
                })
                self.message_post(body=_("Zalo OA information synced successfully!"))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Zalo OA information synced successfully!'),
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                error_msg = f"Failed to sync Zalo OA information. Status code: {response.status_code}. Response: {response.text}"
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
            error_msg = f"Failed to sync Zalo OA information: {str(e)}"
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
    
    @api.model
    def get_bom_zns_config(self, company_id=None):
        """Get the BOM ZNS configuration for the given company"""
        if not company_id:
            company_id = self.env.company.id
        
        config = self.search([('company_id', '=', company_id), ('active', '=', True)], limit=1)
        if not config:
            raise UserError(_("BOM ZNS Configuration not found for this company. Please set it up first."))
        
        return config