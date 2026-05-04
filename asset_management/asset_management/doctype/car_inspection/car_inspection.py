import frappe
from frappe.model.document import Document


DEFAULT_EQUIPMENTS = [
	("First Aid Kit",           "حقيبة الإسعافات الأولية"),
	("Fire Extinguisher",       "طفاية الحريق"),
	("Warning Triangle",        "مثلث التحذير"),
	("Tyre and Spare Tyres",    "الإطار والإطار الاحتياطي"),
	("Jack",                    "الرافعة"),
	("Steering Wheel",          "عجلة القيادة"),
]

DEFAULT_ENGINE = [
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

DEFAULT_INTERIOR = [
	("Car Registration and Insurance", "تسجيل المركبة والتأمين"),
	("Lights",                         "الأضواء"),
	("Seats",                          "المقاعد"),
	("Seat Belt",                      "حزام الأمان"),
	("Radio",                          "الراديو"),
	("Driver Safety Equipment",        "معدات سلامة السائق"),
	("Interior Cleanliness",           "نظافة المقصورة الداخلية"),
]

DEFAULT_EXTERIOR = [
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


class CarInspection(Document):
	def after_insert(self):
		self._create_default_items()

	def _create_default_items(self):
		_bulk_insert("Equipments",         self.name, DEFAULT_EQUIPMENTS,  include_rfid=True)
		_bulk_insert("Engine Inspection",  self.name, DEFAULT_ENGINE)
		_bulk_insert("Interior Inspection",self.name, DEFAULT_INTERIOR)
		_bulk_insert("Exterior Inspection",self.name, DEFAULT_EXTERIOR)


def _bulk_insert(doctype, car_inspection, items, include_rfid=False):
	for name_en, name_ar in items:
		doc = frappe.new_doc(doctype)
		doc.car_inspection   = car_inspection
		doc.name_english     = name_en
		doc.name_arabic      = name_ar
		if include_rfid:
			doc.rfid_detected = 0
		doc.insert(ignore_permissions=True)
