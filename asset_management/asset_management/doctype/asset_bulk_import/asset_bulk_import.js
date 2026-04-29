// Copyright (c) 2026, Shayan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Bulk Import", {
	refresh(frm) {
		const can_run = !frm.is_new() && frm.doc.import_file && frm.doc.status !== "Importing";

		if (can_run) {
			frm.add_custom_button(__("Preview Import"), () => preview_import(frm), __("Actions"));
			frm.add_custom_button(__("Start Import"), () => start_import(frm), __("Actions"));
			frm.page.set_inner_btn_group_as_primary(__("Actions"));
		}

		frm.add_custom_button(__("Download Template"), () => download_template());

		if (frm.doc.status) {
			const colors = {
				"Draft": "gray",
				"Importing": "orange",
				"Success": "green",
				"Partial Success": "yellow",
				"Failed": "red"
			};
			frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "gray");
		}
	}
});

function preview_import(frm) {
	frappe.dom.freeze(__("Validating file..."));
	frm.call("preview_import")
		.then((r) => {
			frappe.dom.unfreeze();
			if (r.message && r.message.success) {
				const m = r.message;
				const indicator = m.errors > 0 ? "red" : (m.warnings > 0 ? "orange" : "green");
				frappe.show_alert({
					message: __("Preview ready: {0} row(s), {1} error(s), {2} warning(s)", [m.rows_total, m.errors, m.warnings]),
					indicator: indicator
				}, 7);
			} else {
				frappe.msgprint({
					title: __("Preview Failed"),
					message: (r.message && r.message.message) || __("Unknown error"),
					indicator: "red"
				});
			}
			frm.reload_doc();
		})
		.catch((err) => {
			frappe.dom.unfreeze();
			frappe.msgprint({
				title: __("Preview Failed"),
				message: err.message || String(err),
				indicator: "red"
			});
		});
}

function start_import(frm) {
	frappe.confirm(
		__("Start importing Assets from the uploaded file? This will create Items, Item Groups, Asset Categories and Locations as needed."),
		() => {
			frappe.dom.freeze(__("Importing... please wait"));
			frm.call("start_import")
				.then((r) => {
					frappe.dom.unfreeze();
					if (r.message && r.message.success) {
						const m = r.message;
						const indicator = m.rows_failed > 0 ? (m.rows_success > 0 ? "orange" : "red") : "green";
						frappe.msgprint({
							title: __("Import Finished"),
							message: __("Total: {0} · Success: {1} · Failed: {2}", [m.rows_total, m.rows_success, m.rows_failed]),
							indicator: indicator
						});
					} else {
						frappe.msgprint({
							title: __("Import Failed"),
							message: (r.message && r.message.message) || __("Unknown error"),
							indicator: "red"
						});
					}
					frm.reload_doc();
				})
				.catch((err) => {
					frappe.dom.unfreeze();
					frappe.msgprint({
						title: __("Import Failed"),
						message: err.message || String(err),
						indicator: "red"
					});
				});
		}
	);
}

function download_template() {
	const headers = ["Asset Name", "Item Name", "Category", "Location", "RFID Tag", "Images"];
	const sample = [
		"Laptop-001",
		"Dell Latitude 5420",
		"IT Equipment",
		"Head Office",
		"RFID-0001",
		"/files/laptop1.jpg, /files/laptop2.jpg"
	];

	const csv = [
		headers.join(","),
		sample.map(v => `"${v.replace(/"/g, '""')}"`).join(",")
	].join("\n");

	const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = "asset_bulk_import_template.csv";
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}
