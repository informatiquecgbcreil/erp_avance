import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    Projet,
    Subvention,
    SubventionProjet,
    AtelierActivite,
    ProjetAtelier,
    ProjetIndicateur,
    Competence,
    Referentiel,
)

bp = Blueprint("projets", __name__)

ALLOWED_CR = {"pdf", "doc", "docx", "odt"}


INDICATOR_TEMPLATES = {
    'participants_uniques': 'Participants uniques',
    'presences_totales': 'Présences totales',
    'sessions_totales': 'Sessions réalisées',
    'recurrence_2plus': 'Participants récurrents (≥2 séances)',
    'depenses_totales': 'Dépenses totales (charges)',
    'recettes_totales': 'Recettes totales (produits)',
    'cout_par_participant': 'Coût par participant',
    'cout_par_presence': 'Coût par présence',
}


INDICATOR_PACKS = {
    "caf_base": {
        "label": "Pack CAF (base)",
        "codes": ["participants_uniques", "presences_totales", "sessions_totales", "recurrence_2plus"],
    },
    "financier": {
        "label": "Pack Financier",
        "codes": ["depenses_totales", "recettes_totales", "cout_par_participant", "cout_par_presence"],
    },
    "jeunesse": {
        "label": "Pack Jeunesse (simple)",
        "codes": ["participants_uniques", "recurrence_2plus"],
    },
}

PERIOD_CHOICES = {
    "context": "Période sélectionnée (défaut)",
    "year": "Année sélectionnée",
    "custom": "Personnalisée (dates)",
}

TARGET_OP_CHOICES = {
    "ge": "Atteindre au moins (≥)",
    "le": "Ne pas dépasser (≤)",
}


def can_see_secteur(secteur: str) -> bool:
    if current_user.role in ("directrice", "finance"):
        return True
    if current_user.role == "responsable_secteur":
        return current_user.secteur_assigne == secteur
    return False

def ensure_projets_folder():
    folder = os.path.join(current_app.root_path, "..", "static", "uploads", "projets")
    folder = os.path.abspath(folder)
    os.makedirs(folder, exist_ok=True)
    return folder

