frappe.query_reports["Auditor Performance"] = {
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
			fieldname: "auditor",
			label: __("Auditor"),
			fieldtype: "Data"
		},
		{
			fieldname: "top_n",
			label: __("Top Auditors"),
			fieldtype: "Int",
			default: 5,
			reqd: 1
		}
	]
};