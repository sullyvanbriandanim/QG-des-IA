"""Construit le dossier que Gaston range dans le QG à partir des données Tempoo.

Lecture seule : ce script ne lit que des fichiers JSON déjà téléchargés depuis Tempoo
(collection data/users/me/p/parts) et écrit un seul fichier JSON pour le QG.

Usage : python3 -I tempoo_snapshot.py <dossier_parts> <fichier_sortie.json>
"""
import collections
import datetime
import json
import os
import sys

MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']


def fr(d):
    y, m, j = (int(x) for x in d[:10].split('-'))
    return f"{j} {MOIS[m - 1]} {y}"


def joli_nom(n):
    # "BARON Tristan" -> "Tristan Baron"
    parts = n.split()
    nom = [p for p in parts if p.isupper() and len(p) > 1]
    prenom = [p for p in parts if p not in nom]
    if nom and prenom:
        return ' '.join(prenom) + ' ' + ' '.join(p.capitalize() for p in nom)
    return n


def load(dirp, name, key=None):
    path = os.path.join(dirp, name + '.json')
    if not os.path.exists(path):
        return {} if key is None else None
    data = json.load(open(path, encoding='utf-8'))
    return data.get(key) if key else data


def build(dirp):
    m = load(dirp, 'meta')
    rec = load(dirp, 'rec', 'rec') or {}
    ent = load(dirp, 'ent', 'ent') or {}
    ptyp = load(dirp, 'ptyp', 'ptyp') or []
    docs = load(dirp, 'docs', 'docs') or []
    crea = load(dirp, 'crea', 'crea') or []
    bud = load(dirp, 'bud', 'bud') or {}

    cats = {c['id']: c['n'] for c in m.get('cats', [])}
    tpl = m.get('templates', [])
    cnt = collections.Counter(cats.get(t.get('k'), 'Autre') for t in tpl)
    team = [{"name": joli_nom(a['name']), "role": a.get('role', ''), "from": a.get('cs', ''), "to": a.get('ce', ''),
             "h": a.get('contract', 0), **({"me": True} if a.get('me') else {})} for a in m.get('animators', [])]
    others = [t for t in team if not t.get('me')]
    hired_roles = {a.get('role') for a in m.get('animators', [])}
    posts = [p for p in rec.get('posts', []) if p.get('role') not in hired_roles]
    open_posts = [{"role": p.get('t') or p.get('role'), "nb": p.get('nb', 1), "from": p.get('from', ''), "to": p.get('to', ''), "h": p.get('h', 35)} for p in posts]
    cands = rec.get('cands', [])
    pending = [c for c in cands if c.get('st') not in ('hired', 'refused', 'no')]

    plan_items = []
    for p in ptyp:
        n = sum(len(d) for d in p.get('d', []))
        plan_items.append({"t": f"Planning type « {p['n']} » " + ("prêt" if n else "encore vide"),
                           "d": f"{p.get('h', '')} h · {n} créneaux sur la semaine" if n else f"{p.get('h', '')} h · aucun créneau saisi",
                           **({} if n else {"alert": True})})
    plan_items.append({"t": f"Équipe : {len(team)} contrat(s) dans Tempoo",
                       "d": " · ".join(f"{t['name']} du {fr(t['from'])} au {fr(t['to'])} ({t['h']} h)" for t in team if t['from'] and t['to'])})
    for o in open_posts:
        plan_items.append({"t": f"{o['nb']} poste(s) {o['role']} à pourvoir", "d": f"Du {fr(o['from'])} au {fr(o['to'])} · {o['h']} h · {len(pending)} candidat(s) en cours", "alert": True})
    for aid, lst in (m.get('chg') or {}).items():
        a = next((x for x in m.get('animators', []) if x['id'] == aid), None)
        if a:
            plan_items.append({"t": f"{joli_nom(a['name']).split()[0]} : {sum(len(c.get('days', [])) for c in lst)} changement(s) de disponibilité", "d": "Signalés depuis son espace animateur"})
    for aid, days in (m.get('fh') or {}).items():
        a = next((x for x in m.get('animators', []) if x['id'] == aid), None)
        if a and days:
            plan_items.append({"t": f"{joli_nom(a['name']).split()[0]} : {len(days)} feuille(s) d’heures saisie(s)", "d": ", ".join(fr(d) for d in sorted(days))})

    dispatch = {
        "anim": {"to": "lulu", "items": [
            {"t": f"{len(tpl)} fiches activités dans {len(cats)} catégories", "d": " · ".join(f"{k} {v}" for k, v in cnt.most_common())},
            {"t": f"{len(m.get('sotpl', []))} modèles de soirées", "d": ", ".join(t['t'] for t in m.get('sotpl', []))},
            {"t": f"{len(m.get('must', {}))} incontournables à caser dans le programme", "d": ", ".join(m.get('must', {}).keys())},
            {"t": f"{len(m.get('lieux', []))} lieux d’animation", "d": ", ".join(m.get('lieux', []))}]},
        "plan": {"to": "odile", "items": plan_items},
        "com": {"to": "margaux", "items": [
            {"t": f"{len(rec.get('msgs', []))} modèles de messages aux candidats", "d": ", ".join(x['n'] for x in rec.get('msgs', []))},
            {"t": f"{len(docs)} document(s) partagé(s) avec l’équipe", "d": "; ".join(f"{x.get('t', '')} ({fr(x['d'])})" for x in docs if x.get('d'))}]},
        "cm": {"to": "zoe", "items": [
            *[{"t": "Création Canva : " + (c.get('p', '')[:70] + ('…' if len(c.get('p', '')) > 70 else '')), "d": "À réutiliser en post ou en affiche", **({"url": c['url']} if c.get('url') else {})} for c in crea],
            *[{"t": f"Offre à relayer : {o['nb']} × {o['role']}", "d": f"Du {fr(o['from'])} au {fr(o['to'])} · {o['h']} h"} for o in open_posts]]},
        "suivi": {"to": "rose", "items": [
            {"t": f"{len(ent.get('tpl', []))} trames d’entretien prêtes", "d": ", ".join(x['name'] for x in ent.get('tpl', []))},
            {"t": f"{len(ent.get('mods', []))} modules d’évaluation par poste", "d": ", ".join(x['name'] for x in ent.get('mods', []))},
            {"t": f"{len(ent.get('ses', []))} entretien(s) enregistré(s)", "d": ""}]},
    }
    refs = ['rose', 'basile', 'capucine', 'elio']
    people = [{"who": t['name'], "role": t['role']} for t in others]
    for o in open_posts:
        for i in range(o['nb']):
            people.append({"who": f"{o['role']} n°{i + 1}", "role": f"À recruter ({fr(o['from'])})"})
    while len(people) < 4:
        people.append({"who": f"{len(people) + 1}e animateur/trice", "role": "Poste pas encore ouvert dans Tempoo"})
    referents = [dict(ref=r, **people[i]) for i, r in enumerate(refs)]

    env = (bud.get('env') or {})
    alerts = []
    if not bud.get('items') and not env.get('mat') and not env.get('presta'):
        alerts.append("Budget animation pas encore renseigné (matériel et prestataires à 0 €)")
    if any('sauvegarde' in k.lower() for k in (m.get('mjSeen') or {})):
        alerts.append("Tempoo signale qu’aucune sauvegarde de la saison n’a été téléchargée")
    for e in m.get('events', []):
        alerts.append(f"{e.get('t', '').replace('🔔', '').strip()} le {fr(e['d'])}")

    return {"source": "Tempoo", "syncedAt": datetime.date.today().isoformat(), "camp": "Camping Sandaya La Nublière",
            "team": team, "openPosts": open_posts, "dispatch": dispatch, "referents": referents, "alerts": alerts}


if __name__ == '__main__':
    snap = build(sys.argv[1])
    json.dump(snap, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: len(v['items']) for k, v in snap['dispatch'].items()}, ensure_ascii=False))
