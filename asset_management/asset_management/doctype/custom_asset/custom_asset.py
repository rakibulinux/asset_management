import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, now_datetime


class CustomAsset(Document):
    def autoname(self):
        if self.asset_code:
            self.asset_code = self.asset_code
        else:
            self.asset_code = make_autoname("AST-.#####")
            # self.asset_code = self.name

    def before_insert(self):
        current_dt = now_datetime()
        self.created_date = self.created_date or current_dt
        self.created_by_user = self.created_by_user or frappe.session.user
        self.modified_date = current_dt
        self.modified_by_user = frappe.session.user

    def validate(self):
        self.sync_audit_fields()
        self.validate_partner()
        self.validate_self_links()
        self.validate_date_ranges()
        self.validate_amounts()

    def sync_audit_fields(self):
        if not self.created_date:
            self.created_date = self.creation or now_datetime()

        if not self.created_by_user:
            self.created_by_user = self.owner or frappe.session.user

        self.modified_date = now_datetime()
        self.modified_by_user = frappe.session.user

        if not self.partner_owned:
            self.partner = None

    def validate_partner(self):
        if self.partner_owned and not self.partner:
            frappe.throw(_("Partner is required when the asset is partner owned."))

    def validate_self_links(self):
        if self.name and self.linked_asset and self.linked_asset == self.name:
            frappe.throw(_("Linked Asset cannot be the same as this document."))

    def validate_date_ranges(self):
        self.validate_date_pair("insurance_start_date", "insurance_end_date", "Insurance")
        self.validate_date_pair("amc_start_date", "amc_end_date", "AMC")
        self.validate_date_pair("warranty_start_date", "warranty_end_date", "Warranty")

        if self.purchase_date and self.capitalization_date:
            if getdate(self.capitalization_date) < getdate(self.purchase_date):
                frappe.throw(_("Capitalization Date cannot be before Purchase Date."))

    def validate_date_pair(self, start_field, end_field, label):
        start_date = self.get(start_field)
        end_date = self.get(end_field)

        if start_date and end_date and getdate(end_date) < getdate(start_date):
            frappe.throw(_("{0} End Date cannot be before {0} Start Date.").format(label))

    def validate_amounts(self):
        currency_fields = {
            "Purchase Price": "purchase_price",
            "Capitalization Price": "capitalization_price",
            "Scrap Value": "scrap_value",
            "Accumulated Depreciation": "accumulated_depreciation",
        }

        percent_fields = {
            "Depreciation%": "depreciation_percentage",
            "Income Tax Depreciation%": "income_tax_depreciation_percentage",
        }

        for label, fieldname in currency_fields.items():
            if flt(self.get(fieldname)) < 0:
                frappe.throw(_("{0} cannot be negative.").format(label))

        for label, fieldname in percent_fields.items():
            value = flt(self.get(fieldname))
            if value < 0 or value > 100:
                frappe.throw(_("{0} must be between 0 and 100.").format(label))