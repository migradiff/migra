# MigraDiff

<div align="center">

**Choisissez une langue:**  
[English](README.md) | 
[हिन्दी](README.hi.md) | 
[中文](README.zh.md) | 
[日本語](README.ja.md) | 
[Français](README.fr.md) | 
[Deutsch](README.de.md) | 
[עברית](README.he.md)

</div>

---

# migra — Outil de Différence de Schéma PostgreSQL

[![PyPI version](https://img.shields.io/pypi/v/migradiff)](https://pypi.org/project/migradiff/)
[![Python versions](https://img.shields.io/pypi/pyversions/migradiff)](https://pypi.org/project/migradiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**C'est le fork activement maintenu de [djrobstep/migra](https://github.com/djrobstep/migra).**

migra compare deux schémas de bases de données PostgreSQL et génère le script de migration SQL nécessaire pour transformer l'un en l'autre. Intégrez-le dans votre pipeline CI et arrêtez d'écrire `ALTER TABLE` à la main.

---

## Pourquoi ce Fork

Le `migra` original a été officiellement déprécié en 2024. Ce fork reprend là où il s'est arrêté — en corrigeant les problèmes connus, en ajoutant le support Python 3.12+, et en étendant la couverture pour les fonctionnalités PostgreSQL avancées.

Si vous utilisiez `djrobstep/migra`, ceci est votre continuation directe. Rien n'a changé dans le fonctionnement de l'outil. Nous assurons simplement la continuité et l'amélioration.

**Note sur le nommage :** Ceci est un fork communautaire indépendant. La commande CLI reste `migra` pour la rétrocompatibilité avec les scripts et pipelines existants. Le nom du paquet est `migradiff` pour le distinguer de l'upstream déprécié. Si vous recherchez le djrobstep/migra original, il est archivé à https://github.com/djrobstep/migra.

---

## Démarrage Rapide

### Installation

```bash
pip install migradiff
```

Nécessite Python 3.10+ et une instance PostgreSQL en cours d'exécution (12+).

Pour installer depuis les sources :

```bash
git clone https://github.com/migradiff/migra
cd migra
pip install -e .
```

### Utilisation de Base

Pointez migra vers deux connexions de base de données et il génère le DDL nécessaire pour migrer de l'une vers l'autre :

```bash
migra \
  postgresql://user:pass@localhost/db_production \
  postgresql://user:pass@localhost/db_branch \
  --unsafe
```

La sortie est du SQL pur — pipez-la, révisez-la, appliquez-la :

```bash
migra postgres://db_a postgres://db_b > migration.sql
psql postgres://db_production < migration.sql
```

### Dumps de Schéma (Aucune Connexion en Direct Requise)

Si vous ne pouvez pas ou ne voulez pas pointer migra vers une base de données en direct, utilisez `pg_dump -s` pour générer un dump de schéma et comparer celui-ci à la place :

```bash
pg_dump -s postgres://db_production > schema_a.sql
pg_dump -s postgres://db_branch     > schema_b.sql
migra --from-file schema_a.sql schema_b.sql
```

C'est l'approche recommandée pour les pipelines CI et les environnements soucieux de la sécurité — aucune information d'identification de production requise.

### Répertoire de Migrations (Aucune Base de Données de Branche en Direct Requise)

Si votre état cible est défini par un dossier de fichiers de migration :

```bash
migra --from-migrations-dir ./migrations postgres://db_production
```

MigraDiff applique les migrations à une base de données éphémère et compare le résultat. Prend en charge Supabase, Flyway et les conventions de nommage numérique standard.

### Limité à un Schéma

```bash
# Schéma unique
migra --schema myschema postgres://db_a postgres://db_b

# Plusieurs schémas (séparés par des virgules)
migra --schema public,reporting postgres://db_a postgres://db_b
```

### Sortie JSON

Pour une consommation programmatique ou des pipelines CI :

```bash
migra --output json postgres://db_a postgres://db_b
```

La sortie inclut une classification des risques par instruction (`safe`, `warning`, `destructive`) et un résumé avec le niveau de risque global.

---

## Explication par IA (Optionnelle)

MigraDiff peut expliquer n'importe quelle migration en langage clair — ce que fait chaque changement, les risques qu'il comporte, et des alternatives plus sûres pour les opérations destructrices.

    migra --explain postgres://db_a postgres://db_b

Sortie :

    --- Migration SQL ---
    ALTER TABLE public.users ADD COLUMN email text;
    DROP TABLE public.legacy_sessions;

    --- AI Explanation ---
    This migration makes 2 changes to your database:

    1. SAFE: Adds an email column (text) to the users table.
       No existing data is affected.

    2. ⚠ DESTRUCTIVE: Drops the legacy_sessions table entirely.
       All data in this table will be permanently lost.
       Consider archiving before dropping.

    Overall risk: HIGH

Propulsé par Claude (Anthropic). Apportez votre propre clé API — aucune donnée n'est envoyée aux serveurs MigraDiff.

### Configuration

Installez les extras IA :

    pip install migradiff[ai]

Configurez votre clé API une fois :

    migra --setup-ai

Ou définissez la variable d'environnement :

    export ANTHROPIC_API_KEY=sk-ant-...

Obtenez une clé API sur https://console.anthropic.com

### Génération de Rollback par IA (--rollback)

Générez la migration inverse exacte — le SQL nécessaire pour annuler n'importe quelle migration :

    migra --rollback migration.sql
    migra --rollback postgres://db_a postgres://db_b

MigraDiff utilise le contexte de votre schéma source pour reconstruire avec précision les annulations de DROP TABLE et DROP COLUMN. Les opérations non réversibles (TRUNCATE, DELETE en masse) sont explicitement signalées.

Combinez avec --explain pour une image complète :

    migra --explain --rollback postgres://db_a postgres://db_b

Nécessite `pip install migradiff[ai]` et une clé API Anthropic.

### Conseiller en Performances par IA (--advise)

Avant d'appliquer une migration, obtenez une évaluation des risques de performance — verrouillage, risque de réécriture de table, alternatives sans temps d'arrêt :

    migra --advise postgres://db_a postgres://db_b
    migra --advise migration.sql

MigraDiff analyse chaque instruction pour les risques spécifiques à PostgreSQL : verrous de table, réécritures complètes, perte de données irréversible. Lorsqu'une connexion en direct est fournie, les nombres de lignes des tables sont utilisés pour estimer la durée de verrouillage à votre échelle de données réelle.

Combinez les trois fonctionnalités IA pour une image complète :

    migra --explain --advise --rollback postgres://db_a postgres://db_b

Nécessite pip install migradiff[ai] et une clé API Anthropic.

### Générateur de Migration par IA (--generate)

Décrivez ce que vous voulez en langage clair — MigraDiff génère le SQL de migration basé sur votre schéma réel :

    migra --generate "add email verification to users table" \
      postgres://db_production

Contrairement aux outils IA génériques, MigraDiff connaît vos vrais noms de tables, types de colonnes et contraintes — pas de noms de colonnes hallucinés ni de types erronés.

Générez et révisez immédiatement le risque :

    migra --generate "add index on orders.user_id" \
      --advise postgres://db_production

Nécessite pip install migradiff[ai] et une clé API Anthropic.

---

## Configuration de Développement

La suite de tests nécessite une instance PostgreSQL en cours d'exécution. Le moyen le plus simple est via Docker Compose :

```bash
docker compose up -d
```

Ceci démarre un conteneur Postgres 16 sur localhost:5432 avec authentification de confiance. Aucun mot de passe requis.

Pour l'arrêter :

```bash
docker compose down
```

Les données persistent entre les redémarrages via le volume `migradiff-pgdata`. Pour réinitialiser complètement :

```bash
docker compose down -v
```

---

## Docker

Pas d'environnement Python ? Utilisez l'image officielle :

```bash
docker run --rm ghcr.io/migradiff/migra \
  postgres://db_a postgres://db_b
```

---

## GitHub Actions

Ajoutez la comparaison de schéma à votre workflow de pull request :

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
```

Échouez automatiquement la build si des opérations destructrices sont détectées :

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
    fail_on_destructive: "true"
```

Utilisez des fichiers de dump de schéma au lieu de connexions en direct :

```yaml
- uses: migradiff/migra@v1
  with:
    base_file: schema_production.sql
    head_file: schema_branch.sql
```

Voir [docs/action-usage.md](docs/action-usage.md) pour les options de configuration complètes.

---

## Hook Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/migradiff/migra
    rev: v1.1.0
    hooks:
      - id: migra
```

Voir `pre-commit-config.example.yaml` à la racine du dépôt pour les options de configuration complètes.

---

## Ce que migra Comprend

- Tables, colonnes, contraintes, index
- Vues et vues matérialisées
- Fonctions et procédures stockées
- Séquences
- Énumérations, types composites, domaines
- Politiques de sécurité au niveau des lignes (RLS)
- Wrappers de données distantes (FDW)
- Privilèges au niveau des colonnes
- Tables partitionnées
- Commentaires d'objets (`COMMENT ON`)

---

## Améliorations par Rapport à l'Upstream

| Domaine | Upstream (déprécié) | Ce Fork |
|---|---|---|
| Python 3.12+ | Avertissements de dépréciation | Propre — aucun avertissement |
| Politiques RLS | Partielles, bug d'égalité | CREATE/DROP complets, support des partitions |
| Messages d'erreur | Cryptiques pour les types non supportés | Actionnable avec nom d'objet et lien vers le problème |
| Drapeau --schema | Cas limites dans les bases multi-schémas | Séparés par des virgules, dépendances inter-schémas résolues |
| Entrée pg_dump | Non supporté | Mode `--from-file` de première classe |
| Sortie JSON | Non supporté | `--output json` avec classification des risques |
| Image Docker | Aucune | `ghcr.io/migradiff/migra` |
| GitHub Action | Aucune | `migradiff/migra-action` |
| Hook Pre-commit | Aucun | `.pre-commit-hooks.yaml` |
| Environnement de développement | Commandes Docker manuelles | `docker compose up -d` |
| Explication IA | Aucune | Drapeau `--explain` avec Claude — explication de différence en langage clair, analyse des risques, alternatives plus sûres |
| Différence COMMENT ON | Non supporté | Différence complète — ajout/modification/suppression sur tous les types d'objets |

Voir [CHANGELOG.md](CHANGELOG.md) pour l'historique complet des correctifs.

---

## Limitations Connues

migra génère la différence SQL — il ne l'applique pas. Révisez chaque script généré avant de l'exécuter en production. Les opérations destructrices (`DROP TABLE`, `DROP COLUMN`) sont signalées en mode sortie JSON mais pas bloquées en mode SQL brut.

migra nécessite une connexion PostgreSQL en direct pour introspecter les schémas, ou des fichiers de dump de schéma via `--from-file`. Il n'analyse pas le texte DDL brut.

---

## Contribution

Les signalements de bugs et les PR sont les bienvenus. Si vous corrigez quelque chose qui a été signalé dans `djrobstep/migra`, référencez ce numéro de problème dans votre PR — cela nous aide à suivre ce que la communauté a le plus besoin de voir corrigé.

```bash
git clone https://github.com/migradiff/migra
cd migra
docker compose up -d
pip install -e ".[dev]"
pytest
```

---

## Licence

MigraDiff est **gratuit et open source** sous licence MIT.

**Toutes les fonctionnalités fonctionnent pour tout le monde.** Pas de paywall, pas de restrictions de code, pas de barrieres.

### Une breve histoire

J'ai passe plus de 8 ans en tant qu'ingenieur chez Philips, a supporter des systemes informatiques hospitaliers qui protegent les patients. Quand le VC qui a acquis notre division m'a licencie, j'avais plus de 50 ans dans un marche ou l'age compte. Trouver un autre emploi est devenu presque impossible. Je dois encore subvenir aux besoins de ma famille et mettre de la nourriture sur la table.

C'est pourquoi MigraDiff existe. Je construis des outils qui vous aident, parce que c'est ainsi que je reste employe.

### La demande

**Si vous etes un etudiant, un amateur ou un projet open source :** Licence MIT, gratuit pour toujours. Aucun accord necessaire.

**Si vous etes une entreprise a but lucratif utilisant MigraDiff :** Veuillez signer un contrat de licence commerciale. Il ne s'agit pas de verrouiller le code—chaque fonctionnalite reste gratuite, vous l'executez localement, rien ne change techniquement pour vous. Il s'agit d'equite : si mon outil vous aide a gagner de l'argent, aidez-moi a nourrir ma famille.

Vous possedez toujours tout. Vous controllez vos donnees. Vous accedez a toutes les fonctionnalites. Nous faisons simplement preuve de transparence sur la facon dont nous soutenons le developpement.

Je ne demande pas la charite. Je demande l'equite.

[Obtenir une licence commerciale](https://lateos.ai/license) | [Voir la licence MIT](LICENSE)

---

## Remerciements

Ce projet est un fork de [djrobstep/migra](https://github.com/djrobstep/migra), créé et maintenu à l'origine par Robert Lechte. Le moteur de comparaison principal est son travail. Nous lui en sommes reconnaissants.
