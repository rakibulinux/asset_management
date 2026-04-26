from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import today, add_days
from frappe.utils.data import cint


def execute(filters=None):
	filters = frappe._dict(filters or {})

	filters.from_date = filters.get("from_date") or add_days(today(), -30)
	filters.to_date = filters.get("to_date") or today()
	filters.show_only_incomplete = cint(filters.get("show_only_incomplete") or 0)

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(filters)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Audit"),
			"fieldname": "audit_name",
			"fieldtype": "Link",
			"options": "Asset Audit",
			"width": 180,
		},
		{
			"label": _("Audit Date"),
			"fieldname": "audit_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Location"),
			"fieldname": "location",
			"fieldtype": "Link",
			"options": "Location",
			"width": 160,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Completion State"),
			"fieldname": "completion_state",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Total Expected"),
			"fieldname": "total_expected",
			"fieldtype": "Int",
			"width": 115,
		},
		{
			"label": _("Total Detected"),
			"fieldname": "total_detected",
			"fieldtype": "Int",
			"width": 115,
		},
		{
			"label": _("Total Missing"),
			"fieldname": "total_missing",
			"fieldtype": "Int",
			"width": 115,
		},
		{
			"label": _("Total Unidentified"),
			"fieldname": "total_unidentified",
			"fieldtype": "Int",
			"width": 130,
		},
		{
			"label": _("Detection Rate %"),
			"fieldname": "detection_rate",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 120,
		},
		{
			"label": _("Assigned To"),
			"fieldname": "assigned_to",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Completed By"),
			"fieldname": "completed_by",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Audited By"),
			"fieldname": "audited_by",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Audit Result"),
			"fieldname": "audit_result",
			"fieldtype": "Data",
			"width": 130,
		},
	]


def get_conditions(filters):
	conditions = ["audit_date >= %(from_date)s", "audit_date <= %(to_date)s"]
	params = {
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}

	if filters.get("location"):
		conditions.append("location = %(location)s")
		params["location"] = filters.location

	if filters.get("status"):
		conditions.append("status = %(status)s")
		params["status"] = filters.status

	if cint(filters.get("show_only_incomplete")):
		conditions.append("(COALESCE(status, '') != 'Completed' AND completed_on IS NULL)")

	return conditions, params


def get_data(filters):
	conditions, params = get_conditions(filters)
	where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

	rows = frappe.db.sql(
		f"""
		SELECT
			name AS audit_name,
			audit_date,
			location,
			COALESCE(NULLIF(status, ''), 'No Status') AS status,
			CASE
				WHEN status = 'Completed' OR completed_on IS NOT NULL THEN 'Completed'
				ELSE 'Incomplete'
			END AS completion_state,
			COALESCE(total_expected, 0) AS total_expected,
			COALESCE(total_detected, 0) AS total_detected,
			COALESCE(total_missing, 0) AS total_missing,
			COALESCE(total_unidentified, 0) AS total_unidentified,
			assigned_to,
			completed_by,
			audited_by,
			audit_result
		FROM `tabAsset Audit`
		{where_clause}
		ORDER BY audit_date DESC, modified DESC
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		expected = float(row.total_expected or 0)
		detected = float(row.total_detected or 0)
		row.detection_rate = round((detected * 100.0 / expected), 2) if expected else 0

	return rows


def get_chart(filters):
	conditions, params = get_conditions(filters)
	where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

	status_rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(NULLIF(status, ''), 'No Status') AS status_label,
			COUNT(name) AS audit_count
		FROM `tabAsset Audit`
		{where_clause}
		GROUP BY status_label
		ORDER BY audit_count DESC
		""",
		params,
		as_dict=True,
	)

	labels = [d.status_label for d in status_rows]
	values = [int(d.audit_count or 0) for d in status_rows]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Audit Count"),
					"values": values,
				}
			],
		},
		"type": "pie",
		"height": 320,
	}


def get_report_summary(data):
	total_audits = len(data)
	total_expected = sum(float(d.get("total_expected") or 0) for d in data)
	total_detected = sum(float(d.get("total_detected") or 0) for d in data)
	total_missing = sum(float(d.get("total_missing") or 0) for d in data)
	total_unidentified = sum(float(d.get("total_unidentified") or 0) for d in data)

	completed_audits = sum(1 for d in data if d.get("completion_state") == "Completed")
	incomplete_audits = total_audits - completed_audits

	detection_rate = round((total_detected * 100.0 / total_expected), 2) if total_expected else 0
	completion_rate = round((completed_audits * 100.0 / total_audits), 2) if total_audits else 0

	return [
		{
			"value": detection_rate,
			"label": _("Asset Detection Rate"),
			"datatype": "Percent",
			"indicator": "Green" if detection_rate >= 90 else "Orange",
		},
		{
			"value": completed_audits,
			"label": _("Completed Audits"),
			"datatype": "Int",
			"indicator": "Green",
		},
		{
			"value": incomplete_audits,
			"label": _("Incomplete Audits"),
			"datatype": "Int",
			"indicator": "Red" if incomplete_audits > 0 else "Green",
		},
		{
			"value": total_missing,
			"label": _("Total Missing"),
			"datatype": "Int",
			"indicator": "Red" if total_missing > 0 else "Green",
		},
		{
			"value": total_unidentified,
			"label": _("Total Unidentified"),
			"datatype": "Int",
			"indicator": "Orange" if total_unidentified > 0 else "Green",
		},
		{
			"value": completion_rate,
			"label": _("Completion Rate"),
			"datatype": "Percent",
			"indicator": "Blue",
		},
	]