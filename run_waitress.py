from waitress import serve
from app import create_app

app = create_app()

print("🚀 Démarrage PRO (Compat. PostgreSQL & SQLite)")
print("👥 12 personnes MAX (12 threads)")

serve(
    app,
    host="0.0.0.0",
    port=5000,
    threads=12  # <--- IMPORTANT : 12, PAS 4 !
)