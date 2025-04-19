{
    'name': 'BOM ZNS Integration',
    'version': '1.0',
    'category': 'Marketing',
    'summary': 'Integration with Zalo ZNS via BOM Communications API',
    'author': 'BOM Communications',
    'website': 'https://bom.asia',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
        'contacts',
        'sale',
        'crm',
        'account',
    ],
    'data': [
        # Security
        'security/bom_zns_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/bom_zns_data.xml',
        'data/bom_zns_cron.xml',
        
        # Views
        'views/bom_zns_views.xml',
        'views/bom_zns_template_views.xml',
        'views/bom_zns_history_views.xml',
        'views/bom_zns_dashboard_views.xml',
        'views/bom_zns_variant_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
        'views/assets.xml',
        
        # Wizards
        'wizard/bom_zns_send_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bom/static/src/js/bom_zns_dashboard.js',
            'bom/static/src/js/bom_zns_widget.js',
            'bom/static/src/css/bom_zns_style.css',
        ],
        'web.assets_qweb': [
            'bom/static/src/xml/bom_zns_dashboard_templates.xml',
            'bom/static/src/xml/bom_zns_widget_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1,
    'external_dependencies': {
        'python': ['requests'],
    },
    'description': """
BOM ZNS Integration for Odoo
============================

This module integrates Odoo with Zalo ZNS (Zero Notification Service) through BOM Communications API.
Features:
- Send ZNS messages using templates
- Manage different message variants
- Track message history
- Dashboard for ZNS statistics
- Integration with CRM, Sales, and Invoicing
"""
}