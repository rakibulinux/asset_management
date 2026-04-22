# Test script for Asset Audit expected_assets population
import frappe

# Create test audit
audit = frappe.new_doc("Asset Audit")
audit.location = "Meeting Room"  # replace with actual Location name
audit.category = "IT Assets"  # replace with actual Asset Category name
audit.audit_date = frappe.utils.today()
audit.audit_time = frappe.utils.nowtime()
audit.save()

print(f"Audit created: {audit.name}")
print(f"Expected assets count: {audit.total_expected}")
print(f"Expected assets items: {len(audit.expected_assets)}")
for item in audit.expected_assets:
    print(f"  - {item.asset_name} ({item.asset})")
