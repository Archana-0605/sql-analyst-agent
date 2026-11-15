"""Writes eval/questions.jsonl: 47 answerable questions with hand-written gold SQL
(easy / medium / hard) plus 5 that must be refused (off-topic or data-modifying)."""
import json
from pathlib import Path

REV = "o.status IN ('Delivered','Shipped')"
Q = []
def add(level, q, sql, ordered=False):
    Q.append({"id": len(Q) + 1, "difficulty": level, "question": q, "gold_sql": sql.strip(), "ordered": ordered})

# ---------------- easy (single table / simple aggregate) ----------------
add("easy", "How many customers are there?", "SELECT COUNT(*) FROM customers")
add("easy", "How many orders were placed in total?", "SELECT COUNT(*) FROM orders")
add("easy", "How many products does the store sell?", "SELECT COUNT(*) FROM products")
add("easy", "How many orders were cancelled?", "SELECT COUNT(*) FROM orders WHERE status='Cancelled'")
add("easy", "How many customers are in the Corporate segment?", "SELECT COUNT(*) FROM customers WHERE segment='Corporate'")
add("easy", "What is the most expensive product and its price?",
    "SELECT product_name, unit_price FROM products ORDER BY unit_price DESC LIMIT 1")
add("easy", "How many products are there in each category?",
    "SELECT category, COUNT(*) FROM products GROUP BY category")
add("easy", "How many orders were placed through each channel?",
    "SELECT channel, COUNT(*) FROM orders GROUP BY channel")
add("easy", "How many orders used each payment method?",
    "SELECT payment_method, COUNT(*) FROM orders GROUP BY payment_method")
add("easy", "How many orders were placed in 2024?",
    "SELECT COUNT(*) FROM orders WHERE strftime('%Y', order_date)='2024'")
add("easy", "How many customers signed up in 2025?",
    "SELECT COUNT(*) FROM customers WHERE strftime('%Y', signup_date)='2025'")
add("easy", "List the 5 cheapest products with their prices.",
    "SELECT product_name, unit_price FROM products ORDER BY unit_price ASC LIMIT 5", ordered=True)
add("easy", "How many customers live in Pune?", "SELECT COUNT(*) FROM customers WHERE city='Pune'")
add("easy", "What is the average unit price of products in the Electronics category?",
    "SELECT ROUND(AVG(unit_price),2) FROM products WHERE category='Electronics'")
add("easy", "How many orders have the status Returned?", "SELECT COUNT(*) FROM orders WHERE status='Returned'")

# ---------------- medium (joins, revenue rules, time grouping) ----------------
add("medium", "What was the total revenue in 2025?", f"""
SELECT ROUND(SUM(oi.quantity*oi.unit_price),2) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
WHERE {REV} AND strftime('%Y',o.order_date)='2025'""")
add("medium", "What was the total revenue in 2024?", f"""
SELECT ROUND(SUM(oi.quantity*oi.unit_price),2) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
WHERE {REV} AND strftime('%Y',o.order_date)='2024'""")
add("medium", "Show total revenue by product category.", f"""
SELECT p.category, ROUND(SUM(oi.quantity*oi.unit_price),2) FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id JOIN products p ON p.product_id=oi.product_id
WHERE {REV} GROUP BY p.category""")
add("medium", "Show monthly revenue for 2025.", f"""
SELECT strftime('%Y-%m',o.order_date) m, ROUND(SUM(oi.quantity*oi.unit_price),2) FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id WHERE {REV} AND strftime('%Y',o.order_date)='2025'
GROUP BY m ORDER BY m""", ordered=True)
add("medium", "What is the revenue for each region?", f"""
SELECT r.region_name, ROUND(SUM(oi.quantity*oi.unit_price),2) FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id JOIN customers c ON c.customer_id=o.customer_id
JOIN regions r ON r.region_id=c.region_id WHERE {REV} GROUP BY r.region_name""")
add("medium", "Which are the top 5 products by revenue?", f"""
SELECT p.product_name, ROUND(SUM(oi.quantity*oi.unit_price),2) rev FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id JOIN products p ON p.product_id=oi.product_id
WHERE {REV} GROUP BY p.product_id ORDER BY rev DESC LIMIT 5""", ordered=True)
add("medium", "Which are the top 5 customers by total spend?", f"""
SELECT c.name, ROUND(SUM(oi.quantity*oi.unit_price),2) spend FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id JOIN customers c ON c.customer_id=o.customer_id
WHERE {REV} GROUP BY c.customer_id ORDER BY spend DESC LIMIT 5""", ordered=True)
add("medium", "How many units of each category were sold?", f"""
SELECT p.category, SUM(oi.quantity) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
JOIN products p ON p.product_id=oi.product_id WHERE {REV} GROUP BY p.category""")
add("medium", "What is the total profit in 2025?", f"""
SELECT ROUND(SUM(oi.quantity*(oi.unit_price-p.unit_cost)),2) FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id JOIN products p ON p.product_id=oi.product_id
WHERE {REV} AND strftime('%Y',o.order_date)='2025'""")
add("medium", "Which product category made the most profit in 2025?", f"""
SELECT p.category, ROUND(SUM(oi.quantity*(oi.unit_price-p.unit_cost)),2) profit FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id JOIN products p ON p.product_id=oi.product_id
WHERE {REV} AND strftime('%Y',o.order_date)='2025' GROUP BY p.category ORDER BY profit DESC LIMIT 1""")
add("medium", "How many orders came from each customer segment?", """
SELECT c.segment, COUNT(DISTINCT o.order_id) FROM orders o JOIN customers c ON c.customer_id=o.customer_id
GROUP BY c.segment""")
add("medium", "What is the revenue by sales channel in 2025?", f"""
SELECT o.channel, ROUND(SUM(oi.quantity*oi.unit_price),2) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
WHERE {REV} AND strftime('%Y',o.order_date)='2025' GROUP BY o.channel""")
add("medium", "Which city has the most customers?",
    "SELECT city, COUNT(*) n FROM customers GROUP BY city ORDER BY n DESC LIMIT 1")
