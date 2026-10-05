# Словник даних проєкту CityFlow (Пакет S08)

## Таблиця: `customers.csv`
**Опис:** Реєстр зареєстрованих користувачів платформи CityFlow.
**Зернистість (Grain):** Один рядок = один клієнт сервісу

| Колонка | Тип pandas | Логічний тип | Роль ключа | Nullable | Приклад | Виявлені проблеми |
|---|---|---|---|---|---|---|
| `customer_id` | `str` | `VARCHAR(32)` | Primary Key candidate | NO | `S08-C000001` | 1 повний дублікат рядка (S08-C000504) |
| `full_name` | `str` | `VARCHAR` | Attribute | NO | `Natalia Shevchenko` | Не виявлено |
| `email` | `str` | `VARCHAR(128)` | Attribute | NO | `s08.customer000001@example.test` | Не виявлено |
| `phone` | `float64` | `VARCHAR(32)` | Attribute | YES | `380501799552.0` | 5 пропущених значень (NaN) |
| `city` | `str` | `VARCHAR` | Attribute | NO | `Kharkiv` | Не виявлено |
| `service_zone_id` | `str` | `VARCHAR` | Attribute | NO | `KHA-Z01` | Не виявлено |
| `registered_at` | `str` | `TIMESTAMPTZ` | Attribute | NO | `2026-01-24T23:51:01.642906949Z` | Не виявлено |
| `customer_status` | `str` | `VARCHAR` | Attribute | NO | `active` | Не виявлено |

---

## Таблиця: `merchants.csv`
**Опис:** Реєстр закладів-партнерів мережі (ресторани, магазини).
**Зернистість (Grain):** Один рядок = один партнерський заклад

| Колонка | Тип pandas | Логічний тип | Роль ключа | Nullable | Приклад | Виявлені проблеми |
|---|---|---|---|---|---|---|
| `merchant_id` | `str` | `VARCHAR(32)` | Primary Key candidate | NO | `S08-M00001` | 1 повний дублікат рядка (S08-M00009) |
| `merchant_name` | `str` | `VARCHAR` | Attribute | NO | `Family Table 01` | Не виявлено |
| `merchant_type` | `str` | `VARCHAR` | Attribute | NO | `restaurant` | Не виявлено |
| `city` | `str` | `VARCHAR(64)` | Attribute | NO | `Dnipro` | Не виявлено |
| `service_zone_id` | `str` | `VARCHAR` | Attribute | NO | `DNI-Z03` | Не виявлено |
| `opened_at` | `str` | `TIMESTAMPTZ` | Attribute | NO | `2024-07-18T04:35:38.016284212Z` | Не виявлено |
| `merchant_status` | `str` | `VARCHAR` | Attribute | NO | `active` | Не виявлено |

---

## Таблиця: `products.csv`
**Опис:** Каталог товарів та номенклатурних позицій закладів.
**Зернистість (Grain):** Один рядок = один товар конкретного закладу

| Колонка | Тип pandas | Логічний тип | Роль ключа | Nullable | Приклад | Виявлені проблеми |
|---|---|---|---|---|---|---|
| `product_id` | `str` | `VARCHAR(32)` | Primary Key candidate | NO | `S08-P000001` | 1 повний дублікат рядка (S08-P000219) |
| `merchant_id` | `str` | `VARCHAR(32)` | Foreign Key -> merchants.merchant_id | NO | `S08-M00001` | 1 сирітний запис без батьківського закладу (S08-P000331) |
| `product_name` | `str` | `VARCHAR` | Attribute | NO | `Chicken Burger` | Не виявлено |
| `category` | `str` | `VARCHAR(64)` | Attribute | NO | `burgers` | Не виявлено |
| `unit_price_uah` | `float64` | `NUMERIC(10, 2)` | Attribute | NO | `202.92` | 1 запис із ціною <= 0 |
| `is_active` | `bool` | `VARCHAR` | Attribute | NO | `True` | Не виявлено |
| `updated_at` | `str` | `VARCHAR` | Attribute | NO | `2025-10-19T02:50:44.689822020Z` | Не виявлено |

---

## Таблиця: `orders.csv`
**Опис:** Транзакційні записи замовлень користувачів.
**Зернистість (Grain):** Один рядок = одна транзакція замовлення

| Колонка | Тип pandas | Логічний тип | Роль ключа | Nullable | Приклад | Виявлені проблеми |
|---|---|---|---|---|---|---|
| `order_id` | `str` | `VARCHAR(32)` | Primary Key candidate | NO | `S08-O0000001` | 1 повний дублікат рядка (S08-O0000683) |
| `customer_id` | `str` | `VARCHAR(32)` | Foreign Key -> customers.customer_id | NO | `S08-C000147` | 1 сирітний запис без зареєстрованого клієнта (S08-O0004825) |
| `merchant_id` | `str` | `VARCHAR(32)` | Foreign Key -> merchants.merchant_id | NO | `S08-M00030` | 1 сирітний запис без закладу (S08-O0005136) |
| `created_at` | `str` | `TIMESTAMPTZ` | Attribute | NO | `2025-09-01T11:47:50Z` | 2 пошкоджені часові мітки (NaT) |
| `order_status` | `str` | `VARCHAR(32)` | Attribute | NO | `partially_refunded` | Не виявлено |
| `currency` | `str` | `VARCHAR(3)` | Attribute | NO | `UAH` | 1 аномальне значення 'UA H' |
| `subtotal_amount` | `float64` | `VARCHAR` | Attribute | NO | `196.55` | Не виявлено |
| `delivery_fee` | `float64` | `VARCHAR` | Attribute | NO | `86.22` | Не виявлено |
| `discount_amount` | `float64` | `VARCHAR` | Attribute | NO | `19.66` | Не виявлено |
| `total_amount` | `float64` | `NUMERIC(12, 2)` | Attribute | NO | `263.11` | Не виявлено |

---
