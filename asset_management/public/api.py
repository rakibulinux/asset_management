import frappe

@frappe.whitelist(allow_guest=True)
def my_endpoint():
    return {
        "status": "ok",
        "message": "API is working"
    }


import frappe
from frappe import _


def _is_admin_user(user: str) -> bool:
    try:
        return "System Manager" in frappe.get_roles(user)
    except Exception:
        return False


def _assert_user_can_access_audit(audit_doc, user: str) -> None:
    if _is_admin_user(user):
        return

    assigned_to = getattr(audit_doc, "assigned_to", None)
    if not assigned_to:
        frappe.throw(_("This audit is not assigned"))
    if assigned_to != user:
        frappe.throw(_("Not permitted"))


def _decode_iso_datetime(value: str) -> str:
    if not value:
        return frappe.utils.now()
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return frappe.utils.now()


def _attach_base64_file(
    *,
    doctype: str,
    docname: str,
    filename: str,
    base64_content: str,
    content_type: str | None = None,
    is_private: int = 0,
):
    """Attach a file to a document using base64 content.

    Expects base64 without the data URL header.
    """
    if not filename:
        filename = "image.jpg"
    if not base64_content:
        frappe.throw(_("Empty file content"))

    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "attached_to_doctype": doctype,
            "attached_to_name": docname,
            "is_private": is_private,
            "content": base64_content,
            "decode": 1,
        }
    )
    if content_type:
        file_doc.content_type = content_type
    file_doc.insert(ignore_permissions=True)
    return file_doc

