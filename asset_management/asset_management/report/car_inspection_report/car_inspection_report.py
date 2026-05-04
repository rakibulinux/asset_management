from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if not filters.get("car_inspection"):
		return get_columns(), [], _("Please select a Car Inspection.")

	doc = frappe.get_doc("Car Inspection", filters.car_inspection)

	message = get_inspection_header_html(doc)
	columns = get_columns()
	data = get_data(filters.car_inspection)

	return columns, data, message


def get_columns():
	return [
		{
			"label": _("Section / Name"),
			"fieldname": "name_english",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Name Arabic"),
			"fieldname": "name_arabic",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("RFID Code"),
			"fieldname": "rfid_code",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("RFID Detected"),
			"fieldname": "rfid_detected",
			"fieldtype": "Check",
			"width": 110,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 260,
		},
	]


def _section_row(label):
	return frappe._dict(
		name_english=label,
		name_arabic="",
		rfid_code="",
		rfid_detected="",
		status="",
		description="",
		_doc_name="",
		_doctype="",
		_is_section_header=True,
	)


def _empty_row():
	return frappe._dict(name_english=_("— No records —"), name_arabic="", rfid_code="", rfid_detected="", status="", description="", _doc_name="", _doctype="")


def get_data(car_inspection):
	rows = []

	# ── Equipments ──────────────────────────────────────────────────────────
	rows.append(_section_row("⚙  Equipments"))
	equipments = frappe.get_all(
		"Equipments",
		filters={"car_inspection": car_inspection},
		fields=["name", "name_english", "name_arabic", "rfid_code", "rfid_detected", "status", "description"],
		order_by="name_english asc",
	)
	for row in equipments:
		rows.append(frappe._dict(row, _doc_name=row["name"], _doctype="Equipments"))

	if not equipments:
		rows.append(_empty_row())

	# ── Engine Inspection ────────────────────────────────────────────────────
	rows.append(_section_row("🔧  Engine Inspection"))
	engine_items = frappe.get_all(
		"Engine Inspection",
		filters={"car_inspection": car_inspection},
		fields=["name", "name_english", "name_arabic", "status", "description"],
		order_by="name_english asc",
	)
	for row in engine_items:
		rows.append(frappe._dict(row, rfid_code="", rfid_detected="", _doc_name=row["name"], _doctype="Engine Inspection"))

	if not engine_items:
		rows.append(_empty_row())

	# ── Interior Inspection ──────────────────────────────────────────────────
	rows.append(_section_row("🪑  Interior Inspection"))
	interior_items = frappe.get_all(
		"Interior Inspection",
		filters={"car_inspection": car_inspection},
		fields=["name", "name_english", "name_arabic", "status", "description"],
		order_by="name_english asc",
	)
	for row in interior_items:
		rows.append(frappe._dict(row, rfid_code="", rfid_detected="", _doc_name=row["name"], _doctype="Interior Inspection"))

	if not interior_items:
		rows.append(_empty_row())

	# ── Exterior Inspection ──────────────────────────────────────────────────
	rows.append(_section_row("🚗  Exterior Inspection"))
	exterior_items = frappe.get_all(
		"Exterior Inspection",
		filters={"car_inspection": car_inspection},
		fields=["name", "name_english", "name_arabic", "status", "description"],
		order_by="name_english asc",
	)
	for row in exterior_items:
		rows.append(frappe._dict(row, rfid_code="", rfid_detected="", _doc_name=row["name"], _doctype="Exterior Inspection"))

	if not exterior_items:
		rows.append(_empty_row())

	return rows


