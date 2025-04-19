import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

_logger = logging.getLogger(__name__)

class BomZnsPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        """Add ZNS message count to portal home page"""
        values = super()._prepare_home_portal_values(counters)
        
        if 'zns_count' in counters:
            partner = request.env.user.partner_id
            values['zns_count'] = request.env['bom_zns_simple.zns.history'].sudo().search_count([
                ('partner_id', '=', partner.id)
            ])
        
        return values
    
    @http.route(['/my/zns', '/my/zns/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_zns(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        """Display ZNS messages in customer portal"""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        BomZnsHistory = request.env['bom_zns_simple.zns.history'].sudo()
        
        domain = [('partner_id', '=', partner.id)]
        
        # Archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('bom_zns_simple.zns.history', domain)
        
        # Date filtering
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
        
        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Template'), 'order': 'template_id'},
            'status': {'label': _('Status'), 'order': 'state'},
        }
        
        # Default sorting
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Filtering
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'read': {'label': _('Read'), 'domain': [('state', '=', 'read')]},
            'delivered': {'label': _('Delivered'), 'domain': [('state', '=', 'delivered')]},
            'failed': {'label': _('Failed'), 'domain': [('state', '=', 'failed')]},
        }
        
        # Default filter
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        # Count for pager
        zns_count = BomZnsHistory.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/zns",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=zns_count,
            page=page,
            step=self._items_per_page
        )
        
        # Content
        messages = BomZnsHistory.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'date': date_begin,
            'messages': messages,
            'page_name': 'zns',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/zns',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        })
        
        return request.render("bom_zns_simple.portal_my_zns", values)
    
    @http.route(['/my/zns/<int:zns_id>'], type='http', auth="user", website=True)
    def portal_my_zns_detail(self, zns_id, **kw):
        """Display a specific ZNS message in the portal"""
        partner = request.env.user.partner_id
        BomZnsHistory = request.env['bom_zns_simple.zns.history'].sudo()
        
        # Get the message if it belongs to the partner
        message = BomZnsHistory.search([
            ('id', '=', zns_id),
            ('partner_id', '=', partner.id)
        ], limit=1)
        
        if not message:
            return request.redirect('/my/zns')
        
        # Mark as read if delivered
        if message.state == 'delivered':
            message.write({
                'state': 'read',
                'read_date': fields.Datetime.now(),
            })
        
        # Prepare values
        values = {
            'message': message,
            'page_name': 'zns',
        }
        
        return request.render("bom_zns_simple.portal_my_zns_detail", values)