@frappe.whitelist(allow_guest=False)
def create_asset_audit():
    """
    API endpoint for creating asset audits from mobile RFID app.
    POST /api/method/erpnext.assets.api.create_asset_audit
    
    Request Body (JSON):
    {
        "location": "Store",
        "categories": ["Category1", "Category2"],
        "audit_date": "2026-04-06",
        "audit_time": "06:56:42",
        "audited_by": "",
        "assigned_to": "user@example.com",
        "device_info": "Chainway RFID Scanner",
        "assignee_comment": "...",
        "total_expected": 1,
        "total_detected": 0,
        "total_missing": 1,
        "total_unidentified": 0,
        "notes": "...",
        "expected_assets": [...],
        "detected_assets": [...],
        "missing_assets": [...],
        "unidentified_tags": [...]
    }
    """
    try:
        data = frappe.request.json
        
        # Validate required fields
        if not data.get('location'):
            frappe.throw(_('Location is required'))
        if not data.get('categories'):
            frappe.throw(_('Categories is required'))
        
        # Create the audit document
        audit = frappe.get_doc({
            'doctype': 'Asset Audit',
            'location': data.get('location'),
            'categories': data.get('categories', []),
            'status': 'Pending',
            'audit_date': data.get('audit_date', frappe.utils.today()),
            'assigned_to': data.get('assigned_to'),
            'audit_time': data.get('audit_time', frappe.utils.nowtime()),
            'audited_by': data.get('audited_by'),
            'device_info': data.get('device_info'),
            'assignee_comment': data.get('assignee_comment'),
            'total_expected': data.get('total_expected', 0),
            'total_detected': data.get('total_detected', 0),
            'total_missing': data.get('total_missing', 0),
            'total_unidentified': data.get('total_unidentified', 0),
            'audit_result': 'Pending',
            'notes': data.get('notes')
        })
        
        # Add expected assets from location if none provided
        expected_assets_data = data.get('expected_assets', [])
        if not expected_assets_data and data.get('location'):
            # Auto-fetch assets from the location
            location_assets = frappe.get_all(
                'Asset',
                filters={
                    'location': data.get('location'),
                    'status': ['not in', ['Scrapped', 'Sold']]
                },
                fields=['name', 'asset_name', 'item_code']
            )
            for asset in location_assets:
                audit.append('expected_assets', {
                    'asset': asset.name,
                    'asset_name': asset.asset_name or asset.name,
                    'item_code': asset.item_code,
                    'status': 'Expected'
                })
            # Update totals based on auto-populated assets
            audit.total_expected = len(location_assets)
            audit.total_missing = len(location_assets)
        else:
            # Add expected assets from provided data
            for asset_data in expected_assets_data:
                audit.append('expected_assets', {
                    'asset': asset_data.get('asset'),
                    'asset_name': asset_data.get('asset_name'),
                    'item_code': asset_data.get('item_code'),
                    'status': asset_data.get('status', 'Expected')
                })
        
        # Add detected assets
        for asset_data in data.get('detected_assets', []):
            detection_time = asset_data.get('detection_time')
            if detection_time:
                # Convert ISO format to MySQL datetime format
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(detection_time.replace('Z', '+00:00'))
                    detection_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    detection_time = frappe.utils.now()
            
            audit.append('detected_assets', {
                'asset': asset_data.get('asset'),
                'asset_name': asset_data.get('asset_name'),
                'item_code': asset_data.get('item_code'),
                'rfid_tag': asset_data.get('rfid_tag'),
                'status': 'Detected',
                'detection_time': detection_time,
                'scan_count': asset_data.get('scan_count', 1)
            })
        
        # Add missing assets
        for asset_data in data.get('missing_assets', []):
            audit.append('missing_assets', {
                'asset': asset_data.get('asset'),
                'asset_name': asset_data.get('asset_name'),
                'item_code': asset_data.get('item_code'),
                'rfid_tag': asset_data.get('rfid_tag'),
                'status': 'Missing'
            })
        
        # Add unidentified tags
        for tag_data in data.get('unidentified_tags', []):
            detection_time = tag_data.get('detection_time')
            if detection_time:
                # Convert ISO format to MySQL datetime format
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(detection_time.replace('Z', '+00:00'))
                    detection_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    detection_time = frappe.utils.now()
            
            audit.append('unidentified_tags', {
                'rfid_tag': tag_data.get('rfid_tag'),
                'detection_time': detection_time,
                'scan_count': tag_data.get('scan_count', 1),
                'notes': tag_data.get('notes')
            })
        
        # Determine audit result
        if audit.total_expected == 0:
            audit.audit_result = 'No Assets'
        elif audit.total_missing == 0 and audit.total_unidentified == 0:
            audit.audit_result = 'Complete'
        elif audit.total_detected > 0:
            audit.audit_result = 'Partial'
        else:
            audit.audit_result = 'Failed'
        
        audit.insert()
        frappe.db.commit()
        
        return {
            'success': True,
            'message': 'Audit created successfully',
            'audit_id': audit.name
        }
        
    except Exception as e:
        frappe.log_error(f"Asset Audit API Error: {str(e)}")
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist(allow_guest=False)
def get_my_asset_audits():
    """Get audits assigned to the logged-in user.

    Query params:
    - status: pending|in_progress|completed|all (default pending)
    - limit: default 50
    - offset: default 0
    """
    try:
        user = frappe.session.user
        frappe.logger().info(f"[AUDIT DEBUG] get_my_asset_audits called by user: {user}")
        
        status = (frappe.request.args.get("status") or "pending").lower()
        limit = int(frappe.request.args.get("limit", 50))
        offset = int(frappe.request.args.get("offset", 0))

        filters = {}
        is_admin = _is_admin_user(user)
        frappe.logger().info(f"[AUDIT DEBUG] is_admin: {is_admin}")
        
        if not is_admin:
            filters["assigned_to"] = user

        if status == "pending":
            filters["status"] = ["in", ["Pending", "In Progress"]]
        elif status == "in_progress":
            filters["status"] = "In Progress"
        elif status == "completed":
            filters["status"] = "Completed"
        elif status == "all":
            pass
        else:
            frappe.throw(_("Invalid status"))
        
        frappe.logger().info(f"[AUDIT DEBUG] filters: {filters}")

        audits = frappe.get_list(
            "Asset Audit",
            filters=filters,
            fields=[
                "name",
                "location",
                "categories",
                "audit_date",
                "assigned_to",
                "audit_time",
                "completed_by",
                "audited_by",
                "completed_on",
                "device_info",
                "assignee_comment",
                "status",
                "audit_result",
                "total_expected",
                "total_detected",
                "total_missing",
                "total_unidentified",
                "notes",
                "modified",
                "creation",
            ],
            order_by="modified desc",
            limit_start=offset,
            limit_page_length=limit,
        )
        
        frappe.logger().info(f"[AUDIT DEBUG] found {len(audits)} audits")

        return {"success": True, "audits": audits}
    except Exception as e:
        frappe.log_error(f"Asset Audit get_my_asset_audits error: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist(allow_guest=False)
def get_my_asset_audit_detail(audit_id):
    """Get audit detail, scoped to assigned user (or admin).
    Auto-populates expected_assets from location if empty."""
    try:
        if not audit_id:
            frappe.throw(_("Audit ID is required"))
        user = frappe.session.user
        audit = frappe.get_doc("Asset Audit", audit_id)
        _assert_user_can_access_audit(audit, user)

        # Auto-populate expected_assets from location if empty
        expected_assets_data = []
        if not audit.expected_assets and audit.location:
            # Get assets from the location
            location_assets = frappe.get_all(
                "Asset",
                filters={
                    "location": audit.location,
                    "status": ["not in", ["Scrapped", "Sold"]]
                },
                fields=["name", "asset_name", "item_code"]
            )
            # Build expected assets list
            expected_assets_data = [
                {
                    "asset": asset.name,
                    "asset_name": asset.asset_name or asset.name,
                    "item_code": asset.item_code,
                    "rfid_tag": None,
                    "status": "Expected"
                }
                for asset in location_assets
            ]
            # Update audit totals
            audit.total_expected = len(location_assets)
            audit.total_missing = len(location_assets)
            audit.save(ignore_permissions=True)
            frappe.db.commit()
        else:
            # Use existing expected assets
            expected_assets_data = [
                {
                    "asset": item.asset,
                    "asset_name": item.asset_name,
                    "item_code": item.item_code,
                    "rfid_tag": item.rfid_tag,
                    "status": item.status,
                    "condition": getattr(item, "condition", None),
                    "notes": getattr(item, "notes", None),
                    "photos": getattr(item, "photos", None),
                    "gps_location": getattr(item, "gps_location", None),
                }
                for item in audit.expected_assets
            ]

        return {
            "success": True,
            "audit": {
                "name": audit.name,
                "location": audit.location,
                "categories": [cat.category for cat in getattr(audit, "categories", [])],
                "audit_date": audit.audit_date,
                "audit_time": audit.audit_time,
                "assigned_to": getattr(audit, "assigned_to", None),
                "status": getattr(audit, "status", None),
                "audit_result": audit.audit_result,
                "notes": audit.notes,
                "assignee_comment": getattr(audit, "assignee_comment", None),
                "completed_on": getattr(audit, "completed_on", None),
                "completed_by": getattr(audit, "completed_by", None),
                "audited_by": getattr(audit, "audited_by", None),
                "device_info": getattr(audit, "device_info", None),
                "total_expected": audit.total_expected,
                "total_detected": audit.total_detected,
                "total_missing": audit.total_missing,
                "total_unidentified": audit.total_unidentified,
                "expected_assets": expected_assets_data,
                "detected_assets": [
                    {
                        "asset": item.asset,
                        "asset_name": item.asset_name,
                        "item_code": item.item_code,
                        "rfid_tag": item.rfid_tag,
                        "status": item.status,
                        "detection_time": item.detection_time,
                        "scan_count": item.scan_count,
                        "condition": getattr(item, "condition", None),
                        "notes": getattr(item, "notes", None),
                        "photos": getattr(item, "photos", None),
                        "gps_location": getattr(item, "gps_location", None),
                    }
                    for item in audit.detected_assets
                ],
                "missing_assets": [
                    {
                        "asset": item.asset,
                        "asset_name": item.asset_name,
                        "item_code": item.item_code,
                        "rfid_tag": item.rfid_tag,
                        "status": item.status,
                        "condition": getattr(item, "condition", None),
                        "notes": getattr(item, "notes", None),
                        "photos": getattr(item, "photos", None),
                        "gps_location": getattr(item, "gps_location", None),
                    }
                    for item in audit.missing_assets
                ],
                "unidentified_tags": [
                    {
                        "rfid_tag": item.rfid_tag,
                        "detection_time": item.detection_time,
                        "scan_count": item.scan_count,
                        "notes": item.notes,
                    }
                    for item in audit.unidentified_tags
                ],
            },
        }
    except Exception as e:
        frappe.log_error(f"Asset Audit get_my_asset_audit_detail error: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist(allow_guest=False)
def submit_asset_audit():
    """Submit/update an existing assigned audit.

    POST body:
    {
      "audit_id": "AUDIT-...",
      "assignee_comment": "...",
      "detected_assets": [...],
      "missing_assets": [...],
      "unidentified_tags": [...],
      "images": [{"filename": "a.jpg", "content_type": "image/jpeg", "base64": "..."}]
    }
    """
    try:
        user = frappe.session.user
        data = frappe.request.json or {}
        audit_id = data.get("audit_id")
        if not audit_id:
            frappe.throw(_("Audit ID is required"))

        audit = frappe.get_doc("Asset Audit", audit_id)
        _assert_user_can_access_audit(audit, user)

        # If audit has status field, move it to In Progress (if not completed yet)
        if getattr(audit, "status", None) in (None, "Pending"):
            try:
                audit.status = "In Progress"
            except Exception:
                pass

        # Optional comment
        if hasattr(audit, "assignee_comment"):
            audit.assignee_comment = data.get("assignee_comment")

        # Replace result tables (single source of truth)
        audit.set("detected_assets", [])
        audit.set("missing_assets", [])
        audit.set("unidentified_tags", [])

        for asset_data in data.get("detected_assets", []) or []:
            audit.append(
                "detected_assets",
                {
                    "asset": asset_data.get("asset"),
                    "asset_name": asset_data.get("asset_name"),
                    "item_code": asset_data.get("item_code"),
                    "rfid_tag": asset_data.get("rfid_tag"),
                    "status": "Detected",
                    "detection_time": _decode_iso_datetime(
                        asset_data.get("detection_time")
                    ),
                    "scan_count": asset_data.get("scan_count", 1),
                    "rssi": asset_data.get("rssi"),
                    "condition": asset_data.get("condition"),
                    "notes": asset_data.get("notes"),
                    "photos": asset_data.get("photos"),
                    "gps_location": asset_data.get("gps_location"),
                },
            )

        for asset_data in data.get("missing_assets", []) or []:
            audit.append(
                "missing_assets",
                {
                    "asset": asset_data.get("asset"),
                    "asset_name": asset_data.get("asset_name"),
                    "item_code": asset_data.get("item_code"),
                    "rfid_tag": asset_data.get("rfid_tag"),
                    "status": "Missing",
                    "condition": asset_data.get("condition"),
                    "notes": asset_data.get("notes"),
                    "photos": asset_data.get("photos"),
                    "gps_location": asset_data.get("gps_location"),
                },
            )

        for tag_data in data.get("unidentified_tags", []) or []:
            audit.append(
                "unidentified_tags",
                {
                    "rfid_tag": tag_data.get("rfid_tag"),
                    "detection_time": _decode_iso_datetime(
                        tag_data.get("detection_time")
                    ),
                    "scan_count": tag_data.get("scan_count", 1),
                    "rssi": tag_data.get("rssi"),
                    "notes": tag_data.get("notes"),
                },
            )

        # Update totals
        expected_count = len(audit.expected_assets or [])
        detected_count = len(audit.detected_assets or [])
        missing_count = len(audit.missing_assets or [])
        unidentified_count = len(audit.unidentified_tags or [])

        audit.total_expected = expected_count
        audit.total_detected = detected_count
        audit.total_missing = missing_count
        audit.total_unidentified = unidentified_count

        # Determine result
        if missing_count == 0 and unidentified_count == 0 and expected_count > 0:
            audit.audit_result = "Complete"
        elif detected_count > 0:
            audit.audit_result = "Partial"
        else:
            audit.audit_result = "Failed"

        # Mark completed
        if hasattr(audit, "status"):
            audit.status = "Completed"
        if hasattr(audit, "completed_on"):
            audit.completed_on = frappe.utils.now()
        if hasattr(audit, "completed_by"):
            audit.completed_by = user

        audit.save(ignore_permissions=True)

        # Attach images
        attached_files = []
        for img in data.get("images", []) or []:
            file_doc = _attach_base64_file(
                doctype="Asset Audit",
                docname=audit.name,
                filename=img.get("filename") or "image.jpg",
                base64_content=img.get("base64"),
                content_type=img.get("content_type"),
                is_private=int(img.get("is_private", 0) or 0),
            )
            attached_files.append({"file_url": file_doc.file_url, "name": file_doc.name})

        frappe.db.commit()

        return {
            "success": True,
            "audit_id": audit.name,
            "status": getattr(audit, "status", None),
            "audit_result": audit.audit_result,
            "files": attached_files,
        }
    except Exception as e:
        frappe.log_error(f"Asset Audit submit_asset_audit error: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist(allow_guest=False)
def get_asset_audits():
    """
    Get list of asset audits for mobile app history view.
    GET /api/method/erpnext.assets.api.get_asset_audits
    
    Query params:
    - location (optional): Filter by location
    - limit (optional): Number of records (default 50)
    """
    try:
        filters = {}
        location = frappe.request.args.get('location')
        if location:
            filters['location'] = location
        
        limit = int(frappe.request.args.get('limit', 50))
        
        audits = frappe.get_list(
            'Asset Audit',
            filters=filters,
            fields=['name', 'location', 'categories', 'audit_date', 'assigned_to', 'audit_time',
                   'completed_by', 'audited_by', 'completed_on', 'device_info', 'assignee_comment',
                   'status', 'audit_result', 'total_expected', 'total_detected', 'total_missing',
                   'total_unidentified', 'notes', 'creation'],
            order_by='creation desc',
            limit=limit
        )
        
        return {
            'success': True,
            'audits': audits
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist(allow_guest=False)
def get_asset_audit_detail(audit_id):
    """
    Get full details of a specific audit.
    GET /api/method/erpnext.assets.api.get_asset_audit_detail?audit_id=AUDIT-001
    """
    try:
        if not audit_id:
            frappe.throw(_('Audit ID is required'))
        
        audit = frappe.get_doc('Asset Audit', audit_id)
        
        return {
            'success': True,
            'audit': {
                'name': audit.name,
                'location': audit.location,
                'categories': [cat.category for cat in getattr(audit, "categories", [])],
                'audit_date': audit.audit_date,
                'assigned_to': getattr(audit, "assigned_to", None),
                'audit_time': audit.audit_time,
                'completed_by': getattr(audit, "completed_by", None),
                'audited_by': audit.audited_by,
                'completed_on': getattr(audit, "completed_on", None),
                'device_info': audit.device_info,
                'assignee_comment': getattr(audit, "assignee_comment", None),
                'status': getattr(audit, "status", None),
                'total_expected': audit.total_expected,
                'total_detected': audit.total_detected,
                'total_missing': audit.total_missing,
                'total_unidentified': audit.total_unidentified,
                'audit_result': audit.audit_result,
                'notes': audit.notes,
                'expected_assets': [{
                    'asset': item.asset,
                    'asset_name': item.asset_name,
                    'item_code': item.item_code,
                    'rfid_tag': item.rfid_tag,
                    'status': item.status
                } for item in audit.expected_assets],
                'detected_assets': [{
                    'asset': item.asset,
                    'asset_name': item.asset_name,
                    'item_code': item.item_code,
                    'rfid_tag': item.rfid_tag,
                    'status': item.status,
                    'detection_time': item.detection_time,
                    'scan_count': item.scan_count,
                    'condition': getattr(item, "condition", None),
                    'notes': getattr(item, "notes", None),
                    'photos': getattr(item, "photos", None),
                    'gps_location': getattr(item, "gps_location", None),
                } for item in audit.detected_assets],
                'missing_assets': [{
                    'asset': item.asset,
                    'asset_name': item.asset_name,
                    'item_code': item.item_code,
                    'rfid_tag': item.rfid_tag,
                    'status': item.status,
                    'condition': getattr(item, "condition", None),
                    'notes': getattr(item, "notes", None),
                    'photos': getattr(item, "photos", None),
                    'gps_location': getattr(item, "gps_location", None),
                } for item in audit.missing_assets],
                'unidentified_tags': [{
                    'rfid_tag': item.rfid_tag,
                    'detection_time': item.detection_time,
                    'scan_count': item.scan_count,
                    'notes': item.notes
                } for item in audit.unidentified_tags]
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist(allow_guest=False)
def get_assets_by_location():
    """
    Get all assets in a specific location with their RFID tags.
    GET /api/method/erpnext.assets.api.get_assets_by_location?location=Store
    """
    try:
        location = frappe.request.args.get('location')
        if not location:
            frappe.throw(_('Location is required'))
        
        # Get assets in this location that are not scrapped/sold
        assets = frappe.get_list(
            'Asset',
            filters={
                'location': location,
                'status': ['not in', ['Scrapped', 'Sold']]
            },
            fields=['name', 'asset_name', 'item_code'],
            limit=1000
        )
        
        return {
            'success': True,
            'location': location,
            'assets': assets,
            'count': len(assets)
        }
        
    except Exception as e:
        frappe.log_error(f"Asset Audit get_assets_by_location error: {str(e)}")
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist(allow_guest=False)
def auto_populate_expected_assets(audit_id=None):
    """
    Auto-populate expected_assets for an audit from its location.
    Call this when viewing an audit in the list to ensure data is populated.
    
    GET /api/method/erpnext.assets.api.auto_populate_expected_assets?audit_id=AUDIT-001
    """
    try:
        if not audit_id:
            # If no audit_id, process all audits with empty expected_assets
            audits = frappe.get_all("Asset Audit", filters={"total_expected": 0}, fields=["name"])
            fixed = 0
            for audit_info in audits:
                result = _populate_audit_assets(audit_info.name)
                if result.get("success"):
                    fixed += 1
            return {"success": True, "fixed": fixed, "message": f"Populated {fixed} audits"}
        else:
            # Populate specific audit
            result = _populate_audit_assets(audit_id)
            return result
            
    except Exception as e:
        frappe.log_error(f"Asset Audit auto_populate error: {str(e)}")
        return {"success": False, "message": str(e)}


def _populate_audit_assets(audit_name):
    """Helper to populate expected assets for a single audit"""
    audit = frappe.get_doc("Asset Audit", audit_name)
    
    # Skip if already has expected assets
    if audit.expected_assets:
        return {"success": False, "message": "Already populated", "audit_id": audit_name}
    
    if not audit.location:
        return {"success": False, "message": "No location set", "audit_id": audit_name}
    
    # Get assets from the location
    assets = frappe.get_all(
        "Asset",
        filters={
            "location": audit.location,
            "status": ["not in", ["Scrapped", "Sold"]]
        },
        fields=["name", "asset_name", "item_code"]
    )
    
    if not assets:
        return {"success": False, "message": "No assets found in location", "audit_id": audit_name}
    
    # Add assets to expected_assets
    for asset in assets:
        audit.append("expected_assets", {
            "asset": asset.name,
            "asset_name": asset.asset_name or asset.name,
            "item_code": asset.item_code,
            "status": "Expected"
        })
    
    # Update totals
    audit.total_expected = len(assets)
    audit.total_missing = len(assets)
    audit.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {
        "success": True, 
        "audit_id": audit_name, 
        "count": len(assets),
        "location": audit.location
    }


@frappe.whitelist(allow_guest=False)
def whoami():
    """Debug: Returns current session user info."""
    return {
        "user": frappe.session.user,
        "roles": frappe.get_roles(),
        "is_admin": _is_admin_user(frappe.session.user),
    }