def get_inspection_header_html(doc):
	status_color = {
		"Draft": "#6b7280",
		"Passed": "#16a34a",
		"Failed": "#dc2626",
		"Needs Maintenance": "#d97706",
	}.get(doc.overall_status or "Draft", "#6b7280")

	def img(url, label):
		if not url:
			return ""
		return f"""
			<div style="text-align:center; flex:1; min-width:120px; max-width:160px;">
				<img src="{url}" style="width:100%; height:110px; object-fit:cover; border-radius:6px; border:1px solid #e5e7eb;" />
				<div style="font-size:11px; color:#6b7280; margin-top:4px;">{label}</div>
			</div>"""

	images_html = "".join([
		img(doc.front_image,    "Front"),
		img(doc.rear_image,     "Rear"),
		img(doc.left_side_image,  "Left"),
		img(doc.right_side_image, "Right"),
		img(doc.top_image,       "Top"),
		img(doc.interior_image,  "Interior"),
		img(doc.additional_image, "Additional"),
	])

	images_section = f"""
		<div style="margin-top:16px;">
			<div style="font-weight:600; color:#374151; margin-bottom:8px; font-size:13px;">Vehicle Images</div>
			<div style="display:flex; flex-wrap:wrap; gap:10px;">
				{images_html}
			</div>
		</div>""" if images_html.strip() else ""

	notes_section = f"""
		<div style="margin-top:16px; padding:12px; background:#fef9c3; border-radius:6px; border:1px solid #fde68a;">
			<div style="font-weight:600; color:#92400e; margin-bottom:4px;">Faults &amp; Notes</div>
			<div style="color:#78350f; font-size:13px;">{doc.faults_and_notes}</div>
		</div>""" if doc.faults_and_notes else ""

	def field(label, value):
		if not value:
			return ""
		return f"""
			<div style="margin-bottom:6px;">
				<span style="color:#6b7280; font-size:11px; text-transform:uppercase; letter-spacing:.5px;">{label}</span><br>
				<span style="color:#111827; font-size:13px; font-weight:500;">{value}</span>
			</div>"""

	return f"""
	<div style="font-family:sans-serif; background:#f9fafb; border:1px solid #e5e7eb; border-radius:10px; padding:20px; margin-bottom:16px;">

		<!-- Header bar -->
		<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; padding-bottom:12px; border-bottom:2px solid #e5e7eb;">
			<div>
				<div style="font-size:18px; font-weight:700; color:#1e3a5f;">Car Inspection Report</div>
				<div style="font-size:13px; color:#6b7280; margin-top:2px;">{doc.name}</div>
			</div>
			<div style="background:{status_color}; color:#fff; padding:6px 16px; border-radius:20px; font-size:13px; font-weight:600;">
				{doc.overall_status or "Draft"}
			</div>
		</div>

		<!-- Two columns: vehicle info + inspection info -->
		<div style="display:grid; grid-template-columns:1fr 1fr; gap:24px;">

			<div>
				<div style="font-weight:600; color:#1a73e8; margin-bottom:10px; font-size:13px; text-transform:uppercase;">Vehicle Information</div>
				{field("Vehicle Number", doc.vehicle_number)}
				{field("Vehicle", doc.vehicle)}
				{field("Plate Number", doc.plate_number)}
				{field("Make", doc.make)}
				{field("Model", doc.model)}
				{field("Color", doc.color)}
				{field("Chassis Number", doc.chassis_number)}
				{field("Registration Number", doc.registration_number)}
				{field("Insurance Number", doc.insurance_number)}
				{field("RFID Code", doc.rfid_code)}
				{field("Barcode", doc.barcode)}
			</div>

			<div>
				<div style="font-weight:600; color:#1a73e8; margin-bottom:10px; font-size:13px; text-transform:uppercase;">Inspection Information</div>
				{field("Inspector", doc.inspector)}
				{field("Inspection Date", str(doc.inspection_date) if doc.inspection_date else "")}
				{field("Inspection Time", str(doc.inspection_time) if doc.inspection_time else "")}
				{field("Scan Method", doc.scan_method)}
				{field("Mileage", str(doc.mileage) + " km" if doc.mileage else "")}
				{field("Fuel Level", doc.fuel_level)}
			</div>
		</div>

		{images_section}
		{notes_section}
	</div>
	"""
