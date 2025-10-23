import psycopg2
from psycopg2.extras import execute_values
import numpy as np

DB_URI = "postgresql://postgres:0987654321@localhost:5432/DocAI"

def test_postgres_vector_db():
    conn, cursor = None, None
    try:
        print("🔍 Connecting to PostgreSQL...")
        conn = psycopg2.connect(DB_URI)
        cursor = conn.cursor()
        print("✅ Connection successful!")

        # Step 1: Check pgvector extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cursor.execute("SELECT extname FROM pg_extension WHERE extname='vector';")
        if cursor.fetchone():
            print("✅ pgvector extension available.")
        else:
            raise Exception("pgvector extension not found!")

        # Step 2: Drop old test table if exists
        cursor.execute("DROP TABLE IF EXISTS test_vectors;")

        # Step 3: Create test table
        cursor.execute("""
            CREATE TABLE test_vectors (
                id SERIAL PRIMARY KEY,
                description TEXT,
                embedding vector(5)
            );
        """)
        print("✅ Test table created.")

        # Step 4: Insert test embeddings
        print("📥 Inserting test vectors...")
        test_data = [
            ("Heart rate check", np.random.rand(5).tolist()),
            ("Blood sugar levels", np.random.rand(5).tolist()),
            ("Cholesterol report", np.random.rand(5).tolist())
        ]
        execute_values(cursor,
                       "INSERT INTO test_vectors (description, embedding) VALUES %s",
                       [(desc, vector) for desc, vector in test_data])
        conn.commit()
        print("✅ Inserted 3 records successfully.")

        # Step 5: Fetch one
        cursor.execute("SELECT * FROM test_vectors LIMIT 1;")
        print("📄 Sample record:", cursor.fetchone())

        # Step 6: Run similarity search
        print("🔎 Running vector similarity search...")
        test_vec = np.random.rand(5).tolist()
        cursor.execute("""
            SELECT description, embedding <-> %s::vector AS distance
            FROM test_vectors
            ORDER BY distance ASC
            LIMIT 3;
        """, (test_vec,))
        print("🔢 Similarity results:")
        for row in cursor.fetchall():
            print("  →", row)

        print("\n🎉 PostgreSQL + pgvector test successful!")

    except Exception as e:
        print("❌ Error during test:", e)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    test_postgres_vector_db()
    
