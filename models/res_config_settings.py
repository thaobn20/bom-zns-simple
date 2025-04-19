from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    bom_zns_api_key = fields.Char(string='BOM ZNS API Key', help='API Key provided by BOM')
    bom_zns_api_secret = fields.Char(string='BOM ZNS API Secret', help='API Secret provided by BOM')
    bom_zns_base_url = fields.Char(string='BOM ZNS API URL', help='Base URL for BOM ZNS API')
    bom_zns_debug_mode = fields.Boolean(string='Debug Mode', help='Enable debug mode for ZNS')
    bom_zns_auto_check = fields.Boolean(string='Auto Check Status', 
                                      help='Automatically check message status with cron job')
    bom_zns_check_interval = fields.Integer(string='Check Interval (Minutes)', default=60,
                                         help='Interval in minutes to check message status')
    bom_zns_config_id = fields.Many2one('bom.zns.config', string='ZNS Configuration')
    bom_zns_safe_eval = fields.Boolean(string='Enable Custom Expressions', 
                                     help='Enable custom expressions for variant values (security risk)')
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        
        # Get configuration
        config = self.env['bom.zns.config'].search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1)
        
        # Set values from configuration
        if config:
            res.update({
                'bom_zns_api_key': config.api_key,
                'bom_zns_api_secret': config.api_secret,
                'bom_zns_base_url': config.base_url,
                'bom_zns_debug_mode': config.debug_mode,
                'bom_zns_config_id': config.id,
            })
        
        # Get other settings from parameters
        IrParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'bom_zns_auto_check': IrParam.get_param('bom.zns.auto_check', 'True').lower() == 'true',
            'bom_zns_check_interval': int(IrParam.get_param('bom.zns.check_interval', '60')),
            'bom_zns_safe_eval': IrParam.get_param('bom.zns.safe_eval', 'False').lower() == 'true',
        })
        
        return res
    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        
        # Update configuration
        config = self.bom_zns_config_id
        if not config:
            config = self.env['bom.zns.config'].search([
                ('company_id', '=', self.env.company.id),
                ('active', '=', True)
            ], limit=1)
        
        if not config:
            # Create new configuration if none exists
            config = self.env['bom.zns.config'].create({
                'name': 'BOM ZNS Configuration',
                'company_id': self.env.company.id,
                'api_key': self.bom_zns_api_key,
                'api_secret': self.bom_zns_api_secret,
                'base_url': self.bom_zns_base_url or 'https://zns.bom.asia/api',
                'debug_mode': self.bom_zns_debug_mode,
            })
        else:
            # Update existing configuration
            config.write({
                'api_key': self.bom_zns_api_key,
                'api_secret': self.bom_zns_api_secret,
                'base_url': self.bom_zns_base_url or config.base_url,
                'debug_mode': self.bom_zns_debug_mode,
            })
        
        # Update parameters
        IrParam = self.env['ir.config_parameter'].sudo()
        IrParam.set_param('bom.zns.auto_check', str(self.bom_zns_auto_check))
        IrParam.set_param('bom.zns.check_interval', str(self.bom_zns_check_interval))
        IrParam.set_param('bom.zns.safe_eval', str(self.bom_zns_safe_eval))
        
        # Update cron job interval if it exists
        cron_job = self.env.ref('bom.bom_zns_cron_check_status', raise_if_not_found=False)
        if cron_job and self.bom_zns_check_interval:
            # Convert minutes to cron interval
            cron_job.interval_number = self.bom_zns_check_interval
            cron_job.active = self.bom_zns_auto_check
    
    def action_bom_zns_test_connection(self):
        """Test connection to BOM ZNS API"""
        config = self.bom_zns_config_id
        if not config:
            config = self.env['bom.zns.config'].search([
                ('company_id', '=', self.env.company.id),
                ('active', '=', True)
            ], limit=1)
        
        if not config:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Please save settings first to create the configuration.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        return config.test_connection()