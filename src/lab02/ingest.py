import csv
from pathlib import Path
from src.lab02.db import get_connection

DATA_SOURCES = [
    {
        "table": "stg.customers",
        "file": Path("data/raw/base_v1/customers.csv"),
        "expected_cols": [
            "customer_id", "full_name", "email", "phone", "city", 
            "service_zone_id", "registered_at", "customer_status"
        ],
    },
    {
        "table": "stg.merchants",
        "file": Path("data/raw/base_v1/merchants.csv"),
        "expected_cols": [
            "merchant_id", "merchant_name", "merchant_type", "city", 
            "service_zone_id", "opened_at", "merchant_status"
        ],
    },
    {
        "table": "stg.products",
        "file": Path("data/raw/base_v1/products.csv"),
        "expected_cols": [
            "product_id", "merchant_id", "product_name", "category", 
            "unit_price_uah", "is_active", "updated_at"
        ],
    },
    {
        "table": "stg.orders",
        "file": Path("data/raw/base_v1/orders.csv"),
        "expected_cols": [
            "order_id", "customer_id", "merchant_id", "created_at", 
            "order_status", "currency", "subtotal_amount", "delivery_fee", 
            "discount_amount", "total_amount"
        ],
    },
    {
        "table": "stg.order_items",
        "file": Path("data/raw/lab02_relational/order_items.csv"),
        "expected_cols": [
            "order_item_id", "order_id", "product_id", "quantity", 
            "unit_price", "line_discount", "line_total", "currency"
        ],
    },
]

def load_staging(batch_id: str = "S08-V1") -> dict[str, int]:
    row_counts = {}

    with get_connection() as conn:
        with conn.cursor() as cur:
            for src in DATA_SOURCES:
                file_path = src["file"]
                table_name = src["table"]
                expected_cols = src["expected_cols"]

                if not file_path.exists():
                    raise FileNotFoundError(f"Файл {file_path} відсутній!")

                cur.execute(f"TRUNCATE TABLE {table_name};")

                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)

                    if header != expected_cols:
                        raise ValueError(
                            f"Порушення схеми CSV у {file_path.name}. "
                            f"Очікувалось: {expected_cols}, отримано: {header}"
                        )

                    insert_cols = expected_cols + ["batch_id", "source_file", "source_row_number"]
                    cols_str = ", ".join(insert_cols)
                    copy_sql = f"COPY {table_name} ({cols_str}) FROM STDIN"

                    row_count = 0
                    with cur.copy(copy_sql) as copy:
                        for row_idx, row in enumerate(reader, start=1):
                            if len(row) != len(expected_cols):
                                raise ValueError(f"Пошкоджений рядок {row_idx} у {file_path.name}")
                            payload = row + [batch_id, file_path.name, str(row_idx)]
                            copy.write_row(payload)
                            row_count += 1

                row_counts[file_path.name] = row_count
                print(f"[STAGING COPY] {file_path.name:18} -> {table_name:17}: {row_count} рядків.")

        conn.commit()
    return row_counts

if __name__ == "__main__":
    load_staging()
