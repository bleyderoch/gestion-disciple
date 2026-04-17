"""
Application de gestion du disciple au sein de l'assemblée de famille.
Auteur : généré pour Roch Bleyde
"""
import os
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort
)
from flask_sqlalchemy import SQLAlchemy

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")

# Base de données : PostgreSQL en prod, SQLite en local
db_url = os.environ.get("DATABASE_URL", "sqlite:///disciples.db")
# Render.com retourne postgres:// qu'il faut transformer en postgresql://
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Credentials de l'assemblée (modifiable via variables d'environnement)
APP_USERNAME = os.environ.get("APP_USERNAME", "assemblee")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "assemblee2026")

db = SQLAlchemy(app)


# ----------------------------------------------------------------------------
# Modèles
# ----------------------------------------------------------------------------
class Disciple(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(50), unique=True, nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    tel = db.Column(db.String(30))
    lieu_habitation = db.Column(db.String(200))
    lien_plan_domicile = db.Column(db.String(500))  # URL externe (Drive, etc.)
    zone = db.Column(db.String(100))
    sous_centre = db.Column(db.String(100))
    assemblee = db.Column(db.String(100))

    # Faiseur de disciple
    faiseur_nom = db.Column(db.String(200))
    faiseur_contact = db.Column(db.String(30))

    # Mentore
    mentore_nom = db.Column(db.String(100))
    mentore_prenom = db.Column(db.String(100))
    mentore_tel = db.Column(db.String(30))
    mentore_qualite = db.Column(db.String(30))  # Pasteur / Missionnaire / Disciple

    # Statut spirituel
    repentance = db.Column(db.Boolean, default=False)
    bapteme = db.Column(db.Boolean, default=False)
    date_bapteme = db.Column(db.Date)
    brisement_liens = db.Column(db.Boolean, default=False)
    formation_disciple = db.Column(db.Boolean, default=False)

    # Niveau académique
    niveau_academique = db.Column(db.String(50))  # Analphabete/CM2/BAC/Superieur
    details_niveau = db.Column(db.String(200))    # Précisions (avec CPE, avec BAC, diplôme)
    lien_cv = db.Column(db.String(500))           # URL du CV

    cree_le = db.Column(db.DateTime, default=datetime.utcnow)

    amis = db.relationship("Ami", backref="disciple", cascade="all, delete-orphan", lazy="dynamic")
    familles = db.relationship("Famille", backref="disciple", cascade="all, delete-orphan", lazy="dynamic")
    adorations = db.relationship("Adoration", backref="disciple", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenom}"


class Ami(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disciple_id = db.Column(db.Integer, db.ForeignKey("disciple.id"), nullable=False)
    nom_prenoms = db.Column(db.String(200), nullable=False)
    tel = db.Column(db.String(30))
    lieu_habitation = db.Column(db.String(200))


class Famille(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disciple_id = db.Column(db.Integer, db.ForeignKey("disciple.id"), nullable=False)
    nom_famille = db.Column(db.String(200), nullable=False)  # Père / Mère
    tel = db.Column(db.String(30))
    lieu_habitation = db.Column(db.String(200))


class Evangeliste(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    tel = db.Column(db.String(30))
    zone = db.Column(db.String(100))
    sous_centre = db.Column(db.String(100))
    assemblee = db.Column(db.String(100))
    qualite = db.Column(db.String(30))  # Pasteur / Missionnaire / Disciple
    cree_le = db.Column(db.DateTime, default=datetime.utcnow)

    rdvs = db.relationship("RDVEvangelisation", backref="evangeliste", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenom}"


class RDVEvangelisation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evangeliste_id = db.Column(db.Integer, db.ForeignKey("evangeliste.id"), nullable=False)
    numero_semaine = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False, default=lambda: date.today().year)
    jour = db.Column(db.String(10))      # L/M/M/J/V/S/D
    heure = db.Column(db.String(10))
    type_ame = db.Column(db.String(20))  # Ami / Famille
    nom_ame = db.Column(db.String(200), nullable=False)
    tel_ame = db.Column(db.String(30))
    lieu_rdv = db.Column(db.String(200))
    statut_rdv = db.Column(db.String(10), default="NOK")         # OK / NOK
    statut_engagement = db.Column(db.String(10), default="NOK")  # OK / NOK
    cree_le = db.Column(db.DateTime, default=datetime.utcnow)


class Adoration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disciple_id = db.Column(db.Integer, db.ForeignKey("disciple.id"), nullable=False)
    numero_semaine = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    date_dimanche = db.Column(db.Date, nullable=False)
    present = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint("disciple_id", "date_dimanche", name="uq_disciple_dimanche"),
    )


# ----------------------------------------------------------------------------
# Auth très simple (compte unique d'assemblée)
# ----------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        if u == APP_USERNAME and p == APP_PASSWORD:
            session["logged_in"] = True
            session.permanent = True
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        flash("Identifiant ou mot de passe incorrect.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for("login"))


# ----------------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    nb_disciples = Disciple.query.count()
    nb_evangelistes = Evangeliste.query.count()

    today = date.today()
    iso_week = today.isocalendar()[1]

    rdvs_semaine = RDVEvangelisation.query.filter_by(
        numero_semaine=iso_week, annee=today.year
    ).all()
    rdv_total = len(rdvs_semaine)
    rdv_ok = sum(1 for r in rdvs_semaine if r.statut_rdv == "OK")
    eng_ok = sum(1 for r in rdvs_semaine if r.statut_engagement == "OK")

    taux_rdv = round(rdv_ok / rdv_total * 100, 1) if rdv_total else 0
    taux_eng = round(eng_ok / rdv_total * 100, 1) if rdv_total else 0

    # Dernières présences enregistrées (dimanche courant)
    presences = Adoration.query.filter_by(date_dimanche=last_sunday()).all()
    pres_total = len(presences)
    pres_ok = sum(1 for p in presences if p.present)
    taux_presence = round(pres_ok / pres_total * 100, 1) if pres_total else 0

    return render_template(
        "dashboard.html",
        nb_disciples=nb_disciples,
        nb_evangelistes=nb_evangelistes,
        rdv_total=rdv_total,
        rdv_ok=rdv_ok,
        eng_ok=eng_ok,
        taux_rdv=taux_rdv,
        taux_eng=taux_eng,
        pres_total=pres_total,
        pres_ok=pres_ok,
        taux_presence=taux_presence,
        semaine=iso_week,
        annee=today.year,
    )


def last_sunday():
    today = date.today()
    # weekday : lundi=0 ... dimanche=6
    days_since_sunday = (today.weekday() + 1) % 7
    from datetime import timedelta
    return today - timedelta(days=days_since_sunday)


# ----------------------------------------------------------------------------
# Disciples
# ----------------------------------------------------------------------------
@app.route("/disciples")
@login_required
def disciples_list():
    q = request.args.get("q", "").strip()
    query = Disciple.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Disciple.nom.ilike(like))
            | (Disciple.prenom.ilike(like))
            | (Disciple.matricule.ilike(like))
            | (Disciple.tel.ilike(like))
        )
    disciples = query.order_by(Disciple.nom, Disciple.prenom).all()
    return render_template("disciples_list.html", disciples=disciples, q=q)


@app.route("/disciples/nouveau", methods=["GET", "POST"])
@app.route("/disciples/<int:disciple_id>/editer", methods=["GET", "POST"])
@login_required
def disciple_form(disciple_id=None):
    d = Disciple.query.get(disciple_id) if disciple_id else None

    if request.method == "POST":
        if d is None:
            d = Disciple()
            db.session.add(d)

        d.matricule = request.form.get("matricule", "").strip()
        d.nom = request.form.get("nom", "").strip()
        d.prenom = request.form.get("prenom", "").strip()
        d.tel = request.form.get("tel", "").strip()
        d.lieu_habitation = request.form.get("lieu_habitation", "").strip()
        d.lien_plan_domicile = request.form.get("lien_plan_domicile", "").strip()
        d.zone = request.form.get("zone", "").strip()
        d.sous_centre = request.form.get("sous_centre", "").strip()
        d.assemblee = request.form.get("assemblee", "").strip()

        d.faiseur_nom = request.form.get("faiseur_nom", "").strip()
        d.faiseur_contact = request.form.get("faiseur_contact", "").strip()
        d.mentore_nom = request.form.get("mentore_nom", "").strip()
        d.mentore_prenom = request.form.get("mentore_prenom", "").strip()
        d.mentore_tel = request.form.get("mentore_tel", "").strip()
        d.mentore_qualite = request.form.get("mentore_qualite", "")

        d.repentance = bool(request.form.get("repentance"))
        d.bapteme = bool(request.form.get("bapteme"))
        db_date = request.form.get("date_bapteme", "").strip()
        d.date_bapteme = datetime.strptime(db_date, "%Y-%m-%d").date() if db_date else None
        d.brisement_liens = bool(request.form.get("brisement_liens"))
        d.formation_disciple = bool(request.form.get("formation_disciple"))

        d.niveau_academique = request.form.get("niveau_academique", "")
        d.details_niveau = request.form.get("details_niveau", "").strip()
        d.lien_cv = request.form.get("lien_cv", "").strip()

        # Amis (max 10)
        # On supprime les anciens puis on recrée
        if d.id:
            for a in d.amis.all():
                db.session.delete(a)
            for f in d.familles.all():
                db.session.delete(f)

        for i in range(10):
            nom = request.form.get(f"ami_nom_{i}", "").strip()
            if nom:
                ami = Ami(
                    disciple=d,
                    nom_prenoms=nom,
                    tel=request.form.get(f"ami_tel_{i}", "").strip(),
                    lieu_habitation=request.form.get(f"ami_lieu_{i}", "").strip(),
                )
                db.session.add(ami)

        for i in range(5):
            nom = request.form.get(f"fam_nom_{i}", "").strip()
            if nom:
                fam = Famille(
                    disciple=d,
                    nom_famille=nom,
                    tel=request.form.get(f"fam_tel_{i}", "").strip(),
                    lieu_habitation=request.form.get(f"fam_lieu_{i}", "").strip(),
                )
                db.session.add(fam)

        try:
            db.session.commit()
            flash(f"Disciple {d.nom_complet} enregistré avec succès.", "success")
            return redirect(url_for("disciples_list"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur : {e}", "danger")

    return render_template("disciple_form.html", d=d)


@app.route("/disciples/<int:disciple_id>")
@login_required
def disciple_detail(disciple_id):
    d = Disciple.query.get_or_404(disciple_id)
    # Assiduité
    adorations = Adoration.query.filter_by(disciple_id=d.id).order_by(Adoration.date_dimanche.desc()).all()
    total_ad = len(adorations)
    nb_presences = sum(1 for a in adorations if a.present)
    taux_presence = round(nb_presences / total_ad * 100, 1) if total_ad else 0
    return render_template(
        "disciple_detail.html",
        d=d, adorations=adorations,
        total_ad=total_ad, nb_presences=nb_presences,
        taux_presence=taux_presence,
    )


@app.route("/disciples/<int:disciple_id>/supprimer", methods=["POST"])
@login_required
def disciple_delete(disciple_id):
    d = Disciple.query.get_or_404(disciple_id)
    nom = d.nom_complet
    db.session.delete(d)
    db.session.commit()
    flash(f"Disciple {nom} supprimé.", "info")
    return redirect(url_for("disciples_list"))


# ----------------------------------------------------------------------------
# Évangélistes
# ----------------------------------------------------------------------------
@app.route("/evangelistes")
@login_required
def evangelistes_list():
    evangelistes = Evangeliste.query.order_by(Evangeliste.nom, Evangeliste.prenom).all()
    return render_template("evangelistes_list.html", evangelistes=evangelistes)


@app.route("/evangelistes/nouveau", methods=["GET", "POST"])
@app.route("/evangelistes/<int:evangeliste_id>/editer", methods=["GET", "POST"])
@login_required
def evangeliste_form(evangeliste_id=None):
    e = Evangeliste.query.get(evangeliste_id) if evangeliste_id else None
    if request.method == "POST":
        if e is None:
            e = Evangeliste()
            db.session.add(e)
        e.nom = request.form.get("nom", "").strip()
        e.prenom = request.form.get("prenom", "").strip()
        e.tel = request.form.get("tel", "").strip()
        e.zone = request.form.get("zone", "").strip()
        e.sous_centre = request.form.get("sous_centre", "").strip()
        e.assemblee = request.form.get("assemblee", "").strip()
        e.qualite = request.form.get("qualite", "")
        db.session.commit()
        flash(f"Évangéliste {e.nom_complet} enregistré.", "success")
        return redirect(url_for("evangelistes_list"))
    return render_template("evangeliste_form.html", e=e)


@app.route("/evangelistes/<int:evangeliste_id>/supprimer", methods=["POST"])
@login_required
def evangeliste_delete(evangeliste_id):
    e = Evangeliste.query.get_or_404(evangeliste_id)
    nom = e.nom_complet
    db.session.delete(e)
    db.session.commit()
    flash(f"Évangéliste {nom} supprimé.", "info")
    return redirect(url_for("evangelistes_list"))


# ----------------------------------------------------------------------------
# Planning évangélisation
# ----------------------------------------------------------------------------
@app.route("/planning")
@login_required
def planning_list():
    annee = int(request.args.get("annee", date.today().year))
    semaine = int(request.args.get("semaine", date.today().isocalendar()[1]))
    evangeliste_id = request.args.get("evangeliste_id", "")

    query = RDVEvangelisation.query.filter_by(annee=annee, numero_semaine=semaine)
    if evangeliste_id:
        query = query.filter_by(evangeliste_id=int(evangeliste_id))
    rdvs = query.order_by(RDVEvangelisation.jour, RDVEvangelisation.heure).all()

    evangelistes = Evangeliste.query.order_by(Evangeliste.nom).all()
    return render_template(
        "planning_list.html",
        rdvs=rdvs, annee=annee, semaine=semaine,
        evangeliste_id=evangeliste_id, evangelistes=evangelistes,
    )


@app.route("/planning/nouveau", methods=["GET", "POST"])
@app.route("/planning/<int:rdv_id>/editer", methods=["GET", "POST"])
@login_required
def rdv_form(rdv_id=None):
    r = RDVEvangelisation.query.get(rdv_id) if rdv_id else None
    evangelistes = Evangeliste.query.order_by(Evangeliste.nom).all()
    if request.method == "POST":
        if r is None:
            r = RDVEvangelisation()
            db.session.add(r)
        r.evangeliste_id = int(request.form.get("evangeliste_id"))
        r.annee = int(request.form.get("annee") or date.today().year)
        r.numero_semaine = int(request.form.get("numero_semaine"))
        r.jour = request.form.get("jour", "")
        r.heure = request.form.get("heure", "").strip()
        r.type_ame = request.form.get("type_ame", "")
        r.nom_ame = request.form.get("nom_ame", "").strip()
        r.tel_ame = request.form.get("tel_ame", "").strip()
        r.lieu_rdv = request.form.get("lieu_rdv", "").strip()
        r.statut_rdv = request.form.get("statut_rdv", "NOK")
        r.statut_engagement = request.form.get("statut_engagement", "NOK")
        db.session.commit()
        flash("RDV enregistré.", "success")
        return redirect(url_for("planning_list", annee=r.annee, semaine=r.numero_semaine))
    return render_template(
        "rdv_form.html", r=r, evangelistes=evangelistes,
        semaine_defaut=date.today().isocalendar()[1], annee_defaut=date.today().year,
    )


@app.route("/planning/<int:rdv_id>/statut", methods=["POST"])
@login_required
def rdv_update_statut(rdv_id):
    r = RDVEvangelisation.query.get_or_404(rdv_id)
    r.statut_rdv = request.form.get("statut_rdv", r.statut_rdv)
    r.statut_engagement = request.form.get("statut_engagement", r.statut_engagement)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/planning/<int:rdv_id>/supprimer", methods=["POST"])
@login_required
def rdv_delete(rdv_id):
    r = RDVEvangelisation.query.get_or_404(rdv_id)
    db.session.delete(r)
    db.session.commit()
    flash("RDV supprimé.", "info")
    return redirect(url_for("planning_list"))


# ----------------------------------------------------------------------------
# Assiduité adoration du dimanche
# ----------------------------------------------------------------------------
@app.route("/adoration", methods=["GET", "POST"])
@login_required
def adoration():
    date_str = request.args.get("date") or request.form.get("date") or last_sunday().isoformat()
    try:
        d_dim = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        d_dim = last_sunday()
    semaine = d_dim.isocalendar()[1]
    annee = d_dim.isocalendar()[0]

    disciples = Disciple.query.order_by(Disciple.nom, Disciple.prenom).all()

    if request.method == "POST":
        for disc in disciples:
            present = request.form.get(f"present_{disc.id}") == "on"
            rec = Adoration.query.filter_by(disciple_id=disc.id, date_dimanche=d_dim).first()
            if rec is None:
                rec = Adoration(disciple_id=disc.id, date_dimanche=d_dim,
                                numero_semaine=semaine, annee=annee, present=present)
                db.session.add(rec)
            else:
                rec.present = present
                rec.numero_semaine = semaine
                rec.annee = annee
        db.session.commit()
        flash(f"Présences du {d_dim.strftime('%d/%m/%Y')} enregistrées.", "success")
        return redirect(url_for("adoration", date=d_dim.isoformat()))

    existing = {a.disciple_id: a.present for a in Adoration.query.filter_by(date_dimanche=d_dim).all()}
    return render_template(
        "adoration.html",
        disciples=disciples, date_dimanche=d_dim,
        semaine=semaine, annee=annee, existing=existing,
    )


# ----------------------------------------------------------------------------
# Rapports
# ----------------------------------------------------------------------------
@app.route("/rapports/evangelisation")
@login_required
def rapport_evangelisation():
    periode_type = request.args.get("periode_type", "semaine")  # semaine / mois
    annee = int(request.args.get("annee", date.today().year))
    semaine = int(request.args.get("semaine", date.today().isocalendar()[1]))
    mois = int(request.args.get("mois", date.today().month))
    evangeliste_id = request.args.get("evangeliste_id", "")

    query = RDVEvangelisation.query.filter_by(annee=annee)
    periode_libelle = ""
    if periode_type == "semaine":
        query = query.filter_by(numero_semaine=semaine)
        periode_libelle = f"Semaine {semaine} - {annee}"
    else:
        # Approximation par numéros de semaines qui appartiennent au mois
        semaines_du_mois = _semaines_du_mois(annee, mois)
        query = query.filter(RDVEvangelisation.numero_semaine.in_(semaines_du_mois))
        periode_libelle = f"{MOIS_LIBELLES[mois-1]} {annee}"

    rdvs_assemblee = query.all()
    rdvs_evangeliste = [r for r in rdvs_assemblee if str(r.evangeliste_id) == evangeliste_id] if evangeliste_id else []

    def stats(lst):
        total = len(lst)
        ok = sum(1 for r in lst if r.statut_rdv == "OK")
        eng = sum(1 for r in lst if r.statut_engagement == "OK")
        taux_ok = round(ok / total * 100, 1) if total else 0
        taux_eng = round(eng / total * 100, 1) if total else 0
        return dict(total=total, ok=ok, eng=eng, taux_ok=taux_ok, taux_eng=taux_eng)

    evangelistes = Evangeliste.query.order_by(Evangeliste.nom).all()
    return render_template(
        "rapport_evangelisation.html",
        periode_type=periode_type, annee=annee, semaine=semaine, mois=mois,
        periode_libelle=periode_libelle,
        evangeliste_id=evangeliste_id, evangelistes=evangelistes,
        stats_assemblee=stats(rdvs_assemblee),
        stats_evangeliste=stats(rdvs_evangeliste) if evangeliste_id else None,
        mois_libelles=MOIS_LIBELLES,
    )


@app.route("/rapports/assiduite")
@login_required
def rapport_assiduite():
    periode_type = request.args.get("periode_type", "mois")  # mois / annee
    annee = int(request.args.get("annee", date.today().year))
    mois = int(request.args.get("mois", date.today().month))
    disciple_id = request.args.get("disciple_id", "")

    query = Adoration.query.filter_by(annee=annee)
    periode_libelle = ""
    if periode_type == "mois":
        query = query.filter(db.extract("month", Adoration.date_dimanche) == mois)
        periode_libelle = f"{MOIS_LIBELLES[mois-1]} {annee}"
    else:
        # Pour une année : prendre en compte les mois achevés uniquement
        today = date.today()
        if annee == today.year:
            query = query.filter(db.extract("month", Adoration.date_dimanche) < today.month)
            periode_libelle = f"Année {annee} (jusqu'à {MOIS_LIBELLES[today.month-2]} inclus)" if today.month > 1 else f"Année {annee} (aucun mois achevé)"
        else:
            periode_libelle = f"Année {annee}"

    ados_assemblee = query.all()
    ados_disciple = [a for a in ados_assemblee if str(a.disciple_id) == disciple_id] if disciple_id else []

    # Nombre d'adorations uniques (dimanches enregistrés distincts) sur la période
    def stats(lst):
        dimanches_uniques = set(a.date_dimanche for a in lst)
        total_dim = len(dimanches_uniques)
        nb_pres = sum(1 for a in lst if a.present)
        nb_abs = sum(1 for a in lst if not a.present)
        total = len(lst)
        taux_pres = round(nb_pres / total * 100, 1) if total else 0
        taux_abs = round(nb_abs / total * 100, 1) if total else 0
        return dict(
            total_dim=total_dim, nb_pres=nb_pres, nb_abs=nb_abs,
            taux_pres=taux_pres, taux_abs=taux_abs, total=total,
        )

    disciples = Disciple.query.order_by(Disciple.nom, Disciple.prenom).all()
    return render_template(
        "rapport_assiduite.html",
        periode_type=periode_type, annee=annee, mois=mois,
        periode_libelle=periode_libelle,
        disciple_id=disciple_id, disciples=disciples,
        stats_assemblee=stats(ados_assemblee),
        stats_disciple=stats(ados_disciple) if disciple_id else None,
        mois_libelles=MOIS_LIBELLES,
    )


# ----------------------------------------------------------------------------
# Utilitaires
# ----------------------------------------------------------------------------
MOIS_LIBELLES = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


def _semaines_du_mois(annee, mois):
    """Retourne la liste des numéros de semaines ISO qui contiennent un jour du mois donné."""
    from datetime import timedelta
    semaines = set()
    d = date(annee, mois, 1)
    while d.month == mois:
        semaines.add(d.isocalendar()[1])
        d += timedelta(days=1)
    return list(semaines)


@app.context_processor
def inject_globals():
    return dict(
        current_year=date.today().year,
        mois_libelles=MOIS_LIBELLES,
    )


# ----------------------------------------------------------------------------
# Init DB
# ----------------------------------------------------------------------------
def init_db():
    with app.app_context():
        db.create_all()


init_db()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
