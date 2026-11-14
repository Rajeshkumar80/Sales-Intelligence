"""Dashboard analytics read pre-aggregated Hive output from MongoDB (no Python row loops)."""

from datetime import datetime

from . import db


def _match(date_from: str | None, date_to: str | None, product_id: str | None,
           category: str | None, region: str | None) -> dict:
    match: dict = {}
    window: dict = {}
    if date_from:
        window["$gte"] = date_from
    if date_to:
        window["$lte"] = date_to
    if window:
        match["sale_date"] = window
    if product_id:
        match["product_id"] = product_id
    if category:
        match["category"] = category
    if region:
        match["region"] = region
    return match


def overview(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    product_id: str | None = None,
    category: str | None = None,
    region: str | None = None,
) -> dict:
    match = _match(date_from, date_to, product_id, category, region)
    facet = db.get_db()[db.FACT_DAILY].aggregate([
        {"$match": match},
        {"$facet": {
            "total": [{"$group": {
                "_id": None,
                "revenue": {"$sum": "$revenue"},
                "quantity": {"$sum": "$quantity"},
                "orders": {"$sum": "$orders"},
                "products": {"$addToSet": "$product_id"},
            }}],
            "daily": [
                {"$group": {"_id": "$sale_date", "revenue": {"$sum": "$revenue"},
                            "quantity": {"$sum": "$quantity"}, "orders": {"$sum": "$orders"}}},
                {"$sort": {"_id": 1}},
            ],
            "monthly": [
                {"$group": {"_id": {"$substrBytes": ["$sale_date", 0, 7]},
                            "revenue": {"$sum": "$revenue"}, "quantity": {"$sum": "$quantity"},
                            "orders": {"$sum": "$orders"}}},
                {"$sort": {"_id": 1}},
            ],
            "category": [
                {"$group": {"_id": "$category", "revenue": {"$sum": "$revenue"},
                            "quantity": {"$sum": "$quantity"}}},
                {"$sort": {"revenue": -1}},
            ],
            "region": [
                {"$group": {"_id": "$region", "revenue": {"$sum": "$revenue"},
                            "quantity": {"$sum": "$quantity"}, "orders": {"$sum": "$orders"}}},
                {"$sort": {"revenue": -1}},
            ],
            "products": [
                {"$group": {"_id": "$product_id", "product_name": {"$first": "$product_name"},
                            "revenue": {"$sum": "$revenue"}, "quantity": {"$sum": "$quantity"},
                            "orders": {"$sum": "$orders"}}},
                {"$sort": {"revenue": -1}},
            ],
        }},
    ])
    result = next(facet, {}) or {}
    total = (result.get("total") or [{}])[0]
    revenue = round(float(total.get("revenue", 0.0)), 2)
    orders = int(total.get("orders", 0))
    products = sorted(total.get("products") or [])
    return {
        "has_data": bool(orders),
        "filters": {"date_from": date_from, "date_to": date_to, "product_id": product_id,
                    "category": category, "region": region},
        "kpis": {
            "total_revenue": revenue,
            "total_transactions": orders,
            "total_products": len(products),
            "total_quantity": int(total.get("quantity", 0)),
            "average_order_value": round(revenue / orders, 2) if orders else 0.0,
        },
        "daily": [{"date": row["_id"], "revenue": round(row["revenue"], 2),
                   "quantity": int(row["quantity"]), "orders": int(row["orders"])}
                  for row in result.get("daily", [])],
        "monthly": [{"month": row["_id"], "revenue": round(row["revenue"], 2),
                     "quantity": int(row["quantity"]), "orders": int(row["orders"])}
                    for row in result.get("monthly", [])],
        "category": [{"category": row["_id"], "revenue": round(row["revenue"], 2),
                      "quantity": int(row["quantity"])} for row in result.get("category", [])],
        "region": [{"region": row["_id"], "revenue": round(row["revenue"], 2),
                    "quantity": int(row["quantity"]), "orders": int(row["orders"])}
                   for row in result.get("region", [])],
        "top_products": [{"product_id": row["_id"], "product_name": row["product_name"],
                          "revenue": round(row["revenue"], 2), "quantity": int(row["quantity"]),
                          "orders": int(row["orders"])} for row in (result.get("products") or [])[:10]],
        "all_products": [{"product_id": row["_id"], "product_name": row["product_name"],
                          "revenue": round(row["revenue"], 2), "quantity": int(row["quantity"]),
                          "orders": int(row["orders"])} for row in (result.get("products") or [])],
    }


def latest_snapshot() -> dict | None:
    doc = db.get_db()[db.SNAPSHOTS].find_one({}, sort=[("generated_at", -1)])
    if doc:
        doc["generated_at"] = doc["generated_at"].isoformat() if isinstance(doc["generated_at"], datetime) else doc["generated_at"]
    return doc


def mr_products(limit: int = 5000) -> dict:
    batch = db.get_db()[db.SNAPSHOTS].find_one({}, sort=[("generated_at", -1)])
    if not batch:
        return {"batch_id": None, "items": []}
    items = list(db.get_db()[db.MR_PRODUCT].find({"batch_id": batch["batch_id"]}, {"_id": 0})
                 .sort("revenue", -1).limit(limit))
    return {"batch_id": batch["batch_id"], "items": items}


def filter_options() -> dict:
    db_handle = db.get_db()
    regions = sorted(db_handle[db.FACT_DAILY].distinct("region"))
    categories = sorted(db_handle[db.FACT_DAILY].distinct("category"))
    products = sorted(
        db_handle[db.FACT_DAILY].aggregate([
            {"$group": {"_id": "$product_id", "product_name": {"$first": "$product_name"}}},
            {"$sort": {"_id": 1}},
        ]),
        key=lambda row: row["_id"],
    )
    return {
        "regions": regions,
        "categories": categories,
        "products": [{"product_id": row["_id"], "product_name": row["product_name"]} for row in products],
        "dates": sorted(db_handle[db.FACT_DAILY].distinct("sale_date")),
    }
