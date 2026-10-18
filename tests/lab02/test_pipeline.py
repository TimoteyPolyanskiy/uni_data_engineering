import psycopg
import pytest
from src.lab02.db import get_connection
from src.lab02.pipeline import run_pipeline


def get_core_metrics():
    """Повертає кількість рядків у core та контрольні суми замовлень за валютами."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            counts = {}
            for table in [
                "customers",
                "merchants",
                "products",
                "orders",
                "order_items",
            ]:
                cur.execute(f"SELECT count(*) FROM core.{table};")
                counts[table] = cur.fetchone()[0]

            cur.execute("""
                SELECT currency, sum(total_amount)::numeric(12,2)
                FROM core.orders
                GROUP BY currency ORDER BY currency;
            """)
            sums = dict(cur.fetchall())
            return counts, sums


def test_idempotency_rerun():
    """Завдання 8.1: Повторний запуск зберігає стан core, суми за валютами та створює новий SUCCESS run."""
    run_id_1 = run_pipeline("S08-V1")
    counts_1, sums_1 = get_core_metrics()

    run_id_2 = run_pipeline("S08-V1")
    counts_2, sums_2 = get_core_metrics()

    assert run_id_2 > run_id_1, "Повторний запуск повинен отримати новий run_id"
    assert (
        counts_1 == counts_2
    ), f"Кількість рядків у core змінилася: {counts_1} != {counts_2}"
    assert sums_1 == sums_2, f"Суми замовлень змінилися: {sums_1} != {sums_2}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM audit.pipeline_runs WHERE run_id = %s;",
                (run_id_2,),
            )
            assert cur.fetchone()[0] == "SUCCESS"


def test_controlled_failure_rollback(tmp_path, monkeypatch):
    """Завдання 8.2: Помилка CHECK(quantity > 0) викликає ROLLBACK core та фіксує статус FAILED."""
    from src.lab02 import ingest

    # Фіксуємо початковий стан core
    counts_before, _ = get_core_metrics()

    # Створюємо синтетичний fixture з дефектом: рядок із quantity = -1
    clean_items_path = ingest.DATA_SOURCES[4]["file"]
    corrupted_items_path = tmp_path / "corrupted_order_items.csv"

    with open(clean_items_path, "r", encoding="utf-8") as f_in:
        lines = f_in.readlines()

    # Підміняємо першу позицію товару на від'ємну кількість
    header = lines[0]
    sample_parts = lines[1].strip().split(",")
    sample_parts[3] = "-1"  # quantity = -1
    corrupted_line = ",".join(sample_parts) + "\n"

    with open(corrupted_items_path, "w", encoding="utf-8") as f_out:
        f_out.write(header)
        f_out.write(corrupted_line)

    # Підміняємо джерело в модулі ingest
    mock_sources = [dict(s) for s in ingest.DATA_SOURCES]
    mock_sources[4]["file"] = corrupted_items_path
    monkeypatch.setattr(ingest, "DATA_SOURCES", mock_sources)

    # Запуск конвеєра повинен впасти через порушення обмеження CHECK
    with pytest.raises(Exception):
        run_pipeline("TEST-FAIL-BATCH")

    # Перевіряємо, що транзакція відкотилася і стан core не пошкоджений
    counts_after, _ = get_core_metrics()
    assert counts_before == counts_after, (
        f"ROLLBACK не спрацював: стан core змінився! {counts_before} != {counts_after}"
    )

    # Перевіряємо, що в журналі зафіксовано статус FAILED
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, error_message FROM audit.pipeline_runs ORDER BY run_id DESC LIMIT 1;"
            )
            status, err_msg = cur.fetchone()
            assert status == "FAILED"
            assert "check" in err_msg.lower() or "quantity" in err_msg.lower()

    # Відновлюємо валідний стан
    monkeypatch.undo()
    recovery_run_id = run_pipeline("S08-V1")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM audit.pipeline_runs WHERE run_id = %s;",
                (recovery_run_id,),
            )
            assert cur.fetchone()[0] == "SUCCESS"


def test_schema_failure_pre_ingest(tmp_path, monkeypatch):
    """Завдання 8.3: Некоректний заголовок файлу зупиняє конвеєр до моменту публікації в core."""
    from src.lab02 import ingest

    counts_before, _ = get_core_metrics()

    bad_csv = tmp_path / "bad_customers.csv"
    bad_csv.write_text("invalid_col1,invalid_col2\n1,test\n", encoding="utf-8")

    mock_sources = [dict(s) for s in ingest.DATA_SOURCES]
    mock_sources[0]["file"] = bad_csv
    monkeypatch.setattr(ingest, "DATA_SOURCES", mock_sources)

    with pytest.raises(ValueError, match="Порушення схеми CSV"):
        ingest.load_staging("TEST-SCHEMA-FAIL")

    counts_after, _ = get_core_metrics()
    assert (
        counts_before == counts_after
    ), "Стан core не повинен змінюватися при помилці схеми джерела!"
