# %% [markdown]
# # Лабораторна робота №1: Первинне дослідження джерел даних (CityFlow S08)
# **Студент:** Tim
# **Середовище:** Arch Linux, Neovim, uv, Python 3.12+

# %%
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# Визначення кореня проєкту
root = Path.cwd()
if root.name == "notebooks":
    root = root.parent

raw_path = root / "data" / "raw"
sample_path = root / "data" / "sample"
docs_path = root / "docs"
sample_path.mkdir(parents=True, exist_ok=True)
docs_path.mkdir(parents=True, exist_ok=True)

# 1. Зчитування сирих CSV
customers = pd.read_csv(raw_path / "customers.csv")
merchants = pd.read_csv(raw_path / "merchants.csv")
products = pd.read_csv(raw_path / "products.csv")
orders = pd.read_csv(raw_path / "orders.csv")

dfs = {
    "customers": (customers, "customer_id"),
    "merchants": (merchants, "merchant_id"),
    "products": (products, "product_id"),
    "orders": (orders, "order_id")
}

# %% [markdown]
# ## 1. Збереження вибірки (Sample Data)
# Збереження перших 100 рядків кожного джерела для відтворюваності в Git без raw-даних.

# %%
for name, (df, _) in dfs.items():
    df.head(100).to_csv(sample_path / f"{name}_sample.csv", index=False)
print("Семпли збережено в data/sample/")

# %% [markdown]
# ## 2. Базові характеристики та Grain
# - **customers**: Grain — один зареєстрований користувач; ключ — customer_id
# - **merchants**: Grain — один заклад-партнер; ключ — merchant_id
# - **products**: Grain — одна позиція меню/товару; ключ — product_id; FK: merchant_id
# - **orders**: Grain — одна транзакція замовлення; ключ — order_id; FK: customer_id, merchant_id

# %%
for name, (df, key) in dfs.items():
    print(f"=== {name.upper()} ===")
    print(f"Розмірність (rows, cols): {df.shape}")
    print(f"Кандидатний ключ: {key}")
    print(f"Типи даних:\n{df.dtypes}\n")

# %% [markdown]
# ## 3. Перевірка пропусків і порожніх значень
# Враховуються: системні null (NaN/None), порожні рядки ('') та пробіли ('   ').

# %%
def audit_nulls(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for col in df.columns:
        null_count = df[col].isna().sum()
        empty_str_count = 0
        whitespace_count = 0
        if df[col].dtype == "object":
            empty_str_count = (df[col] == "").sum()
            whitespace_count = df[col].astype(str).str.strip().eq("").sum() - null_count - empty_str_count
            if whitespace_count < 0:
                whitespace_count = 0
        total_missing = null_count + empty_str_count + whitespace_count
        records.append({
            "column": col,
            "nulls": null_count,
            "empty_strings": empty_str_count,
            "whitespace_only": whitespace_count,
            "total_missing": total_missing,
            "missing_pct": round(total_missing / len(df) * 100, 2)
        })
    return pd.DataFrame(records)

for name, (df, _) in dfs.items():
    print(f"--- Пропуски у {name} ---")
    missing_report = audit_nulls(df)
    print(missing_report[missing_report["total_missing"] > 0])
    print()

# %% [markdown]
# ## 4. Перевірка дублікатів (повні рядки та кандидатні ключі)

# %%
for name, (df, key) in dfs.items():
    full_dups = df.duplicated().sum()
    key_dups = df.duplicated(subset=[key]).sum()
    print(f"[{name}] Повні дублікати: {full_dups} | Дублікати ключа '{key}': {key_dups}")
    if key_dups > 0:
        print(f"Приклади колізій ключа в {name}:")
        print(df[df.duplicated(subset=[key], keep=False)].head(4))
        print()

# %% [markdown]
# ## 5. Перевірка зв'язків (Foreign Keys цілісність)

# %%
# Перевірка: orders.customer_id -> customers.customer_id
orphan_orders_cust = orders[~orders["customer_id"].isin(customers["customer_id"])]
print(f"Замовлень із неіснуючим customer_id: {len(orphan_orders_cust)}")

# Перевірка: orders.merchant_id -> merchants.merchant_id
orphan_orders_merch = orders[~orders["merchant_id"].isin(merchants["merchant_id"])]
print(f"Замовлень із неіснуючим merchant_id: {len(orphan_orders_merch)}")

# Перевірка: products.merchant_id -> merchants.merchant_id
orphan_prods_merch = products[~products["merchant_id"].isin(merchants["merchant_id"])]
print(f"Товарів із неіснуючим merchant_id: {len(orphan_prods_merch)}")

# %% [markdown]
# ## 6. Статистичний огляд колонок

# %%
print("--- Статистика Orders (числові поля) ---")
print(orders.describe())

print("\n--- Категоріальні значення Orders (статуси) ---")
print(orders["order_status"].value_counts(dropna=False))

# %% [markdown]
# ## 7. Підсумкова діагностична таблиця

# %%
summary_records = []
for name, (df, key) in dfs.items():
    min_date, max_date = "N/A", "N/A"
    for date_col in ["created_at", "registered_at", "opened_at"]:
        if date_col in df.columns:
            temp_dates = pd.to_datetime(df[date_col], errors="coerce")
            min_date = str(temp_dates.min())
            max_date = str(temp_dates.max())
            break
            
    summary_records.append({
        "dataset": name,
        "rows_count": len(df),
        "columns_count": df.shape[1],
        "unique_keys": df[key].nunique(),
        "key_duplicates": df.duplicated(subset=[key]).sum(),
        "full_row_duplicates": df.duplicated().sum(),
        "total_null_cells": df.isna().sum().sum(),
        "min_date": min_date,
        "max_date": max_date
    })

summary_df = pd.DataFrame(summary_records)
print(summary_df.to_string(index=False))

# %% [markdown]
# ## 8. Генерація діагностичних графіків
# Графіки зберігаються у docs/ як PNG без використання GUI.

# %%
# Графік 1: Кількість замовлень за статусами
plt.figure(figsize=(8, 4.5))
status_counts = orders["order_status"].fillna("NULL/MISSING").value_counts()
status_counts.plot(kind="bar", color="#2b5c8f", edgecolor="black")
plt.title("Розподіл замовлень за статусами (CityFlow S08)")
plt.xlabel("Статус замовлення")
plt.ylabel("Кількість записів")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(docs_path / "orders_by_status.png", dpi=300)
plt.close()

# Графік 2: Динаміка замовлень за датою
orders["order_date"] = pd.to_datetime(orders["created_at"], errors="coerce").dt.date
date_counts = orders["order_date"].value_counts().sort_index()

plt.figure(figsize=(10, 4.5))
date_counts.plot(kind="line", marker="o", color="#d95f02", linewidth=1.5)
plt.title("Кількість замовлень за датами (CityFlow S08)")
plt.xlabel("Дата")
plt.ylabel("Кількість замовлень")
plt.grid(True, linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig(docs_path / "orders_by_date.png", dpi=300)
plt.close()

print("Графіки збережено в docs/: orders_by_status.png, orders_by_date.png")
