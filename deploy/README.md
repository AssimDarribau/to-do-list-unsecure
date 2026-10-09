# Déploiement de la todolist

Playbook Ansible issu du TP J1 (déploiement + durcissement), piloté par Jenkins.

## Lancement

    ansible-playbook deploy_app.yml --limit <app-dev|app-prod1> -e branch=<branche> --private-key <clé>

- `--limit` : environnement cible (app-dev = recette, app-prod1 = production)
- `-e branch=` : branche Git de l'application à déployer (main par défaut)
- `--skip-tags audit` : saute l'audit Lynis (plus rapide)

## Règle de production

La production (app-prod1, `prod_env: true`) ne reçoit **que la branche `main`**,
c'est-à-dire du code déjà testé et validé. Le playbook refuse tout autre
déploiement en prod (tâche `assert` en tête de playbook), et le job Jenkins
applique la même règle avant même de lancer Ansible.

## Accès

Les clés publiques autorisées sur les serveurs sont dans `keys/` (admin et
compte de déploiement Jenkins). Aucune clé privée ne doit être commitée.