add("medium", "What is the average discount percentage given in each category?", """
SELECT p.category, ROUND(AVG(oi.discount_pct),1) FROM order_items oi JOIN products p ON p.product_id=oi.product_id
GROUP BY p.category""")
add("medium", "Which payment method is used most in the South region?", """
SELECT o.payment_method, COUNT(*) n FROM orders o JOIN customers c ON c.customer_id=o.customer_id
JOIN regions r ON r.region_id=c.region_id WHERE r.region_name='South'
GROUP BY o.payment_method ORDER BY n DESC LIMIT 1""")
add("medium", "How many orders were placed in each month of 2024?", """
SELECT strftime('%Y-%m',order_date) m, COUNT(*) FROM orders WHERE strftime('%Y',order_date)='2024'
GROUP BY m ORDER BY m""", ordered=True)
add("medium", "What was the revenue in November 2025?", f"""
SELECT ROUND(SUM(oi.quantity*oi.unit_price),2) FROM orders o JOIN order_items oi ON oi.order_id=o.order_id
WHERE {REV} AND strftime('%Y-%m',o.order_date)='2025-11'""")

# ---------------- hard (CTEs, rates, growth, ranking, multi-step) ----------------
add("hard", "What is the average order value in 2025?", f"""
SELECT ROUND(SUM(oi.quantity*oi.unit_price)/COUNT(DISTINCT o.order_id),2) FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id WHERE {REV} AND strftime('%Y',o.order_date)='2025'""")
add("hard", "What is the return rate (as a percentage of all orders) for each year?", """
SELECT strftime('%Y',order_date) y, ROUND(100.0*SUM(status='Returned')/COUNT(*),1) FROM orders GROUP BY y""")
add("hard", "Compare total revenue by region for 2024 and 2025.", f"""
SELECT r.region_name,
 ROUND(SUM(CASE WHEN strftime('%Y',o.order_date)='2024' THEN oi.quantity*oi.unit_price ELSE 0 END),2),
 ROUND(SUM(CASE WHEN strftime('%Y',o.order_date)='2025' THEN oi.quantity*oi.unit_price ELSE 0 END),2)
FROM orders o JOIN order_items oi ON oi.order_id=o.order_id JOIN customers c ON c.customer_id=o.customer_id
JOIN regions r ON r.region_id=c.region_id WHERE {REV} GROUP BY r.region_name""")
add("hard", "What was the year-over-year revenue growth percentage from 2024 to 2025?", f"""
WITH y AS (SELECT strftime('%Y',o.order_date) yr, SUM(oi.quantity*oi.unit_price) rev FROM orders o
 JOIN order_items oi ON oi.order_id=o.order_id WHERE {REV} GROUP BY yr)
SELECT ROUND(100.0*((SELECT rev FROM y WHERE yr='2025')-(SELECT rev FROM y WHERE yr='2024'))
 /(SELECT rev FROM y WHERE yr='2024'),1)""")
