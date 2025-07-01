import sqlite3

# Connect to DB
conn = sqlite3.connect("gsmarena.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Drop the old table if it exists
c.execute("DROP TABLE IF EXISTS pivoted_by_model")

# Get column info from pivoted_data
c.execute("PRAGMA table_info(pivoted_data)")
cols_info = c.fetchall()
all_cols = [col["name"] for col in cols_info]

# Use 'models' as the column to split
has_models_col = "models" in all_cols

# Columns to copy (exclude 'models' if present)
base_cols = [col for col in all_cols if col != "models"]
base_cols_quoted = [f'"{col}"' for col in base_cols]

# Create new table with those columns + 'model'
quoted_create = ",\n    ".join([f'"{col}" TEXT' for col in base_cols])
c.execute(f"""
CREATE TABLE pivoted_by_model (
    model TEXT,
    {quoted_create}
)
""")

# Read all rows from pivoted_data
c.execute("SELECT * FROM pivoted_data")
rows = c.fetchall()

for row in rows:
    models_raw = row["models"].strip() if has_models_col and row["models"] else None

    if models_raw:
        models_list = [m.strip() for m in models_raw.split(",") if m.strip()]
    else:
        models_list = [row["model_name"].strip()]

    for model in models_list:
        values = [row[col] for col in base_cols]
        placeholders = ", ".join(["?"] * (1 + len(base_cols)))  # 1 for model + others
        quoted_base_cols = ", ".join(base_cols_quoted)
        c.execute(
            f"INSERT INTO pivoted_by_model (model, {quoted_base_cols}) VALUES ({placeholders})",
            [model] + values
        )

conn.commit()

# preview the first few rows
print("\nPreview of pivoted_by_model:")
for row in c.execute("SELECT model, model_name, * FROM pivoted_by_model LIMIT 5"):
    print(row)

conn.close()

print("pivoted_by_model table created successfully!")
