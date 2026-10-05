from pathlib import Path
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd

# Ініціалізація шляхів
root = Path.cwd()
raw_path = root / "data" / "raw"
docs_path = root / "docs"
docs_path.mkdir(parents=True, exist_ok=True)

# 1. Зчитування даних для вилучення реальних типів і прикладів
customers = pd.read_csv(raw_path / "customers.csv")
merchants = pd.read_csv(raw_path / "merchants.csv")
products = pd.read_csv(raw_path / "products.csv")
orders = pd.read_csv(raw_path / "orders.csv")

# 2. Метадані для словника даних
meta = {
    "customers": {
        "desc": "Реєстр зареєстрованих користувачів платформи CityFlow.",
        "grain": "Один рядок = один клієнт сервісу",
        "keys": {"customer_id": "Primary Key candidate"},
        "expected": {
            "customer_id": "VARCHAR(32)",
            "first_name": "VARCHAR(64)",
            "last_name": "VARCHAR(64)",
            "email": "VARCHAR(128)",
            "phone": "VARCHAR(32)",
            "registered_at": "TIMESTAMPTZ",
        },
        "issues": {
            "customer_id": "1 повний дублікат рядка (S08-C000504)",
            "phone": "5 пропущених значень (NaN)",
        },
    },
    "merchants": {
        "desc": "Реєстр закладів-партнерів мережі (ресторани, магазини).",
        "grain": "Один рядок = один партнерський заклад",
        "keys": {"merchant_id": "Primary Key candidate"},
        "expected": {
            "merchant_id": "VARCHAR(32)",
            "name": "VARCHAR(128)",
            "category": "VARCHAR(64)",
            "city": "VARCHAR(64)",
            "opened_at": "TIMESTAMPTZ",
        },
        "issues": {
            "merchant_id": "1 повний дублікат рядка (S08-M00009)",
        },
    },
    "products": {
        "desc": "Каталог товарів та номенклатурних позицій закладів.",
        "grain": "Один рядок = один товар конкретного закладу",
        "keys": {
            "product_id": "Primary Key candidate",
            "merchant_id": "Foreign Key -> merchants.merchant_id",
        },
        "expected": {
            "product_id": "VARCHAR(32)",
            "merchant_id": "VARCHAR(32)",
            "name": "VARCHAR(128)",
            "category": "VARCHAR(64)",
            "unit_price_uah": "NUMERIC(10, 2)",
        },
        "issues": {
            "product_id": "1 повний дублікат рядка (S08-P000219)",
            "merchant_id": "1 сирітний запис без батьківського закладу (S08-P000331)",
            "unit_price_uah": "1 запис із ціною <= 0",
        },
    },
    "orders": {
        "desc": "Транзакційні записи замовлень користувачів.",
        "grain": "Один рядок = одна транзакція замовлення",
        "keys": {
            "order_id": "Primary Key candidate",
            "customer_id": "Foreign Key -> customers.customer_id",
            "merchant_id": "Foreign Key -> merchants.merchant_id",
        },
        "expected": {
            "order_id": "VARCHAR(32)",
            "customer_id": "VARCHAR(32)",
            "merchant_id": "VARCHAR(32)",
            "order_status": "VARCHAR(32)",
            "total_amount": "NUMERIC(12, 2)",
            "currency": "VARCHAR(3)",
            "created_at": "TIMESTAMPTZ",
        },
        "issues": {
            "order_id": "1 повний дублікат рядка (S08-O0000683)",
            "customer_id": "1 сирітний запис без зареєстрованого клієнта (S08-O0004825)",
            "merchant_id": "1 сирітний запис без закладу (S08-O0005136)",
            "currency": "1 аномальне значення 'UA H'",
            "created_at": "2 пошкоджені часові мітки (NaT)",
        },
    },
}

# Генерація data_dictionary.md
dict_lines = ["# Словник даних проєкту CityFlow (Пакет S08)\n"]

for tbl_name, df in [
    ("customers", customers),
    ("merchants", merchants),
    ("products", products),
    ("orders", orders),
]:
    cfg = meta[tbl_name]
    dict_lines.append(f"## Таблиця: `{tbl_name}.csv`")
    dict_lines.append(f"**Опис:** {cfg['desc']}")
    dict_lines.append(f"**Зернистість (Grain):** {cfg['grain']}\n")
    dict_lines.append(
        "| Колонка | Тип pandas | Логічний тип | Роль ключа | Nullable | Приклад | Виявлені проблеми |"
    )
    dict_lines.append(
        "|---|---|---|---|---|---|---|"
    )

    for col in df.columns:
        p_dtype = str(df[col].dtype)
        l_dtype = cfg["expected"].get(col, "VARCHAR")
        key_role = cfg["keys"].get(col, "Attribute")
        nullable = "YES" if df[col].isna().sum() > 0 else "NO"
        sample_val = (
            str(df[col].dropna().iloc[0]).replace("\n", " ")
            if not df[col].dropna().empty
            else "NULL"
        )
        issues = cfg["issues"].get(col, "Не виявлено")
        dict_lines.append(
            f"| `{col}` | `{p_dtype}` | `{l_dtype}` | {key_role} | {nullable} | `{sample_val}` | {issues} |"
        )
    dict_lines.append("\n---\n")

