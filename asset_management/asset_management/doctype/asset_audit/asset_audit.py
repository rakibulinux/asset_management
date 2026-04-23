import json
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


@frappe.whitelist()
def get_location_tree(doctype, txt, searchfield, start, page_len, filters):
	locations = frappe.get_all(
		"Location",
		fields=["name", "location_name", "parent_location", "lft", "rgt"],
		filters=[
			["Location", "name", "like", f"%{txt}%"]
		],
		order_by="lft"
	)

	# اگر location_name هم باید جستجو شود
	if txt:
		locations = frappe.db.sql("""
			SELECT name, location_name, parent_location, lft, rgt
			FROM `tabLocation`
			WHERE name LIKE %(txt)s OR location_name LIKE %(txt)s
			ORDER BY lft
			LIMIT %(start)s, %(page_len)s
		""", {
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len
		}, as_dict=True)

	parent_map = {}
	all_locations = frappe.get_all(
		"Location",
		fields=["name", "parent_location"]
	)
	for loc in all_locations:
		parent_map[loc.name] = loc.parent_location

	def get_level(name):
		level = 0
		parent = parent_map.get(name)
		while parent:
			level += 1
			parent = parent_map.get(parent)
		return level

	result = []
	for loc in locations:
		display_name = loc.location_name or loc.name
		level = get_level(loc.name)
		indent = "    " * level
		prefix = "└── " if level > 0 else ""
		result.append([loc.name, f"{indent}{prefix}{display_name}"])

	return result


@frappe.whitelist()
def get_location_tree_data():
	"""Get location tree data for hierarchical display"""
	locations = frappe.get_all("Location",
		fields=["name", "location_name", "parent_location", "is_group", "lft", "rgt"],
		order_by="lft"
	)

	# Build tree structure
	location_map = {}
	root_nodes = []

	for loc in locations:
		loc['children'] = []
		location_map[loc.name] = loc

	for loc in locations:
		if loc.parent_location:
			if loc.parent_location in location_map:
				location_map[loc.parent_location]['children'].append(loc)
		else:
			root_nodes.append(loc)

	return root_nodes



class AssetAudit(Document):
    def before_save(self):
        if self.docstatus != 0:
            return
        # Ensure required fields have values
        if not self.status:
            self.status = "Pending"
        if not self.audit_date:
            self.audit_date = frappe.utils.today()
        if not self.audit_time:
            self.audit_time = frappe.utils.nowtime()
        repopulate = False
        if self.is_new():
            repopulate = True
        else:
            old = self.get_doc_before_save()
            # Check if location or categories changed
            old_categories = [c.category for c in old.categories] if old and old.categories else []
            new_categories = [c.category for c in self.categories] if self.categories else []
            if old and (old.location != self.location or set(old_categories) != set(new_categories)):
                repopulate = True
            elif not self.expected_assets:
                repopulate = True
        if repopulate:
            self.populate_expected_assets()

    @frappe.whitelist()
    def populate_expected_assets(self):
        filters = {}
        if self.location:
            filters["location"] = self.location
        # Get categories from the categories table
        categories = [c.category for c in self.categories] if self.categories else []
        if categories:
            filters["category"] = ["in", categories]

        assets = frappe.get_all(
            "Custom Asset",
            filters=filters,
            fields=["name", "asset_name", "asset_code"]
        )
        self.set("expected_assets", [])
        for a in assets:
            self.append("expected_assets", {
                "asset": a.name,
                "asset_name": a.asset_name,
                "rfid_tag": a.asset_code or "",
                "status": "Expected"
            })
        self.total_expected = len(assets)
        # Ensure totals are set
        self.total_detected = 0
        self.total_missing = 0
        self.total_unidentified = 0


def normalize_rfid(value):
    return (value or "").strip().upper()


@frappe.whitelist()
def process_scanned_codes(audit_name, scanned_codes):
    if isinstance(scanned_codes, str):
        try:
            scanned_codes = json.loads(scanned_codes)
        except Exception:
            scanned_codes = [x.strip() for x in scanned_codes.splitlines() if x.strip()]

    audit = frappe.get_doc("Asset Audit", audit_name)

    if not audit.location:
        frappe.throw("Please select Location first.")

    # Get expected assets from Custom Asset by location and categories
    filters = {"location": audit.location}
    # Get categories from the categories table
    categories = [c.category for c in audit.categories] if audit.categories else []
    if categories:
        filters["category"] = ["in", categories]
    expected_assets = frappe.get_all(
        "Custom Asset",
        filters=filters,
        fields=["name", "asset_name", "asset_code"]
    )

    expected_map = {}
    for asset in expected_assets:
        rfid = normalize_rfid(asset.get("asset_code"))
        if rfid:
            expected_map[rfid] = asset

    # Normalize scanned RFID tags and remove duplicates
    scanned_unique = []
    seen = set()

    for code in scanned_codes:
        rfid = normalize_rfid(code)
        if rfid and rfid not in seen:
            scanned_unique.append(rfid)
            seen.add(rfid)

    # Clear old results
    audit.set("detected_assets", [])
    audit.set("missing_assets", [])
    audit.set("unidentified_tags", [])

    detected_rfids = set()

    # Fill detected assets and unidentified tags
    for rfid in scanned_unique:
        if rfid in expected_map:
            asset = expected_map[rfid]
            detected_rfids.add(rfid)

            audit.append("detected_assets", {
                "asset": asset.get("name"),
                "asset_name": asset.get("asset_name"),
                "rfid_tag": asset.get("asset_code")
            })
        else:
            audit.append("unidentified_tags", {
                "rfid_tag": rfid
            })

    # Fill missing assets
    for rfid, asset in expected_map.items():
        if rfid not in detected_rfids:
            audit.append("missing_assets", {
                "asset": asset.get("name"),
                "asset_name": asset.get("asset_name"),
                "rfid_tag": asset.get("asset_code")
            })

    # Update totals
    audit.total_expected = len(expected_map)
    audit.total_detected = len(detected_rfids)
    audit.total_missing = len(expected_map) - len(detected_rfids)
    audit.total_unidentified = len(scanned_unique) - len(detected_rfids)

    # Set audit result
    if audit.total_expected > 0 and audit.total_missing == 0 and audit.total_unidentified == 0:
        audit.audit_result = "Complete"
    elif audit.total_detected > 0:
        audit.audit_result = "Partial"
    else:
        audit.audit_result = "Failed"

    audit.status = "Completed"
    audit.completed_on = now_datetime()
    audit.completed_by = frappe.session.user

    audit.save(ignore_permissions=True)

    return {
        "total_expected": audit.total_expected,
        "total_detected": audit.total_detected,
        "total_missing": audit.total_missing,
        "total_unidentified": audit.total_unidentified,
        "audit_result": audit.audit_result
    }