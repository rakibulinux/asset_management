"""
Vehicle Inspection API
======================
Base URL prefix: /api/method/asset_management.vehicle_inspection.api

All endpoints require authentication (allow_guest=False).
POST/PUT bodies must be JSON. GET parameters are query-string.
Images are passed as base64-encoded strings (without data-URL header).
"""

from __future__ import annotations

import frappe
from frappe import _

# ─────────────────────────────────────────────────────────────────────────────
# Default item lists (mirrors car_inspection.py)
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_EQUIPMENTS = [
    ("First Aid Kit",           "حقيبة الإسعافات الأولية"),
    ("Fire Extinguisher",       "طفاية الحريق"),
    ("Warning Triangle",        "مثلث التحذير"),
    ("Tyre and Spare Tyres",    "الإطار والإطار الاحتياطي"),
    ("Jack",                    "الرافعة"),
    ("Steering Wheel",          "عجلة القيادة"),
]

_DEFAULT_ENGINE = [
    ("Oil Level",               "مستوى الزيت"),
    ("Coolant Level",           "مستوى سائل التبريد"),
    ("Brake Fluid Level",       "مستوى سائل الفرامل"),
    ("Power Steering Fluid",    "سائل نظام التوجيه"),
    ("Windshield Washer Fluid", "سائل غسيل الزجاج الأمامي"),
    ("Cruise Control",          "مثبت السرعة"),
    ("Wiper Condition",         "حالة المساحات"),
    ("Fan",                     "المروحة"),
    ("Battery",                 "البطارية"),
]

_DEFAULT_INTERIOR = [
    ("Car Registration and Insurance", "تسجيل المركبة والتأمين"),
    ("Lights",                         "الأضواء"),
    ("Seats",                          "المقاعد"),
    ("Seat Belt",                      "حزام الأمان"),
    ("Radio",                          "الراديو"),
    ("Driver Safety Equipment",        "معدات سلامة السائق"),
    ("Interior Cleanliness",           "نظافة المقصورة الداخلية"),
]

_DEFAULT_EXTERIOR = [
    ("Plate Number Condition",  "حالة لوحة الأرقام"),
    ("Front Glass",             "الزجاج الأمامي"),
    ("Windows",                 "النوافذ"),
    ("Side Mirrors",            "المرايا الجانبية"),
    ("Tyres and Tyre Pressure", "الإطارات وضغط الإطارات"),
    ("Tyre Profile",            "نقشة الإطارات"),
    ("Body Condition",          "حالة هيكل المركبة"),
    ("Front Side Image",        "صورة الجهة الأمامية"),
    ("Rear Side Image",         "صورة الجهة الخلفية"),
    ("Left Side Image",         "صورة الجهة اليسرى"),
    ("Right Side Image",        "صورة الجهة اليمنى"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_CAR_INSPECTION_IMAGE_FIELDS = {
    "front_image", "rear_image", "left_side_image", "right_side_image",
    "top_image", "interior_image", "additional_image",
}


def _attach_image(doctype: str, docname: str, filename: str, base64_content: str,
                  content_type: str | None = None) -> str:
    """Save a base64 image as a File doc and return its URL."""
    if not base64_content:
        frappe.throw(_("Empty image content"))
    filename = filename or "image.jpg"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "attached_to_doctype": doctype,
        "attached_to_name": docname,
        "is_private": 0,
        "content": base64_content,
        "decode": 1,
    })
    if content_type:
        file_doc.content_type = content_type
    file_doc.insert(ignore_permissions=True)
    return file_doc.file_url


def _ok(data: dict | None = None, **kwargs) -> dict:
    result = {"success": True}
    if data:
        result.update(data)
    result.update(kwargs)
    return result