def allowed_cr(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_CR

@bp.route("/projets")
@login_required
def projets_list():
    if current_user.role == "admin_tech":
        abort(403)

    q = Projet.query
    if current_user.role == "responsable_secteur":
        q = q.filter(Projet.secteur == current_user.secteur_assigne)

    projets = q.order_by(Projet.created_at.desc()).all()
    secteurs = current_app.config.get("SECTEURS", [])
    return render_template("projets_list.html", projets=projets, secteurs=secteurs)

@bp.route("/projets/new", methods=["GET", "POST"])
@login_required
def projets_new():
    if current_user.role == "admin_tech":
        abort(403)

    secteurs = current_app.config.get("SECTEURS", [])

    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        secteur = (request.form.get("secteur") or "").strip()
        description = (request.form.get("description") or "").strip()

        if current_user.role == "responsable_secteur":
            secteur = current_user.secteur_assigne

        if not nom or not secteur:
            flash("Nom + secteur obligatoires.", "danger")
            return redirect(url_for("projets.projets_new"))

        if not can_see_secteur(secteur):
            abort(403)

        p = Projet(nom=nom, secteur=secteur, description=description)
        db.session.add(p)
        db.session.commit()

        flash("Projet créé.", "success")
        return redirect(url_for("projets.projets_edit", projet_id=p.id))

    return render_template("projets_new.html", secteurs=secteurs)


@bp.route("/projets/<int:projet_id>", methods=["GET", "POST"])
@login_required
def projets_edit(projet_id):
    if current_user.role == "admin_tech":
        abort(403)

    p = Projet.query.get_or_404(projet_id)
    if not can_see_secteur(p.secteur):
        abort(403)

    if request.method == "POST":
        action = request.form.get("action") or ""

        if action == "update":
            p.nom = (request.form.get("nom") or "").strip()
            p.description = (request.form.get("description") or "").strip()

            if not p.nom:
                flash("Nom obligatoire.", "danger")
                return redirect(url_for("projets.projets_edit", projet_id=p.id))

            db.session.commit()
            flash("Projet modifié.", "success")
            return redirect(url_for("projets.projets_edit", projet_id=p.id))

        if action == "update_competences":
            competence_ids = [int(cid) for cid in request.form.getlist("competence_ids") if cid.isdigit()]
            if competence_ids:
                p.competences = Competence.query.filter(Competence.id.in_(competence_ids)).all()
            else:
                p.competences = []
            db.session.commit()
            flash("Compétences du projet mises à jour.", "success")
            return redirect(url_for("projets.projets_edit", projet_id=p.id))

        if action == "upload_cr":
            file = request.files.get("cr_file")
            if not file or not file.filename:
                flash("Aucun fichier.", "danger")
                return redirect(url_for("projets.projets_edit", projet_id=p.id))

            if not allowed_cr(file.filename):
                flash("Type autorisé : pdf/doc/docx/odt", "danger")
                return redirect(url_for("projets.projets_edit", projet_id=p.id))

            folder = ensure_projets_folder()
            safe_original = secure_filename(file.filename)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            stored = secure_filename(f"P{p.id}_{ts}_{safe_original}")
            file.save(os.path.join(folder, stored))

            p.cr_filename = stored
            p.cr_original_name = safe_original
            db.session.commit()

            flash("Compte-rendu uploadé.", "success")
            return redirect(url_for("projets.projets_edit", projet_id=p.id))

        if action == "toggle_subvention":
            sub_id = int(request.form.get("subvention_id") or 0)
            s = Subvention.query.get_or_404(sub_id)

            if s.secteur != p.secteur:
                abort(400)

            link = SubventionProjet.query.filter_by(projet_id=p.id, subvention_id=s.id).first()
            if link:
                db.session.delete(link)
                db.session.commit()
                flash("Subvention retirée du projet.", "warning")
            else:
                db.session.add(SubventionProjet(projet_id=p.id, subvention_id=s.id))
                db.session.commit()
                flash("Subvention ajoutée au projet.", "success")

            return redirect(url_for("projets.projets_edit", projet_id=p.id))

        # ---- Liens projet <-> ateliers ----
        if action == "toggle_atelier":
            atelier_id = int(request.form.get("atelier_id") or 0)
            a = AtelierActivite.query.get_or_404(atelier_id)
            if a.secteur != p.secteur or a.is_deleted:
                abort(400)

            link = ProjetAtelier.query.filter_by(projet_id=p.id, atelier_id=a.id).first()
            if link:
                db.session.delete(link)
                db.session.commit()
                flash("Atelier délié du projet.", "warning")
            else:
                db.session.add(ProjetAtelier(projet_id=p.id, atelier_id=a.id))
                db.session.commit()
                flash("Atelier lié au projet.", "success")

            return redirect(url_for("projets.projets_edit", projet_id=p.id))

        # ---- Indicateurs projet ----

        if action == "add_pack":
            pack = (request.form.get("pack") or "").strip()
            cfg = INDICATOR_PACKS.get(pack)
            if not cfg:
                flash("Pack invalide.", "danger")
                return redirect(url_for("projets.projets_edit", projet_id=p.id))

            added = 0
            for code in cfg["codes"]:
                if code not in INDICATOR_TEMPLATES:
                    continue
                exists = ProjetIndicateur.query.filter_by(projet_id=p.id, code=code).first()
                if exists:
                    continue
                db.session.add(ProjetIndicateur(
                    projet_id=p.id,
                    code=code,
                    label=INDICATOR_TEMPLATES.get(code, code),
                    is_active=True,
                    params_json=None,
                ))
                added += 1
            db.session.commit()
            flash(f"Pack ajouté ({added} indicateur(s)).", "success")
            return redirect(url_for("projets.projets_edit", projet_id=p.id))

        if action == "add_indicateur":
            code = (request.form.get("code") or "").strip()
            label = (request.form.get("label") or "").strip()
            if code not in INDICATOR_TEMPLATES:
                flash("Indicateur invalide.", "danger")
                return redirect(url_for("projets.projets_edit", projet_id=p.id))
            if not label:
                label = INDICATOR_TEMPLATES[code]

            exists = ProjetIndicateur.query.filter_by(projet_id=p.id, code=code).first()
            if exists:
                flash("Indicateur déjà présent pour ce projet.", "warning")
                return redirect(url_for("projets.projets_edit", projet_id=p.id))

            db.session.add(ProjetIndicateur(projet_id=p.id, code=code, label=label, is_active=True))
            db.session.commit()
            flash("Indicateur ajouté.", "success")
            return redirect(url_for("projets.projets_edit", projet_id=p.id))

        if action == "toggle_indicateur":
            indic_id = int(request.form.get("indicateur_id") or 0)
            ind = ProjetIndicateur.query.get_or_404(indic_id)
            if ind.projet_id != p.id:
                abort(400)
            ind.is_active = not bool(ind.is_active)
            db.session.commit()
            flash("Indicateur mis à jour.", "success")
            return redirect(url_for("projets.projets_edit", projet_id=p.id))

        if action == "save_indicateur":
            indic_id = int(request.form.get("indicateur_id") or 0)
            ind = ProjetIndicateur.query.get_or_404(indic_id)
            if ind.projet_id != p.id:
                abort(400)

            # label editable (optionnel)
            label = (request.form.get("label") or "").strip()
            if label:
                ind.label = label

            period = (request.form.get("period") or "context").strip()
            if period not in PERIOD_CHOICES:
                period = "context"

            target_raw = (request.form.get("target") or "").strip().replace(",", ".")
            target = None
            if target_raw:
                try:
                    target = float(target_raw)
                except ValueError:
                    target = None

            target_op = (request.form.get("target_op") or "ge").strip()
            if target_op not in TARGET_OP_CHOICES:
                target_op = "ge"

            atelier_id_raw = (request.form.get("atelier_id") or "").strip()
            atelier_id = None
            if atelier_id_raw:
                try:
                    atelier_id = int(atelier_id_raw)
                except ValueError:
                    atelier_id = None

            # bornes custom
            start = (request.form.get("start") or "").strip()
            end = (request.form.get("end") or "").strip()

            params = ind.params()
            params.update({
                "period": period,
                "target": target,
                "target_op": target_op,
                "atelier_id": atelier_id,
                "start": start if period == "custom" else None,
                "end": end if period == "custom" else None,
            })
            # nettoyage
            if params.get("atelier_id") is None:
                params.pop("atelier_id", None)
            if params.get("target") is None:
                params.pop("target", None)
            if period != "custom":
                params.pop("start", None)
                params.pop("end", None)

            ind.params_json = json.dumps(params, ensure_ascii=False)
            db.session.commit()
            flash("Paramètres de l'indicateur enregistrés.", "success")
            return redirect(url_for("projets.projets_edit", projet_id=p.id))


        if action == "delete_indicateur":
            indic_id = int(request.form.get("indicateur_id") or 0)
            ind = ProjetIndicateur.query.get_or_404(indic_id)
            if ind.projet_id != p.id:
                abort(400)
            db.session.delete(ind)
            db.session.commit()
            flash("Indicateur supprimé.", "warning")
            return redirect(url_for("projets.projets_edit", projet_id=p.id))

        abort(400)

    # ----- GET (lists) -----
    subs_q = Subvention.query.filter_by(est_archive=False).filter(Subvention.secteur == p.secteur)
    subs = subs_q.order_by(Subvention.annee_exercice.desc(), Subvention.nom.asc()).all()
    linked_subs = set(sp.subvention_id for sp in p.subventions)

    ateliers = AtelierActivite.query.filter_by(secteur=p.secteur, is_deleted=False).order_by(AtelierActivite.nom.asc()).all()
    linked_ateliers = set(link.atelier_id for link in ProjetAtelier.query.filter_by(projet_id=p.id).all())

    indicateurs = ProjetIndicateur.query.filter_by(projet_id=p.id).order_by(ProjetIndicateur.created_at.asc()).all()
    referentiels = Referentiel.query.order_by(Referentiel.nom.asc()).all()
    selected_competences = {c.id for c in p.competences}

    return render_template(
        "projets_edit.html",
        projet=p,
        subs=subs,
        linked=linked_subs,
        ateliers=ateliers,
        linked_ateliers=linked_ateliers,
        indicateurs=indicateurs,
        indicator_templates=INDICATOR_TEMPLATES,
        indicator_packs=INDICATOR_PACKS,
        period_choices=PERIOD_CHOICES,
        target_op_choices=TARGET_OP_CHOICES,
        referentiels=referentiels,
        selected_competences=selected_competences,
    )

@bp.route("/projets/cr/<int:projet_id>/download")
@login_required
def projets_cr_download(projet_id):
    if current_user.role == "admin_tech":
        abort(403)

    p = Projet.query.get_or_404(projet_id)
    if not can_see_secteur(p.secteur):
        abort(403)

    if not p.cr_filename:
        abort(404)

    folder = ensure_projets_folder()
    return send_from_directory(folder, p.cr_filename, as_attachment=True, download_name=(p.cr_original_name or p.cr_filename))
