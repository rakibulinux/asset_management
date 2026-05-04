frappe.query_reports["Car Inspection Report"] = {
	filters: [
		{
			fieldname: "car_inspection",
			label: __("Car Inspection"),
			fieldtype: "Link",
			options: "Car Inspection",
			reqd: 1,
			on_change: function() {
				frappe.query_report.refresh();
			}
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		if (data && data._is_section_header) {
			return `<span style="font-weight:700; font-size:13px; color:#1a73e8;">${value || ""}</span>`;
		}

		if (column.fieldname === "name_english" && data && data._doc_name && data._doctype) {
			const route = frappe.utils.get_form_link(data._doctype, data._doc_name);
			return `<a href="${route}" style="color:#1a73e8; text-decoration:none;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${frappe.utils.escape_html(value || "")}</a>`;
		}

		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status") {
			const colors = {
				"Good": "green",
				"Damaged": "red",
				"Missing": "orange",
				"Needs Repair": "#d97706",
				"Not Applicable": "grey"
			};
			const color = colors[data && data.status] || "grey";
			if (data && data.status) {
				value = `<span style="color:${color}; font-weight:600;">${data.status}</span>`;
			}
		}
		return value;
	}
};
