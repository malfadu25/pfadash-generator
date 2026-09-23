# Générateur du Dashboard PFA — Bloc Sud (GPEI)

Générateur reproductible du tableau de bord de surveillance des PFA du Bloc Sud-Est
(Haut-Katanga, Haut-Lomami, Lualaba, Tanganyika). Il remplace la rustine manuelle
du fichier HTML : à chaque mise à jour hebdomadaire, il recalcule les champs de
données par zone de santé à partir des canevas provinciaux, et reporte le scoring.

## Ce qu'il fait

`build_dashboard.py` prend :
- un **gabarit** (le dernier dashboard HTML, qui porte le tableau `D` des 68 zones,
  le scoring, les isolats, l'historique et la structure des onglets) ;
- les **quatre canevas provinciaux** de la semaine (onglets `Base de données` et `ZS`).

Il produit un dashboard HTML à jour, en recalculant par zone de santé :
`c26`, `pfa_o15`, `pop15_25`, `pop15_26`, `t26`, `ta26`, `t12`, `ta12`.

## Méthodologie (fait foi : consigne projet)

- **Numérateur** depuis la **liste linéaire** (`Base de données`), jamais la synthèse :
  EPID distincts, **contacts exclus** (colonne Cas(1)/Contact(2) = 2, ou EPID en `-Cx`/`CC`),
  cas **< 15 ans** (les ≥ 15 ans vont dans `pfa_o15`). Les séparateurs d'EPID sont
  normalisés pour dédoublonner les fautes de frappe (double tiret, parenthèse).
- **Populations < 15 ans** : onglet `ZS`, colonne « Pop <15 ans 2026 ». On pose
  `pop15_25 = pop15_26`. Exclure la ligne « Total » et la ligne au nom de la province.
- **Taux** : `t26 = c26 / pop15_26 × 1e5 × 52 / semaine` ; `ta26 = t26 × IF`.
  Idem sur 12 mois (`t12`, `ta12`). La semaine d'annualisation est la **semaine max
  réelle** de la liste linéaire (paramètre `SEMAINE`, actuellement 38).
- **Seuil de sensibilité** du taux de PFA non polio : **≥ 3 pour 100 000** enfants
  de moins de 15 ans (décision projet ; ne jamais utiliser 2).
- **Alias de zones** : `RUASHI` (dashboard) = `RWASHI` (fichiers).

## Ce qui est REPORTÉ (passe de scoring périodique, pas hebdomadaire)

Conformément à la consigne, la mise à jour hebdomadaire **ne recalcule pas**
`cat` (CONFORME / SOUS-SEUIL), `flags`, `priority`, `risk_*` : ce sont des indices
composites (à part de jugement) recalculés lors d'une passe de scoring séparée.
Le générateur les **reporte** du gabarit précédent.

## Validation (reproduction de l'étalon)

Sur le dashboard v9.7 et les canevas S38 :
- Haut-Katanga 135/135, Haut-Lomami 80/80, Tanganyika 55/55 champs concordants.
- Lualaba : le générateur produit les comptes corrects depuis la liste linéaire ;
  les écarts avec le dashboard reflètent des fautes de saisie de la base Lualaba S38
  (doublons à double tiret, un cas de Sandoa classé sous Lualaba), signalées à la
  province pour correction.

## À reconstituer exactement (TODO)

- `aq26` (% selles adéquates) : le dashboard d'origine le calcule sur la liste
  linéaire avec sa propre définition d'adéquation. En attendant sa reconstitution
  exacte, `aq26` est **reporté** du gabarit précédent (non écrasé).
- `c12` (fenêtre 12 mois) : à recalculer depuis les dates de la liste linéaire.
- Anonymisation Managers → Public (codes AT-/AP- stables) : à intégrer.
- Mise à jour de `__META__` (version, semaine, changelog) et du pied de page.

## Utilisation

```bash
python3 build_dashboard.py            # lit le gabarit + 4 canevas, écrit le HTML à jour
```

Adapter les chemins des canevas et du gabarit en tête de la section `__main__`.

## Contexte

Coordination GPEI Bloc Sud-Est (RDC). Deux versions du dashboard sont produites
à chaque mise à jour : `PUBLIC` (anonymisée) et `SECURISE` (noms + codes).
Ce dépôt ne contient **aucune donnée sensible** : ni noms d'agents, ni line list.
