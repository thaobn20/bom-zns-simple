odoo.define('bom_zns_simple.zns_dashboard', function (require) {
    "use strict";
    
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var _t = core._t;
    
    var BomZnsDashboard = AbstractAction.extend({
        template: 'BomZnsDashboard',
        events: {
            'click .o_bom_zns_refresh': '_onRefresh',
            'click .o_bom_zns_message_link': '_onMessageClick',
        },
        
        /**
         * @override
         */
        init: function(parent, action) {
            this._super.apply(this, arguments);
            this.dashboardData = {};
            this.chartInstances = {};
        },
        
        /**
         * @override
         */
        willStart: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                return self._fetchDashboardData();
            });
        },
        
        /**
         * @override
         */
        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                self._renderDashboard();
                // Refresh data every 5 minutes
                self._refreshInterval = setInterval(function() {
                    self._fetchDashboardData().then(function() {
                        self._renderDashboard();
                    });
                }, 300000);
            });
        },
        
        /**
         * @override
         */
        destroy: function() {
            if (this._refreshInterval) {
                clearInterval(this._refreshInterval);
            }
            // Destroy chart instances
            Object.keys(this.chartInstances).forEach(function(key) {
                if (this.chartInstances[key]) {
                    this.chartInstances[key].destroy();
                }
            }.bind(this));
            this._super.apply(this, arguments);
        },
        
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        
        /**
         * Fetch dashboard data from the server
         *
         * @private
         * @returns {Promise}
         */
        _fetchDashboardData: function() {
            var self = this;
            return rpc.query({
                route: '/bom/zns/dashboard/data',
                params: {},
            }).then(function(result) {
                if (result.status === 'success') {
                    self.dashboardData = result.data;
                } else {
                    self.displayNotification({
                        title: _t('Error'),
                        message: result.message || _t('Failed to load dashboard data'),
                        type: 'danger',
                    });
                }
            }).guardedCatch(function(error) {
                self.displayNotification({
                    title: _t('Error'),
                    message: _t('Failed to load dashboard data'),
                    type: 'danger',
                });
            });
        },
        
        /**
         * Render the dashboard with the fetched data
         *
         * @private
         */
        _renderDashboard: function() {
            if (!this.dashboardData) return;
            
            // Update KPIs
            this.$('.o_bom_zns_total_messages').text(this.dashboardData.total_messages || 0);
            this.$('.o_bom_zns_read_messages').text(this.dashboardData.state_counts.read || 0);
            this.$('.o_bom_zns_failed_messages').text(this.dashboardData.state_counts.failed || 0);
            
            // Update OA info
            var config = this.dashboardData.config || {};
            this.$('.o_bom_zns_oa_name').text(config.zalo_oa_name || '-');
            this.$('.o_bom_zns_oa_id').text(config.zalo_oa_id || '-');
            this.$('.o_bom_zns_last_sync').text(config.last_sync_date || '-');
            
            // Render charts
            this._renderStatusChart();
            this._renderMonthlyChart();
            this._renderTemplateChart();
            
            // Render recent messages
            this._renderRecentMessages();
        },
        
        /**
         * Render the status chart
         *
         * @private
         */
        _renderStatusChart: function() {
            var self = this;
            var $chartContainer = this.$('.o_bom_zns_status_chart');
            
            // Destroy existing chart
            if (this.chartInstances.statusChart) {
                this.chartInstances.statusChart.destroy();
            }
            
            // Prepare data
            var states = ['draft', 'sent', 'delivered', 'read', 'failed'];
            var counts = states.map(function(state) {
                return self.dashboardData.state_counts[state] || 0;
            });
            
            // Colors for each state
            var colors = ['#6c757d', '#17a2b8', '#ffc107', '#28a745', '#dc3545'];
            
            // Create new chart
            var ctx = $('<canvas>').appendTo($chartContainer.empty())[0].getContext('2d');
            this.chartInstances.statusChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: [_t('Draft'), _t('Sent'), _t('Delivered'), _t('Read'), _t('Failed')],
                    datasets: [{
                        data: counts,
                        backgroundColor: colors,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: {
                        position: 'right',
                    },
                }
            });
        },
        
        /**
         * Render the recent messages table
         *
         * @private
         */
        _renderRecentMessages: function() {
            var self = this;
            var $container = this.$('.o_bom_zns_recent_messages tbody');
            $container.empty();
            
            if (!this.dashboardData.recent_messages || this.dashboardData.recent_messages.length === 0) {
                $('<tr class="o_bom_zns_no_messages"><td colspan="5" class="text-center">' + _t('No recent messages') + '</td></tr>').appendTo($container);
                return;
            }
            
            // Status badge colors
            var statusColors = {
                'draft': 'secondary',
                'sent': 'info',
                'delivered': 'warning',
                'read': 'success',
                'failed': 'danger'
            };
            
            // Status labels
            var statusLabels = {
                'draft': _t('Draft'),
                'sent': _t('Sent'),
                'delivered': _t('Delivered'),
                'read': _t('Read'),
                'failed': _t('Failed')
            };
            
            this.dashboardData.recent_messages.forEach(function(message) {
                var $row = $('<tr>');
                
                // Format date
                var date = moment(message.create_date).format('YYYY-MM-DD HH:mm:ss');
                $row.append($('<td>').text(date));
                
                // Template name
                $row.append($('<td>').text(message.template_name || '-'));
                
                // Recipient
                $row.append($('<td>').text(message.recipient || message.phone || '-'));
                
                // Status badge
                var statusColor = statusColors[message.state] || 'secondary';
                var statusLabel = statusLabels[message.state] || message.state;
                var $status = $('<span class="badge badge-' + statusColor + '">').text(statusLabel);
                $row.append($('<td>').append($status));
                
                // Actions
                var $actions = $('<td>');
                $('<a href="#" class="btn btn-sm btn-primary o_bom_zns_message_link" data-id="' + message.id + '">')
                    .text(_t('View'))
                    .appendTo($actions);
                
                $row.append($actions);
                $row.appendTo($container);
            });
        },
        
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        
        /**
         * Handle refresh button click
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onRefresh: function(ev) {
            ev.preventDefault();
            var self = this;
            this._fetchDashboardData().then(function() {
                self._renderDashboard();
            });
        },
        
        /**
         * Handle message link click
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onMessageClick: function(ev) {
            ev.preventDefault();
            var messageId = $(ev.currentTarget).data('id');
            if (messageId) {
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'bom_zns_simple.zns.history',
                    res_id: messageId,
                    views: [[false, 'form']],
                    target: 'current',
                });
            }
        },
    });
    
    core.action_registry.add('bom_zns_dashboard', BomZnsDashboard);
    
    return BomZnsDashboard;
});
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: {
                        position: 'right',
                    },
                }
            });
        },
        
        /**
         * Render the monthly chart
         *
         * @private
         */
        _renderMonthlyChart: function() {
            var self = this;
            var $chartContainer = this.$('.o_bom_zns_monthly_chart');
            
            // Destroy existing chart
            if (this.chartInstances.monthlyChart) {
                this.chartInstances.monthlyChart.destroy();
            }
            
            // Prepare data
            var months = [];
            var counts = [];
            
            if (this.dashboardData.monthly_stats) {
                this.dashboardData.monthly_stats.forEach(function(item) {
                    months.push(item.month);
                    counts.push(item.count);
                });
            }
            
            // Create new chart
            var ctx = $('<canvas>').appendTo($chartContainer.empty())[0].getContext('2d');
            this.chartInstances.monthlyChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: months,
                    datasets: [{
                        label: _t('Messages Sent'),
                        data: counts,
                        backgroundColor: '#007bff',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        yAxes: [{
                            ticks: {
                                beginAtZero: true,
                                precision: 0,
                            }
                        }]
                    }
                }
            });
        },
        
        /**
         * Render the template usage chart
         *
         * @private
         */
        _renderTemplateChart: function() {
            var self = this;
            var $chartContainer = this.$('.o_bom_zns_template_chart');
            
            // Destroy existing chart
            if (this.chartInstances.templateChart) {
                this.chartInstances.templateChart.destroy();
            }
            
            // Prepare data
            var templates = [];
            var counts = [];
            var backgroundColors = [];
            
            // Generate colors
            function getRandomColor() {
                var letters = '0123456789ABCDEF';
                var color = '#';
                for (var i = 0; i < 6; i++) {
                    color += letters[Math.floor(Math.random() * 16)];
                }
                return color;
            }
            
            if (this.dashboardData.template_usage) {
                this.dashboardData.template_usage.forEach(function(item) {
                    templates.push(item.template_name);
                    counts.push(item.count);
                    backgroundColors.push(getRandomColor());
                });
            }
            
            // Create new chart
            var ctx = $('<canvas>').appendTo($chartContainer.empty())[0].getContext('2d');
            this.chartInstances.templateChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: templates,
                    datasets: [{
                        data: counts,
                        backgroundColor: backgroundColors,
                    }]
                },
                options: {