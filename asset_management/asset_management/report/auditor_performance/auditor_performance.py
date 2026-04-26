from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Auditor"),
			"fieldname": "auditor",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Total Audits"),
			"fieldname": "total_audits",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Completed Audits"),
			"fieldname": "completed_audits",
			"fieldtype": "Int",
			"width": 140,
		},
		{
			"label": _("Total Expected"),
			"fieldname": "total_expected",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Total Detected"),
			"fieldname": "total_detected",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Total Missing"),
			"fieldname": "total_missing",
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"label": _("Total Unidentified"),
			"fieldname": "total_unidentified",
			"fieldtype": "Int",
			"width": 140,
		},
		{
			"label": _("Detection Rate %"),
			"fieldname": "detection_rate",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 130,
		},
		{
			"label": _("Missing Rate %"),
			"fieldname": "missing_rate",
			"fieldtype": "Percent",
			"precision": 2,
			"width": 120,
		},
	]


def get_data(filters):
	conditions = []
	params = {}

	if filters.get("from_date"):
		conditions.append("audit_date >= %(from_date)s")
		params["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("audit_date <= %(to_date)s")
		params["to_date"] = filters.get("to_date")

	if filters.get("location"):
		conditions.append("location = %(location)s")
		params["location"] = filters.get("location")

	if filters.get("auditor"):
		conditions.append(
			"""(
				audited_by = %(auditor)s
				or completed_by = %(auditor)s
				or assigned_to = %(auditor)s
			)"""
		)
		params["auditor"] = filters.get("auditor")

	where_clause = ""
	if conditions:
		where_clause = "WHERE " + " AND ".join(conditions)

	rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(
				NULLIF(audited_by, ''),
				NULLIF(completed_by, ''),
				NULLIF(assigned_to, ''),
				'Unassigned'
			) AS auditor,
			COUNT(name) AS total_audits,
			SUM(
				CASE
					WHEN status = 'Completed' OR completed_on IS NOT NULL THEN 1
					ELSE 0
				END
			) AS completed_audits,
			SUM(COALESCE(total_expected, 0)) AS total_expected,
			SUM(COALESCE(total_detected, 0)) AS total_detected,
			SUM(COALESCE(total_missing, 0)) AS total_missing,
			SUM(COALESCE(total_unidentified, 0)) AS total_unidentified
		FROM `tabAsset Audit`
		{where_clause}
		GROUP BY auditor
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		expected = float(row.total_expected or 0)
		detected = float(row.total_detected or 0)
		missing = float(row.total_missing or 0)

		row.detection_rate = round((detected * 100.0 / expected), 2) if expected else 0
		row.missing_rate = round((missing * 100.0 / expected), 2) if expected else 0

	rows.sort(
		key=lambda d: (
			float(d.get("detection_rate") or 0),
			int(d.get("total_audits") or 0),
			-int(d.get("total_missing") or 0),
		),
		reverse=True,
	)

	top_n = cint_safe(filters.get("top_n"), 10)
	return rows[:top_n]


def get_chart(data):
	labels = [d.get("auditor") for d in data]
	values = [float(d.get("detection_rate") or 0) for d in data]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Detection Rate %"),
					"values": values,
				}
			],
		},
		"type": "bar",
		"height": 300,
		"fieldtype": "Percent",
	}


def get_report_summary(data):
	total_audits = sum(int(d.get("total_audits") or 0) for d in data)
	total_expected = sum(float(d.get("total_expected") or 0) for d in data)
	total_detected = sum(float(d.get("total_detected") or 0) for d in data)
	total_missing = sum(float(d.get("total_missing") or 0) for d in data)

	avg_detection = round((total_detected * 100.0 / total_expected), 2) if total_expected else 0
	avg_missing = round((total_missing * 100.0 / total_expected), 2) if total_expected else 0

	return [
		{
			"value": len(data),
			"label": _("Auditors"),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": total_audits,
			"label": _("Total Audits"),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": avg_detection,
			"label": _("Average Detection Rate"),
			"datatype": "Percent",
			"indicator": "Green" if avg_detection >= 90 else "Orange",
		},
		{
			"value": avg_missing,
			"label": _("Average Missing Rate"),
			"datatype": "Percent",
			"indicator": "Red" if avg_missing > 10 else "Green",
		},
	]


def cint_safe(value, default=0):
	try:
		return int(value)
	except Exception:
		return default