(docs_path / "data_dictionary.md").write_text(
    "\n".join(dict_lines).strip() + "\n", encoding="utf-8"
)
print("docs/data_dictionary.md згенеровано.")

# 3. Генерація architecture_v0.png
fig, ax = plt.subplots(figsize=(13, 7.5), dpi=300)
ax.set_xlim(0, 13)
ax.set_ylim(0, 8)
ax.axis("off")


def draw_block(ax, x, y, w, h, title, subtitle, color, linestyle="solid"):
    rect = patches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.08",
        edgecolor=color,
        facecolor="#ffffff",
        linestyle=linestyle,
        linewidth=1.5,
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2,
        y + h * 0.62,
        title,
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#0f172a",
    )
    ax.text(
        x + w / 2,
        y + h * 0.30,
        subtitle,
        ha="center",
        va="center",
        fontsize=7.2,
        color="#475569",
    )


# Межі Git-репозиторію
git_box = patches.FancyBboxPatch(
    (3.5, 0.4),
    9.0,
    7.2,
    boxstyle="round,pad=0.12",
    edgecolor="#64748b",
    facecolor="#f8fafc",
    linestyle="--",
    linewidth=1.2,
)
ax.add_patch(git_box)
ax.text(
    8.0,
    7.35,
    "Git Repository (Single Source of Truth, Raw Data Excluded via .gitignore)",
    ha="center",
    va="center",
    fontsize=9,
    fontweight="bold",
    color="#334155",
)

# Реалізовані компоненти Лабораторної №1
draw_block(
    ax,
    0.4,
    4.8,
    2.6,
    1.3,
    "Raw CSV Archive",
    "cityflow_S08_base_v1.zip\n(SHA-256 Verified)",
    "#1d4ed8",
)
draw_block(
    ax,
    3.8,
    4.8,
    2.4,
    1.3,
    "Local Raw Storage",
    "data/raw/*.csv\n(Untracked in Git)",
    "#1d4ed8",
)
draw_block(
    ax,
    6.8,
    4.8,
    2.4,
    1.3,
    "Profiling Pipeline",
    "01_source_profiling.py\n(jupytext <-> .ipynb)",
    "#1d4ed8",
)
draw_block(
    ax,
    9.8,
    5.7,
    2.3,
    1.0,
    "Sample Storage",
    "data/sample/*.csv\n(<= 100 rows)",
    "#15803d",
)
draw_block(
    ax,
    9.8,
    4.4,
    2.3,
    1.0,
    "Documentation",
    "data_dictionary.md\nquality_findings.md",
    "#15803d",
)
draw_block(
    ax,
    9.8,
    3.1,
    2.3,
    1.0,
    "Diagnostic Plots",
    "orders_by_status.png\norders_by_date.png",
    "#15803d",
)

# Заплановані компоненти наступних лабораторних
draw_block(
    ax,
    3.8,
    0.8,
    2.4,
    1.4,
    "[Planned] Ingestion & Batch",
    "CLI / Bash / API Ingestion\nOrchestration scripts",
    "#94a3b8",
    linestyle="dashed",
)
draw_block(
    ax,
    6.8,
    0.8,
    2.4,
    1.4,
    "[Planned] PostgreSQL",
    "Staging & Core Relational\nIntegrity Constraints (FK, CHECK)",
    "#94a3b8",
    linestyle="dashed",
)
draw_block(
    ax,
    9.8,
    0.8,
    2.3,
    1.4,
    "[Planned] Analytics DWH",
    "Transformations (dbt / SQL)\nBI Dashboards",
    "#94a3b8",
    linestyle="dashed",
)

# Стрілки руху даних
props = dict(arrowstyle="->", color="#1d4ed8", lw=1.5)
ax.annotate("", xy=(3.8, 5.45), xytext=(3.0, 5.45), arrowprops=props)
ax.annotate("", xy=(6.8, 5.45), xytext=(6.2, 5.45), arrowprops=props)
ax.annotate("", xy=(9.8, 6.2), xytext=(9.2, 5.65), arrowprops=props)
ax.annotate("", xy=(9.8, 4.9), xytext=(9.2, 5.45), arrowprops=props)
ax.annotate("", xy=(9.8, 3.6), xytext=(9.2, 5.25), arrowprops=props)

plan_props = dict(arrowstyle="->", color="#94a3b8", lw=1.2, linestyle="dashed")
ax.annotate("", xy=(6.8, 1.5), xytext=(6.2, 1.5), arrowprops=plan_props)
ax.annotate("", xy=(9.8, 1.5), xytext=(9.2, 1.5), arrowprops=plan_props)
ax.annotate("", xy=(5.0, 2.2), xytext=(5.0, 4.8), arrowprops=plan_props)

plt.tight_layout()
plt.savefig(docs_path / "architecture_v0.png", dpi=300)
plt.close()
print("docs/architecture_v0.png згенеровано.")
