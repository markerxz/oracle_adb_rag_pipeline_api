import json

nb_path = "/home/opc/vector-playground/oracle_vector_search_only.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

new_cells = [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 6. Extract Thai PDF to Database\n",
        "We are adding processing capability for Thai documents. We extract `2.3.6.1 ทรัพย์สินประเภทที่ธนาคารรับเป็นหลักประกัน.pdf` using `PyMuPDF`."
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "try:\n",
        "    import fitz\n",
        "except ImportError:\n",
        "    print(\"Installing PyMuPDF...\")\n",
        "    import os\n",
        "    os.system(\"python3 -m pip install PyMuPDF\")\n",
        "    import fitz\n",
        "\n",
        "pdf_path = \"/home/opc/vector-playground/documents/2.3.6.1 ทรัพย์สินประเภทที่ธนาคารรับเป็นหลักประกัน.pdf\"\n",
        "print(f\"Reading PDF: {pdf_path}\")\n",
        "\n",
        "doc = fitz.open(pdf_path)\n",
        "pdf_text = \"\"\n",
        "for page_num in range(len(doc)):\n",
        "    pdf_text += doc[page_num].get_text(\"text\") + \"\\n\"\n",
        "\n",
        "print(f\"Extracted {len(pdf_text)} characters from Thai PDF.\")"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 7. Chunk & Embed PDF Document\n",
        "We clear out previous chunks for a different ID (e.g., PDF_999) and store the PDF text."
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "pdf_customer_id = \"PDF_999\" # Dummy ID for the PDF chunks\n",
        "cursor.execute(\"DELETE FROM LOAN_CHUNK WHERE CUSTOMER_ID = :cust_id\", {'cust_id': pdf_customer_id})\n",
        "connection.commit()\n",
        "\n",
        "# Chunk the PDF text\n",
        "size = 50\n",
        "insert_sql = f\"\"\"\n",
        "    INSERT INTO LOAN_CHUNK (CUSTOMER_ID, CHUNK_ID, CHUNK_TEXT)\n",
        "    SELECT :cust_id,\n",
        "        :chunk_size + vc.chunk_offset,\n",
        "        vc.chunk_text\n",
        "    FROM (SELECT :rec_text AS txt FROM dual) s,\n",
        "        VECTOR_CHUNKS(\n",
        "        dbms_vector_chain.utl_to_text(s.txt)\n",
        "        BY words\n",
        "        MAX {size}\n",
        "        OVERLAP 0\n",
        "        SPLIT BY sentence\n",
        "        LANGUAGE american\n",
        "        NORMALIZE all\n",
        "        ) vc\n",
        "\"\"\"\n",
        "cursor.execute(insert_sql, {'cust_id': pdf_customer_id, 'chunk_size': size, 'rec_text': pdf_text})\n",
        "connection.commit()\n",
        "\n",
        "# Embed PDF Chunks\n",
        "cursor.execute(\"SELECT CHUNK_ID, CHUNK_TEXT FROM LOAN_CHUNK WHERE CUSTOMER_ID = :cust_id\", {'cust_id': pdf_customer_id})\n",
        "pdf_chunks = cursor.fetchall()\n",
        "\n",
        "print(f\"Generating embeddings for {len(pdf_chunks)} PDF chunks...\")\n",
        "for cid, ctext in pdf_chunks:\n",
        "    text = ctext.read() if hasattr(ctext, 'read') else ctext\n",
        "    embedding = model.encode(text or \"\").tolist()\n",
        "    vec_str = str(embedding)\n",
        "    \n",
        "    cursor.execute(\"\"\"\n",
        "        UPDATE LOAN_CHUNK\n",
        "           SET CHUNK_VECTOR = TO_VECTOR(:vec)\n",
        "         WHERE CUSTOMER_ID = :cust_id AND CHUNK_ID = :cid\n",
        "    \"\"\", {'cust_id': pdf_customer_id, 'cid': cid, 'vec': vec_str})\n",
        "\n",
        "connection.commit()\n",
        "print(\"✅ PDF chunking and embedding complete.\")"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 8. Querying the Thai PDF\n",
        "Now we can try searching for specific Thai rules within the KBank document."
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "pdf_question = \"ที่ดินเปล่าเพื่อการพาณิชย์และเพื่อที่อยู่อาศัยรับเป็นหลักประกันได้กี่เปอเซ็นต์?\"\n",
        "print(f\"Searching for: '{pdf_question}'\\n\")\n",
        "\n",
        "q_vec_pdf = model.encode(pdf_question).tolist()\n",
        "q_vec_str_pdf = str(q_vec_pdf)\n",
        "\n",
        "cursor.execute(\"\"\"\n",
        "    SELECT CHUNK_ID, CHUNK_TEXT, VECTOR_DISTANCE(CHUNK_VECTOR, TO_VECTOR(:qv), COSINE) as dist\n",
        "    FROM LOAN_CHUNK\n",
        "    WHERE CUSTOMER_ID = :cust_id\n",
        "    AND CHUNK_VECTOR IS NOT NULL\n",
        "    ORDER BY dist ASC\n",
        "    FETCH FIRST 3 ROWS ONLY\n",
        "\"\"\", {'cust_id': pdf_customer_id, 'qv': q_vec_str_pdf})\n",
        "\n",
        "retrieved_pdf = cursor.fetchall()\n",
        "\n",
        "for rank, row in enumerate(retrieved_pdf):\n",
        "    cid = row[0]\n",
        "    text = row[1].read() if hasattr(row[1], 'read') else row[1]\n",
        "    dist = row[2]\n",
        "    print(f\"⭐ Rank {rank+1} [Distance: {dist:.4f}] - Chunk {cid}\")\n",
        "    text_clean = text.strip().replace('\\n', ' ')\n",
        "    print(f\"   Text: {text_clean}\\n\")"
      ]
    }
]

# Append new cells
nb["cells"].extend(new_cells)

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=2)

print("Added PDF extraction and search to notebook.")
