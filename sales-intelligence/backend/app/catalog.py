"""Product catalog used by the simulator and sample data. Shared with the dataset generator."""

PRODUCTS = [
    ("P-1001", "Wireless Keyboard", "Electronics", 42.50),
    ("P-1002", "USB-C Hub", "Electronics", 29.99),
    ("P-1003", "Noise Cancelling Headphones", "Electronics", 129.00),
    ("P-1004", "27-inch Monitor", "Electronics", 219.90),
    ("P-2001", "Ergonomic Office Chair", "Furniture", 189.50),
    ("P-2002", "Standing Desk", "Furniture", 349.00),
    ("P-2003", "Bookshelf, 5 Tier", "Furniture", 89.99),
    ("P-3001", "Stainless Steel Cookware Set", "Kitchen", 149.00),
    ("P-3002", "Espresso Machine", "Kitchen", 279.00),
    ("P-3003", "Blender Pro", "Kitchen", 79.95),
    ("P-4001", "Running Shoes", "Apparel", 119.00),
    ("P-4002", "Waterproof Jacket", "Apparel", 159.00),
    ("P-5001", "Cordless Drill", "Tools", 99.00),
    ("P-5002", "Socket Wrench Kit", "Tools", 64.50),
    ("P-6001", "Yoga Mat", "Sports", 34.99),
    ("P-6002", "Adjustable Dumbbell Set", "Sports", 249.00),
]

REGIONS = ["North", "South", "East", "West", "Central"]

CATEGORIES = sorted({p[2] for p in PRODUCTS})
