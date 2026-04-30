from typing import Any

import frappe
from frappe import _
from frappe.utils.dashboard import cache_source


@frappe.whitelist()
@cache_source
def get(
    chart_name: str | None = None,
    chart: Any = None,
    no_cache: Any = None,
    filters: dict | str | None = None,
    from_date: Any = None,
    to_date: Any = None,
    timespan: Any = None,
    time_interval: Any = None,
    heatmap_year: Any = None,
):
    rows = frappe.db.sql("""
        SELECT
            COALESCE(asset_category, 'Not Set') AS asset_category,
            COUNT(name) AS asset_count
        FROM `tabAsset`
        GROUP BY asset_category
        ORDER BY asset_count DESC
    """, as_dict=True)

    return {
        "labels": [row.asset_category for row in rows],
        "datasets": [
            {
                "name": _("Assets"),
                "values": [row.asset_count for row in rows],
            }
        ],
    }
