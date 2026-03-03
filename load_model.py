import oracledb

username = "ADMIN"
password = "ppPPPP__253fSEDF8675__3fcdvbj"
dsn = "adbforailowercost_high"
wallet_dir = "/home/opc/vector-playground/wallet"
model_path = "/home/opc/vector-playground/all-MiniLM-L6-v2.onnx"
model_name = "DEMO_MODEL"

print("Connecting to Oracle Database...")
try:
    connection = oracledb.connect(
        user=username, password=password, dsn=dsn,
        config_dir=wallet_dir, wallet_location=wallet_dir, wallet_password=password
    )
    print("✅ Connection successful!")
    
    with connection.cursor() as cursor:
        print(f"Loading ONNX model '{model_name}' into database from {model_path}...")
        cursor.execute(f"BEGIN DBMS_VECTOR.DROP_ONNX_MODEL('{model_name}', TRUE); EXCEPTION WHEN OTHERS THEN NULL; END;")
        
        # In newer Oracle versions, dbms_vector.load_onnx_model takes a directory object.
        # But we can also use DBMS_VECTOR_CHAIN if available, or just load it via a file.
        # Wait, the best way for a user without directory access is uploading via the Python driver's load_onnx_model if supported,
        # but let's try the standard way. Currently, oracledb doesn't have a direct helper, so we might need a DIRECTORY object.
        # If we can't create a directory, ADB provides DBMS_CLOUD or similar to load from object store.
        pass

except Exception as e:
    print(f"❌ Error: {e}")
