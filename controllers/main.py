import logging
import json
import werkzeug
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class BomZnsController(http.Controller):
    @http.route('/bom/zns/webhook', type='json', auth='none', csrf=False, methods=['POST'])
    def webhook(self, **post):
        """Handle BOM ZNS webhook for status updates"""
        # Get data from request
        data = request.jsonrequest
        
        # Log request if possible
        try:
            # Get configuration for debug mode
            config = request.env['bom.zns.config'].sudo().search([('active', '=', True)], limit=1)
            if config and config.debug_mode:
                _logger.info(f"ZNS Webhook data: {json.dumps(data)}")
        except Exception as e:
            _logger.error(f"Error logging webhook data: {str(e)}")
        
        # Validate data
        if not data:
            return {'status': 'error', 'message': 'No data received'}
        
        message_id = data.get('message_id')
        if not message_id:
            return {'status': 'error', 'message': 'No message_id provided'}
        
        # Get the status
        status = data.get('status')
        if not status:
            return {'status': 'error', 'message': 'No status provided'}
        
        # Process the status update
        try:
            # Find the message history
            history = request.env['bom.zns.history'].sudo().search([('message_id', '=', message_id)], limit=1)
            if not history:
                return {'status': 'error', 'message': 'Message not found'}
            
            # Update status based on the webhook data
            vals = {'bom_response': json.dumps(data)}
            
            if status == 'delivered':
                vals.update({
                    'state': 'delivered',
                    'delivery_date': fields.Datetime.now(),
                })
            elif status == 'read':
                vals.update({
                    'state': 'read',
                    'delivery_date': history.delivery_date or fields.Datetime.now(),
                    'read_date': fields.Datetime.now(),
                })
            elif status == 'failed':
                vals.update({
                    'state': 'failed',
                    'error_message': data.get('message', 'Failed to deliver message'),
                })
            
            # Update the history record
            history.write(vals)
            
            return {'status': 'success', 'message': 'Status updated'}
        
        except Exception as e:
            _logger.exception(f"Error processing ZNS webhook: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    @http.route('/bom/zns/status/<string:message_id>', type='http', auth='user')
    def check_status(self, message_id, **kwargs):
        """Check and update status of a specific message"""
        try:
            # Create ZNS API instance
            zns_api = request.env['bom.zns'].sudo().create({})
            
            # Check message status
            result = zns_api.check_message_status(message_id)
            
            # Redirect to the message history
            if result.get('history_id'):
                return werkzeug.utils.redirect('/web#id=%s&model=bom.zns.history&view_type=form' % result.get('history_id'))
            else:
                return werkzeug.exceptions.BadRequest("Error checking message status: " + result.get('error', 'Unknown error'))
        
        except Exception as e:
            _logger.exception(f"Error checking message status: {str(e)}")
            return werkzeug.exceptions.InternalServerError(str(e))

class BomZnsDashboardController(http.Controller):
    @http.route('/bom/zns/dashboard/data', type='json', auth='user')
    def dashboard_data(self, **kwargs):
        """Get dashboard data for ZNS"""
        try:
            # Get statistics for dashboard
            History = request.env['bom.zns.history'].sudo()
            Template = request.env['bom.zns.template'].sudo()
            
            # Get counts by state
            state_counts = {}
            for state in ['draft', 'sent', 'delivered', 'read', 'failed']:
                state_counts[state] = History.search_count([('state', '=', state)])
            
            # Get template usage
            template_usage = []
            templates = Template.search([])
            for template in templates:
                count = History.search_count([('template_id', '=', template.id)])
                if count > 0:
                    template_usage.append({
                        'template_name': template.name,
                        'count': count,
                    })
            
            # Get recent messages
            recent_messages = []
            messages = History.search([], order='create_date desc', limit=10)
            for message in messages:
                recent_messages.append({
                    'id': message.id,
                    'message_id': message.message_id,
                    'template_name': message.template_id.name if message.template_id else 'Unknown',
                    'recipient': message.partner_id.name if message.partner_id else message.phone,
                    'state': message.state,
                    'create_date': message.create_date,
                })
            
            # Get monthly stats (last 6 months)
            monthly_stats = []
            for i in range(5, -1, -1):
                # Calculate date range for month
                start_date = (fields.Date.today() - relativedelta(months=i))
                end_date = (fields.Date.today() - relativedelta(months=i-1))
                
                # Get counts for the month
                month_count = History.search_count([
                    ('create_date', '>=', start_date),
                    ('create_date', '<', end_date),
                ])
                
                monthly_stats.append({
                    'month': start_date.strftime('%B %Y'),
                    'count': month_count,
                })
            
            return {
                'status': 'success',
                'data': {
                    'state_counts': state_counts,
                    'template_usage': template_usage,
                    'recent_messages': recent_messages,
                    'monthly_stats': monthly_stats,
                    'total_messages': sum(state_counts.values()),
                }
            }
        
        except Exception as e:
            _logger.exception(f"Error getting dashboard data: {str(e)}")
            return {'status': 'error', 'message': str(e)}