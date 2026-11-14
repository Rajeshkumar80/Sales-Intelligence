import csv
import io

import pytest

from app.csv_import import parse_csv
from app.schemas import TransactionIn, to_utc

HEADER = "transaction_id,product_id,product_name,category,quantity,unit_price,region,timestamp\n"


def test_valid_csv_parses_and_normalises_timestamp():
    raw = (HEADER + "T1,P-1001,Wireless Keyboard,Electronics,2,42.50,North,2026-01-01T00:00:00Z\n").encode()
    result = parse_csv(raw)
    assert not result["errors"]
    doc = result["rows"][0]
    assert doc["quantity"] == 2 and doc["unit_price"] == 42.5
    assert doc["revenue"] == 85.0
    assert doc["timestamp"].isoformat().startswith("2026-01-01T00:00:00")
    assert doc["source"] == "csv" and doc["processed"] is False


def test_bom_and_quoted_fields_are_handled():
    raw = ("\ufeff" + HEADER + 'T9,P-2003,"Bookshelf, 5 Tier",Furniture,1,89.99,East,2026-01-02 10:30:00\n').encode()
    result = parse_csv(raw)
    assert not result["errors"]
    assert result["rows"][0]["product_name"] == "Bookshelf, 5 Tier"


def test_missing_column_rejected_with_clear_message():
    with pytest.raises(ValueError) as exc:
        parse_csv(b"transaction_id,product_id\nT1,P-1\n")
    assert "missing required columns" in str(exc.value)


def test_bad_rows_are_reported_not_raised():
    raw = (HEADER
           + "T1,P-1001,Keyboard,Electronics,0,42.50,North,2026-01-01T00:00:00Z\n"
           + "T2,P-1002,Hub,Electronics,abc,29.99,North,2026-01-01T00:00:00Z\n").encode()
    result = parse_csv(raw)
    assert result["rows"] == []
    assert [error["row"] for error in result["errors"]] == [2, 3]


def test_naive_timestamp_is_treated_as_utc():
    payload = TransactionIn(product_id="P-1", product_name="X", category="Tools", quantity=1,
                            unit_price=1.0, region="North", timestamp="2026-05-01T12:00:00")
    assert payload.timestamp.utcoffset().total_seconds() == 0


def test_csv_template_endpoint_matches_required_columns(client):
    response = client.get("/api/sales/transactions/template.csv")
    assert response.status_code == 200
    header = next(csv.reader(io.StringIO(response.text)))
    assert header == ["transaction_id", "product_id", "product_name", "category", "quantity",
                      "unit_price", "region", "timestamp"]
