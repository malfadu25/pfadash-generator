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

## Version publique et bandeau (implémenté)

- **Version PUBLIC** : produite automatiquement à partir de la version MANAGERS.
  Chaque `"Nom (CODE)"` devient `"CODE"` (codes AT-/AP-). Validé : reproduit
  exactement la version publique de référence (0 nom résiduel, 2 377 codes).
- **Bandeau `__META__`** : mise à jour de `version`, `semaine`, `date_maj`, ajout
  d'une entrée de `changelog` en tête, et bascule du numéro de version du titre et
  du pied de page (`Dashboard PFA vX.Y`).

## Ce qui est REPORTÉ (passe de scoring périodique, pas hebdomadaire)

Conformément à la consigne, la mise à jour hebdomadaire **ne recalcule pas**
`cat` (CONFORME / SOUS-SEUIL), `flags`, `priority`, `risk_*` : ce sont des indices
composites (à part de jugement) recalculés lors d'une passe de scoring séparée.
`aq26` (% selles adéquates) relève également de cette passe (la consigne ne le
liste pas parmi les champs hebdomadaires), et est donc **reporté**, pas écrasé
par le pourcentage de la synthèse provinciale. Le générateur reporte tous ces
champs du gabarit précédent.

## Validation (reproduction de l'étalon)

Sur le dashboard v9.7 et les canevas S38 :
- Haut-Katanga 135/135, Haut-Lomami 80/80, Tanganyika 55/55 champs concordants.
- Lualaba : le générateur produit les comptes corrects depuis la liste linéaire ;
  les écarts avec le dashboard reflètent des fautes de saisie de la base Lualaba S38
  (doublons à double tiret, un cas de Sandoa classé sous Lualaba), signalées à la
  province pour correction.

## Champs reportés qui exigent des données hors du canevas hebdomadaire

Ces champs ne peuvent pas être recalculés à partir des seuls canevas de la semaine
et sont donc **reportés** du gabarit précédent (comportement correct) :

- `c12` (fenêtre 12 mois glissante) : les canevas hebdomadaires ne couvrent que
  l'année en cours (2026), or la fenêtre de 12 mois déborde sur fin 2025 (vérifié :
  34 zones sur 68 ont `c12 > c26`). Son calcul exige une **line list historique
  multi-années** (type POLIOCASES.csv). Une fois ce fichier fourni, le générateur
  pourra compter les cas < 15 ans distincts par ZS sur les 12 mois glissants, et
  `t12`/`ta12` se recalculeront automatiquement.
- Passe de scoring périodique (`cat`, `flags`, `priority`, `risk_*`, `aq26`) :
  indices composites rejoués ponctuellement lors d'une passe séparée.

## Contrôle qualité des canevas (rappel)

Le parseur signale les anomalies de saisie (le dédoublonnage des EPID a révélé,
dans la base Lualaba S38, des doublons à double tiret, un cas de Sandoa classé
sous Lualaba, et une date de paralysie erronée en « 2028 »). Toujours présenter
la réconciliation à l'utilisateur avant d'écrire, et proposer un courriel de
correction à la province si l'anomalie vient d'elle.

## Utilisation

```bash
python3 build_dashboard.py            # lit le gabarit + 4 canevas, écrit le HTML à jour
```

Adapter les chemins des canevas et du gabarit en tête de la section `__main__`.

## Contexte

Coordination GPEI Bloc Sud-Est (RDC). Deux versions du dashboard sont produites
à chaque mise à jour : `PUBLIC` (anonymisée) et `SECURISE` (noms + codes).
Ce dépôt ne contient **aucune donnée sensible** : ni noms d'agents, ni line list.