def _err(e: Exception) -> dict:
    frappe.log_error(str(e), "Vehicle Inspection API")
    return {"success": False, "message": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Car Inspection
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_car_inspections(vehicle=None, inspector=None, from_date=None,
                        to_date=None, status=None, limit=50, offset=0):
    """
    GET /api/method/asset_management.vehicle_inspection.api.get_car_inspections

    Query params (all optional):
      vehicle, inspector, from_date (YYYY-MM-DD), to_date, status, limit, offset
    """
    try:
        filters = {}
        if vehicle:
            filters["vehicle"] = vehicle
        if inspector:
            filters["inspector"] = inspector
        if status:
            filters["overall_status"] = status
        if from_date:
            filters["inspection_date"] = [">=", from_date]
        if to_date:
            existing = filters.get("inspection_date")
            if existing:
                filters["inspection_date"] = ["between", [from_date, to_date]]
            else:
                filters["inspection_date"] = ["<=", to_date]

        inspections = frappe.get_list(
            "Car Inspection",
            filters=filters,
            fields=[
                "name", "vehicle_number", "vehicle", "plate_number",
                "inspector", "inspection_date", "inspection_time",
                "overall_status", "mileage", "fuel_level",
                "make", "model", "color", "scan_method",
                "creation", "modified",
            ],
            order_by="inspection_date desc, creation desc",
            limit_start=int(offset),
            limit_page_length=int(limit),
        )
        return _ok(inspections=inspections, count=len(inspections))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def get_car_inspection(inspection_id):
    """
    GET /api/method/asset_management.vehicle_inspection.api.get_car_inspection
        ?inspection_id=INSP-00001

    Returns full inspection detail including all 4 sub-sections.
    """
    try:
        if not inspection_id:
            frappe.throw(_("inspection_id is required"))

        doc = frappe.get_doc("Car Inspection", inspection_id)

        equipments = frappe.get_all(
            "Equipments",
            filters={"car_inspection": inspection_id},
            fields=["name", "name_english", "name_arabic", "rfid_code",
                    "rfid_detected", "status", "description", "picture"],
            order_by="name_english asc",
        )
        engine_items = frappe.get_all(
            "Engine Inspection",
            filters={"car_inspection": inspection_id},
            fields=["name", "name_english", "name_arabic", "status",
                    "description", "picture"],
            order_by="name_english asc",
        )
        interior_items = frappe.get_all(
            "Interior Inspection",
            filters={"car_inspection": inspection_id},
            fields=["name", "name_english", "name_arabic", "status",
                    "description", "picture"],
            order_by="name_english asc",
        )
        exterior_items = frappe.get_all(
            "Exterior Inspection",
            filters={"car_inspection": inspection_id},
            fields=["name", "name_english", "name_arabic", "status",
                    "description", "picture"],
            order_by="name_english asc",
        )

        return _ok(inspection={
            "name":                doc.name,
            "vehicle_number":      doc.vehicle_number,
            "vehicle":             doc.vehicle,
            "plate_number":        doc.plate_number,
            "vehicle_code":        doc.vehicle_code,
            "barcode":             doc.barcode,
            "rfid_code":           doc.rfid_code,
            "make":                doc.make,
            "model":               doc.model,
            "color":               doc.color,
            "chassis_number":      doc.chassis_number,
            "registration_number": doc.registration_number,
            "insurance_number":    doc.insurance_number,
            "inspector":           doc.inspector,
            "inspection_date":     str(doc.inspection_date) if doc.inspection_date else None,
            "inspection_time":     str(doc.inspection_time) if doc.inspection_time else None,
            "scan_method":         doc.scan_method,
            "mileage":             doc.mileage,
            "fuel_level":          doc.fuel_level,
            "overall_status":      doc.overall_status,
            "front_image":         doc.front_image,
            "rear_image":          doc.rear_image,
            "left_side_image":     doc.left_side_image,
            "right_side_image":    doc.right_side_image,
            "top_image":           doc.top_image,
            "interior_image":      doc.interior_image,
            "additional_image":    doc.additional_image,
            "faults_and_notes":    doc.faults_and_notes,
            "creation":            str(doc.creation),
            "modified":            str(doc.modified),
            "equipments":          equipments,
            "engine_inspection":   engine_items,
            "interior_inspection": interior_items,
            "exterior_inspection": exterior_items,
        })
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def create_car_inspection():
    """
    POST /api/method/asset_management.vehicle_inspection.api.create_car_inspection

    Body (JSON):
    {
      "vehicle_number": "V-001",   // required
      "inspector": "user@example.com",  // required
      "inspection_date": "2026-05-04",  // required
      "vehicle": "VEH-001",
      "plate_number": "...",
      "vehicle_code": "...",
      "barcode": "...",
      "rfid_code": "...",
      "make": "...", "model": "...", "color": "...",
      "chassis_number": "...", "registration_number": "...", "insurance_number": "...",
      "inspection_time": "HH:MM:SS",
      "scan_method": "Manual|Barcode|RFID",
      "mileage": 12345,
      "fuel_level": "Full|3/4|1/2|1/4|Empty",
      "overall_status": "Draft",
      "faults_and_notes": "..."
    }

    Creates the inspection and auto-inserts default items for all 4 sections.
    """
    try:
        data = frappe.request.json or {}

        if not data.get("vehicle_number"):
            frappe.throw(_("vehicle_number is required"))
        if not data.get("inspector"):
            frappe.throw(_("inspector is required"))
        if not data.get("inspection_date"):
            frappe.throw(_("inspection_date is required"))

        doc = frappe.get_doc({
            "doctype":             "Car Inspection",
            "vehicle_number":      data["vehicle_number"],
            "vehicle":             data.get("vehicle"),
            "plate_number":        data.get("plate_number"),
            "vehicle_code":        data.get("vehicle_code"),
            "barcode":             data.get("barcode"),
            "rfid_code":           data.get("rfid_code"),
            "make":                data.get("make"),
            "model":               data.get("model"),
            "color":               data.get("color"),
            "chassis_number":      data.get("chassis_number"),
            "registration_number": data.get("registration_number"),
            "insurance_number":    data.get("insurance_number"),
            "inspector":           data["inspector"],
            "inspection_date":     data["inspection_date"],
            "inspection_time":     data.get("inspection_time"),
            "scan_method":         data.get("scan_method", "Manual"),
            "mileage":             data.get("mileage"),
            "fuel_level":          data.get("fuel_level"),
            "overall_status":      data.get("overall_status", "Draft"),
            "faults_and_notes":    data.get("faults_and_notes"),
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return _ok(inspection_id=doc.name, message=_("Car Inspection created"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def update_car_inspection():
    """
    PUT /api/method/asset_management.vehicle_inspection.api.update_car_inspection

    Body (JSON):
    {
      "inspection_id": "INSP-00001",   // required
      "mileage": 15000,
      "fuel_level": "1/2",
      "overall_status": "Passed",
      "faults_and_notes": "...",
      "scan_method": "...",
      "inspection_time": "...",
      "plate_number": "...",
      ... any top-level field of Car Inspection
    }
    """
    try:
        data = frappe.request.json or {}
        inspection_id = data.get("inspection_id")
        if not inspection_id:
            frappe.throw(_("inspection_id is required"))

        doc = frappe.get_doc("Car Inspection", inspection_id)

        updatable = [
            "vehicle_number", "vehicle", "plate_number", "vehicle_code",
            "barcode", "rfid_code", "make", "model", "color",
            "chassis_number", "registration_number", "insurance_number",
            "inspector", "inspection_date", "inspection_time", "scan_method",
            "mileage", "fuel_level", "overall_status", "faults_and_notes",
        ]
        for field in updatable:
            if field in data:
                setattr(doc, field, data[field])

        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return _ok(inspection_id=doc.name, message=_("Car Inspection updated"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def delete_car_inspection():
    """
    DELETE /api/method/asset_management.vehicle_inspection.api.delete_car_inspection

    Body (JSON):  { "inspection_id": "INSP-00001" }
    """
    try:
        data = frappe.request.json or {}
        inspection_id = data.get("inspection_id")
        if not inspection_id:
            frappe.throw(_("inspection_id is required"))

        frappe.delete_doc("Car Inspection", inspection_id, ignore_permissions=True)
        frappe.db.commit()
        return _ok(message=_("Car Inspection deleted"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def submit_car_inspection():
    """
    POST /api/method/asset_management.vehicle_inspection.api.submit_car_inspection

    Body (JSON):
    {
      "inspection_id": "INSP-00001",
      "overall_status": "Passed"   // optional, defaults to "Passed"
    }

    Finalises the inspection by setting overall_status to Passed/Failed.
    """
    try:
        data = frappe.request.json or {}
        inspection_id = data.get("inspection_id")
        if not inspection_id:
            frappe.throw(_("inspection_id is required"))

        final_status = data.get("overall_status", "Passed")
        if final_status not in ("Passed", "Failed", "Needs Maintenance"):
            frappe.throw(_("overall_status must be Passed, Failed, or Needs Maintenance"))

        doc = frappe.get_doc("Car Inspection", inspection_id)
        doc.overall_status = final_status
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return _ok(inspection_id=doc.name, overall_status=doc.overall_status,
                   message=_("Car Inspection submitted"))
    except Exception as e:
        return _err(e)


# ─────────────────────────────────────────────────────────────────────────────
# Default Inspection Items
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_default_inspection_items():
    """
    GET /api/method/asset_management.vehicle_inspection.api.get_default_inspection_items

    Returns the master list of default items for all 4 sections.
    """
    try:
        return _ok(defaults={
            "equipments":          [{"name_english": e, "name_arabic": a} for e, a in _DEFAULT_EQUIPMENTS],
            "engine_inspection":   [{"name_english": e, "name_arabic": a} for e, a in _DEFAULT_ENGINE],
            "interior_inspection": [{"name_english": e, "name_arabic": a} for e, a in _DEFAULT_INTERIOR],
            "exterior_inspection": [{"name_english": e, "name_arabic": a} for e, a in _DEFAULT_EXTERIOR],
        })
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def create_default_items_for_inspection():
    """
    POST /api/method/asset_management.vehicle_inspection.api.create_default_items_for_inspection

    Body (JSON):  { "inspection_id": "INSP-00001" }

    Creates all default items if they don't already exist for this inspection.
    """
    try:
        data = frappe.request.json or {}
        inspection_id = data.get("inspection_id")
        if not inspection_id:
            frappe.throw(_("inspection_id is required"))

        if not frappe.db.exists("Car Inspection", inspection_id):
            frappe.throw(_("Car Inspection {0} not found").format(inspection_id))

        created = {"equipments": 0, "engine_inspection": 0,
                   "interior_inspection": 0, "exterior_inspection": 0}

        for name_en, name_ar in _DEFAULT_EQUIPMENTS:
            if not frappe.db.exists("Equipments", {"car_inspection": inspection_id, "name_english": name_en}):
                frappe.get_doc({"doctype": "Equipments", "car_inspection": inspection_id,
                                "name_english": name_en, "name_arabic": name_ar,
                                "rfid_detected": 0}).insert(ignore_permissions=True)
                created["equipments"] += 1

        for name_en, name_ar in _DEFAULT_ENGINE:
            if not frappe.db.exists("Engine Inspection", {"car_inspection": inspection_id, "name_english": name_en}):
                frappe.get_doc({"doctype": "Engine Inspection", "car_inspection": inspection_id,
                                "name_english": name_en, "name_arabic": name_ar}).insert(ignore_permissions=True)
                created["engine_inspection"] += 1

        for name_en, name_ar in _DEFAULT_INTERIOR:
            if not frappe.db.exists("Interior Inspection", {"car_inspection": inspection_id, "name_english": name_en}):
                frappe.get_doc({"doctype": "Interior Inspection", "car_inspection": inspection_id,
                                "name_english": name_en, "name_arabic": name_ar}).insert(ignore_permissions=True)
                created["interior_inspection"] += 1

        for name_en, name_ar in _DEFAULT_EXTERIOR:
            if not frappe.db.exists("Exterior Inspection", {"car_inspection": inspection_id, "name_english": name_en}):
                frappe.get_doc({"doctype": "Exterior Inspection", "car_inspection": inspection_id,
                                "name_english": name_en, "name_arabic": name_ar}).insert(ignore_permissions=True)
                created["exterior_inspection"] += 1

        frappe.db.commit()
        return _ok(created=created, message=_("Default items created"))
    except Exception as e:
        return _err(e)


# ─────────────────────────────────────────────────────────────────────────────
# Generic helpers for the 4 sub-doctypes
# ─────────────────────────────────────────────────────────────────────────────

def _get_items(doctype, inspection_id, extra_fields=None):
    fields = ["name", "name_english", "name_arabic", "status", "description", "picture"]
    if extra_fields:
        fields += extra_fields
    return frappe.get_all(
        doctype,
        filters={"car_inspection": inspection_id},
        fields=fields,
        order_by="name_english asc",
    )


def _create_item(doctype, data, extra_fields=None):
    inspection_id = data.get("inspection_id") or data.get("car_inspection")
    if not inspection_id:
        frappe.throw(_("inspection_id is required"))
    if not data.get("name_english"):
        frappe.throw(_("name_english is required"))

    doc = frappe.get_doc({
        "doctype":        doctype,
        "car_inspection": inspection_id,
        "name_english":   data["name_english"],
        "name_arabic":    data.get("name_arabic"),
        "status":         data.get("status"),
        "description":    data.get("description"),
    })
    if extra_fields:
        for f in extra_fields:
            if f in data:
                setattr(doc, f, data[f])
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


def _update_item(doctype, data, extra_fields=None):
    item_id = data.get("item_id") or data.get("name")
    if not item_id:
        frappe.throw(_("item_id is required"))

    doc = frappe.get_doc(doctype, item_id)
    for field in ["name_english", "name_arabic", "status", "description"]:
        if field in data:
            setattr(doc, field, data[field])
    if extra_fields:
        for f in extra_fields:
            if f in data:
                setattr(doc, f, data[f])
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


def _delete_item(doctype, data):
    item_id = data.get("item_id") or data.get("name")
    if not item_id:
        frappe.throw(_("item_id is required"))
    frappe.delete_doc(doctype, item_id, ignore_permissions=True)
    frappe.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Equipments
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_equipments(inspection_id):
    """
    GET .../get_equipments?inspection_id=INSP-00001
    """
    try:
        items = _get_items("Equipments", inspection_id,
                           extra_fields=["rfid_code", "rfid_detected"])
        return _ok(equipments=items, count=len(items))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def create_equipment():
    """
    POST .../create_equipment

    Body: { "inspection_id": "INSP-00001", "name_english": "...", "name_arabic": "...",
            "rfid_code": "...", "status": "...", "description": "..." }
    """
    try:
        data = frappe.request.json or {}
        name = _create_item("Equipments", data, extra_fields=["rfid_code", "rfid_detected"])
        return _ok(item_id=name, message=_("Equipment created"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def update_equipment():
    """
    PUT .../update_equipment

    Body: { "item_id": "EQ-00001", "status": "Good", "description": "...",
            "rfid_code": "...", "rfid_detected": 1 }
    """
    try:
        data = frappe.request.json or {}
        _update_item("Equipments", data, extra_fields=["rfid_code", "rfid_detected"])
        return _ok(message=_("Equipment updated"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def delete_equipment():
    """
    DELETE .../delete_equipment

    Body: { "item_id": "EQ-00001" }
    """
    try:
        _delete_item("Equipments", frappe.request.json or {})
        return _ok(message=_("Equipment deleted"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def scan_equipment_rfid():
    """
    POST .../scan_equipment_rfid

    Body: { "rfid_code": "RFID-ABC123", "inspection_id": "INSP-00001" }

    Finds the matching Equipment by RFID code within the inspection and marks
    rfid_detected = 1.  Returns the matched item or an error if not found.
    """
    try:
        data = frappe.request.json or {}
        rfid_code = (data.get("rfid_code") or "").strip().upper()
        inspection_id = data.get("inspection_id")

        if not rfid_code:
            frappe.throw(_("rfid_code is required"))
        if not inspection_id:
            frappe.throw(_("inspection_id is required"))

        matches = frappe.get_all(
            "Equipments",
            filters={"car_inspection": inspection_id,
                     "rfid_code": rfid_code},
            fields=["name", "name_english", "name_arabic"],
        )

        if not matches:
            return _ok(matched=False,
                       message=_("No equipment found with RFID {0}").format(rfid_code))

        item = frappe.get_doc("Equipments", matches[0].name)
        item.rfid_detected = 1
        item.save(ignore_permissions=True)
        frappe.db.commit()

        return _ok(matched=True, item_id=item.name,
                   name_english=item.name_english,
                   name_arabic=item.name_arabic,
                   message=_("RFID detected"))
    except Exception as e:
        return _err(e)


# ─────────────────────────────────────────────────────────────────────────────
# Engine Inspection
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_engine_items(inspection_id):
    """GET .../get_engine_items?inspection_id=INSP-00001"""
    try:
        items = _get_items("Engine Inspection", inspection_id)
        return _ok(engine_items=items, count=len(items))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def create_engine_item():
    """POST .../create_engine_item"""
    try:
        name = _create_item("Engine Inspection", frappe.request.json or {})
        return _ok(item_id=name, message=_("Engine item created"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def update_engine_item():
    """PUT .../update_engine_item"""
    try:
        _update_item("Engine Inspection", frappe.request.json or {})
        return _ok(message=_("Engine item updated"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def delete_engine_item():
    """DELETE .../delete_engine_item"""
    try:
        _delete_item("Engine Inspection", frappe.request.json or {})
        return _ok(message=_("Engine item deleted"))
    except Exception as e:
        return _err(e)


# ─────────────────────────────────────────────────────────────────────────────
# Interior Inspection
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_interior_items(inspection_id):
    """GET .../get_interior_items?inspection_id=INSP-00001"""
    try:
        items = _get_items("Interior Inspection", inspection_id)
        return _ok(interior_items=items, count=len(items))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def create_interior_item():
    """POST .../create_interior_item"""
    try:
        name = _create_item("Interior Inspection", frappe.request.json or {})
        return _ok(item_id=name, message=_("Interior item created"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def update_interior_item():
    """PUT .../update_interior_item"""
    try:
        _update_item("Interior Inspection", frappe.request.json or {})
        return _ok(message=_("Interior item updated"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def delete_interior_item():
    """DELETE .../delete_interior_item"""
    try:
        _delete_item("Interior Inspection", frappe.request.json or {})
        return _ok(message=_("Interior item deleted"))
    except Exception as e:
        return _err(e)


# ─────────────────────────────────────────────────────────────────────────────
# Exterior Inspection
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_exterior_items(inspection_id):
    """GET .../get_exterior_items?inspection_id=INSP-00001"""
    try:
        items = _get_items("Exterior Inspection", inspection_id)
        return _ok(exterior_items=items, count=len(items))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def create_exterior_item():
    """POST .../create_exterior_item"""
    try:
        name = _create_item("Exterior Inspection", frappe.request.json or {})
        return _ok(item_id=name, message=_("Exterior item created"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def update_exterior_item():
    """PUT .../update_exterior_item"""
    try:
        _update_item("Exterior Inspection", frappe.request.json or {})
        return _ok(message=_("Exterior item updated"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def delete_exterior_item():
    """DELETE .../delete_exterior_item"""
    try:
        _delete_item("Exterior Inspection", frappe.request.json or {})
        return _ok(message=_("Exterior item deleted"))
    except Exception as e:
        return _err(e)


# ─────────────────────────────────────────────────────────────────────────────
# Upload Images
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def upload_car_inspection_image():
    """
    POST .../upload_car_inspection_image

    Body:
    {
      "inspection_id": "INSP-00001",
      "field_name": "front_image",   // front_image | rear_image | left_side_image |
                                     // right_side_image | top_image | interior_image | additional_image
      "filename": "front.jpg",
      "base64": "<base64-string-without-data-url-header>",
      "content_type": "image/jpeg"
    }
    """
    try:
        data = frappe.request.json or {}
        inspection_id = data.get("inspection_id")
        field_name    = data.get("field_name")
        base64_data   = data.get("base64")
        filename      = data.get("filename", "image.jpg")
        content_type  = data.get("content_type")

        if not inspection_id:
            frappe.throw(_("inspection_id is required"))
        if field_name not in _CAR_INSPECTION_IMAGE_FIELDS:
            frappe.throw(_("field_name must be one of: {0}").format(
                ", ".join(sorted(_CAR_INSPECTION_IMAGE_FIELDS))))

        file_url = _attach_image("Car Inspection", inspection_id,
                                 filename, base64_data, content_type)

        doc = frappe.get_doc("Car Inspection", inspection_id)
        setattr(doc, field_name, file_url)
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return _ok(file_url=file_url, field_name=field_name,
                   message=_("Image uploaded"))
    except Exception as e:
        return _err(e)


def _upload_item_image(doctype, data):
    item_id      = data.get("item_id") or data.get("name")
    base64_data  = data.get("base64")
    filename     = data.get("filename", "image.jpg")
    content_type = data.get("content_type")

    if not item_id:
        frappe.throw(_("item_id is required"))

    file_url = _attach_image(doctype, item_id, filename, base64_data, content_type)

    doc = frappe.get_doc(doctype, item_id)
    doc.picture = file_url
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return file_url


@frappe.whitelist(allow_guest=False)
def upload_equipment_image():
    """
    POST .../upload_equipment_image

    Body: { "item_id": "EQ-00001", "filename": "...", "base64": "...", "content_type": "..." }
    """
    try:
        file_url = _upload_item_image("Equipments", frappe.request.json or {})
        return _ok(file_url=file_url, message=_("Image uploaded"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def upload_engine_item_image():
    """
    POST .../upload_engine_item_image

    Body: { "item_id": "ENGI-00001", "filename": "...", "base64": "...", "content_type": "..." }
    """
    try:
        file_url = _upload_item_image("Engine Inspection", frappe.request.json or {})
        return _ok(file_url=file_url, message=_("Image uploaded"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def upload_interior_item_image():
    """
    POST .../upload_interior_item_image

    Body: { "item_id": "INTI-00001", "filename": "...", "base64": "...", "content_type": "..." }
    """
    try:
        file_url = _upload_item_image("Interior Inspection", frappe.request.json or {})
        return _ok(file_url=file_url, message=_("Image uploaded"))
    except Exception as e:
        return _err(e)


@frappe.whitelist(allow_guest=False)
def upload_exterior_item_image():
    """
    POST .../upload_exterior_item_image

    Body: { "item_id": "EXTI-00001", "filename": "...", "base64": "...", "content_type": "..." }
    """
    try:
        file_url = _upload_item_image("Exterior Inspection", frappe.request.json or {})
        return _ok(file_url=file_url, message=_("Image uploaded"))
    except Exception as e:
        return _err(e)
