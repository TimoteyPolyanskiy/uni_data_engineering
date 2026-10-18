import psycopg
from src.lab02.db import get_connection
from src.lab02.ingest import load_staging


def run_pipeline(batch_id: str = "S08-V1") -> int:
    """Виконує транзакційну валідацію, карантин та публікацію в core."""

    # 1. Завантаження CSV у stg.* без втрат
    load_staging(batch_id)

    # 2. Реєстрація спроби RUNNING в окремій транзакції
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit.pipeline_runs (batch_id, status)
                VALUES (%s, 'RUNNING')
                RETURNING run_id;
                """,
                (batch_id,),
            )
            run_id = cur.fetchone()[0]
        conn.commit()

    print(f"\n[PIPELINE] Розпочато запуск RUN_ID={run_id} (Batch: {batch_id})")

    try:
        # 3. Транзакційний блок публікації
        with get_connection() as conn:
            with conn.cursor() as cur:

                # -------------------------------------------------------------
                # 3.1 CUSTOMERS
                # -------------------------------------------------------------
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY customer_id, full_name, email, phone, city,
                                         service_zone_id, registered_at, customer_status
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.customers
                    )
                    INSERT INTO audit.rejected_rows (
                        run_id, batch_id, source_file, source_row_number,
                        entity_key, raw_payload, reason_code
                    )
                    SELECT %s, batch_id, source_file, source_row_number, customer_id,
                           to_jsonb(sub), 'FULL_DUPLICATE'
                    FROM ranked sub WHERE rn > 1;
                    """,
                    (run_id,),
                )

                cur.execute("TRUNCATE TABLE core.customers CASCADE;")
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY customer_id, full_name, email, phone, city,
                                         service_zone_id, registered_at, customer_status
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.customers
                    )
                    INSERT INTO core.customers (customer_id, full_name, city, registered_at)
                    SELECT customer_id, full_name, city, registered_at::timestamptz
                    FROM ranked
                    WHERE rn = 1;
                    """
                )

                # -------------------------------------------------------------
                # 3.2 MERCHANTS
                # -------------------------------------------------------------
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY merchant_id, merchant_name, merchant_type, city,
                                         service_zone_id, opened_at, merchant_status
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.merchants
                    )
                    INSERT INTO audit.rejected_rows (
                        run_id, batch_id, source_file, source_row_number,
                        entity_key, raw_payload, reason_code
                    )
                    SELECT %s, batch_id, source_file, source_row_number, merchant_id,
                           to_jsonb(sub), 'FULL_DUPLICATE'
                    FROM ranked sub WHERE rn > 1;
                    """,
                    (run_id,),
                )

                cur.execute("TRUNCATE TABLE core.merchants CASCADE;")
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY merchant_id, merchant_name, merchant_type, city,
                                         service_zone_id, opened_at, merchant_status
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.merchants
                    )
                    INSERT INTO core.merchants (merchant_id, merchant_name, city, opened_at)
                    SELECT merchant_id, merchant_name, city, opened_at::timestamptz
                    FROM ranked
                    WHERE rn = 1;
                    """
                )

                # -------------------------------------------------------------
                # 3.3 PRODUCTS
                # -------------------------------------------------------------
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY product_id, merchant_id, product_name, category,
                                         unit_price_uah, is_active, updated_at
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.products
                    )
                    INSERT INTO audit.rejected_rows (
                        run_id, batch_id, source_file, source_row_number,
                        entity_key, raw_payload, reason_code
                    )
                    SELECT %s, batch_id, source_file, source_row_number, product_id,
                           to_jsonb(sub), 'FULL_DUPLICATE'
                    FROM ranked sub WHERE rn > 1;
                    """,
                    (run_id,),
                )

                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY product_id, merchant_id, product_name, category,
                                         unit_price_uah, is_active, updated_at
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.products
                    )
                    INSERT INTO audit.rejected_rows (
                        run_id, batch_id, source_file, source_row_number,
                        entity_key, raw_payload, reason_code
                    )
                    SELECT %s, batch_id, source_file, source_row_number, product_id,
                           to_jsonb(sub),
                           CASE 
                               WHEN unit_price_uah::numeric <= 0 THEN 'INVALID_PRICE'
                               WHEN merchant_id NOT IN (SELECT merchant_id FROM core.merchants) THEN 'ORPHAN_MERCHANT_FK'
                           END
                    FROM ranked sub
                    WHERE rn = 1 
                      AND (unit_price_uah::numeric <= 0 
                           OR merchant_id NOT IN (SELECT merchant_id FROM core.merchants));
                    """,
                    (run_id,),
                )

                cur.execute("TRUNCATE TABLE core.products CASCADE;")
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY product_id, merchant_id, product_name, category,
                                         unit_price_uah, is_active, updated_at
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.products
                    )
                    INSERT INTO core.products (product_id, merchant_id, product_name, unit_price_uah, is_active)
                    SELECT product_id, merchant_id, product_name,
                           unit_price_uah::numeric(12, 2), is_active::boolean
                    FROM ranked
                    WHERE rn = 1 
                      AND unit_price_uah::numeric > 0
                      AND merchant_id IN (SELECT merchant_id FROM core.merchants);
                    """
                )

                # -------------------------------------------------------------
                # 3.4 ORDERS
                # -------------------------------------------------------------
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY order_id, customer_id, merchant_id, created_at,
                                         order_status, currency, subtotal_amount, delivery_fee,
                                         discount_amount, total_amount
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.orders
                    )
                    INSERT INTO audit.rejected_rows (
                        run_id, batch_id, source_file, source_row_number,
                        entity_key, raw_payload, reason_code
                    )
                    SELECT %s, batch_id, source_file, source_row_number, order_id,
                           to_jsonb(sub), 'FULL_DUPLICATE'
                    FROM ranked sub WHERE rn > 1;
                    """,
                    (run_id,),
                )

                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY order_id, customer_id, merchant_id, created_at,
                                         order_status, currency, subtotal_amount, delivery_fee,
                                         discount_amount, total_amount
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.orders
                    )
                    INSERT INTO audit.rejected_rows (
                        run_id, batch_id, source_file, source_row_number,
                        entity_key, raw_payload, reason_code
                    )
                    SELECT %s, batch_id, source_file, source_row_number, order_id,
                           to_jsonb(sub),
                           CASE 
                               WHEN stg.try_cast_timestamptz(created_at) IS NULL THEN 'INVALID_DATE'
                               WHEN customer_id NOT IN (SELECT customer_id FROM core.customers) THEN 'ORPHAN_CUSTOMER_FK'
                               WHEN merchant_id NOT IN (SELECT merchant_id FROM core.merchants) THEN 'ORPHAN_MERCHANT_FK'
                           END
                    FROM ranked sub
                    WHERE rn = 1 
                      AND (stg.try_cast_timestamptz(created_at) IS NULL
                           OR customer_id NOT IN (SELECT customer_id FROM core.customers)
                           OR merchant_id NOT IN (SELECT merchant_id FROM core.merchants));
                    """,
                    (run_id,),
                )

                cur.execute("TRUNCATE TABLE core.orders CASCADE;")
                cur.execute(
                    """
                    WITH ranked AS (
                        SELECT *, ROW_NUMBER() OVER(
                            PARTITION BY order_id, customer_id, merchant_id, created_at,
                                         order_status, currency, subtotal_amount, delivery_fee,
                                         discount_amount, total_amount
                            ORDER BY source_row_number
                        ) AS rn
                        FROM stg.orders
                    )
                    INSERT INTO core.orders (
                        order_id, customer_id, merchant_id, created_at,
                        order_status, currency, subtotal_amount, delivery_fee,
                        discount_amount, total_amount
                    )
                    SELECT order_id, customer_id, merchant_id,
                           stg.try_cast_timestamptz(created_at), order_status,
                           REPLACE(currency, ' ', ''),
                           subtotal_amount::numeric(12, 2),
                           delivery_fee::numeric(12, 2),
                           discount_amount::numeric(12, 2),
                           total_amount::numeric(12, 2)
                    FROM ranked
                    WHERE rn = 1
                      AND stg.try_cast_timestamptz(created_at) IS NOT NULL
                      AND customer_id IN (SELECT customer_id FROM core.customers)
                      AND merchant_id IN (SELECT merchant_id FROM core.merchants);
                    """
                )

                # -------------------------------------------------------------
                # 3.5 ORDER_ITEMS
                # -------------------------------------------------------------
                cur.execute(
                    """
                    INSERT INTO audit.rejected_rows (
                        run_id, batch_id, source_file, source_row_number,
                        entity_key, raw_payload, reason_code
                    )
                    SELECT %s, batch_id, source_file, source_row_number, order_item_id,
                           to_jsonb(oi), 'PARENT_REJECTED'
                    FROM stg.order_items oi
                    WHERE order_id NOT IN (SELECT order_id FROM core.orders)
                       OR product_id NOT IN (SELECT product_id FROM core.products);
                    """,
                    (run_id,),
                )

                cur.execute("TRUNCATE TABLE core.order_items CASCADE;")
                cur.execute(
                    """
                    INSERT INTO core.order_items (
                        order_item_id, order_id, product_id, quantity,
                        unit_price, line_discount, line_total, currency
                    )
                    SELECT order_item_id, order_id, product_id,
                           quantity::integer,
                           unit_price::numeric(12, 2),
                           line_discount::numeric(12, 2),
                           line_total::numeric(12, 2),
                           currency
                    FROM stg.order_items
                    WHERE order_id IN (SELECT order_id FROM core.orders)
                      AND product_id IN (SELECT product_id FROM core.products);
                    """
                )

                # -------------------------------------------------------------
                # 3.6 RECONCILIATION
                # -------------------------------------------------------------
                files = [
                    ("customers.csv", "stg.customers", "core.customers"),
                    ("merchants.csv", "stg.merchants", "core.merchants"),
                    ("products.csv", "stg.products", "core.products"),
                    ("orders.csv", "stg.orders", "core.orders"),
                    ("order_items.csv", "stg.order_items", "core.order_items"),
                ]

                print("\n=== Результати звірки файлового балансу ===")
                for fname, stg_t, core_t in files:
                    cur.execute(f"SELECT COUNT(*) FROM {stg_t};")
                    inp = cur.fetchone()[0]

                    cur.execute(f"SELECT COUNT(*) FROM {core_t};")
                    acc = cur.fetchone()[0]

                    cur.execute(
                        """
                        SELECT COUNT(*) FROM audit.rejected_rows
                        WHERE run_id = %s AND source_file = %s AND reason_code = 'FULL_DUPLICATE';
                        """,
                        (run_id, fname),
                    )
                    dups = cur.fetchone()[0]

                    cur.execute(
                        """
                        SELECT COUNT(*) FROM audit.rejected_rows
                        WHERE run_id = %s AND source_file = %s AND reason_code != 'FULL_DUPLICATE';
                        """,
                        (run_id, fname),
                    )
                    rejs = cur.fetchone()[0]

                    if inp != (dups + rejs + acc):
                        raise ValueError(
                            f"Порушення балансу для {fname}: "
                            f"input({inp}) != dups({dups}) + rejs({rejs}) + acc({acc})"
                        )

                    cur.execute(
                        """
                        INSERT INTO audit.run_file_stats (
                            run_id, source_file, input_count,
                            duplicate_count, rejected_count, accepted_count
                        )
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (run_id, fname, inp, dups, rejs, acc),
                    )
                    print(
                        f"  {fname:18}: input={inp} | dups={dups} | rejs={rejs} | acc={acc} (OK)"
                    )

                cur.execute(
                    """
                    UPDATE audit.pipeline_runs
                    SET finished_at = clock_timestamp(), status = 'SUCCESS'
                    WHERE run_id = %s;
                    """,
                    (run_id,),
                )

            conn.commit()

        print(f"[PIPELINE] Успішно зафіксовано RUN_ID={run_id}\n")
        return run_id

    except Exception as e:
        print(f"\n[PIPELINE ERROR] Збій під час RUN_ID={run_id}: {e}")
        with get_connection() as err_conn:
            with err_conn.cursor() as err_cur:
                err_cur.execute(
                    """
                    UPDATE audit.pipeline_runs
                    SET finished_at = clock_timestamp(),
                        status = 'FAILED',
                        error_message = %s
                    WHERE run_id = %s;
                    """,
                    (str(e), run_id),
                )
            err_conn.commit()
        raise e


if __name__ == "__main__":
    run_pipeline()