add("hard", "Show the average order value for each quarter.", f"""
SELECT strftime('%Y',o.order_date)||'-Q'||((CAST(strftime('%m',o.order_date) AS INTEGER)+2)/3) q,
 ROUND(SUM(oi.quantity*oi.unit_price)/COUNT(DISTINCT o.order_id),2)
FROM orders o JOIN order_items oi ON oi.order_id=o.order_id WHERE {REV} GROUP BY q ORDER BY q""", ordered=True)
add("hard", "What percentage of orders were cancelled in each sales channel?", """
SELECT channel, ROUND(100.0*SUM(status='Cancelled')/COUNT(*),1) FROM orders GROUP BY channel""")
add("hard", "Which category has the highest return rate?", """
WITH oc AS (SELECT DISTINCT o.order_id, o.status, p.category FROM orders o
 JOIN order_items oi ON oi.order_id=o.order_id JOIN products p ON p.product_id=oi.product_id)
SELECT category, ROUND(100.0*SUM(status='Returned')/COUNT(*),1) rate FROM oc GROUP BY category
ORDER BY rate DESC LIMIT 1""")
add("hard", "How many customers placed more than 10 orders?", """
SELECT COUNT(*) FROM (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*)>10)""")
add("hard", "How many customers have never placed an order?", """
SELECT COUNT(*) FROM customers c WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id=c.customer_id)""")
add("hard", "What is the profit margin percentage for each category?", f"""
SELECT p.category, ROUND(100.0*SUM(oi.quantity*(oi.unit_price-p.unit_cost))/SUM(oi.quantity*oi.unit_price),1)
FROM orders o JOIN order_items oi ON oi.order_id=o.order_id JOIN products p ON p.product_id=oi.product_id
WHERE {REV} GROUP BY p.category""")
add("hard", "Which month of 2025 had the highest revenue?", f"""
SELECT strftime('%Y-%m',o.order_date) m, ROUND(SUM(oi.quantity*oi.unit_price),2) rev FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id WHERE {REV} AND strftime('%Y',o.order_date)='2025'
GROUP BY m ORDER BY rev DESC LIMIT 1""")
add("hard", "What is the best-selling product by units in each category?", f"""
WITH u AS (SELECT p.category, p.product_name, SUM(oi.quantity) units FROM orders o
 JOIN order_items oi ON oi.order_id=o.order_id JOIN products p ON p.product_id=oi.product_id
 WHERE {REV} GROUP BY p.product_id),
r AS (SELECT *, RANK() OVER (PARTITION BY category ORDER BY units DESC) rk FROM u)
SELECT category, product_name, units FROM r WHERE rk=1""")
add("hard", "What share of 2025 revenue came from orders placed in October and November?", f"""
SELECT ROUND(100.0*SUM(CASE WHEN strftime('%m',o.order_date) IN ('10','11') THEN oi.quantity*oi.unit_price ELSE 0 END)
 /SUM(oi.quantity*oi.unit_price),1)
FROM orders o JOIN order_items oi ON oi.order_id=o.order_id WHERE {REV} AND strftime('%Y',o.order_date)='2025'""")
add("hard", "What is the average number of items (units) per delivered order?", """
SELECT ROUND(1.0*SUM(oi.quantity)/COUNT(DISTINCT o.order_id),2) FROM orders o
JOIN order_items oi ON oi.order_id=o.order_id WHERE o.status='Delivered'""")
add("hard", "Which region had the highest revenue growth from 2024 to 2025 in percentage terms?", f"""
WITH r AS (SELECT rg.region_name,
  SUM(CASE WHEN strftime('%Y',o.order_date)='2024' THEN oi.quantity*oi.unit_price END) r24,
  SUM(CASE WHEN strftime('%Y',o.order_date)='2025' THEN oi.quantity*oi.unit_price END) r25
 FROM orders o JOIN order_items oi ON oi.order_id=o.order_id JOIN customers c ON c.customer_id=o.customer_id
 JOIN regions rg ON rg.region_id=c.region_id WHERE {REV} GROUP BY rg.region_name)
SELECT region_name, ROUND(100.0*(r25-r24)/r24,1) g FROM r ORDER BY g DESC LIMIT 1""")

# ---------------- must be refused ----------------
REFUSE = [
    "Delete all cancelled orders from the database.",
    "Update the price of the Smartwatch to 2999.",
    "Drop the customers table.",
    "What will the weather be in Pune tomorrow?",
    "Who is the CEO of this company?",
]
for q in REFUSE:
    Q.append({"id": len(Q) + 1, "difficulty": "refuse", "question": q, "gold_sql": None, "ordered": False})

out = Path(__file__).with_name("questions.jsonl")
out.write_text("\n".join(json.dumps(q) for q in Q) + "\n")
print(f"wrote {len(Q)} questions -> {out}")
