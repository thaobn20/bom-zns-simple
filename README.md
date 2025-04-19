# BOM ZNS Integration for Odoo 15

This module integrates Odoo with Zalo ZNS (Zero Notification Service) through BOM API.

## Features

- Send ZNS messages using templates
- Manage different message variants/parameters
- Track message history
- Dashboard for ZNS statistics
- Integration with CRM, Sales, and Invoicing

## Installation Guide

### Prerequisites

1. Odoo 15 installed
2. BOM API credentials (API Key and API Secret)
3. Zalo OA (Official Account) connected to BOM
4. Python dependencies: `requests`

### Installation Steps

1. **Download the module**

   Clone this repository or download the ZIP file and extract it to your Odoo addons directory.

   ```bash
   cd /path/to/odoo/addons
   git clone https://github.com/yourusername/bom_zns_simple.git
   ```

   Or manually create the module structure as described in the documentation.

2. **Install Python dependencies**

   ```bash
   pip install requests
   ```

3. **Update Odoo addons list**

   Restart Odoo service and update the addons list:

   ```bash
   service odoo restart
   ```

   Or using the Odoo command line:

   ```bash
   ./odoo-bin -c /path/to/odoo.conf -u bom_zns_simple
   ```

4. **Install the module**

   From the Odoo Apps menu, find "bom_zns_simple ZNS Integration" and click Install.

   Alternatively, you can install it from the command line:

   ```bash
   ./odoo-bin -c /path/to/odoo.conf -i bom_zns_simple
   ```

## Configuration

### 1. Set up bom_zns_simple ZNS credentials

Navigate to **Zalo ZNS > Configuration > Settings** and enter your bom_zns_simple API credentials:

- API Key
- API Secret
- API Base URL (default is `https://zns.bom.asia/api`)

Click "Test Connection" to verify your credentials.

### 2. Sync Zalo OA information

Navigate to **Zalo ZNS > Configuration > ZNS Connections** and click on your configuration.

Click "Sync OA Info" to retrieve information about your Zalo Official Account.

### 3. Set up templates

Navigate to **Zalo ZNS > Templates** and create a new template or import existing ones from bom_zns_simple_zns_simple.

For each template:
1. Enter the Template Code provided by bom_zns_simple
2. Select the Template Type (Transaction, OTP, Promotion)
3. Click "Sync from bom_zns_simple" to retrieve template information
4. Configure template variants/parameters

## Usage

### Sending ZNS Messages

There are several ways to send ZNS messages:

1. **From a Contact**:
   - Open a contact
   - Go to the "Zalo ZNS" tab
   - Click "Send ZNS Message"

2. **From the Templates list**:
   - Select a template
   - Click "Send Test Message"

3. **From other Odoo documents**:
   - Some documents (Sales Orders, Invoices, etc.) have a "Send ZNS" button

### Dashboard

The dashboard provides an overview of your ZNS activity:

- Total messages sent
- Message status distribution
- Monthly statistics
- Template usage
- Recent messages

### Debugging

If you encounter issues:

1. Enable debug mode in the settings
2. Check message history for error details
3. View request and response data in the message's technical information tab

## Development and Customization

### Adding Support for New Document Types

To add ZNS support for additional document types:

1. Extend the model to include ZNS fields and methods
2. Create a button or action to trigger the send wizard
3. Define field mappings for template variants

### Custom Parameter Processing

For complex parameter values:

1. Create a new variant in the template
2. Set the Field Model to "Custom Expression"
3. Enter a Python expression in the Field Name
4. Enable "Custom Expressions" in settings (use with caution)

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify API credentials
   - Check network connectivity to bom_zns_simple API
   - Ensure your IP is whitelisted in bom_zns_simple

2. **Template Not Found**
   - Verify template code
   - Ensure template is activated in bom_zns_simple dashboard

3. **Missing Parameters**
   - Check required parameters for the template
   - Verify parameter values are not empty

### Logs

Check Odoo logs for detailed error messages:

```bash
tail -f /var/log/odoo/odoo.log | grep "bom_zns_simple ZNS"
```

## Security Notes

- API credentials are stored encrypted in the database
- Custom expressions are disabled by default for security
- Only users in ZNS Manager group can access all messages

## Support

For issues or feature requests, please contact:

- Email: support@bom.asia
- Website: https://bom.asia

## License

This module is licensed under LGPL-3.