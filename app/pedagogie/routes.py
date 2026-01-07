from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.extensions import db
from app.models import Referentiel, Competence, Objectif, Projet, AtelierActivite, SessionActivite, PresenceActivite, Evaluation

from . import bp


@bp.route("/referentiels", methods=["GET", "POST"])
@login_required
def referentiels_list():
    if request.method == "POST":
        action = request.form.get("action") or ""
        if action == "create_referentiel":
            nom = (request.form.get("nom") or "").strip()
            description = (request.form.get("description") or "").strip() or None
            if not nom:
                flash("Nom du référentiel obligatoire.", "danger")
                return redirect(url_for("pedagogie.referentiels_list"))
            ref = Referentiel(nom=nom, description=description)
            db.session.add(ref)
            db.session.commit()
            flash("Référentiel créé.", "success")
            return redirect(url_for("pedagogie.referentiels_list"))

        if action == "delete_referentiel":
            ref_id = int(request.form.get("referentiel_id") or 0)
            ref = Referentiel.query.get_or_404(ref_id)
            db.session.delete(ref)
            db.session.commit()
            flash("Référentiel supprimé.", "warning")
            return redirect(url_for("pedagogie.referentiels_list"))

    referentiels = Referentiel.query.order_by(Referentiel.nom.asc()).all()
    return render_template("pedagogie/referentiels.html", referentiels=referentiels)


@bp.route("/referentiels/<int:referentiel_id>", methods=["GET", "POST"])
@login_required
def referentiels_edit(referentiel_id: int):
    referentiel = Referentiel.query.get_or_404(referentiel_id)

    if request.method == "POST":
        action = request.form.get("action") or ""

        if action == "update_referentiel":
            referentiel.nom = (request.form.get("nom") or "").strip()
            referentiel.description = (request.form.get("description") or "").strip() or None
            if not referentiel.nom:
                flash("Nom obligatoire.", "danger")
                return redirect(url_for("pedagogie.referentiels_edit", referentiel_id=referentiel.id))
            db.session.commit()
            flash("Référentiel mis à jour.", "success")
            return redirect(url_for("pedagogie.referentiels_edit", referentiel_id=referentiel.id))

        if action == "add_competence":
            code = (request.form.get("code") or "").strip()
            nom = (request.form.get("nom") or "").strip()
            description = (request.form.get("description") or "").strip() or None
            if not code or not nom:
                flash("Code et nom de compétence obligatoires.", "danger")
                return redirect(url_for("pedagogie.referentiels_edit", referentiel_id=referentiel.id))
            comp = Competence(
                referentiel_id=referentiel.id,
                code=code,
                nom=nom,
                description=description,
            )
            db.session.add(comp)
            db.session.commit()
            flash("Compétence ajoutée.", "success")
            return redirect(url_for("pedagogie.referentiels_edit", referentiel_id=referentiel.id))

        if action == "delete_competence":
            comp_id = int(request.form.get("competence_id") or 0)
            comp = Competence.query.get_or_404(comp_id)
            if comp.referentiel_id != referentiel.id:
                flash("Compétence invalide.", "danger")
                return redirect(url_for("pedagogie.referentiels_edit", referentiel_id=referentiel.id))
            db.session.delete(comp)
            db.session.commit()
            flash("Compétence supprimée.", "warning")
            return redirect(url_for("pedagogie.referentiels_edit", referentiel_id=referentiel.id))

    competences = Competence.query.filter_by(referentiel_id=referentiel.id).order_by(Competence.code.asc()).all()
    return render_template(
        "pedagogie/referentiel_edit.html",
        referentiel=referentiel,
        competences=competences,
    )


