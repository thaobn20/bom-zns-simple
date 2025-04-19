import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class BomZnsVariant(models.Model):
    _name = 'bom.zns.variant'
    _description = 'BOM ZNS Template Variant'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'sequence, id'
    
    name = fields.Char('Variant Name', required=True, track_visibility='onchange')
    param_name = fields.Char('Parameter Name', required=True, track_visibility='onchange',
                            help='Parameter name as defined in the ZNS template')
    description = fields.Text('Description', help='Description of this parameter')
    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer('Sequence', default=10, help='Sequence for ordering')
    
    # Parameter properties
    param_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('currency', 'Currency'),
        ('url', 'URL'),
    ], string='Parameter Type', required=True, default='text',
       help='Type of the parameter')
    
    required = fields.Boolean('Required', default=False, 
                             help='Whether this parameter is required for the template')
    
    # Related fields
    template_id = fields.Many2one('bom.zns.template', string='Template', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='template_id.company_id', store=True, readonly=True)
    
    # Default value for testing
    default_value = fields.Char('Default Test Value', help='Default value used for testing')
    
    # Field mapping
    field_model = fields.Selection([
        ('res.partner', 'Contact'),
        ('sale.order', 'Sales Order'),
        ('account.move', 'Invoice'),
        ('crm.lead', 'CRM Lead'),
        ('custom', 'Custom Expression'),
    ], string='Source Model', default='custom',
       help='Model from which to pull the field value')
    
    field_name = fields.Char('Source Field', 
                            help='Field name from the source model or a custom expression')
    
    field_format = fields.Char('Format String', 
                              help='Python format string to apply to the field value')
    
    # For numeric fields
    decimal_places = fields.Integer('Decimal Places', default=2,
                                  help='Number of decimal places for numeric values')
    thousand_separator = fields.Boolean('Thousand Separator', default=True,
                                      help='Use thousand separator for numeric values')
    
    # For date fields
    date_format = fields.Char('Date Format', default='%d/%m/%Y',
                             help='Format for date values')
    
    # For currency fields
    currency_symbol = fields.Char('Currency Symbol', default='₫',
                                 help='Currency symbol to use')
    currency_position = fields.Selection([
        ('before', 'Before Amount'),
        ('after', 'After Amount'),
    ], string='Symbol Position', default='before',
       help='Position of the currency symbol')
    
    _sql_constraints = [
        ('param_name_template_uniq', 'unique(param_name, template_id)', 
         'Parameter name must be unique per template!')
    ]
    
    def get_formatted_value(self, record=None, value=None):
        """Get formatted value for this parameter
        
        :param record: The record from which to extract the value (if field_model and field_name are set)
        :param value: The explicit value to format (if record is not provided)
        :return: Formatted value according to parameter settings
        """
        if record and self.field_model and self.field_name:
            # Extract value from record
            if self.field_model == 'custom':
                # Using safe_eval to evaluate custom expressions with record
                try:
                    value = self.env['ir.config_parameter'].sudo().get_param('bom.zns.safe_eval', 'False').lower() == 'true'
                    if value:
                        value = self.env['ir.actions.server']._eval_context(record).get('record', record)
                        value = safe_eval(self.field_name, {'record': value})
                    else:
                        _logger.warning("Safe eval disabled for security. Using default value instead.")
                        value = self.default_value
                except Exception as e:
                    _logger.error(f"Error evaluating custom expression: {str(e)}")
                    value = self.default_value
            else:
                # Direct field access
                try:
                    field_path = self.field_name.split('.')
                    current = record
                    for field in field_path:
                        if not current:
                            break
                        current = current[field] if hasattr(current, '__getitem__') else getattr(current, field, None)
                    value = current
                except Exception as e:
                    _logger.error(f"Error getting field value: {str(e)}")
                    value = self.default_value
        
        # If no value yet, use default
        if value is None:
            value = self.default_value
        
        # Format the value according to its type
        try:
            if self.param_type == 'number':
                value = float(value) if value else 0.0
                if self.thousand_separator:
                    value = '{:,.{prec}f}'.format(value, prec=self.decimal_places).replace(',', ' ')
                else:
                    value = '{:.{prec}f}'.format(value, prec=self.decimal_places)
            
            elif self.param_type == 'date' and value:
                if isinstance(value, str):
                    # Try to parse the string as a date
                    try:
                        from datetime import datetime
                        value = datetime.strptime(value, '%Y-%m-%d').strftime(self.date_format or '%d/%m/%Y')
                    except Exception:
                        pass
                else:
                    # Assume it's a datetime object
                    value = value.strftime(self.date_format or '%d/%m/%Y')
            
            elif self.param_type == 'currency' and value:
                value = float(value) if value else 0.0
                formatted_value = '{:,.{prec}f}'.format(value, prec=self.decimal_places).replace(',', ' ')
                
                if self.currency_position == 'before':
                    value = f"{self.currency_symbol or '₫'}{formatted_value}"
                else:
                    value = f"{formatted_value}{self.currency_symbol or '₫'}"
            
            # Apply custom format if specified
            if self.field_format and value is not None:
                try:
                    value = self.field_format.format(value)
                except Exception as e:
                    _logger.error(f"Error formatting value: {str(e)}")
            
        except Exception as e:
            _logger.error(f"Error formatting parameter value: {str(e)}")
            value = self.default_value
        
        return str(value) if value is not None else ""