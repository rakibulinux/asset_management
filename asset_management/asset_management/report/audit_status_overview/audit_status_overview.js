frappe.query_reports["Audit Status Overview"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "location",
			label: __("Location"),
			fieldtype: "Link",
			options: "Location"
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\\nOpen\\nPending\\nCompleted"
		},
		{
			fieldname: "show_only_incomplete",
			label: __("Show Only Incomplete"),
			fieldtype: "Check",
			default: 0
		}
	]
};