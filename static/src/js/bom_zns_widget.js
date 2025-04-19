odoo.define('bom_zns_simple.zns_widget', function (require) {
    "use strict";
    
    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var field_registry = require('web.field_registry');
    var QWeb = core.qweb;
    var _t = core._t;
    
    /**
     * ZNS Status Widget
     * 
     * Displays a badge with the ZNS message status
     */
    var ZnsStatusWidget = AbstractField.extend({
        template: 'ZnsStatusBadge',
        
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.statusColors = {
                'draft': 'secondary',
                'sent': 'info',
                'delivered': 'warning',
                'read': 'success',
                'failed': 'danger'
            };
            this.statusLabels = {
                'draft': _t('Draft'),
                'sent': _t('Sent'),
                'delivered': _t('Delivered'),
                'read': _t('Read'),
                'failed': _t('Failed')
            };
        },
        
        /**
         * @override
         */
        _render: function () {
            var self = this;
            var statusColor = this.statusColors[this.value] || 'secondary';
            var statusLabel = this.statusLabels[this.value] || this.value;
            
            this.$el.html(QWeb.render('ZnsStatusBadge', {
                status: this.value,
                color: statusColor,
                label: statusLabel
            }));
        }
    });
    
    field_registry.add('zns_status', ZnsStatusWidget);
    
    /**
     * ZNS Send Button Widget
     * 
     * Displays a button to send a ZNS message
     */
    var ZnsSendButton = AbstractField.extend({
        template: 'ZnsSendButton',
        events: {
            'click .o_bom_zns_send': '_onClickSend',
        },
        
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.displayButton = true;
        },
        
        /**
         * @override
         */
        _render: function () {
            var self = this;
            this.$el.html(QWeb.render('ZnsSendButton', {
                displayButton: this.displayButton
            }));
        },
        
        /**
         * Handle click on send button
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickSend: function (ev) {
            ev.preventDefault();
            
            // Get partner ID from context
            var partnerID = false;
            if (this.record && this.record.model === 'res.partner') {
                partnerID = this.record.res_id;
            }
            
            // Get model and res_id
            var model = this.record ? this.record.model : false;
            var resID = this.record ? this.record.res_id : false;
            
            // Open wizard
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'bom_zns_simple.zns.send.wizard',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    'default_partner_id': partnerID,
                    'default_model': model,
                    'default_res_id': resID
                }
            });
        }
    });
    
    field_registry.add('zns_send_button', ZnsSendButton);
    
    return {
        ZnsStatusWidget: ZnsStatusWidget,
        ZnsSendButton: ZnsSendButton
    };
});

// QWeb Templates
odoo.define('bom_zns_simple.zns_widget_templates', function (require) {
    "use strict";
    
    var core = require('web.core');
    var QWeb = core.qweb;
    
    // Status Badge Template
    QWeb.add_template(
        '<t t-name="ZnsStatusBadge">' +
        '    <span t-att-class="\'badge badge-\' + color">' +
        '        <t t-esc="label"/>' +
        '    </span>' +
        '</t>'
    );
    
    // Send Button Template
    QWeb.add_template(
        '<t t-name="ZnsSendButton">' +
        '    <button t-if="displayButton" class="btn btn-primary btn-sm o_bom_zns_send">' +
        '        <i class="fa fa-paper-plane"></i> Send ZNS' +
        '    </button>' +
        '</t>'
    );
});