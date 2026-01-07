from app import create_app
from app.extensions import db
from app.models import User

ADMIN_EMAIL = "admin@asso.com"
ADMIN_PASS = "admin123!"

DIRECTRICE_EMAIL = "c.charpentierbrassens60@gmail.com"
DIRECTRICE_PASS = "Brassens1985!"

FINANCE_EMAIL = "s.khediribrassenscreil@gmail.com"
FINANCE_PASS = "Brassens1985!"

RESP_EMAIL = "a.vivien@cgbcreil.com"
RESP_PASS = "cGbCreil123!"
RESP_SECTEUR = "Numérique"

def upsert_user(email, nom, role, password, secteur=None):
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(email=email, nom=nom, role=role, secteur_assigne=secteur)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        print(f"✅ Créé: {email} ({role})")
        return

    u.nom = nom
    u.role = role
    u.secteur_assigne = secteur
    u.set_password(password)
    db.session.commit()
    print(f"✅ Mis à jour: {email} ({role})")

def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        upsert_user(ADMIN_EMAIL, "Admin Tech", "admin_tech", ADMIN_PASS, None)
        upsert_user(DIRECTRICE_EMAIL, "Directrice", "directrice", DIRECTRICE_PASS, None)
        upsert_user(FINANCE_EMAIL, "Finance", "finance", FINANCE_PASS, None)
        upsert_user(RESP_EMAIL, f"Resp Secteur ({RESP_SECTEUR})", "responsable_secteur", RESP_PASS, RESP_SECTEUR)

        print("\n--- IDENTIFIANTS ---")
        print(f"admin_tech : {ADMIN_EMAIL} / {ADMIN_PASS}")
        print(f"directrice : {DIRECTRICE_EMAIL} / {DIRECTRICE_PASS}")
        print(f"finance    : {FINANCE_EMAIL} / {FINANCE_PASS}")
        print(f"resp sect. : {RESP_EMAIL} / {RESP_PASS} (secteur={RESP_SECTEUR})")

if __name__ == "__main__":
    main()
