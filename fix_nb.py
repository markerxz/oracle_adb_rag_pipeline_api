import json

nb_path = "/home/opc/vector-playground/oracle_vector_search_only.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        source = cell["source"]
        for i, line in enumerate(source):
            if "print(f\"   Text: {text.strip().replace" in line:
                source[i] = "    text_clean = text.strip().replace('\\n', ' ')\n"
                source.insert(i + 1, "    print(f\"   Text: {text_clean}\\n\")\n")

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=2)

print("Notebook successfully fixed.")
