from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User

bp = Blueprint("admin", __name__, url_prefix="/admin")

def is_admin_tech():
    return current_user.is_authenticated and current_user.role == "admin_tech"

@bp.route("/users", methods=["GET", "POST"])
@login_required
def users():
    if not is_admin_tech():
        abort(403)

    secteurs = current_app.config.get("SECTEURS", [])

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        nom = (request.form.get("nom") or "").strip()
        role = (request.form.get("role") or "").strip()
        secteur = (request.form.get("secteur_assigne") or "").strip() or None
        password = (request.form.get("password") or "").strip()

        if not email or not nom or not role or not password:
            flash("Email, nom, rôle, mot de passe obligatoires.", "danger")
            return redirect(url_for("admin.users"))

        if User.query.filter_by(email=email).first():
            flash("Email déjà utilisé.", "danger")
            return redirect(url_for("admin.users"))

        u = User(email=email, nom=nom, role=role, secteur_assigne=secteur)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        flash("Utilisateur créé.", "success")
        return redirect(url_for("admin.users"))

    users = User.query.order_by(User.role.asc(), User.nom.asc()).all()
    return render_template("admin_users.html", users=users, secteurs=secteurs)

@bp.route("/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if not is_admin_tech():
        abort(403)

    if current_user.id == user_id:
        flash("Tu peux pas te supprimer toi-même.", "danger")
        return redirect(url_for("admin.users"))

    u = User.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()

    flash("Utilisateur supprimé.", "warning")
    return redirect(url_for("admin.users"))
