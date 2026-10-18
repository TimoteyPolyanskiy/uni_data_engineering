# CityFlow Data Engineering Project (S08)

## 1. Загальний опис проєкту
Проєкт присвячений побудові платформи обробки даних для сервісу доставки **CityFlow**. Платформа акумулює інформацію про клієнтів, партнерські заклади (мерчанти), номенклатуру товарів і транзакції замовлень.

- **Студент:** Tim
- **Варіант набору даних:** CityFlow S08 (`cityflow_S08_base_v1.zip`)
- **Робоче середовище:** Arch Linux, Neovim, uv, Python 3.12+

---

## 2. Архітектура та рух даних
![Початкова архітектура системи](docs/architecture_v0.png)

Рух даних на етапі Лабораторної роботи №1:
1. Сирі CSV-файли верифікуються за SHA-256 та імпортуються до каталогу `data/raw/` (виключені з контролю версій Git).
2. Пайплайн профілювання (`notebooks/01_source_profiling.py` <-> `.ipynb`) виконує структурний, статистичний та реляційний аудит джерел.
3. Артефакти фіксуються у вигляді семплів даних (`data/sample/`), діагностичних графіків (`docs/*.png`) та аналітичної документації (`docs/*.md`).
4. Компоненти реляційного завантаження (PostgreSQL) та аналітичного сховища заплановані для реалізації на наступних етапах[cite: 4].

---

## 3. Структура проєкту
```text
├── data/
│   ├── raw/                 # Незмінні первинні CSV (ігноруються в Git)
│   └── sample/              # Семпли даних (100 рядків) для відтворюваності
├── docs/
│   ├── architecture_v0.png  # Архітектурна діаграма системи
│   ├── data_dictionary.md   # Повний словник атрибутів джерел
│   ├── data_quality_findings.md # Реєстр виявлених проблем якості
│   └── orders_by_*.png      # Діагностичні графіки розподілу замовлень
├── notebooks/
│   ├── 01_source_profiling.py     # Джерельний Python-код із розміткою percent
│   └── 01_source_profiling.ipynb  # Скомпільований блокнот з розрахунками
├── scripts/
│   └── build_docs.py        # Утиліта генерації документації та схем
├── pyproject.toml           # Маніфест залежностей uv
├── uv.lock                  # Зафіксовані точні версії середовища
└── README.md
## Лабораторна робота №2: PostgreSQL Data Pipeline (S08)

### Інфраструктура та підключення
- **СУБД:** PostgreSQL 16-alpine у контейнері `cityflow_postgres_s08`.
- **Конфігурація:** параметри підключення винесено у `.env` (шаблон надано в `.env.example`).
- **Схеми:** `stg` (сирий вхід), `core` (реляційний шар), `audit` (журнал запусків і карантин).

### Інструкція з відтворення
```fish
# 1. Запуск контейнера СУБД
docker compose up -d

# 2. Застосування DDL-структури
docker compose exec -T postgres psql -U cityflow_user -d cityflow_s08 < sql/lab02/01_ddl.sql

# 3. Виконання конвеєра імпорту та публікації
uv run python -m src.lab02.pipeline

# 4. Виконання контрольних SQL-перевірок цілісності
docker compose exec -T postgres psql -U cityflow_user -d cityflow_s08 < sql/lab02/02_checks.sql

# 5. Запуск автотестів надійності та ідемпотентності
uv run pytest tests/lab02/test_pipeline.py -v

# 6. Компіляція підсумкового звіту
uv run python scripts/lab02/generate_report.py
typst compile docs/lab02/report_lab_02.typ docs/lab02/report_lab_02.pdf
