import json

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Oracle AI Database Vector Search\n",
                "This notebook implements the Vector Search portion of the lab, completely skipping the OCI GenAI requirement. It uses the Oracle DB wallet connection details you provided."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "import shutil\n",
                "import oracledb\n",
                "import pandas as pd\n",
                "import json\n",
                "\n",
                "# Connection Configurations\n",
                "username = \"ADMIN\"\n",
                "password = \"ppPPPP__253fSEDF8675__3fcdvbj\"\n",
                "dsn = \"adbforailowercost_high\"\n",
                "wallet_zip = \"/home/opc/vector-playground/Wallet_ADBforAIlowerCost_22-Feb-2026.zip\"\n",
                "wallet_dir = \"/home/opc/vector-playground/wallet\"\n",
                "\n",
                "# Unzip wallet if not already done\n",
                "if not os.path.exists(wallet_dir):\n",
                "    print(f\"Unzipping wallet to {wallet_dir}...\")\n",
                "    import zipfile\n",
                "    with zipfile.ZipFile(wallet_zip, 'r') as zip_ref:\n",
                "        zip_ref.extractall(wallet_dir)\n",
                "    print(\"✅ Wallet unzipped.\")\n",
                "else:\n",
                "    print(f\"✅ Wallet directory already exists at {wallet_dir}\")\n",
                "\n",
                "print(\"Connecting to Oracle Database...\")\n",
                "try:\n",
                "    # Thin mode connection with wallet\n",
                "    connection = oracledb.connect(\n",
                "        user=username,\n",
                "        password=password,\n",
                "        dsn=dsn,\n",
                "        config_dir=wallet_dir,\n",
                "        wallet_location=wallet_dir,\n",
                "        wallet_password=password\n",
                "    )\n",
                "    print(\"✅ Connection successful!\")\n",
                "except Exception as e:\n",
                "    print(f\"❌ Connection failed: {e}\")\n",
                "\n",
                "cursor = connection.cursor()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. Fetch Customer Data\n",
                "Queries the `clients_dv` duality view to verify data connectivity and fetch customer `CUST_1000`."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "def fetch_customer_data(customer_id):\n",
                "    cursor.execute(\n",
                "        \"SELECT data FROM customers_dv WHERE JSON_VALUE(data, '$._id') = :customer_id\",\n",
                "        {'customer_id': customer_id}\n",
                "    )\n",
                "    result = cursor.fetchone()\n",
                "    if not result: return None\n",
                "    # Handle CLOB read\n",
                "    val = result[0].read() if hasattr(result[0], 'read') else result[0]\n",
                "    return json.loads(val) if isinstance(val, str) else val\n",
                "\n",
                "selected_customer_id = 100001\n",
                "customer_json = fetch_customer_data(selected_customer_id)\n",
                "\n",
                "if customer_json:\n",
                "    print(f\"Found Customer Info: {customer_json.get('FirstName', '')} {customer_json.get('LastName', '')}\")\n",
                "else:\n",
                "    print(\"Warning: Customer 100001 not found. Did you run the 'setup_db.py' script from the lab?\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. Prepare Mock Recommendation Text\n",
                "Since we are skipping OCI GenAI, we're providing a localized dummy response to chunk, store, and vectorize."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "mock_recommendation = \"\"\"\n",
                "1. Comprehensive Evaluation\n",
                "James Smith has a solid credit score but quite a bit of existing debt. The combination of income and credit history makes James a reasonable candidate for several loan types.\n",
                "\n",
                "2. Top 3 Loan Recommendations\n",
                "- Loan A: 30-Year Fixed Mortgage at 6.5% interest. Ideal for stable, long-term payments.\n",
                "- Loan B: 15-Year Fixed Mortgage at 5.8% interest. Better interest rate but higher monthly payments.\n",
                "- Loan C: FHA Loan at 6.0% interest. Good for first-time buyers with lower down payment requirements.\n",
                "\n",
                "3. Recommendations Explanations\n",
                "The 30-year fixed is recommended because it keeps the monthly payment affordable given the existing debt-to-income ratio. The 15-year is presented as a faster payoff alternative.\n",
                "\n",
                "4. Final Suggestion\n",
                "We suggest proceeding with Loan A (30-Year Fixed) so that James has a comfortable emergency buffer in his monthly budget.\n",
                "\"\"\"\n",
                "print(\"✅ Mock recommendation prepared.\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. Chunk and Store the Document\n",
                "We chunk the text into multiple smaller blocks using Oracle's `VECTOR_CHUNKS` function, and store it."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Clean any prior chunks for this customer\n",
                "cursor.execute(\"DELETE FROM LOAN_CHUNK WHERE CUSTOMER_ID = :cust_id\", {'cust_id': selected_customer_id})\n",
                "connection.commit()\n",
                "\n",
                "chunk_sizes = [50]\n",
                "\n",
                "# Insert chunks\n",
                "for size in chunk_sizes:\n",
                "    insert_sql = f\"\"\"\n",
                "        INSERT INTO LOAN_CHUNK (CUSTOMER_ID, CHUNK_ID, CHUNK_TEXT)\n",
                "        SELECT :cust_id,\n",
                "            :chunk_size + vc.chunk_offset,\n",
                "            vc.chunk_text\n",
                "        FROM (SELECT :rec_text AS txt FROM dual) s,\n",
                "            VECTOR_CHUNKS(\n",
                "            dbms_vector_chain.utl_to_text(s.txt)\n",
                "            BY words\n",
                "            MAX {size}\n",
                "            OVERLAP 0\n",
                "            SPLIT BY sentence\n",
                "            LANGUAGE american\n",
                "            NORMALIZE all\n",
                "            ) vc\n",
                "    \"\"\"\n",
                "    cursor.execute(\n",
                "        insert_sql,\n",
                "        {'cust_id': selected_customer_id, 'chunk_size': size, 'rec_text': mock_recommendation}\n",
                "    )\n",
                "\n",
                "# Fetch chunks to verify\n",
                "cursor.execute(\"\"\"\n",
                "SELECT CHUNK_ID, CHUNK_TEXT\n",
                "  FROM LOAN_CHUNK\n",
                " WHERE CUSTOMER_ID = :cust_id\n",
                "  ORDER BY CHUNK_ID\n",
                "\"\"\", {'cust_id': selected_customer_id})\n",
                "rows = cursor.fetchall()\n",
                "\n",
                "items = []\n",
                "for cid, ctext in rows:\n",
                "    txt = ctext.read() if hasattr(ctext, 'read') else ctext\n",
                "    txt = txt or \"\"\n",
                "    items.append({\n",
                "        \"CHUNK_ID\": cid,\n",
                "        \"Chars\": len(txt),\n",
                "        \"Preview\": (txt[:100] + \"...\") if len(txt) > 100 else txt\n",
                "    })\n",
                "\n",
                "df_chunks = pd.DataFrame(items)\n",
                "connection.commit()\n",
                "print(\"✅ Chunking complete!\")\n",
                "display(df_chunks)"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4. DB Data Embedding\n",
                "Since the `DEMO_MODEL` ONNX model is missing from the database, we'll generate the vector embeddings locally in Python using `sentence-transformers`, and upload those vector arrays directly into the Oracle database `VECTOR` column."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "try:\n",
                "    from sentence_transformers import SentenceTransformer\n",
                "except ImportError:\n",
                "    print(\"Installing sentence-transformers...\")\n",
                "    import os\n",
                "    os.system(\"python3 -m pip install sentence-transformers\")\n",
                "    from sentence_transformers import SentenceTransformer\n",
                "\n",
                "print(\"Loading lightweight embedding model locally...\")\n",
                "model = SentenceTransformer('all-MiniLM-L6-v2')\n",
                "\n",
                "print(\"Fetching chunks to embed...\")\n",
                "cursor.execute(\"SELECT CHUNK_ID, CHUNK_TEXT FROM LOAN_CHUNK WHERE CUSTOMER_ID = :cust_id\", {'cust_id': selected_customer_id})\n",
                "chunks = cursor.fetchall()\n",
                "\n",
                "print(f\"Generating embeddings for {len(chunks)} chunks...\")\n",
                "for cid, ctext in chunks:\n",
                "    text = ctext.read() if hasattr(ctext, 'read') else ctext\n",
                "    # Generate 384-dimensional vector and convert to string for Oracle\n",
                "    embedding = model.encode(text).tolist()\n",
                "    vec_str = str(embedding)\n",
                "    \n",
                "    # Update the row with the new vector array\n",
                "    cursor.execute(\"\"\"\n",
                "        UPDATE LOAN_CHUNK\n",
                "           SET CHUNK_VECTOR = TO_VECTOR(:vec)\n",
                "         WHERE CUSTOMER_ID = :cust_id AND CHUNK_ID = :cid\n",
                "    \"\"\", {'cust_id': selected_customer_id, 'cid': cid, 'vec': vec_str})\n",
                "    \n",
                "connection.commit()\n",
                "print(\"✅ Local vectorization and DB update complete.\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 5. Vector Search against the Embeddings\n",
                "We use the same local model to vectorize our search question, and query the DB using `.VECTOR_DISTANCE()`."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "question = \"Which loan do you suggest for a faster payoff and what is the interest rate?\"\n",
                "print(f\"Searching for: '{question}'\\n\")\n",
                "\n",
                "# Vectorize the query locally and convert to string for Oracle\n",
                "q_vec = model.encode(question).tolist()\n",
                "q_vec_str = str(q_vec)\n",
                "\n",
                "# Perform similarity search in database \n",
                "cursor.execute(\"\"\"\n",
                "    SELECT CHUNK_ID, CHUNK_TEXT, VECTOR_DISTANCE(CHUNK_VECTOR, TO_VECTOR(:qv), COSINE) as dist\n",
                "    FROM LOAN_CHUNK\n",
                "    WHERE CUSTOMER_ID = :cust_id\n",
                "    AND CHUNK_VECTOR IS NOT NULL\n",
                "    ORDER BY dist ASC\n",
                "    FETCH FIRST 3 ROWS ONLY\n",
                "\"\"\", {'cust_id': selected_customer_id, 'qv': q_vec_str})\n",
                "\n",
                "retrieved = cursor.fetchall()\n",
                "\n",
                "for rank, row in enumerate(retrieved):\n",
                "    cid = row[0]\n",
                "    text = row[1].read() if hasattr(row[1], 'read') else row[1]\n",
                "    dist = row[2]\n",
                "    print(f\"⭐ Rank {rank+1} [Distance: {dist:.4f}] - Chunk {cid}\")\n",
                "    print(f\"   Text: {text.strip().replace('\\n', ' ')}\\n\")"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.9.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

with open('/home/opc/vector-playground/oracle_vector_search_only.ipynb', 'w') as f:
    json.dump(notebook, f, indent=2)

print("Notebook generated successfully!")
