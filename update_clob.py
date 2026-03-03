import json
nb_path = "/home/opc/vector-playground/oracle_vector_search_only.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb["cells"]:
    if cell.get("cell_type") == "code":
        source = cell.get("source", [])
        for i, line in enumerate(source):
            if "cursor.execute(insert_sql, {'cust_id': pdf_customer_id, 'chunk_size': size, 'rec_text': pdf_text})" in line:
                source.insert(i, "cursor.setinputsizes(rec_text=oracledb.DB_TYPE_CLOB)\n")
                break

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=2)

print("Notebook updated with CLOB binding.")
