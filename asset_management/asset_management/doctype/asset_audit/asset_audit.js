// Copyright (c) 2026, Shayan and contributors
// For license information, please see license.txt
frappe.ui.form.on("Asset Audit", {
	refresh(frm) {
		frm.set_query("location", function() {
			return {
				query: "asset_management.asset_management.doctype.asset_audit.asset_audit.get_location_tree"
			};
		});
	},

	location(frm) {
		if (frm.doc.location) {
			frm.call("populate_expected_assets");
		}
	}
});