@bp.route("/objectifs", methods=["GET", "POST"])
@login_required
def objectifs():
    projet_id = request.args.get("projet_id", type=int)
    atelier_id = request.args.get("atelier_id", type=int)
    session_id = request.args.get("session_id", type=int)

    if request.method == "POST":
        action = request.form.get("action") or ""
        if action == "create_objectif":
            obj_type = (request.form.get("type") or "").strip()
            titre = (request.form.get("titre") or "").strip()
            description = (request.form.get("description") or "").strip() or None
            seuil_validation = request.form.get("seuil_validation", type=float) or 0.0
            parent_id = request.form.get("parent_id", type=int)
            selected_session_id = request.form.get("session_id", type=int)
            selected_atelier_id = request.form.get("atelier_id", type=int)
            selected_projet_id = request.form.get("projet_id", type=int)

            if not obj_type or not titre:
                flash("Type et titre obligatoires.", "danger")
                return redirect(url_for("pedagogie.objectifs", projet_id=projet_id, atelier_id=atelier_id, session_id=session_id))

            obj = Objectif(
                type=obj_type,
                titre=titre,
                description=description,
                seuil_validation=seuil_validation,
                parent_id=parent_id,
                projet_id=selected_projet_id,
                atelier_id=selected_atelier_id,
                session_id=selected_session_id,
            )
            competence_ids = [int(cid) for cid in request.form.getlist("competence_ids") if cid.isdigit()]
            if competence_ids:
                obj.competences = Competence.query.filter(Competence.id.in_(competence_ids)).all()
            db.session.add(obj)
            db.session.commit()
            flash("Objectif ajouté.", "success")
            return redirect(url_for("pedagogie.objectifs", projet_id=selected_projet_id, atelier_id=selected_atelier_id, session_id=selected_session_id))

        if action == "delete_objectif":
            obj_id = int(request.form.get("objectif_id") or 0)
            obj = Objectif.query.get_or_404(obj_id)
            db.session.delete(obj)
            db.session.commit()
            flash("Objectif supprimé.", "warning")
            return redirect(url_for("pedagogie.objectifs", projet_id=projet_id, atelier_id=atelier_id, session_id=session_id))

    projets = Projet.query.order_by(Projet.secteur.asc(), Projet.nom.asc()).all()
    ateliers = AtelierActivite.query.filter(AtelierActivite.is_deleted.is_(False)).order_by(AtelierActivite.nom.asc()).all()
    sessions = SessionActivite.query.filter(SessionActivite.is_deleted.is_(False)).order_by(SessionActivite.created_at.desc()).all()
    referentiels = Referentiel.query.order_by(Referentiel.nom.asc()).all()

    objectifs = Objectif.query
    if projet_id:
        objectifs = objectifs.filter(Objectif.projet_id == projet_id)
    if atelier_id:
        objectifs = objectifs.filter(Objectif.atelier_id == atelier_id)
    if session_id:
        objectifs = objectifs.filter(Objectif.session_id == session_id)
    objectifs = objectifs.order_by(Objectif.created_at.asc()).all()

    def _participants_success_rate(session_id: int, competences: list[Competence]) -> dict:
        if not competences:
            return {"total": 0, "success": 0, "ratio": 0}
        presences = PresenceActivite.query.filter_by(session_id=session_id).all()
        total = len(presences)
        if total == 0:
            return {"total": 0, "success": 0, "ratio": 0}
        comp_ids = [c.id for c in competences]
        success_count = 0
        for pr in presences:
            evals = (
                Evaluation.query.filter(
                    Evaluation.session_id == session_id,
                    Evaluation.participant_id == pr.participant_id,
                    Evaluation.competence_id.in_(comp_ids),
                    Evaluation.etat >= 2,
                )
                .distinct()
                .count()
            )
            if evals == len(comp_ids):
                success_count += 1
        ratio = (success_count / total * 100) if total else 0
        return {"total": total, "success": success_count, "ratio": ratio}

    def _objective_success(obj: Objectif) -> dict:
        if obj.type == "operationnel" and obj.session_id:
            stats = _participants_success_rate(obj.session_id, obj.competences)
            validated = stats["ratio"] >= (obj.seuil_validation or 0)
            return {"ratio": stats["ratio"], "validated": validated, "total": stats["total"], "success": stats["success"]}

        enfants = obj.enfants or []
        if not enfants:
            return {"ratio": 0, "validated": False, "total": 0, "success": 0}
        results = [_objective_success(child) for child in enfants]
        total = len(results)
        success = sum(1 for r in results if r["validated"])
        ratio = (success / total * 100) if total else 0
        validated = ratio >= (obj.seuil_validation or 0)
        return {"ratio": ratio, "validated": validated, "total": total, "success": success}

    objectifs_stats = []
    for obj in objectifs:
        stats = _objective_success(obj)
        objectifs_stats.append({"objectif": obj, **stats})

    parent_options = Objectif.query.order_by(Objectif.created_at.asc()).all()

    return render_template(
        "pedagogie/objectifs.html",
        projets=projets,
        ateliers=ateliers,
        sessions=sessions,
        referentiels=referentiels,
        objectifs=objectifs_stats,
        parent_options=parent_options,
        projet_id=projet_id,
        atelier_id=atelier_id,
        session_id=session_id,
    )
