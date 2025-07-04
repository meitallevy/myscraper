import sqlite3

# Connect to the existing database
conn = sqlite3.connect("gsmarena_full_with_pivots.db")
c = conn.cursor()

# Get all distinct param_names from models_params
c.execute("SELECT DISTINCT param_name FROM models_params")
param_names = [row[0] for row in c.fetchall()]

# Build dynamic SQL CASE statements for pivoting
pivot_columns = ",\n    ".join(
    f"MAX(CASE WHEN mp.param_name = '{param}' THEN mp.param_value END) AS [{param}]"
    for param in param_names
)

# Build the full SQL query
query = f"""
DROP TABLE IF EXISTS pivoted_data;

CREATE TABLE pivoted_data AS
SELECT
    mv.unique_model_id,
    mv.maker,
    mv.model_name,
    mv.esim_support,
    mv.sim_data,
    mv.is_android,
    mv.os_data,
    {pivot_columns}
FROM models_view mv
LEFT JOIN models_params mp ON mv.unique_model_id = mp.unique_model_id
GROUP BY mv.unique_model_id;
"""

# Execute the query
c.executescript(query)
conn.commit()

print("pivoted_data table created successfully with the following parameters:")
for param in param_names:
    print(f" - {param}")

# preview the first few rows
print("\nPreview of pivoted_data:")
for row in c.execute("SELECT * FROM pivoted_data LIMIT 5"):
    print(row)

# Close the connection
conn.close()
