frappe.ui.form.on("Custom Asset", {
	refresh(frm) {
		toggle_partner(frm);

		frm.set_query("linked_asset", function () {
			return {
				filters: {
					name: ["!=", frm.doc.name || ""]
				}
			};
		});
	},

	partner_owned(frm) {
		toggle_partner(frm);
	}
});

function toggle_partner(frm) {
	frm.toggle_display("partner", !!frm.doc.partner_owned);
	frm.toggle_reqd("partner", !!frm.doc.partner_owned);
}