#!/usr/bin/env python3
"""Gate de sécurité des dépendances (J2 - exercice 13).

Lit le rapport JSON de pip-audit, récupère la sévérité de chaque vulnérabilité
dans la base publique OSV (via son alias GitHub Advisory, GHSA) et fait échouer
le build si au moins une vulnérabilité est de sévérité CRITICAL.

Usage : python3 pip_audit_gate.py pip-audit.json [SEUIL]
SEUIL : CRITICAL (défaut) ou HIGH.
"""
import json
import sys
import urllib.request

ORDRE = {"LOW": 1, "MODERATE": 2, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


ERREURS_RESEAU = []


def severite_osv(identifiant, cache={}):
    if identifiant in cache:
        return cache[identifiant]
    niveau = None
    try:
        url = f"https://api.osv.dev/v1/vulns/{identifiant}"
        with urllib.request.urlopen(url, timeout=15) as reponse:
            fiche = json.load(reponse)
        niveau = (fiche.get("database_specific") or {}).get("severity")
        niveau = niveau.upper() if niveau else None
    except Exception as erreur:
        ERREURS_RESEAU.append(f"{identifiant} : {erreur}")
        niveau = None
    cache[identifiant] = niveau
    return niveau


def main():
    rapport = json.load(open(sys.argv[1]))
    seuil = (sys.argv[2] if len(sys.argv) > 2 else "CRITICAL").upper()
    bloquantes, vues = [], set()

    print(f"{'Paquet':<10} {'Version':<8} {'Vulnérabilité':<18} {'Alias':<40} Sévérité")
    print("-" * 95)
    for dep in rapport.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            cle = (dep["name"], vuln["id"])
            if cle in vues:
                continue
            vues.add(cle)
            alias = vuln.get("aliases", [])
            niveau = None
            for ident in [vuln["id"]] + alias:
                if ident.startswith("GHSA-"):
                    niveau = severite_osv(ident)
                    if niveau:
                        break
            niveau_affiche = niveau or "INCONNUE"
            print(f"{dep['name']:<10} {dep['version']:<8} {vuln['id']:<18} {','.join(alias)[:40]:<40} {niveau_affiche}")
            if niveau and ORDRE.get(niveau, 0) >= ORDRE[seuil]:
                bloquantes.append((dep["name"], dep["version"], vuln["id"], alias, vuln.get("fix_versions", [])))

    print()
    # Fail-closed : si OSV est injoignable, on ne peut pas conclure -> on bloque
    if ERREURS_RESEAU:
        print("ÉCHEC DE LA GATE DÉPENDANCES : base OSV injoignable, sévérités impossibles à vérifier.")
        for ligne in ERREURS_RESEAU[:5]:
            print(f"  - {ligne}")
        sys.exit(2)
    if bloquantes:
        print(f"ÉCHEC DE LA GATE DÉPENDANCES : {len(bloquantes)} vulnérabilité(s) de sévérité >= {seuil}")
        for nom, version, ident, alias, correctifs in bloquantes:
            print(f"  - {nom} {version} : {ident} ({', '.join(alias)}) -> corrigé en {', '.join(correctifs) or 'aucune version'}")
        print("Mettez ces dépendances à jour avant tout déploiement.")
        sys.exit(1)
    print(f"Gate dépendances OK : aucune vulnérabilité de sévérité >= {seuil}")


if __name__ == "__main__":
    main()
