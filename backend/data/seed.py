"""
Builds the demo database: a fictional Indian online retailer ("ShopKart"),
2024-01-01 to 2025-12-31. Deterministic (fixed seed), so evaluation results
are reproducible on any machine.

    python data/seed.py            # writes data/retail.db
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "retail.db"
random.seed(42)

REGIONS = [
    (1, "North", ["Delhi", "Jaipur", "Lucknow", "Chandigarh"]),
    (2, "South", ["Bengaluru", "Chennai", "Hyderabad", "Kochi"]),
    (3, "West", ["Mumbai", "Pune", "Ahmedabad", "Surat"]),
    (4, "East", ["Kolkata", "Bhubaneswar", "Patna", "Guwahati"]),
]

CATEGORIES = {
    "Electronics": [("Wireless Earbuds", 1999), ("Smartwatch", 3499), ("Bluetooth Speaker", 2499),
                    ("Power Bank 20000mAh", 1499), ("Laptop Stand", 999), ("Mechanical Keyboard", 4299),
                    ("4K Monitor", 23999), ("Webcam HD", 2199), ("USB-C Hub", 1799), ("Noise Cancelling Headphones", 8999)],
    "Home & Kitchen": [("Air Fryer", 5999), ("Mixer Grinder", 3299), ("Non-stick Pan Set", 1899),
                       ("Water Purifier", 11999), ("Steel Water Bottle", 499), ("Pressure Cooker 5L", 2299),
                       ("Electric Kettle", 1299), ("Dinner Set 18pc", 2799), ("Vacuum Cleaner", 7499), ("LED Bulb Pack", 599)],
    "Fashion": [("Cotton Kurta", 899), ("Denim Jeans", 1499), ("Running Shoes", 2999), ("Silk Saree", 4599),
                ("Leather Wallet", 799), ("Sunglasses", 1199), ("Formal Shirt", 1299), ("Handbag", 2199),
                ("Sports T-shirt", 599), ("Winter Jacket", 3499)],
    "Books": [("Atomic Habits", 499), ("Python Crash Course", 899), ("The Psychology of Money", 399),
              ("Clean Code", 1099), ("Wings of Fire", 299), ("Deep Learning Book", 2499),
              ("Ikigai", 349), ("Rich Dad Poor Dad", 399), ("Sapiens", 599), ("Think and Grow Rich", 249)],
    "Beauty": [("Face Wash", 299), ("Sunscreen SPF50", 549), ("Hair Oil", 249), ("Perfume", 1799),
               ("Lip Balm", 199), ("Moisturiser", 449), ("Shampoo", 399), ("Beard Trimmer", 1499),
               ("Hair Dryer", 1999), ("Makeup Kit", 2499)],
    "Sports": [("Yoga Mat", 799), ("Dumbbell Set 10kg", 2499), ("Cricket Bat", 3299), ("Badminton Racket", 1499),
               ("Football", 899), ("Cycling Helmet", 1799), ("Skipping Rope", 299), ("Resistance Bands", 699),
               ("Treadmill", 32999), ("Gym Bag", 1199)],
}
CATEGORY_WEIGHT = {"Electronics": 1.3, "Home & Kitchen": 1.1, "Fashion": 1.4, "Books": 0.9, "Beauty": 1.0, "Sports": 0.7}
FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Sai", "Reyansh", "Krishna", "Ishaan", "Rohan", "Kabir",
         "Ananya", "Diya", "Aadhya", "Saanvi", "Priya", "Meera", "Kavya", "Anika", "Nisha", "Lakshmi",
         "Rahul", "Vikram", "Neha", "Pooja", "Arun", "Divya", "Karthik", "Sneha", "Manoj", "Asha"]
LAST = ["Sharma", "Nair", "Iyer", "Reddy", "Patel", "Gupta", "Singh", "Das", "Menon", "Kulkarni",
        "Joshi", "Rao", "Banerjee", "Mehta", "Pillai", "Verma", "Chopra", "Mishra", "Bose", "Shetty"]
SEGMENTS = [("Consumer", 0.7), ("Corporate", 0.2), ("Small Business", 0.1)]
CHANNELS = [("Website", 0.45), ("Mobile App", 0.45), ("Marketplace", 0.10)]
PAYMENTS = [("UPI", 0.5), ("Card", 0.25), ("Cash on Delivery", 0.15), ("Net Banking", 0.10)]

SCHEMA = """
CREATE TABLE regions (
    region_id   INTEGER PRIMARY KEY,
    region_name TEXT NOT NULL            -- North, South, West, East
);
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL,
    region_id   INTEGER NOT NULL REFERENCES regions(region_id),
    segment     TEXT NOT NULL,           -- Consumer, Corporate, Small Business
    signup_date TEXT NOT NULL            -- YYYY-MM-DD
);
CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,          -- Electronics, Home & Kitchen, Fashion, Books, Beauty, Sports
    unit_price   REAL NOT NULL,          -- list price in INR
    unit_cost    REAL NOT NULL           -- cost to the company in INR
);
CREATE TABLE orders (
    order_id       INTEGER PRIMARY KEY,
    customer_id    INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date     TEXT NOT NULL,        -- YYYY-MM-DD
    status         TEXT NOT NULL,        -- Delivered, Shipped, Cancelled, Returned
    channel        TEXT NOT NULL,        -- Website, Mobile App, Marketplace
    payment_method TEXT NOT NULL         -- UPI, Card, Cash on Delivery, Net Banking
);
CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    quantity      INTEGER NOT NULL,
    unit_price    REAL NOT NULL,         -- price actually charged per unit, after discount (INR)
    discount_pct  REAL NOT NULL          -- 0, 5, 10, 15 or 20
);
"""


def pick(options):
    r, acc = random.random(), 0.0
    for value, w in options:
        acc += w
        if r <= acc:
            return value
    return options[-1][0]


def build(path: Path = DB_PATH) -> Path:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)

    con.executemany("INSERT INTO regions VALUES (?, ?)", [(rid, name) for rid, name, _ in REGIONS])

    products, pid = [], 1
    for cat, items in CATEGORIES.items():
        for name, price in items:
            margin = random.uniform(0.18, 0.45)
            products.append((pid, name, cat, float(price), round(price * (1 - margin), 2)))
            pid += 1
    con.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)

    customers = []
    start = date(2023, 6, 1)
    for cid in range(1, 801):
        rid, _, cities = random.choices(REGIONS, weights=[0.27, 0.30, 0.28, 0.15])[0]
        signup = start + timedelta(days=random.randint(0, 900))
        customers.append((cid, f"{random.choice(FIRST)} {random.choice(LAST)}", random.choice(cities), rid,
                          pick(SEGMENTS), signup.isoformat()))
    con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?)", customers)

    by_cat = {}
    for p in products:
        by_cat.setdefault(p[2], []).append(p)
    cats, cat_w = list(CATEGORY_WEIGHT), list(CATEGORY_WEIGHT.values())

    orders, items, oid, iid = [], [], 1, 1
    day = date(2024, 1, 1)
    while day <= date(2025, 12, 31):
        # Growth over time + festive season (Oct-Nov) spike + weekend bump.
        growth = 1 + 0.35 * ((day - date(2024, 1, 1)).days / 730)
        festive = 1.8 if day.month in (10, 11) else (1.25 if day.month == 12 else 1.0)
        weekend = 1.2 if day.weekday() >= 5 else 1.0
        n = max(0, int(random.gauss(9 * growth * festive * weekend, 2.5)))
        for _ in range(n):
            cust = random.choice(customers)
            if cust[5] > day.isoformat():
                continue
            status = pick([("Delivered", 0.84), ("Shipped", 0.04), ("Cancelled", 0.07), ("Returned", 0.05)])
            if day >= date(2025, 12, 20) and status == "Delivered":
                status = "Shipped"
            orders.append((oid, cust[0], day.isoformat(), status, pick(CHANNELS), pick(PAYMENTS)))
            for _ in range(random.choices([1, 2, 3, 4], weights=[0.55, 0.28, 0.12, 0.05])[0]):
                prod = random.choice(by_cat[random.choices(cats, weights=cat_w)[0]])
                disc = random.choices([0, 5, 10, 15, 20], weights=[0.45, 0.2, 0.18, 0.1, 0.07])[0]
                if day.month in (10, 11) and disc == 0 and random.random() < 0.4:
                    disc = 10
                qty = random.choices([1, 2, 3], weights=[0.8, 0.15, 0.05])[0]
                items.append((iid, oid, prod[0], qty, round(prod[3] * (1 - disc / 100), 2), float(disc)))
                iid += 1
            oid += 1
        day += timedelta(days=1)

    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders)
    con.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?)", items)
    con.executescript("""
        CREATE INDEX idx_orders_date ON orders(order_date);
        CREATE INDEX idx_orders_customer ON orders(customer_id);
        CREATE INDEX idx_items_order ON order_items(order_id);
        CREATE INDEX idx_items_product ON order_items(product_id);
    """)
    con.commit()
    con.close()
    print(f"built {path}: {len(customers)} customers, {len(products)} products, "
          f"{len(orders)} orders, {len(items)} order items")
    return path


if __name__ == "__main__":
    build()
