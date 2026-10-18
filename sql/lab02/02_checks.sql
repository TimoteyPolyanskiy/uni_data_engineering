-- sql/lab02/02_checks.sql
-- Контрольні SQL-перевірки реляційної моделі (Lab 02)

-- ============================================================================
-- 1. ДУБЛІКАТИ PK У ТАБЛИЦЯХ CORE (Очікується: 0 рядків)
-- ============================================================================
SELECT 'core.customers' AS target_table, customer_id AS duplicate_key, count(*) AS duplicate_count
FROM core.customers
GROUP BY customer_id HAVING count(*) > 1
UNION ALL
SELECT 'core.merchants', merchant_id, count(*)
FROM core.merchants
GROUP BY merchant_id HAVING count(*) > 1
UNION ALL
SELECT 'core.products', product_id, count(*)
FROM core.products
GROUP BY product_id HAVING count(*) > 1
UNION ALL
SELECT 'core.orders', order_id, count(*)
FROM core.orders
GROUP BY order_id HAVING count(*) > 1
UNION ALL
SELECT 'core.order_items', order_item_id, count(*)
FROM core.order_items
GROUP BY order_item_id HAVING count(*) > 1;

-- ============================================================================
-- 2. СИРІТНІ ЗОВНІШНІ КЛЮЧІ У CORE (Очікується: orphan_count = 0)
-- ============================================================================
SELECT 'orders -> customers' AS foreign_key, count(*) AS orphan_count
FROM core.orders o
LEFT JOIN core.customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL
UNION ALL
SELECT 'orders -> merchants', count(*)
FROM core.orders o
LEFT JOIN core.merchants m ON o.merchant_id = m.merchant_id
WHERE m.merchant_id IS NULL
UNION ALL
SELECT 'products -> merchants', count(*)
FROM core.products p
LEFT JOIN core.merchants m ON p.merchant_id = m.merchant_id
WHERE m.merchant_id IS NULL
UNION ALL
SELECT 'order_items -> orders', count(*)
FROM core.order_items oi
LEFT JOIN core.orders o ON oi.order_id = o.order_id
WHERE o.order_id IS NULL
UNION ALL
SELECT 'order_items -> products', count(*)
FROM core.order_items oi
LEFT JOIN core.products p ON oi.product_id = p.product_id
WHERE p.product_id IS NULL;

-- ============================================================================
-- 3. ЗВІРКА РЯДКІВ ТА СУМ ЗА ВАЛЮТАМИ У CORE
-- ============================================================================
SELECT 
    currency,
    count(*) AS orders_count,
    sum(subtotal_amount) AS sum_subtotal,
    sum(delivery_fee) AS sum_delivery,
    sum(discount_amount) AS sum_discount,
    sum(total_amount) AS sum_total_orders
FROM core.orders
GROUP BY currency
ORDER BY currency;

SELECT 
    currency,
    count(*) AS items_count,
    sum(quantity) AS sum_quantity,
    sum(line_total) AS sum_line_total
FROM core.order_items
GROUP BY currency
ORDER BY currency;

-- ============================================================================
-- 4. АНАЛІЗ ЗАВИЩЕННЯ СУМИ ПРИ JOIN ТА КОРЕКТНИЙ ЗАПИТ
-- ============================================================================
-- 4.1. Демонстрація викривлення (Join Fan-out):
SELECT 
    'Некоректний JOIN (завищення через 1:N)' AS calculation_method,
    count(*) AS rows_in_calculation,
    sum(o.total_amount) AS calculated_sum
FROM core.orders o
JOIN core.order_items oi ON o.order_id = oi.order_id
UNION ALL
SELECT 
    'Фактична сума core.orders (істинна)',
    count(*),
    sum(total_amount)
FROM core.orders;

-- 4.2. Коректний розрахунок без використання DISTINCT:
-- Агрегація проводиться на рівні деталізації замовлення до виконання JOIN
WITH items_agg AS (
    SELECT 
        order_id,
        sum(line_total) AS order_items_sum
    FROM core.order_items
    GROUP BY order_id
)
SELECT 
    o.currency,
    count(o.order_id) AS orders_count,
    sum(o.total_amount) AS total_orders_amount,
    sum(ia.order_items_sum) AS total_items_amount
FROM core.orders o
JOIN items_agg ia ON o.order_id = ia.order_id
GROUP BY o.currency
ORDER BY o.currency;
