frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Assets by Category"] = {
	method: "asset_management.asset_management.dashboard_chart_source.assets_by_category.assets_by_category.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "only_active",
			label: __("Only Active Assets"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
